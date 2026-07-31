"""Diagnostic source descriptor validation and preparation."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from .archive_paths import MANIFEST_ARCHIVE_PATH, _source_relative_path
from .source_record_fields import (
    DEFAULT_CONTENT_TYPE,
    DEFAULT_SOURCE_MAX_BYTES,
    SOURCE_CATEGORIES,
    _normalize_nonnegative_int,
    _normalize_optional_text,
    _strip_required_text,
)

_UNSET = object()


@dataclass(frozen=True, slots=True)
class DiagnosticSource:
    """Caller-supplied diagnostic source descriptor.

    ``collect`` is evaluated only after all source descriptors pass validation.
    Use ``payload`` for already-materialized small fixture data, ``collect`` for
    runtime data, and ``omitted_reason`` when a source is intentionally listed in
    the manifest without collecting content.
    """

    source_id: str
    name: str
    category: str
    collect: Callable[[], object] | None = None
    payload: object = _UNSET
    relative_path: str | None = None
    content_type: str = DEFAULT_CONTENT_TYPE
    max_bytes: int = DEFAULT_SOURCE_MAX_BYTES
    display_path: str | None = None
    logical_label: str | None = None
    omitted_reason: str | None = None


@dataclass(frozen=True, slots=True)
class _PreparedSource:
    source: DiagnosticSource
    source_id: str
    name: str
    category: str
    relative_path: str | None
    content_type: str
    max_bytes: int
    display_path: str | None
    logical_label: str | None
    omitted_reason: str | None

    @property
    def should_omit_without_collection(self) -> bool:
        return self.omitted_reason is not None or (
            self.source.collect is None and self.source.payload is _UNSET
        )


def prepare_sources(sources: Iterable[DiagnosticSource]) -> tuple[_PreparedSource, ...]:
    prepared: list[_PreparedSource] = []
    seen_source_ids: set[str] = set()
    seen_archive_paths: set[str] = {MANIFEST_ARCHIVE_PATH}

    for source in sources:
        validate_source_descriptor(source)
        source_id = _strip_required_text(source.source_id, "source_id")
        if source_id in seen_source_ids:
            raise ValueError(f"duplicate diagnostic source_id: {source_id}")
        seen_source_ids.add(source_id)

        prepared_source = _prepared_source(source, source_id)
        relative_path = prepared_source.relative_path

        if relative_path is not None:
            if relative_path in seen_archive_paths:
                raise ValueError(f"duplicate diagnostic archive path: {relative_path}")
            seen_archive_paths.add(relative_path)

        append_prepared_source(prepared, prepared_source)

    return tuple(prepared)


def validate_source_descriptor(source: object) -> None:
    """Validate descriptor shape and mutually exclusive payload/collector fields."""
    if not isinstance(source, DiagnosticSource):
        raise ValueError("diagnostic sources must be DiagnosticSource instances")
    if source.collect is not None and source.payload is not _UNSET:
        raise ValueError(
            f"diagnostic source {source.source_id!r} cannot define both collect and payload"
        )
    if source.collect is not None and not callable(source.collect):
        raise ValueError(f"diagnostic source {source.source_id!r} collect must be callable")


def append_prepared_source(
    prepared: list[_PreparedSource],
    prepared_source: _PreparedSource,
) -> None:
    prepared.append(prepared_source)


def _prepared_source(source: DiagnosticSource, source_id: str) -> _PreparedSource:
    name = _strip_required_text(source.name, "name")
    category = _strip_required_text(source.category, "category")
    if category not in SOURCE_CATEGORIES:
        raise ValueError(f"invalid diagnostic source category: {category}")

    content_type = _strip_required_text(source.content_type, "content_type")
    max_bytes = _normalize_nonnegative_int(source.max_bytes, "max_bytes")
    display_path = _normalize_optional_text(source.display_path)
    logical_label = _normalize_optional_text(source.logical_label)
    omitted_reason = _normalize_optional_text(source.omitted_reason)
    relative_path = _source_relative_path(source_id, source.relative_path, omitted_reason)

    return _PreparedSource(
        source=source,
        source_id=source_id,
        name=name,
        category=category,
        relative_path=relative_path,
        content_type=content_type,
        max_bytes=max_bytes,
        display_path=display_path,
        logical_label=logical_label,
        omitted_reason=omitted_reason,
    )
