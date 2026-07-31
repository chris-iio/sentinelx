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
from functools import partial
from threading import Lock
from typing import Any

from app.cache.store import CacheStore
from .attempt_execution import run_single_attempt
from .diagnostics import (
    _coerce_job_diagnostics,
    _normalize_provider_name,
    apply_cache_update,
    apply_error_update,
    apply_latency_update,
    apply_retry_update,
    build_dispatch_diagnostics,
)
from .diagnostic_state import apply_job_diagnostics_update
from .dispatch_plan import build_dispatch_pairs, build_provider_semaphores
from .job_execution import run_dispatch_pairs
from .lookup_execution import run_lookup_with_retries
from .job_state import (
    cached_markers_snapshot,
    mark_live_job_failed,
    mark_live_job_finished,
    mark_live_job_running,
    register_live_job,
    record_cached_marker,
    record_live_lookup_result,
    resolved_job_record,
)
from .models import EnrichmentError, EnrichmentResult
from . import retry_policy
from .status_snapshots import (
    incremental_status_snapshot,
    status_snapshot,
)
from app.pipeline.models import IOC

logger = logging.getLogger(__name__)

_BACKOFF_BASE = retry_policy.BACKOFF_BASE
_BACKOFF_JITTER = retry_policy.BACKOFF_JITTER
_BACKOFF_MULTIPLIER = retry_policy.BACKOFF_MULTIPLIER
_MAX_RATE_LIMIT_RETRIES = retry_policy.MAX_RATE_LIMIT_RETRIES

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

        self._semaphores = build_provider_semaphores(adapters, provider_concurrency)

    def register_queued_job(self, job_id: str, iocs: list[IOC]) -> None:
        """Register a pollable queued job before executor submission."""
        dispatch_pairs = build_dispatch_pairs(self._adapters, iocs)
        diagnostics = build_dispatch_diagnostics(dispatch_pairs)
        with self._lock:
            register_live_job(
                self._jobs,
                self._terminal_jobs,
                job_id,
                total=len(dispatch_pairs),
                diagnostics=diagnostics,
                max_jobs=self._max_jobs,
            )

    def fail_job(
        self,
        job_id: str,
        exc: BaseException,
        *,
        reason: str = "job_failed",
    ) -> None:
        """Fail a queued or running job while preserving recorded results."""
        with self._lock:
            mark_live_job_failed(self._jobs, job_id, exc, reason=reason)

    def enrich_all(self, job_id: str, iocs: list[IOC]) -> None:
        """Run all matching provider/IOC lookups for one queued job."""
        dispatch_pairs = build_dispatch_pairs(self._adapters, iocs)

        with self._lock:
            if job_id not in self._jobs:
                diagnostics = build_dispatch_diagnostics(dispatch_pairs)
                register_live_job(
                    self._jobs,
                    self._terminal_jobs,
                    job_id,
                    total=len(dispatch_pairs),
                    diagnostics=diagnostics,
                    max_jobs=self._max_jobs,
                )
            mark_live_job_running(self._jobs, job_id)

        try:
            if dispatch_pairs:
                run_dispatch_pairs(
                    job_id,
                    dispatch_pairs,
                    max_workers=self._max_workers,
                    lookup=self._do_lookup,
                    record_result=self._record_lookup_result,
                )
        except Exception as exc:
            logger.exception("Enrichment job %s failed", job_id)
            self.fail_job(job_id, exc)
            return

        with self._lock:
            mark_live_job_finished(self._jobs, job_id)

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
            job = resolved_job_record(self._jobs, self._terminal_jobs, job_id)
            if job is None:
                return None
            return status_snapshot(job)

    def get_incremental_status(self, job_id: str, since: int = 0) -> dict[str, Any] | None:
        """Return a lock-safe status snapshot containing only the requested tail.

        The returned payload preserves the scalar job fields from ``get_status()``
        but copies only ``results[since:]`` plus the cached markers needed to
        serialize that tail. ``next_since`` is computed from the retained result
        length so callers do not need to reconstruct cursor state from a full
        snapshot. Terminal tombstones preserve the existing safe cursor fallback.
        """
        with self._lock:
            job = resolved_job_record(self._jobs, self._terminal_jobs, job_id)
            if job is None:
                return None
            return incremental_status_snapshot(job, since, self._cached_markers)

    def get_diagnostics(self, job_id: str) -> dict[str, Any] | None:
        """Return a safe snapshot of bounded per-job runtime/provider diagnostics."""
        with self._lock:
            job = resolved_job_record(self._jobs, self._terminal_jobs, job_id)
            if job is None:
                return None
            raw = job.get("_diagnostics")
        return _coerce_job_diagnostics(raw)

    @property
    def cached_markers(self) -> dict[str, str]:
        """Return copy of cached result markers (ioc_value|provider -> cached_at).

        Protected by _lock to prevent returning a partially-written snapshot when
        worker threads are simultaneously updating _cached_markers.
        """
        with self._lock:
            return cached_markers_snapshot(self._cached_markers)

    def _record_lookup_result(
        self,
        job_id: str,
        result: EnrichmentResult | EnrichmentError,
    ) -> None:
        """Record one completed lookup result under the job lock."""
        with self._lock:
            record_live_lookup_result(self._jobs, job_id, result)

    def _record_cache(self, job_id: str, provider_name: str, hit: bool) -> None:
        """Record a cache hit or miss without letting diagnostics failures escape."""
        self._update_job_diagnostics(
            job_id,
            provider_name,
            apply_cache_update,
            hit=hit,
        )

    def _record_retry(self, job_id: str, provider_name: str, rate_limit: bool) -> None:
        """Record an extra lookup attempt triggered by retry logic."""
        self._update_job_diagnostics(
            job_id,
            provider_name,
            apply_retry_update,
            rate_limit=rate_limit,
        )

    def _record_latency(self, job_id: str, provider_name: str, latency_seconds: float) -> None:
        """Record bounded latency aggregates for one lookup attempt."""
        self._update_job_diagnostics(
            job_id,
            provider_name,
            apply_latency_update,
            latency_seconds=latency_seconds,
        )

    def _record_error(self, job_id: str, provider_name: str) -> None:
        """Record a provider-scoped error tally without mutating adapters."""
        self._update_job_diagnostics(job_id, provider_name, apply_error_update)

    def _record_cached_marker(self, cache_key: str, cached_at: str) -> None:
        """Record a cache-hit marker under the orchestrator lock."""
        with self._lock:
            record_cached_marker(self._cached_markers, cache_key, cached_at)

    def _update_job_diagnostics(
        self,
        job_id: str,
        provider_name: str,
        update: Any,
        **update_kwargs: Any,
    ) -> None:
        """Apply a bounded diagnostics update under the job lock.

        The update path is intentionally defensive: malformed internal state is
        coerced back to a safe aggregate snapshot and diagnostics failures never
        change enrichment control flow.
        """
        try:
            with self._lock:
                apply_job_diagnostics_update(
                    self._jobs,
                    job_id,
                    provider_name,
                    update,
                    **update_kwargs,
                )
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

        The semaphore wraps each *individual attempt* (cache-check + provider lookup +
        cache-store) but is released before any backoff sleep between retries.  This
        prevents a batch of concurrent 429s from holding all semaphore slots while
        sleeping, which would starve every other queued IOC.

        Control flow:
          1. Acquire semaphore -> single attempt -> release semaphore.
          2a. On 429 error:     sleep (outside sem) → loop back to 1.
          2b. On non-429 error: sleep 1s (outside sem) → loop back to 1 (once).
          3. On success or retry exhaustion: return result.

        try/finally guarantees semaphore release even when an attempt raises.

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
        attempt = partial(
            run_single_attempt,
            cache=self._cache,
            cache_ttl_seconds=self._cache_ttl_seconds,
            record_cache=self._record_cache,
            record_error=self._record_error,
            record_latency=self._record_latency,
            record_cached_marker=self._record_cached_marker,
        )

        return run_lookup_with_retries(
            job_id,
            adapter,
            ioc,
            provider_name=provider_name,
            semaphore=sem,
            attempt=attempt,
            record_retry=self._record_retry,
            sleep=time.sleep,
            random_uniform=random.uniform,  # noqa: S311
            logger=logger,
        )
