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
from app.health_contract import HEALTH_PATH, build_health_payload
from app.pipeline.extractor import run_pipeline
from app.text_utils import has_non_whitespace

from ._helpers import (
    _append_serialized_ioc_by_type,
    _get_enrichment_status,
    _online_fanout_diagnostics,
    _online_limit_response,
    _online_limits_from_config,
    _serialized_ioc_response_payload,
    _serialize_ioc,
    _setup_orchestrator,
)

bp_api = Blueprint("api", __name__, url_prefix="/api")

_VALID_MODES = frozenset(("offline", "online"))


def _health_check_ok(detail: str = "ok") -> dict[str, str]:
    """Return a normalized healthy check result."""
    return {"status": "ok", "detail": detail}


def _health_check_degraded(exc: Exception) -> dict[str, str]:
    """Return a bounded degraded check without leaking paths or secrets."""
    return {"status": "degraded", "detail": exc.__class__.__name__}


def _registry_health_detail(registry) -> str:
    """Return configured/registered provider health detail from direct counts."""
    configured_count = registry.configured_count()
    registered_count = registry.registered_count()
    return f"{configured_count}/{registered_count} providers configured"


@bp_api.route(HEALTH_PATH.removeprefix("/api"), methods=["GET"])
@limiter.limit("240 per minute")
def api_health():
    """Return a cheap, secret-free health contract for local probes."""
    checks: dict[str, dict[str, str]] = {}

    try:
        current_app.cache_store.stats()
        checks["cache"] = _health_check_ok()
    except Exception as exc:  # pragma: no cover - exercised by route tests
        current_app.logger.warning("Health cache check failed: %s", exc.__class__.__name__)
        checks["cache"] = _health_check_degraded(exc)

    try:
        current_app.history_store.list_recent(limit=1)
        checks["history"] = _health_check_ok()
    except Exception as exc:  # pragma: no cover - exercised by route tests
        current_app.logger.warning("Health history check failed: %s", exc.__class__.__name__)
        checks["history"] = _health_check_degraded(exc)

    try:
        checks["registry"] = _health_check_ok(_registry_health_detail(current_app.registry))
    except Exception as exc:  # pragma: no cover - exercised by route tests
        current_app.logger.warning("Health registry check failed: %s", exc.__class__.__name__)
        checks["registry"] = _health_check_degraded(exc)

    return jsonify(build_health_payload(checks)), 200


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
    if not isinstance(text, str) or not has_non_whitespace(text):
        return jsonify({"error": "Field 'text' is required and must be non-empty"}), 400

    mode = data.get("mode", "offline")
    if mode not in _VALID_MODES:
        return jsonify({"error": f"Invalid mode '{mode}'. Must be 'offline' or 'online'."}), 400

    iocs = run_pipeline(text)
    total_count = len(iocs)
    if total_count == 0:
        return jsonify({
            "mode": mode,
            "total_count": 0,
            "iocs": [],
            "grouped": {},
        }), 200

    job_id: str | None = None

    if mode == "online":
        registry = current_app.registry
        configured_providers = registry.configured()

        if not configured_providers:
            return jsonify({
                "error": (
                    "No provider API keys configured. "
                    "Configure at least one provider in /settings."
                ),
            }), 400

        max_iocs, max_dispatches = _online_limits_from_config()
        fanout_diagnostics = _online_fanout_diagnostics(
            iocs,
            registry,
            max_iocs=max_iocs,
            max_dispatches=max_dispatches,
        )
        if not fanout_diagnostics["allowed"]:
            current_app.logger.warning(
                "API online enrichment rejected by admission guard: iocs=%s dispatches=%s limits=%s/%s",
                fanout_diagnostics["ioc_count"],
                fanout_diagnostics["dispatch_count"],
                fanout_diagnostics["max_iocs"],
                fanout_diagnostics["max_dispatches"],
            )
            return jsonify(_online_limit_response(fanout_diagnostics)), 413

        job_id, _, registry = _setup_orchestrator(
            iocs, text, mode, current_app.history_store, configured_providers,
        )

    serialized_iocs, grouped_summary = _serialized_ioc_response_payload(iocs)

    response: dict = {
        "mode": mode,
        "total_count": total_count,
        "iocs": serialized_iocs,
        "grouped": grouped_summary,
    }

    if job_id is not None:
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
    return _get_enrichment_status(job_id)
