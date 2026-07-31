"""Pure job-state helpers for enrichment orchestration."""
from __future__ import annotations

from collections import OrderedDict
from typing import Any

from .diagnostics import _coerce_job_diagnostics
from .models import EnrichmentError

EVICTED_JOB_ERROR = "Enrichment job status was evicted from memory."


def initial_job_state(total: int, diagnostics: dict[str, Any]) -> dict[str, Any]:
    """Return the queued status record for one enrichment job."""
    return {
        "total": total,
        "done": 0,
        "results": [],
        "complete": False,
        "status": "queued",
        "terminal": False,
        "terminal_reason": None,
        "error": None,
        "_diagnostics": diagnostics,
    }


def mark_job_running(job: dict[str, Any]) -> None:
    """Move a queued job to the running state."""
    if job["status"] != "queued":
        raise RuntimeError(f"Cannot start enrichment job from {job['status']} state")
    job["status"] = "running"


def mark_job_failed(
    job: dict[str, Any],
    exc: BaseException,
    *,
    reason: str = "job_failed",
) -> None:
    """Mutate a live job record into an explicit terminal failure."""
    job["complete"] = False
    job["status"] = "failed"
    job["terminal"] = True
    job["terminal_reason"] = reason
    job["error"] = str(exc) or exc.__class__.__name__


def mark_job_complete(job: dict[str, Any]) -> None:
    """Mutate a fully successful job record into a completion."""
    if job["done"] != job["total"]:
        raise RuntimeError("Cannot complete enrichment job with unfinished lookups")
    job["complete"] = True
    job["status"] = "complete"


def mark_live_job_running(jobs: OrderedDict[str, dict], job_id: str) -> None:
    """Move a registered queued job to the running state."""
    mark_job_running(jobs[job_id])


def mark_live_job_failed(
    jobs: OrderedDict[str, dict],
    job_id: str,
    exc: BaseException,
    *,
    reason: str = "job_failed",
) -> None:
    """Mutate a registered live job into an explicit terminal failure."""
    mark_job_failed(jobs[job_id], exc, reason=reason)


def mark_live_job_finished(jobs: OrderedDict[str, dict], job_id: str) -> None:
    """Finish a job successfully or expose provider-level partial failure."""
    job = jobs[job_id]
    failed_lookups = sum(
        1 for result in job["results"] if isinstance(result, EnrichmentError)
    )
    if failed_lookups:
        total = job["total"]
        mark_job_failed(
            job,
            RuntimeError(f"{failed_lookups} of {total} enrichment lookups failed"),
            reason="partial_failure" if failed_lookups < total else "provider_failure",
        )
        return
    mark_job_complete(job)


def record_lookup_result(job: dict[str, Any], result: Any) -> None:
    """Append one completed lookup result and advance job progress."""
    append_job_result(job, result)
    job["done"] += 1


def append_job_result(job: dict[str, Any], result: Any) -> None:
    job["results"].append(result)


def record_live_lookup_result(
    jobs: OrderedDict[str, dict],
    job_id: str,
    result: Any,
) -> None:
    """Append one lookup result to a registered live job and advance progress."""
    record_lookup_result(jobs[job_id], result)


def register_live_job(
    jobs: OrderedDict[str, dict],
    terminal_jobs: OrderedDict[str, dict],
    job_id: str,
    *,
    total: int,
    diagnostics: dict[str, Any],
    max_jobs: int,
) -> None:
    """Register a live job and clear any stale terminal state for the same id."""
    jobs[job_id] = initial_job_state(total, diagnostics)
    terminal_jobs.pop(job_id, None)
    evict_oldest_jobs(jobs, terminal_jobs, max_jobs)


def resolved_job_record(
    jobs: OrderedDict[str, dict],
    terminal_jobs: OrderedDict[str, dict],
    job_id: str,
) -> dict | None:
    """Return the live job record or terminal tombstone for *job_id*."""
    job = jobs.get(job_id)
    if job is not None:
        return job
    return terminal_jobs.get(job_id)


def eviction_tombstone(evicted_job: dict[str, Any]) -> dict[str, Any]:
    """Return a terminal tombstone for an evicted job status record."""
    return {
        "total": evicted_job["total"],
        "done": evicted_job["done"],
        "results": [],
        "complete": False,
        "status": "failed",
        "terminal": True,
        "terminal_reason": "evicted",
        "error": EVICTED_JOB_ERROR,
        "_diagnostics": _coerce_job_diagnostics(evicted_job.get("_diagnostics")),
    }


def evict_oldest_jobs(
    jobs: OrderedDict[str, dict],
    terminal_jobs: OrderedDict[str, dict],
    max_jobs: int,
) -> None:
    """Evict live and terminal job state down to the configured retention cap."""
    while len(jobs) > max_jobs:
        evicted_job_id, evicted_job = jobs.popitem(last=False)
        terminal_jobs[evicted_job_id] = eviction_tombstone(evicted_job)
        while len(terminal_jobs) > max_jobs:
            terminal_jobs.popitem(last=False)


def cached_markers_snapshot(markers: dict[str, str]) -> dict[str, str]:
    """Return a caller-isolated marker snapshot without constructor-copying."""
    marker_count = len(markers)
    if marker_count == 0:
        return {}
    if marker_count == 1:
        key = next(iter(markers))
        return {key: markers[key]}
    if marker_count == 2:
        iterator = iter(markers)
        first = next(iterator)
        second = next(iterator)
        return {first: markers[first], second: markers[second]}
    if marker_count == 3:
        iterator = iter(markers)
        first = next(iterator)
        second = next(iterator)
        third = next(iterator)
        return {first: markers[first], second: markers[second], third: markers[third]}
    if marker_count == 4:
        iterator = iter(markers)
        first = next(iterator)
        second = next(iterator)
        third = next(iterator)
        fourth = next(iterator)
        return {
            first: markers[first],
            second: markers[second],
            third: markers[third],
            fourth: markers[fourth],
        }

    snapshot: dict[str, str] = {}
    for key in markers:
        append_cached_marker_snapshot_entry(snapshot, markers, key)
    return snapshot


def append_cached_marker_snapshot_entry(
    snapshot: dict[str, str],
    markers: dict[str, str],
    key: str,
) -> None:
    snapshot[key] = markers[key]


def record_cached_marker(markers: dict[str, str], cache_key: str, cached_at: str) -> None:
    """Record a cache-hit marker in the mutable marker map."""
    markers[cache_key] = cached_at
