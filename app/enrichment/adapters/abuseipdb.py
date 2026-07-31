"""AbuseIPDB IP reputation adapter."""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import NamedTuple

from .base import BaseHTTPAdapter
from ..models import EnrichmentResult, provider_result
from app.pipeline.models import IOC, IOCType

ABUSEIPDB_BASE = "https://api.abuseipdb.com/api/v2/check"
_EMPTY_DATA: Mapping[str, object] = MappingProxyType({})


class AbuseIpdbSignals(NamedTuple):
    data: Mapping[str, object]
    score: int
    total_reports: int
    distinct_users: int
    last_reported_at: str | None


def _abuseipdb_signals(body: dict) -> AbuseIpdbSignals:
    raw_data = body.get("data")
    data = raw_data if isinstance(raw_data, Mapping) else _EMPTY_DATA
    return AbuseIpdbSignals(
        data=data,
        score=data.get("abuseConfidenceScore", 0),
        total_reports=data.get("totalReports", 0),
        distinct_users=data.get("numDistinctUsers", 0),
        last_reported_at=data.get("lastReportedAt"),
    )


class AbuseIPDBAdapter(BaseHTTPAdapter):
    """AbuseIPDB check endpoint — see BaseHTTPAdapter for the template pattern."""

    supported_types: frozenset[IOCType] = frozenset((IOCType.IPV4, IOCType.IPV6))
    name = "AbuseIPDB"
    requires_api_key = True
    _rate_limit_on_429 = True

    def _build_url(self, ioc: IOC) -> str:
        return f"{ABUSEIPDB_BASE}?ipAddress={ioc.value}&maxAgeInDays=90"

    def _auth_headers(self) -> dict:
        return {
            "Key": self._api_key,          # CRITICAL: capital 'Key' (AbuseIPDB convention)
            "Accept": "application/json",  # Required: avoid HTML response
        }

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return _parse_response(ioc, body, self.name)


def _parse_response(ioc: IOC, body: dict, provider_name: str) -> EnrichmentResult:
    signals = _abuseipdb_signals(body)

    return _abuseipdb_result(
        ioc=ioc,
        provider=provider_name,
        verdict=_abuseipdb_verdict(signals.score, signals.total_reports),
        detection_count=signals.total_reports,
        total_engines=signals.distinct_users,
        scan_date=signals.last_reported_at,
        raw_stats=_abuseipdb_raw_stats(
            data=signals.data,
            score=signals.score,
            total_reports=signals.total_reports,
            distinct_users=signals.distinct_users,
            last_reported_at=signals.last_reported_at,
        ),
    )


def _abuseipdb_verdict(score: int, total_reports: int) -> str:
    if score >= 75:
        return "malicious"
    if score >= 25:
        return "suspicious"
    if total_reports > 0:
        return "clean"
    return "no_data"


def _abuseipdb_raw_stats(
    *,
    data: Mapping[str, object],
    score: int,
    total_reports: int,
    distinct_users: int,
    last_reported_at: str | None,
) -> dict[str, object]:
    return {
        "abuseConfidenceScore": score,
        "totalReports": total_reports,
        "numDistinctUsers": distinct_users,
        "countryCode": data.get("countryCode"),
        "isp": data.get("isp"),
        "usageType": data.get("usageType"),
        "lastReportedAt": last_reported_at,
        "isWhitelisted": data.get("isWhitelisted"),
    }


def _abuseipdb_result(
    *,
    ioc: IOC,
    provider: str,
    verdict: str,
    detection_count: int,
    total_engines: int,
    scan_date: str | None,
    raw_stats: dict,
) -> EnrichmentResult:
    return provider_result(
        ioc=ioc,
        provider=provider,
        verdict=verdict,
        detection_count=detection_count,
        total_engines=total_engines,
        scan_date=scan_date,
        raw_stats=raw_stats,
    )
