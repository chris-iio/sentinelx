"""Safe backend runtime source composition for diagnostic exports.

This module only builds :class:`DiagnosticSource` descriptors.  It does not
assemble archives, register routes, read raw config files, or traverse the
filesystem.  Callers inject the runtime objects they want considered so tests
and future routes can stay explicit about which local state is inspected.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from . import runtime_payloads
from .policy import DIAGNOSTIC_SANITIZATION_POLICY
from .source_preparation import DiagnosticSource
from app.time_utils import utcnow_iso

DEFAULT_HISTORY_LIMIT = runtime_payloads.DEFAULT_HISTORY_LIMIT
HealthChecksProvider = runtime_payloads.HealthChecksProvider
JobDiagnosticsAccessor = runtime_payloads.JobDiagnosticsAccessor

_SOURCE_MAX_BYTES = DIAGNOSTIC_SANITIZATION_POLICY.runtime_source_max_bytes
_CONFIG_STORE_NOT_PROVIDED = "config_store_not_provided"
_CACHE_STORE_NOT_PROVIDED = "cache_store_not_provided"
_HISTORY_STORE_NOT_PROVIDED = "history_store_not_provided"
_JOB_ID_NOT_PROVIDED = "job_id_not_provided"
_JOB_DIAGNOSTICS_ACCESSOR_NOT_PROVIDED = "job_diagnostics_accessor_not_provided"


@dataclass(frozen=True, slots=True)
class _DefaultSourceContext:
    history_limit: int
    generated_at: str


def build_default_diagnostic_sources(
    *,
    config_store: Any | None = None,
    cache_store: Any | None = None,
    history_store: Any | None = None,
    history_limit: int = DEFAULT_HISTORY_LIMIT,
    health_checks: Mapping[str, Mapping[str, Any]] | HealthChecksProvider | None = None,
    job_id: str | None = None,
    job_diagnostics_accessor: JobDiagnosticsAccessor | None = None,
    generated_at: str | None = None,
) -> tuple[DiagnosticSource, ...]:
    """Return safe runtime diagnostic source descriptors.

    The returned descriptors are suitable for ``assemble_diagnostic_bundle`` and
    intentionally use dependency injection.  Missing optional runtime objects are
    represented as omitted sources so the manifest remains an explicit inventory
    of what was considered.
    """

    context = _default_source_context(history_limit=history_limit, generated_at=generated_at)

    return _default_runtime_sources(
        context=context,
        config_store=config_store,
        cache_store=cache_store,
        history_store=history_store,
        health_checks=health_checks,
        job_id=job_id,
        job_diagnostics_accessor=job_diagnostics_accessor,
    )


def _default_runtime_sources(
    *,
    context: _DefaultSourceContext,
    config_store: Any | None,
    cache_store: Any | None,
    history_store: Any | None,
    health_checks: Mapping[str, Mapping[str, Any]] | HealthChecksProvider | None,
    job_id: str | None,
    job_diagnostics_accessor: JobDiagnosticsAccessor | None,
) -> tuple[DiagnosticSource, ...]:
    return (
        _metadata_source(
            generated_at=context.generated_at,
            history_limit=context.history_limit,
            job_id_requested=bool(job_id),
            config_store=config_store,
            cache_store=cache_store,
            history_store=history_store,
            job_diagnostics_accessor=job_diagnostics_accessor,
        ),
        _config_secret_source(config_store),
        _cache_stats_source(cache_store),
        _recent_history_source(history_store, context.history_limit),
        _history_save_source(),
        _health_source(
            health_checks=health_checks,
            config_store=config_store,
            cache_store=cache_store,
            history_store=history_store,
        ),
        _orchestration_source(
            job_id=job_id,
            job_diagnostics_accessor=job_diagnostics_accessor,
        ),
    )


def _metadata_source(
    *,
    generated_at: str,
    history_limit: int,
    job_id_requested: bool,
    config_store: Any | None,
    cache_store: Any | None,
    history_store: Any | None,
    job_diagnostics_accessor: JobDiagnosticsAccessor | None,
) -> DiagnosticSource:
    return DiagnosticSource(
        source_id="diagnostic-export-metadata",
        name="Diagnostic export metadata",
        category="metadata",
        payload=_metadata_payload(
            generated_at=generated_at,
            history_limit=history_limit,
            job_id_requested=job_id_requested,
            config_store=config_store,
            cache_store=cache_store,
            history_store=history_store,
            job_diagnostics_accessor=job_diagnostics_accessor,
        ),
        relative_path="runtime/diagnostic-export-metadata.json",
        max_bytes=_SOURCE_MAX_BYTES,
    )


def _metadata_payload(
    *,
    generated_at: str,
    history_limit: int,
    job_id_requested: bool,
    config_store: Any | None,
    cache_store: Any | None,
    history_store: Any | None,
    job_diagnostics_accessor: JobDiagnosticsAccessor | None,
) -> dict[str, Any]:
    return {
        "schema": "sentinelx.diagnostic_sources.v1",
        "generated_at": generated_at,
        "history_limit": history_limit,
        "job_id_requested": job_id_requested,
        "runtime_objects": {
            "config_store": config_store is not None,
            "cache_store": cache_store is not None,
            "history_store": history_store is not None,
            "job_diagnostics_accessor": job_diagnostics_accessor is not None,
        },
    }


def _default_source_context(
    *,
    history_limit: int,
    generated_at: str | None,
) -> _DefaultSourceContext:
    return _DefaultSourceContext(
        history_limit=_bounded_limit(history_limit),
        generated_at=generated_at or _utcnow_iso(),
    )


def _runtime_source(
    *,
    source_id: str,
    name: str,
    category: str,
    collect: Callable[[], object],
    relative_path: str,
) -> DiagnosticSource:
    return DiagnosticSource(
        source_id=source_id,
        name=name,
        category=category,
        collect=collect,
        relative_path=relative_path,
        max_bytes=_SOURCE_MAX_BYTES,
    )


def _optional_runtime_source(
    *,
    dependency: Any | None,
    source_id: str,
    name: str,
    category: str,
    omitted_reason: str,
    collect: Callable[[Any], object],
    relative_path: str,
) -> DiagnosticSource:
    if dependency is None:
        return _omitted(source_id, name, category, omitted_reason)
    return _runtime_source(
        source_id=source_id,
        name=name,
        category=category,
        collect=_dependency_collector(dependency, collect),
        relative_path=relative_path,
    )


def _dependency_collector(
    dependency: Any,
    collect: Callable[[Any], object],
) -> Callable[[], object]:
    return lambda dependency=dependency: collect(dependency)


def _config_secret_source(config_store: Any | None) -> DiagnosticSource:
    return _optional_runtime_source(
        dependency=config_store,
        source_id="config-secret-inventory",
        name="Config secret inventory",
        category="config",
        omitted_reason=_CONFIG_STORE_NOT_PROVIDED,
        collect=runtime_payloads.config_secret_inventory_payload,
        relative_path="runtime/config-secret-inventory.json",
    )


def _cache_stats_source(cache_store: Any | None) -> DiagnosticSource:
    return _optional_runtime_source(
        dependency=cache_store,
        source_id="cache-stats",
        name="Cache statistics",
        category="cache",
        omitted_reason=_CACHE_STORE_NOT_PROVIDED,
        collect=runtime_payloads.cache_stats_payload,
        relative_path="runtime/cache-stats.json",
    )


def _recent_history_source(
    history_store: Any | None,
    history_limit: int,
) -> DiagnosticSource:
    return _optional_runtime_source(
        dependency=history_store,
        source_id="recent-history",
        name="Recent history summaries",
        category="history",
        omitted_reason=_HISTORY_STORE_NOT_PROVIDED,
        collect=lambda store, limit=history_limit: runtime_payloads.recent_history_payload(
            store,
            limit,
        ),
        relative_path="runtime/recent-history.json",
    )


def _orchestration_source(
    *,
    job_id: str | None,
    job_diagnostics_accessor: JobDiagnosticsAccessor | None,
) -> DiagnosticSource:
    if not job_id:
        return _omitted_orchestration_source(_JOB_ID_NOT_PROVIDED)
    if job_diagnostics_accessor is None:
        return _omitted_orchestration_source(_JOB_DIAGNOSTICS_ACCESSOR_NOT_PROVIDED)
    return _runtime_source(
        source_id="orchestration-diagnostics",
        name="Orchestration diagnostics",
        category="orchestrator",
        collect=lambda accessor=job_diagnostics_accessor, requested_job_id=job_id: (
            runtime_payloads.job_diagnostics_payload(accessor, requested_job_id)
        ),
        relative_path="runtime/orchestration-diagnostics.json",
    )


def _omitted_orchestration_source(reason: str) -> DiagnosticSource:
    return _omitted(
        "orchestration-diagnostics",
        "Orchestration diagnostics",
        "orchestrator",
        reason,
    )


def _health_source(
    *,
    health_checks: Mapping[str, Mapping[str, Any]] | HealthChecksProvider | None,
    config_store: Any | None,
    cache_store: Any | None,
    history_store: Any | None,
) -> DiagnosticSource:
    return _runtime_source(
        source_id="health-checks",
        name="Health and dependency checks",
        category="health",
        collect=_health_payload_collector(
            health_checks=health_checks,
            config_store=config_store,
            cache_store=cache_store,
            history_store=history_store,
        ),
        relative_path="runtime/health-checks.json",
    )


def _health_payload_collector(
    *,
    health_checks: Mapping[str, Mapping[str, Any]] | HealthChecksProvider | None,
    config_store: Any | None,
    cache_store: Any | None,
    history_store: Any | None,
) -> Callable[[], dict[str, Any]]:
    return (
        lambda checks=health_checks,
        config=config_store,
        cache=cache_store,
        history=history_store: runtime_payloads.health_payload(
            checks,
            config,
            cache,
            history,
        )
    )


def _history_save_source() -> DiagnosticSource:
    return _runtime_source(
        source_id="history-save-diagnostics",
        name="History save diagnostics",
        category="history",
        collect=runtime_payloads.history_save_diagnostics_payload,
        relative_path="runtime/history-save-diagnostics.json",
    )


def _omitted(source_id: str, name: str, category: str, reason: str) -> DiagnosticSource:
    return DiagnosticSource(
        source_id=source_id,
        name=name,
        category=category,
        omitted_reason=reason,
        max_bytes=_SOURCE_MAX_BYTES,
    )


def _bounded_limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int):
        return DEFAULT_HISTORY_LIMIT
    return max(0, min(limit, DEFAULT_HISTORY_LIMIT))


def _utcnow_iso() -> str:
    return utcnow_iso()


__all__ = [
    "DEFAULT_HISTORY_LIMIT",
    "build_default_diagnostic_sources",
]
