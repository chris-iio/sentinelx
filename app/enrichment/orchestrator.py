"""Enrichment orchestrator.

Runs IOC lookups in parallel via ThreadPoolExecutor, tracks job progress in a
thread-safe dict, retries failed lookups once, and evicts old jobs via LRU.

Design decisions:
- max_workers=20 default: thread pool is no longer the concurrency gate; per-provider
  semaphores cap rate-limited providers (e.g. VT at 4) while zero-auth providers run freely.
- _semaphores dict: keyed by adapter name; built for adapters with requires_api_key=True;
  each semaphore limits peak concurrent lookups for that provider (default cap: 4).
- Zero-auth adapters (requires_api_key=False) have no semaphore — unlimited concurrency.
- Semaphore wraps entire lookup+retry cycle in _do_lookup (not per-attempt) to avoid
  re-entrant deadlock.
- OrderedDict for LRU eviction: simple FIFO eviction without external libraries
- Lock protects all reads/writes to _jobs dict (thread safety)
- enrich_all is designed to be called from a threading.Thread (Plan 03)
- Fresh requests.Session is the adapter's responsibility (Pitfall 3)
- Phase 3: accepts a list of adapters, each declaring its own supported_types set
"""
from __future__ import annotations

import logging
import random
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, Semaphore
from typing import Any

logger = logging.getLogger(__name__)

# 429 / rate-limit backoff parameters
_BACKOFF_BASE = 15            # seconds for first retry delay
_BACKOFF_MULTIPLIER = 2       # exponential factor per subsequent retry
_BACKOFF_JITTER = 2.0         # max random jitter added to each delay (seconds)
_MAX_RATE_LIMIT_RETRIES = 2   # extra retries on 429 (3 total attempts)

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
      - requires_api_key: bool — True if the provider needs an API key

    Per-provider semaphores cap rate-limited providers independently of zero-auth
    providers, ensuring VT rate limits do not starve Shodan, DNS, ip-api, etc.

    The thread pool (max_workers=20 default) is intentionally large so that
    zero-auth providers are never blocked by rate-limited providers.
    Per-provider semaphores (built from requires_api_key=True adapters) are
    the real concurrency gate — they cap API-key providers at 4 by default.

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
        self._lock = Lock()
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cached_markers: dict[str, str] = {}

        # Build per-provider semaphores for adapters that require an API key.
        # Zero-auth adapters get no semaphore (unrestricted concurrency).
        concurrency = provider_concurrency or {}
        self._semaphores: dict[str, Semaphore] = {}
        for adapter in adapters:
            name = getattr(adapter, "name", "")
            if getattr(adapter, "requires_api_key", False) and name:
                limit = concurrency.get(name, 4)  # default cap: 4 for key-required providers
                self._semaphores[name] = Semaphore(limit)

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
        """Look up a single IOC via a specific adapter, with per-provider semaphore gating.

        Acquires the provider's semaphore (if one exists) before entering the lookup+retry
        cycle, holding it for the full duration. This ensures requires_api_key providers
        never exceed their configured concurrency cap while zero-auth providers run freely.

        The semaphore wraps the *entire* cache-check + lookup + retry cycle (not per-attempt)
        to avoid re-entrant deadlock on single-threaded semaphore exhaustion.

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
                return self._do_lookup_inner(adapter, ioc, provider_name)
        return self._do_lookup_inner(adapter, ioc, provider_name)

    def _do_lookup_inner(
        self, adapter: Any, ioc: IOC, provider_name: str
    ) -> EnrichmentResult | EnrichmentError:
        """Execute the actual cache-check, lookup, retry, and cache-store cycle.

        Called by _do_lookup, optionally under a provider semaphore. Separated to
        keep semaphore acquisition and lookup logic distinct.

        Checks cache before calling adapter. Stores successful results in cache.
        Retries exactly once on EnrichmentError; returns second result regardless.

        Args:
            adapter:       The adapter to use for this lookup.
            ioc:           The IOC to enrich.
            provider_name: Pre-resolved adapter name (avoids repeated getattr).

        Returns:
            EnrichmentResult on success (first or retry attempt).
            EnrichmentError if both attempts fail.
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
                # 429: exponential backoff with jitter, up to _MAX_RATE_LIMIT_RETRIES
                for attempt in range(1, _MAX_RATE_LIMIT_RETRIES + 1):
                    delay = (
                        _BACKOFF_BASE * (_BACKOFF_MULTIPLIER ** (attempt - 1))
                        + random.uniform(0, _BACKOFF_JITTER)
                    )
                    logger.warning(
                        "Rate limit (429) from %s for %s — backoff attempt %d, sleeping %.1fs",
                        provider_name,
                        ioc.value,
                        attempt,
                        delay,
                    )
                    time.sleep(delay)
                    result = adapter.lookup(ioc)
                    if not isinstance(result, EnrichmentError):
                        break
                    if not self._is_rate_limit_error(result):
                        break  # different error on retry — stop 429-backoff loop
            else:
                # Non-429 error: single immediate retry (existing behavior)
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
