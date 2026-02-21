"""IOC Normalizer — defanging to canonical form.

Converts defanged IOC strings to their canonical (refanged) form.
Handles all common defanging patterns used in threat intelligence reports.

Security:
- Pure function: no side effects, no network calls, no imports beyond `re`
- Input is not trusted — patterns apply sequentially without interpretation
"""
from __future__ import annotations

import re

# Ordered list of (compiled_pattern, replacement_string) tuples.
# Applied sequentially — ordering matters for compound patterns.
#
# Precedence rules:
# 1. Scheme [://] variants handled before bare hxxp:// to avoid double-replacement
# 2. Dot patterns applied after scheme to handle URLs with defanged dots
# 3. At-sign defanging comes last
_DEFANG_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # --- Scheme normalization ---
    # hxxps[://] must come before hxxp[://] (longer match first)
    (re.compile(r"hxxps\[://\]", re.IGNORECASE), "https://"),
    (re.compile(r"hxxp\[://\]", re.IGNORECASE), "http://"),
    # hxxps[:] and hxxp[:] — bracket colon only; // already present in text
    (re.compile(r"hxxps\[:\]", re.IGNORECASE), "https:"),
    (re.compile(r"hxxp\[:\]", re.IGNORECASE), "http:"),
    # https[:/] and http[:/] — bracket colon-slash variant (replaces separator)
    (re.compile(r"https\[:/\]", re.IGNORECASE), "https://"),
    (re.compile(r"http\[:/\]", re.IGNORECASE), "http://"),
    # hxxps:// and hxxp:// — bare defanged scheme (must come after bracket variants)
    (re.compile(r"hxxps://", re.IGNORECASE), "https://"),
    (re.compile(r"hxxp://", re.IGNORECASE), "http://"),
    # --- Dot defanging ---
    # Bracket, paren, brace variants: [.] (.) {.}
    (re.compile(r"\[\.\]"), "."),
    (re.compile(r"\(\.\)"), "."),
    (re.compile(r"\{\.\}"), "."),
    # Word variants: [dot] (dot) {dot}
    (re.compile(r"\[dot\]", re.IGNORECASE), "."),
    (re.compile(r"\(dot\)", re.IGNORECASE), "."),
    (re.compile(r"\{dot\}", re.IGNORECASE), "."),
    # Underscore variant: _dot_
    (re.compile(r"_dot_", re.IGNORECASE), "."),
    # --- At-sign defanging ---
    # [@] and (@) variants
    (re.compile(r"\[@\]"), "@"),
    (re.compile(r"\(@\)"), "@"),
    # [at] variant
    (re.compile(r"\[at\]", re.IGNORECASE), "@"),
]


def normalize(text: str) -> str:
    """Refang a single defanged IOC string to its canonical form.

    Applies all known defanging patterns sequentially to the input string.
    Already-clean inputs are returned unchanged. Empty string returns empty string.

    Args:
        text: A potentially defanged IOC string from analyst input.

    Returns:
        The canonical (refanged) form of the IOC string.
        If no defanging patterns match, the input is returned unchanged.

    Examples:
        >>> normalize("hxxps://example[.]com")
        'https://example.com'
        >>> normalize("192[.]168[.]1[.]1")
        '192.168.1.1'
        >>> normalize("192.168.1.1")  # already clean
        '192.168.1.1'
    """
    if not text:
        return text

    result = text
    for pattern, replacement in _DEFANG_PATTERNS:
        result = pattern.sub(replacement, result)
    return result
