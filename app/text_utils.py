"""Shared string helpers for request and health payload normalization."""
from __future__ import annotations

import re

_WHITESPACE_RE = re.compile(r"\s+")


def has_non_whitespace(value: str) -> bool:
    """Return whether *value* contains at least one non-whitespace character."""
    for char in value:
        if not char.isspace():
            return True
    return False


def stripped_bounded_text(value: str, *, max_chars: int) -> str | None:
    """Return stripped bounded text, or None when the stripped text is empty."""
    bounds = _stripped_bounds(value)
    if bounds is None:
        return None
    start, end = bounds
    bounded_end = start + max_chars
    if bounded_end < end:
        return value[start:bounded_end]
    return value[start:end]


def stripped_text_or_none(value: str) -> str | None:
    """Return stripped text, or None when the stripped text is empty."""
    bounds = _stripped_bounds(value)
    if bounds is None:
        return None
    start, end = bounds
    if start == 0 and end == len(value):
        return value
    return value[start:end]


def _stripped_bounds(value: str) -> tuple[int, int] | None:
    """Return the non-whitespace bounds for *value*, or None when blank."""
    start = 0
    end = len(value)
    while start < end and value[start].isspace():
        start += 1
    if start == end:
        return None
    while end > start and value[end - 1].isspace():
        end -= 1
    return start, end


def stripped_bounded_non_whitespace(value: str, *, max_chars: int) -> str | None:
    """Return bounded stripped text after scanning for non-whitespace content."""
    return stripped_bounded_text(value, max_chars=max_chars)


def collapse_whitespace(value: str) -> str:
    """Return text with leading/trailing and internal whitespace collapsed."""
    bounds = _stripped_bounds(value)
    if bounds is None:
        return ""
    start, end = bounds
    return _WHITESPACE_RE.sub(" ", value[start:end])


def decode_utf8_replace(value: bytes | bytearray) -> str:
    """Decode UTF-8 bytes, replacing malformed byte sequences."""
    return bytes(value).decode("utf-8", errors="replace")
