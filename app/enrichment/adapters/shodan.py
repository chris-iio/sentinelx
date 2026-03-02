"""Shodan InternetDB API adapter.

Implements IP enrichment against the Shodan InternetDB API with full HTTP
safety controls matching the MBAdapter pattern:
  - SEC-04: timeout=(5, 30) on all requests
  - SEC-05: stream=True + byte counting, 1 MB response cap
  - SEC-06: allow_redirects=False on all requests
  - SEC-07/SEC-16: ALLOWED_API_HOSTS allowlist enforced before every network call

InternetDB API behavior:
  - GET https://internetdb.shodan.io/{ip}  (path param, not query string)
  - 200: {ip, ports, hostnames, cpes, vulns, tags}
  - 404: {"detail": "No information available"} -> verdict=no_data (not an error)
  - 422: validation error -> EnrichmentError("HTTP 422")
  - 429: rate limited -> EnrichmentError("HTTP 429")

Verdict priority (high to low):
  1. tags contains "malware", "compromised", or "doublepulsar" -> malicious
  2. vulns is non-empty -> suspicious
  3. has data but no vulns/bad tags -> no_data
  4. 404 -> no_data

No API key required — InternetDB is a public zero-auth endpoint.

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

SHODAN_INTERNETDB_BASE = "https://internetdb.shodan.io"
_MALICIOUS_TAGS = frozenset({"malware", "compromised", "doublepulsar"})


class ShodanAdapter:
    """Adapter for the Shodan InternetDB API.

    Supports IP IOC lookups (IPv4 and IPv6) using the zero-auth Shodan
    InternetDB public endpoint. Verdict is derived from CVEs and bad tags:

    - Malicious tags (malware/compromised/doublepulsar) -> verdict=malicious
    - Known CVEs (vulns list) -> verdict=suspicious
    - IP data but no vulns or bad tags -> verdict=no_data
    - IP not in Shodan (404) -> verdict=no_data

    No API key required — InternetDB is fully public.

    Thread safety: uses a standalone requests.get call per lookup() invocation.
    No shared session state between calls.

    Args:
        allowed_hosts: SSRF allowlist -- only these hostnames may be contacted.
    """

    supported_types: frozenset[IOCType] = frozenset({IOCType.IPV4, IOCType.IPV6})
    name = "Shodan InternetDB"
    requires_api_key = False

    def __init__(self, allowed_hosts: list[str]) -> None:
        self._allowed_hosts = allowed_hosts

    def is_configured(self) -> bool:
        """Always returns True -- Shodan InternetDB requires no API key."""
        return True

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        """Enrich a single IP IOC using the Shodan InternetDB API.

        Returns EnrichmentError immediately for non-IP types.
        Validates the InternetDB endpoint against the SSRF allowlist before any
        network call. Makes a GET request with full safety controls and
        parses the response.

        Response semantics:
          - 200 + malicious tags -> verdict=malicious
          - 200 + vulns list     -> verdict=suspicious
          - 200 + ports only     -> verdict=no_data
          - 404                  -> verdict=no_data (not an error)
          - HTTP error / timeout  -> EnrichmentError

        IMPORTANT: 404 is checked BEFORE resp.raise_for_status() to prevent
        treating "no data" responses as HTTP errors.

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

        url = f"{SHODAN_INTERNETDB_BASE}/{ioc.value}"

        try:
            validate_endpoint(url, self._allowed_hosts)
        except ValueError as exc:
            return EnrichmentError(ioc=ioc, provider=self.name, error=str(exc))

        try:
            resp = requests.get(
                url,
                timeout=TIMEOUT,           # SEC-04
                allow_redirects=False,     # SEC-06
                stream=True,               # SEC-05 setup
            )
            # CRITICAL: check 404 BEFORE raise_for_status — 404 is "no data", not an error
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
            body = read_limited(resp)     # SEC-05: byte cap enforced
            return _parse_response(ioc, body, self.name)
        except requests.exceptions.Timeout:
            return EnrichmentError(ioc=ioc, provider=self.name, error="Timeout")
        except requests.exceptions.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else "unknown"
            return EnrichmentError(ioc=ioc, provider=self.name, error=f"HTTP {code}")
        except Exception:
            logger.exception(
                "Unexpected error during Shodan lookup for %s", ioc.value
            )
            return EnrichmentError(
                ioc=ioc, provider=self.name, error="Unexpected error during lookup"
            )


def _parse_response(ioc: IOC, body: dict, provider_name: str) -> EnrichmentResult:
    """Parse a Shodan InternetDB API response into an EnrichmentResult.

    Extracts vulns, tags, ports, hostnames, and cpes from the response body.
    Applies verdict priority: malicious tags > vulns > no_data.

    Args:
        ioc:           The IOC that was queried.
        body:          Parsed JSON from InternetDB API response.
        provider_name: Provider name string for result construction.

    Returns:
        EnrichmentResult with verdict "malicious", "suspicious", or "no_data".
    """
    vulns: list[str] = body.get("vulns", [])
    tags: list[str] = body.get("tags", [])
    ports: list[int] = body.get("ports", [])
    hostnames: list[str] = body.get("hostnames", [])
    cpes: list[str] = body.get("cpes", [])

    bad_tags = [t for t in tags if t in _MALICIOUS_TAGS]

    if bad_tags:
        verdict = "malicious"
        detection_count = len(bad_tags)
    elif vulns:
        verdict = "suspicious"
        detection_count = len(vulns)
    else:
        verdict = "no_data"
        detection_count = 0

    return EnrichmentResult(
        ioc=ioc,
        provider=provider_name,
        verdict=verdict,
        detection_count=detection_count,
        total_engines=1,
        scan_date=None,
        raw_stats={
            "ports": ports,
            "vulns": vulns,
            "tags": tags,
            "hostnames": hostnames,
            "cpes": cpes,
        },
    )
