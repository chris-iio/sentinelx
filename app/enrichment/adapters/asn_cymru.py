"""Team Cymru DNS-based IP-to-ASN lookup adapter (port 53, not HTTP — no SSRF surface)."""
from __future__ import annotations

import ipaddress
import logging

import dns.exception
import dns.resolver

from app.enrichment.models import EnrichmentError, EnrichmentResult
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
    supported_types: frozenset[IOCType] = frozenset({IOCType.IPV4, IOCType.IPV6})
    requires_api_key = False

    def __init__(self, allowed_hosts: list[str]) -> None:
        # Accepted for API compatibility with Provider protocol; intentionally unused.
        # DNS uses port 53 directly — no HTTP, no SSRF surface.
        pass

    def is_configured(self) -> bool:
        return True

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        if ioc.type not in self.supported_types:
            return EnrichmentError(
                ioc=ioc,
                provider=self.name,
                error="Unsupported type",
            )

        try:
            ip = ipaddress.ip_address(ioc.value)
        except ValueError:
            return EnrichmentError(
                ioc=ioc,
                provider=self.name,
                error="Invalid IP address",
            )

        if ip.version == 4:
            query = ip.reverse_pointer.replace(_IPV4_SUFFIX, _CYMRU_ZONE_V4)
        else:
            query = ip.reverse_pointer.replace(_IPV6_SUFFIX, _CYMRU_ZONE_V6)

        resolver = dns.resolver.Resolver(configure=True)
        resolver.lifetime = _RESOLVER_LIFETIME

        try:
            answers = resolver.resolve(query, "TXT")
            txt = b"".join(list(answers)[0].strings).decode("utf-8", errors="replace")
            return _parse_response(ioc, txt, self.name)
        except dns.resolver.NXDOMAIN:
            # Private/RFC-1918 IPs or unrouted space have no BGP route — expected.
            return EnrichmentResult(
                ioc=ioc,
                provider=self.name,
                verdict="no_data",
                detection_count=0,
                total_engines=0,
                scan_date=None,
                raw_stats={},
            )
        except (dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.exception.Timeout):
            # Expected DNS conditions — no data available, not an error.
            return EnrichmentResult(
                ioc=ioc,
                provider=self.name,
                verdict="no_data",
                detection_count=0,
                total_engines=0,
                scan_date=None,
                raw_stats={},
            )
        except Exception:
            logger.exception("Unexpected error during Cymru ASN lookup for %s", ioc.value)
            return EnrichmentError(
                ioc=ioc,
                provider=self.name,
                error="Unexpected error",
            )


def _parse_response(ioc: IOC, txt: str, provider_name: str) -> EnrichmentResult:
    """Parse a pipe-delimited Cymru TXT record: "ASN | prefix | cc | rir | allocated"."""
    # Verdict always no_data — ASN context is informational, not a threat signal.
    parts = [p.strip() for p in txt.split("|")]
    raw_stats = {
        "asn":       parts[0] if len(parts) > 0 else "",
        "prefix":    parts[1] if len(parts) > 1 else "",
        "rir":       parts[3] if len(parts) > 3 else "",
        "allocated": parts[4] if len(parts) > 4 else "",
    }
    return EnrichmentResult(
        ioc=ioc,
        provider=provider_name,
        verdict="no_data",
        detection_count=0,
        total_engines=0,
        scan_date=None,
        raw_stats=raw_stats,
    )
