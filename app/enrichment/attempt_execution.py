"""Single-attempt cache and adapter execution for enrichment lookups."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any, Protocol

from .cache_payloads import (
    cache_marker_key,
    cache_payload_for_result,
    cached_enrichment_result,
)
from .models import EnrichmentError, EnrichmentResult, error_result
from app.pipeline.models import IOC

logger = logging.getLogger(__name__)


class AttemptCache(Protocol):
    def get(
        self,
        value: str,
        ioc_type: str,
        provider: str,
        ttl_seconds: int,
    ) -> dict | None: ...

    def put(
        self,
        value: str,
        ioc_type: str,
        provider: str,
        payload: dict,
    ) -> None: ...


RecordCacheFn = Callable[[str, str, bool], None]
RecordErrorFn = Callable[[str, str], None]
RecordLatencyFn = Callable[[str, str, float], None]
RecordCachedMarkerFn = Callable[[str, str], None]


def run_single_attempt(
    job_id: str,
    adapter: Any,
    ioc: IOC,
    provider_name: str,
    *,
    cache: AttemptCache | None,
    cache_ttl_seconds: int,
    record_cache: RecordCacheFn,
    record_error: RecordErrorFn,
    record_latency: RecordLatencyFn,
    record_cached_marker: RecordCachedMarkerFn,
) -> EnrichmentResult | EnrichmentError:
    """Execute one attempt and convert operation exceptions to provider errors."""
    started = time.perf_counter()
    operation = "cache read"
    try:
        if cache is not None and provider_name:
            cached = cache.get(
                ioc.value,
                ioc.type.value,
                provider_name,
                cache_ttl_seconds,
            )
            if cached is not None:
                record_cache(job_id, provider_name, True)
                cached_at = cached.get("cached_at", "")
                record_cached_marker(cache_marker_key(ioc, provider_name), cached_at)
                return cached_enrichment_result(ioc, cached)
            record_cache(job_id, provider_name, False)

        operation = "provider lookup"
        result = adapter.lookup(ioc)

        if cache is not None and provider_name and isinstance(result, EnrichmentResult):
            operation = "cache write"
            cache.put(
                ioc.value,
                ioc.type.value,
                provider_name,
                cache_payload_for_result(result),
            )

        if isinstance(result, EnrichmentError):
            record_error(job_id, provider_name)
        return result
    except Exception as exc:
        record_error(job_id, provider_name)
        detail = str(exc) or exc.__class__.__name__
        return error_result(
            ioc,
            provider_name or "unknown",
            f"{operation} failed: {detail}",
        )
    finally:
        try:
            record_latency(job_id, provider_name, time.perf_counter() - started)
        except Exception:
            logger.debug("Failed to record enrichment attempt latency", exc_info=True)
