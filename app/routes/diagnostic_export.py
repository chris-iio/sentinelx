"""Diagnostic export route response helpers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from flask import Response

from app.diagnostics import assemble_diagnostic_bundle, build_default_diagnostic_sources
from app.time_utils import utc_iso, utc_now

DIAGNOSTIC_EXPORT_FAILURE_BODY = "Diagnostic export failed. Check server logs."


@dataclass(frozen=True, slots=True)
class DiagnosticExportHttpResponse:
    """Diagnostic export route response before Flask materializes it."""

    body: bytes | str
    status: int = 200
    mimetype: str = "application/zip"
    headers: dict[str, str] | None = None


def apply_diagnostic_export_http_response(
    result: DiagnosticExportHttpResponse,
    *,
    response_factory: Callable[..., Any] = Response,
) -> Any:
    """Apply a diagnostic export response decision through Flask."""
    return response_factory(
        result.body,
        status=result.status,
        mimetype=result.mimetype,
        headers=result.headers,
    )


def diagnostic_export_response(
    *,
    timestamp: datetime,
    config_store: object,
    cache_store: object,
    history_store: object,
) -> DiagnosticExportHttpResponse:
    """Build the analyst diagnostic ZIP response for a route request."""
    generated_at = utc_iso(timestamp)
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
    filename = f"sentinelx-diagnostic-{timestamp.date().isoformat()}.zip"
    return DiagnosticExportHttpResponse(
        bundle.archive_bytes,
        mimetype="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Diagnostic-Sources": str(bundle.summary["source_count"]),
        },
    )


def diagnostic_export_route_response(
    *,
    cache_store: object,
    history_store: object,
    timestamp: datetime | None = None,
    now_factory: Callable[[], datetime] | None = None,
    config_store_factory: Callable[[], object],
    failure_logger: object,
) -> Response:
    """Build a diagnostic export route response with bounded failure handling."""
    resolved_now_factory = utc_now if now_factory is None else now_factory
    export_timestamp = timestamp if timestamp is not None else resolved_now_factory()
    config_store = config_store_factory()
    try:
        return apply_diagnostic_export_http_response(
            diagnostic_export_response(
                timestamp=export_timestamp,
                config_store=config_store,
                cache_store=cache_store,
                history_store=history_store,
            )
        )
    except Exception:  # noqa: BLE001 - export failures must be bounded for analysts.
        failure_logger.error("Diagnostic export assembly failed", exc_info=True)  # type: ignore[attr-defined]
        return apply_diagnostic_export_http_response(diagnostic_export_failure_response())


def diagnostic_export_failure_response() -> DiagnosticExportHttpResponse:
    """Return the bounded analyst-facing diagnostic export failure response."""
    return DiagnosticExportHttpResponse(
        DIAGNOSTIC_EXPORT_FAILURE_BODY,
        status=500,
        mimetype="text/plain",
    )
