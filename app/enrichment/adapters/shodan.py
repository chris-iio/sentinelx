"""Shodan InternetDB API adapter.

Subclasses BaseHTTPAdapter for IP enrichment against the Shodan InternetDB API.
All HTTP safety controls (SSRF allowlist, size cap, timeouts) are inherited.

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
"""
from __future__ import annotations

import logging

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.models import EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)

SHODAN_INTERNETDB_BASE = "https://internetdb.shodan.io"
_MALICIOUS_TAGS = frozenset({"malware", "compromised", "doublepulsar"})


class ShodanAdapter(BaseHTTPAdapter):
    """Adapter for the Shodan InternetDB API.

    Supports IP IOC lookups (IPv4 and IPv6) using the zero-auth Shodan
    InternetDB public endpoint. Verdict is derived from CVEs and bad tags:

    - Malicious tags (malware/compromised/doublepulsar) -> verdict=malicious
    - Known CVEs (vulns list) -> verdict=suspicious
    - IP data but no vulns or bad tags -> verdict=no_data
    - IP not in Shodan (404) -> verdict=no_data

    No API key required — InternetDB is fully public.

    Thread safety: a persistent requests.Session is created by BaseHTTPAdapter.__init__
    and reused across lookup() calls for TCP connection pooling.

    Args:
        allowed_hosts: SSRF allowlist -- only these hostnames may be contacted.
    """

    supported_types: frozenset[IOCType] = frozenset({IOCType.IPV4, IOCType.IPV6})
    name = "Shodan InternetDB"
    requires_api_key = False

    def _build_url(self, ioc: IOC) -> str:
        return f"{SHODAN_INTERNETDB_BASE}/{ioc.value}"

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
