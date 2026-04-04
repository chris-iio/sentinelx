"""DNS record lookup adapter using dnspython."""
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
    """Live DNS record lookup via port 53 — no HTTP, no SSRF surface."""

    name = "DNS Records"
    supported_types: frozenset[IOCType] = frozenset({IOCType.DOMAIN})
    requires_api_key = False

    def __init__(self, allowed_hosts: list[str]) -> None:
        # allowed_hosts accepted for Provider protocol compat; unused (DNS, not HTTP).
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
