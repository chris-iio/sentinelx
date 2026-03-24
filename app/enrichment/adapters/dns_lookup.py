"""DNS record lookup adapter.

Implements live DNS resolution for domain IOCs using dnspython, returning A, MX,
NS, and TXT records in raw_stats.

Design notes:
  - DNS uses port 53 directly — NOT HTTP. Do NOT import or use http_safety.py.
    validate_endpoint(), TIMEOUT, and read_limited() are HTTP-specific controls
    that are irrelevant and must not be used here.
  - No API key required — uses the system resolver (resolv.conf).
  - allowed_hosts parameter is accepted for API compatibility with the Provider
    protocol (other adapters pass it in from setup.py) but is intentionally
    ignored here. DNS does not make HTTP calls; there is no SSRF surface.
  - resolver.lifetime=5.0 (seconds): a single float timeout for the resolver,
    distinct from the (connect, read) tuple used by HTTP adapters.
  - NXDOMAIN and NoAnswer are expected outcomes, not errors. They result in
    EnrichmentResult(verdict='no_data') with empty record lists.
  - Partial failures (e.g., MX times out but A succeeds) populate lookup_errors
    while keeping the successfully-resolved record types.
  - verdict is always 'no_data' — DNS records are informational context, not
    threat signals.

Thread safety: a fresh dns.resolver.Resolver instance is created per lookup()
call (no shared state).
"""
from __future__ import annotations

import logging

import dns.exception
import dns.resolver

from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)

# Record types to query, in order. Tuple of (rdtype string, raw_stats key).
_RECORD_TYPES: tuple[tuple[str, str], ...] = (
    ("A", "a"),
    ("MX", "mx"),
    ("NS", "ns"),
    ("TXT", "txt"),
)

# Resolver timeout in seconds (float, not HTTP connect/read tuple).
_RESOLVER_LIFETIME: float = 5.0


class DnsAdapter:
    """Adapter for live DNS record lookups using dnspython.

    Supports DOMAIN IOC type only. Queries A, MX, NS, and TXT records for
    each domain. Returns all found records in raw_stats; never assigns a
    threat verdict (verdict is always 'no_data').

    No API key required — uses the system resolver. No HTTP calls are made.

    DNS resolution goes directly to port 53. This adapter intentionally does
    NOT use http_safety.py controls (validate_endpoint, TIMEOUT, read_limited),
    which apply only to HTTP/HTTPS traffic.

    Args:
        allowed_hosts: Accepted for API compatibility with the Provider protocol
            but unused. DNS does not make HTTP calls, so SSRF allowlisting is
            not applicable.
    """

    name = "DNS Records"
    supported_types: frozenset[IOCType] = frozenset({IOCType.DOMAIN})
    requires_api_key = False

    def __init__(self, allowed_hosts: list[str]) -> None:
        # Accepted for API compatibility with Provider protocol; intentionally unused.
        # DNS uses port 53 directly — no HTTP, no SSRF surface.
        pass

    def is_configured(self) -> bool:
        """Always returns True — no API key or configuration required."""
        return True

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        """Perform DNS resolution for a domain IOC.

        Queries A, MX, NS, and TXT records independently using dnspython.
        Each record type is resolved in a separate resolver.resolve() call so
        that failure of one type does not prevent the others from succeeding.

        Expected DNS conditions are handled gracefully:
          - NXDOMAIN: domain does not exist -> no_data result (not an error)
          - NoAnswer: record type not present for this domain -> empty list
          - Timeout: resolver timed out -> appended to lookup_errors
          - NoNameservers: no nameservers authoritative -> appended to lookup_errors

        Returns:
            EnrichmentResult with verdict='no_data' and raw_stats containing
            'a', 'mx', 'ns', 'txt' lists plus 'lookup_errors' for any partial
            failures.

            EnrichmentError only for unsupported IOC types.
        """
        if ioc.type not in self.supported_types:
            return EnrichmentError(
                ioc=ioc,
                provider=self.name,
                error="Unsupported type",
            )

        resolver = dns.resolver.Resolver(configure=True)
        resolver.lifetime = _RESOLVER_LIFETIME

        raw_stats: dict = {
            "a": [],
            "mx": [],
            "ns": [],
            "txt": [],
            "lookup_errors": [],
        }

        for rdtype, _key in _RECORD_TYPES:
            try:
                answers = resolver.resolve(ioc.value, rdtype)
                if rdtype == "A":
                    raw_stats["a"] = [r.to_text() for r in answers]
                elif rdtype == "MX":
                    raw_stats["mx"] = [
                        f"{r.preference} {r.exchange.to_text()}" for r in answers
                    ]
                elif rdtype == "NS":
                    raw_stats["ns"] = [r.to_text() for r in answers]
                elif rdtype == "TXT":
                    raw_stats["txt"] = [
                        b"".join(r.strings).decode("utf-8", errors="replace")
                        for r in answers
                    ]
            except dns.resolver.NXDOMAIN:
                # Domain does not exist — expected; leave lists empty, no error entry.
                pass
            except dns.resolver.NoAnswer:
                # No records of this type exist for the domain — expected; leave list empty.
                pass
            except dns.resolver.NoNameservers:
                raw_stats["lookup_errors"].append(f"{rdtype}: no nameservers")
            except dns.exception.Timeout:
                raw_stats["lookup_errors"].append(f"{rdtype}: timeout")
            except Exception:
                logger.exception(
                    "Unexpected error resolving %s %s for %s",
                    rdtype,
                    ioc.value,
                    self.name,
                )
                raw_stats["lookup_errors"].append(f"{rdtype}: unexpected error")

        return EnrichmentResult(
            ioc=ioc,
            provider=self.name,
            verdict="no_data",
            detection_count=0,
            total_engines=0,
            scan_date=None,
            raw_stats=raw_stats,
        )
