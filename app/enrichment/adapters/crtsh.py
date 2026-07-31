"""crt.sh certificate transparency adapter."""
from __future__ import annotations

from collections.abc import Iterator
from heapq import nsmallest

from .base import BaseHTTPAdapter
from ..models import EnrichmentResult, no_data_result
from app.pipeline.models import IOC, IOCType
from app.text_utils import stripped_text_or_none

CRTSH_BASE = "https://crt.sh"

# Maximum number of unique subdomains to include in raw_stats
_SUBDOMAIN_CAP = 50


def _capped_sorted_subdomains(subdomains: set[str]) -> list[str]:
    subdomain_count = len(subdomains)
    if subdomain_count == 0:
        return []
    if subdomain_count == 1:
        for subdomain in subdomains:
            return [subdomain]
    if subdomain_count == 2:
        first = ""
        second = ""
        for subdomain in subdomains:
            if not first:
                first = subdomain
            else:
                second = subdomain
                break
        if first <= second:
            return [first, second]
        return [second, first]
    if subdomain_count == 3:
        first = ""
        second = ""
        third = ""
        for subdomain in subdomains:
            if not first:
                first = subdomain
            elif not second:
                second = subdomain
            else:
                third = subdomain
                break
        if first > second:
            first, second = second, first
        if second > third:
            second, third = third, second
            if first > second:
                first, second = second, first
        return [first, second, third]
    if subdomain_count == 4:
        first = ""
        second = ""
        third = ""
        fourth = ""
        for subdomain in subdomains:
            if not first:
                first = subdomain
            elif not second:
                second = subdomain
            elif not third:
                third = subdomain
            else:
                fourth = subdomain
                break
        if first > second:
            first, second = second, first
        if third > fourth:
            third, fourth = fourth, third
        if first > third:
            first, third = third, first
        if second > fourth:
            second, fourth = fourth, second
        if second > third:
            second, third = third, second
        return [first, second, third, fourth]
    if subdomain_count <= _SUBDOMAIN_CAP:
        ordered: list[str] = []
        for subdomain in subdomains:
            append_ordered_subdomain(ordered, subdomain)
        return ordered
    return nsmallest(_SUBDOMAIN_CAP, subdomains)


def append_ordered_subdomain(ordered: list[str], subdomain: str) -> None:
    subdomain_count = len(ordered)
    if subdomain_count == 0:
        ordered.append(subdomain)
        return

    index = 0
    while index < subdomain_count:
        if subdomain <= ordered[index]:
            ordered.insert(index, subdomain)
            return
        index += 1

    ordered.append(subdomain)


def _iter_name_values(name_value: str) -> Iterator[str]:
    start = 0
    while True:
        separator = name_value.find("\n", start)
        if separator < 0:
            yield name_value[start:]
            return
        yield name_value[start:separator]
        start = separator + 1


def _trim_wildcard_prefix(name: str) -> str:
    start = 0
    end = len(name)
    while start < end and name[start] in "*.":
        start += 1
    return name[start:end]


def _clean_name_value(raw_name: str) -> str | None:
    """Return a normalized crt.sh SAN value, or None when blank."""
    stripped = stripped_text_or_none(raw_name)
    if stripped is None:
        return None
    cleaned = _trim_wildcard_prefix(stripped).lower()
    return cleaned or None


class CrtShAdapter(BaseHTTPAdapter):
    """crt.sh CT search endpoint."""

    supported_types: frozenset[IOCType] = frozenset((IOCType.DOMAIN,))
    name = "Cert History"
    requires_api_key = False

    def _build_url(self, ioc: IOC) -> str:
        return f"{CRTSH_BASE}/?q={ioc.value}&output=json"

    def _parse_response(self, ioc: IOC, body: list) -> EnrichmentResult:
        return _parse_response(ioc, body, self.name)  # type: ignore[arg-type]


def _parse_response(ioc: IOC, body: list, provider_name: str) -> EnrichmentResult:
    # Empty response: no certificates found
    if not body:
        return _crtsh_result(
            ioc=ioc,
            provider=provider_name,
            raw_stats={},
        )

    cert_count = len(body)

    return _crtsh_result(
        ioc=ioc,
        provider=provider_name,
        raw_stats=_crtsh_raw_stats(body=body, cert_count=cert_count),
    )


def _crtsh_raw_stats(*, body: list, cert_count: int) -> dict:
    # Collect date range and subdomains from name_value (SANs).
    earliest = ""
    latest = ""
    subdomain_set: set[str] = set()
    for entry in body:
        not_before = entry.get("not_before")
        if not_before:
            cert_date = not_before[:10]
            if not earliest or cert_date < earliest:
                earliest = cert_date
            if not latest or cert_date > latest:
                latest = cert_date

        name_value = entry.get("name_value")
        if not name_value:
            continue
        add_name_value_subdomains(subdomain_set, name_value)

    # Sort alphabetically, cap at _SUBDOMAIN_CAP
    subdomains = _capped_sorted_subdomains(subdomain_set)

    return {
        "cert_count": cert_count,
        "earliest": earliest,
        "latest": latest,
        "subdomains": subdomains,
    }


def add_name_value_subdomains(subdomains: set[str], name_value: str) -> None:
    for raw_name in _iter_name_values(name_value):
        cleaned = _clean_name_value(raw_name)
        if cleaned is not None:
            subdomains.add(cleaned)


def _crtsh_result(*, ioc: IOC, provider: str, raw_stats: dict) -> EnrichmentResult:
    return no_data_result(ioc, provider, raw_stats)
