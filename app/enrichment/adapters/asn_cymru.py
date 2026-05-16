"""Team Cymru DNS-based IP-to-ASN lookup adapter (port 53, not HTTP — no SSRF surface)."""
from __future__ import annotations

import ipaddress
import logging

import dns.exception
import dns.resolver

from app.enrichment.models import EnrichmentError, EnrichmentResult, error_result, no_data_result
from app.pipeline.models import IOC, IOCType
from app.text_utils import decode_utf8_replace

logger = logging.getLogger(__name__)

# Resolver timeout in seconds (float, not HTTP connect/read tuple).
_RESOLVER_LIFETIME: float = 5.0

# Suffix constants for zone substitution.
_IPV4_SUFFIX = ".in-addr.arpa"
_IPV6_SUFFIX = ".ip6.arpa"
_CYMRU_ZONE_V4 = ".origin.asn.cymru.com"
_CYMRU_ZONE_V6 = ".origin6.asn.cymru.com"


class CymruASNAdapter:
    """Team Cymru IP-to-ASN lookup via DNS TXT queries — verdict always no_data."""

    name = "ASN Intel"
    supported_types: frozenset[IOCType] = frozenset((IOCType.IPV4, IOCType.IPV6))
    requires_api_key = False

    def __init__(self, allowed_hosts: list[str]) -> None:
        # Accepted for API compatibility with Provider protocol; intentionally unused.
        # DNS uses port 53 directly — no HTTP, no SSRF surface.
        pass

    def is_configured(self) -> bool:
        return True

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        if ioc.type not in self.supported_types:
            return error_result(ioc, self.name, "Unsupported type")

        try:
            ip = ipaddress.ip_address(ioc.value)
        except ValueError:
            return error_result(ioc, self.name, "Invalid IP address")

        if ip.version == 4:
            query = ip.reverse_pointer.replace(_IPV4_SUFFIX, _CYMRU_ZONE_V4)
        else:
            query = ip.reverse_pointer.replace(_IPV6_SUFFIX, _CYMRU_ZONE_V6)

        resolver = dns.resolver.Resolver(configure=True)
        resolver.lifetime = _RESOLVER_LIFETIME

        try:
            answers = resolver.resolve(query, "TXT")
            txt = _decode_txt_strings(next(iter(answers)).strings)
            return _parse_response(ioc, txt, self.name)
        except dns.resolver.NXDOMAIN:
            # Private/RFC-1918 IPs or unrouted space have no BGP route — expected.
            return _no_data_result(ioc, self.name)
        except (dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.exception.Timeout):
            # Expected DNS conditions — no data available, not an error.
            return _no_data_result(ioc, self.name)
        except Exception:
            logger.exception("Unexpected error during Cymru ASN lookup for %s", ioc.value)
            return error_result(ioc, self.name, "Unexpected error")


def _parse_response(ioc: IOC, txt: str, provider_name: str) -> EnrichmentResult:
    """Parse a pipe-delimited Cymru TXT record: "ASN | prefix | cc | rir | allocated"."""
    # Verdict always no_data — ASN context is informational, not a threat signal.
    asn, prefix, _country, rir, allocated = _parse_txt_fields(txt)
    raw_stats = {
        "asn": asn,
        "prefix": prefix,
        "rir": rir,
        "allocated": allocated,
    }
    return _no_data_result(
        ioc=ioc,
        provider_name=provider_name,
        raw_stats=raw_stats,
    )


def _decode_txt_strings(strings) -> str:
    string_count = len(strings)
    if string_count == 1:
        raw_text = strings[0]
    elif string_count == 2:
        raw_text = strings[0] + strings[1]
    elif string_count == 3:
        raw_text = strings[0] + strings[1] + strings[2]
    else:
        raw_text = b"".join(strings)
    return decode_utf8_replace(raw_text)


def _no_data_result(
    ioc: IOC,
    provider_name: str,
    raw_stats: dict | None = None,
) -> EnrichmentResult:
    return no_data_result(ioc, provider_name, raw_stats)


def _parse_txt_fields(txt: str) -> tuple[str, str, str, str, str]:
    """Extract up to five pipe-delimited fields without allocating field lists."""
    asn, start, found = _next_txt_field(txt, 0)
    if not found:
        return asn, "", "", "", ""

    prefix, start, found = _next_txt_field(txt, start)
    if not found:
        return asn, prefix, "", "", ""

    country, start, found = _next_txt_field(txt, start)
    if not found:
        return asn, prefix, country, "", ""

    rir, start, found = _next_txt_field(txt, start)
    if not found:
        return asn, prefix, country, rir, ""

    allocated = _strip_txt_field(txt, start, len(txt))
    return asn, prefix, country, rir, allocated


def _strip_txt_field(txt: str, start: int, end: int) -> str:
    while start < end and txt[start].isspace():
        start += 1
    while end > start and txt[end - 1].isspace():
        end -= 1
    return txt[start:end]


def _next_txt_field(txt: str, start: int) -> tuple[str, int, bool]:
    separator = txt.find("|", start)
    if separator < 0:
        return _strip_txt_field(txt, start, len(txt)), len(txt), False
    return _strip_txt_field(txt, start, separator), separator + 1, True
