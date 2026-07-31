"""ConfigStore domain value normalization helpers."""

from __future__ import annotations

from typing import Any


def provider_option_name(name: str) -> str:
    """Normalize provider names to their config option key."""
    return name.lower()


def configured_value(value: str | None) -> str | None:
    """Return configured text values, treating empty strings as absent."""
    return value or None


def cache_ttl_hours(value: str | None, *, default: int) -> int:
    """Return a cache TTL in hours, falling back on missing or invalid values."""
    if value is not None:
        try:
            return int(value)
        except ValueError:
            return default
    return default


def append_provider_key(keys: dict[str, str], section: object, name: str) -> None:
    """Append one provider key from a config section proxy."""
    keys[name] = section[name]  # type: ignore[index]


def provider_keys_from_config(
    cfg: Any,
    *,
    providers_section: str,
) -> dict[str, str]:
    """Return all provider keys from a config parser without copying section proxies."""
    if providers_section not in cfg:
        return {}
    section = cfg[providers_section]
    key_count = len(section)
    if key_count == 0:
        return {}
    if key_count == 1:
        for name in section:
            return {name: section[name]}
    if key_count == 2:
        key_iter = iter(section)
        first = next(key_iter)
        second = next(key_iter)
        return {first: section[first], second: section[second]}
    if key_count == 3:
        key_iter = iter(section)
        first = next(key_iter)
        second = next(key_iter)
        third = next(key_iter)
        return {
            first: section[first],
            second: section[second],
            third: section[third],
        }
    if key_count == 4:
        key_iter = iter(section)
        first = next(key_iter)
        second = next(key_iter)
        third = next(key_iter)
        fourth = next(key_iter)
        return {
            first: section[first],
            second: section[second],
            third: section[third],
            fourth: section[fourth],
        }

    keys: dict[str, str] = {}
    for name in section:
        append_provider_key(keys, section, name)
    return keys
