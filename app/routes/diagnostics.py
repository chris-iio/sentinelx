"""Diagnostic export route for analyst support bundles."""
from __future__ import annotations

import logging

from flask import Response, current_app

from app import limiter
from app.enrichment.config_store import ConfigStore

from . import bp
from .diagnostic_export import diagnostic_export_route_response

logger = logging.getLogger(__name__)


@bp.route("/diagnostics/export", methods=["GET"])
@limiter.limit("3 per minute")
def diagnostics_export() -> Response:
    """Return a bounded, redacted diagnostic ZIP archive for analysts."""
    return diagnostic_export_route_response(
        cache_store=current_app.cache_store,
        history_store=current_app.history_store,
        config_store_factory=ConfigStore,
        failure_logger=logger,
    )
