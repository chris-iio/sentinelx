"""Application routes.

Flask blueprint wiring the offline IOC extraction pipeline to the web UI,
and the online enrichment pipeline via background threads.

Routes:
    GET  /          — renders index.html (paste form)
    POST /analyze   — runs pipeline; offline renders results, online launches enrichment
    GET  /settings  — renders settings.html (API key form)
    POST /settings  — saves VT API key via ConfigStore, redirects back
    GET  /enrichment/status/<job_id> — returns JSON enrichment progress for polling

Security:
    - SEC-16: ALLOWED_API_HOSTS established in config; enforced by VTAdapter before calls
    - No outbound network calls in offline mode (UI-02)
    - Input size capped by MAX_CONTENT_LENGTH before route runs (SEC-12)
    - CSRF token validated by Flask-WTF on all POST requests (SEC-10)
    - Host header validated by TRUSTED_HOSTS middleware (SEC-11)
    - Background enrichment runs in daemon thread — does not block Flask (Pitfall 4)
"""
import uuid
from threading import Thread

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for

from app.enrichment.adapters.virustotal import ENDPOINT_MAP
from app.enrichment.adapters.virustotal import VTAdapter
from app.enrichment.config_store import ConfigStore
from app.enrichment.orchestrator import EnrichmentOrchestrator
from app.pipeline.extractor import run_pipeline
from app.pipeline.models import group_by_type

bp = Blueprint("main", __name__)

# Module-level registry mapping job_id -> EnrichmentOrchestrator instance.
# Allows the polling endpoint to look up the orchestrator for a given job.
# This dict is shared across threads; orchestrators are written once then only read.
_orchestrators: dict[str, EnrichmentOrchestrator] = {}


def _mask_key(key: str | None) -> str | None:
    """Return key with all but the last 4 characters replaced by asterisks.

    Returns None if key is None or shorter than 4 characters (never reveal partial keys).
    """
    if not key or len(key) <= 4:
        return None
    return "*" * (len(key) - 4) + key[-4:]


@bp.route("/")
def index():
    """Home page — shows the IOC paste form."""
    return render_template("index.html")


@bp.route("/analyze", methods=["POST"])
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

    if mode == "online":
        config_store = ConfigStore()
        api_key = config_store.get_vt_api_key()

        if not api_key:
            flash(
                "Please configure your VirusTotal API key before using online mode",
                "warning",
            )
            return redirect(url_for("main.settings_get"))

        job_id = uuid.uuid4().hex

        allowed_hosts = current_app.config.get("ALLOWED_API_HOSTS", [])
        adapter = VTAdapter(api_key=api_key, allowed_hosts=allowed_hosts)
        orchestrator = EnrichmentOrchestrator(adapter)

        _orchestrators[job_id] = orchestrator

        thread = Thread(
            target=orchestrator.enrich_all,
            args=(job_id, iocs),
            daemon=True,
        )
        thread.start()

        enrichable_count = sum(1 for ioc in iocs if ioc.type in ENDPOINT_MAP)

        if total_count == 0:
            return render_template(
                "results.html",
                grouped={},
                mode=mode,
                total_count=0,
                no_results=True,
                job_id=job_id,
                enrichable_count=enrichable_count,
            )

        return render_template(
            "results.html",
            grouped=grouped,
            mode=mode,
            total_count=total_count,
            no_results=False,
            job_id=job_id,
            enrichable_count=enrichable_count,
        )

    # Offline mode — no enrichment
    if total_count == 0:
        return render_template(
            "results.html",
            grouped={},
            mode=mode,
            total_count=0,
            no_results=True,
        )

    return render_template(
        "results.html",
        grouped=grouped,
        mode=mode,
        total_count=total_count,
        no_results=False,
    )


@bp.route("/settings", methods=["GET"])
def settings_get():
    """Settings page — shows the API key configuration form.

    Reads the current API key from ConfigStore and masks all but the last
    4 characters for display, so analysts can confirm a key is saved without
    exposing the full value.
    """
    config_store = ConfigStore()
    current_key = config_store.get_vt_api_key()
    masked_key = _mask_key(current_key)
    return render_template("settings.html", masked_key=masked_key)


@bp.route("/settings", methods=["POST"])
def settings_post():
    """Save the VT API key submitted via the settings form.

    Validates that the submitted key is a non-empty string, then saves it
    via ConfigStore and redirects back to GET /settings with a success flash.
    """
    api_key = request.form.get("api_key", "").strip()

    if not api_key:
        flash("API key cannot be empty.", "error")
        return redirect(url_for("main.settings_get"))

    config_store = ConfigStore()
    config_store.set_vt_api_key(api_key)

    flash("API key saved successfully.", "success")
    return redirect(url_for("main.settings_get"))


@bp.route("/enrichment/status/<job_id>", methods=["GET"])
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
    orchestrator = _orchestrators.get(job_id)
    if orchestrator is None:
        return jsonify({"error": "job not found"}), 404

    status = orchestrator.get_status(job_id)
    if status is None:
        return jsonify({"error": "job not found"}), 404

    serialized_results = []
    for r in status["results"]:
        from app.enrichment.models import EnrichmentResult, EnrichmentError

        if isinstance(r, EnrichmentResult):
            serialized_results.append(
                {
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
            )
        elif isinstance(r, EnrichmentError):
            serialized_results.append(
                {
                    "type": "error",
                    "ioc_value": r.ioc.value,
                    "ioc_type": r.ioc.type.value,
                    "provider": r.provider,
                    "error": r.error,
                }
            )

    return jsonify(
        {
            "total": status["total"],
            "done": status["done"],
            "complete": status["complete"],
            "results": serialized_results,
        }
    )
