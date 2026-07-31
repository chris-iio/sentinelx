"""Cache payload helpers for enrichment lookups."""
from __future__ import annotations

from .models import EnrichmentResult
from app.pipeline.models import IOC


def cached_enrichment_result(ioc: IOC, cached: dict) -> EnrichmentResult:
    """Hydrate an enrichment result from cache without mutating the cached payload."""
    return EnrichmentResult(
        ioc=ioc,
        provider=cached["provider"],
        verdict=cached["verdict"],
        detection_count=cached["detection_count"],
        total_engines=cached["total_engines"],
        scan_date=cached.get("scan_date"),
        raw_stats=cached.get("raw_stats", {}),
    )


def cache_marker_key(ioc: IOC, provider_name: str) -> str:
    """Return the stable cache marker key used by status serialization."""
    return ioc.value + "|" + provider_name


def cache_payload_for_result(result: EnrichmentResult) -> dict:
    """Return the payload persisted for successful enrichment results."""
    return {
        "provider": result.provider,
        "verdict": result.verdict,
        "detection_count": result.detection_count,
        "total_engines": result.total_engines,
        "scan_date": result.scan_date,
        "raw_stats": result.raw_stats,
    }
