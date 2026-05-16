"""History routes: list and reload past analyses."""

from flask import abort, current_app, render_template

from app import limiter
from app.json_utils import EMPTY_JSON_ARRAY, EMPTY_JSON_OBJECT, encode_json_array

from . import bp
from ._helpers import _group_history_iocs, _history_ioc_template_context

_EMPTY_JSON_ARRAY = EMPTY_JSON_ARRAY
_EMPTY_JSON_OBJECT = EMPTY_JSON_OBJECT


def _history_results_json(results: list[dict]) -> str:
    """Serialize replay results without invoking JSON machinery for the empty case."""
    return encode_json_array(results)


@bp.route("/history")
@limiter.limit("30 per minute")
def history_list():
    """List recent analyses."""
    analyses = current_app.history_store.list_recent(limit=50)
    return render_template("history.html", analyses=analyses)


@bp.route("/history/<analysis_id>")
@limiter.limit("30 per minute")
def history_detail(analysis_id: str):
    """Reload a past analysis from history."""
    store = current_app.history_store
    record = store.load_analysis(analysis_id)
    if record is None:
        abort(404)

    enrichable_count = len(record["results"])

    history_results = _history_results_json(record["results"])

    return render_template(
        "results.html",
        mode="online",
        **_history_ioc_template_context(record["iocs"], record["total_count"]),
        job_id="history",
        enrichable_count=enrichable_count,
        provider_counts=_EMPTY_JSON_OBJECT,
        provider_coverage={"registered": 0, "configured": 0, "needs_key": 0},
        history_results=history_results,
        results_owner="history",
    )
