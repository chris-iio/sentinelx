"""History replay template context helpers."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.json_utils import EMPTY_JSON_OBJECT, encode_json_array

from .analysis_modes import ANALYSIS_MODE_ONLINE
from .ioc_payloads import _history_ioc_template_context
from .template_results import TemplateResult, apply_template_result

HISTORY_JOB_ID = "history"
HISTORY_RESULTS_OWNER = "history"
EMPTY_PROVIDER_COVERAGE = {"registered": 0, "configured": 0, "needs_key": 0}
HISTORY_LIST_LIMIT = 50


def history_list_context(
    history_store: object,
    *,
    limit: int = HISTORY_LIST_LIMIT,
) -> dict[str, object]:
    """Return history-list template context from the bounded recent-history query."""
    return {
        "analyses": history_store.list_recent(limit=limit),  # type: ignore[attr-defined]
    }


def history_list_result(history_store: object) -> TemplateResult:
    """Return the history list render decision for the current history store."""
    return TemplateResult("history.html", history_list_context(history_store), 200)


def history_list_route_response(
    history_store: object,
    *,
    render_template: Callable[..., Any],
) -> Any:
    """Apply the history list render decision for a route-supplied store."""
    return apply_template_result(
        history_list_result(history_store),
        render_template=render_template,
    )


def load_history_replay_context(
    history_store: object,
    analysis_id: str,
) -> dict[str, object] | None:
    """Load a persisted analysis and return its replay context, or None when absent."""
    record = history_store.load_analysis(analysis_id)  # type: ignore[attr-defined]
    if record is None:
        return None
    return history_replay_context(record)


def history_detail_result(history_store: object, analysis_id: str) -> TemplateResult:
    """Return the history detail render decision for a persisted analysis id."""
    context = load_history_replay_context(history_store, analysis_id)
    if context is None:
        return TemplateResult(None, None, 404)
    return TemplateResult("results.html", context, 200)


def history_detail_route_response(
    history_store: object,
    analysis_id: str,
    *,
    abort_request: Callable[[int], Any],
    render_template: Callable[..., Any],
) -> Any:
    """Apply the history detail render-or-404 decision for a route-supplied store."""
    return apply_template_result(
        history_detail_result(history_store, analysis_id),
        abort_request=abort_request,
        render_template=render_template,
    )


def history_results_json(results: list[dict]) -> str:
    """Serialize replay results without invoking JSON machinery for the empty case."""
    return encode_json_array(results)


def history_replay_context(record: dict) -> dict[str, object]:
    """Return result-template context for a persisted analysis replay."""
    results = record["results"]
    context = _history_ioc_template_context(record["iocs"], record["total_count"])
    context["mode"] = ANALYSIS_MODE_ONLINE
    context["job_id"] = HISTORY_JOB_ID
    context["enrichable_count"] = len(results)
    context["provider_counts"] = EMPTY_JSON_OBJECT
    context["provider_coverage"] = EMPTY_PROVIDER_COVERAGE
    context["history_results"] = history_results_json(results)
    context["results_owner"] = HISTORY_RESULTS_OWNER
    return context
