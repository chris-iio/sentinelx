"""OTX AlienVault API adapter.

Implements IP, domain, URL, hash (MD5/SHA1/SHA256), and CVE enrichment against
the OTX AlienVault v1 API with full HTTP safety controls matching the ShodanAdapter
pattern:
  - SEC-04: timeout=(5, 30) on all requests
  - SEC-05: stream=True + byte counting, 1 MB response cap
  - SEC-06: allow_redirects=False on all requests
  - SEC-07/SEC-16: ALLOWED_API_HOSTS allowlist enforced before every network call

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

404 response -> no_data (not an error) — MUST be checked BEFORE raise_for_status.

Supports 8 IOCType values (all except EMAIL) including CVE (the first CVE-capable provider).

Thread safety: a fresh requests.get call is used per lookup() call (no shared Session).
"""
from __future__ import annotations

import logging

import requests
import requests.exceptions

from app.enrichment.http_safety import TIMEOUT, read_limited, validate_endpoint
from app.enrichment.models import EnrichmentError, EnrichmentResult
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


class OTXAdapter:
    """Adapter for the OTX AlienVault v1 API.

    Supports 8 IOC types (IPV4, IPV6, DOMAIN, URL, MD5, SHA1, SHA256, CVE).
    EMAIL is intentionally excluded — OTX has no email lookup endpoint.
    Uses GET requests with X-OTX-API-KEY header.

    Verdict is derived from pulse_info.count in the response:
    - count >= 5  -> malicious
    - count 1-4   -> suspicious
    - count == 0  -> no_data
    - 404         -> no_data (IOC not in OTX)

    All hash types (MD5, SHA1, SHA256) map to the "file" endpoint path.

    Args:
        api_key:       OTX API key for the X-OTX-API-KEY header.
        allowed_hosts: SSRF allowlist -- only these hostnames may be contacted.
    """

    supported_types: frozenset[IOCType] = frozenset({
        IOCType.IPV4, IOCType.IPV6, IOCType.DOMAIN, IOCType.URL,
        IOCType.MD5, IOCType.SHA1, IOCType.SHA256, IOCType.CVE,
    })  # EMAIL excluded — OTX has no email lookup endpoint
    name = "OTX AlienVault"
    requires_api_key = True

    def __init__(self, api_key: str, allowed_hosts: list[str]) -> None:
        self._api_key = api_key
        self._allowed_hosts = allowed_hosts

    def is_configured(self) -> bool:
        """Return True if a non-empty API key is set."""
        return bool(self._api_key)

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        """Enrich a single IOC using the OTX AlienVault API.

        Supports 8 IOC types (IPV4, IPV6, DOMAIN, URL, MD5, SHA1, SHA256, CVE).
        EMAIL is not supported — callers should check supported_types before calling.
        Validates the OTX endpoint against the SSRF allowlist before any network call.
        Makes a GET request with full safety controls and derives verdict from
        pulse_info.count.

        Response semantics:
          - pulse_info.count >= 5 -> verdict=malicious
          - pulse_info.count 1-4  -> verdict=suspicious
          - pulse_info.count == 0 -> verdict=no_data
          - 404                   -> verdict=no_data (not an error)
          - HTTP 500+             -> EnrichmentError

        IMPORTANT: 404 is checked BEFORE resp.raise_for_status() to prevent
        treating "no data" responses as HTTP errors.

        Args:
            ioc: The IOC to look up. All IOCType values are supported.

        Returns:
            EnrichmentResult on success (including 404 no_data).
            EnrichmentError on SSRF block or network failure.
        """
        otx_type = _OTX_TYPE_MAP[ioc.type]
        url = f"{OTX_BASE}/{otx_type}/{ioc.value}/general"

        try:
            validate_endpoint(url, self._allowed_hosts)
        except ValueError as exc:
            return EnrichmentError(ioc=ioc, provider=self.name, error=str(exc))

        try:
            resp = requests.get(
                url,
                headers={
                    "X-OTX-API-KEY": self._api_key,
                    "Accept": "application/json",
                },
                timeout=TIMEOUT,               # SEC-04
                allow_redirects=False,         # SEC-06
                stream=True,                   # SEC-05 setup
            )
            # CRITICAL: check 404 BEFORE raise_for_status — 404 means "not in OTX", not an error
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
            resp.raise_for_status()
            body = read_limited(resp)          # SEC-05: byte cap enforced
            return _parse_response(ioc, body, self.name)
        except requests.exceptions.Timeout:
            return EnrichmentError(ioc=ioc, provider=self.name, error="Timeout")
        except requests.exceptions.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else "unknown"
            return EnrichmentError(ioc=ioc, provider=self.name, error=f"HTTP {code}")
        except Exception:
            logger.exception(
                "Unexpected error during OTX lookup for %s", ioc.value
            )
            return EnrichmentError(
                ioc=ioc, provider=self.name, error="Unexpected error during lookup"
            )


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
