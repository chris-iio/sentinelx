"""Analysis routes: home page and IOC analysis endpoint."""

from flask import (
    current_app, flash, redirect, render_template, request, url_for,
)

from app import limiter
from app.json_utils import encode_json_object
from app.pipeline.extractor import run_pipeline
from app.pipeline.models import IOCType
from app.text_utils import has_non_whitespace

from . import bp
from ._helpers import (
    _group_iocs_for_template,
    _ioc_template_context,
    _online_fanout_diagnostics,
    _online_limits_from_config,
    _setup_orchestrator,
)

_PROVIDER_COUNT_IOC_TYPES = (
    IOCType.IPV4,
    IOCType.IPV6,
    IOCType.DOMAIN,
    IOCType.URL,
    IOCType.MD5,
    IOCType.SHA1,
    IOCType.SHA256,
    IOCType.EMAIL,
)


def _provider_counts_json(registry) -> str:
    """Return provider-count metadata without allocating provider lists."""
    provider_counts: dict[str, int] = {}
    for ioc_type in _PROVIDER_COUNT_IOC_TYPES:
        provider_counts[ioc_type.value] = registry.provider_count_for_type(ioc_type)
    return encode_json_object(provider_counts)


def _provider_coverage(registry, configured=None) -> dict[str, int]:
    """Return registered/configured provider coverage without copying all providers."""
    registered_count = registry.registered_count()
    configured_providers = registry.configured() if configured is None else configured
    configured_count = len(configured_providers)
    return {
        "registered": registered_count,
        "configured": configured_count,
        "needs_key": registered_count - configured_count,
    }


def _enrichable_count(iocs, registry) -> int:
    """Return total provider fanout while counting each IOC type once."""
    counts_by_type: dict[IOCType, int] = {}
    total = 0
    for ioc in iocs:
        ioc_type = ioc.type
        if ioc_type not in counts_by_type:
            counts_by_type[ioc_type] = registry.provider_count_for_type(ioc_type)
        total += counts_by_type[ioc_type]
    return total


def _recent_analyses_context(limit: int = 4) -> dict:
    """Return fail-open recent-analysis template context for the intake page."""
    try:
        recent_analyses = current_app.history_store.list_recent(limit=limit)
    except Exception as exc:  # pragma: no cover - exercised through the route
        current_app.logger.warning(
            "Recent history lookup failed for index page: %s",
            type(exc).__name__,
        )
        return {"recent_analyses": [], "recent_analyses_unavailable": True}

    return {
        "recent_analyses": recent_analyses,
        "recent_analyses_unavailable": False,
    }


@bp.route("/")
@limiter.limit("60 per minute")
def index():
    """Home page — shows the IOC paste form and recent analysis summaries."""
    return render_template("index.html", **_recent_analyses_context(limit=4))


@bp.route("/analyze", methods=["POST"])
@limiter.limit("10 per minute")
def analyze():
    """IOC analysis endpoint.

    Offline mode: extract IOCs and render results.
    Online mode: extract, launch background enrichment, render with job_id.
    """
    text = request.form.get("text", "")
    mode = request.form.get("mode", "offline")

    if not has_non_whitespace(text):
        return render_template(
            "index.html",
            error="No input provided.",
            **_recent_analyses_context(limit=4),
        )

    iocs = run_pipeline(text)
    total_count = len(iocs)

    template_extras: dict = {}
    if mode == "online" and iocs:
        registry = current_app.registry
        configured_providers = registry.configured()

        if not configured_providers:
            flash(
                "Please configure at least one provider API key before using online mode",
                "warning",
            )
            return redirect(url_for("main.settings_get"))

        max_iocs, max_dispatches = _online_limits_from_config()
        fanout_diagnostics = _online_fanout_diagnostics(
            iocs,
            registry,
            max_iocs=max_iocs,
            max_dispatches=max_dispatches,
        )
        if not fanout_diagnostics["allowed"]:
            current_app.logger.warning(
                "Online enrichment rejected by admission guard: iocs=%s dispatches=%s limits=%s/%s",
                fanout_diagnostics["ioc_count"],
                fanout_diagnostics["dispatch_count"],
                fanout_diagnostics["max_iocs"],
                fanout_diagnostics["max_dispatches"],
            )
            template_extras = {
                "online_limit_diagnostics": fanout_diagnostics,
                "provider_counts": _provider_counts_json(registry),
                "provider_coverage": _provider_coverage(registry, configured_providers),
            }
        else:
            job_id, _, registry = _setup_orchestrator(
                iocs, text, mode, current_app.history_store, configured_providers,
            )

            template_extras = {
                "job_id": job_id,
                "enrichable_count": fanout_diagnostics["dispatch_count"],
                "provider_counts": _provider_counts_json(registry),
                "provider_coverage": _provider_coverage(registry, configured_providers),
            }

    return render_template(
        "results.html",
        mode=mode,
        **_ioc_template_context(iocs),
        **template_extras,
    )
