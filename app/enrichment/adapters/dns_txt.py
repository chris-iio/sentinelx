"""Shared DNS TXT chunk decoding helpers."""
from __future__ import annotations

from app.text_utils import decode_utf8_replace


def decode_txt_chunks(strings) -> str:
    string_count = len(strings)
    if string_count == 0:
        raw_text = b""
    elif string_count == 1:
        raw_text = strings[0]
    elif string_count == 2:
        raw_text = strings[0] + strings[1]
    elif string_count == 3:
        raw_text = strings[0] + strings[1] + strings[2]
    elif string_count == 4:
        raw_text = strings[0] + strings[1] + strings[2] + strings[3]
    else:
        raw_text = b"".join(strings)
    return decode_utf8_replace(raw_text)
