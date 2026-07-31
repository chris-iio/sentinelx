"""Per-source diagnostic collection result helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .payload_encoding import (
    collect_source_payload,
    redact_and_encode_payload,
)
from .records import error_record, included_record, omitted_record

if TYPE_CHECKING:
    from .contract import DiagnosticSourceRecord
    from .redaction import ConfigSecretStore
    from .source_preparation import _PreparedSource


@dataclass(frozen=True, slots=True)
class SourceCollectionResult:
    record: DiagnosticSourceRecord
    payload_entry: tuple[str, bytes] | None = None


def collect_source_results(
    prepared_sources: tuple[_PreparedSource, ...],
    *,
    config_store: ConfigSecretStore | None,
) -> tuple[tuple[DiagnosticSourceRecord, ...], list[tuple[str, bytes]]]:
    """Return manifest records and payload entries for ordered prepared sources."""
    source_count = len(prepared_sources)
    if source_count == 0:
        return (), []
    if source_count == 1:
        return _collection_result_tuple(
            source_collection_result(prepared_sources[0], config_store=config_store)
        )
    if source_count == 2:
        return _collection_result_tuple(
            source_collection_result(prepared_sources[0], config_store=config_store),
            source_collection_result(prepared_sources[1], config_store=config_store),
        )
    if source_count == 3:
        return _collection_result_tuple(
            source_collection_result(prepared_sources[0], config_store=config_store),
            source_collection_result(prepared_sources[1], config_store=config_store),
            source_collection_result(prepared_sources[2], config_store=config_store),
        )
    if source_count == 4:
        return _collection_result_tuple(
            source_collection_result(prepared_sources[0], config_store=config_store),
            source_collection_result(prepared_sources[1], config_store=config_store),
            source_collection_result(prepared_sources[2], config_store=config_store),
            source_collection_result(prepared_sources[3], config_store=config_store),
        )

    records: list[DiagnosticSourceRecord] = []
    payload_entries: list[tuple[str, bytes]] = []
    for prepared in prepared_sources:
        append_collected_source_result(
            records,
            payload_entries,
            prepared,
            config_store=config_store,
        )
    return tuple(records), payload_entries


def _collection_result_tuple(
    *results: SourceCollectionResult,
) -> tuple[tuple[DiagnosticSourceRecord, ...], list[tuple[str, bytes]]]:
    result_count = len(results)
    if result_count == 0:
        return (), []
    if result_count == 1:
        first = results[0]
        if first.payload_entry is None:
            return (first.record,), []
        return (first.record,), [first.payload_entry]
    if result_count == 2:
        first = results[0]
        second = results[1]
        payload_entries: list[tuple[str, bytes]] = []
        append_payload_entry(payload_entries, first)
        append_payload_entry(payload_entries, second)
        return (first.record, second.record), payload_entries

    first = results[0]
    second = results[1]
    third = results[2]
    if result_count == 3:
        payload_entries: list[tuple[str, bytes]] = []
        append_payload_entry(payload_entries, first)
        append_payload_entry(payload_entries, second)
        append_payload_entry(payload_entries, third)
        return (first.record, second.record, third.record), payload_entries

    if result_count == 4:
        fourth = results[3]
        payload_entries: list[tuple[str, bytes]] = []
        append_payload_entry(payload_entries, first)
        append_payload_entry(payload_entries, second)
        append_payload_entry(payload_entries, third)
        append_payload_entry(payload_entries, fourth)
        return (first.record, second.record, third.record, fourth.record), payload_entries

    records: list[DiagnosticSourceRecord] = []
    payload_entries: list[tuple[str, bytes]] = []
    for result in results:
        append_source_collection_result(records, payload_entries, result)
    return tuple(records), payload_entries


def append_source_collection_result(
    records: list[DiagnosticSourceRecord],
    payload_entries: list[tuple[str, bytes]],
    result: SourceCollectionResult,
) -> None:
    records.append(result.record)
    append_payload_entry(payload_entries, result)


def append_collected_source_result(
    records: list[DiagnosticSourceRecord],
    payload_entries: list[tuple[str, bytes]],
    prepared: _PreparedSource,
    *,
    config_store: ConfigSecretStore | None,
) -> None:
    append_source_collection_result(
        records,
        payload_entries,
        source_collection_result(prepared, config_store=config_store),
    )


def append_payload_entry(
    payload_entries: list[tuple[str, bytes]],
    result: SourceCollectionResult,
) -> None:
    if result.payload_entry is not None:
        payload_entries.append(result.payload_entry)


def source_collection_result(
    prepared: _PreparedSource,
    *,
    config_store: ConfigSecretStore | None,
) -> SourceCollectionResult:
    """Return the manifest record and optional archive payload for one source."""
    if prepared.should_omit_without_collection:
        return SourceCollectionResult(omitted_record(prepared))

    try:
        payload = collect_source_payload(prepared.source)
        encoded, metadata = redact_and_encode_payload(
            payload,
            content_type=prepared.content_type,
            config_store=config_store,
        )
    except Exception as exc:  # noqa: BLE001 - source failures become manifest records.
        return SourceCollectionResult(error_record(prepared, exc, config_store=config_store))

    record, included = included_record(prepared, encoded, metadata)
    if prepared.relative_path is None:
        return SourceCollectionResult(record)
    return SourceCollectionResult(record, source_payload_entry(prepared, included))


def source_payload_entry(
    prepared: _PreparedSource,
    included: bytes,
) -> tuple[str, bytes]:
    """Return the archive payload entry for one prepared source."""
    if prepared.relative_path is None:
        raise ValueError("prepared source does not have an archive payload path")
    return (prepared.relative_path, included)
