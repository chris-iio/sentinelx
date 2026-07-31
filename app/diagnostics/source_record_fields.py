"""Diagnostic source-record field normalization and payload shaping."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.text_utils import collapse_whitespace, stripped_bounded_text

SOURCE_STATUS_INCLUDED = "included"
SOURCE_STATUS_OMITTED = "omitted"
SOURCE_STATUS_TRUNCATED = "truncated"
SOURCE_STATUS_ERROR = "error"
SOURCE_STATUSES = frozenset((
    SOURCE_STATUS_INCLUDED,
    SOURCE_STATUS_OMITTED,
    SOURCE_STATUS_TRUNCATED,
    SOURCE_STATUS_ERROR,
))
_OMITTED_REASON_STATUSES = frozenset((SOURCE_STATUS_OMITTED, SOURCE_STATUS_TRUNCATED))
_ZERO_INCLUDED_BYTES_STATUSES = frozenset((SOURCE_STATUS_OMITTED, SOURCE_STATUS_ERROR))

SOURCE_CATEGORIES = frozenset((
    "cache",
    "config",
    "health",
    "history",
    "metadata",
    "orchestrator",
    "runtime",
))

DEFAULT_SOURCE_MAX_BYTES = 256 * 1024
MAX_SAFE_ERROR_SUMMARY_CHARS = 120
MAX_SOURCE_TEXT_CHARS = 160
MAX_REDACTION_LABEL_CHARS = 64
DEFAULT_CONTENT_TYPE = "application/octet-stream"
DEFAULT_OMITTED_REASON = "not_collected"
DEFAULT_ERROR_SUMMARY = "Diagnostic source could not be collected."


@dataclass(frozen=True, slots=True)
class NormalizedSourceRecordFields:
    source_id: str
    name: str
    category: str
    status: str
    relative_path: str | None
    display_path: str | None
    logical_label: str | None
    content_type: str
    original_bytes: int
    included_bytes: int
    max_bytes: int
    truncated: bool
    omitted_reason: str | None
    safe_error_summary: str | None
    redaction_count: int
    redaction_labels: tuple[str, ...]


def normalize_source_record_fields(source: Any) -> NormalizedSourceRecordFields:
    source_id = _strip_required_text(source.source_id, "source_id")
    name = _strip_required_text(source.name, "name")
    category = _strip_required_text(source.category, "category")
    if category not in SOURCE_CATEGORIES:
        raise ValueError(f"invalid diagnostic source category: {category}")

    status = _strip_required_text(source.status, "status")
    if status not in SOURCE_STATUSES:
        raise ValueError(f"invalid diagnostic source status: {status}")

    content_type = _strip_required_text(source.content_type, "content_type")
    original_bytes = _normalize_nonnegative_int(source.original_bytes, "original_bytes")
    included_bytes = _normalize_nonnegative_int(source.included_bytes, "included_bytes")
    max_bytes = _normalize_nonnegative_int(source.max_bytes, "max_bytes")
    redaction_count = _normalize_nonnegative_int(source.redaction_count, "redaction_count")

    if included_bytes > original_bytes and original_bytes > 0:
        raise ValueError("included_bytes cannot exceed original_bytes")
    if included_bytes > max_bytes:
        raise ValueError("included_bytes cannot exceed max_bytes")

    if not isinstance(source.truncated, bool):
        raise ValueError("truncated must be a boolean")
    truncated = status == SOURCE_STATUS_TRUNCATED
    if source.truncated and status != SOURCE_STATUS_TRUNCATED:
        raise ValueError("truncated flag is only valid for truncated source records")

    relative_path = _normalize_optional_text(source.relative_path, max_chars=240)
    display_path = _normalize_optional_text(source.display_path, max_chars=240)
    logical_label = _normalize_optional_text(source.logical_label, max_chars=240)
    if relative_path is None and display_path is None and logical_label is None:
        logical_label = name

    omitted_reason = _normalize_optional_text(source.omitted_reason)
    safe_error_summary = _normalize_error_summary(source.safe_error_summary)
    if status == SOURCE_STATUS_OMITTED and omitted_reason is None:
        omitted_reason = DEFAULT_OMITTED_REASON
    if status == SOURCE_STATUS_ERROR and safe_error_summary is None:
        safe_error_summary = DEFAULT_ERROR_SUMMARY
    if status not in _OMITTED_REASON_STATUSES:
        omitted_reason = None
    if status != SOURCE_STATUS_ERROR:
        safe_error_summary = None
    if status in _ZERO_INCLUDED_BYTES_STATUSES:
        included_bytes = 0
        if original_bytes == 0:
            max_bytes = max(max_bytes, 0)

    return NormalizedSourceRecordFields(
        source_id=source_id,
        name=name,
        category=category,
        status=status,
        relative_path=relative_path,
        display_path=display_path,
        logical_label=logical_label,
        content_type=content_type,
        original_bytes=original_bytes,
        included_bytes=included_bytes,
        max_bytes=max_bytes,
        truncated=truncated,
        omitted_reason=omitted_reason,
        safe_error_summary=safe_error_summary,
        redaction_count=redaction_count,
        redaction_labels=_normalize_redaction_labels(source.redaction_labels),
    )


def source_record_payload(source: Any) -> dict[str, Any]:
    """Return a JSON-safe source record with stable key ordering."""
    return {
        "source_id": source.source_id,
        "name": source.name,
        "category": source.category,
        "status": source.status,
        "relative_path": source.relative_path,
        "display_path": source.display_path,
        "logical_label": source.logical_label,
        "content_type": source.content_type,
        "original_bytes": source.original_bytes,
        "included_bytes": source.included_bytes,
        "max_bytes": source.max_bytes,
        "truncated": source.truncated,
        "omitted_reason": source.omitted_reason,
        "safe_error_summary": source.safe_error_summary,
        "redaction_count": source.redaction_count,
        "redaction_labels": _copy_redaction_labels(source.redaction_labels),
    }


def _strip_required_text(
    value: object,
    field_name: str,
    *,
    max_chars: int = MAX_SOURCE_TEXT_CHARS,
) -> str:
    """Return a stripped non-empty string or raise ``ValueError``."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string")
    stripped = stripped_bounded_text(value, max_chars=max_chars)
    if stripped is None:
        raise ValueError(f"{field_name} must be a non-empty string")
    return stripped


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
    return stripped_bounded_text(value, max_chars=max_chars)


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
    summary = collapse_whitespace(value)
    if not summary:
        return None
    if len(summary) <= MAX_SAFE_ERROR_SUMMARY_CHARS:
        return summary
    return summary[: MAX_SAFE_ERROR_SUMMARY_CHARS - 3] + "..."


def _normalize_redaction_labels(labels: tuple[str, ...] | list[str] | set[str]) -> tuple[str, ...]:
    """Return stable, unique, bounded redaction labels."""
    input_count = len(labels)
    if input_count == 0:
        return ()
    if input_count == 1:
        for label in labels:
            return (_normalize_redaction_label(label),)
    if input_count == 2:
        iterator = iter(labels)
        first = _normalize_redaction_label(next(iterator))
        second = _normalize_redaction_label(next(iterator))
        if first == second:
            return (first,)
        if first < second:
            return (first, second)
        return (second, first)
    if input_count == 3:
        iterator = iter(labels)
        first = _normalize_redaction_label(next(iterator))
        second = _normalize_redaction_label(next(iterator))
        third = _normalize_redaction_label(next(iterator))
        if first > second:
            first, second = second, first
        if second > third:
            second, third = third, second
            if first > second:
                first, second = second, first
        if first == second:
            if second == third:
                return (first,)
            return (first, third)
        if second == third:
            return (first, second)
        return (first, second, third)
    if input_count == 4:
        iterator = iter(labels)
        first = _normalize_redaction_label(next(iterator))
        second = _normalize_redaction_label(next(iterator))
        third = _normalize_redaction_label(next(iterator))
        fourth = _normalize_redaction_label(next(iterator))
        if first > second:
            first, second = second, first
        if third > fourth:
            third, fourth = fourth, third
        if first > third:
            first, third = third, first
        if second > fourth:
            second, fourth = fourth, second
        if second > third:
            second, third = third, second
        if first == second:
            if second == third:
                if third == fourth:
                    return (first,)
                return (first, fourth)
            if third == fourth:
                return (first, third)
            return (first, third, fourth)
        if second == third:
            if third == fourth:
                return (first, second)
            return (first, second, fourth)
        if third == fourth:
            return (first, second, third)
        return (first, second, third, fourth)

    ordered: list[str] = []
    for label in labels:
        _append_normalized_redaction_label(ordered, label)
    return tuple(ordered)


def _append_normalized_redaction_label(ordered: list[str], label: str) -> None:
    _append_ordered_unique_redaction_label(ordered, _normalize_redaction_label(label))


def _append_ordered_unique_redaction_label(ordered: list[str], label: str) -> None:
    label_count = len(ordered)
    if label_count == 0:
        ordered.append(label)
        return

    index = 0
    while index < label_count:
        current = ordered[index]
        if label == current:
            return
        if label < current:
            ordered.insert(index, label)
            return
        index += 1

    ordered.append(label)


def _normalize_redaction_label(label: str) -> str:
    return _strip_required_text(
        label,
        "redaction label",
        max_chars=MAX_REDACTION_LABEL_CHARS,
    )


def _copy_redaction_labels(labels: tuple[str, ...]) -> list[str]:
    """Return a mutable JSON-safe copy of normalized redaction labels."""
    label_count = len(labels)
    if label_count == 0:
        return []
    if label_count == 1:
        return [labels[0]]
    if label_count == 2:
        return [labels[0], labels[1]]
    if label_count == 3:
        return [labels[0], labels[1], labels[2]]
    if label_count == 4:
        return [labels[0], labels[1], labels[2], labels[3]]

    copied: list[str] = []
    for label in labels:
        _append_redaction_label_copy(copied, label)
    return copied


def _append_redaction_label_copy(copied: list[str], label: str) -> None:
    copied.append(label)
