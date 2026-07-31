"""Shodan InternetDB API adapter."""
from __future__ import annotations

from typing import NamedTuple

from .base import BaseHTTPAdapter
from ..models import EnrichmentResult, provider_result
from app.pipeline.models import IOC, IOCType

SHODAN_INTERNETDB_BASE = "https://internetdb.shodan.io"
_MALICIOUS_TAGS = frozenset(("malware", "compromised", "doublepulsar"))


class ShodanSignals(NamedTuple):
    ports: list[int]
    vulns: list[str]
    tags: list[str]
    hostnames: list[str]
    cpes: list[str]


def _list_field(body: dict, key: str) -> list:
    value = body.get(key)
    return value if isinstance(value, list) else []


def _shodan_signals(body: dict) -> ShodanSignals:
    return ShodanSignals(
        ports=_list_field(body, "ports"),
        vulns=_list_field(body, "vulns"),
        tags=_list_field(body, "tags"),
        hostnames=_list_field(body, "hostnames"),
        cpes=_list_field(body, "cpes"),
    )


def _raw_stats(
    *,
    ports: list[int],
    vulns: list[str],
    tags: list[str],
    hostnames: list[str],
    cpes: list[str],
) -> dict[str, list]:
    """Return the stable Shodan raw_stats envelope."""
    return {
        "ports": ports,
        "vulns": vulns,
        "tags": tags,
        "hostnames": hostnames,
        "cpes": cpes,
    }


class ShodanAdapter(BaseHTTPAdapter):
    """Shodan InternetDB endpoint — see BaseHTTPAdapter for the template pattern."""

    supported_types: frozenset[IOCType] = frozenset((IOCType.IPV4, IOCType.IPV6))
    name = "Shodan InternetDB"
    requires_api_key = False
    _no_data_on_404 = True

    def _build_url(self, ioc: IOC) -> str:
        return f"{SHODAN_INTERNETDB_BASE}/{ioc.value}"

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return _parse_response(ioc, body, self.name)


def _parse_response(ioc: IOC, body: dict, provider_name: str) -> EnrichmentResult:
    signals = _shodan_signals(body)
    verdict, detection_count = _shodan_verdict(signals.tags, signals.vulns)
    raw_stats = _raw_stats(
        ports=signals.ports,
        vulns=signals.vulns,
        tags=signals.tags,
        hostnames=signals.hostnames,
        cpes=signals.cpes,
    )

    return _shodan_result(
        ioc=ioc,
        provider_name=provider_name,
        verdict=verdict,
        detection_count=detection_count,
        total_engines=1,
        raw_stats=raw_stats,
    )


def _shodan_verdict(tags: list[str], vulns: list[str]) -> tuple[str, int]:
    if not tags and not vulns:
        return ("no_data", 0)
    if not tags:
        return ("suspicious", len(vulns))

    bad_tag_count = _malicious_tag_count(tags)
    if bad_tag_count:
        return ("malicious", bad_tag_count)
    if vulns:
        return ("suspicious", len(vulns))
    return ("no_data", 0)


def _malicious_tag_count(tags: list[str]) -> int:
    tag_count = len(tags)
    if tag_count == 1:
        return 1 if tags[0] in _MALICIOUS_TAGS else 0
    if tag_count == 2:
        bad_tag_count = 0
        if tags[0] in _MALICIOUS_TAGS:
            bad_tag_count += 1
        if tags[1] in _MALICIOUS_TAGS:
            bad_tag_count += 1
        return bad_tag_count
    if tag_count == 3:
        bad_tag_count = 0
        if tags[0] in _MALICIOUS_TAGS:
            bad_tag_count += 1
        if tags[1] in _MALICIOUS_TAGS:
            bad_tag_count += 1
        if tags[2] in _MALICIOUS_TAGS:
            bad_tag_count += 1
        return bad_tag_count
    if tag_count == 4:
        bad_tag_count = 0
        if tags[0] in _MALICIOUS_TAGS:
            bad_tag_count += 1
        if tags[1] in _MALICIOUS_TAGS:
            bad_tag_count += 1
        if tags[2] in _MALICIOUS_TAGS:
            bad_tag_count += 1
        if tags[3] in _MALICIOUS_TAGS:
            bad_tag_count += 1
        return bad_tag_count

    bad_tag_count = 0
    for tag in tags:
        if tag in _MALICIOUS_TAGS:
            bad_tag_count += 1
    return bad_tag_count


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
