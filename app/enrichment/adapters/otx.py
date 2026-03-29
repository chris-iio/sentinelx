"""OTX AlienVault API adapter.

Implements IP, domain, URL, hash (MD5/SHA1/SHA256), and CVE enrichment against
the OTX AlienVault v1 API. Delegates all HTTP safety controls to safe_request()
in http_safety.py.

OTX API behavior (all endpoints are GET with X-OTX-API-KEY header):
  - GET /api/v1/indicators/IPv4/{value}/general
  - GET /api/v1/indicators/IPv6/{value}/general
  - GET /api/v1/indicators/domain/{value}/general
  - GET /api/v1/indicators/url/{value}/general
  - GET /api/v1/indicators/file/{value}/general  (MD5, SHA1, SHA256 ALL map to "file")
  - GET /api/v1/indicators/cve/{value}/general

CRITICAL: All three hash types (MD5, SHA1, SHA256) use "file" in the URL path.
OTX does not have separate endpoints per hash type.

Verdict from pulse_info.count:
  - count >= 5 -> malicious
  - count 1-4  -> suspicious
  - count == 0 -> no_data

404 response -> no_data (not an error) — handled via pre_raise_hook.

Supports 8 IOCType values (all except EMAIL) including CVE (the first CVE-capable provider).
"""
from __future__ import annotations

import logging

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.models import EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)

OTX_BASE = "https://otx.alienvault.com/api/v1/indicators"

# Maps IOCType to the OTX path segment used in the URL
# CRITICAL: MD5, SHA1, SHA256 ALL map to "file" — not "md5"/"sha1"/"sha256"
_OTX_TYPE_MAP: dict[IOCType, str] = {
    IOCType.IPV4: "IPv4",
    IOCType.IPV6: "IPv6",
    IOCType.DOMAIN: "domain",
    IOCType.URL: "url",
    IOCType.MD5: "file",
    IOCType.SHA1: "file",
    IOCType.SHA256: "file",
    IOCType.CVE: "cve",
}

# Threshold for verdict classification
_MALICIOUS_THRESHOLD = 5  # pulse_info.count >= this -> malicious
_SUSPICIOUS_MIN = 1       # pulse_info.count >= this -> suspicious (below malicious threshold)


class OTXAdapter(BaseHTTPAdapter):
    """Adapter for the OTX AlienVault v1 API.

    Extends BaseHTTPAdapter for multi-type IOC enrichment against the OTX
    AlienVault v1 API. All HTTP safety controls (SSRF allowlist, size cap,
    timeouts) are inherited.

    Supports 8 IOC types (IPV4, IPV6, DOMAIN, URL, MD5, SHA1, SHA256, CVE).
    EMAIL is intentionally excluded — OTX has no email lookup endpoint.
    Uses GET requests with X-OTX-API-KEY header.

    Verdict is derived from pulse_info.count in the response:
    - count >= 5  -> malicious
    - count 1-4   -> suspicious
    - count == 0  -> no_data
    - 404         -> no_data (IOC not in OTX)

    All hash types (MD5, SHA1, SHA256) map to the "file" endpoint path.

    Thread safety: a persistent requests.Session is created by BaseHTTPAdapter.__init__
    and reused across lookup() calls for TCP connection pooling.

    Args:
        allowed_hosts: SSRF allowlist -- only these hostnames may be contacted.
        api_key:       OTX API key for the X-OTX-API-KEY header (keyword-only).
    """

    supported_types: frozenset[IOCType] = frozenset({
        IOCType.IPV4, IOCType.IPV6, IOCType.DOMAIN, IOCType.URL,
        IOCType.MD5, IOCType.SHA1, IOCType.SHA256, IOCType.CVE,
    })  # EMAIL excluded — OTX has no email lookup endpoint
    name = "OTX AlienVault"
    requires_api_key = True

    def _build_url(self, ioc: IOC) -> str:
        otx_type = _OTX_TYPE_MAP[ioc.type]
        return f"{OTX_BASE}/{otx_type}/{ioc.value}/general"

    def _auth_headers(self) -> dict:
        return {
            "X-OTX-API-KEY": self._api_key,
            "Accept": "application/json",
        }

    def _make_pre_raise_hook(self, ioc: IOC):
        def _404_hook(resp):
            if resp.status_code == 404:
                return EnrichmentResult(
                    ioc=ioc,
                    provider=self.name,
                    verdict="no_data",
                    detection_count=0,
                    total_engines=0,
                    scan_date=None,
                    raw_stats={},
                )
            return None
        return _404_hook

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return _parse_response(ioc, body, self.name)


def _parse_response(ioc: IOC, body: dict, provider_name: str) -> EnrichmentResult:
    """Parse an OTX AlienVault API response into an EnrichmentResult.

    Derives verdict from pulse_info.count using these thresholds:
      - count >= 5  -> malicious
      - count 1-4   -> suspicious
      - count == 0  -> no_data

    Extracts pulse_count, reputation, and type_title for raw_stats.

    Args:
        ioc:           The IOC that was queried.
        body:          Parsed JSON from OTX API response.
        provider_name: Provider name string for result construction.

    Returns:
        EnrichmentResult with verdict "malicious", "suspicious", or "no_data".
    """
    pulse_info: dict = body.get("pulse_info", {}) or {}
    pulse_count: int = pulse_info.get("count", 0) or 0
    reputation: int = body.get("reputation", 0) or 0
    type_title: str = body.get("type_title", "") or ""

    if pulse_count >= _MALICIOUS_THRESHOLD:
        verdict = "malicious"
    elif pulse_count >= _SUSPICIOUS_MIN:
        verdict = "suspicious"
    else:
        verdict = "no_data"

    return EnrichmentResult(
        ioc=ioc,
        provider=provider_name,
        verdict=verdict,
        detection_count=pulse_count,
        total_engines=1,
        scan_date=None,
        raw_stats={
            "pulse_count": pulse_count,
            "reputation": reputation,
            "type_title": type_title,
        },
    )
