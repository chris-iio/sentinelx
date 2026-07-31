"""Recursive diagnostic payload redaction traversal."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .payload_rules import (
    AUTHORIZATION_BEARER_LABEL,
    payload_key_redaction_label,
)
from .text_rules import REDACTED_TEXT
from app.text_utils import stripped_text_or_none

CIRCULAR_TEXT = "[Circular]"
MAX_DEPTH_TEXT = "[MaxDepth]"
PAYLOAD_SEQUENCE_TYPES = (list, tuple)
PAYLOAD_CONTAINER_TYPES = (dict, list, tuple)

TextRedactor = Callable[[str, tuple[Any, ...], Any], str]
ExactSecretRedactor = Callable[[str, tuple[Any, ...], Any], str]


def safe_payload_key(
    value: object,
    candidates: tuple[Any, ...],
    acc: Any,
    *,
    text_redactor: TextRedactor,
) -> object:
    if isinstance(value, str):
        return text_redactor(value, candidates, acc)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return f"[UnserializableKey:{type(value).__name__}]"


def redact_entire_scalar(
    value: object,
    label: str,
    candidates: tuple[Any, ...],
    acc: Any,
    *,
    exact_secret_redactor: ExactSecretRedactor,
) -> object:
    """Redact a scalar value because its field/header name is credential-like."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = stripped_text_or_none(value)
        if stripped is None:
            return value
        exact_secret_redactor(value, candidates, acc)
        acc.add(label)
        if label == AUTHORIZATION_BEARER_LABEL and stripped.lower().startswith("bearer "):
            return f"Bearer {REDACTED_TEXT}"
        return REDACTED_TEXT
    if isinstance(value, (int, float, bool)):
        return value
    acc.add(label)
    return REDACTED_TEXT


def redact_payload_value(
    value: object,
    candidates: tuple[Any, ...],
    acc: Any,
    *,
    depth: int,
    seen: set[int],
    text_redactor: TextRedactor,
    exact_secret_redactor: ExactSecretRedactor,
) -> object:
    if depth < 0:
        return MAX_DEPTH_TEXT

    if isinstance(value, str):
        return text_redactor(value, candidates, acc)

    if value is None or isinstance(value, (int, float, bool)):
        return value

    value_id = id(value)
    if isinstance(value, PAYLOAD_CONTAINER_TYPES):
        if value_id in seen:
            return CIRCULAR_TEXT
        seen.add(value_id)
        try:
            if isinstance(value, dict):
                return redact_payload_mapping(
                    value,
                    candidates,
                    acc,
                    depth=depth - 1,
                    seen=seen,
                    text_redactor=text_redactor,
                    exact_secret_redactor=exact_secret_redactor,
                )

            return redact_payload_sequence(
                value,
                candidates,
                acc,
                depth=depth - 1,
                seen=seen,
                text_redactor=text_redactor,
                exact_secret_redactor=exact_secret_redactor,
            )
        finally:
            seen.remove(value_id)

    return f"[Unserializable:{type(value).__name__}]"


def redact_payload_mapping(
    value: dict[object, object],
    candidates: tuple[Any, ...],
    acc: Any,
    *,
    depth: int,
    seen: set[int],
    text_redactor: TextRedactor,
    exact_secret_redactor: ExactSecretRedactor,
) -> dict[object, object]:
    redacted_dict: dict[object, object] = {}
    for raw_key in value:
        raw_child = value[raw_key]
        redacted_key = safe_payload_key(
            raw_key,
            candidates,
            acc,
            text_redactor=text_redactor,
        )
        key_label = payload_key_redaction_label(raw_key)
        if key_label is not None:
            child = redact_entire_scalar(
                raw_child,
                key_label,
                candidates,
                acc,
                exact_secret_redactor=exact_secret_redactor,
            )
        else:
            child = redact_payload_value(
                raw_child,
                candidates,
                acc,
                depth=depth,
                seen=seen,
                text_redactor=text_redactor,
                exact_secret_redactor=exact_secret_redactor,
            )
        redacted_dict[redacted_key] = child
    return redacted_dict


def redact_payload_sequence(
    value: list[object] | tuple[object, ...],
    candidates: tuple[Any, ...],
    acc: Any,
    *,
    depth: int,
    seen: set[int],
    text_redactor: TextRedactor,
    exact_secret_redactor: ExactSecretRedactor,
) -> list[object]:
    value_count = len(value)
    if value_count == 0:
        return []
    if value_count == 1:
        return [
            redact_payload_child(
                value[0],
                candidates,
                acc,
                depth=depth,
                seen=seen,
                text_redactor=text_redactor,
                exact_secret_redactor=exact_secret_redactor,
            )
        ]
    if value_count == 2:
        return [
            redact_payload_child(
                value[0],
                candidates,
                acc,
                depth=depth,
                seen=seen,
                text_redactor=text_redactor,
                exact_secret_redactor=exact_secret_redactor,
            ),
            redact_payload_child(
                value[1],
                candidates,
                acc,
                depth=depth,
                seen=seen,
                text_redactor=text_redactor,
                exact_secret_redactor=exact_secret_redactor,
            ),
        ]
    if value_count == 3:
        return [
            redact_payload_child(
                value[0],
                candidates,
                acc,
                depth=depth,
                seen=seen,
                text_redactor=text_redactor,
                exact_secret_redactor=exact_secret_redactor,
            ),
            redact_payload_child(
                value[1],
                candidates,
                acc,
                depth=depth,
                seen=seen,
                text_redactor=text_redactor,
                exact_secret_redactor=exact_secret_redactor,
            ),
            redact_payload_child(
                value[2],
                candidates,
                acc,
                depth=depth,
                seen=seen,
                text_redactor=text_redactor,
                exact_secret_redactor=exact_secret_redactor,
            ),
        ]
    if value_count == 4:
        return [
            redact_payload_child(
                value[0],
                candidates,
                acc,
                depth=depth,
                seen=seen,
                text_redactor=text_redactor,
                exact_secret_redactor=exact_secret_redactor,
            ),
            redact_payload_child(
                value[1],
                candidates,
                acc,
                depth=depth,
                seen=seen,
                text_redactor=text_redactor,
                exact_secret_redactor=exact_secret_redactor,
            ),
            redact_payload_child(
                value[2],
                candidates,
                acc,
                depth=depth,
                seen=seen,
                text_redactor=text_redactor,
                exact_secret_redactor=exact_secret_redactor,
            ),
            redact_payload_child(
                value[3],
                candidates,
                acc,
                depth=depth,
                seen=seen,
                text_redactor=text_redactor,
                exact_secret_redactor=exact_secret_redactor,
            ),
        ]

    redacted_items: list[object] = []
    for child in value:
        append_redacted_payload_child(
            redacted_items,
            child,
            candidates,
            acc,
            depth=depth,
            seen=seen,
            text_redactor=text_redactor,
            exact_secret_redactor=exact_secret_redactor,
        )
    return redacted_items


def append_redacted_payload_child(
    redacted_items: list[object],
    child: object,
    candidates: tuple[Any, ...],
    acc: Any,
    *,
    depth: int,
    seen: set[int],
    text_redactor: TextRedactor,
    exact_secret_redactor: ExactSecretRedactor,
) -> None:
    redacted_items.append(
        redact_payload_child(
            child,
            candidates,
            acc,
            depth=depth,
            seen=seen,
            text_redactor=text_redactor,
            exact_secret_redactor=exact_secret_redactor,
        )
    )


def redact_payload_child(
    child: object,
    candidates: tuple[Any, ...],
    acc: Any,
    *,
    depth: int,
    seen: set[int],
    text_redactor: TextRedactor,
    exact_secret_redactor: ExactSecretRedactor,
) -> object:
    """Redact one child value through the shared recursive boundary."""
    return redact_payload_value(
        child,
        candidates,
        acc,
        depth=depth,
        seen=seen,
        text_redactor=text_redactor,
        exact_secret_redactor=exact_secret_redactor,
    )
