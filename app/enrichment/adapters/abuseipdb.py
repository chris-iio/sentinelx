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

import requests

from app.enrichment.http_safety import safe_request
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)

ABUSEIPDB_BASE = "https://api.abuseipdb.com/api/v2/check"


class AbuseIPDBAdapter:
    """Adapter for the AbuseIPDB IP reputation API.

    Supports IP IOC lookups (IPv4 and IPv6) using the AbuseIPDB check endpoint.
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

    Thread safety: uses a persistent requests.Session (self._session) created in __init__.
    The session is reused across lookup() calls for TCP connection pooling.

    Args:
        api_key:       AbuseIPDB API key.
        allowed_hosts: SSRF allowlist -- only these hostnames may be contacted.
    """

    supported_types: frozenset[IOCType] = frozenset({IOCType.IPV4, IOCType.IPV6})
    name = "AbuseIPDB"
    requires_api_key = True

    def __init__(self, api_key: str, allowed_hosts: list[str]) -> None:
        self._api_key = api_key
        self._allowed_hosts = allowed_hosts
        self._session = requests.Session()
        self._session.headers.update({
            "Key": self._api_key,          # CRITICAL: capital 'Key' (AbuseIPDB convention)
            "Accept": "application/json",  # Required: avoid HTML response
        })

    def is_configured(self) -> bool:
        """Return True when a non-empty API key is set."""
        return bool(self._api_key)

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        """Enrich a single IP IOC using the AbuseIPDB check API.

        Returns EnrichmentError immediately for non-IP types.
        Calls safe_request() and parses the response.

        Response semantics:
          - 200 + score >= 75               -> verdict=malicious
          - 200 + 25 <= score < 75          -> verdict=suspicious
          - 200 + score < 25 + reports > 0  -> verdict=clean
          - 200 + totalReports == 0         -> verdict=no_data
          - 429                             -> EnrichmentError("Rate limit exceeded (429)")
          - HTTP error / timeout             -> EnrichmentError

        NOTE: AbuseIPDB does NOT use 404 for unknown IPs. Always 200.
        The 404-before-raise_for_status pattern from Shodan/GreyNoise is NOT used here.

        Args:
            ioc: The IOC to look up. Must be IPv4 or IPv6.

        Returns:
            EnrichmentResult on success.
            EnrichmentError on unsupported type, SSRF block, or network failure.
        """
        if ioc.type not in self.supported_types:
            return EnrichmentError(
                ioc=ioc, provider=self.name, error="Unsupported type"
            )

        url = f"{ABUSEIPDB_BASE}?ipAddress={ioc.value}&maxAgeInDays=90"

        def _429_hook(resp):
            if resp.status_code == 429:
                return EnrichmentError(
                    ioc=ioc, provider=self.name, error="Rate limit exceeded (429)"
                )
            return None

        result = safe_request(
            self._session, url, self._allowed_hosts, ioc, self.name,
            pre_raise_hook=_429_hook,
        )
        if not isinstance(result, dict):
            return result
        return _parse_response(ioc, result, self.name)


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
