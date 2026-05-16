"""DNS record lookup adapter using dnspython."""
from __future__ import annotations

import logging

import dns.exception
import dns.resolver

from app.enrichment.models import EnrichmentError, EnrichmentResult, error_result, no_data_result
from app.pipeline.models import IOC, IOCType
from app.text_utils import decode_utf8_replace

logger = logging.getLogger(__name__)


def _extract_text_records(answers) -> list[str]:
    answer_count = len(answers)
    if answer_count == 0:
        return []
    if answer_count == 1:
        return [answers[0].to_text()]
    if answer_count == 2:
        return [answers[0].to_text(), answers[1].to_text()]
    if answer_count == 3:
        return [answers[0].to_text(), answers[1].to_text(), answers[2].to_text()]

    records: list[str] = []
    for record in answers:
        records.append(record.to_text())
    return records


def _extract_mx_records(answers) -> list[str]:
    answer_count = len(answers)
    if answer_count == 0:
        return []
    if answer_count == 1:
        record = answers[0]
        return [f"{record.preference} {record.exchange.to_text()}"]
    if answer_count == 2:
        first = answers[0]
        second = answers[1]
        return [
            f"{first.preference} {first.exchange.to_text()}",
            f"{second.preference} {second.exchange.to_text()}",
        ]
    if answer_count == 3:
        first = answers[0]
        second = answers[1]
        third = answers[2]
        return [
            f"{first.preference} {first.exchange.to_text()}",
            f"{second.preference} {second.exchange.to_text()}",
            f"{third.preference} {third.exchange.to_text()}",
        ]

    records: list[str] = []
    for record in answers:
        records.append(f"{record.preference} {record.exchange.to_text()}")
    return records


def _extract_txt_records(answers) -> list[str]:
    answer_count = len(answers)
    if answer_count == 0:
        return []
    if answer_count == 1:
        return [_decode_txt_record(answers[0])]
    if answer_count == 2:
        return [_decode_txt_record(answers[0]), _decode_txt_record(answers[1])]
    if answer_count == 3:
        return [_decode_txt_record(answers[0]), _decode_txt_record(answers[1]), _decode_txt_record(answers[2])]

    records: list[str] = []
    for record in answers:
        records.append(_decode_txt_record(record))
    return records


def _decode_txt_record(record) -> str:
    strings = record.strings
    string_count = len(strings)
    if string_count == 1:
        raw_text = strings[0]
    elif string_count == 2:
        raw_text = strings[0] + strings[1]
    else:
        raw_text = b"".join(strings)
    return decode_utf8_replace(raw_text)


# Record types to query, in order. Tuple of (rdtype string, raw_stats key).
_RECORD_TYPES = (
    ("A", "a", _extract_text_records),
    ("MX", "mx", _extract_mx_records),
    ("NS", "ns", _extract_text_records),
    ("TXT", "txt", _extract_txt_records),
)

# Resolver timeout in seconds (float, not HTTP connect/read tuple).
_RESOLVER_LIFETIME: float = 5.0


class DnsAdapter:
    """Live DNS record lookup via port 53 — no HTTP, no SSRF surface."""

    name = "DNS Records"
    supported_types: frozenset[IOCType] = frozenset((IOCType.DOMAIN,))
    requires_api_key = False

    def __init__(self, allowed_hosts: list[str]) -> None:
        # allowed_hosts accepted for Provider protocol compat; unused (DNS, not HTTP).
        pass

    def is_configured(self) -> bool:
        return True

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        if ioc.type not in self.supported_types:
            return error_result(ioc, self.name, "Unsupported type")

        resolver = dns.resolver.Resolver(configure=True)
        resolver.lifetime = _RESOLVER_LIFETIME

        raw_stats: dict = {
            "a": [],
            "mx": [],
            "ns": [],
            "txt": [],
            "lookup_errors": [],
        }

        for rdtype, key, extract_records in _RECORD_TYPES:
            try:
                answers = resolver.resolve(ioc.value, rdtype)
                raw_stats[key] = extract_records(answers)
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

        return _dns_result(
            ioc=ioc,
            provider=self.name,
            raw_stats=raw_stats,
        )


def _dns_result(*, ioc: IOC, provider: str, raw_stats: dict) -> EnrichmentResult:
    return no_data_result(ioc, provider, raw_stats)
