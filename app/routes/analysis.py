"""Analysis routes: home page and IOC analysis endpoint."""

import json
import uuid

from flask import (
    current_app, flash, redirect, render_template, request, url_for,
)

from app import limiter
from app.enrichment.config_store import ConfigStore
from app.enrichment.orchestrator import EnrichmentOrchestrator
from app.pipeline.extractor import run_pipeline
from app.pipeline.models import IOCType, group_by_type

from . import bp
from ._helpers import (
    _MAX_ORCHESTRATORS,
    _enrichment_pool,
    _orch_lock,
    _orchestrators,
    _run_enrichment_and_save,
)


@bp.route("/")
@limiter.limit("60 per minute")
def index():
    """Home page — shows the IOC paste form with recent analyses."""
    try:
        recent_analyses = current_app.history_store.list_recent(limit=10)
    except Exception:
        recent_analyses = []
    return render_template("index.html", recent_analyses=recent_analyses)


@bp.route("/analyze", methods=["POST"])
@limiter.limit("10 per minute")
def analyze():
    """IOC analysis endpoint.

    Offline mode: extract IOCs and render results.
    Online mode: extract, launch background enrichment, render with job_id.
    """
    text = request.form.get("text", "")
    mode = request.form.get("mode", "offline")

    if not text.strip():
        return render_template("index.html", error="No input provided.")

    iocs = run_pipeline(text)
    grouped = group_by_type(iocs)
    total_count = len(iocs)

    template_extras: dict = {}
    if mode == "online":
        registry = current_app.registry

        if not registry.configured():
            flash(
                "Please configure at least one provider API key before using online mode",
                "warning",
            )
            return redirect(url_for("main.settings_get"))

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

        type_providers = {
            ioc_type: registry.providers_for_type(ioc_type)
            for ioc_type in IOCType
            if ioc_type != IOCType.CVE
        }
        enrichable_count = sum(
            len(type_providers.get(ioc.type, []))
            for ioc in iocs
        )
        provider_counts = json.dumps({
            t.value: len(ps) for t, ps in type_providers.items()
        })
        provider_coverage = {
            "registered": len(registry.all()),
            "configured": len(registry.configured()),
            "needs_key": len(registry.all()) - len(registry.configured()),
        }
        template_extras = {
            "job_id": job_id,
            "enrichable_count": enrichable_count,
            "provider_counts": provider_counts,
            "provider_coverage": provider_coverage,
        }

    no_results = total_count == 0
    return render_template(
        "results.html",
        grouped={} if no_results else grouped,
        mode=mode,
        total_count=total_count,
        no_results=no_results,
        **template_extras,
    )
