"""Team Cymru DNS-based IP-to-ASN lookup adapter.

Implements ASN/BGP intelligence for IP IOCs using the Team Cymru DNS mapping service.
Queries the reversed IP address against origin.asn.cymru.com (IPv4) or
origin6.asn.cymru.com (IPv6) and parses the TXT response containing ASN, CIDR prefix,
RIR, and allocation date.

Design notes:
  - DNS uses port 53 directly — NOT HTTP. Do NOT import or use http_safety.py.
    validate_endpoint(), TIMEOUT, and read_limited() are HTTP-specific controls
    that are irrelevant and must not be used here.
  - No API key required — queries the Team Cymru public DNS service directly.
  - allowed_hosts parameter is accepted for API compatibility with the Provider
    protocol (other adapters pass it in from setup.py) but is intentionally
    ignored here. DNS does not make HTTP calls; there is no SSRF surface.
  - resolver.lifetime=5.0 (seconds): a single float timeout for the resolver,
    distinct from the (connect, read) tuple used by HTTP adapters.
  - NXDOMAIN is expected for private/RFC-1918 IPs (no BGP route) — return
    EnrichmentResult(verdict='no_data') mirroring how IPApiAdapter handles
    private IPs.
  - verdict is always 'no_data' — ASN context is informational, not a threat
    signal.

Thread safety: a fresh dns.resolver.Resolver instance is created per lookup()
call (no shared state).

Team Cymru TXT response format (pipe-delimited):
  "ASN | CIDR_prefix | country_code | rir | allocation_date"
  Example: "23028 | 216.90.108.0/24 | US | arin | 1998-09-25"

Reference: https://www.team-cymru.com/ip-asn-mapping
"""
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
    """Adapter for IP-to-ASN lookup using Team Cymru's public DNS service.

    Supports IPV4 and IPV6 IOC types. Returns CIDR prefix, ASN number, RIR, and
    allocation date in raw_stats. Never assigns a threat verdict (verdict is always
    'no_data') — ASN context is informational, not a threat signal.

    No API key required. No HTTP calls are made — queries go directly to port 53.
    Private/RFC-1918 IPs return NXDOMAIN (no BGP route), which is handled as a
    no_data result rather than an error.

    Args:
        allowed_hosts: Accepted for API compatibility with the Provider protocol
            but unused. DNS does not make HTTP calls, so SSRF allowlisting is
            not applicable.
    """

    name = "ASN Intel"
    supported_types: frozenset[IOCType] = frozenset({IOCType.IPV4, IOCType.IPV6})
    requires_api_key = False

    def __init__(self, allowed_hosts: list[str]) -> None:
        # Accepted for API compatibility with Provider protocol; intentionally unused.
        # DNS uses port 53 directly — no HTTP, no SSRF surface.
        pass

    def is_configured(self) -> bool:
        """Always returns True — no API key or configuration required."""
        return True

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        """Perform ASN lookup for an IPv4 or IPv6 IOC via Team Cymru DNS.

        Constructs the reversed IP query name using ipaddress.reverse_pointer,
        replaces the .in-addr.arpa / .ip6.arpa suffix with the Cymru zone,
        then resolves TXT records with dnspython.

        Expected DNS conditions are handled gracefully:
          - NXDOMAIN: private/unrouted IP has no BGP entry -> no_data result (not an error)
          - NoAnswer: no TXT record for this query -> no_data result
          - NoNameservers: no authoritative nameservers -> no_data result
          - Timeout: resolver timed out -> no_data result

        Returns:
            EnrichmentResult with verdict='no_data' and raw_stats containing
            'asn', 'prefix', 'rir', 'allocated' on success, or {} on
            NXDOMAIN/NoAnswer/NoNameservers/Timeout.

            EnrichmentError for:
              - Unsupported IOC types (non-IP)
              - Invalid IP string values
              - Unexpected/generic exceptions
        """
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
    """Parse a Team Cymru TXT response into an EnrichmentResult.

    The TXT record format is pipe-delimited with spaces around pipes:
      "ASN | CIDR_prefix | country_code | rir | allocation_date"

    Fields are extracted by position (0=ASN, 1=prefix, 3=rir, 4=allocated).
    Country code (index 2) is intentionally excluded — it is a RIR assignment
    region, not a geolocation, and ip-api.com already provides geolocation context.

    Note on multi-origin ASN: when an IP prefix is announced by multiple ASNs,
    parts[0] may contain multiple space-separated ASN numbers (e.g., "23028 1234").
    This is stored as-is in raw_stats['asn'].

    Args:
        ioc: The IOC that was looked up.
        txt: The decoded TXT record string.
        provider_name: The provider name to include in the result.

    Returns:
        EnrichmentResult with verdict='no_data' and parsed raw_stats.
    """
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
