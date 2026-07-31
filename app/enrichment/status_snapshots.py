"""Lock-safe enrichment job status snapshot helpers."""

from __future__ import annotations

from itertools import islice
from typing import Any

from .cache_payloads import cache_marker_key
from .models import EnrichmentResult


def status_fields_snapshot(job: dict[str, Any]) -> dict[str, Any]:
    """Return scalar status fields without live results or diagnostics state."""
    return {
        "total": job.get("total", 0),
        "done": job.get("done", 0),
        "complete": job.get("complete", False),
        "status": job.get("status"),
        "terminal": job.get("terminal", False),
        "terminal_reason": job.get("terminal_reason"),
        "error": job.get("error"),
    }


def copy_results_tail(results: list[Any], start: int) -> list[Any]:
    """Copy retained results from *start* without slicing or constructor-copying."""
    result_count = len(results)
    if start >= result_count:
        return []
    if start == result_count - 1:
        return [results[start]]
    if start == result_count - 2:
        return [results[start], results[start + 1]]
    if start == result_count - 3:
        return [results[start], results[start + 1], results[start + 2]]
    if start == result_count - 4:
        return [results[start], results[start + 1], results[start + 2], results[start + 3]]

    copied_results: list[Any] = []
    for result in islice(results, start, None):
        append_result_tail_item(copied_results, result)
    return copied_results


def append_result_tail_item(copied_results: list[Any], result: Any) -> None:
    copied_results.append(result)


def status_snapshot(job: dict[str, Any]) -> dict[str, Any]:
    """Return a safe full status snapshot without diagnostics internals."""
    raw_results = job.get("results")
    results = raw_results if isinstance(raw_results, list) else []
    snapshot = status_fields_snapshot(job)
    snapshot["results"] = copy_results_tail(results, 0)
    return snapshot


def append_cached_marker_for_result(
    aligned_markers: dict[str, str],
    result: Any,
    cached_markers: dict[str, str],
) -> None:
    """Append a cached marker for one result when one is available."""
    if not isinstance(result, EnrichmentResult):
        return
    cache_key = cache_marker_key(result.ioc, result.provider)
    cached_at = cached_markers.get(cache_key)
    if cached_at:
        aligned_markers[cache_key] = cached_at


def aligned_cached_markers_snapshot(
    tail_results: list[Any],
    cached_markers: dict[str, str],
) -> dict[str, str]:
    """Return cached markers aligned to the already-copied result tail."""
    result_count = len(tail_results)
    aligned_markers: dict[str, str] = {}
    if result_count == 0:
        return aligned_markers
    if result_count == 1:
        append_cached_marker_for_result(aligned_markers, tail_results[0], cached_markers)
        return aligned_markers
    if result_count == 2:
        append_cached_marker_for_result(aligned_markers, tail_results[0], cached_markers)
        append_cached_marker_for_result(aligned_markers, tail_results[1], cached_markers)
        return aligned_markers
    if result_count == 3:
        append_cached_marker_for_result(aligned_markers, tail_results[0], cached_markers)
        append_cached_marker_for_result(aligned_markers, tail_results[1], cached_markers)
        append_cached_marker_for_result(aligned_markers, tail_results[2], cached_markers)
        return aligned_markers
    if result_count == 4:
        append_cached_marker_for_result(aligned_markers, tail_results[0], cached_markers)
        append_cached_marker_for_result(aligned_markers, tail_results[1], cached_markers)
        append_cached_marker_for_result(aligned_markers, tail_results[2], cached_markers)
        append_cached_marker_for_result(aligned_markers, tail_results[3], cached_markers)
        return aligned_markers

    for result in tail_results:
        append_cached_marker_for_result(aligned_markers, result, cached_markers)
    return aligned_markers


def incremental_status_snapshot(
    job: dict[str, Any],
    since: int,
    cached_markers: dict[str, str],
) -> dict[str, Any]:
    """Return a safe tail-only status snapshot plus aligned cached markers."""
    raw_results = job.get("results")
    results = raw_results if isinstance(raw_results, list) else []
    result_count = len(results)
    start = 0 if since < 0 else since
    tail_results = incremental_tail_results(results, result_count, start)
    snapshot = status_fields_snapshot(job)
    snapshot["results"] = tail_results
    snapshot["next_since"] = start if snapshot.get("terminal", False) else result_count
    snapshot["cached_markers"] = aligned_cached_markers_snapshot(
        tail_results,
        cached_markers,
    )
    return snapshot


def incremental_tail_results(results: list[Any], result_count: int, start: int) -> list[Any]:
    if start >= result_count:
        return []
    return copy_results_tail(results, start)
