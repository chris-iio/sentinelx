"""Shared Online-mode admission helpers for browser and API analysis routes."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass

from flask import current_app

from app.pipeline.models import IOC

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class OnlineAdmission:
    """Shared Online-mode admission decision for HTML and JSON routes."""

    registry: object
    configured_providers: list[object]
    fanout_diagnostics: dict[str, object] | None

    @property
    def has_configured_providers(self) -> bool:
        return bool(self.configured_providers)

    @property
    def rejected_by_limit(self) -> bool:
        diagnostics = self.fanout_diagnostics
        return diagnostics is not None and not bool(diagnostics["allowed"])


def _online_limits_from_config(config: Mapping[str, object] | None = None) -> tuple[int, int]:
    """Return Online enrichment admission limits from app config."""
    resolved_config = _resolve_online_limit_config(config)
    return (
        int(resolved_config.get("ONLINE_MAX_IOCS", 50)),
        int(resolved_config.get("ONLINE_MAX_DISPATCHES", 200)),
    )


def _resolve_online_limit_config(
    config: Mapping[str, object] | None = None,
) -> Mapping[str, object]:
    """Return explicit Online limit config, falling back to current app config."""
    return current_app.config if config is None else config


def _online_fanout_diagnostics(
    iocs: list[IOC],
    registry: object,
    *,
    max_iocs: int,
    max_dispatches: int,
) -> dict[str, object]:
    """Return secret-free admission diagnostics for Online enrichment fan-out."""
    provider_counts_by_type: dict[str, int] = {}
    dispatch_count = 0

    for ioc in iocs:
        type_key = ioc.type.value
        if type_key not in provider_counts_by_type:
            try:
                provider_counts_by_type[type_key] = registry.provider_count_for_type(ioc.type)  # type: ignore[attr-defined]
            except Exception as exc:
                logger.warning(
                    "Online fanout provider-count lookup failed for %s: %s",
                    type_key,
                    exc.__class__.__name__,
                )
                provider_counts_by_type[type_key] = 0
        dispatch_count += provider_counts_by_type[type_key]

    ioc_count = len(iocs)
    over_ioc_limit = ioc_count > max_iocs
    over_dispatch_limit = dispatch_count > max_dispatches
    return {
        "ioc_count": ioc_count,
        "dispatch_count": dispatch_count,
        "max_iocs": max_iocs,
        "max_dispatches": max_dispatches,
        "over_ioc_limit": over_ioc_limit,
        "over_dispatch_limit": over_dispatch_limit,
        "allowed": not over_ioc_limit and not over_dispatch_limit,
        "provider_counts_by_type": provider_counts_by_type,
    }


def _online_limit_response(diagnostics: dict[str, object]) -> dict[str, object]:
    """Return a JSON-safe Online limit payload without IOC values or secrets."""
    return {
        "error": "Online enrichment limit exceeded. Reduce the submission or use offline mode.",
        "code": "online_limit_exceeded",
        "limits": {
            "max_iocs": diagnostics["max_iocs"],
            "max_dispatches": diagnostics["max_dispatches"],
        },
        "observed": {
            "ioc_count": diagnostics["ioc_count"],
            "dispatch_count": diagnostics["dispatch_count"],
        },
    }


def _log_online_limit_rejection(
    diagnostics: dict[str, object],
    *,
    app_logger: object,
    surface: str,
) -> None:
    """Log secret-free Online admission-limit rejection details."""
    prefix = "API online" if surface == "api" else "Online"
    app_logger.warning(  # type: ignore[attr-defined]
        "%s enrichment rejected by admission guard: iocs=%s dispatches=%s limits=%s/%s",
        prefix,
        diagnostics["ioc_count"],
        diagnostics["dispatch_count"],
        diagnostics["max_iocs"],
        diagnostics["max_dispatches"],
    )


def _online_admission(
    iocs: list[IOC],
    *,
    registry: object,
    configured_providers: list[object] | None = None,
    online_limits: tuple[int, int] | None = None,
) -> OnlineAdmission:
    """Return the shared Online enrichment admission decision.

    Routes keep their own response formatting, but the provider configuration
    check, limit lookup, and fan-out diagnostics stay in one backend path.
    """
    providers = (
        registry.configured()  # type: ignore[attr-defined]
        if configured_providers is None
        else configured_providers
    )
    if not providers:
        return OnlineAdmission(
            registry=registry,
            configured_providers=providers,
            fanout_diagnostics=None,
        )

    max_iocs, max_dispatches = (
        _online_limits_from_config() if online_limits is None else online_limits
    )
    return OnlineAdmission(
        registry=registry,
        configured_providers=providers,
        fanout_diagnostics=_online_fanout_diagnostics(
            iocs,
            registry,
            max_iocs=max_iocs,
            max_dispatches=max_dispatches,
        ),
    )
