"""AbuseIPDB IP reputation adapter."""
from __future__ import annotations

import logging

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)

ABUSEIPDB_BASE = "https://api.abuseipdb.com/api/v2/check"


class AbuseIPDBAdapter(BaseHTTPAdapter):
    """AbuseIPDB check endpoint — see BaseHTTPAdapter for the template pattern."""

    supported_types: frozenset[IOCType] = frozenset({IOCType.IPV4, IOCType.IPV6})
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
                return EnrichmentError(
                    ioc=ioc, provider=self.name, error="Rate limit exceeded (429)"
                )
            return None
        return _429_hook

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return _parse_response(ioc, body, self.name)


def _parse_response(ioc: IOC, body: dict, provider_name: str) -> EnrichmentResult:
    data: dict = body.get("data", {})
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

    return EnrichmentResult(
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
