"""Enrichment orchestrator.

Runs IOC lookups in parallel via ThreadPoolExecutor, tracks job progress in a
thread-safe dict, retries failed lookups once, and evicts old jobs via LRU.

Design decisions:
- max_workers=4 default: respects VT free tier 4 req/min (Pitfall 7 from research)
- OrderedDict for LRU eviction: simple FIFO eviction without external libraries
- Lock protects all reads/writes to _jobs dict (thread safety)
- enrich_all is designed to be called from a threading.Thread (Plan 03)
- Fresh requests.Session is the adapter's responsibility (Pitfall 3)
- Phase 3: accepts a list of adapters, each declaring its own supported_types set
"""
from __future__ import annotations

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Any

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

    Args:
        adapters:    List of adapter objects. Each IOC is dispatched to every
                     adapter whose supported_types includes the IOC's type.
        max_workers: Maximum number of concurrent worker threads. Default 4 respects
                     VirusTotal free tier rate limit of 4 requests/minute.
        max_jobs:    Maximum number of job status entries to retain. Oldest entries
                     are evicted via FIFO (OrderedDict) when limit is exceeded.
    """

    def __init__(self, adapters: list[Any], max_workers: int = 4, max_jobs: int = 100) -> None:
        self._adapters = adapters
        self._max_workers = max_workers
        self._max_jobs = max_jobs
        self._jobs: OrderedDict[str, dict] = OrderedDict()
        self._lock = Lock()

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

    def _do_lookup(self, adapter: Any, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        """Look up a single IOC via a specific adapter, retrying once on EnrichmentError.

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
        result = adapter.lookup(ioc)
        if isinstance(result, EnrichmentError):
            result = adapter.lookup(ioc)
        return result

    def _evict_if_needed(self) -> None:
        """Evict the oldest job entry when the LRU limit is exceeded.

        Must be called with self._lock held.
        Evicts one entry per call (FIFO via OrderedDict ordering).
        """
        while len(self._jobs) > self._max_jobs:
            self._jobs.popitem(last=False)
