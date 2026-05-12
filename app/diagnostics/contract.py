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

DIAGNOSTIC_EXPORT_SCHEMA_VERSION = "diagnostic-export-manifest/v1"

SOURCE_STATUS_INCLUDED = "included"
SOURCE_STATUS_OMITTED = "omitted"
SOURCE_STATUS_TRUNCATED = "truncated"
SOURCE_STATUS_ERROR = "error"
SOURCE_STATUSES = frozenset({
    SOURCE_STATUS_INCLUDED,
    SOURCE_STATUS_OMITTED,
    SOURCE_STATUS_TRUNCATED,
    SOURCE_STATUS_ERROR,
})

SOURCE_CATEGORIES = frozenset({
    "cache",
    "config",
    "health",
    "history",
    "metadata",
    "orchestrator",
    "runtime",
})

DEFAULT_SOURCE_MAX_BYTES = 256 * 1024
MAX_SAFE_ERROR_SUMMARY_CHARS = 120
MAX_SOURCE_TEXT_CHARS = 160
MAX_REDACTION_LABEL_CHARS = 64
DEFAULT_CONTENT_TYPE = "application/octet-stream"
DEFAULT_OMITTED_REASON = "not_collected"
DEFAULT_ERROR_SUMMARY = "Diagnostic source could not be collected."


def _strip_required_text(
    value: object,
    field_name: str,
    *,
    max_chars: int = MAX_SOURCE_TEXT_CHARS,
) -> str:
    """Return a stripped non-empty string or raise ``ValueError``."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string")
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} must be a non-empty string")
    return stripped[:max_chars]


def _normalize_optional_text(
    value: object,
    *,
    max_chars: int = MAX_SOURCE_TEXT_CHARS,
) -> str | None:
    """Return stripped bounded text, or ``None`` when the input is empty/missing."""
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    stripped = value.strip()
    if not stripped:
        return None
    return stripped[:max_chars]


def _normalize_nonnegative_int(value: object, field_name: str) -> int:
    """Return a non-negative integer, rejecting bools and negative values."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be a non-negative integer")
    if value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _normalize_error_summary(value: object) -> str | None:
    """Return a bounded single-line safe error summary."""
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    summary = " ".join(value.strip().split())
    if not summary:
        return None
    if len(summary) <= MAX_SAFE_ERROR_SUMMARY_CHARS:
        return summary
    return summary[: MAX_SAFE_ERROR_SUMMARY_CHARS - 3] + "..."


def _normalize_redaction_labels(labels: tuple[str, ...] | list[str] | set[str]) -> tuple[str, ...]:
    """Return stable, unique, bounded redaction labels."""
    normalized = {
        _strip_required_text(label, "redaction label", max_chars=MAX_REDACTION_LABEL_CHARS)
        for label in labels
    }
    return tuple(sorted(normalized))


@dataclass(frozen=True)
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
        source_id = _strip_required_text(self.source_id, "source_id")
        name = _strip_required_text(self.name, "name")
        category = _strip_required_text(self.category, "category")
        if category not in SOURCE_CATEGORIES:
            raise ValueError(f"invalid diagnostic source category: {category}")

        status = _strip_required_text(self.status, "status")
        if status not in SOURCE_STATUSES:
            raise ValueError(f"invalid diagnostic source status: {status}")

        content_type = _strip_required_text(self.content_type, "content_type")
        original_bytes = _normalize_nonnegative_int(self.original_bytes, "original_bytes")
        included_bytes = _normalize_nonnegative_int(self.included_bytes, "included_bytes")
        max_bytes = _normalize_nonnegative_int(self.max_bytes, "max_bytes")
        redaction_count = _normalize_nonnegative_int(self.redaction_count, "redaction_count")

        if included_bytes > original_bytes and original_bytes > 0:
            raise ValueError("included_bytes cannot exceed original_bytes")
        if included_bytes > max_bytes:
            raise ValueError("included_bytes cannot exceed max_bytes")

        if not isinstance(self.truncated, bool):
            raise ValueError("truncated must be a boolean")
        truncated = status == SOURCE_STATUS_TRUNCATED
        if self.truncated and status != SOURCE_STATUS_TRUNCATED:
            raise ValueError("truncated flag is only valid for truncated source records")

        relative_path = _normalize_optional_text(self.relative_path, max_chars=240)
        display_path = _normalize_optional_text(self.display_path, max_chars=240)
        logical_label = _normalize_optional_text(self.logical_label, max_chars=240)
        if relative_path is None and display_path is None and logical_label is None:
            logical_label = name

        omitted_reason = _normalize_optional_text(self.omitted_reason)
        safe_error_summary = _normalize_error_summary(self.safe_error_summary)
        if status == SOURCE_STATUS_OMITTED and omitted_reason is None:
            omitted_reason = DEFAULT_OMITTED_REASON
        if status == SOURCE_STATUS_ERROR and safe_error_summary is None:
            safe_error_summary = DEFAULT_ERROR_SUMMARY
        if status not in {SOURCE_STATUS_OMITTED, SOURCE_STATUS_TRUNCATED}:
            omitted_reason = None
        if status != SOURCE_STATUS_ERROR:
            safe_error_summary = None
        if status in {SOURCE_STATUS_OMITTED, SOURCE_STATUS_ERROR}:
            included_bytes = 0
            if original_bytes == 0:
                max_bytes = max(max_bytes, 0)

        redaction_labels = _normalize_redaction_labels(self.redaction_labels)

        object.__setattr__(self, "source_id", source_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "relative_path", relative_path)
        object.__setattr__(self, "display_path", display_path)
        object.__setattr__(self, "logical_label", logical_label)
        object.__setattr__(self, "content_type", content_type)
        object.__setattr__(self, "original_bytes", original_bytes)
        object.__setattr__(self, "included_bytes", included_bytes)
        object.__setattr__(self, "max_bytes", max_bytes)
        object.__setattr__(self, "truncated", truncated)
        object.__setattr__(self, "omitted_reason", omitted_reason)
        object.__setattr__(self, "safe_error_summary", safe_error_summary)
        object.__setattr__(self, "redaction_count", redaction_count)
        object.__setattr__(self, "redaction_labels", redaction_labels)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe source record with stable key ordering."""
        return {
            "source_id": self.source_id,
            "name": self.name,
            "category": self.category,
            "status": self.status,
            "relative_path": self.relative_path,
            "display_path": self.display_path,
            "logical_label": self.logical_label,
            "content_type": self.content_type,
            "original_bytes": self.original_bytes,
            "included_bytes": self.included_bytes,
            "max_bytes": self.max_bytes,
            "truncated": self.truncated,
            "omitted_reason": self.omitted_reason,
            "safe_error_summary": self.safe_error_summary,
            "redaction_count": self.redaction_count,
            "redaction_labels": list(self.redaction_labels),
        }

    def to_json(self, *, indent: int | None = None) -> str:
        """Return a deterministic JSON representation of this source record."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


@dataclass(frozen=True)
class DiagnosticManifest:
    """Diagnostic export manifest with aggregate source outcome counts."""

    sources: tuple[DiagnosticSourceRecord, ...] = field(default_factory=tuple)
    generated_at: str | None = None
    schema_version: str = DIAGNOSTIC_EXPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DIAGNOSTIC_EXPORT_SCHEMA_VERSION:
            raise ValueError(f"unsupported diagnostic export schema_version: {self.schema_version}")
        if not isinstance(self.sources, tuple):
            object.__setattr__(self, "sources", tuple(self.sources))

        source_ids = [source.source_id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("duplicate diagnostic source_id values are not allowed")

        generated_at = _normalize_optional_text(self.generated_at, max_chars=80)
        object.__setattr__(self, "generated_at", generated_at)

    @property
    def sorted_sources(self) -> tuple[DiagnosticSourceRecord, ...]:
        """Return sources in deterministic manifest order."""
        return tuple(sorted(self.sources, key=lambda source: source.source_id))

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe manifest with stable key ordering and aggregate counts."""
        sources = self.sorted_sources
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "source_count": len(sources),
            "included_count": sum(
                1 for source in sources if source.status == SOURCE_STATUS_INCLUDED
            ),
            "truncated_count": sum(
                1 for source in sources if source.status == SOURCE_STATUS_TRUNCATED
            ),
            "omitted_count": sum(1 for source in sources if source.status == SOURCE_STATUS_OMITTED),
            "error_count": sum(1 for source in sources if source.status == SOURCE_STATUS_ERROR),
            "redaction_count": sum(source.redaction_count for source in sources),
            "sources": [source.to_dict() for source in sources],
        }

    def to_json(self, *, indent: int | None = None) -> str:
        """Return a deterministic JSON representation of this manifest."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


def serialize_source_record(source: DiagnosticSourceRecord) -> dict[str, Any]:
    """Serialize a source record to its stable JSON-safe dictionary shape."""
    return source.to_dict()


def serialize_manifest(manifest: DiagnosticManifest) -> dict[str, Any]:
    """Serialize a manifest to its stable JSON-safe dictionary shape."""
    return manifest.to_dict()


def manifest_to_json(manifest: DiagnosticManifest, *, indent: int | None = None) -> str:
    """Serialize a manifest to deterministic JSON without reading clocks or files."""
    return manifest.to_json(indent=indent)
