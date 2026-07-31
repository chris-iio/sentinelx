"""Diagnostic archive path and generated filename safety helpers."""

from __future__ import annotations

import posixpath
import re
from collections.abc import Iterator

from .policy import DIAGNOSTIC_SANITIZATION_POLICY
from .source_record_fields import _strip_required_text

MANIFEST_ARCHIVE_PATH = "manifest.json"
DEFAULT_SOURCE_PREFIX = "sources"
_FORBIDDEN_PATH_SEGMENTS = frozenset((".gsd", ".planning", ".audits", ".git"))
_DOT_PATH_SEGMENTS = frozenset(("", ".", ".."))
_SAFE_SOURCE_ID_CHARS = re.compile(r"[^A-Za-z0-9_.-]+")
_SOURCE_FILENAME_TRIM_CHARS = frozenset("._-")
_ARCHIVE_PATH_MAX_CHARS = DIAGNOSTIC_SANITIZATION_POLICY.max_archive_path_chars
_SAFE_SOURCE_FILENAME_MAX_CHARS = DIAGNOSTIC_SANITIZATION_POLICY.max_generated_filename_chars


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
    return _validate_archive_path(
        f"{DEFAULT_SOURCE_PREFIX}/{_safe_source_filename(source_id)}.json"
    )


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
    raw_path = _strip_required_text(
        path,
        "relative_path",
        max_chars=_ARCHIVE_PATH_MAX_CHARS,
    )
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
