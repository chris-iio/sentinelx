"""Pure diagnostic bundle ordering and summary helpers."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from .archive_paths import MANIFEST_ARCHIVE_PATH
from .manifest_payloads import source_counts_payload

if TYPE_CHECKING:
    from .contract import DiagnosticSourceRecord

T = TypeVar("T")


def ordered_by_source_id(sources: tuple[T, ...]) -> tuple[T, ...]:
    """Return sources ordered by ``source_id`` with tiny-input fast paths."""
    source_count = len(sources)
    if source_count <= 1:
        return sources
    if source_count == 2:
        first = sources[0]
        second = sources[1]
        if _source_id(first) <= _source_id(second):
            return (first, second)
        return (second, first)
    if source_count == 3:
        first = sources[0]
        second = sources[1]
        third = sources[2]
        if _source_id(second) < _source_id(first):
            first, second = second, first
        if _source_id(third) < _source_id(second):
            second, third = third, second
            if _source_id(second) < _source_id(first):
                first, second = second, first
        return (first, second, third)
    if source_count == 4:
        first = sources[0]
        second = sources[1]
        third = sources[2]
        fourth = sources[3]
        if _source_id(second) < _source_id(first):
            first, second = second, first
        if _source_id(fourth) < _source_id(third):
            third, fourth = fourth, third
        if _source_id(third) < _source_id(first):
            first, third = third, first
        if _source_id(fourth) < _source_id(second):
            second, fourth = fourth, second
        if _source_id(third) < _source_id(second):
            second, third = third, second
        return (first, second, third, fourth)
    ordered: list[T] = []
    for source in sources:
        append_ordered_source(ordered, source)
    return tuple(ordered)


def append_ordered_source(ordered: list[T], source: T) -> None:
    source_count = len(ordered)
    if source_count == 0:
        ordered.append(source)
        return

    source_id = _source_id(source)
    index = 0
    while index < source_count:
        if source_id <= _source_id(ordered[index]):
            ordered.insert(index, source)
            return
        index += 1

    ordered.append(source)


def ordered_payload_entries(entries: list[tuple[str, bytes]]) -> tuple[tuple[str, bytes], ...]:
    """Return payload entries ordered by archive path with tiny-input fast paths."""
    entry_count = len(entries)
    if entry_count == 0:
        return ()
    if entry_count == 1:
        return (entries[0],)
    if entry_count == 2:
        first = entries[0]
        second = entries[1]
        if first[0] <= second[0]:
            return (first, second)
        return (second, first)
    if entry_count == 3:
        first = entries[0]
        second = entries[1]
        third = entries[2]
        if second[0] < first[0]:
            first, second = second, first
        if third[0] < second[0]:
            second, third = third, second
            if second[0] < first[0]:
                first, second = second, first
        return (first, second, third)
    if entry_count == 4:
        first = entries[0]
        second = entries[1]
        third = entries[2]
        fourth = entries[3]
        if second[0] < first[0]:
            first, second = second, first
        if fourth[0] < third[0]:
            third, fourth = fourth, third
        if third[0] < first[0]:
            first, third = third, first
        if fourth[0] < second[0]:
            second, fourth = fourth, second
        if third[0] < second[0]:
            second, third = third, second
        return (first, second, third, fourth)
    ordered: list[tuple[str, bytes]] = []
    for entry in entries:
        append_ordered_payload_entry(ordered, entry)
    return tuple(ordered)


def append_ordered_payload_entry(
    ordered: list[tuple[str, bytes]],
    entry: tuple[str, bytes],
) -> None:
    entry_count = len(ordered)
    if entry_count == 0:
        ordered.append(entry)
        return

    entry_path = entry[0]
    index = 0
    while index < entry_count:
        if entry_path <= ordered[index][0]:
            ordered.insert(index, entry)
            return
        index += 1

    ordered.append(entry)


def archive_entries(
    manifest_bytes: bytes,
    payload_entries: list[tuple[str, bytes]],
) -> tuple[tuple[str, bytes], ...]:
    """Return manifest-first archive entries with ordered payload entries."""
    manifest_entry = (MANIFEST_ARCHIVE_PATH, manifest_bytes)
    ordered_payloads = ordered_payload_entries(payload_entries)
    payload_count = len(ordered_payloads)
    if payload_count == 0:
        return (manifest_entry,)
    if payload_count == 1:
        return (manifest_entry, ordered_payloads[0])
    if payload_count == 2:
        return (manifest_entry, ordered_payloads[0], ordered_payloads[1])
    if payload_count == 3:
        return (manifest_entry, ordered_payloads[0], ordered_payloads[1], ordered_payloads[2])
    if payload_count == 4:
        return (
            manifest_entry,
            ordered_payloads[0],
            ordered_payloads[1],
            ordered_payloads[2],
            ordered_payloads[3],
        )

    entries: list[tuple[str, bytes]] = [manifest_entry]
    for entry in ordered_payloads:
        append_archive_entry(entries, entry)
    return tuple(entries)


def append_archive_entry(
    entries: list[tuple[str, bytes]],
    entry: tuple[str, bytes],
) -> None:
    entries.append(entry)


def archive_entry_paths(entries: tuple[tuple[str, bytes], ...]) -> tuple[str, ...]:
    """Return archive paths in write order without exposing payload bytes."""
    entry_count = len(entries)
    if entry_count == 0:
        return ()
    if entry_count == 1:
        return (entries[0][0],)
    if entry_count == 2:
        return (entries[0][0], entries[1][0])
    if entry_count == 3:
        return (entries[0][0], entries[1][0], entries[2][0])
    if entry_count == 4:
        return (entries[0][0], entries[1][0], entries[2][0], entries[3][0])
    if entry_count == 5:
        return (
            entries[0][0],
            entries[1][0],
            entries[2][0],
            entries[3][0],
            entries[4][0],
        )

    paths: list[str] = []
    for path, _payload in entries:
        append_archive_entry_path(paths, path)
    return tuple(paths)


def append_archive_entry_path(paths: list[str], path: str) -> None:
    paths.append(path)


def bundle_summary(
    sources: tuple[DiagnosticSourceRecord, ...],
    *,
    schema_version: str,
    generated_at: str,
    archive_size_bytes: int,
) -> dict[str, int | str | None]:
    """Return secret-free aggregate diagnostic bundle summary fields."""
    summary: dict[str, int | str | None] = {
        "schema_version": schema_version,
        "generated_at": generated_at,
        "archive_size_bytes": archive_size_bytes,
    }
    summary.update(source_counts_payload(sources))
    return summary


def _source_id(source: Any) -> str:
    return source.source_id
