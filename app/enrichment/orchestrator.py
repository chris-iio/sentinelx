"""Enrichment orchestrator.

Runs IOC lookups in parallel via ThreadPoolExecutor, tracks job progress in a
thread-safe dict, retries failed lookups once, and evicts old jobs via LRU.

Design decisions:
- max_workers=20 default: thread pool is intentionally generous so zero-auth
  providers can always run in parallel; per-provider semaphores are the real
  concurrency gate (R014).
- _semaphores dict: adapters with requires_api_key=True get a Semaphore (default
  cap 4, overridable via provider_concurrency). Zero-auth adapters run ungated.
- OrderedDict for LRU eviction: simple FIFO eviction without external libraries
- Lock protects all reads/writes to _jobs dict (thread safety)
- enrich_all is designed to be called from a threading.Thread (Plan 03)
- Fresh requests.Session is the adapter's responsibility (Pitfall 3)
- Phase 3: accepts a list of adapters, each declaring its own supported_types set
"""
from __future__ import annotations

import logging
import random
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

from app.cache.store import CacheStore
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC


class EnrichmentOrchestrator:
    """Orchestrates parallel IOC enrichment using ThreadPoolExecutor.

    Dispatches all enrichable IOCs concurrently to all matching adapters,
    retries each failure once, and records per-job progress in a thread-safe,
    LRU-bounded dict.

    Each adapter must expose:
      - supported_types: set[IOCType] — types handled by this adapter
      - lookup(ioc): IOC -> EnrichmentResult | EnrichmentError

    The thread pool (max_workers=20 default) is intentionally large so that
    zero-auth providers are never blocked by rate-limited providers.
    Per-provider semaphores (built from requires_api_key=True adapters) are
    the real concurrency gate — they cap API-key providers at 4 by default.

    Args:
        adapters:             List of adapter objects. Each IOC is dispatched to
                              every adapter whose supported_types includes the IOC's
                              type.
        max_workers:          Thread pool size. Intentionally generous (default 20)
                              so zero-auth providers always have threads available.
                              The semaphore, not the pool, caps rate-limited providers.
        max_jobs:             Maximum number of job status entries to retain. Oldest
                              entries are evicted via FIFO (OrderedDict) when exceeded.
        provider_concurrency: Optional per-provider-name override for the semaphore
                              cap. E.g. {"VirusTotal": 2} limits VT to 2 concurrent
                              calls. Only adapters with requires_api_key=True receive
                              a semaphore; this dict adjusts the cap value for them.
                              Defaults to {} (all API-key providers capped at 4).
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
        self._lock = Lock()
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cached_markers: dict[str, str] = {}

        # Build per-provider semaphores for API-key-required adapters.
        # Zero-auth adapters are intentionally excluded — they run ungated.
        _concurrency_overrides = provider_concurrency or {}
        self._semaphores: dict[str, threading.Semaphore] = {}
        for adapter in self._adapters:
            if getattr(adapter, "requires_api_key", False):
                name = adapter.name
                if name not in self._semaphores:
                    cap = _concurrency_overrides.get(name, 4)
                    self._semaphores[name] = threading.Semaphore(cap)

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

        with self._lock:
            self._jobs[job_id] = {
                "total": len(dispatch_pairs),
                "done": 0,
                "results": [],
                "complete": False,
            }
            self._evict_if_needed()

        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            futures = {
                pool.submit(self._do_lookup, adapter, ioc): (adapter, ioc)
                for adapter, ioc in dispatch_pairs
            }
            for future in as_completed(futures):
                result = future.result()
                with self._lock:
                    self._jobs[job_id]["results"].append(result)
                    self._jobs[job_id]["done"] += 1

        with self._lock:
            self._jobs[job_id]["complete"] = True

    def get_status(self, job_id: str) -> dict | None:
        """Return a shallow copy of the job status dict, or None if not found.

        Returns a shallow copy to prevent callers from mutating the internal state.

        Args:
            job_id: The job identifier returned by enrich_all.

        Returns:
            Shallow copy of status dict with keys: total, done, results, complete.
            None if job_id is not found (evicted or never created).
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return dict(job)

    @property
    def cached_markers(self) -> dict[str, str]:
        """Return copy of cached result markers (ioc_value|provider -> cached_at)."""
        return dict(self._cached_markers)

    @staticmethod
    def _is_rate_limit_error(result: EnrichmentError) -> bool:
        """Check if an EnrichmentError indicates a rate limit (429) response."""
        error_lower = result.error.lower()
        return "429" in error_lower or "rate limit" in error_lower

    def _do_lookup(self, adapter: Any, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        """Look up a single IOC via a specific adapter, retrying once on EnrichmentError.

        Checks cache before calling adapter. Stores successful results in cache.
        If the adapter has a semaphore (requires_api_key=True), the entire
        lookup+retry body is executed while holding that semaphore so that
        concurrent calls to the same rate-limited provider are capped.

        Calls adapter.lookup(ioc). If the result is an EnrichmentError,
        retries the lookup exactly once and returns the second result regardless
        of success or failure.

        Args:
            adapter: The adapter to use for this lookup.
            ioc:     The IOC to enrich.

        Returns:
            EnrichmentResult on success (first or retry attempt).
            EnrichmentError if both attempts fail.
        """
        provider_name = getattr(adapter, "name", "")
        sem = self._semaphores.get(provider_name)

        if sem is not None:
            with sem:
                return self._do_lookup_body(adapter, ioc, provider_name)
        else:
            return self._do_lookup_body(adapter, ioc, provider_name)

    def _do_lookup_body(self, adapter: Any, ioc: IOC, provider_name: str) -> EnrichmentResult | EnrichmentError:
        """Inner lookup+retry body, extracted so semaphore wrapping is clean.

        Called by _do_lookup either inside a semaphore context (for API-key
        providers) or directly (for zero-auth providers).

        Args:
            adapter:       The adapter to use.
            ioc:           The IOC to enrich.
            provider_name: Pre-resolved adapter name string.

        Returns:
            EnrichmentResult on success, EnrichmentError after two failures.
        """
        # Check cache
        if self._cache is not None and provider_name:
            cached = self._cache.get(
                ioc.value, ioc.type.value, provider_name, self._cache_ttl_seconds
            )
            if cached is not None:
                cached_at = cached.pop("cached_at", "")
                cache_key = ioc.value + "|" + provider_name
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

        result = adapter.lookup(ioc)
        if isinstance(result, EnrichmentError):
            if self._is_rate_limit_error(result):
                # Rate-limit (429): exponential backoff, up to 2 retries (3 total attempts).
                # The semaphore is intentionally held during backoff sleeps — a backing-off
                # request still occupies its concurrency slot.
                for attempt in range(1, 3):  # attempt 1 and 2
                    delay = (15 * (2 ** (attempt - 1))) + random.uniform(0, 2)
                    logger.warning(
                        "Rate limit from %s for %s, attempt %d/3, backoff %.1fs",
                        provider_name, ioc.value, attempt + 1, delay,
                    )
                    time.sleep(delay)
                    result = adapter.lookup(ioc)
                    if not isinstance(result, EnrichmentError) or not self._is_rate_limit_error(result):
                        break
            else:
                # Non-rate-limit error: immediate single retry (existing behavior).
                result = adapter.lookup(ioc)

        # Store successful results in cache
        if self._cache is not None and provider_name and isinstance(result, EnrichmentResult):
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

        return result

    def _evict_if_needed(self) -> None:
        """Evict the oldest job entry when the LRU limit is exceeded.

        Must be called with self._lock held.
        Evicts one entry per call (FIFO via OrderedDict ordering).
        """
        while len(self._jobs) > self._max_jobs:
            self._jobs.popitem(last=False)
