"""REST API routes for programmatic IOC analysis.

Provides JSON endpoints for IOC extraction and enrichment polling.
CSRF-exempt (stateless JSON API) but rate-limited.

Routes:
    POST /api/analyze  — extract IOCs from text, optionally launch enrichment
    GET  /api/status/<job_id> — poll enrichment progress (same as HTML endpoint)
"""

import json
import uuid

from flask import Blueprint, current_app, jsonify, request

from app import limiter
from app.enrichment.config_store import ConfigStore
from app.enrichment.orchestrator import EnrichmentOrchestrator
from app.pipeline.extractor import run_pipeline
from app.pipeline.models import IOCType, group_by_type

from ._helpers import (
    _MAX_ORCHESTRATORS,
    _enrichment_pool,
    _orch_lock,
    _orchestrators,
    _run_enrichment_and_save,
    _serialize_ioc,
    _serialize_result,
)

bp_api = Blueprint("api", __name__, url_prefix="/api")

_VALID_MODES = {"offline", "online"}


@bp_api.route("/analyze", methods=["POST"])
@limiter.limit("10 per minute")
def api_analyze():
    """Extract IOCs from submitted text and return structured JSON.

    Request body (JSON):
        text (str, required): Free-form text containing IOCs.
        mode (str, optional): "offline" (default) or "online".

    Offline response (200):
        {"mode": "offline", "total_count": N, "iocs": [...]}

    Online response (200):
        {"mode": "online", "total_count": N, "iocs": [...], "job_id": "...",
         "status_url": "/api/status/<job_id>"}

    Errors:
        400: Missing/invalid JSON body, empty text, or invalid mode.
        400: No provider configured (online mode).
    """
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Request body must be JSON"}), 400

    text = data.get("text", "")
    if not isinstance(text, str) or not text.strip():
        return jsonify({"error": "Field 'text' is required and must be non-empty"}), 400

    mode = data.get("mode", "offline")
    if mode not in _VALID_MODES:
        return jsonify({"error": f"Invalid mode '{mode}'. Must be 'offline' or 'online'."}), 400

    iocs = run_pipeline(text)
    grouped = group_by_type(iocs)
    total_count = len(iocs)

    serialized_iocs = [_serialize_ioc(ioc) for ioc in iocs]

    # Build grouped summary
    grouped_summary = {}
    for ioc_type, ioc_list in grouped.items():
        type_key = ioc_type.value if isinstance(ioc_type, IOCType) else str(ioc_type)
        grouped_summary[type_key] = [_serialize_ioc(i) for i in ioc_list]

    response: dict = {
        "mode": mode,
        "total_count": total_count,
        "iocs": serialized_iocs,
        "grouped": grouped_summary,
    }

    if mode == "online":
        registry = current_app.registry

        if not registry.configured():
            return jsonify({
                "error": "No provider API keys configured. Configure at least one provider in /settings.",
            }), 400

        job_id = uuid.uuid4().hex
        cache = current_app.cache_store
        config_store = ConfigStore()
        cache_ttl_hours = config_store.get_cache_ttl()
        orchestrator = EnrichmentOrchestrator(
            adapters=registry.configured(),
            cache=cache,
            cache_ttl_seconds=cache_ttl_hours * 3600,
        )

        with _orch_lock:
            _orchestrators[job_id] = orchestrator
            while len(_orchestrators) > _MAX_ORCHESTRATORS:
                _orchestrators.popitem(last=False)

        _enrichment_pool.submit(
            _run_enrichment_and_save,
            orchestrator, job_id, iocs, text, mode,
            current_app.history_store,
        )

        response["job_id"] = job_id
        response["status_url"] = f"/api/status/{job_id}"

    return jsonify(response), 200


@bp_api.route("/status/<job_id>", methods=["GET"])
@limiter.limit("120 per minute")
def api_status(job_id: str):
    """Poll enrichment progress for a job.

    Same semantics as the HTML enrichment_status endpoint.
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

    return jsonify({
        "total": status["total"],
        "done": status["done"],
        "complete": status["complete"],
        "results": serialized,
        "next_since": len(all_results),
    })
