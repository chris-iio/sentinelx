"""Runtime diagnostic payload builders used by diagnostic source descriptors."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from itertools import islice
from typing import Any

from .jsonish import (
    _safe_jsonish,
    _safe_mapping,
)
from .secret_inventory import collect_configured_secret_inventory
from app.health_contract import build_health_payload

DEFAULT_HISTORY_LIMIT = 10

JobDiagnosticsAccessor = Callable[[str], Mapping[str, Any] | None]
HealthChecksProvider = Callable[[], Mapping[str, Mapping[str, Any]]]


def config_secret_inventory_payload(config_store: Any) -> dict[str, Any]:
    inventory = collect_configured_secret_inventory(config_store)
    if inventory.config_error:
        raise RuntimeError(inventory.config_error)
    return config_secret_inventory_payload_from_inventory(inventory)


def config_secret_inventory_payload_from_inventory(inventory: Any) -> dict[str, Any]:
    return {
        "configured_secret_count": len(inventory.secret_labels),
        "configured_secret_labels": copy_label_tuple(inventory.secret_labels),
        "provider_count": len(inventory.provider_labels),
        "provider_labels": copy_label_tuple(inventory.provider_labels),
        "config_error": inventory.config_error,
    }


def copy_label_tuple(labels: tuple[str, ...]) -> list[str]:
    label_count = len(labels)
    if label_count == 0:
        return []
    if label_count == 1:
        return [labels[0]]
    if label_count == 2:
        return [labels[0], labels[1]]
    if label_count == 3:
        return [labels[0], labels[1], labels[2]]
    if label_count == 4:
        return [labels[0], labels[1], labels[2], labels[3]]

    copied: list[str] = []
    for label in labels:
        append_label_copy(copied, label)
    return copied


def append_label_copy(copied: list[str], label: str) -> None:
    copied.append(label)


def cache_stats_payload(cache_store: Any) -> dict[str, Any]:
    stats = cache_store.stats()
    if not isinstance(stats, Mapping):
        raise TypeError("CacheStore.stats() returned non-mapping diagnostics")
    return _safe_mapping(stats)


def recent_history_payload(history_store: Any, limit: int) -> dict[str, Any]:
    recent = history_store.list_recent(limit=limit)
    if not isinstance(recent, list):
        raise TypeError("HistoryStore.list_recent() returned non-list diagnostics")
    safe_recent = recent_history_items(recent, limit)
    return {
        "limit": limit,
        "returned_count": len(safe_recent),
        "items": safe_recent,
    }


def recent_history_items(recent: list[Any], limit: int) -> list[Any]:
    recent_count = len(recent)
    if recent_count == 0 or limit <= 0:
        return []
    if recent_count == 1:
        return [_safe_jsonish(recent[0])]
    if recent_count == 2 and limit >= 2:
        return [_safe_jsonish(recent[0]), _safe_jsonish(recent[1])]
    if recent_count == 3 and limit >= 3:
        return [
            _safe_jsonish(recent[0]),
            _safe_jsonish(recent[1]),
            _safe_jsonish(recent[2]),
        ]
    if recent_count == 4 and limit >= 4:
        return [
            _safe_jsonish(recent[0]),
            _safe_jsonish(recent[1]),
            _safe_jsonish(recent[2]),
            _safe_jsonish(recent[3]),
        ]

    safe_recent: list[Any] = []
    for item in islice(recent, limit):
        append_recent_history_item(safe_recent, item)
    return safe_recent


def append_recent_history_item(safe_recent: list[Any], item: Any) -> None:
    safe_recent.append(_safe_jsonish(item))


def history_save_diagnostics_payload() -> dict[str, Any]:
    from app.enrichment.history_diagnostics import get_history_save_diagnostics

    return _safe_mapping(get_history_save_diagnostics())


def health_payload(
    health_checks: Mapping[str, Mapping[str, Any]] | HealthChecksProvider | None,
    config_store: Any | None,
    cache_store: Any | None,
    history_store: Any | None,
) -> dict[str, Any]:
    return build_health_payload(
        health_checks_mapping(health_checks, config_store, cache_store, history_store)
    )


def health_checks_mapping(
    health_checks: Mapping[str, Mapping[str, Any]] | HealthChecksProvider | None,
    config_store: Any | None,
    cache_store: Any | None,
    history_store: Any | None,
) -> Mapping[str, Mapping[str, Any]]:
    checks = resolved_health_checks(health_checks, config_store, cache_store, history_store)
    if not isinstance(checks, Mapping):
        raise TypeError("health checks provider returned non-mapping diagnostics")
    return checks


def resolved_health_checks(
    health_checks: Mapping[str, Mapping[str, Any]] | HealthChecksProvider | None,
    config_store: Any | None,
    cache_store: Any | None,
    history_store: Any | None,
) -> object:
    if callable(health_checks):
        return health_checks()
    if health_checks is not None:
        return health_checks
    return default_health_checks(config_store, cache_store, history_store)


def default_health_checks(
    config_store: Any | None,
    cache_store: Any | None,
    history_store: Any | None,
) -> dict[str, dict[str, str]]:
    return {
        "cache": presence_check(cache_store, "cache_store_not_provided"),
        "history": presence_check(history_store, "history_store_not_provided"),
        "registry": presence_check(config_store, "config_store_not_provided"),
    }


def presence_check(value: Any | None, missing_detail: str) -> dict[str, str]:
    if value is None:
        return {"status": "degraded", "detail": missing_detail}
    return {"status": "ok", "detail": "available"}


def job_diagnostics_payload(accessor: JobDiagnosticsAccessor, job_id: str) -> dict[str, Any]:
    snapshot = accessor(job_id)
    if snapshot is None:
        return {"job_id": job_id, "found": False, "reason": "job_not_found"}
    return safe_job_diagnostics_payload(snapshot, job_id)


def safe_job_diagnostics_payload(snapshot: object, job_id: str) -> dict[str, Any]:
    if not isinstance(snapshot, Mapping):
        raise TypeError("job diagnostics accessor returned non-mapping diagnostics")
    safe = _safe_mapping(snapshot)
    apply_job_diagnostics_defaults(safe, job_id)
    return safe


def apply_job_diagnostics_defaults(payload: dict[str, Any], job_id: str) -> None:
    if "job_id" not in payload:
        payload["job_id"] = job_id
    if "found" not in payload:
        payload["found"] = True
