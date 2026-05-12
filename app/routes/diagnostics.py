"""Diagnostic export route for analyst support bundles."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from flask import Response, current_app

from app import limiter
from app.diagnostics import assemble_diagnostic_bundle, build_default_diagnostic_sources
from app.enrichment.config_store import ConfigStore

from . import bp

logger = logging.getLogger(__name__)
_FAILURE_BODY = "Diagnostic export failed. Check server logs."


def _utcnow() -> datetime:
    """Return current UTC time for diagnostic export timestamps."""
    return datetime.now(timezone.utc)


def _utc_iso(timestamp: datetime) -> str:
    """Return an ISO-8601 UTC timestamp using the app's Zulu convention."""
    return timestamp.isoformat().replace("+00:00", "Z")


@bp.route("/diagnostics/export", methods=["GET"])
@limiter.limit("3 per minute")
def diagnostics_export() -> Response:
    """Return a bounded, redacted diagnostic ZIP archive for analysts."""
    timestamp = _utcnow()
    generated_at = _utc_iso(timestamp)
    config_store = ConfigStore()
    cache_store = current_app.cache_store
    history_store = current_app.history_store

    try:
        sources = build_default_diagnostic_sources(
            config_store=config_store,
            cache_store=cache_store,
            history_store=history_store,
            generated_at=generated_at,
        )
        bundle = assemble_diagnostic_bundle(
            sources,
            generated_at=generated_at,
            config_store=config_store,
        )
    except Exception:  # noqa: BLE001 - export failures must be bounded for analysts.
        logger.error("Diagnostic export assembly failed", exc_info=True)
        return Response(_FAILURE_BODY, status=500, mimetype="text/plain")

    filename = f"sentinelx-diagnostic-{timestamp.date().isoformat()}.zip"
    return Response(
        bundle.archive_bytes,
        mimetype="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Diagnostic-Sources": str(bundle.summary["source_count"]),
        },
    )
