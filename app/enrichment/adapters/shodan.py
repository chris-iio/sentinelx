"""Shodan InternetDB API adapter."""
from __future__ import annotations

import logging

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.models import EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)

SHODAN_INTERNETDB_BASE = "https://internetdb.shodan.io"
_MALICIOUS_TAGS = frozenset({"malware", "compromised", "doublepulsar"})


class ShodanAdapter(BaseHTTPAdapter):
    """Shodan InternetDB endpoint — see BaseHTTPAdapter for the template pattern."""

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
