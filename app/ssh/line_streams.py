"""Line-stream helpers for SSH auth.log parsing."""
from __future__ import annotations

import io
from collections.abc import Iterator
from typing import IO

from app.text_utils import decode_utf8_replace


def iter_lines(stream: IO[bytes] | IO[str]) -> Iterator[str]:
    """Yield decoded text lines from a bytes or text stream."""
    if isinstance(stream, (io.RawIOBase, io.BufferedIOBase, io.BytesIO)):
        for raw_line in stream:
            yield coerce_stream_line(raw_line)
        return

    for raw_line in stream:
        yield raw_line


def coerce_stream_line(raw_line: object) -> str:
    """Return one stream line as text, replacing malformed UTF-8 bytes."""
    if isinstance(raw_line, (bytes, bytearray)):
        return decode_utf8_replace(raw_line)
    return str(raw_line)


def strip_line_ending(value: str) -> str:
    """Return *value* without trailing CR/LF characters."""
    end = len(value)
    while end > 0 and value[end - 1] in "\r\n":
        end -= 1
    return value[:end]
