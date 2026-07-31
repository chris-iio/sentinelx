"""REST API routes for programmatic IOC analysis.

Provides JSON endpoints for IOC extraction and enrichment polling.
CSRF-exempt (stateless JSON API) but rate-limited.

Routes:
    GET  /api/health — local liveness/readiness probe with fixed JSON contract
    POST /api/analyze  — extract IOCs from text, optionally launch enrichment
    GET  /api/status/<job_id> — poll enrichment progress (same as HTML endpoint)
"""

from flask import Blueprint, current_app, jsonify, request

from app import limiter
from app.health_contract import HEALTH_PATH
from app.pipeline.extractor import run_pipeline
from app.text_utils import has_non_whitespace

from .api_analysis import api_analyze_route_response
from .api_health import api_health_route_response
from .enrichment_jobs import _get_enrichment_status
from . import online

bp_api = Blueprint("api", __name__, url_prefix="/api")


@bp_api.route(HEALTH_PATH.removeprefix("/api"), methods=["GET"])
@limiter.limit("240 per minute")
def api_health():
    """Return a cheap, secret-free health contract for local probes."""
    return api_health_route_response(
        cache_store=current_app.cache_store,
        history_store=current_app.history_store,
        registry=current_app.registry,
        app_logger=current_app.logger,
        jsonify_response=jsonify,
    )


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
    return api_analyze_route_response(
        request,
        has_content=has_non_whitespace,
        extract_iocs=run_pipeline,
        history_store=current_app.history_store,
        registry=current_app.registry,
        cache_store=current_app.cache_store,
        online_limits=online._online_limits_from_config(current_app.config),
        app_logger=current_app.logger,
        jsonify_response=jsonify,
    )


@bp_api.route("/status/<job_id>", methods=["GET"])
@limiter.limit("120 per minute")
def api_status(job_id: str):
    """Poll enrichment progress for a job.

    Same semantics as the HTML enrichment_status endpoint.
    Supports cursor-based polling via ?since= query param.
    """
    return _get_enrichment_status(job_id)
