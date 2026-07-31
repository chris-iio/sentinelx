"""Diagnostic archive JSON payload normalization helpers."""

from __future__ import annotations

from collections.abc import Callable, Mapping

JSON_SAFE_SEQUENCE_TYPES = (tuple, list)
SequenceNormalizer = Callable[[tuple[object, ...] | list[object]], list[object]]


def safe_json_payload(
    value: object,
    *,
    sequence_normalizer: SequenceNormalizer | None = None,
) -> object:
    """Return a JSON-encodable diagnostic payload without calling arbitrary reprs."""
    normalize_sequence = sequence_normalizer or safe_json_sequence
    if isinstance(value, Mapping):
        return safe_json_mapping(value, sequence_normalizer=normalize_sequence)
    if isinstance(value, JSON_SAFE_SEQUENCE_TYPES):
        return normalize_sequence(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return safe_json_default(value)


def safe_json_mapping(
    value: Mapping[object, object],
    *,
    sequence_normalizer: SequenceNormalizer | None = None,
) -> dict[str, object]:
    normalize_sequence = sequence_normalizer or safe_json_sequence
    if type(value) is dict:
        value_count = len(value)
        if value_count == 0:
            return {}
        if value_count == 1:
            for key in value:
                return {
                    str(key): safe_json_payload(
                        value[key],
                        sequence_normalizer=normalize_sequence,
                    )
                }
        if value_count == 2:
            key_iter = iter(value)
            first_key = next(key_iter)
            second_key = next(key_iter)
            return {
                str(first_key): safe_json_payload(
                    value[first_key],
                    sequence_normalizer=normalize_sequence,
                ),
                str(second_key): safe_json_payload(
                    value[second_key],
                    sequence_normalizer=normalize_sequence,
                ),
            }
        if value_count == 3:
            key_iter = iter(value)
            first_key = next(key_iter)
            second_key = next(key_iter)
            third_key = next(key_iter)
            return {
                str(first_key): safe_json_payload(
                    value[first_key],
                    sequence_normalizer=normalize_sequence,
                ),
                str(second_key): safe_json_payload(
                    value[second_key],
                    sequence_normalizer=normalize_sequence,
                ),
                str(third_key): safe_json_payload(
                    value[third_key],
                    sequence_normalizer=normalize_sequence,
                ),
            }
        if value_count == 4:
            key_iter = iter(value)
            first_key = next(key_iter)
            second_key = next(key_iter)
            third_key = next(key_iter)
            fourth_key = next(key_iter)
            return {
                str(first_key): safe_json_payload(
                    value[first_key],
                    sequence_normalizer=normalize_sequence,
                ),
                str(second_key): safe_json_payload(
                    value[second_key],
                    sequence_normalizer=normalize_sequence,
                ),
                str(third_key): safe_json_payload(
                    value[third_key],
                    sequence_normalizer=normalize_sequence,
                ),
                str(fourth_key): safe_json_payload(
                    value[fourth_key],
                    sequence_normalizer=normalize_sequence,
                ),
            }

    safe: dict[str, object] = {}
    for key in value:
        set_safe_json_mapping_value(
            safe,
            key,
            value[key],
            sequence_normalizer=normalize_sequence,
        )
    return safe


def set_safe_json_mapping_value(
    safe: dict[str, object],
    key: object,
    child: object,
    *,
    sequence_normalizer: SequenceNormalizer,
) -> None:
    safe[str(key)] = safe_json_payload(
        child,
        sequence_normalizer=sequence_normalizer,
    )


def safe_json_sequence(
    value: tuple[object, ...] | list[object],
    *,
    sequence_normalizer: SequenceNormalizer | None = None,
) -> list[object]:
    normalize_sequence = sequence_normalizer or safe_json_sequence
    value_count = len(value)
    if value_count == 0:
        return []
    if value_count == 1:
        return [
            safe_json_payload(value[0], sequence_normalizer=normalize_sequence)
        ]
    if value_count == 2:
        return [
            safe_json_payload(value[0], sequence_normalizer=normalize_sequence),
            safe_json_payload(value[1], sequence_normalizer=normalize_sequence),
        ]
    if value_count == 3:
        return [
            safe_json_payload(value[0], sequence_normalizer=normalize_sequence),
            safe_json_payload(value[1], sequence_normalizer=normalize_sequence),
            safe_json_payload(value[2], sequence_normalizer=normalize_sequence),
        ]
    if value_count == 4:
        return [
            safe_json_payload(value[0], sequence_normalizer=normalize_sequence),
            safe_json_payload(value[1], sequence_normalizer=normalize_sequence),
            safe_json_payload(value[2], sequence_normalizer=normalize_sequence),
            safe_json_payload(value[3], sequence_normalizer=normalize_sequence),
        ]

    safe_items: list[object] = []
    for child in value:
        append_safe_json_item(safe_items, child, sequence_normalizer=normalize_sequence)
    return safe_items


def append_safe_json_item(
    safe_items: list[object],
    child: object,
    *,
    sequence_normalizer: SequenceNormalizer,
) -> None:
    safe_items.append(
        safe_json_payload(child, sequence_normalizer=sequence_normalizer)
    )


def safe_json_default(value: object) -> str:
    return f"[Unserializable:{type(value).__name__}]"
