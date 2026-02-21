"""Enrichment result models.

Provides typed, immutable data structures for enrichment results.
Both models are frozen dataclasses to match the Phase 1 immutability pattern.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.pipeline.models import IOC


@dataclass(frozen=True)
class EnrichmentResult:
    """An immutable enrichment result from a TI provider.

    Attributes:
        ioc:             The IOC that was queried.
        provider:        Name of the TI provider (e.g., "VirusTotal").
        verdict:         "malicious" | "clean" | "no_data"
        detection_count: Number of engines flagging the IOC as malicious.
        total_engines:   Total number of engines that scanned the IOC.
        scan_date:       ISO8601 string of last analysis date, or None.
        raw_stats:       Raw last_analysis_stats dict from provider response.
    """

    ioc: IOC
    provider: str
    verdict: str
    detection_count: int
    total_engines: int
    scan_date: str | None
    raw_stats: dict


@dataclass(frozen=True)
class EnrichmentError:
    """An immutable enrichment failure result.

    Returned when a provider lookup fails (timeout, auth error, etc.)
    or the IOC type is not supported by the provider.

    Attributes:
        ioc:      The IOC that was queried.
        provider: Name of the TI provider.
        error:    Human-readable error message.
    """

    ioc: IOC
    provider: str
    error: str
