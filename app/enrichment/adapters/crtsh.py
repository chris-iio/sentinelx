"""crt.sh certificate transparency adapter."""
from __future__ import annotations

from collections.abc import Iterator
from heapq import nsmallest

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.http_safety import safe_request
from app.enrichment.models import EnrichmentError, EnrichmentResult, error_result, no_data_result
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
    if subdomain_count <= _SUBDOMAIN_CAP:
        return sorted(subdomains)
    return nsmallest(_SUBDOMAIN_CAP, subdomains)


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
    """crt.sh CT search endpoint — overrides lookup() for JSON-list responses."""

    supported_types: frozenset[IOCType] = frozenset((IOCType.DOMAIN,))
    name = "Cert History"
    requires_api_key = False

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        if ioc.type not in self.supported_types:
            return error_result(ioc, self.name, "Unsupported type")

        url = self._build_url(ioc)
        result = safe_request(
            self._session, url, self._allowed_hosts, ioc, self.name,
        )
        if isinstance(result, EnrichmentError):
            return result
        return _parse_response(ioc, result, self.name)

    def _build_url(self, ioc: IOC) -> str:
        return f"{CRTSH_BASE}/?q={ioc.value}&output=json"

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        # Not called by our lookup() override, but required by the abstract interface.
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
        for raw_name in _iter_name_values(name_value):
            cleaned = _clean_name_value(raw_name)
            if cleaned is not None:
                subdomain_set.add(cleaned)

    # Sort alphabetically, cap at _SUBDOMAIN_CAP
    subdomains = _capped_sorted_subdomains(subdomain_set)

    return _crtsh_result(
        ioc=ioc,
        provider=provider_name,
        raw_stats={
            "cert_count": cert_count,
            "earliest": earliest,
            "latest": latest,
            "subdomains": subdomains,
        },
    )


def _crtsh_result(*, ioc: IOC, provider: str, raw_stats: dict) -> EnrichmentResult:
    return no_data_result(ioc, provider, raw_stats)
