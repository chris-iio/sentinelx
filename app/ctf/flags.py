"""CTF flag detection helpers.

Detects flag-shaped ``PREFIX{...}`` tokens in free text so pasted challenge
output, notes, and descriptions can feed the flag vault automatically.
Detection is purely syntactic; it never verifies a flag against an event
platform.
"""
from __future__ import annotations

import re

FLAG_PATTERN = re.compile(r"\b([A-Za-z][A-Za-z0-9_.-]{0,31})\{([^{}\s]{1,128})\}")

MAX_FLAG_LENGTH = 160
_MAX_MATCHES_PER_TEXT = 64


def detect_flags(text: str) -> list[str]:
    """Return deduplicated flag-shaped tokens found in *text*, first-seen order.

    Args:
        text: Free-form analyst text (notes, challenge output, descriptions).

    Returns:
        Flag strings such as ``HTB{example}``. Empty when nothing matches.
    """
    if not text:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for match in FLAG_PATTERN.finditer(text):
        token = f"{match.group(1)}{{{match.group(2)}}}"
        if len(token) > MAX_FLAG_LENGTH or token in seen:
            continue
        seen.add(token)
        found.append(token)
        if len(found) >= _MAX_MATCHES_PER_TEXT:
            break
    return found
