"""GreyNoise Community API adapter.

Implements IP enrichment against the GreyNoise Community API. Delegates all HTTP
safety controls to safe_request() in http_safety.py.

GreyNoise Community API behavior:
  - GET https://api.greynoise.io/v3/community/{ip}
  - Auth header: 'key' (lowercase) with the API key value
  - 200: {ip, noise, riot, classification, name, link, last_seen, message}
  - 404: IP not in GreyNoise database -> verdict=no_data (not an error)
  - 429: rate limited -> EnrichmentError("HTTP 429")
  - 401: unauthorized -> EnrichmentError("HTTP 401")

Verdict priority (high to low):
  1. riot == True  -> "clean"   (known benign: Google DNS, Cloudflare, etc.)
  2. classification == "malicious" -> "malicious"
  3. noise == True -> "suspicious" (active scanner, not explicitly malicious)
  4. Else -> "no_data"

API key required — GreyNoise Community API requires registration.
"""
from __future__ import annotations

import logging

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)

GREYNOISE_BASE = "https://api.greynoise.io/v3/community"


class GreyNoiseAdapter(BaseHTTPAdapter):
    """Adapter for the GreyNoise Community API.

    Extends BaseHTTPAdapter for IP enrichment against the GreyNoise Community
    endpoint. All HTTP safety controls (SSRF allowlist, size cap, timeouts) are
    inherited.

    Verdict is derived from the riot/noise/classification fields:

    - riot=True (known benign service) -> verdict=clean
    - classification="malicious" -> verdict=malicious
    - noise=True (active scanner) -> verdict=suspicious
    - Everything else -> verdict=no_data
    - IP not in GreyNoise (404) -> verdict=no_data

    API key required — register at https://www.greynoise.io/

    CRITICAL: Auth header is lowercase 'key' (not 'Key', 'Authorization',
    or 'X-Api-Key').

    Thread safety: a persistent requests.Session is created by BaseHTTPAdapter.__init__
    and reused across lookup() calls for TCP connection pooling.

    Args:
        allowed_hosts: SSRF allowlist -- only these hostnames may be contacted.
        api_key:       GreyNoise Community API key (keyword-only).
    """

    supported_types: frozenset[IOCType] = frozenset({IOCType.IPV4, IOCType.IPV6})
    name = "GreyNoise"
    requires_api_key = True

    def _build_url(self, ioc: IOC) -> str:
        return f"{GREYNOISE_BASE}/{ioc.value}"

    def _auth_headers(self) -> dict:
        return {
            "key": self._api_key,  # CRITICAL: lowercase 'key' (GreyNoise convention)
        }

    def _make_pre_raise_hook(self, ioc: IOC):
        def _404_hook(resp):
            if resp.status_code == 404:
                return EnrichmentResult(
                    ioc=ioc,
                    provider=self.name,
                    verdict="no_data",
                    detection_count=0,
                    total_engines=1,
                    scan_date=None,
                    raw_stats={},
                )
            return None
        return _404_hook

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return _parse_response(ioc, body, self.name)


def _parse_response(ioc: IOC, body: dict, provider_name: str) -> EnrichmentResult:
    """Parse a GreyNoise Community API response into an EnrichmentResult.

    Applies verdict priority: riot > malicious classification > noise > no_data.

    Verdict rules:
      - riot=True               -> "clean"      (known benign service)
      - classification="malicious" -> "malicious"
      - noise=True              -> "suspicious" (active internet scanner)
      - else                    -> "no_data"

    detection_count is 1 for malicious/suspicious, 0 for clean/no_data.

    Args:
        ioc:           The IOC that was queried.
        body:          Parsed JSON from GreyNoise Community API response.
        provider_name: Provider name string for result construction.

    Returns:
        EnrichmentResult with verdict "clean", "malicious", "suspicious", or "no_data".
    """
    riot: bool = body.get("riot", False)
    noise: bool = body.get("noise", False)
    classification: str = body.get("classification", "") or ""
    name: str = body.get("name", "") or ""
    link: str = body.get("link", "") or ""
    last_seen: str | None = body.get("last_seen")

    if riot:
        verdict = "clean"
        detection_count = 0
    elif classification == "malicious":
        verdict = "malicious"
        detection_count = 1
    elif noise:
        verdict = "suspicious"
        detection_count = 1
    else:
        verdict = "no_data"
        detection_count = 0

    return EnrichmentResult(
        ioc=ioc,
        provider=provider_name,
        verdict=verdict,
        detection_count=detection_count,
        total_engines=1,
        scan_date=last_seen,
        raw_stats={
            "noise": noise,
            "riot": riot,
            "classification": classification,
            "name": name,
            "link": link,
            "last_seen": last_seen,
        },
    )
