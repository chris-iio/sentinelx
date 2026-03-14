"""Application routes.

Flask blueprint wiring the offline IOC extraction pipeline to the web UI,
and the online enrichment pipeline via background threads.

Routes:
    GET  /          — renders index.html (paste form)
    POST /analyze   — runs pipeline; offline renders results, online launches enrichment
    GET  /settings  — renders settings.html (multi-provider API key forms)
    POST /settings  — saves provider API key via ConfigStore, redirects back
    GET  /enrichment/status/<job_id> — returns JSON enrichment progress for polling
    GET  /ioc/<ioc_type>/<path:ioc_value> — renders IOC detail page with tabbed results

Security:
    - SEC-16: ALLOWED_API_HOSTS established in config; enforced by each adapter before calls
    - No outbound network calls in offline mode (UI-02)
    - Input size capped by MAX_CONTENT_LENGTH before route runs (SEC-12)
    - CSRF token validated by Flask-WTF on all POST requests (SEC-10)
    - Host header validated by TRUSTED_HOSTS middleware (SEC-11)
    - Background enrichment runs in daemon thread — does not block Flask (Pitfall 4)
"""

import json
import uuid
from collections import OrderedDict
from threading import Lock, Thread

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, url_for

from app import limiter
from app.cache.store import CacheStore
from app.enrichment.config_store import ConfigStore
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.orchestrator import EnrichmentOrchestrator
from app.enrichment.setup import PROVIDER_INFO, build_registry
from app.pipeline.extractor import run_pipeline
from app.pipeline.models import IOCType, group_by_type

bp = Blueprint("main", __name__)

# Module-level registry mapping job_id -> EnrichmentOrchestrator instance.
# Allows the polling endpoint to look up the orchestrator for a given job.
# SEC-18: Bounded OrderedDict with LRU eviction to prevent memory exhaustion.
_MAX_ORCHESTRATORS = 200
_orchestrators: OrderedDict[str, EnrichmentOrchestrator] = OrderedDict()
_orch_lock = Lock()


def _mask_key(key: str | None) -> str | None:
    """Return key with all but the last 4 characters replaced by asterisks.

    Returns None if key is None or shorter than 4 characters (never reveal partial keys).
    """
    if not key or len(key) <= 4:
        return None
    return "*" * (len(key) - 4) + key[-4:]


def _serialize_result(
    r: EnrichmentResult | EnrichmentError,
    cached_markers: dict[str, str] | None = None,
) -> dict:
    """Serialize an enrichment result or error to a JSON-safe dict.

    Used by the polling endpoint to return incremental results to the browser.
    If cached_markers is provided, adds 'cached_at' for cache-served results.
    """
    if isinstance(r, EnrichmentResult):
        d: dict = {
            "type": "result",
            "ioc_value": r.ioc.value,
            "ioc_type": r.ioc.type.value,
            "provider": r.provider,
            "verdict": r.verdict,
            "detection_count": r.detection_count,
            "total_engines": r.total_engines,
            "scan_date": r.scan_date,
            "raw_stats": r.raw_stats,
        }
        if cached_markers is not None:
            cache_key = r.ioc.value + "|" + r.provider
            cached_at = cached_markers.get(cache_key)
            if cached_at:
                d["cached_at"] = cached_at
        return d
    return {
        "type": "error",
        "ioc_value": r.ioc.value,
        "ioc_type": r.ioc.type.value,
        "provider": r.provider,
        "error": r.error,
    }


@bp.route("/")
@limiter.limit("60 per minute")
def index():
    """Home page — shows the IOC paste form."""
    return render_template("index.html")


@bp.route("/analyze", methods=["POST"])
@limiter.limit("10 per minute")
def analyze():
    """IOC analysis endpoint.

    Reads analyst text from the POST body, runs the extraction pipeline.

    Offline mode (UI-02): no outbound network calls are made.
    Online mode: checks for configured API key (redirects to /settings if missing),
    then runs pipeline and launches background enrichment via EnrichmentOrchestrator.
    Returns results page immediately with job_id for polling.
    """
    text = request.form.get("text", "")
    mode = request.form.get("mode", "offline")

    if not text.strip():
        return render_template("index.html", error="No input provided.")

    iocs = run_pipeline(text)
    grouped = group_by_type(iocs)
    total_count = len(iocs)

    # Online mode — launch background enrichment
    template_extras: dict = {}
    if mode == "online":
        config_store = ConfigStore()
        allowed_hosts = current_app.config.get("ALLOWED_API_HOSTS", [])
        registry = build_registry(allowed_hosts=allowed_hosts, config_store=config_store)

        if not registry.configured():
            flash(
                "Please configure at least one provider API key before using online mode",
                "warning",
            )
            return redirect(url_for("main.settings_get"))

        job_id = uuid.uuid4().hex
        cache = CacheStore()
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

        thread = Thread(
            target=orchestrator.enrich_all,
            args=(job_id, iocs),
            daemon=True,
        )
        thread.start()

        enrichable_count = sum(
            len(registry.providers_for_type(ioc.type))
            for ioc in iocs
        )
        provider_counts = json.dumps({
            ioc_type.value: registry.provider_count_for_type(ioc_type)
            for ioc_type in IOCType
            if ioc_type != IOCType.CVE
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


@bp.route("/settings", methods=["GET"])
@limiter.limit("30 per minute")
def settings_get():
    """Settings page — shows per-provider API key configuration forms.

    Builds a list of provider metadata dicts (from PROVIDER_INFO) enriched with
    the current key status from ConfigStore. Each entry includes a masked_key
    (last 4 chars visible, rest asterisks) and a configured boolean.

    Template variable:
        providers: list[dict] — one entry per key-requiring provider, with keys:
            id, name, requires_key, signup_url, description, masked_key, configured
    """
    config_store = ConfigStore()
    providers_with_status = []
    for info in PROVIDER_INFO:
        pid = info["id"]
        if pid == "virustotal":
            key = config_store.get_vt_api_key()
        else:
            key = config_store.get_provider_key(pid)
        providers_with_status.append({
            **info,
            "masked_key": _mask_key(key),
            "configured": key is not None,
        })
    cache = CacheStore()
    cache_stats = cache.stats()
    cache_ttl = config_store.get_cache_ttl()
    return render_template(
        "settings.html",
        providers=providers_with_status,
        cache_stats=cache_stats,
        cache_ttl=cache_ttl,
    )


@bp.route("/settings", methods=["POST"])
@limiter.limit("10 per minute")
def settings_post():
    """Save a provider API key submitted via the settings form.

    Accepts a provider_id hidden field to identify which provider the key is for.
    Validates that both provider_id is known and api_key is non-empty, then saves
    via ConfigStore and redirects back to GET /settings with a flash message.

    VirusTotal uses the legacy set_vt_api_key() path; all others use set_provider_key().
    """
    provider_id = request.form.get("provider_id", "").strip()
    api_key = request.form.get("api_key", "").strip()

    if not api_key:
        flash("API key cannot be empty.", "error")
        return redirect(url_for("main.settings_get"))

    valid_ids = {p["id"] for p in PROVIDER_INFO}
    if provider_id not in valid_ids:
        flash("Unknown provider.", "error")
        return redirect(url_for("main.settings_get"))

    config_store = ConfigStore()
    if provider_id == "virustotal":
        config_store.set_vt_api_key(api_key)
    else:
        config_store.set_provider_key(provider_id, api_key)

    flash(f"API key saved for {provider_id}.", "success")
    return redirect(url_for("main.settings_get"))


@bp.route("/settings/cache/clear", methods=["POST"])
@limiter.limit("10 per minute")
def cache_clear():
    """Clear all cached enrichment results."""
    cache = CacheStore()
    cache.clear()
    flash("Cache cleared.", "success")
    return redirect(url_for("main.settings_get"))


@bp.route("/settings/cache/ttl", methods=["POST"])
@limiter.limit("10 per minute")
def cache_ttl_set():
    """Update cache TTL hours setting."""
    ttl_str = request.form.get("cache_ttl", "").strip()
    try:
        ttl = int(ttl_str)
        if ttl < 1:
            raise ValueError
    except (ValueError, TypeError):
        flash("TTL must be a positive integer.", "error")
        return redirect(url_for("main.settings_get"))
    config_store = ConfigStore()
    config_store.set_cache_ttl(ttl)
    flash(f"Cache TTL set to {ttl} hours.", "success")
    return redirect(url_for("main.settings_get"))


@bp.route("/ioc/<ioc_type>/<path:ioc_value>")
@limiter.limit("30 per minute")
def ioc_detail(ioc_type: str, ioc_value: str) -> str:
    """IOC detail page — shows all cached provider results for a single IOC.

    Uses a path converter (<path:ioc_value>) so URL IOCs containing slashes
    are captured correctly.

    Validates ioc_type against the IOCType enum; returns 404 for unknown types.
    Reads provider results from CacheStore (no TTL — detail page shows all history).
    Builds graph_nodes and graph_edges for the SVG relationship graph.
    """
    valid_types = {t.value for t in IOCType}
    if ioc_type not in valid_types:
        abort(404)

    cache = CacheStore()
    provider_results = cache.get_all_for_ioc(ioc_value, ioc_type)

    # Build graph data: central IOC node + one node per provider
    graph_nodes = [
        {"id": "ioc", "label": ioc_value[:20], "verdict": "ioc", "role": "ioc"}
    ]
    graph_edges = []
    for result in provider_results:
        provider = result.get("provider", "unknown")
        verdict = result.get("verdict", "no_data")
        graph_nodes.append({
            "id": provider,
            "label": provider[:12],
            "verdict": verdict,
            "role": "provider",
        })
        graph_edges.append({"from": "ioc", "to": provider, "verdict": verdict})

    return render_template(
        "ioc_detail.html",
        ioc_value=ioc_value,
        ioc_type=ioc_type,
        provider_results=provider_results,
        graph_nodes=graph_nodes,
        graph_edges=graph_edges,
    )


@bp.route("/enrichment/status/<job_id>", methods=["GET"])
@limiter.limit("120 per minute")
def enrichment_status(job_id: str):
    """Return the current enrichment progress for a job as JSON.

    Used by the browser to poll for incremental enrichment results after
    submitting in online mode. The job_id is returned in the results page.

    Returns:
        200 JSON with total, done, complete, and serialized results list.
        404 JSON with error if the job is not found (evicted or never created).

    Each serialized result includes:
        - type: "result" or "error"
        - provider: TI provider name (ENRC-05)
        - verdict: "malicious" | "clean" | "no_data" (ENRC-05)
        - scan_date: ISO8601 timestamp or None (ENRC-05)
    """
    with _orch_lock:
        orchestrator = _orchestrators.get(job_id)
    if orchestrator is None:
        return jsonify({"error": "job not found"}), 404

    status = orchestrator.get_status(job_id)
    if status is None:
        return jsonify({"error": "job not found"}), 404

    cached_markers = orchestrator.cached_markers
    serialized_results = [
        _serialize_result(r, cached_markers) for r in status["results"]
    ]

    return jsonify(
        {
            "total": status["total"],
            "done": status["done"],
            "complete": status["complete"],
            "results": serialized_results,
        }
    )
