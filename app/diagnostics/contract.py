"""Diagnostic export manifest contract.

This module is intentionally backend-only and independent of Flask route handlers,
filesystem traversal, zip assembly, and gitignored planning/runtime paths.  It
only defines the JSON-safe vocabulary that later diagnostic bundle code can use
to report every source outcome without leaking secret values.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .bundle_layout import ordered_by_source_id
from .manifest_payloads import manifest_payload
from .source_record_fields import (
    DEFAULT_CONTENT_TYPE as DEFAULT_CONTENT_TYPE,
    DEFAULT_SOURCE_MAX_BYTES as DEFAULT_SOURCE_MAX_BYTES,
    _normalize_optional_text,
    normalize_source_record_fields,
    source_record_payload,
)

DIAGNOSTIC_EXPORT_SCHEMA_VERSION = "diagnostic-export-manifest/v1"

@dataclass(frozen=True, slots=True)
class DiagnosticSourceRecord:
    """One manifest entry for a diagnostic source outcome.

    A record represents exactly one source attempt.  It is never silently
    omitted from a manifest: successful sources use ``included`` or
    ``truncated``; intentionally skipped sources use ``omitted``; failed source
    reads use ``error`` with a bounded, secret-free summary.
    """

    source_id: str
    name: str
    category: str
    status: str
    relative_path: str | None = None
    display_path: str | None = None
    logical_label: str | None = None
    content_type: str = DEFAULT_CONTENT_TYPE
    original_bytes: int = 0
    included_bytes: int = 0
    max_bytes: int = DEFAULT_SOURCE_MAX_BYTES
    truncated: bool = False
    omitted_reason: str | None = None
    safe_error_summary: str | None = None
    redaction_count: int = 0
    redaction_labels: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        normalized = normalize_source_record_fields(self)
        object.__setattr__(self, "source_id", normalized.source_id)
        object.__setattr__(self, "name", normalized.name)
        object.__setattr__(self, "category", normalized.category)
        object.__setattr__(self, "status", normalized.status)
        object.__setattr__(self, "relative_path", normalized.relative_path)
        object.__setattr__(self, "display_path", normalized.display_path)
        object.__setattr__(self, "logical_label", normalized.logical_label)
        object.__setattr__(self, "content_type", normalized.content_type)
        object.__setattr__(self, "original_bytes", normalized.original_bytes)
        object.__setattr__(self, "included_bytes", normalized.included_bytes)
        object.__setattr__(self, "max_bytes", normalized.max_bytes)
        object.__setattr__(self, "truncated", normalized.truncated)
        object.__setattr__(self, "omitted_reason", normalized.omitted_reason)
        object.__setattr__(self, "safe_error_summary", normalized.safe_error_summary)
        object.__setattr__(self, "redaction_count", normalized.redaction_count)
        object.__setattr__(self, "redaction_labels", normalized.redaction_labels)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe source record with stable key ordering."""
        return source_record_payload(self)

    def to_json(self, *, indent: int | None = None) -> str:
        """Return a deterministic JSON representation of this source record."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


@dataclass(frozen=True, slots=True)
class DiagnosticManifest:
    """Diagnostic export manifest with aggregate source outcome counts."""

    sources: tuple[DiagnosticSourceRecord, ...] = field(default_factory=tuple)
    generated_at: str | None = None
    schema_version: str = DIAGNOSTIC_EXPORT_SCHEMA_VERSION
    _sorted_sources: tuple[DiagnosticSourceRecord, ...] = field(
        default_factory=tuple,
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if self.schema_version != DIAGNOSTIC_EXPORT_SCHEMA_VERSION:
            raise ValueError(f"unsupported diagnostic export schema_version: {self.schema_version}")
        seen_source_ids: set[str] = set()
        sources: list[DiagnosticSourceRecord] | None = None
        if not isinstance(self.sources, tuple):
            sources = []

        for source in self.sources:
            source_id = source.source_id
            if source_id in seen_source_ids:
                raise ValueError("duplicate diagnostic source_id values are not allowed")
            seen_source_ids.add(source_id)
            if sources is not None:
                append_manifest_source(sources, source)

        if sources is not None:
            object.__setattr__(self, "sources", tuple(sources))

        generated_at = _normalize_optional_text(self.generated_at, max_chars=80)
        object.__setattr__(self, "generated_at", generated_at)
        object.__setattr__(self, "_sorted_sources", ordered_by_source_id(self.sources))

    @property
    def sorted_sources(self) -> tuple[DiagnosticSourceRecord, ...]:
        """Return sources in deterministic manifest order."""
        return self._sorted_sources

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe manifest with stable key ordering and aggregate counts."""
        return manifest_payload(
            self.sorted_sources,
            schema_version=self.schema_version,
            generated_at=self.generated_at,
        )

    def to_json(self, *, indent: int | None = None) -> str:
        """Return a deterministic JSON representation of this manifest."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


def append_manifest_source(
    sources: list[DiagnosticSourceRecord],
    source: DiagnosticSourceRecord,
) -> None:
    sources.append(source)


def serialize_source_record(source: DiagnosticSourceRecord) -> dict[str, Any]:
    """Serialize a source record to its stable JSON-safe dictionary shape."""
    return source.to_dict()


def serialize_manifest(manifest: DiagnosticManifest) -> dict[str, Any]:
    """Serialize a manifest to its stable JSON-safe dictionary shape."""
    return manifest.to_dict()


def manifest_to_json(manifest: DiagnosticManifest, *, indent: int | None = None) -> str:
    """Serialize a manifest to deterministic JSON without reading clocks or files."""
    return manifest.to_json(indent=indent)


def manifest_to_json_bytes(manifest: DiagnosticManifest, *, indent: int | None = None) -> bytes:
    """Serialize a manifest to deterministic UTF-8 JSON bytes with a trailing newline."""
    return (manifest_to_json(manifest, indent=indent) + "\n").encode("utf-8")
