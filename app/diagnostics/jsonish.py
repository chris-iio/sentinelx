"""JSON-safe diagnostic payload coercion helpers."""

from __future__ import annotations

from collections.abc import Mapping
from itertools import islice
from typing import Any

from .policy import DIAGNOSTIC_SANITIZATION_POLICY

_MAX_SAFE_STRING_CHARS = DIAGNOSTIC_SANITIZATION_POLICY.max_safe_string_chars
_MAX_LIST_ITEMS = DIAGNOSTIC_SANITIZATION_POLICY.max_list_items
_MAX_DICT_ITEMS = DIAGNOSTIC_SANITIZATION_POLICY.max_dict_items
_MAX_DEPTH = DIAGNOSTIC_SANITIZATION_POLICY.max_jsonish_depth


def _safe_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    safe = _safe_jsonish(value)
    if not isinstance(safe, dict):
        raise TypeError("diagnostic mapping could not be coerced")
    return safe


def _safe_jsonish(value: Any, *, depth: int = 0) -> Any:
    if depth >= _MAX_DEPTH:
        return "<max-depth>"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:_MAX_SAFE_STRING_CHARS]
    if isinstance(value, Mapping):
        return _safe_jsonish_mapping(value, depth=depth)
    if isinstance(value, (list, tuple)):
        return _safe_jsonish_sequence(value, depth=depth)
    if isinstance(value, (set, frozenset)):
        return _safe_jsonish_set(value, depth=depth)
    return _safe_jsonish_default(value)


def _safe_jsonish_mapping(value: Mapping[Any, Any], *, depth: int) -> dict[str, Any]:
    child_depth = depth + 1
    if type(value) is dict:
        value_count = len(value)
        if value_count == 0:
            return {}
        if value_count == 1:
            for key in value:
                return {str(key)[:80]: _safe_jsonish(value[key], depth=child_depth)}
        if value_count == 2:
            key_iter = iter(value)
            first_key = next(key_iter)
            second_key = next(key_iter)
            return {
                str(first_key)[:80]: _safe_jsonish(value[first_key], depth=child_depth),
                str(second_key)[:80]: _safe_jsonish(value[second_key], depth=child_depth),
            }
        if value_count == 3:
            key_iter = iter(value)
            first_key = next(key_iter)
            second_key = next(key_iter)
            third_key = next(key_iter)
            return {
                str(first_key)[:80]: _safe_jsonish(value[first_key], depth=child_depth),
                str(second_key)[:80]: _safe_jsonish(value[second_key], depth=child_depth),
                str(third_key)[:80]: _safe_jsonish(value[third_key], depth=child_depth),
            }
        if value_count == 4:
            key_iter = iter(value)
            first_key = next(key_iter)
            second_key = next(key_iter)
            third_key = next(key_iter)
            fourth_key = next(key_iter)
            return {
                str(first_key)[:80]: _safe_jsonish(value[first_key], depth=child_depth),
                str(second_key)[:80]: _safe_jsonish(value[second_key], depth=child_depth),
                str(third_key)[:80]: _safe_jsonish(value[third_key], depth=child_depth),
                str(fourth_key)[:80]: _safe_jsonish(value[fourth_key], depth=child_depth),
            }
    safe: dict[str, Any] = {}
    for key in islice(value, _MAX_DICT_ITEMS):
        _set_safe_jsonish_mapping_value(safe, key, value[key], depth=child_depth)
    return safe


def _set_safe_jsonish_mapping_value(
    safe: dict[str, Any], key: Any, child: Any, *, depth: int
) -> None:
    safe[str(key)[:80]] = _safe_jsonish(child, depth=depth)


def _safe_jsonish_sequence(value: list[Any] | tuple[Any, ...], *, depth: int) -> list[Any]:
    child_depth = depth + 1
    value_count = len(value)
    if value_count == 0:
        return []
    if value_count == 1:
        return [_safe_jsonish(value[0], depth=child_depth)]
    if value_count == 2:
        return [
            _safe_jsonish(value[0], depth=child_depth),
            _safe_jsonish(value[1], depth=child_depth),
        ]
    if value_count == 3:
        return [
            _safe_jsonish(value[0], depth=child_depth),
            _safe_jsonish(value[1], depth=child_depth),
            _safe_jsonish(value[2], depth=child_depth),
        ]
    if value_count == 4:
        return [
            _safe_jsonish(value[0], depth=child_depth),
            _safe_jsonish(value[1], depth=child_depth),
            _safe_jsonish(value[2], depth=child_depth),
            _safe_jsonish(value[3], depth=child_depth),
        ]
    safe_items: list[Any] = []
    for item in islice(value, _MAX_LIST_ITEMS):
        _append_safe_jsonish_item(safe_items, item, depth=child_depth)
    return safe_items


def _append_safe_jsonish_item(safe_items: list[Any], item: Any, *, depth: int) -> None:
    safe_items.append(_safe_jsonish(item, depth=depth))


def _safe_jsonish_set(value: set[Any] | frozenset[Any], *, depth: int) -> list[Any]:
    child_depth = depth + 1
    safe_items: list[Any] = []
    for item in islice(value, _MAX_LIST_ITEMS):
        _append_safe_jsonish_item(safe_items, item, depth=child_depth)
    return safe_items


def _safe_jsonish_default(value: Any) -> str:
    return repr(value)[:_MAX_SAFE_STRING_CHARS]
