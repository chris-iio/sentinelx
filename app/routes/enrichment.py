"""Enrichment polling route."""

from flask import jsonify, request

from app import limiter

from . import bp
from ._helpers import _orch_lock, _orchestrators, _serialize_result


@bp.route("/enrichment/status/<job_id>", methods=["GET"])
@limiter.limit("120 per minute")
def enrichment_status(job_id: str):
    """Return current enrichment progress for a job as JSON.

    Supports cursor-based polling via ?since= query param.
    """
    with _orch_lock:
        orchestrator = _orchestrators.get(job_id)
    if orchestrator is None:
        return jsonify({"error": "job not found"}), 404

    status = orchestrator.get_status(job_id)
    if status is None:
        return jsonify({"error": "job not found"}), 404

    since = request.args.get("since", 0, type=int)
    cached_markers = orchestrator.cached_markers

    all_results = status["results"]
    new_results = all_results[since:]
    serialized = [
        _serialize_result(r, cached_markers) for r in new_results
    ]

    return jsonify(
        {
            "total": status["total"],
            "done": status["done"],
            "complete": status["complete"],
            "results": serialized,
            "next_since": len(all_results),
        }
    )
