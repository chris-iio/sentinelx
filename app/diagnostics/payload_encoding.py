"""Diagnostic source collection, redaction, and payload encoding helpers."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .json_safe import (
    safe_json_default,
    safe_json_payload,
)
from .redaction import (
    redact_diagnostic_payload,
    redact_diagnostic_text,
)
from app.text_utils import decode_utf8_replace

if TYPE_CHECKING:
    from .redaction import ConfigSecretStore, RedactionMetadata
    from .source_preparation import DiagnosticSource


def collect_source_payload(source: DiagnosticSource) -> object:
    """Return a diagnostic source payload from its lazy collector or value."""
    if source.collect is not None:
        return source.collect()
    return source.payload


def redact_and_encode_payload(
    payload: object,
    *,
    content_type: str,
    config_store: ConfigSecretStore | None,
) -> tuple[bytes, RedactionMetadata]:
    """Redact a diagnostic payload and encode it for archive storage."""
    if isinstance(payload, bytes):
        return redact_and_encode_text(
            decode_utf8_replace(payload),
            config_store=config_store,
        )

    if isinstance(payload, str):
        return redact_and_encode_text(payload, config_store=config_store)

    return redact_and_encode_json_payload(payload, config_store=config_store)


def redact_and_encode_json_payload(
    payload: object,
    *,
    config_store: ConfigSecretStore | None,
) -> tuple[bytes, RedactionMetadata]:
    redacted_payload, metadata = redact_diagnostic_payload(payload, config_store=config_store)
    encoded = json.dumps(
        safe_json_payload(redacted_payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=safe_json_default,
    ).encode("utf-8")
    return encoded, metadata


def redact_and_encode_text(
    text: str,
    *,
    config_store: ConfigSecretStore | None,
) -> tuple[bytes, RedactionMetadata]:
    redacted, metadata = redact_diagnostic_text(text, config_store=config_store)
    return redacted.encode("utf-8"), metadata
