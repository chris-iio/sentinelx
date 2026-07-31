"""Bounded diagnostics helpers for enrichment jobs."""

from __future__ import annotations

from typing import Any

from app.pipeline.models import IOC
from app.text_utils import stripped_text_or_none

_UNKNOWN_PROVIDER = "unknown"
_DIAGNOSTIC_COUNTER_FIELDS = (
    "dispatch_count",
    "attempt_count",
    "cache_hits",
    "cache_misses",
    "retry_count",
    "rate_limit_retry_count",
    "error_count",
)
_DIAGNOSTIC_FLOAT_FIELDS = ("latency_total_seconds", "latency_max_seconds")


def _provider_diagnostics_defaults() -> dict[str, int | float]:
    """Return the bounded aggregate defaults for a single provider bucket."""
    return {
        "dispatch_count": 0,
        "attempt_count": 0,
        "cache_hits": 0,
        "cache_misses": 0,
        "retry_count": 0,
        "rate_limit_retry_count": 0,
        "error_count": 0,
        "latency_total_seconds": 0.0,
        "latency_max_seconds": 0.0,
    }


def _job_diagnostics_defaults() -> dict[str, Any]:
    """Return the bounded aggregate defaults for one enrichment job."""
    return {
        **_provider_diagnostics_defaults(),
        "providers": {},
    }


def _provider_diagnostics_bucket(
    providers: dict[str, dict[str, int | float]],
    provider_name: str,
) -> dict[str, int | float]:
    """Return a provider diagnostics bucket without setdefault's eager defaults."""
    provider = providers.get(provider_name)
    if provider is None:
        provider = _provider_diagnostics_defaults()
        providers[provider_name] = provider
    return provider


def _normalize_provider_name(raw_name: object) -> str:
    """Return a bounded provider bucket name, falling back to ``unknown``."""
    if not isinstance(raw_name, str):
        return _UNKNOWN_PROVIDER
    provider_name = stripped_text_or_none(raw_name)
    if provider_name is None:
        return _UNKNOWN_PROVIDER
    return provider_name[:64]


def _coerce_provider_diagnostics(raw: object) -> dict[str, int | float]:
    """Return a safe provider diagnostics snapshot even if state is malformed."""
    data = raw if isinstance(raw, dict) else {}
    diagnostics = _provider_diagnostics_defaults()

    _coerce_diagnostic_counters(diagnostics, data)
    _coerce_diagnostic_floats(diagnostics, data)

    return diagnostics


def _merge_provider_diagnostics(
    target: dict[str, int | float],
    source: dict[str, int | float],
) -> None:
    """Merge *source* into *target* without dropping bounded aggregate fields."""
    target["dispatch_count"] += int(source["dispatch_count"])
    target["attempt_count"] += int(source["attempt_count"])
    target["cache_hits"] += int(source["cache_hits"])
    target["cache_misses"] += int(source["cache_misses"])
    target["retry_count"] += int(source["retry_count"])
    target["rate_limit_retry_count"] += int(source["rate_limit_retry_count"])
    target["error_count"] += int(source["error_count"])
    target["latency_total_seconds"] += float(source["latency_total_seconds"])
    target["latency_max_seconds"] = max(
        float(target["latency_max_seconds"]),
        float(source["latency_max_seconds"]),
    )


def _coerce_job_diagnostics(raw: object) -> dict[str, Any]:
    """Return a safe job diagnostics snapshot even if state is malformed."""
    data = raw if isinstance(raw, dict) else {}
    diagnostics = _provider_diagnostics_defaults() | {"providers": {}}

    _coerce_diagnostic_counters(diagnostics, data)
    _coerce_diagnostic_floats(diagnostics, data)

    raw_providers = data.get("providers")
    if isinstance(raw_providers, dict):
        providers: dict[str, dict[str, int | float]] = {}
        for raw_name in raw_providers:
            raw_provider = raw_providers[raw_name]
            provider_name = _normalize_provider_name(raw_name)
            provider_snapshot = _coerce_provider_diagnostics(raw_provider)
            append_provider_diagnostics_snapshot(
                providers,
                provider_name,
                provider_snapshot,
            )
        diagnostics["providers"] = providers

    return diagnostics


def append_provider_diagnostics_snapshot(
    providers: dict[str, dict[str, int | float]],
    provider_name: str,
    provider_snapshot: dict[str, int | float],
) -> None:
    existing = providers.get(provider_name)
    if existing is None:
        providers[provider_name] = provider_snapshot
        return
    _merge_provider_diagnostics(existing, provider_snapshot)


def _coerce_diagnostic_counters(
    diagnostics: dict[str, Any],
    data: dict[str, Any],
) -> None:
    _coerce_diagnostic_counter(diagnostics, data, "dispatch_count")
    _coerce_diagnostic_counter(diagnostics, data, "attempt_count")
    _coerce_diagnostic_counter(diagnostics, data, "cache_hits")
    _coerce_diagnostic_counter(diagnostics, data, "cache_misses")
    _coerce_diagnostic_counter(diagnostics, data, "retry_count")
    _coerce_diagnostic_counter(diagnostics, data, "rate_limit_retry_count")
    _coerce_diagnostic_counter(diagnostics, data, "error_count")


def _coerce_diagnostic_counter(
    diagnostics: dict[str, Any],
    data: dict[str, Any],
    field: str,
) -> None:
    value = data.get(field)
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        diagnostics[field] = value


def _coerce_diagnostic_floats(
    diagnostics: dict[str, Any],
    data: dict[str, Any],
) -> None:
    _coerce_diagnostic_float(diagnostics, data, "latency_total_seconds")
    _coerce_diagnostic_float(diagnostics, data, "latency_max_seconds")


def _coerce_diagnostic_float(
    diagnostics: dict[str, Any],
    data: dict[str, Any],
    field: str,
) -> None:
    value = data.get(field)
    if isinstance(value, (int, float)) and value >= 0:
        diagnostics[field] = float(value)


def build_dispatch_diagnostics(dispatch_pairs: list[tuple[Any, IOC]]) -> dict[str, Any]:
    """Create the initial bounded diagnostics snapshot for a job."""
    diagnostics = _job_diagnostics_defaults()
    pair_count = len(dispatch_pairs)
    if pair_count == 0:
        return diagnostics
    if pair_count == 1:
        record_dispatch_pair(diagnostics, dispatch_pairs[0])
        return diagnostics
    if pair_count == 2:
        record_dispatch_pair(diagnostics, dispatch_pairs[0])
        record_dispatch_pair(diagnostics, dispatch_pairs[1])
        return diagnostics
    if pair_count == 3:
        record_dispatch_pair(diagnostics, dispatch_pairs[0])
        record_dispatch_pair(diagnostics, dispatch_pairs[1])
        record_dispatch_pair(diagnostics, dispatch_pairs[2])
        return diagnostics
    if pair_count == 4:
        record_dispatch_pair(diagnostics, dispatch_pairs[0])
        record_dispatch_pair(diagnostics, dispatch_pairs[1])
        record_dispatch_pair(diagnostics, dispatch_pairs[2])
        record_dispatch_pair(diagnostics, dispatch_pairs[3])
        return diagnostics

    for dispatch_pair in dispatch_pairs:
        record_dispatch_pair(diagnostics, dispatch_pair)
    return diagnostics


def record_dispatch_pair(diagnostics: dict[str, Any], dispatch_pair: tuple[Any, IOC]) -> None:
    adapter, _ioc = dispatch_pair
    provider_name = _normalize_provider_name(getattr(adapter, "name", ""))
    provider = _provider_diagnostics_bucket(diagnostics["providers"], provider_name)
    diagnostics["dispatch_count"] += 1
    provider["dispatch_count"] += 1


def apply_cache_update(
    diagnostics: dict[str, Any],
    provider: dict[str, int | float],
    *,
    hit: bool,
) -> None:
    """Record one cache hit or miss in job and provider diagnostics."""
    field = "cache_hits" if hit else "cache_misses"
    diagnostics[field] += 1
    provider[field] += 1


def apply_retry_update(
    diagnostics: dict[str, Any],
    provider: dict[str, int | float],
    *,
    rate_limit: bool,
) -> None:
    """Record one retry attempt in job and provider diagnostics."""
    diagnostics["retry_count"] += 1
    provider["retry_count"] += 1
    if rate_limit:
        diagnostics["rate_limit_retry_count"] += 1
        provider["rate_limit_retry_count"] += 1


def apply_latency_update(
    diagnostics: dict[str, Any],
    provider: dict[str, int | float],
    *,
    latency_seconds: float,
) -> None:
    """Record one bounded latency sample in job and provider diagnostics."""
    safe_latency = max(float(latency_seconds), 0.0)
    diagnostics["attempt_count"] += 1
    diagnostics["latency_total_seconds"] += safe_latency
    diagnostics["latency_max_seconds"] = max(
        float(diagnostics["latency_max_seconds"]),
        safe_latency,
    )
    provider["attempt_count"] += 1
    provider["latency_total_seconds"] += safe_latency
    provider["latency_max_seconds"] = max(
        float(provider["latency_max_seconds"]),
        safe_latency,
    )


def apply_error_update(
    diagnostics: dict[str, Any],
    provider: dict[str, int | float],
) -> None:
    """Record one provider-scoped error in job and provider diagnostics."""
    diagnostics["error_count"] += 1
    provider["error_count"] += 1
