"""Secret-free route diagnostics helpers for enrichment jobs."""

from __future__ import annotations

from collections.abc import Mapping
from itertools import islice

from app.enrichment.history_diagnostics import copy_mapping
from app.text_utils import stripped_bounded_non_whitespace, stripped_text_or_none


_ORCHESTRATION_STATUS_COUNT_FIELDS = ("total", "done")
_ORCHESTRATION_STATUS_BOOL_FIELDS = ("complete", "terminal")
_ORCHESTRATION_STATUS_TEXT_FIELDS = ("status", "terminal_reason", "error")


def _export_scalar(value: object) -> object:
    if isinstance(value, str):
        return value[:240]
    return value


def _is_export_scalar(value: object) -> bool:
    return isinstance(value, (str, int, float, bool)) or value is None


def _append_export_scalar(children: list[object], value: object) -> None:
    if _is_export_scalar(value):
        children.append(_export_scalar(value))


def _set_export_child_scalar(
    children: dict[str, object],
    child_key: object,
    child_value: object,
) -> None:
    if _is_export_scalar(child_value):
        children[str(child_key)[:80]] = _export_scalar(child_value)


def _set_export_value(safe: dict[str, object], key_text: str, value: object) -> None:
    if _is_export_scalar(value):
        safe[key_text] = _export_scalar(value)
    elif isinstance(value, dict):
        children: dict[str, object] = {}
        for child_key in islice(value, 40):
            _set_export_child_scalar(children, child_key, value[child_key])
        safe[key_text] = children
    elif isinstance(value, list):
        safe[key_text] = _coerce_export_list(value)
    else:
        safe[key_text] = repr(value)[:240]


def _coerce_export_list(value: list[object]) -> list[object]:
    item_count = len(value)
    if item_count == 0:
        return []
    if item_count == 1:
        first = value[0]
        return [_export_scalar(first)] if _is_export_scalar(first) else []
    if item_count == 2:
        children: list[object] = []
        _append_export_scalar(children, value[0])
        _append_export_scalar(children, value[1])
        return children
    if item_count == 3:
        children: list[object] = []
        _append_export_scalar(children, value[0])
        _append_export_scalar(children, value[1])
        _append_export_scalar(children, value[2])
        return children
    if item_count == 4:
        children: list[object] = []
        _append_export_scalar(children, value[0])
        _append_export_scalar(children, value[1])
        _append_export_scalar(children, value[2])
        _append_export_scalar(children, value[3])
        return children

    children: list[object] = []
    for item in islice(value, 25):
        _append_export_scalar(children, item)
    return children


def _coerce_orchestration_status_for_diagnostics(raw: object) -> dict[str, object]:
    data = raw if isinstance(raw, dict) else {}
    status: dict[str, object] = {}
    _coerce_status_count_field(status, data, "total")
    _coerce_status_count_field(status, data, "done")
    _coerce_status_bool_field(status, data, "complete")
    _coerce_status_bool_field(status, data, "terminal")
    _coerce_status_text_field(status, data, "status")
    _coerce_status_text_field(status, data, "terminal_reason")
    _coerce_status_text_field(status, data, "error")
    result_count = data.get("results")
    if isinstance(result_count, list):
        status["result_count"] = len(result_count)
    return status


def _coerce_status_count_field(
    status: dict[str, object],
    data: dict[str, object],
    field: str,
) -> None:
    value = data.get(field)
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        status[field] = value


def _coerce_status_bool_field(
    status: dict[str, object],
    data: dict[str, object],
    field: str,
) -> None:
    value = data.get(field)
    if isinstance(value, bool):
        status[field] = value


def _coerce_status_text_field(
    status: dict[str, object],
    data: dict[str, object],
    field: str,
) -> None:
    value = data.get(field)
    if isinstance(value, str):
        text = stripped_bounded_non_whitespace(value, max_chars=160)
        if text is not None:
            status[field] = text


def _coerce_orchestration_diagnostics_for_export(raw: object) -> dict[str, object]:
    data = raw if isinstance(raw, dict) else {}
    safe: dict[str, object] = {}
    for key in islice(data, 40):
        value = data[key]
        key_text = str(key)[:80]
        _set_export_value(safe, key_text, value)
    return safe


def build_orchestration_diagnostics_snapshot(
    *,
    job_id: object,
    orchestrator: object | None,
    terminal_job: Mapping[str, object] | None,
) -> dict[str, object]:
    """Return a copied, secret-free orchestration diagnostics snapshot."""
    normalized_job_id = stripped_text_or_none(str(job_id or "")) or ""
    if not normalized_job_id:
        return {"job_id": "", "found": False, "reason": "job_id_not_provided"}

    terminal = copy_mapping(terminal_job)
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
