"""Pure API health-check helpers."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.health_contract import build_health_payload
from .json_results import JsonResult, apply_json_result


def health_check_ok(detail: str = "ok") -> dict[str, str]:
    """Return a normalized healthy check result."""
    return {"status": "ok", "detail": detail}


def health_check_degraded(exc: Exception) -> dict[str, str]:
    """Return a bounded degraded check without leaking paths or secrets."""
    return {"status": "degraded", "detail": exc.__class__.__name__}


def registry_health_detail(registry: Any) -> str:
    """Return configured/registered provider health detail from direct counts."""
    configured_count = registry.configured_count()
    registered_count = registry.registered_count()
    return f"{configured_count}/{registered_count} providers configured"


def _cache_health_detail(cache_store: Any) -> str:
    cache_store.stats()
    return "ok"


def _history_health_detail(history_store: Any) -> str:
    history_store.list_recent(limit=1)
    return "ok"


def _probe_health_check(
    checks: dict[str, dict[str, str]],
    name: str,
    detail_probe: Callable[[], str],
    app_logger: Any,
) -> None:
    try:
        checks[name] = health_check_ok(detail_probe())
    except Exception as exc:  # pragma: no cover - exercised by route tests
        app_logger.warning("Health %s check failed: %s", name, exc.__class__.__name__)
        checks[name] = health_check_degraded(exc)


def build_api_health_checks(
    *,
    cache_store: Any,
    history_store: Any,
    registry: Any,
    app_logger: Any,
) -> dict[str, dict[str, str]]:
    """Probe local dependencies and return secret-free health check rows."""
    checks: dict[str, dict[str, str]] = {}

    _probe_health_check(
        checks, "cache", lambda: _cache_health_detail(cache_store), app_logger
    )
    _probe_health_check(
        checks, "history", lambda: _history_health_detail(history_store), app_logger
    )
    _probe_health_check(
        checks, "registry", lambda: registry_health_detail(registry), app_logger
    )

    return checks


def api_health_result(
    *,
    cache_store: Any,
    history_store: Any,
    registry: Any,
    app_logger: Any,
) -> JsonResult:
    """Return the health contract payload/status for the current app."""
    return JsonResult(
        build_health_payload(
            build_api_health_checks(
                cache_store=cache_store,
                history_store=history_store,
                registry=registry,
                app_logger=app_logger,
            )
        ),
        200,
    )


def api_health_route_response(
    *,
    cache_store: Any,
    history_store: Any,
    registry: Any,
    app_logger: Any,
    jsonify_response: Callable[[dict[str, Any]], Any],
) -> Any:
    """Resolve and apply the API health response for route dependencies."""
    return apply_json_result(
        api_health_result(
            cache_store=cache_store,
            history_store=history_store,
            registry=registry,
            app_logger=app_logger,
        ),
        jsonify_response=jsonify_response,
    )
