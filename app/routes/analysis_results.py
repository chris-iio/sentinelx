"""Template context helpers for analysis result routes."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from app.pipeline.models import IOC

from .analysis_modes import ANALYSIS_MODE_ONLINE
from .analysis_workflow import (
    ANALYSIS_ERROR_EMPTY_TEXT,
    ANALYSIS_ERROR_INVALID_MODE,
    OnlineStartDecision,
    analysis_request_values,
    build_analysis_intake,
    start_online_analysis,
)
from .browser_responses import FlashRedirect, apply_flash_redirect
from .ioc_payloads import _ioc_template_context
from .online import _log_online_limit_rejection
from .provider_metadata import provider_counts_json, provider_coverage
from .template_results import TemplateResult, apply_template_result


@dataclass(frozen=True, slots=True)
class BrowserAnalyzeResult:
    """Browser analyze route response decision before Flask renders it."""

    template_name: str | None = None
    context: dict[str, object] | None = None
    status: int = 200
    flash_message: str | None = None
    flash_category: str | None = None
    redirect_endpoint: str | None = None


def apply_browser_analyze_result(
    result: BrowserAnalyzeResult,
    *,
    flash_message: Callable[[str, str], None],
    redirect_to: Callable[[str], Any],
    endpoint_url: Callable[[str], str],
    render_template: Callable[..., Any],
) -> Any:
    """Apply a browser analyze result through Flask primitives."""
    if result.redirect_endpoint is not None:
        return apply_flash_redirect(
            FlashRedirect(
                result.redirect_endpoint,
                result.flash_message,
                result.flash_category,
            ),
            flash_message=flash_message,
            redirect_to=redirect_to,
            resolve_url=endpoint_url,
        )
    return apply_template_result(
        TemplateResult(result.template_name, result.context or {}, result.status),
        render_template=render_template,
    )


def browser_analyze_route_response(
    values: Mapping[str, object],
    *,
    recent_context: Callable[[], dict[str, object]],
    has_content: Callable[[str], bool],
    extract_iocs: Callable[[str], list[IOC]],
    history_store: object,
    registry: object,
    cache_store: object,
    online_limits: tuple[int, int] | None,
    app_logger: object,
    setup_orchestrator: Callable[..., str],
    flash_message: Callable[[str, str], None],
    redirect_to: Callable[[str], Any],
    endpoint_url: Callable[[str], str],
    render_template: Callable[..., Any],
) -> Any:
    """Resolve and apply the browser analyze response for route dependencies."""
    return apply_browser_analyze_result(
        browser_analyze_result(
            values,
            recent_context=recent_context,
            has_content=has_content,
            extract_iocs=extract_iocs,
            history_store=history_store,
            registry=registry,
            cache_store=cache_store,
            online_limits=online_limits,
            app_logger=app_logger,
            setup_orchestrator=setup_orchestrator,
        ),
        flash_message=flash_message,
        redirect_to=redirect_to,
        endpoint_url=endpoint_url,
        render_template=render_template,
    )


def recent_analyses_context(
    history_store: object,
    app_logger: object,
    *,
    limit: int = 4,
) -> dict[str, object]:
    """Return fail-open recent-analysis template context for the intake page."""
    try:
        recent_analyses = history_store.list_recent(limit=limit)  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - exercised through route tests
        app_logger.warning(  # type: ignore[attr-defined]
            "Recent history lookup failed for index page: %s",
            type(exc).__name__,
        )
        return {"recent_analyses": [], "recent_analyses_unavailable": True}

    return {
        "recent_analyses": recent_analyses,
        "recent_analyses_unavailable": False,
    }


def index_page_result(
    history_store: object,
    app_logger: object,
    *,
    limit: int = 4,
) -> TemplateResult:
    """Return the index page render decision with recent-analysis context."""
    return TemplateResult(
        "index.html",
        recent_analyses_context(history_store, app_logger, limit=limit),
        200,
    )


def index_page_route_response(
    history_store: object,
    app_logger: object,
    *,
    render_template: Callable[..., Any],
    limit: int = 4,
) -> Any:
    """Apply the index page render decision for route-supplied dependencies."""
    return apply_template_result(
        index_page_result(history_store, app_logger, limit=limit),
        render_template=render_template,
    )


def online_result_template_extras(start: OnlineStartDecision) -> dict[str, object]:
    """Return Online-mode extras for the browser analysis results template."""
    registry = start.registry
    configured_providers = start.admission.configured_providers
    fanout_diagnostics = start.fanout_diagnostics
    extras: dict[str, object] = {
        "provider_counts": provider_counts_json(registry),
        "provider_coverage": provider_coverage(registry, configured_providers),
    }

    if start.rejected_by_limit and fanout_diagnostics is not None:
        extras["online_limit_diagnostics"] = fanout_diagnostics
        return extras

    extras["job_id"] = start.job_id
    if fanout_diagnostics is not None:
        extras["enrichable_count"] = fanout_diagnostics["dispatch_count"]
    return extras


def browser_analyze_result(
    values: Mapping[str, object],
    *,
    recent_context: Callable[[], dict[str, object]],
    has_content: Callable[[str], bool],
    extract_iocs: Callable[[str], list[IOC]],
    history_store: object,
    registry: object,
    cache_store: object,
    online_limits: tuple[int, int] | None,
    app_logger: object,
    setup_orchestrator: Callable[..., tuple[str, object, object]],
    start_online: Callable[..., OnlineStartDecision] = start_online_analysis,
) -> BrowserAnalyzeResult:
    """Return the browser analyze render/redirect decision for submitted form values."""
    request_values = analysis_request_values(values)
    intake = build_analysis_intake(
        text=request_values.text,
        mode=request_values.mode,
        has_content=has_content,
        extract_iocs=extract_iocs,
    )

    if intake.error == ANALYSIS_ERROR_INVALID_MODE:
        return BrowserAnalyzeResult(
            template_name="index.html",
            context={"error": "Invalid mode selected.", **recent_context()},
            status=400,
        )

    if intake.error == ANALYSIS_ERROR_EMPTY_TEXT:
        return BrowserAnalyzeResult(
            template_name="index.html",
            context={"error": "No input provided.", **recent_context()},
        )

    iocs = intake.iocs
    template_extras: dict[str, object] = {}
    if intake.mode == ANALYSIS_MODE_ONLINE and iocs:
        start = start_online(
            iocs=iocs,
            text=intake.text,
            mode=intake.mode,
            history_store=history_store,
            registry=registry,
            cache_store=cache_store,
            online_limits=online_limits,
            setup_orchestrator=setup_orchestrator,
        )

        if not start.has_configured_providers:
            return BrowserAnalyzeResult(
                flash_message=(
                    "Please configure at least one provider API key before using online mode"
                ),
                flash_category="warning",
                redirect_endpoint="main.settings_get",
            )

        fanout_diagnostics = start.fanout_diagnostics
        if start.rejected_by_limit and fanout_diagnostics is not None:
            _log_online_limit_rejection(
                fanout_diagnostics,
                app_logger=app_logger,
                surface="html",
            )
        template_extras = online_result_template_extras(start)

    return BrowserAnalyzeResult(
        template_name="results.html",
        context={
            "mode": intake.mode,
            **_ioc_template_context(iocs),
            **template_extras,
        },
    )
