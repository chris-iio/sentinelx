"""Locked enrichment job diagnostic-state repair and update helpers."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from .diagnostics import (
    _coerce_job_diagnostics,
    _job_diagnostics_defaults,
    _normalize_provider_name,
    _provider_diagnostics_defaults,
)


def apply_job_diagnostics_update(
    jobs: OrderedDict[str, dict],
    job_id: str,
    provider_name: str,
    update: Any,
    **update_kwargs: Any,
) -> None:
    """Apply one diagnostics update to a live job.

    The caller owns synchronization. Missing jobs are ignored so late worker
    metrics cannot revive evicted or failed job state.
    """
    job = jobs.get(job_id)
    if job is None:
        return

    diagnostics = job.get("_diagnostics")
    if not isinstance(diagnostics, dict):
        diagnostics = _job_diagnostics_defaults()
        job["_diagnostics"] = diagnostics

    providers = diagnostics.get("providers")
    if not isinstance(providers, dict):
        diagnostics = _coerce_job_diagnostics(diagnostics)
        job["_diagnostics"] = diagnostics
        providers = diagnostics["providers"]

    provider_bucket = _normalize_provider_name(provider_name)
    provider = providers.get(provider_bucket)
    if not isinstance(provider, dict):
        provider = _provider_diagnostics_defaults()
        providers[provider_bucket] = provider

    update(diagnostics, provider, **update_kwargs)
