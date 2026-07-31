"""Common diagnostic text credential pattern redaction rules."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol

REDACTED_TEXT = "[REDACTED]"


class TextRedactionAccumulator(Protocol):
    def add(self, label: str, count: int = 1) -> None: ...


class ExactSecretCandidate(Protocol):
    label: str
    value: str


@dataclass(frozen=True, slots=True)
class _TextRule:
    label: str
    regex: re.Pattern[str]
    replace: Any


def _replace_authorization_bearer(match: re.Match[str]) -> str:
    return f"{match.group('prefix')}Bearer {REDACTED_TEXT}"


def _replace_standalone_bearer(match: re.Match[str]) -> str:
    return f"{match.group('prefix')}Bearer {REDACTED_TEXT}"


def _replace_named_secret(match: re.Match[str]) -> str:
    return f"{match.group('prefix')}{REDACTED_TEXT}"


def _replace_jsonish_field(match: re.Match[str]) -> str:
    quote = match.group("quote") or ""
    close_quote = quote if quote else ""
    return f"{match.group('prefix')}{quote}{REDACTED_TEXT}{close_quote}"


def _query_secret_rule(name: str) -> _TextRule:
    return _TextRule(
        label=f"pattern:query:{name}",
        regex=re.compile(
            rf"(?P<prefix>(?:[?&;]|\b){name}\s*=\s*)(?P<secret>[^&\s\"'<>]+)",
            re.IGNORECASE,
        ),
        replace=_replace_named_secret,
    )


def _jsonish_field_rule(name: str) -> _TextRule:
    return _TextRule(
        label=f"pattern:field:{name}",
        regex=re.compile(
            rf"(?P<prefix>(?<![A-Za-z0-9_])[\"']?{name}[\"']?\s*:\s*)(?P<quote>[\"']?)(?P<secret>[^\s,}}\]\"']+)(?P=quote)",
            re.IGNORECASE,
        ),
        replace=_replace_jsonish_field,
    )


_TEXT_RULES = (
    _TextRule(
        label="pattern:authorization_bearer",
        regex=re.compile(
            r"(?P<prefix>\bauthorization\s*[:=]\s*)bearer\s+"
            r"(?P<secret>[^\s,;\"'<>]+)",
            re.IGNORECASE,
        ),
        replace=_replace_authorization_bearer,
    ),
    _TextRule(
        label="pattern:authorization_bearer",
        regex=re.compile(
            r"(?P<prefix>\b)bearer\s+(?P<secret>[^\s,;\"'<>]+)",
            re.IGNORECASE,
        ),
        replace=_replace_standalone_bearer,
    ),
    _TextRule(
        label="pattern:header:x-api-key",
        regex=re.compile(
            r"(?P<prefix>\bx-api-key\s*[:=]\s*)(?P<secret>[^\s,;\"'<>]+)",
            re.IGNORECASE,
        ),
        replace=_replace_named_secret,
    ),
    _TextRule(
        label="pattern:header:auth-key",
        regex=re.compile(
            r"(?P<prefix>\bauth-key\s*[:=]\s*)(?P<secret>[^\s,;\"'<>]+)",
            re.IGNORECASE,
        ),
        replace=_replace_named_secret,
    ),
    _TextRule(
        label="pattern:header:key",
        regex=re.compile(
            r"(?P<prefix>\bkey\s*[:=]\s*)(?P<secret>[^\s,;\"'<>]+)",
            re.IGNORECASE,
        ),
        replace=_replace_named_secret,
    ),
    _query_secret_rule("api_key"),
    _query_secret_rule("apikey"),
    _query_secret_rule("token"),
    _query_secret_rule("secret"),
    _jsonish_field_rule("api_key"),
    _jsonish_field_rule("apikey"),
    _jsonish_field_rule("token"),
    _jsonish_field_rule("secret"),
)


def apply_exact_secret_redaction(
    text: str,
    candidates: tuple[ExactSecretCandidate, ...],
    acc: TextRedactionAccumulator,
) -> str:
    """Redact configured secrets with literal replacement before regex rules."""
    redacted = text
    for secret in candidates:
        if not secret.value or secret.value == REDACTED_TEXT:
            continue
        occurrences = redacted.count(secret.value)
        if occurrences:
            redacted = redacted.replace(secret.value, REDACTED_TEXT)
            acc.add(secret.label, occurrences)
    return redacted


def apply_text_pattern_redaction(
    text: str,
    acc: TextRedactionAccumulator,
) -> str:
    """Apply common credential pattern redaction to a string."""
    redacted = text

    for rule in _TEXT_RULES:
        redacted = _apply_text_rule(redacted, rule, acc)

    return redacted


def _apply_text_rule(
    text: str,
    rule: _TextRule,
    acc: TextRedactionAccumulator,
) -> str:
    replacements = 0

    def _callback(match: re.Match[str]) -> str:
        nonlocal replacements
        secret_value = match.groupdict().get("secret") or ""
        if secret_value == REDACTED_TEXT:
            return match.group(0)
        replacements += 1
        return rule.replace(match)

    redacted = rule.regex.sub(_callback, text)
    acc.add(rule.label, replacements)
    return redacted


def redact_text_with_candidates(
    text: str,
    candidates: tuple[ExactSecretCandidate, ...],
    acc: TextRedactionAccumulator,
) -> str:
    """Apply exact configured-secret and pattern redaction to text."""
    redacted = apply_exact_secret_redaction(text, candidates, acc)
    return apply_text_pattern_redaction(redacted, acc)
