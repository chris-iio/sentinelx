"""API analyze request workflow helpers."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from app.pipeline.models import IOC

from .analysis_modes import ANALYSIS_MODE_ONLINE
from .analysis_workflow import (
    ANALYSIS_ERROR_EMPTY_TEXT,
    ANALYSIS_ERROR_INVALID_MODE,
    analysis_request_values,
    build_analysis_intake,
    start_online_analysis,
)
from .ioc_payloads import (
    api_analysis_response_payload,
    api_invalid_mode_error_payload,
    api_json_required_error_payload,
    api_no_provider_error_payload,
    api_text_required_error_payload,
)
from .json_results import JsonResult, apply_json_result
from .json_values import json_mapping_payload
from .online import _log_online_limit_rejection, _online_limit_response


def api_analyze_route_response(
    request_obj: object,
    *,
    has_content: Callable[[str], bool],
    extract_iocs: Callable[[str], list[IOC]],
    history_store: object,
    registry: object,
    cache_store: object,
    online_limits: tuple[int, int] | None,
    app_logger: object,
    jsonify_response: Callable[[dict[str, object]], Any],
) -> Any:
    """Decode, resolve, and apply an API analyze response for route dependencies."""
    return apply_json_result(
        api_analyze_result(
            json_mapping_payload(request_obj),
            has_content=has_content,
            extract_iocs=extract_iocs,
            history_store=history_store,
            registry=registry,
            cache_store=cache_store,
            online_limits=online_limits,
            app_logger=app_logger,
        ),
        jsonify_response=jsonify_response,
    )


def api_analyze_result(
    data: Mapping[str, object] | None,
    *,
    has_content: Callable[[str], bool],
    extract_iocs: Callable[[str], list[IOC]],
    history_store: object,
    registry: object,
    cache_store: object,
    online_limits: tuple[int, int] | None,
    app_logger: object,
    start_online: Callable[..., object] = start_online_analysis,
) -> JsonResult:
    """Return the API analyze payload/status for a decoded JSON request."""
    if data is None:
        return JsonResult(api_json_required_error_payload(), 400)

    request_values = analysis_request_values(data)
    intake = build_analysis_intake(
        text=request_values.text,
        mode=request_values.mode,
        has_content=has_content,
        extract_iocs=extract_iocs,
    )
    if intake.error == ANALYSIS_ERROR_EMPTY_TEXT:
        return JsonResult(api_text_required_error_payload(), 400)
    if intake.error == ANALYSIS_ERROR_INVALID_MODE:
        return JsonResult(api_invalid_mode_error_payload(request_values.mode), 400)

    iocs = intake.iocs
    if not iocs:
        return JsonResult(api_analysis_response_payload(iocs, mode=intake.mode), 200)

    job_id: str | None = None
    if intake.mode == ANALYSIS_MODE_ONLINE:
        start = start_online(
            iocs=iocs,
            text=intake.text,
            mode=intake.mode,
            history_store=history_store,
            registry=registry,
            cache_store=cache_store,
            online_limits=online_limits,
        )

        if not start.has_configured_providers:
            return JsonResult(api_no_provider_error_payload(), 400)

        fanout_diagnostics = start.fanout_diagnostics
        if start.rejected_by_limit and fanout_diagnostics is not None:
            _log_online_limit_rejection(
                fanout_diagnostics,
                app_logger=app_logger,
                surface="api",
            )
            return JsonResult(_online_limit_response(fanout_diagnostics), 413)

        job_id = start.job_id

    return JsonResult(
        api_analysis_response_payload(iocs, mode=intake.mode, job_id=job_id),
        200,
    )
