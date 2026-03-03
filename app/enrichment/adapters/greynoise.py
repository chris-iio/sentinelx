"""GreyNoise Community API adapter.

Implements IP enrichment against the GreyNoise Community API with full HTTP
safety controls matching the established adapter pattern:
  - SEC-04: timeout=(5, 30) on all requests
  - SEC-05: stream=True + byte counting, 1 MB response cap
  - SEC-06: allow_redirects=False on all requests
  - SEC-07/SEC-16: ALLOWED_API_HOSTS allowlist enforced before every network call

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

GREYNOISE_BASE = "https://api.greynoise.io/v3/community"


class GreyNoiseAdapter:
    """Adapter for the GreyNoise Community API.

    Supports IP IOC lookups (IPv4 and IPv6) using the GreyNoise Community
    endpoint. Verdict is derived from the riot/noise/classification fields:

    - riot=True (known benign service) -> verdict=clean
    - classification="malicious" -> verdict=malicious
    - noise=True (active scanner) -> verdict=suspicious
    - Everything else -> verdict=no_data
    - IP not in GreyNoise (404) -> verdict=no_data

    API key required — register at https://www.greynoise.io/

    CRITICAL: Auth header is lowercase 'key' (not 'Key', 'Authorization',
    or 'X-Api-Key').

    Thread safety: uses a standalone requests.get call per lookup() invocation.
    No shared session state between calls.

    Args:
        api_key:       GreyNoise Community API key.
        allowed_hosts: SSRF allowlist -- only these hostnames may be contacted.
    """

    supported_types: frozenset[IOCType] = frozenset({IOCType.IPV4, IOCType.IPV6})
    name = "GreyNoise"
    requires_api_key = True

    def __init__(self, api_key: str, allowed_hosts: list[str]) -> None:
        self._api_key = api_key
        self._allowed_hosts = allowed_hosts

    def is_configured(self) -> bool:
        """Return True when a non-empty API key is set."""
        return bool(self._api_key)

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        """Enrich a single IP IOC using the GreyNoise Community API.

        Returns EnrichmentError immediately for non-IP types.
        Validates the GreyNoise endpoint against the SSRF allowlist before any
        network call. Makes a GET request with full safety controls and
        parses the response.

        Response semantics:
          - 200 + riot=True           -> verdict=clean
          - 200 + classification=malicious -> verdict=malicious
          - 200 + noise=True          -> verdict=suspicious
          - 200 (no signals)          -> verdict=no_data
          - 404                       -> verdict=no_data (not in database, not an error)
          - HTTP error / timeout       -> EnrichmentError

        IMPORTANT: 404 is checked BEFORE resp.raise_for_status() to prevent
        treating "not in database" responses as HTTP errors.

        Args:
            ioc: The IOC to look up. Must be IPv4 or IPv6.

        Returns:
            EnrichmentResult on success (including 404 no_data).
            EnrichmentError on unsupported type, SSRF block, or network failure.
        """
        if ioc.type not in self.supported_types:
            return EnrichmentError(
                ioc=ioc, provider=self.name, error="Unsupported type"
            )

        url = f"{GREYNOISE_BASE}/{ioc.value}"

        try:
            validate_endpoint(url, self._allowed_hosts)
        except ValueError as exc:
            return EnrichmentError(ioc=ioc, provider=self.name, error=str(exc))

        try:
            resp = requests.get(
                url,
                headers={
                    "key": self._api_key,       # CRITICAL: lowercase 'key' (GreyNoise convention)
                    "Accept": "application/json",
                },
                timeout=TIMEOUT,               # SEC-04
                allow_redirects=False,         # SEC-06
                stream=True,                   # SEC-05 setup
            )
            # CRITICAL: check 404 BEFORE raise_for_status — 404 means "no data", not an error
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
                "Unexpected error during GreyNoise lookup for %s", ioc.value
            )
            return EnrichmentError(
                ioc=ioc, provider=self.name, error="Unexpected error during lookup"
            )


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
