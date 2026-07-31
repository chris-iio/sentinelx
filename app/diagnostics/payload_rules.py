"""Credential-like diagnostic payload key classification."""

from __future__ import annotations

from app.text_utils import stripped_text_or_none

PAYLOAD_QUERY_NAMES = ("api_key", "apikey", "token", "secret")
PAYLOAD_FIELD_NAMES = frozenset(PAYLOAD_QUERY_NAMES)
PAYLOAD_AUTH_HEADER_KEYS = frozenset(("authorization", "x-api-key", "auth-key", "key"))
AUTHORIZATION_BEARER_LABEL = "pattern:authorization_bearer"


def payload_key_redaction_label(raw_key: object) -> str | None:
    """Return the redaction label implied by a diagnostic payload key."""
    if not isinstance(raw_key, str):
        return None
    stripped_key = stripped_text_or_none(raw_key)
    if stripped_key is None:
        return None

    key_for_rules = stripped_key.lower()
    if key_for_rules in PAYLOAD_FIELD_NAMES:
        return f"pattern:field:{key_for_rules}"
    if key_for_rules == "authorization":
        return AUTHORIZATION_BEARER_LABEL
    if key_for_rules in PAYLOAD_AUTH_HEADER_KEYS:
        return f"pattern:header:{key_for_rules}"
    return None
