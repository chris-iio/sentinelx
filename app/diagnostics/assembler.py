"""Deterministic backend-only diagnostic bundle assembly.

The assembler consumes caller-supplied diagnostic source descriptors and returns a
bounded ZIP archive plus the manifest object describing every considered source.
It deliberately does not know about Flask routes or filesystem traversal; callers
are responsible for collecting runtime/fixture data and handing it to this module
as values or lazy callables.
"""
from __future__ import annotations

import io
import json
import posixpath
import re
import zipfile
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

from app.diagnostics.contract import (
    DEFAULT_CONTENT_TYPE,
    DEFAULT_OMITTED_REASON,
    DEFAULT_SOURCE_MAX_BYTES,
    DiagnosticManifest,
    DiagnosticSourceRecord,
    SOURCE_CATEGORIES,
    SOURCE_STATUS_ERROR,
    SOURCE_STATUS_INCLUDED,
    SOURCE_STATUS_OMITTED,
    SOURCE_STATUS_TRUNCATED,
    manifest_to_json,
    manifest_to_json_bytes,
)
from app.diagnostics.policy import DIAGNOSTIC_SANITIZATION_POLICY
from app.diagnostics.redaction import (
    ConfigSecretStore,
    RedactionMetadata,
    redact_diagnostic_payload,
    redact_diagnostic_text,
)
from app.text_utils import decode_utf8_replace, stripped_bounded_text

MANIFEST_ARCHIVE_PATH = "manifest.json"
DEFAULT_SOURCE_PREFIX = "sources"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_FORBIDDEN_PATH_SEGMENTS = frozenset((".gsd", ".planning", ".audits", ".git"))
_DOT_PATH_SEGMENTS = frozenset(("", ".", ".."))
_JSON_SAFE_SEQUENCE_TYPES = (tuple, list)
_SAFE_SOURCE_ID_CHARS = re.compile(r"[^A-Za-z0-9_.-]+")
_SOURCE_FILENAME_TRIM_CHARS = frozenset("._-")
_ARCHIVE_PATH_MAX_CHARS = DIAGNOSTIC_SANITIZATION_POLICY.max_archive_path_chars
_SAFE_SOURCE_FILENAME_MAX_CHARS = DIAGNOSTIC_SANITIZATION_POLICY.max_generated_filename_chars
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
class DiagnosticBundle:
    """Assembled diagnostic ZIP bytes and safe inspection metadata."""

    archive_bytes: bytes
    manifest: DiagnosticManifest
    archive_paths: tuple[str, ...] = field(default_factory=tuple)

    @property
    def archive_size_bytes(self) -> int:
        """Return the final ZIP size in bytes."""
        return len(self.archive_bytes)

    @property
    def summary(self) -> dict[str, int | str | None]:
        """Return secret-free aggregate fields useful to routes/tests."""
        sources = self.manifest.sorted_sources
        included_count = 0
        truncated_count = 0
        omitted_count = 0
        error_count = 0
        redaction_count = 0
        for source in sources:
            if source.status == SOURCE_STATUS_INCLUDED:
                included_count += 1
            elif source.status == SOURCE_STATUS_TRUNCATED:
                truncated_count += 1
            elif source.status == SOURCE_STATUS_OMITTED:
                omitted_count += 1
            elif source.status == SOURCE_STATUS_ERROR:
                error_count += 1
            redaction_count += source.redaction_count

        return {
            "schema_version": self.manifest.schema_version,
            "generated_at": self.manifest.generated_at,
            "source_count": len(sources),
            "included_count": included_count,
            "truncated_count": truncated_count,
            "omitted_count": omitted_count,
            "error_count": error_count,
            "redaction_count": redaction_count,
            "archive_size_bytes": self.archive_size_bytes,
        }


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


def assemble_diagnostic_bundle(
    sources: Iterable[DiagnosticSource],
    *,
    generated_at: str,
    config_store: ConfigSecretStore | None = None,
) -> DiagnosticBundle:
    """Assemble a deterministic bounded diagnostic ZIP archive.

    Validation for duplicate IDs, duplicate archive paths, unsafe paths, malformed
    categories, and ambiguous source descriptors happens before any source
    callable is evaluated.  Individual source collection failures are captured as
    manifest ``error`` records and do not abort unrelated sources.
    """
    prepared_sources = _prepare_sources(sources)

    records: list[DiagnosticSourceRecord] = []
    payload_entries: list[tuple[str, bytes]] = []

    ordered_sources = _ordered_prepared_sources(prepared_sources)

    for prepared in ordered_sources:
        if prepared.should_omit_without_collection:
            records.append(_omitted_record(prepared))
            continue

        try:
            payload = _collect_source_payload(prepared.source)
            encoded, metadata = _redact_and_encode_payload(
                payload,
                content_type=prepared.content_type,
                config_store=config_store,
            )
        except Exception as exc:  # noqa: BLE001 - source failures become manifest records.
            records.append(_error_record(prepared, exc, config_store=config_store))
            continue

        included = encoded[: prepared.max_bytes]
        status = (
            SOURCE_STATUS_TRUNCATED
            if len(encoded) > prepared.max_bytes
            else SOURCE_STATUS_INCLUDED
        )
        record = DiagnosticSourceRecord(
            source_id=prepared.source_id,
            name=prepared.name,
            category=prepared.category,
            status=status,
            relative_path=prepared.relative_path,
            display_path=prepared.display_path,
            logical_label=prepared.logical_label,
            content_type=prepared.content_type,
            original_bytes=len(encoded),
            included_bytes=len(included),
            max_bytes=prepared.max_bytes,
            redaction_count=metadata.redaction_count,
            redaction_labels=metadata.redaction_labels,
        )
        records.append(record)
        if prepared.relative_path is not None:
            payload_entries.append((prepared.relative_path, included))

    manifest = DiagnosticManifest(sources=tuple(records), generated_at=generated_at)
    manifest_bytes = manifest_to_json_bytes(manifest, indent=2)
    archive_entries = [(MANIFEST_ARCHIVE_PATH, manifest_bytes)]
    archive_entries.extend(_ordered_payload_entries(payload_entries))
    archive_bytes = _write_stable_zip(archive_entries)
    archive_paths: list[str] = []
    for path, _ in archive_entries:
        archive_paths.append(path)

    return DiagnosticBundle(
        archive_bytes=archive_bytes,
        manifest=manifest,
        archive_paths=tuple(archive_paths),
    )


def _ordered_prepared_sources(sources: tuple[_PreparedSource, ...]) -> tuple[_PreparedSource, ...]:
    source_count = len(sources)
    if source_count <= 1:
        return sources
    if source_count == 2:
        first = sources[0]
        second = sources[1]
        if first.source_id <= second.source_id:
            return (first, second)
        return (second, first)
    if source_count == 3:
        first = sources[0]
        second = sources[1]
        third = sources[2]
        if second.source_id < first.source_id:
            first, second = second, first
        if third.source_id < second.source_id:
            second, third = third, second
            if second.source_id < first.source_id:
                first, second = second, first
        return (first, second, third)
    return tuple(sorted(sources, key=lambda item: item.source_id))


def _ordered_payload_entries(entries: list[tuple[str, bytes]]) -> tuple[tuple[str, bytes], ...]:
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
    return tuple(sorted(entries))


def _prepare_sources(sources: Iterable[DiagnosticSource]) -> tuple[_PreparedSource, ...]:
    prepared: list[_PreparedSource] = []
    seen_source_ids: set[str] = set()
    seen_archive_paths: set[str] = {MANIFEST_ARCHIVE_PATH}

    for source in sources:
        if not isinstance(source, DiagnosticSource):
            raise ValueError("diagnostic sources must be DiagnosticSource instances")
        if source.collect is not None and source.payload is not _UNSET:
            raise ValueError(f"diagnostic source {source.source_id!r} cannot define both collect and payload")
        if source.collect is not None and not callable(source.collect):
            raise ValueError(f"diagnostic source {source.source_id!r} collect must be callable")

        source_id = _required_text(source.source_id, "source_id")
        if source_id in seen_source_ids:
            raise ValueError(f"duplicate diagnostic source_id: {source_id}")
        seen_source_ids.add(source_id)

        name = _required_text(source.name, "name")
        category = _required_text(source.category, "category")
        if category not in SOURCE_CATEGORIES:
            raise ValueError(f"invalid diagnostic source category: {category}")

        content_type = _required_text(source.content_type, "content_type")
        max_bytes = _nonnegative_int(source.max_bytes, "max_bytes")
        display_path = _optional_text(source.display_path)
        logical_label = _optional_text(source.logical_label)
        omitted_reason = _optional_text(source.omitted_reason)
        relative_path = _source_relative_path(source_id, source.relative_path, omitted_reason)

        if relative_path is not None:
            if relative_path in seen_archive_paths:
                raise ValueError(f"duplicate diagnostic archive path: {relative_path}")
            seen_archive_paths.add(relative_path)

        prepared.append(
            _PreparedSource(
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
        )

    return tuple(prepared)


def _source_relative_path(
    source_id: str,
    caller_path: str | None,
    omitted_reason: str | None,
) -> str | None:
    if caller_path is not None:
        safe_path = _validate_archive_path(caller_path)
        if omitted_reason is not None:
            return None
        return safe_path
    if omitted_reason is not None:
        return None
    return _validate_archive_path(f"{DEFAULT_SOURCE_PREFIX}/{_safe_source_filename(source_id)}.json")


def _safe_source_filename(source_id: str) -> str:
    filename = _trim_source_filename(_SAFE_SOURCE_ID_CHARS.sub("_", source_id))
    if not filename:
        raise ValueError(f"source_id {source_id!r} does not produce a safe archive filename")
    return filename[:_SAFE_SOURCE_FILENAME_MAX_CHARS]


def _trim_source_filename(value: str) -> str:
    """Trim generated filename punctuation that is unsafe at path boundaries."""
    start = 0
    end = len(value)
    while start < end and value[start] in _SOURCE_FILENAME_TRIM_CHARS:
        start += 1
    while end > start and value[end - 1] in _SOURCE_FILENAME_TRIM_CHARS:
        end -= 1
    return value[start:end]


def _validate_archive_path(path: str) -> str:
    raw_path = _required_text(path, "relative_path", max_chars=_ARCHIVE_PATH_MAX_CHARS)
    if "\\" in raw_path:
        raise ValueError(f"unsafe diagnostic archive path: {raw_path}")
    if raw_path.startswith("/") or raw_path.startswith("//") or re.match(r"^[A-Za-z]:", raw_path):
        raise ValueError(f"unsafe diagnostic archive path: {raw_path}")

    for part in _iter_archive_path_segments(raw_path):
        if part in _DOT_PATH_SEGMENTS or part.lower() in _FORBIDDEN_PATH_SEGMENTS:
            raise ValueError(f"unsafe diagnostic archive path: {raw_path}")

    normalized = posixpath.normpath(raw_path)
    if normalized == "." or normalized.startswith("../") or normalized == "..":
        raise ValueError(f"unsafe diagnostic archive path: {raw_path}")
    if normalized == MANIFEST_ARCHIVE_PATH:
        raise ValueError("diagnostic source path cannot collide with manifest.json")
    return normalized


def _iter_archive_path_segments(raw_path: str) -> Iterator[str]:
    start = 0
    while True:
        separator = raw_path.find("/", start)
        if separator < 0:
            yield raw_path[start:]
            return
        yield raw_path[start:separator]
        start = separator + 1


def _collect_source_payload(source: DiagnosticSource) -> object:
    if source.collect is not None:
        return source.collect()
    return source.payload


def _redact_and_encode_payload(
    payload: object,
    *,
    content_type: str,
    config_store: ConfigSecretStore | None,
) -> tuple[bytes, RedactionMetadata]:
    if isinstance(payload, bytes):
        text = decode_utf8_replace(payload)
        redacted, metadata = redact_diagnostic_text(text, config_store=config_store)
        return redacted.encode("utf-8"), metadata

    if isinstance(payload, str):
        redacted, metadata = redact_diagnostic_text(payload, config_store=config_store)
        return redacted.encode("utf-8"), metadata

    redacted_payload, metadata = redact_diagnostic_payload(payload, config_store=config_store)
    json_safe_payload = _json_safe(redacted_payload)
    encoded = json.dumps(
        json_safe_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=_safe_json_default,
    ).encode("utf-8")
    return encoded, metadata


def _json_safe(value: object) -> object:
    if isinstance(value, Mapping):
        if type(value) is dict:
            value_count = len(value)
            if value_count == 0:
                return {}
            if value_count == 1:
                for key in value:
                    return {str(key): _json_safe(value[key])}
        safe: dict[str, object] = {}
        for key in value:
            safe[str(key)] = _json_safe(value[key])
        return safe
    if isinstance(value, _JSON_SAFE_SEQUENCE_TYPES):
        return _json_safe_sequence(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return _safe_json_default(value)


def _json_safe_sequence(value: tuple[object, ...] | list[object]) -> list[object]:
    value_count = len(value)
    if value_count == 0:
        return []
    if value_count == 1:
        return [_json_safe(value[0])]
    if value_count == 2:
        return [_json_safe(value[0]), _json_safe(value[1])]

    safe_items: list[object] = []
    for child in value:
        safe_items.append(_json_safe(child))
    return safe_items


def _safe_json_default(value: object) -> str:
    return f"[Unserializable:{type(value).__name__}]"


def _omitted_record(prepared: _PreparedSource) -> DiagnosticSourceRecord:
    return DiagnosticSourceRecord(
        source_id=prepared.source_id,
        name=prepared.name,
        category=prepared.category,
        status=SOURCE_STATUS_OMITTED,
        display_path=prepared.display_path,
        logical_label=prepared.logical_label,
        content_type=prepared.content_type,
        max_bytes=prepared.max_bytes,
        omitted_reason=prepared.omitted_reason or DEFAULT_OMITTED_REASON,
    )


def _error_record(
    prepared: _PreparedSource,
    exc: Exception,
    *,
    config_store: ConfigSecretStore | None,
) -> DiagnosticSourceRecord:
    error_text = _exception_summary(exc)
    safe_error_summary, metadata = redact_diagnostic_text(error_text, config_store=config_store)
    return DiagnosticSourceRecord(
        source_id=prepared.source_id,
        name=prepared.name,
        category=prepared.category,
        status=SOURCE_STATUS_ERROR,
        display_path=prepared.display_path,
        logical_label=prepared.logical_label,
        content_type=prepared.content_type,
        max_bytes=prepared.max_bytes,
        safe_error_summary=safe_error_summary,
        redaction_count=metadata.redaction_count,
        redaction_labels=metadata.redaction_labels,
    )


def _exception_summary(exc: Exception) -> str:
    try:
        message = str(exc)
    except Exception:  # noqa: BLE001 - defensive summary fallback must not leak reprs.
        message = ""
    if message:
        return f"{type(exc).__name__}: {message}"
    return type(exc).__name__


def _write_stable_zip(entries: Iterable[tuple[str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_STORED) as archive:
        for path, payload in entries:
            info = zipfile.ZipInfo(filename=path, date_time=ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o600 << 16
            archive.writestr(info, payload)
    return buffer.getvalue()


def _required_text(value: object, field_name: str, *, max_chars: int = 160) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string")
    stripped = stripped_bounded_text(value, max_chars=max_chars)
    if stripped is None:
        raise ValueError(f"{field_name} must be a non-empty string")
    return stripped


def _optional_text(value: object, *, max_chars: int = 160) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    return stripped_bounded_text(value, max_chars=max_chars)


def _nonnegative_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be a non-negative integer")
    if value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


__all__ = [
    "DiagnosticBundle",
    "DiagnosticSource",
    "assemble_diagnostic_bundle",
]
