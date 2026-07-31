"""Team Cymru DNS-based IP-to-ASN lookup adapter (port 53, not HTTP — no SSRF surface)."""
from __future__ import annotations

import ipaddress
import logging

import dns.exception
import dns.resolver

from .dns_txt import decode_txt_chunks
from ..models import EnrichmentError, EnrichmentResult, error_result, no_data_result
from app.pipeline.models import IOC, IOCType

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

    def is_configured(self) -> bool:
        return True

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        if ioc.type not in self.supported_types:
            return error_result(ioc, self.name, "Unsupported type")

        try:
            ip = ipaddress.ip_address(ioc.value)
        except ValueError:
            return error_result(ioc, self.name, "Invalid IP address")

        try:
            answers = _configured_resolver().resolve(_cymru_query_name(ip), "TXT")
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


def _cymru_query_name(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> str:
    if ip.version == 4:
        return ip.reverse_pointer.replace(_IPV4_SUFFIX, _CYMRU_ZONE_V4)
    return ip.reverse_pointer.replace(_IPV6_SUFFIX, _CYMRU_ZONE_V6)


def _configured_resolver():
    resolver = dns.resolver.Resolver(configure=True)
    resolver.lifetime = _RESOLVER_LIFETIME
    return resolver


def _parse_response(ioc: IOC, txt: str, provider_name: str) -> EnrichmentResult:
    """Parse a pipe-delimited Cymru TXT record: "ASN | prefix | cc | rir | allocated"."""
    # Verdict always no_data — ASN context is informational, not a threat signal.
    return _no_data_result(
        ioc=ioc,
        provider_name=provider_name,
        raw_stats=_asn_raw_stats(txt),
    )


def _asn_raw_stats(txt: str) -> dict:
    asn, prefix, _country, rir, allocated = _parse_txt_fields(txt)
    return {
        "asn": asn,
        "prefix": prefix,
        "rir": rir,
        "allocated": allocated,
    }


def _decode_txt_strings(strings) -> str:
    return decode_txt_chunks(strings)


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
