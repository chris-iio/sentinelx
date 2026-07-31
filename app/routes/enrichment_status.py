"""Pure status-payload helpers for enrichment polling routes."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.enrichment.cache_payloads import cache_marker_key
from app.enrichment.models import EnrichmentError, EnrichmentResult

STATUS_NOT_FOUND_REASONS = frozenset(("unknown", "evicted"))
EVICTED_JOB_ERROR = "Enrichment job status was evicted from memory."
UNKNOWN_JOB_ERROR = "Enrichment job was not found."


@dataclass(frozen=True, slots=True)
class EnrichmentStatusResponse:
    """JSON payload and HTTP status for one enrichment status poll."""

    payload: dict[str, Any]
    status: int


def serialize_result(
    result: EnrichmentResult | EnrichmentError,
    cached_markers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Serialize one enrichment result or error to a JSON-safe dict."""
    if isinstance(result, EnrichmentResult):
        payload: dict[str, Any] = {
            "type": "result",
            "ioc_value": result.ioc.value,
            "ioc_type": result.ioc.type.value,
            "provider": result.provider,
            "verdict": result.verdict,
            "detection_count": result.detection_count,
            "total_engines": result.total_engines,
            "scan_date": result.scan_date,
            "raw_stats": result.raw_stats,
        }
        if cached_markers:
            cache_key = cache_marker_key(result.ioc, result.provider)
            cached_at = cached_markers.get(cache_key)
            if cached_at:
                payload["cached_at"] = cached_at
        return payload
    return {
        "type": "error",
        "ioc_value": result.ioc.value,
        "ioc_type": result.ioc.type.value,
        "provider": result.provider,
        "error": result.error,
    }


def serialize_results(
    results: list[EnrichmentResult | EnrichmentError],
    cached_markers: dict[str, str] | None = None,
    *,
    serializer: Callable[
        [EnrichmentResult | EnrichmentError, dict[str, str] | None],
        dict[str, Any],
    ] = serialize_result,
) -> list[dict[str, Any]]:
    """Serialize enrichment results with direct accumulation."""
    result_count = len(results)
    if result_count == 0:
        return []
    if result_count == 1:
        return [serializer(results[0], cached_markers)]
    if result_count == 2:
        return [
            serializer(results[0], cached_markers),
            serializer(results[1], cached_markers),
        ]
    if result_count == 3:
        return [
            serializer(results[0], cached_markers),
            serializer(results[1], cached_markers),
            serializer(results[2], cached_markers),
        ]
    if result_count == 4:
        return [
            serializer(results[0], cached_markers),
            serializer(results[1], cached_markers),
            serializer(results[2], cached_markers),
            serializer(results[3], cached_markers),
        ]

    serialized: list[dict[str, Any]] = []
    for result in results:
        append_serialized_result(serialized, result, cached_markers, serializer=serializer)
    return serialized


def append_serialized_result(
    serialized: list[dict[str, Any]],
    result: EnrichmentResult | EnrichmentError,
    cached_markers: dict[str, str] | None = None,
    *,
    serializer: Callable[
        [EnrichmentResult | EnrichmentError, dict[str, str] | None],
        dict[str, Any],
    ] = serialize_result,
) -> None:
    serialized.append(serializer(result, cached_markers))


def build_status_payload(status: dict[str, Any], serialized_results: list[dict[str, Any]]) -> dict:
    """Normalize status responses for both live progress and terminal states."""
    return {
        "total": status["total"],
        "done": status["done"],
        "complete": status["complete"],
        "results": serialized_results,
        "next_since": status_next_since(status),
        "status": status_text(status),
        "terminal": status.get("terminal", False),
        "terminal_reason": status.get("terminal_reason"),
        "error": status.get("error"),
    }


def status_next_since(status: dict[str, Any]) -> int:
    """Return the explicit polling cursor or the retained-result fallback."""
    next_since = status.get("next_since")
    if next_since is None:
        return len(status.get("results", []))
    return next_since


def status_text(status: dict[str, Any]) -> str:
    """Return explicit status text or derive it from completion state."""
    return status.get("status", "complete" if status["complete"] else "running")


def serialized_status_results(status: dict[str, Any]) -> list[dict[str, Any]]:
    """Serialize the current status result tail with its cached-marker map."""
    cached_markers = status.get("cached_markers")
    return serialize_results(status["results"], cached_markers)


def terminal_status(job_id: str, *, reason: str, error: str, since: int = 0) -> dict:
    """Return a terminal status payload for missing/evicted/failed jobs."""
    return {
        "job_id": job_id,
        "total": 0,
        "done": 0,
        "complete": False,
        "results": [],
        "next_since": since,
        "status": "failed",
        "terminal": True,
        "terminal_reason": reason,
        "error": error,
    }


def evicted_terminal_status(job_id: str) -> dict:
    """Return the standard route-level terminal tombstone for evicted jobs."""
    return terminal_status(
        job_id,
        reason="evicted",
        error=EVICTED_JOB_ERROR,
    )


def unknown_terminal_status(job_id: str, *, since: int = 0) -> dict:
    """Return the standard terminal tombstone for unknown job ids."""
    return terminal_status(
        job_id,
        reason="unknown",
        error=UNKNOWN_JOB_ERROR,
        since=since,
    )


def status_code_for_payload(payload: dict[str, Any]) -> int:
    """Return the HTTP status code for a normalized polling payload."""
    if payload["terminal"] and payload["terminal_reason"] in STATUS_NOT_FOUND_REASONS:
        return 404
    return 200


def terminal_status_response(
    job_id: str,
    terminal: dict[str, Any] | None,
    *,
    since: int,
) -> EnrichmentStatusResponse:
    """Return the terminal/unknown response for a missing live orchestrator."""
    payload = terminal or unknown_terminal_status(job_id, since=since)
    payload["next_since"] = since
    return EnrichmentStatusResponse(payload, 404)


def live_status_response(status: dict[str, Any]) -> EnrichmentStatusResponse:
    """Return the normalized response for a live orchestrator status snapshot."""
    serialized = serialized_status_results(status)
    payload = build_status_payload(status, serialized)
    return EnrichmentStatusResponse(payload, status_code_for_payload(payload))


def enrichment_status_response(
    job_id: str,
    *,
    orchestrator: Any | None,
    terminal: dict[str, Any] | None,
    since: int,
) -> EnrichmentStatusResponse:
    """Resolve live, terminal, and unknown job states into a route response."""
    if orchestrator is None:
        return terminal_status_response(job_id, terminal, since=since)

    status = orchestrator.get_incremental_status(job_id, since=since)
    if status is None:
        return EnrichmentStatusResponse(
            unknown_terminal_status(job_id, since=since),
            404,
        )

    return live_status_response(status)


def coerce_status_cursor(value: int | None) -> int:
    """Normalize polling cursors so negative values cannot request tail slices."""
    if value is None or value < 0:
        return 0
    return value
