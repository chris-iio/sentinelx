"""History routes: list and reload past analyses."""

import json

from flask import abort, current_app, render_template

from app import limiter
from app.pipeline.models import IOC, IOCType, group_by_type

from . import bp


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

    iocs = [
        IOC(
            type=IOCType(d["type"]),
            value=d["value"],
            raw_match=d["raw_match"],
        )
        for d in record["iocs"]
    ]
    grouped = group_by_type(iocs)
    total_count = record["total_count"]
    no_results = total_count == 0
    enrichable_count = len(record["results"])

    history_results = json.dumps(record["results"])

    return render_template(
        "results.html",
        grouped={} if no_results else grouped,
        mode="online",
        total_count=total_count,
        no_results=no_results,
        job_id="history",
        enrichable_count=enrichable_count,
        provider_counts="{}",
        provider_coverage={"registered": 0, "configured": 0, "needs_key": 0},
        history_results=history_results,
    )
