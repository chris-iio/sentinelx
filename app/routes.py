"""Application routes.

Flask blueprint wiring the offline IOC extraction pipeline to the web UI.

Routes:
    GET  /          — renders index.html (paste form)
    POST /analyze   — runs pipeline, renders results.html

Security:
    - SEC-16: ALLOWED_API_HOSTS established in config (empty for Phase 1 — no outbound calls)
    - No outbound network calls in offline mode (UI-02)
    - Input size capped by MAX_CONTENT_LENGTH before route runs (SEC-12)
    - CSRF token validated by Flask-WTF on all POST requests (SEC-10)
    - Host header validated by TRUSTED_HOSTS middleware (SEC-11)
"""
from flask import Blueprint, render_template, request

from app.pipeline.extractor import run_pipeline
from app.pipeline.models import group_by_type

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    """Home page — shows the IOC paste form."""
    return render_template("index.html")


@bp.route("/analyze", methods=["POST"])
def analyze():
    """IOC analysis endpoint.

    Reads analyst text from the POST body, runs the offline extraction
    pipeline, and renders grouped results.

    Offline mode (UI-02): no outbound network calls are made here.
    Enrichment is Phase 2 — this route only calls run_pipeline().
    """
    text = request.form.get("text", "")
    mode = request.form.get("mode", "offline")

    if not text.strip():
        return render_template("index.html", error="No input provided.")

    iocs = run_pipeline(text)
    grouped = group_by_type(iocs)
    total_count = len(iocs)

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
