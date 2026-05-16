"""AbuseIPDB IP reputation adapter."""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.models import EnrichmentError, EnrichmentResult, error_result, provider_result
from app.pipeline.models import IOC, IOCType

ABUSEIPDB_BASE = "https://api.abuseipdb.com/api/v2/check"
_EMPTY_DATA: Mapping[str, object] = MappingProxyType({})


class AbuseIPDBAdapter(BaseHTTPAdapter):
    """AbuseIPDB check endpoint — see BaseHTTPAdapter for the template pattern."""

    supported_types: frozenset[IOCType] = frozenset((IOCType.IPV4, IOCType.IPV6))
    name = "AbuseIPDB"
    requires_api_key = True

    def _build_url(self, ioc: IOC) -> str:
        return f"{ABUSEIPDB_BASE}?ipAddress={ioc.value}&maxAgeInDays=90"

    def _auth_headers(self) -> dict:
        return {
            "Key": self._api_key,          # CRITICAL: capital 'Key' (AbuseIPDB convention)
            "Accept": "application/json",  # Required: avoid HTML response
        }

    def _make_pre_raise_hook(self, ioc: IOC):
        def _429_hook(resp):
            if resp.status_code == 429:
                return error_result(ioc, self.name, "Rate limit exceeded (429)")
            return None
        return _429_hook

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return _parse_response(ioc, body, self.name)


def _parse_response(ioc: IOC, body: dict, provider_name: str) -> EnrichmentResult:
    raw_data = body.get("data")
    data = raw_data if isinstance(raw_data, Mapping) else _EMPTY_DATA
    score: int = data.get("abuseConfidenceScore", 0)
    total_reports: int = data.get("totalReports", 0)
    distinct_users: int = data.get("numDistinctUsers", 0)
    last_reported_at: str | None = data.get("lastReportedAt")

    if score >= 75:
        verdict = "malicious"
    elif score >= 25:
        verdict = "suspicious"
    elif total_reports > 0:
        verdict = "clean"
    else:
        verdict = "no_data"

    return _abuseipdb_result(
        ioc=ioc,
        provider=provider_name,
        verdict=verdict,
        detection_count=total_reports,
        total_engines=distinct_users,
        scan_date=last_reported_at,
        raw_stats={
            "abuseConfidenceScore": score,
            "totalReports": total_reports,
            "numDistinctUsers": distinct_users,
            "countryCode": data.get("countryCode"),
            "isp": data.get("isp"),
            "usageType": data.get("usageType"),
            "lastReportedAt": last_reported_at,
            "isWhitelisted": data.get("isWhitelisted"),
        },
    )


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
