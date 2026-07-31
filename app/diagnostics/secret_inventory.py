"""Configured-secret inventory and exact-redaction candidate ordering."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from .policy import DIAGNOSTIC_SANITIZATION_POLICY
from app.enrichment.config_store import ConfigStore
from app.text_utils import stripped_text_or_none

MIN_CONFIGURED_SECRET_CHARS = 8


class ConfigSecretStore(Protocol):
    """Minimal ConfigStore surface needed for diagnostic redaction."""

    def get_vt_api_key(self) -> str | None: ...

    def all_provider_keys(self) -> dict[str, str]: ...


@dataclass(frozen=True, slots=True)
class ConfiguredSecretInventory:
    """Safe ConfigStore secret inventory metadata."""

    secret_labels: tuple[str, ...] = field(default_factory=tuple)
    provider_labels: tuple[str, ...] = field(default_factory=tuple)
    config_error: str | None = None


@dataclass(frozen=True, slots=True)
class _SecretCandidate:
    """Internal exact-match redaction candidate."""

    label: str
    value: str = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class _SecretCollection:
    candidates: tuple[_SecretCandidate, ...]
    inventory: ConfiguredSecretInventory


_LABEL_PART_RE = re.compile(r"[^a-z0-9_.-]+")


def _normalize_label_part(value: object) -> str:
    """Return a bounded label component without secret-bearing punctuation."""
    if not isinstance(value, str):
        value = str(value)
    stripped = stripped_text_or_none(value)
    label = _trim_label_underscores(
        _LABEL_PART_RE.sub("_", stripped.lower() if stripped is not None else "")
    )
    return label[:DIAGNOSTIC_SANITIZATION_POLICY.max_redaction_label_chars] or "unknown"


def _trim_label_underscores(value: str) -> str:
    start = 0
    end = len(value)
    while start < end and value[start] == "_":
        start += 1
    while end > start and value[end - 1] == "_":
        end -= 1
    return value[start:end]


def _usable_configured_secret(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = stripped_text_or_none(value)
    if stripped is None or len(stripped) < MIN_CONFIGURED_SECRET_CHARS:
        return None
    return stripped


def _stable_keys(keys: dict[str, str]) -> tuple[str, ...]:
    key_count = len(keys)
    if key_count == 0:
        return ()
    if key_count == 1:
        for key in keys:
            return (key,)
    if key_count == 2:
        iterator = iter(keys)
        first = next(iterator)
        second = next(iterator)
        if first <= second:
            return (first, second)
        return (second, first)
    if key_count == 3:
        iterator = iter(keys)
        first = next(iterator)
        second = next(iterator)
        third = next(iterator)
        if first > second:
            first, second = second, first
        if second > third:
            second, third = third, second
            if first > second:
                first, second = second, first
        return (first, second, third)
    if key_count == 4:
        iterator = iter(keys)
        first = next(iterator)
        second = next(iterator)
        third = next(iterator)
        fourth = next(iterator)
        if first > second:
            first, second = second, first
        if third > fourth:
            third, fourth = fourth, third
        if first > third:
            first, third = third, first
        if second > fourth:
            second, fourth = fourth, second
        if second > third:
            second, third = third, second
        return (first, second, third, fourth)
    ordered: list[str] = []
    for key in keys:
        append_ordered_label(ordered, key)
    return tuple(ordered)


def _stable_label_tuple(labels: list[str] | dict[str, None]) -> tuple[str, ...]:
    label_count = len(labels)
    if label_count == 0:
        return ()
    if label_count == 1:
        for label in labels:
            return (label,)
    if label_count == 2:
        iterator = iter(labels)
        first = next(iterator)
        second = next(iterator)
        if first <= second:
            return (first, second)
        return (second, first)
    if label_count == 3:
        iterator = iter(labels)
        first = next(iterator)
        second = next(iterator)
        third = next(iterator)
        if first > second:
            first, second = second, first
        if second > third:
            second, third = third, second
            if first > second:
                first, second = second, first
        if first == second:
            if second == third:
                return (first,)
            return (first, third)
        if second == third:
            return (first, second)
        return (first, second, third)
    if label_count == 4:
        iterator = iter(labels)
        first = next(iterator)
        second = next(iterator)
        third = next(iterator)
        fourth = next(iterator)
        if first > second:
            first, second = second, first
        if third > fourth:
            third, fourth = fourth, third
        if first > third:
            first, third = third, first
        if second > fourth:
            second, fourth = fourth, second
        if second > third:
            second, third = third, second
        return (first, second, third, fourth)
    ordered: list[str] = []
    for label in labels:
        append_ordered_label(ordered, label)
    return tuple(ordered)


def append_ordered_label(ordered: list[str], label: str) -> None:
    label_count = len(ordered)
    if label_count == 0:
        ordered.append(label)
        return

    index = 0
    while index < label_count:
        if label <= ordered[index]:
            ordered.insert(index, label)
            return
        index += 1

    ordered.append(label)


def _stable_secret_candidates(
    candidates: list[_SecretCandidate],
) -> tuple[_SecretCandidate, ...]:
    candidate_count = len(candidates)
    if candidate_count == 0:
        return ()
    if candidate_count == 1:
        return (candidates[0],)
    if candidate_count == 2:
        first = candidates[0]
        second = candidates[1]
        if len(first.value) < len(second.value):
            return (second, first)
        return (first, second)
    if candidate_count == 3:
        first = candidates[0]
        second = candidates[1]
        third = candidates[2]
        if len(first.value) < len(second.value):
            first, second = second, first
        if len(second.value) < len(third.value):
            second, third = third, second
            if len(first.value) < len(second.value):
                first, second = second, first
        return (first, second, third)
    if candidate_count == 4:
        first = candidates[0]
        second = candidates[1]
        third = candidates[2]
        fourth = candidates[3]
        if len(first.value) < len(second.value):
            first, second = second, first
        if len(third.value) < len(fourth.value):
            third, fourth = fourth, third
        if len(first.value) < len(third.value):
            first, third = third, first
        if len(second.value) < len(fourth.value):
            second, fourth = fourth, second
        if len(second.value) < len(third.value):
            second, third = third, second
        return (first, second, third, fourth)
    ordered: list[_SecretCandidate] = []
    for candidate in candidates:
        append_longest_first_candidate(ordered, candidate)
    return tuple(ordered)


def append_longest_first_candidate(
    ordered: list[_SecretCandidate],
    candidate: _SecretCandidate,
) -> None:
    candidate_count = len(ordered)
    if candidate_count == 0:
        ordered.append(candidate)
        return

    candidate_length = len(candidate.value)
    index = 0
    while index < candidate_count:
        if candidate_length > len(ordered[index].value):
            ordered.insert(index, candidate)
            return
        index += 1

    ordered.append(candidate)


def _append_configured_secret_candidate(
    candidates: list[_SecretCandidate],
    *,
    label: str,
    raw_secret: object,
) -> bool:
    secret = _usable_configured_secret(raw_secret)
    if secret is None:
        return False
    candidates.append(_SecretCandidate(label=label, value=secret))
    return True


def _collect_configured_secret_candidates(
    config_store: ConfigSecretStore | None = None,
    *,
    config_store_factory: Callable[[], ConfigSecretStore] = ConfigStore,
) -> _SecretCollection:
    """Read ConfigStore once and return internal candidates plus safe inventory."""
    store = config_store if config_store is not None else config_store_factory()

    try:
        vt_key = store.get_vt_api_key()
        provider_keys = store.all_provider_keys()
    except Exception:
        return _SecretCollection(
            candidates=(),
            inventory=ConfiguredSecretInventory(config_error="config_read_failed"),
        )

    candidates: list[_SecretCandidate] = []
    _append_configured_secret_candidate(
        candidates,
        label="configured_secret:virustotal",
        raw_secret=vt_key,
    )

    provider_labels: dict[str, None] = {}
    for raw_provider_name in _stable_keys(provider_keys):
        append_provider_secret_candidate(
            candidates,
            provider_labels,
            raw_provider_name,
            provider_keys[raw_provider_name],
        )

    ordered_candidates = _stable_secret_candidates(candidates)
    return _SecretCollection(
        candidates=ordered_candidates,
        inventory=ConfiguredSecretInventory(
            secret_labels=_candidate_label_tuple(ordered_candidates),
            provider_labels=_stable_label_tuple(provider_labels),
        ),
    )


def append_provider_secret_candidate(
    candidates: list[_SecretCandidate],
    provider_labels: dict[str, None],
    raw_provider_name: str,
    raw_secret: object,
) -> None:
    """Append one provider secret candidate and safe provider label when usable."""
    provider_label = _normalize_label_part(raw_provider_name)
    if _append_configured_secret_candidate(
        candidates,
        label=f"configured_secret:provider:{provider_label}",
        raw_secret=raw_secret,
    ):
        provider_labels[provider_label] = None


def _candidate_label_tuple(candidates: tuple[_SecretCandidate, ...]) -> tuple[str, ...]:
    candidate_count = len(candidates)
    if candidate_count == 0:
        return ()
    if candidate_count == 1:
        return (candidates[0].label,)
    if candidate_count == 2:
        first = candidates[0].label
        second = candidates[1].label
        if first <= second:
            return (first, second)
        return (second, first)
    if candidate_count == 3:
        first = candidates[0].label
        second = candidates[1].label
        third = candidates[2].label
        if first > second:
            first, second = second, first
        if second > third:
            second, third = third, second
            if first > second:
                first, second = second, first
        return (first, second, third)
    if candidate_count == 4:
        first = candidates[0].label
        second = candidates[1].label
        third = candidates[2].label
        fourth = candidates[3].label
        if first > second:
            first, second = second, first
        if third > fourth:
            third, fourth = fourth, third
        if first > third:
            first, third = third, first
        if second > fourth:
            second, fourth = fourth, second
        if second > third:
            second, third = third, second
        return (first, second, third, fourth)

    labels: list[str] = []
    for candidate in candidates:
        append_candidate_label(labels, candidate)
    return _stable_label_tuple(labels)


def append_candidate_label(labels: list[str], candidate: _SecretCandidate) -> None:
    labels.append(candidate.label)


def collect_configured_secret_inventory(
    config_store: ConfigSecretStore | None = None,
    *,
    config_store_factory: Callable[[], ConfigSecretStore] = ConfigStore,
) -> ConfiguredSecretInventory:
    """Return secret-free ConfigStore inventory labels for diagnostics."""
    return _collect_configured_secret_candidates(
        config_store,
        config_store_factory=config_store_factory,
    ).inventory
