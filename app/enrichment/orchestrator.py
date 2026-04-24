"""Enrichment orchestrator.

Runs IOC lookups in parallel via ThreadPoolExecutor, tracks job progress in a
thread-safe dict, retries failed lookups once, and evicts old jobs via LRU.

Design decisions:
- max_workers=20 default: thread pool is no longer the concurrency gate; per-provider
  semaphores cap rate-limited providers (e.g. VT at 4) while zero-auth providers run freely.
- _semaphores dict: keyed by adapter name; built for adapters with requires_api_key=True;
  each semaphore limits peak concurrent lookups for that provider (default cap: 4).
- Zero-auth adapters (requires_api_key=False) have no semaphore — unlimited concurrency.
- Semaphore wraps each individual attempt (cache-check + lookup + cache-store) in _do_lookup,
  but NOT the backoff sleep between retries. This prevents concurrent 429s from holding all
  semaphore slots while sleeping, which would starve every other queued IOC.
- OrderedDict for LRU eviction: simple FIFO eviction without external libraries.
- Lock protects all reads/writes to _jobs dict and the job-scoped diagnostics snapshots.
- Fresh requests.Session is the adapter's responsibility (Pitfall 3).
- Diagnostics stay job-local inside the orchestrator; shared adapters remain stateless.
"""
from __future__ import annotations

import logging
import random
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, Semaphore
from typing import Any

from app.cache.store import CacheStore
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC

logger = logging.getLogger(__name__)

# 429 / rate-limit backoff parameters
_BACKOFF_BASE = 15            # seconds for first retry delay
_BACKOFF_MULTIPLIER = 2       # exponential factor per subsequent retry
_BACKOFF_JITTER = 2.0         # max random jitter added to each delay (seconds)
_MAX_RATE_LIMIT_RETRIES = 2   # extra retries on 429 (3 total attempts)

_UNKNOWN_PROVIDER = "unknown"
_DIAGNOSTIC_COUNTER_FIELDS = (
    "dispatch_count",
    "attempt_count",
    "cache_hits",
    "cache_misses",
    "retry_count",
    "rate_limit_retry_count",
    "error_count",
)
_DIAGNOSTIC_FLOAT_FIELDS = ("latency_total_seconds", "latency_max_seconds")


def _provider_diagnostics_defaults() -> dict[str, int | float]:
    """Return the bounded aggregate defaults for a single provider bucket."""
    return {
        "dispatch_count": 0,
        "attempt_count": 0,
        "cache_hits": 0,
        "cache_misses": 0,
        "retry_count": 0,
        "rate_limit_retry_count": 0,
        "error_count": 0,
        "latency_total_seconds": 0.0,
        "latency_max_seconds": 0.0,
    }


def _job_diagnostics_defaults() -> dict[str, Any]:
    """Return the bounded aggregate defaults for one enrichment job."""
    return {
        **_provider_diagnostics_defaults(),
        "providers": {},
    }


def _normalize_provider_name(raw_name: object) -> str:
    """Return a bounded provider bucket name, falling back to ``unknown``."""
    if not isinstance(raw_name, str):
        return _UNKNOWN_PROVIDER
    provider_name = raw_name.strip()
    if not provider_name:
        return _UNKNOWN_PROVIDER
    return provider_name[:64]


def _coerce_provider_diagnostics(raw: object) -> dict[str, int | float]:
    """Return a safe provider diagnostics snapshot even if state is malformed."""
    data = raw if isinstance(raw, dict) else {}
    diagnostics = _provider_diagnostics_defaults()

    for field in _DIAGNOSTIC_COUNTER_FIELDS:
        value = data.get(field)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            diagnostics[field] = value

    for field in _DIAGNOSTIC_FLOAT_FIELDS:
        value = data.get(field)
        if isinstance(value, (int, float)) and value >= 0:
            diagnostics[field] = float(value)

    return diagnostics


def _merge_provider_diagnostics(
    target: dict[str, int | float], source: dict[str, int | float]
) -> None:
    """Merge *source* into *target* without dropping bounded aggregate fields."""
    for field in _DIAGNOSTIC_COUNTER_FIELDS:
        target[field] += int(source[field])
    target["latency_total_seconds"] += float(source["latency_total_seconds"])
    target["latency_max_seconds"] = max(
        float(target["latency_max_seconds"]),
        float(source["latency_max_seconds"]),
    )


def _coerce_job_diagnostics(raw: object) -> dict[str, Any]:
    """Return a safe job diagnostics snapshot even if state is malformed."""
    data = raw if isinstance(raw, dict) else {}
    diagnostics = _provider_diagnostics_defaults() | {"providers": {}}

    for field in _DIAGNOSTIC_COUNTER_FIELDS:
        value = data.get(field)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            diagnostics[field] = value

    for field in _DIAGNOSTIC_FLOAT_FIELDS:
        value = data.get(field)
        if isinstance(value, (int, float)) and value >= 0:
            diagnostics[field] = float(value)

    raw_providers = data.get("providers")
    if isinstance(raw_providers, dict):
        providers: dict[str, dict[str, int | float]] = {}
        for raw_name, raw_provider in raw_providers.items():
            provider_name = _normalize_provider_name(raw_name)
            provider_snapshot = _coerce_provider_diagnostics(raw_provider)
            if provider_name not in providers:
                providers[provider_name] = provider_snapshot
            else:
                _merge_provider_diagnostics(providers[provider_name], provider_snapshot)
        diagnostics["providers"] = providers

    return diagnostics


class EnrichmentOrchestrator:
    """Orchestrates parallel IOC enrichment using ThreadPoolExecutor.

    Dispatches all enrichable IOCs concurrently to all matching adapters,
    retries each failure once, and records per-job progress in a thread-safe,
    LRU-bounded dict.

    Each adapter must expose:
      - supported_types: set[IOCType] — types handled by this adapter
      - lookup(ioc): IOC -> EnrichmentResult | EnrichmentError
      - requires_api_key: bool — True if the provider needs an API key

    Per-provider semaphores cap rate-limited providers independently of zero-auth
    providers, ensuring VT rate limits do not starve Shodan, DNS, ip-api, etc.

    Args:
        adapters:             List of adapter objects. Each IOC is dispatched to every
                              adapter whose supported_types includes the IOC's type.
        max_workers:          Maximum number of concurrent worker threads. Default 20 so
                              the thread pool is not the bottleneck; semaphores are the
                              real concurrency gate for rate-limited providers.
        max_jobs:             Maximum number of job status entries to retain. Oldest entries
                              are evicted via FIFO (OrderedDict) when limit is exceeded.
        provider_concurrency: Optional per-provider concurrency override dict, keyed by
                              adapter name. For any requires_api_key=True adapter not in
                              this dict, the default cap of 4 is used. Zero-auth adapters
                              are always uncapped regardless of this dict.
    """

    def __init__(
        self,
        adapters: list[Any],
        max_workers: int = 20,
        max_jobs: int = 100,
        cache: CacheStore | None = None,
        cache_ttl_seconds: int = 86400,
        provider_concurrency: dict[str, int] | None = None,
    ) -> None:
        self._adapters = adapters
        self._max_workers = max_workers
        self._max_jobs = max_jobs
        self._jobs: OrderedDict[str, dict] = OrderedDict()
        self._terminal_jobs: OrderedDict[str, dict] = OrderedDict()
        self._lock = Lock()
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cached_markers: dict[str, str] = {}

        # Build per-provider semaphores for adapters that require an API key.
        # Zero-auth adapters get no semaphore (unrestricted concurrency).
        concurrency = provider_concurrency or {}
        self._semaphores: dict[str, Semaphore] = {}
        for adapter in adapters:
            raw_name = getattr(adapter, "name", "")
            provider_name = _normalize_provider_name(raw_name)
            if getattr(adapter, "requires_api_key", False):
                limit = concurrency.get(raw_name, concurrency.get(provider_name, 4))
                self._semaphores[provider_name] = Semaphore(limit)

    def enrich_all(self, job_id: str, iocs: list[IOC]) -> None:
        """Enrich all enrichable IOCs in parallel across all matching adapters.

        For each IOC, dispatches to every adapter whose supported_types includes
        the IOC's type. Runs all lookups concurrently via ThreadPoolExecutor.
        Each failed lookup (EnrichmentError result) is retried exactly once
        before being recorded.

        total reflects the number of dispatched lookups (IOC count x matching
        adapters), not just the IOC count.

        Thread safety: all mutations to the job status dict are protected by _lock.

        Args:
            job_id: Unique identifier for this enrichment job.
            iocs:   List of IOCs to enrich. Unsupported types are silently skipped.
        """
        # Build (adapter, ioc) pairs: each IOC dispatched to every matching adapter
        dispatch_pairs = [
            (adapter, ioc)
            for ioc in iocs
            for adapter in self._adapters
            if ioc.type in adapter.supported_types
        ]
        diagnostics = self._build_dispatch_diagnostics(dispatch_pairs)

        with self._lock:
            self._jobs[job_id] = {
                "total": len(dispatch_pairs),
                "done": 0,
                "results": [],
                "complete": False,
                "status": "running",
                "terminal": False,
                "terminal_reason": None,
                "error": None,
                "_diagnostics": diagnostics,
            }
            self._terminal_jobs.pop(job_id, None)
            self._evict_if_needed()

        try:
            with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
                futures = {
                    pool.submit(self._do_lookup, job_id, adapter, ioc): (adapter, ioc)
                    for adapter, ioc in dispatch_pairs
                }
                for future in as_completed(futures):
                    result = future.result()
                    with self._lock:
                        self._jobs[job_id]["results"].append(result)
                        self._jobs[job_id]["done"] += 1
        except Exception as exc:
            logger.exception("Enrichment job %s failed", job_id)
            with self._lock:
                self._jobs[job_id]["complete"] = True
                self._jobs[job_id]["status"] = "failed"
                self._jobs[job_id]["terminal"] = True
                self._jobs[job_id]["terminal_reason"] = "job_failed"
                self._jobs[job_id]["error"] = str(exc) or exc.__class__.__name__
            return

        with self._lock:
            self._jobs[job_id]["complete"] = True
            self._jobs[job_id]["status"] = "complete"

    def get_status(self, job_id: str) -> dict | None:
        """Return a snapshot of the job status dict, or None if not found.

        Returns a copy with a snapshot of the results list to prevent callers
        from seeing concurrent mutations (RuntimeError: list changed size during
        iteration) or from mutating internal state.

        Args:
            job_id: The job identifier returned by enrich_all.

        Returns:
            Copy of status dict with keys: total, done, results, complete,
            status, terminal, terminal_reason, error.
            The results value is a new list (snapshot), not the live reference.
            Terminal tombstones are returned for evicted jobs.
            None if job_id is not found (never created).
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                terminal = self._terminal_jobs.get(job_id)
                if terminal is None:
                    return None
                return self._status_snapshot(terminal)
            return self._status_snapshot(job)

    def get_diagnostics(self, job_id: str) -> dict[str, Any] | None:
        """Return a safe snapshot of bounded per-job runtime/provider diagnostics."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                raw = job.get("_diagnostics")
            else:
                terminal = self._terminal_jobs.get(job_id)
                if terminal is None:
                    return None
                raw = terminal.get("_diagnostics")
        return _coerce_job_diagnostics(raw)

    @property
    def cached_markers(self) -> dict[str, str]:
        """Return copy of cached result markers (ioc_value|provider -> cached_at).

        Protected by _lock to prevent returning a partially-written snapshot when
        worker threads are simultaneously updating _cached_markers.
        """
        with self._lock:
            return dict(self._cached_markers)

    def _status_snapshot(self, job: dict[str, Any]) -> dict[str, Any]:
        """Return a safe status snapshot without exposing internal diagnostics state."""
        snapshot = {
            key: value
            for key, value in job.items()
            if key != "_diagnostics"
        }
        snapshot["results"] = list(job.get("results", []))
        return snapshot

    def _build_dispatch_diagnostics(
        self, dispatch_pairs: list[tuple[Any, IOC]]
    ) -> dict[str, Any]:
        """Create the initial bounded diagnostics snapshot for a job."""
        diagnostics = _job_diagnostics_defaults()
        for adapter, _ioc in dispatch_pairs:
            provider_name = _normalize_provider_name(getattr(adapter, "name", ""))
            provider = diagnostics["providers"].setdefault(
                provider_name,
                _provider_diagnostics_defaults(),
            )
            diagnostics["dispatch_count"] += 1
            provider["dispatch_count"] += 1
        return diagnostics

    def _record_cache(self, job_id: str, provider_name: str, *, hit: bool) -> None:
        """Record a cache hit or miss without letting diagnostics failures escape."""
        self._update_job_diagnostics(
            job_id,
            provider_name,
            lambda diagnostics, provider: self._apply_cache_update(
                diagnostics,
                provider,
                hit=hit,
            ),
        )

    def _apply_cache_update(
        self,
        diagnostics: dict[str, Any],
        provider: dict[str, int | float],
        *,
        hit: bool,
    ) -> None:
        field = "cache_hits" if hit else "cache_misses"
        diagnostics[field] += 1
        provider[field] += 1

    def _record_retry(self, job_id: str, provider_name: str, *, rate_limit: bool) -> None:
        """Record an extra lookup attempt triggered by retry logic."""
        def apply(diagnostics: dict[str, Any], provider: dict[str, int | float]) -> None:
            diagnostics["retry_count"] += 1
            provider["retry_count"] += 1
            if rate_limit:
                diagnostics["rate_limit_retry_count"] += 1
                provider["rate_limit_retry_count"] += 1

        self._update_job_diagnostics(job_id, provider_name, apply)

    def _record_latency(self, job_id: str, provider_name: str, latency_seconds: float) -> None:
        """Record bounded latency aggregates for one lookup attempt."""
        safe_latency = max(float(latency_seconds), 0.0)

        def apply(diagnostics: dict[str, Any], provider: dict[str, int | float]) -> None:
            diagnostics["attempt_count"] += 1
            diagnostics["latency_total_seconds"] += safe_latency
            diagnostics["latency_max_seconds"] = max(
                float(diagnostics["latency_max_seconds"]),
                safe_latency,
            )
            provider["attempt_count"] += 1
            provider["latency_total_seconds"] += safe_latency
            provider["latency_max_seconds"] = max(
                float(provider["latency_max_seconds"]),
                safe_latency,
            )

        self._update_job_diagnostics(job_id, provider_name, apply)

    def _record_error(self, job_id: str, provider_name: str) -> None:
        """Record a provider-scoped error tally without mutating adapters."""
        def apply(diagnostics: dict[str, Any], provider: dict[str, int | float]) -> None:
            diagnostics["error_count"] += 1
            provider["error_count"] += 1

        self._update_job_diagnostics(job_id, provider_name, apply)

    def _update_job_diagnostics(
        self,
        job_id: str,
        provider_name: str,
        update: Any,
    ) -> None:
        """Apply a bounded diagnostics update under the job lock.

        The update path is intentionally defensive: malformed internal state is
        coerced back to a safe aggregate snapshot and diagnostics failures never
        change enrichment control flow.
        """
        try:
            with self._lock:
                job = self._jobs.get(job_id)
                if job is None:
                    return

                diagnostics = job.get("_diagnostics")
                if not isinstance(diagnostics, dict):
                    diagnostics = _job_diagnostics_defaults()
                    job["_diagnostics"] = diagnostics

                providers = diagnostics.get("providers")
                if not isinstance(providers, dict):
                    diagnostics = _coerce_job_diagnostics(diagnostics)
                    job["_diagnostics"] = diagnostics
                    providers = diagnostics["providers"]

                provider_bucket = _normalize_provider_name(provider_name)
                provider = providers.get(provider_bucket)
                if not isinstance(provider, dict):
                    provider = _provider_diagnostics_defaults()
                    providers[provider_bucket] = provider

                update(diagnostics, provider)
        except Exception:  # pragma: no cover - defensive metrics path
            logger.debug(
                "Failed to update diagnostics for enrichment job %s",
                job_id,
                exc_info=True,
            )

    def _do_lookup(
        self,
        job_id: str,
        adapter: Any,
        ioc: IOC,
    ) -> EnrichmentResult | EnrichmentError:
        """Look up a single IOC via a specific adapter, with per-provider semaphore gating.

        The semaphore wraps each *individual attempt* (cache-check + adapter.lookup() +
        cache-store) but is released before any backoff sleep between retries.  This
        prevents a batch of concurrent 429s from holding all semaphore slots while
        sleeping, which would starve every other queued IOC.

        Control flow:
          1. Acquire semaphore → _single_attempt() → release semaphore.
          2a. On 429 error:     sleep (outside sem) → loop back to 1.
          2b. On non-429 error: sleep 1s (outside sem) → loop back to 1 (once).
          3. On success or retry exhaustion: return result.

        try/finally guarantees semaphore release even when _single_attempt raises.

        Args:
            job_id:  The enrichment job identifier.
            adapter: The adapter to use for this lookup.
            ioc:     The IOC to enrich.

        Returns:
            EnrichmentResult on success (first or retry attempt).
            EnrichmentError if all attempts fail.
        """
        provider_name = _normalize_provider_name(getattr(adapter, "name", ""))
        sem = self._semaphores.get(provider_name)

        # --- First attempt (under semaphore) ---
        if sem is not None:
            sem.acquire()
        try:
            result = self._single_attempt(job_id, adapter, ioc, provider_name)
        finally:
            if sem is not None:
                sem.release()

        if not isinstance(result, EnrichmentError):
            return result

        if self._is_rate_limit_error(result):
            # 429: exponential backoff with jitter, up to _MAX_RATE_LIMIT_RETRIES
            for attempt in range(1, _MAX_RATE_LIMIT_RETRIES + 1):
                self._record_retry(job_id, provider_name, rate_limit=True)
                delay = (
                    _BACKOFF_BASE * (_BACKOFF_MULTIPLIER ** (attempt - 1))
                    + random.uniform(0, _BACKOFF_JITTER)  # noqa: S311
                )
                logger.warning(
                    "Rate limit (429) from %s for %s — backoff attempt %d, sleeping %.1fs",
                    provider_name,
                    ioc.value,
                    attempt,
                    delay,
                )
                # Sleep OUTSIDE semaphore — other threads can make progress
                time.sleep(delay)

                if sem is not None:
                    sem.acquire()
                try:
                    result = self._single_attempt(job_id, adapter, ioc, provider_name)
                finally:
                    if sem is not None:
                        sem.release()

                if not isinstance(result, EnrichmentError):
                    return result
                if not self._is_rate_limit_error(result):
                    break  # different error on retry — stop 429-backoff loop
        else:
            # Non-429 error: single retry after 1s delay (outside semaphore)
            self._record_retry(job_id, provider_name, rate_limit=False)
            time.sleep(1)

            if sem is not None:
                sem.acquire()
            try:
                result = self._single_attempt(job_id, adapter, ioc, provider_name)
            finally:
                if sem is not None:
                    sem.release()

        return result

    def _single_attempt(
        self,
        job_id: str,
        adapter: Any,
        ioc: IOC,
        provider_name: str,
    ) -> EnrichmentResult | EnrichmentError:
        """Execute one cache-check + adapter.lookup() + cache-store attempt.

        Must be called with the provider semaphore already acquired (if applicable).
        Contains no retry or backoff logic — that lives in _do_lookup().

        Cache hit path: reads from cache, records marker under _lock, returns cached result.
        Cache miss path: calls adapter.lookup(), stores success in cache, returns result.

        Args:
            job_id:        The enrichment job identifier.
            adapter:       The adapter to use for this lookup.
            ioc:           The IOC to enrich.
            provider_name: Pre-resolved adapter name (avoids repeated getattr).

        Returns:
            EnrichmentResult on success (cache hit or successful lookup).
            EnrichmentError if adapter.lookup() returns one.
        """
        started = time.perf_counter()
        try:
            # Check cache
            if self._cache is not None and provider_name:
                cached = self._cache.get(
                    ioc.value,
                    ioc.type.value,
                    provider_name,
                    self._cache_ttl_seconds,
                )
                if cached is not None:
                    self._record_cache(job_id, provider_name, hit=True)
                    cached_at = cached.pop("cached_at", "")
                    cache_key = ioc.value + "|" + provider_name
                    with self._lock:
                        self._cached_markers[cache_key] = cached_at
                    return EnrichmentResult(
                        ioc=ioc,
                        provider=cached["provider"],
                        verdict=cached["verdict"],
                        detection_count=cached["detection_count"],
                        total_engines=cached["total_engines"],
                        scan_date=cached.get("scan_date"),
                        raw_stats=cached.get("raw_stats", {}),
                    )
                self._record_cache(job_id, provider_name, hit=False)

            try:
                result = adapter.lookup(ioc)
            except Exception:
                self._record_error(job_id, provider_name)
                raise

            # Store successful results in cache
            if (
                self._cache is not None
                and provider_name
                and isinstance(result, EnrichmentResult)
            ):
                self._cache.put(
                    ioc.value,
                    ioc.type.value,
                    provider_name,
                    {
                        "provider": result.provider,
                        "verdict": result.verdict,
                        "detection_count": result.detection_count,
                        "total_engines": result.total_engines,
                        "scan_date": result.scan_date,
                        "raw_stats": result.raw_stats,
                    },
                )

            if isinstance(result, EnrichmentError):
                self._record_error(job_id, provider_name)
            return result
        finally:
            self._record_latency(job_id, provider_name, time.perf_counter() - started)

    def _is_rate_limit_error(self, result: Any) -> bool:
        """Return True if *result* is a rate-limit (429) EnrichmentError.

        Matches both numeric "429" and the string "rate limit" (case-insensitive)
        so it handles all real-adapter error message variants:
          - "Rate limit exceeded (429)"  — VirusTotal, AbuseIPDB
          - "HTTP 429"                   — GreyNoise, ip-api, Shodan, ThreatMiner
          - "Rate limit exceeded"        — any adapter not including the status code
        """
        if not isinstance(result, EnrichmentError):
            return False
        err = result.error.lower()
        return "429" in err or "rate limit" in err

    def _evict_if_needed(self) -> None:
        """Evict the oldest job entry when the LRU limit is exceeded.

        Must be called with self._lock held.
        Evicts one entry per call (FIFO via OrderedDict ordering) and leaves a
        terminal tombstone so pollers can distinguish eviction from an unknown id.
        """
        while len(self._jobs) > self._max_jobs:
            evicted_job_id, evicted_job = self._jobs.popitem(last=False)
            self._terminal_jobs[evicted_job_id] = {
                "total": evicted_job["total"],
                "done": evicted_job["done"],
                "results": [],
                "complete": True,
                "status": "failed",
                "terminal": True,
                "terminal_reason": "evicted",
                "error": "Enrichment job status was evicted from memory.",
                "_diagnostics": _coerce_job_diagnostics(evicted_job.get("_diagnostics")),
            }
            while len(self._terminal_jobs) > self._max_jobs:
                self._terminal_jobs.popitem(last=False)
