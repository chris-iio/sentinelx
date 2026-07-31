"""Analysis routes: home page and IOC analysis endpoint."""

from flask import (
    current_app, flash, redirect, render_template, request, url_for,
)

from app import limiter
from app.pipeline.extractor import run_pipeline
from app.text_utils import has_non_whitespace

from . import bp
from .analysis_results import (
    browser_analyze_route_response,
    index_page_route_response,
    recent_analyses_context,
)
from .enrichment_jobs import _setup_orchestrator
from . import online


@bp.route("/")
@limiter.limit("60 per minute")
def index():
    """Home page — shows the IOC paste form and recent analysis summaries."""
    return index_page_route_response(
        current_app.history_store,
        current_app.logger,
        render_template=render_template,
        limit=4,
    )


@bp.route("/analyze", methods=["POST"])
@limiter.limit("10 per minute")
def analyze():
    """IOC analysis endpoint.

    Offline mode: extract IOCs and render results.
    Online mode: extract, launch background enrichment, render with job_id.
    """
    return browser_analyze_route_response(
        request.form,
        recent_context=lambda: recent_analyses_context(
            current_app.history_store,
            current_app.logger,
            limit=4,
        ),
        has_content=has_non_whitespace,
        extract_iocs=run_pipeline,
        history_store=current_app.history_store,
        registry=current_app.registry,
        cache_store=current_app.cache_store,
        online_limits=online._online_limits_from_config(current_app.config),
        app_logger=current_app.logger,
        setup_orchestrator=_setup_orchestrator,
        flash_message=flash,
        redirect_to=redirect,
        endpoint_url=url_for,
        render_template=render_template,
    )
