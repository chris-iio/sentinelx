"""Safe backend runtime source composition for diagnostic exports.

This module only builds :class:`DiagnosticSource` descriptors.  It does not
assemble archives, register routes, read raw config files, or traverse the
filesystem.  Callers inject the runtime objects they want considered so tests
and future routes can stay explicit about which local state is inspected.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from itertools import islice
from typing import Any

from app.diagnostics.assembler import DiagnosticSource
from app.diagnostics.policy import DIAGNOSTIC_SANITIZATION_POLICY
from app.diagnostics.redaction import collect_configured_secret_inventory
from app.health_contract import build_health_payload
from app.time_utils import utcnow_iso

DEFAULT_HISTORY_LIMIT = 10
_SOURCE_MAX_BYTES = DIAGNOSTIC_SANITIZATION_POLICY.runtime_source_max_bytes
_MAX_SAFE_STRING_CHARS = DIAGNOSTIC_SANITIZATION_POLICY.max_safe_string_chars
_MAX_LIST_ITEMS = DIAGNOSTIC_SANITIZATION_POLICY.max_list_items
_MAX_DICT_ITEMS = DIAGNOSTIC_SANITIZATION_POLICY.max_dict_items
_MAX_DEPTH = DIAGNOSTIC_SANITIZATION_POLICY.max_jsonish_depth

JobDiagnosticsAccessor = Callable[[str], Mapping[str, Any] | None]
HealthChecksProvider = Callable[[], Mapping[str, Mapping[str, Any]]]


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

    safe_history_limit = _bounded_limit(history_limit)
    metadata_generated_at = generated_at or _utcnow_iso()

    sources: list[DiagnosticSource] = [
        DiagnosticSource(
            source_id="diagnostic-export-metadata",
            name="Diagnostic export metadata",
            category="metadata",
            payload={
                "schema": "sentinelx.diagnostic_sources.v1",
                "generated_at": metadata_generated_at,
                "history_limit": safe_history_limit,
                "job_id_requested": bool(job_id),
                "runtime_objects": {
                    "config_store": config_store is not None,
                    "cache_store": cache_store is not None,
                    "history_store": history_store is not None,
                    "job_diagnostics_accessor": job_diagnostics_accessor is not None,
                },
            },
            relative_path="runtime/diagnostic-export-metadata.json",
            max_bytes=_SOURCE_MAX_BYTES,
        )
    ]

    if config_store is None:
        sources.append(_omitted("config-secret-inventory", "Config secret inventory", "config", "config_store_not_provided"))
    else:
        sources.append(
            DiagnosticSource(
                source_id="config-secret-inventory",
                name="Config secret inventory",
                category="config",
                collect=lambda store=config_store: _config_secret_inventory_payload(store),
                relative_path="runtime/config-secret-inventory.json",
                max_bytes=_SOURCE_MAX_BYTES,
            )
        )

    if cache_store is None:
        sources.append(_omitted("cache-stats", "Cache statistics", "cache", "cache_store_not_provided"))
    else:
        sources.append(
            DiagnosticSource(
                source_id="cache-stats",
                name="Cache statistics",
                category="cache",
                collect=lambda store=cache_store: _cache_stats_payload(store),
                relative_path="runtime/cache-stats.json",
                max_bytes=_SOURCE_MAX_BYTES,
            )
        )

    if history_store is None:
        sources.append(_omitted("recent-history", "Recent history summaries", "history", "history_store_not_provided"))
    else:
        sources.append(
            DiagnosticSource(
                source_id="recent-history",
                name="Recent history summaries",
                category="history",
                collect=lambda store=history_store, limit=safe_history_limit: _recent_history_payload(store, limit),
                relative_path="runtime/recent-history.json",
                max_bytes=_SOURCE_MAX_BYTES,
            )
        )

    sources.append(
        DiagnosticSource(
            source_id="history-save-diagnostics",
            name="History save diagnostics",
            category="history",
            collect=_history_save_diagnostics_payload,
            relative_path="runtime/history-save-diagnostics.json",
            max_bytes=_SOURCE_MAX_BYTES,
        )
    )

    sources.append(
        DiagnosticSource(
            source_id="health-checks",
            name="Health and dependency checks",
            category="health",
            collect=lambda checks=health_checks, config=config_store, cache=cache_store, history=history_store: _health_payload(checks, config, cache, history),
            relative_path="runtime/health-checks.json",
            max_bytes=_SOURCE_MAX_BYTES,
        )
    )

    if not job_id:
        sources.append(_omitted("orchestration-diagnostics", "Orchestration diagnostics", "orchestrator", "job_id_not_provided"))
    elif job_diagnostics_accessor is None:
        sources.append(_omitted("orchestration-diagnostics", "Orchestration diagnostics", "orchestrator", "job_diagnostics_accessor_not_provided"))
    else:
        sources.append(
            DiagnosticSource(
                source_id="orchestration-diagnostics",
                name="Orchestration diagnostics",
                category="orchestrator",
                collect=lambda accessor=job_diagnostics_accessor, requested_job_id=job_id: _job_diagnostics_payload(accessor, requested_job_id),
                relative_path="runtime/orchestration-diagnostics.json",
                max_bytes=_SOURCE_MAX_BYTES,
            )
        )

    return tuple(sources)


def _config_secret_inventory_payload(config_store: Any) -> dict[str, Any]:
    inventory = collect_configured_secret_inventory(config_store)
    if inventory.config_error:
        raise RuntimeError(inventory.config_error)
    return {
        "configured_secret_count": len(inventory.secret_labels),
        "configured_secret_labels": _copy_label_tuple(inventory.secret_labels),
        "provider_count": len(inventory.provider_labels),
        "provider_labels": _copy_label_tuple(inventory.provider_labels),
        "config_error": inventory.config_error,
    }


def _copy_label_tuple(labels: tuple[str, ...]) -> list[str]:
    label_count = len(labels)
    if label_count == 0:
        return []
    if label_count == 1:
        return [labels[0]]
    if label_count == 2:
        return [labels[0], labels[1]]
    if label_count == 3:
        return [labels[0], labels[1], labels[2]]

    copied: list[str] = []
    for label in labels:
        copied.append(label)
    return copied


def _cache_stats_payload(cache_store: Any) -> dict[str, Any]:
    stats = cache_store.stats()
    if not isinstance(stats, Mapping):
        raise TypeError("CacheStore.stats() returned non-mapping diagnostics")
    return _safe_mapping(stats)


def _recent_history_payload(history_store: Any, limit: int) -> dict[str, Any]:
    recent = history_store.list_recent(limit=limit)
    if not isinstance(recent, list):
        raise TypeError("HistoryStore.list_recent() returned non-list diagnostics")
    recent_count = len(recent)
    if recent_count == 0 or limit <= 0:
        return {
            "limit": limit,
            "returned_count": 0,
            "items": [],
        }
    if recent_count == 1:
        return {
            "limit": limit,
            "returned_count": 1,
            "items": [_safe_jsonish(recent[0])],
        }

    safe_recent: list[Any] = []
    for item in islice(recent, limit):
        safe_recent.append(_safe_jsonish(item))
    return {
        "limit": limit,
        "returned_count": len(safe_recent),
        "items": safe_recent,
    }


def _history_save_diagnostics_payload() -> dict[str, Any]:
    from app.routes._helpers import get_history_save_diagnostics

    return _safe_mapping(get_history_save_diagnostics())


def _health_payload(
    health_checks: Mapping[str, Mapping[str, Any]] | HealthChecksProvider | None,
    config_store: Any | None,
    cache_store: Any | None,
    history_store: Any | None,
) -> dict[str, Any]:
    if callable(health_checks):
        checks = health_checks()
    elif health_checks is not None:
        checks = health_checks
    else:
        checks = _default_health_checks(config_store, cache_store, history_store)
    if not isinstance(checks, Mapping):
        raise TypeError("health checks provider returned non-mapping diagnostics")
    return build_health_payload(checks)


def _default_health_checks(config_store: Any | None, cache_store: Any | None, history_store: Any | None) -> dict[str, dict[str, str]]:
    return {
        "cache": _presence_check(cache_store, "cache_store_not_provided"),
        "history": _presence_check(history_store, "history_store_not_provided"),
        "registry": _presence_check(config_store, "config_store_not_provided"),
    }


def _presence_check(value: Any | None, missing_detail: str) -> dict[str, str]:
    if value is None:
        return {"status": "degraded", "detail": missing_detail}
    return {"status": "ok", "detail": "available"}


def _job_diagnostics_payload(accessor: JobDiagnosticsAccessor, job_id: str) -> dict[str, Any]:
    snapshot = accessor(job_id)
    if snapshot is None:
        return {"job_id": job_id, "found": False, "reason": "job_not_found"}
    if not isinstance(snapshot, Mapping):
        raise TypeError("job diagnostics accessor returned non-mapping diagnostics")
    safe = _safe_mapping(snapshot)
    if "job_id" not in safe:
        safe["job_id"] = job_id
    if "found" not in safe:
        safe["found"] = True
    return safe


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


def _safe_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    safe = _safe_jsonish(value)
    if not isinstance(safe, dict):
        raise TypeError("diagnostic mapping could not be coerced")
    return safe


def _safe_jsonish(value: Any, *, depth: int = 0) -> Any:
    if depth >= _MAX_DEPTH:
        return "<max-depth>"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:_MAX_SAFE_STRING_CHARS]
    if isinstance(value, Mapping):
        if type(value) is dict:
            value_count = len(value)
            if value_count == 0:
                return {}
            if value_count == 1:
                for key in value:
                    return {str(key)[:80]: _safe_jsonish(value[key], depth=depth + 1)}
        safe: dict[str, Any] = {}
        for key in islice(value, _MAX_DICT_ITEMS):
            safe[str(key)[:80]] = _safe_jsonish(value[key], depth=depth + 1)
        return safe
    if isinstance(value, (list, tuple)):
        value_count = len(value)
        if value_count == 0:
            return []
        if value_count == 1:
            return [_safe_jsonish(value[0], depth=depth + 1)]
        if value_count == 2:
            return [
                _safe_jsonish(value[0], depth=depth + 1),
                _safe_jsonish(value[1], depth=depth + 1),
            ]
        safe_items: list[Any] = []
        for item in islice(value, _MAX_LIST_ITEMS):
            safe_items.append(_safe_jsonish(item, depth=depth + 1))
        return safe_items
    if isinstance(value, (set, frozenset)):
        safe_items: list[Any] = []
        for item in islice(value, _MAX_LIST_ITEMS):
            safe_items.append(_safe_jsonish(item, depth=depth + 1))
        return safe_items
    return repr(value)[:_MAX_SAFE_STRING_CHARS]


def _utcnow_iso() -> str:
    return utcnow_iso()


__all__ = [
    "DEFAULT_HISTORY_LIMIT",
    "JobDiagnosticsAccessor",
    "build_default_diagnostic_sources",
]
