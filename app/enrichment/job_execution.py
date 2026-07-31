"""Bounded thread-pool execution for enrichment dispatch pairs."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from typing import Any

from .models import EnrichmentError, EnrichmentResult, error_result
from app.pipeline.models import IOC

LookupResult = EnrichmentResult | EnrichmentError
LookupFn = Callable[[str, Any, IOC], LookupResult]
RecordResultFn = Callable[[str, LookupResult], None]
DispatchPair = tuple[Any, IOC]


def _provider_name(adapter: Any) -> str:
    """Return a stable provider label for worker failures."""
    name = getattr(adapter, "name", None)
    if isinstance(name, str) and name.strip():
        return name.strip()
    return adapter.__class__.__name__


def _future_result(future: Future[LookupResult], dispatch_pair: DispatchPair) -> LookupResult:
    """Convert an unexpected worker exception into one provider-scoped outcome."""
    try:
        return future.result()
    except Exception as exc:
        adapter, ioc = dispatch_pair
        detail = str(exc) or exc.__class__.__name__
        return error_result(
            ioc,
            _provider_name(adapter),
            f"provider worker failed: {detail}",
        )


def run_dispatch_pairs(
    job_id: str,
    dispatch_pairs: list[DispatchPair],
    *,
    max_workers: int,
    lookup: LookupFn,
    record_result: RecordResultFn,
) -> None:
    """Run lookups while keeping at most ``max_workers`` futures outstanding."""
    if not dispatch_pairs:
        return

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        active: dict[Future[LookupResult], DispatchPair] = {}
        next_pair = 0

        while next_pair < len(dispatch_pairs) and len(active) < max_workers:
            pair = dispatch_pairs[next_pair]
            active[submit_dispatch_pair(pool, lookup, job_id, pair)] = pair
            next_pair += 1

        while active:
            completed, _ = wait(active, return_when=FIRST_COMPLETED)
            for future in completed:
                pair = active.pop(future)
                record_result(job_id, _future_result(future, pair))

            while next_pair < len(dispatch_pairs) and len(active) < max_workers:
                pair = dispatch_pairs[next_pair]
                active[submit_dispatch_pair(pool, lookup, job_id, pair)] = pair
                next_pair += 1


def submit_dispatch_pair(
    pool: ThreadPoolExecutor,
    lookup: LookupFn,
    job_id: str,
    dispatch_pair: DispatchPair,
) -> Future[LookupResult]:
    """Submit one provider/IOC lookup."""
    adapter, ioc = dispatch_pair
    return pool.submit(lookup, job_id, adapter, ioc)
