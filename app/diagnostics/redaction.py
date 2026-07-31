"""Backend-only diagnostic redaction primitives.

The functions in this module are intentionally independent of Flask request/app
context.  They are designed to run before diagnostic payload serialization so
future bundle assembly can redact configured provider credentials and common auth
material while keeping safe diagnostic context such as IOCs, provider names,
verdicts, counts, and timestamps.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .policy import DIAGNOSTIC_SANITIZATION_POLICY
from .payload_redaction import (
    redact_payload_value,
)
from .secret_inventory import (
    _SecretCollection,
    _collect_configured_secret_candidates,
)
from .text_rules import (
    apply_exact_secret_redaction,
    redact_text_with_candidates,
)

DEFAULT_MAX_REDACTION_DEPTH = DIAGNOSTIC_SANITIZATION_POLICY.max_redaction_depth

__all__ = (
    "DEFAULT_MAX_REDACTION_DEPTH",
    "RedactionMetadata",
    "redact_diagnostic_payload",
    "redact_diagnostic_text",
)

if TYPE_CHECKING:
    from .secret_inventory import ConfigSecretStore


@dataclass(frozen=True, slots=True)
class RedactionMetadata:
    """Secret-free metadata describing redaction work performed."""

    redaction_count: int
    redaction_labels: tuple[str, ...]
    config_error: str | None = None


def _ordered_redaction_label_snapshot(labels: set[str]) -> tuple[str, ...]:
    label_count = len(labels)
    if label_count == 0:
        return ()
    if label_count == 1:
        return (next(iter(labels)),)
    if label_count == 2:
        label_iter = iter(labels)
        first = next(label_iter)
        second = next(label_iter)
        if first <= second:
            return (first, second)
        return (second, first)
    if label_count == 3:
        label_iter = iter(labels)
        first = next(label_iter)
        second = next(label_iter)
        third = next(label_iter)
        if first > second:
            first, second = second, first
        if second > third:
            second, third = third, second
        if first > second:
            first, second = second, first
        return (first, second, third)
    if label_count == 4:
        label_iter = iter(labels)
        first = next(label_iter)
        second = next(label_iter)
        third = next(label_iter)
        fourth = next(label_iter)
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
        append_ordered_redaction_label(ordered, label)
    return tuple(ordered)


def append_ordered_redaction_label(ordered: list[str], label: str) -> None:
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


@dataclass(slots=True)
class _RedactionAccumulator:
    count: int = 0
    labels: set[str] = field(default_factory=set)
    config_error: str | None = None
    _label_snapshot: tuple[str, ...] = field(default_factory=tuple, init=False)
    _labels_dirty: bool = field(default=True, init=False)

    def _remember_label(self, label: str) -> None:
        if label not in self.labels:
            self.labels.add(label)
            self._labels_dirty = True

    def add(self, label: str, count: int = 1) -> None:
        if count <= 0:
            return
        self.count += count
        self._remember_label(label)

    def note(self, label: str) -> None:
        self._remember_label(label)

    def metadata(self) -> RedactionMetadata:
        if self._labels_dirty:
            self._label_snapshot = _ordered_redaction_label_snapshot(self.labels)
            self._labels_dirty = False
        return RedactionMetadata(
            redaction_count=self.count,
            redaction_labels=self._label_snapshot,
            config_error=self.config_error,
        )


def _prepare_redaction(
    config_store: ConfigSecretStore | None,
) -> tuple[_SecretCollection, _RedactionAccumulator]:
    collection = _collect_configured_secret_candidates(config_store)
    acc = _RedactionAccumulator(config_error=collection.inventory.config_error)
    if collection.inventory.config_error is not None:
        acc.note("config:read_failed")
    return collection, acc


def redact_diagnostic_text(
    text: object,
    *,
    config_store: ConfigSecretStore | None = None,
) -> tuple[str, RedactionMetadata]:
    """Redact configured secrets and common auth patterns from plain text."""
    collection, acc = _prepare_redaction(config_store)
    redacted = redact_text_with_candidates(str(text), collection.candidates, acc)
    return redacted, acc.metadata()


def redact_diagnostic_payload(
    payload: object,
    *,
    config_store: ConfigSecretStore | None = None,
    max_depth: int = DEFAULT_MAX_REDACTION_DEPTH,
) -> tuple[object, RedactionMetadata]:
    """Return a redacted JSON-like payload and secret-free metadata.

    The caller-owned input object is not mutated.  Dicts/lists/tuples are copied
    during traversal, cycles are replaced with ``[Circular]``, and unsupported
    object instances are represented by type name only so arbitrary repr strings
    cannot leak credentials.
    """
    collection, acc = _prepare_redaction(config_store)
    redacted = redact_payload_value(
        payload,
        collection.candidates,
        acc,
        depth=max_depth,
        seen=set(),
        text_redactor=redact_text_with_candidates,
        exact_secret_redactor=apply_exact_secret_redaction,
    )
    return redacted, acc.metadata()
