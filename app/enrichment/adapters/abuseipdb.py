"""AbuseIPDB API adapter.

Implements IP enrichment against the AbuseIPDB API. Delegates all HTTP safety
controls to safe_request() in http_safety.py.

AbuseIPDB API behavior:
  - GET https://api.abuseipdb.com/api/v2/check?ipAddress={ip}&maxAgeInDays=90
  - Auth header: 'Key' (capital K) with the API key value
  - Accept: application/json header required to avoid HTML response
  - Always 200 for valid IPs (no 404 for unknown IPs)
  - 429: rate limited -> EnrichmentError("Rate limit exceeded (429)")
  - 401: unauthorized -> EnrichmentError("HTTP 401")

Verdict thresholds (abuseConfidenceScore):
  - score >= 75                     -> "malicious"
  - 25 <= score < 75                -> "suspicious"
  - score < 25 AND totalReports > 0 -> "clean"
  - totalReports == 0               -> "no_data"

detection_count = totalReports (number of abuse reports)
total_engines  = numDistinctUsers (number of distinct reporters)

API key required — register at https://www.abuseipdb.com/
"""
from __future__ import annotations

import logging

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)

ABUSEIPDB_BASE = "https://api.abuseipdb.com/api/v2/check"


class AbuseIPDBAdapter(BaseHTTPAdapter):
    """Adapter for the AbuseIPDB IP reputation API.

    Extends BaseHTTPAdapter for IP enrichment against the AbuseIPDB check
    endpoint. All HTTP safety controls (SSRF allowlist, size cap, timeouts) are
    inherited.

    Verdict is derived from the abuseConfidenceScore and totalReports fields:

    - score >= 75                     -> verdict=malicious
    - 25 <= score < 75                -> verdict=suspicious
    - score < 25 AND totalReports > 0 -> verdict=clean
    - totalReports == 0               -> verdict=no_data

    AbuseIPDB always returns 200 for valid IP addresses — there is no 404 for
    unknown IPs. An unknown IP simply has score=0 and totalReports=0.

    HTTP 429 rate limit is handled specially with a descriptive error message.

    API key required — register at https://www.abuseipdb.com/

    CRITICAL: Auth header is capital 'Key' (not lowercase 'key').
              Include 'Accept: application/json' or API may return HTML.

    Thread safety: a persistent requests.Session is created by BaseHTTPAdapter.__init__
    and reused across lookup() calls for TCP connection pooling.

    Args:
        allowed_hosts: SSRF allowlist -- only these hostnames may be contacted.
        api_key:       AbuseIPDB API key (keyword-only).
    """

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
    """Parse an AbuseIPDB API response into an EnrichmentResult.

    Extracts abuseConfidenceScore and totalReports from response.data and
    applies verdict thresholds.

    Verdict rules:
      - score >= 75                     -> "malicious"
      - 25 <= score < 75                -> "suspicious"
      - score < 25 AND total_reports > 0 -> "clean"
      - else (total_reports == 0)        -> "no_data"

    Args:
        ioc:           The IOC that was queried.
        body:          Parsed JSON from AbuseIPDB API response.
        provider_name: Provider name string for result construction.

    Returns:
        EnrichmentResult with verdict "malicious", "suspicious", "clean", or "no_data".
    """
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
