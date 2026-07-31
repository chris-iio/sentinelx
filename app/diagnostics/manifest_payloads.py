"""Diagnostic manifest dictionary payload builders."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .source_record_fields import (
    SOURCE_STATUS_ERROR,
    SOURCE_STATUS_INCLUDED,
    SOURCE_STATUS_OMITTED,
    SOURCE_STATUS_TRUNCATED,
)


@dataclass(slots=True)
class SourceCountsAccumulator:
    """Accumulate diagnostic source outcome counts in one shared branch."""

    source_count: int = 0
    included_count: int = 0
    truncated_count: int = 0
    omitted_count: int = 0
    error_count: int = 0
    redaction_count: int = 0

    def add(self, source: Any) -> None:
        self.source_count += 1
        if source.status == SOURCE_STATUS_INCLUDED:
            self.included_count += 1
        elif source.status == SOURCE_STATUS_TRUNCATED:
            self.truncated_count += 1
        elif source.status == SOURCE_STATUS_OMITTED:
            self.omitted_count += 1
        elif source.status == SOURCE_STATUS_ERROR:
            self.error_count += 1
        self.redaction_count += source.redaction_count

    def payload(self) -> dict[str, int]:
        return {
            "source_count": self.source_count,
            "included_count": self.included_count,
            "truncated_count": self.truncated_count,
            "omitted_count": self.omitted_count,
            "error_count": self.error_count,
            "redaction_count": self.redaction_count,
        }


def source_counts_payload(sources: tuple[Any, ...]) -> dict[str, int]:
    """Return aggregate source outcome counts without serializing source records."""
    source_count = len(sources)
    if source_count == 0:
        return SourceCountsAccumulator().payload()
    if source_count == 1:
        counts = SourceCountsAccumulator()
        counts.add(sources[0])
        return counts.payload()
    if source_count == 2:
        counts = SourceCountsAccumulator()
        counts.add(sources[0])
        counts.add(sources[1])
        return counts.payload()
    if source_count == 3:
        counts = SourceCountsAccumulator()
        counts.add(sources[0])
        counts.add(sources[1])
        counts.add(sources[2])
        return counts.payload()
    if source_count == 4:
        counts = SourceCountsAccumulator()
        counts.add(sources[0])
        counts.add(sources[1])
        counts.add(sources[2])
        counts.add(sources[3])
        return counts.payload()

    counts = SourceCountsAccumulator()
    for source in sources:
        counts.add(source)
    return counts.payload()


def append_serialized_source(serialized_sources: list[dict[str, Any]], source: Any) -> None:
    """Append one serialized diagnostic source record."""
    serialized_sources.append(source.to_dict())


def _add_and_append_source(
    counts: SourceCountsAccumulator,
    serialized_sources: list[dict[str, Any]],
    source: Any,
) -> None:
    counts.add(source)
    append_serialized_source(serialized_sources, source)


def manifest_payload_from_counts(
    *,
    schema_version: str,
    generated_at: str | None,
    counts_payload: dict[str, int],
    serialized_sources: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return the final public manifest payload shape."""
    payload: dict[str, Any] = {
        "schema_version": schema_version,
        "generated_at": generated_at,
    }
    payload.update(counts_payload)
    payload["sources"] = serialized_sources
    return payload


def manifest_payload(
    sources: tuple[Any, ...],
    *,
    schema_version: str,
    generated_at: str | None,
) -> dict[str, Any]:
    """Return a JSON-safe manifest payload with aggregate counts."""
    source_count = len(sources)
    if source_count == 0:
        return manifest_payload_from_counts(
            schema_version=schema_version,
            generated_at=generated_at,
            counts_payload=SourceCountsAccumulator().payload(),
            serialized_sources=[],
        )
    if source_count == 1:
        source = sources[0]
        counts = SourceCountsAccumulator()
        serialized_sources: list[dict[str, Any]] = []
        _add_and_append_source(counts, serialized_sources, source)
        return manifest_payload_from_counts(
            schema_version=schema_version,
            generated_at=generated_at,
            counts_payload=counts.payload(),
            serialized_sources=serialized_sources,
        )
    if source_count == 2:
        counts = SourceCountsAccumulator()
        serialized_sources: list[dict[str, Any]] = []
        _add_and_append_source(counts, serialized_sources, sources[0])
        _add_and_append_source(counts, serialized_sources, sources[1])
        return manifest_payload_from_counts(
            schema_version=schema_version,
            generated_at=generated_at,
            counts_payload=counts.payload(),
            serialized_sources=serialized_sources,
        )
    if source_count == 3:
        counts = SourceCountsAccumulator()
        serialized_sources: list[dict[str, Any]] = []
        _add_and_append_source(counts, serialized_sources, sources[0])
        _add_and_append_source(counts, serialized_sources, sources[1])
        _add_and_append_source(counts, serialized_sources, sources[2])
        return manifest_payload_from_counts(
            schema_version=schema_version,
            generated_at=generated_at,
            counts_payload=counts.payload(),
            serialized_sources=serialized_sources,
        )
    if source_count == 4:
        counts = SourceCountsAccumulator()
        serialized_sources: list[dict[str, Any]] = []
        _add_and_append_source(counts, serialized_sources, sources[0])
        _add_and_append_source(counts, serialized_sources, sources[1])
        _add_and_append_source(counts, serialized_sources, sources[2])
        _add_and_append_source(counts, serialized_sources, sources[3])
        return manifest_payload_from_counts(
            schema_version=schema_version,
            generated_at=generated_at,
            counts_payload=counts.payload(),
            serialized_sources=serialized_sources,
        )

    counts = SourceCountsAccumulator()
    serialized_sources: list[dict[str, Any]] = []
    for source in sources:
        _add_and_append_source(counts, serialized_sources, source)

    return manifest_payload_from_counts(
        schema_version=schema_version,
        generated_at=generated_at,
        counts_payload=counts.payload(),
        serialized_sources=serialized_sources,
    )
