"""DNS record lookup adapter using dnspython."""
from __future__ import annotations

import logging

import dns.exception
import dns.resolver

from .dns_txt import decode_txt_chunks
from ..models import EnrichmentError, EnrichmentResult, error_result, no_data_result
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)


def _extract_text_records(answers) -> list[str]:
    answer_count = len(answers)
    if answer_count == 0:
        return []
    if answer_count == 1:
        return [_record_text(answers[0])]
    if answer_count == 2:
        return [_record_text(answers[0]), _record_text(answers[1])]
    if answer_count == 3:
        return [_record_text(answers[0]), _record_text(answers[1]), _record_text(answers[2])]
    if answer_count == 4:
        return [
            _record_text(answers[0]),
            _record_text(answers[1]),
            _record_text(answers[2]),
            _record_text(answers[3]),
        ]

    records: list[str] = []
    for record in answers:
        _append_text_record(records, record)
    return records


def _record_text(record) -> str:
    return record.to_text()


def _append_text_record(records: list[str], record) -> None:
    records.append(_record_text(record))


def _extract_mx_records(answers) -> list[str]:
    answer_count = len(answers)
    if answer_count == 0:
        return []
    if answer_count == 1:
        return [_mx_record_text(answers[0])]
    if answer_count == 2:
        return [_mx_record_text(answers[0]), _mx_record_text(answers[1])]
    if answer_count == 3:
        return [
            _mx_record_text(answers[0]),
            _mx_record_text(answers[1]),
            _mx_record_text(answers[2]),
        ]
    if answer_count == 4:
        return [
            _mx_record_text(answers[0]),
            _mx_record_text(answers[1]),
            _mx_record_text(answers[2]),
            _mx_record_text(answers[3]),
        ]

    records: list[str] = []
    for record in answers:
        _append_mx_record(records, record)
    return records


def _mx_record_text(record) -> str:
    return f"{record.preference} {record.exchange.to_text()}"


def _append_mx_record(records: list[str], record) -> None:
    records.append(_mx_record_text(record))


def _extract_txt_records(answers) -> list[str]:
    answer_count = len(answers)
    if answer_count == 0:
        return []
    if answer_count == 1:
        return [_decode_txt_record(answers[0])]
    if answer_count == 2:
        return [_decode_txt_record(answers[0]), _decode_txt_record(answers[1])]
    if answer_count == 3:
        return [
            _decode_txt_record(answers[0]),
            _decode_txt_record(answers[1]),
            _decode_txt_record(answers[2]),
        ]
    if answer_count == 4:
        return [
            _decode_txt_record(answers[0]),
            _decode_txt_record(answers[1]),
            _decode_txt_record(answers[2]),
            _decode_txt_record(answers[3]),
        ]

    records: list[str] = []
    for record in answers:
        _append_txt_record(records, record)
    return records


def _decode_txt_record(record) -> str:
    return decode_txt_chunks(record.strings)


def _append_txt_record(records: list[str], record) -> None:
    records.append(_decode_txt_record(record))


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

    def is_configured(self) -> bool:
        return True

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        if ioc.type not in self.supported_types:
            return error_result(ioc, self.name, "Unsupported type")

        resolver = _configured_resolver()
        raw_stats = _empty_raw_stats()
        lookup_errors = raw_stats["lookup_errors"]

        for rdtype, key, extract_records in _RECORD_TYPES:
            records, error = _resolve_record_type(
                resolver=resolver,
                domain=ioc.value,
                rdtype=rdtype,
                extract_records=extract_records,
                provider=self.name,
            )
            if records is not None:
                raw_stats[key] = records
            if error is not None:
                _append_lookup_error(lookup_errors, error)

        return _dns_result(
            ioc=ioc,
            provider=self.name,
            raw_stats=raw_stats,
        )


def _dns_result(*, ioc: IOC, provider: str, raw_stats: dict) -> EnrichmentResult:
    return no_data_result(ioc, provider, raw_stats)


def _empty_raw_stats() -> dict:
    return {
        "a": [],
        "mx": [],
        "ns": [],
        "txt": [],
        "lookup_errors": [],
    }


def _append_lookup_error(lookup_errors: list[str], error: str) -> None:
    lookup_errors.append(error)


def _configured_resolver():
    resolver = dns.resolver.Resolver(configure=True)
    resolver.lifetime = _RESOLVER_LIFETIME
    return resolver


def _resolve_record_type(
    *,
    resolver,
    domain: str,
    rdtype: str,
    extract_records,
    provider: str,
) -> tuple[list[str] | None, str | None]:
    try:
        answers = resolver.resolve(domain, rdtype)
        return extract_records(answers), None
    except dns.resolver.NXDOMAIN:
        # Domain does not exist — expected; leave lists empty, no error entry.
        return None, None
    except dns.resolver.NoAnswer:
        # No records of this type exist for the domain — expected; leave list empty.
        return None, None
    except dns.resolver.NoNameservers:
        return None, f"{rdtype}: no nameservers"
    except dns.exception.Timeout:
        return None, f"{rdtype}: timeout"
    except Exception:
        logger.exception(
            "Unexpected error resolving %s %s for %s",
            rdtype,
            domain,
            provider,
        )
        return None, f"{rdtype}: unexpected error"
