"""Shared state and utilities for route modules.

Module-level state lives here so that analysis (which creates orchestrators)
and enrichment_status (which reads them) share the same registry.
"""

import logging
import uuid
from collections import OrderedDict
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from itertools import islice
from threading import Lock
from types import MappingProxyType

from flask import current_app, jsonify, request

from app.enrichment.config_store import ConfigStore
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.orchestrator import EnrichmentOrchestrator
from app.pipeline.models import IOC, IOCType, append_ioc_by_type, group_by_type
from app.text_utils import (
    has_non_whitespace,
    stripped_bounded_non_whitespace,
    stripped_text_or_none,
)
from app.time_utils import utcnow_iso

logger = logging.getLogger(__name__)

# Module-level registry mapping job_id -> EnrichmentOrchestrator instance.
# SEC-18: Bounded OrderedDict with LRU eviction to prevent memory exhaustion.
# M012 S01: keep short terminal tombstones so pollers can tell eviction apart
# from a never-seen job id.
_MAX_ORCHESTRATORS = 200
_STATUS_NOT_FOUND_REASONS = frozenset(("unknown", "evicted"))
_orchestrators: OrderedDict[str, EnrichmentOrchestrator] = OrderedDict()
_terminal_jobs: OrderedDict[str, dict] = OrderedDict()
_orch_lock = Lock()

# Shared thread pool for enrichment jobs — caps concurrent enrichments to 4.
_enrichment_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="enrich")

_HISTORY_SAVE_OUTCOMES = frozenset(("never", "saved", "failed", "skipped"))
_HISTORY_SAVE_RECORDABLE_OUTCOMES = frozenset(("saved", "failed", "skipped"))
_HISTORY_SAVE_COUNTER_FIELDS = ("attempts", "successes", "failures", "skipped")
_HISTORY_SAVE_TIMESTAMP_FIELDS = ("last_attempt_at", "last_success_at", "last_failure_at")
_HISTORY_SAVE_DIAGNOSTICS_DEFAULTS = MappingProxyType({
    "attempts": 0,
    "successes": 0,
    "failures": 0,
    "skipped": 0,
    "last_outcome": "never",
    "last_attempt_at": None,
    "last_success_at": None,
    "last_failure_at": None,
    "last_error_summary": None,
})
_history_save_diag_lock = Lock()


def _history_save_diagnostics_defaults() -> dict[str, object]:
    return _copy_mapping(_HISTORY_SAVE_DIAGNOSTICS_DEFAULTS)


def _copy_mapping(source: Mapping[str, object] | None) -> dict[str, object]:
    """Return a shallow dict snapshot without constructor-copying live state."""
    if source is None:
        return {}
    source_count = len(source)
    if source_count == 0:
        return {}
    if source_count == 1:
        for key in source:
            return {key: source[key]}
    if source_count == 2:
        key_iter = iter(source)
        first = next(key_iter)
        second = next(key_iter)
        return {first: source[first], second: source[second]}

    snapshot: dict[str, object] = {}
    for key in source:
        snapshot[key] = source[key]
    return snapshot


def _copy_history_save_diagnostics(source: Mapping[str, object]) -> dict[str, object]:
    return _copy_mapping(source)


def _copy_terminal_job_snapshot(source: Mapping[str, object] | None) -> dict[str, object]:
    return _copy_mapping(source)


_history_save_diagnostics: dict[str, object] = _history_save_diagnostics_defaults()


def _utcnow_iso() -> str:
    """Return the current UTC timestamp in ISO-8601 Zulu form."""
    return utcnow_iso()


def _coerce_history_save_diagnostics(raw: object) -> dict[str, object]:
    """Return a safe diagnostics snapshot even if module state is malformed."""
    data = raw if isinstance(raw, dict) else {}
    diagnostics = _history_save_diagnostics_defaults()

    for field in _HISTORY_SAVE_COUNTER_FIELDS:
        value = data.get(field)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            diagnostics[field] = value

    outcome = data.get("last_outcome")
    if outcome in _HISTORY_SAVE_OUTCOMES:
        diagnostics["last_outcome"] = outcome

    for field in _HISTORY_SAVE_TIMESTAMP_FIELDS:
        value = data.get(field)
        if isinstance(value, str) and has_non_whitespace(value):
            diagnostics[field] = value

    error_summary = data.get("last_error_summary")
    if isinstance(error_summary, str):
        diagnostics["last_error_summary"] = stripped_bounded_non_whitespace(
            error_summary,
            max_chars=120,
        )

    return diagnostics


def _record_history_save_attempt() -> None:
    """Increment bounded aggregate diagnostics before save_analysis() runs."""
    timestamp = _utcnow_iso()
    with _history_save_diag_lock:
        diagnostics = _coerce_history_save_diagnostics(_history_save_diagnostics)
        diagnostics["attempts"] += 1
        diagnostics["last_attempt_at"] = timestamp
        _replace_history_save_diagnostics(diagnostics)


def _record_history_save_outcome(outcome: str, error: Exception | None = None) -> None:
    """Record the last bounded outcome for helper-owned history persistence."""
    if outcome not in _HISTORY_SAVE_RECORDABLE_OUTCOMES:
        return

    timestamp = _utcnow_iso()
    with _history_save_diag_lock:
        diagnostics = _coerce_history_save_diagnostics(_history_save_diagnostics)
        diagnostics["last_outcome"] = outcome
        if outcome == "saved":
            diagnostics["successes"] += 1
            diagnostics["last_success_at"] = timestamp
            diagnostics["last_error_summary"] = None
        elif outcome == "failed":
            diagnostics["failures"] += 1
            diagnostics["last_failure_at"] = timestamp
            diagnostics["last_error_summary"] = (
                f"{error.__class__.__name__} while saving analysis history"
                if error is not None
                else "History save failed"
            )
        else:
            diagnostics["skipped"] += 1
            diagnostics["last_error_summary"] = None

        _replace_history_save_diagnostics(diagnostics)


def get_history_save_diagnostics() -> dict[str, object]:
    """Return a safe snapshot of helper-level history save diagnostics."""
    with _history_save_diag_lock:
        snapshot = _copy_history_save_diagnostics(_history_save_diagnostics)
    return _coerce_history_save_diagnostics(snapshot)


def get_orchestration_diagnostics_snapshot(job_id: str) -> dict[str, object]:
    """Return a copied, secret-free orchestration diagnostics snapshot.

    This accessor is intentionally narrow for backend diagnostic exports: it
    never returns orchestrator instances, live result objects, or mutable job
    internals.  Missing/evicted jobs are represented as safe snapshots so the
    diagnostic manifest can show that the optional job context was considered.
    """
    normalized_job_id = stripped_text_or_none(str(job_id or "")) or ""
    if not normalized_job_id:
        return {"job_id": "", "found": False, "reason": "job_id_not_provided"}

    with _orch_lock:
        orchestrator = _orchestrators.get(normalized_job_id)
        terminal = _copy_terminal_job_snapshot(_terminal_jobs.get(normalized_job_id))

    if orchestrator is None:
        reason = terminal.get("terminal_reason") or "unknown"
        return {
            "job_id": normalized_job_id,
            "found": False,
            "reason": str(reason)[:80],
            "terminal": bool(terminal),
        }

    status = orchestrator.get_status(normalized_job_id)
    diagnostics = orchestrator.get_diagnostics(normalized_job_id)
    if status is None:
        return {
            "job_id": normalized_job_id,
            "found": False,
            "reason": "job_not_found",
        }

    return {
        "job_id": normalized_job_id,
        "found": True,
        "status": _coerce_orchestration_status_for_diagnostics(status),
        "diagnostics": _coerce_orchestration_diagnostics_for_export(diagnostics),
    }


_ORCHESTRATION_STATUS_COUNT_FIELDS = ("total", "done")
_ORCHESTRATION_STATUS_BOOL_FIELDS = ("complete", "terminal")
_ORCHESTRATION_STATUS_TEXT_FIELDS = ("status", "terminal_reason", "error")


def _coerce_orchestration_status_for_diagnostics(raw: object) -> dict[str, object]:
    data = raw if isinstance(raw, dict) else {}
    status: dict[str, object] = {}
    for field in _ORCHESTRATION_STATUS_COUNT_FIELDS:
        value = data.get(field)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            status[field] = value
    for field in _ORCHESTRATION_STATUS_BOOL_FIELDS:
        value = data.get(field)
        if isinstance(value, bool):
            status[field] = value
    for field in _ORCHESTRATION_STATUS_TEXT_FIELDS:
        value = data.get(field)
        if isinstance(value, str):
            text = stripped_bounded_non_whitespace(value, max_chars=160)
            if text is not None:
                status[field] = text
    result_count = data.get("results")
    if isinstance(result_count, list):
        status["result_count"] = len(result_count)
    return status


def _coerce_orchestration_diagnostics_for_export(raw: object) -> dict[str, object]:
    data = raw if isinstance(raw, dict) else {}
    safe: dict[str, object] = {}
    for key in islice(data, 40):
        value = data[key]
        key_text = str(key)[:80]
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key_text] = value[:240] if isinstance(value, str) else value
        elif isinstance(value, dict):
            children: dict[str, object] = {}
            for child_key in islice(value, 40):
                child_value = value[child_key]
                if isinstance(child_value, (str, int, float, bool)) or child_value is None:
                    children[str(child_key)[:80]] = (
                        child_value[:240] if isinstance(child_value, str) else child_value
                    )
            safe[key_text] = children
        elif isinstance(value, list):
            children: list[object] = []
            for item in islice(value, 25):
                if isinstance(item, (str, int, float, bool)) or item is None:
                    children.append(item[:240] if isinstance(item, str) else item)
            safe[key_text] = children
        else:
            safe[key_text] = repr(value)[:240]
    return safe


def _reset_history_save_diagnostics() -> None:
    """Reset helper-level history save diagnostics for focused tests."""
    with _history_save_diag_lock:
        _replace_history_save_diagnostics(_history_save_diagnostics_defaults())


def _replace_history_save_diagnostics(diagnostics: dict[str, object]) -> None:
    """Replace helper-level history diagnostics while preserving dict identity."""
    _history_save_diagnostics.clear()
    _history_save_diagnostics.update(diagnostics)


def _mask_key(key: str | None) -> str | None:
    """Return key with all but the last 4 characters replaced by asterisks.

    Returns None if key is None or shorter than 4 characters.
    """
    if key is None or key == "":
        return None
    key_length = len(key)
    if key_length <= 4:
        return None
    return "*" * (key_length - 4) + key[-4:]


def _serialize_result(
    r: EnrichmentResult | EnrichmentError,
    cached_markers: dict[str, str] | None = None,
) -> dict:
    """Serialize an enrichment result or error to a JSON-safe dict."""
    if isinstance(r, EnrichmentResult):
        d: dict = {
            "type": "result",
            "ioc_value": r.ioc.value,
            "ioc_type": r.ioc.type.value,
            "provider": r.provider,
            "verdict": r.verdict,
            "detection_count": r.detection_count,
            "total_engines": r.total_engines,
            "scan_date": r.scan_date,
            "raw_stats": r.raw_stats,
        }
        if cached_markers:
            cache_key = r.ioc.value + "|" + r.provider
            cached_at = cached_markers.get(cache_key)
            if cached_at:
                d["cached_at"] = cached_at
        return d
    return {
        "type": "error",
        "ioc_value": r.ioc.value,
        "ioc_type": r.ioc.type.value,
        "provider": r.provider,
        "error": r.error,
    }


def _build_status_payload(status: dict, serialized_results: list[dict]) -> dict:
    """Normalize status responses for both live progress and terminal states.

    Contract:
    - status="running": in-flight job; complete=false, terminal=false.
    - status="complete": successful terminal state; complete=true, terminal=false.
    - status="failed": terminal failure; complete=true, terminal=true and
      terminal_reason identifies why (e.g. unknown, evicted, job_failed).

    Existing progress fields stay intact so cursor polling semantics do not change.
    """
    next_since = status.get("next_since")
    if next_since is None:
        next_since = len(status.get("results", []))

    return {
        "total": status["total"],
        "done": status["done"],
        "complete": status["complete"],
        "results": serialized_results,
        "next_since": next_since,
        "status": status.get("status", "complete" if status["complete"] else "running"),
        "terminal": status.get("terminal", False),
        "terminal_reason": status.get("terminal_reason"),
        "error": status.get("error"),
    }


def _terminal_status(job_id: str, *, reason: str, error: str, since: int = 0) -> dict:
    """Return a terminal status payload for missing/evicted/failed jobs."""
    return {
        "job_id": job_id,
        "total": 0,
        "done": 0,
        "complete": True,
        "results": [],
        "next_since": since,
        "status": "failed",
        "terminal": True,
        "terminal_reason": reason,
        "error": error,
    }


def _serialize_ioc(ioc: IOC) -> dict:
    """Serialize an IOC to a JSON-safe dict for history storage."""
    return {
        "type": ioc.type.value,
        "value": ioc.value,
        "raw_match": ioc.raw_match,
    }


def _group_iocs_for_template(iocs: list[IOC]) -> dict[IOCType, list[IOC]]:
    """Return template IOC groups through the shared route payload seam."""
    return group_by_type(iocs)


def _ioc_template_context(iocs: list[IOC]) -> dict[str, object]:
    """Return common result-template IOC context for fresh analysis routes."""
    total_count = len(iocs)
    no_results = total_count == 0
    return {
        "grouped": {} if no_results else _group_iocs_for_template(iocs),
        "total_count": total_count,
        "no_results": no_results,
    }


def _ioc_from_history_row(data: dict) -> IOC:
    return IOC(
        type=IOCType(data["type"]),
        value=data["value"],
        raw_match=data["raw_match"],
    )


def _group_history_iocs(raw_iocs: list[dict]) -> dict[IOCType, list[IOC]]:
    """Rebuild and group persisted IOC rows in one pass."""
    raw_count = len(raw_iocs)
    if raw_count == 0:
        return {}
    if raw_count == 1:
        ioc = _ioc_from_history_row(raw_iocs[0])
        return {ioc.type: [ioc]}
    if raw_count == 2:
        first = _ioc_from_history_row(raw_iocs[0])
        second = _ioc_from_history_row(raw_iocs[1])
        if first.type == second.type:
            return {first.type: [first, second]}
        return {first.type: [first], second.type: [second]}
    if raw_count == 3:
        grouped: dict[IOCType, list[IOC]] = {}
        append_ioc_by_type(grouped, _ioc_from_history_row(raw_iocs[0]))
        append_ioc_by_type(grouped, _ioc_from_history_row(raw_iocs[1]))
        append_ioc_by_type(grouped, _ioc_from_history_row(raw_iocs[2]))
        return grouped

    grouped: dict[IOCType, list[IOC]] = {}
    for data in raw_iocs:
        append_ioc_by_type(grouped, _ioc_from_history_row(data))
    return grouped


def _history_ioc_template_context(raw_iocs: list[dict], total_count: int) -> dict[str, object]:
    """Return common result-template IOC context for history replay routes."""
    no_results = total_count == 0
    return {
        "grouped": {} if no_results else _group_history_iocs(raw_iocs),
        "total_count": total_count,
        "no_results": no_results,
    }


def _serialize_iocs(iocs: list[IOC]) -> list[dict]:
    """Serialize IOC objects with direct accumulation for history storage."""
    ioc_count = len(iocs)
    if ioc_count == 0:
        return []
    if ioc_count == 1:
        return [_serialize_ioc(iocs[0])]
    if ioc_count == 2:
        return [_serialize_ioc(iocs[0]), _serialize_ioc(iocs[1])]
    if ioc_count == 3:
        return [_serialize_ioc(iocs[0]), _serialize_ioc(iocs[1]), _serialize_ioc(iocs[2])]

    serialized: list[dict] = []
    for ioc in iocs:
        serialized.append(_serialize_ioc(ioc))
    return serialized


def _append_serialized_ioc_by_type(
    grouped: dict[str, list[dict]],
    type_key: str,
    serialized_ioc: dict,
) -> None:
    """Append serialized IOC payloads without setdefault's eager list allocation."""
    group = grouped.get(type_key)
    if group is None:
        group = []
        grouped[type_key] = group
    group.append(serialized_ioc)


def _serialized_ioc_response_payload(iocs: list[IOC]) -> tuple[list[dict], dict[str, list[dict]]]:
    """Return serialized IOC rows plus grouped rows for JSON API responses."""
    ioc_count = len(iocs)
    if ioc_count == 0:
        return [], {}
    if ioc_count == 1:
        ioc = iocs[0]
        serialized = _serialize_ioc(ioc)
        return [serialized], {ioc.type.value: [serialized]}
    if ioc_count == 2:
        first = iocs[0]
        second = iocs[1]
        first_serialized = _serialize_ioc(first)
        second_serialized = _serialize_ioc(second)
        serialized_iocs = [first_serialized, second_serialized]
        if first.type == second.type:
            return serialized_iocs, {first.type.value: serialized_iocs}
        return serialized_iocs, {
            first.type.value: [first_serialized],
            second.type.value: [second_serialized],
        }
    if ioc_count == 3:
        first = iocs[0]
        second = iocs[1]
        third = iocs[2]
        first_serialized = _serialize_ioc(first)
        second_serialized = _serialize_ioc(second)
        third_serialized = _serialize_ioc(third)
        serialized_iocs = [first_serialized, second_serialized, third_serialized]
        if first.type == second.type == third.type:
            return serialized_iocs, {first.type.value: serialized_iocs}
        grouped_summary: dict[str, list[dict]] = {}
        _append_serialized_ioc_by_type(grouped_summary, first.type.value, first_serialized)
        _append_serialized_ioc_by_type(grouped_summary, second.type.value, second_serialized)
        _append_serialized_ioc_by_type(grouped_summary, third.type.value, third_serialized)
        return serialized_iocs, grouped_summary

    serialized_iocs: list[dict] = []
    grouped_summary: dict[str, list[dict]] = {}
    for ioc in iocs:
        serialized = _serialize_ioc(ioc)
        serialized_iocs.append(serialized)
        _append_serialized_ioc_by_type(grouped_summary, ioc.type.value, serialized)
    return serialized_iocs, grouped_summary


def _serialize_results(
    results: list[EnrichmentResult | EnrichmentError],
    cached_markers: dict[str, str] | None = None,
) -> list[dict]:
    """Serialize enrichment results with direct accumulation."""
    result_count = len(results)
    if result_count == 0:
        return []
    if result_count == 1:
        return [_serialize_result(results[0], cached_markers)]
    if result_count == 2:
        return [
            _serialize_result(results[0], cached_markers),
            _serialize_result(results[1], cached_markers),
        ]
    if result_count == 3:
        return [
            _serialize_result(results[0], cached_markers),
            _serialize_result(results[1], cached_markers),
            _serialize_result(results[2], cached_markers),
        ]

    serialized: list[dict] = []
    for result in results:
        serialized.append(_serialize_result(result, cached_markers))
    return serialized


def _online_limits_from_config() -> tuple[int, int]:
    """Return Online enrichment admission limits from Flask config."""
    return (
        int(current_app.config.get("ONLINE_MAX_IOCS", 50)),
        int(current_app.config.get("ONLINE_MAX_DISPATCHES", 200)),
    )


def _online_fanout_diagnostics(
    iocs: list[IOC],
    registry: object,
    *,
    max_iocs: int,
    max_dispatches: int,
) -> dict[str, object]:
    """Return secret-free admission diagnostics for Online enrichment fan-out."""
    provider_counts_by_type: dict[str, int] = {}
    dispatch_count = 0

    for ioc in iocs:
        type_key = ioc.type.value
        if type_key not in provider_counts_by_type:
            try:
                provider_counts_by_type[type_key] = registry.provider_count_for_type(ioc.type)  # type: ignore[attr-defined]
            except Exception as exc:
                logger.warning(
                    "Online fanout provider-count lookup failed for %s: %s",
                    type_key,
                    exc.__class__.__name__,
                )
                provider_counts_by_type[type_key] = 0
        dispatch_count += provider_counts_by_type[type_key]

    ioc_count = len(iocs)
    over_ioc_limit = ioc_count > max_iocs
    over_dispatch_limit = dispatch_count > max_dispatches
    return {
        "ioc_count": ioc_count,
        "dispatch_count": dispatch_count,
        "max_iocs": max_iocs,
        "max_dispatches": max_dispatches,
        "over_ioc_limit": over_ioc_limit,
        "over_dispatch_limit": over_dispatch_limit,
        "allowed": not over_ioc_limit and not over_dispatch_limit,
        "provider_counts_by_type": provider_counts_by_type,
    }


def _online_limit_response(diagnostics: dict[str, object]) -> dict[str, object]:
    """Return a JSON-safe Online limit payload without IOC values or secrets."""
    return {
        "error": "Online enrichment limit exceeded. Reduce the submission or use offline mode.",
        "code": "online_limit_exceeded",
        "limits": {
            "max_iocs": diagnostics["max_iocs"],
            "max_dispatches": diagnostics["max_dispatches"],
        },
        "observed": {
            "ioc_count": diagnostics["ioc_count"],
            "dispatch_count": diagnostics["dispatch_count"],
        },
    }


def _run_enrichment_and_save(
    orchestrator: EnrichmentOrchestrator,
    job_id: str,
    iocs: list[IOC],
    input_text: str,
    mode: str,
    history_store: object,
) -> None:
    """Run enrichment and save results to history.

    Failures during history save are logged but do not break enrichment.
    """
    orchestrator.enrich_all(job_id, iocs)

    try:
        status = orchestrator.get_status(job_id)
        if status is None:
            _record_history_save_outcome("skipped")
            return
        serialized_results = _serialize_results(status["results"])
        serialized_iocs = _serialize_iocs(iocs)
        _record_history_save_attempt()
        history_store.save_analysis(  # type: ignore[union-attr]
            input_text=input_text,
            mode=mode,
            iocs=serialized_iocs,
            results=serialized_results,
            analysis_id=job_id,
        )
        _record_history_save_outcome("saved")
    except Exception as exc:
        _record_history_save_outcome("failed", error=exc)
        logger.warning("Failed to save analysis %s to history", job_id, exc_info=True)


def _setup_orchestrator(
    iocs: list[IOC],
    text: str,
    mode: str,
    history_store: object,
    configured_providers: list[object] | None = None,
) -> tuple[str, EnrichmentOrchestrator, object]:
    """Create an orchestrator, register it, and submit the enrichment job.

    Returns (job_id, orchestrator, registry). The 'not configured' guard
    stays in each caller since the response format differs (redirect vs JSON).
    """
    registry = current_app.registry
    job_id = uuid.uuid4().hex
    cache = current_app.cache_store
    config_store = ConfigStore()
    cache_ttl_hours = config_store.get_cache_ttl()
    orchestrator = EnrichmentOrchestrator(
        adapters=configured_providers if configured_providers is not None else registry.configured(),
        cache=cache,
        cache_ttl_seconds=cache_ttl_hours * 3600,
    )

    with _orch_lock:
        _orchestrators[job_id] = orchestrator
        _terminal_jobs.pop(job_id, None)
        while len(_orchestrators) > _MAX_ORCHESTRATORS:
            evicted_job_id, _ = _orchestrators.popitem(last=False)
            _terminal_jobs[evicted_job_id] = _terminal_status(
                evicted_job_id,
                reason="evicted",
                error="Enrichment job status was evicted from memory.",
            )
        while len(_terminal_jobs) > _MAX_ORCHESTRATORS:
            _terminal_jobs.popitem(last=False)

    _enrichment_pool.submit(
        _run_enrichment_and_save,
        orchestrator, job_id, iocs, text, mode,
        history_store,
    )

    return job_id, orchestrator, registry


def _get_enrichment_status(job_id: str):
    """Shared status endpoint body for both HTML and API routes.

    Returns a Flask JSON response tuple. Success responses preserve the existing
    progress/cursor contract and add machine-readable terminal metadata. Missing
    responses stay 404 but now expose whether the poller hit an unknown id,
    helper-level eviction, orchestrator-level eviction, or a failed job.
    """
    since = request.args.get("since", 0, type=int)

    with _orch_lock:
        orchestrator = _orchestrators.get(job_id)
        terminal = _terminal_jobs.get(job_id)

    if orchestrator is None:
        payload = terminal or _terminal_status(
            job_id,
            reason="unknown",
            error="Enrichment job was not found.",
            since=since,
        )
        payload["next_since"] = since
        return jsonify(payload), 404

    status = orchestrator.get_incremental_status(job_id, since=since)
    if status is None:
        payload = _terminal_status(
            job_id,
            reason="unknown",
            error="Enrichment job was not found.",
            since=since,
        )
        return jsonify(payload), 404

    cached_markers = status.get("cached_markers")
    serialized = _serialize_results(status["results"], cached_markers)

    payload = _build_status_payload(status, serialized)
    status_code = (
        404
        if payload["terminal"] and payload["terminal_reason"] in _STATUS_NOT_FOUND_REASONS
        else 200
    )
    return jsonify(payload), status_code
