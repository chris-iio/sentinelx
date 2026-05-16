"""Shodan InternetDB API adapter."""
from __future__ import annotations

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.models import EnrichmentResult, no_data_result, provider_result
from app.pipeline.models import IOC, IOCType

SHODAN_INTERNETDB_BASE = "https://internetdb.shodan.io"
_MALICIOUS_TAGS = frozenset(("malware", "compromised", "doublepulsar"))


def _list_field(body: dict, key: str) -> list:
    value = body.get(key)
    return value if isinstance(value, list) else []


class ShodanAdapter(BaseHTTPAdapter):
    """Shodan InternetDB endpoint — see BaseHTTPAdapter for the template pattern."""

    supported_types: frozenset[IOCType] = frozenset((IOCType.IPV4, IOCType.IPV6))
    name = "Shodan InternetDB"
    requires_api_key = False

    def _build_url(self, ioc: IOC) -> str:
        return f"{SHODAN_INTERNETDB_BASE}/{ioc.value}"

    def _make_pre_raise_hook(self, ioc: IOC):
        def _404_hook(resp):
            if resp.status_code == 404:
                return no_data_result(ioc, self.name)
            return None
        return _404_hook

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return _parse_response(ioc, body, self.name)


def _parse_response(ioc: IOC, body: dict, provider_name: str) -> EnrichmentResult:
    vulns: list[str] = _list_field(body, "vulns")
    tags: list[str] = _list_field(body, "tags")
    ports: list[int] = _list_field(body, "ports")
    hostnames: list[str] = _list_field(body, "hostnames")
    cpes: list[str] = _list_field(body, "cpes")

    if not tags and not vulns:
        return _shodan_result(
            ioc=ioc,
            provider_name=provider_name,
            verdict="no_data",
            detection_count=0,
            total_engines=1,
            raw_stats={
                "ports": ports,
                "vulns": vulns,
                "tags": tags,
                "hostnames": hostnames,
                "cpes": cpes,
            },
        )

    if not tags:
        return _shodan_result(
            ioc=ioc,
            provider_name=provider_name,
            verdict="suspicious",
            detection_count=len(vulns),
            total_engines=1,
            raw_stats={
                "ports": ports,
                "vulns": vulns,
                "tags": tags,
                "hostnames": hostnames,
                "cpes": cpes,
            },
        )

    tag_count = len(tags)
    if tag_count == 1:
        bad_tag_count = 1 if tags[0] in _MALICIOUS_TAGS else 0
    elif tag_count == 2:
        bad_tag_count = 0
        if tags[0] in _MALICIOUS_TAGS:
            bad_tag_count += 1
        if tags[1] in _MALICIOUS_TAGS:
            bad_tag_count += 1
    elif tag_count == 3:
        bad_tag_count = 0
        if tags[0] in _MALICIOUS_TAGS:
            bad_tag_count += 1
        if tags[1] in _MALICIOUS_TAGS:
            bad_tag_count += 1
        if tags[2] in _MALICIOUS_TAGS:
            bad_tag_count += 1
    else:
        bad_tag_count = 0
        for tag in tags:
            if tag in _MALICIOUS_TAGS:
                bad_tag_count += 1

    if bad_tag_count:
        verdict = "malicious"
        detection_count = bad_tag_count
    elif vulns:
        verdict = "suspicious"
        detection_count = len(vulns)
    else:
        verdict = "no_data"
        detection_count = 0

    return _shodan_result(
        ioc=ioc,
        provider_name=provider_name,
        verdict=verdict,
        detection_count=detection_count,
        total_engines=1,
        raw_stats={
            "ports": ports,
            "vulns": vulns,
            "tags": tags,
            "hostnames": hostnames,
            "cpes": cpes,
        },
    )


def _shodan_result(
    *,
    ioc: IOC,
    provider_name: str,
    verdict: str,
    detection_count: int,
    total_engines: int,
    raw_stats: dict | None = None,
) -> EnrichmentResult:
    return provider_result(
        ioc=ioc,
        provider=provider_name,
        verdict=verdict,
        detection_count=detection_count,
        total_engines=total_engines,
        scan_date=None,
        raw_stats=raw_stats,
    )
