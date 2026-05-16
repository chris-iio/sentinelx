"""Backend-only diagnostic redaction primitives.

The functions in this module are intentionally independent of Flask request/app
context.  They are designed to run before diagnostic payload serialization so
future bundle assembly can redact configured provider credentials and common auth
material while keeping safe diagnostic context such as IOCs, provider names,
verdicts, counts, and timestamps.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.enrichment.config_store import ConfigStore
from app.diagnostics.policy import DIAGNOSTIC_SANITIZATION_POLICY
from app.text_utils import stripped_text_or_none

REDACTED_TEXT = "[REDACTED]"
CIRCULAR_TEXT = "[Circular]"
MAX_DEPTH_TEXT = "[MaxDepth]"
MIN_CONFIGURED_SECRET_CHARS = 8
DEFAULT_MAX_REDACTION_DEPTH = DIAGNOSTIC_SANITIZATION_POLICY.max_redaction_depth


class ConfigSecretStore(Protocol):
    """Minimal ConfigStore surface needed for diagnostic redaction."""

    def get_vt_api_key(self) -> str | None: ...

    def all_provider_keys(self) -> dict[str, str]: ...


@dataclass(frozen=True, slots=True)
class ConfiguredSecretInventory:
    """Safe ConfigStore secret inventory metadata.

    This public helper result intentionally contains labels only.  Raw secret
    values are retained only in private in-process redaction candidates and are
    never exposed through metadata or package exports.
    """

    secret_labels: tuple[str, ...] = field(default_factory=tuple)
    provider_labels: tuple[str, ...] = field(default_factory=tuple)
    config_error: str | None = None


@dataclass(frozen=True, slots=True)
class RedactionMetadata:
    """Secret-free metadata describing redaction work performed."""

    redaction_count: int
    redaction_labels: tuple[str, ...]
    config_error: str | None = None


@dataclass(frozen=True, slots=True)
class _SecretCandidate:
    """Internal exact-match redaction candidate.

    The raw value is excluded from repr/str as a defense-in-depth measure, even
    though this class is private and never returned from public helpers.
    """

    label: str
    value: str = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class _SecretCollection:
    candidates: tuple[_SecretCandidate, ...]
    inventory: ConfiguredSecretInventory


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
            label_count = len(self.labels)
            if label_count == 0:
                self._label_snapshot = ()
            elif label_count == 1:
                self._label_snapshot = (next(iter(self.labels)),)
            else:
                self._label_snapshot = tuple(sorted(self.labels))
            self._labels_dirty = False
        return RedactionMetadata(
            redaction_count=self.count,
            redaction_labels=self._label_snapshot,
            config_error=self.config_error,
        )


@dataclass(frozen=True, slots=True)
class _TextRule:
    label: str
    regex: re.Pattern[str]
    replace: Any


_QUERY_NAMES = ("api_key", "apikey", "token", "secret")
_FIELD_NAMES = frozenset(_QUERY_NAMES)
_AUTH_HEADER_KEYS = frozenset(("authorization", "x-api-key", "auth-key", "key"))
_PAYLOAD_SEQUENCE_TYPES = (list, tuple)
_PAYLOAD_CONTAINER_TYPES = (dict, list, tuple)
_LABEL_PART_RE = re.compile(r"[^a-z0-9_.-]+")


def _normalize_label_part(value: object) -> str:
    """Return a bounded label component without secret-bearing punctuation."""
    if not isinstance(value, str):
        value = str(value)
    stripped = stripped_text_or_none(value)
    label = _trim_label_underscores(_LABEL_PART_RE.sub("_", stripped.lower() if stripped is not None else ""))
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
    return tuple(sorted(keys))


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
        return (first, second, third)
    return tuple(sorted(labels))


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
    candidates.sort(key=lambda item: len(item.value), reverse=True)
    return tuple(candidates)


def _collect_configured_secret_candidates(
    config_store: ConfigSecretStore | None = None,
) -> _SecretCollection:
    """Read ConfigStore once and return internal candidates plus safe inventory."""
    store = config_store if config_store is not None else ConfigStore()

    try:
        vt_key = store.get_vt_api_key()
        provider_keys = store.all_provider_keys()
    except Exception:
        return _SecretCollection(
            candidates=(),
            inventory=ConfiguredSecretInventory(config_error="config_read_failed"),
        )

    candidates: list[_SecretCandidate] = []
    vt_secret = _usable_configured_secret(vt_key)
    if vt_secret is not None:
        candidates.append(_SecretCandidate(label="configured_secret:virustotal", value=vt_secret))

    provider_labels: dict[str, None] = {}
    for raw_provider_name in _stable_keys(provider_keys):
        raw_secret = provider_keys[raw_provider_name]
        provider_label = _normalize_label_part(raw_provider_name)
        provider_secret = _usable_configured_secret(raw_secret)
        if provider_secret is not None:
            provider_labels[provider_label] = None
            candidates.append(
                _SecretCandidate(
                    label=f"configured_secret:provider:{provider_label}",
                    value=provider_secret,
                )
            )

    ordered_candidates = _stable_secret_candidates(candidates)
    secret_labels_list: list[str] = []
    for candidate in ordered_candidates:
        secret_labels_list.append(candidate.label)
    secret_labels = _stable_label_tuple(secret_labels_list)
    return _SecretCollection(
        candidates=ordered_candidates,
        inventory=ConfiguredSecretInventory(
            secret_labels=secret_labels,
            provider_labels=_stable_label_tuple(provider_labels),
        ),
    )


def collect_configured_secret_inventory(
    config_store: ConfigSecretStore | None = None,
) -> ConfiguredSecretInventory:
    """Return secret-free ConfigStore inventory labels for diagnostics.

    The helper reads ``ConfigStore.get_vt_api_key()`` and
    ``ConfigStore.all_provider_keys()`` to determine which configured values are
    long enough for exact redaction.  It exposes only safe labels/provider names,
    never raw configured values, suffixes, or fragments.
    """
    return _collect_configured_secret_candidates(config_store).inventory


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
    *(
        _TextRule(
            label=f"pattern:query:{name}",
            regex=re.compile(
                rf"(?P<prefix>(?:[?&;]|\b){name}\s*=\s*)(?P<secret>[^&\s\"'<>]+)",
                re.IGNORECASE,
            ),
            replace=_replace_named_secret,
        )
        for name in _QUERY_NAMES
    ),
    *(
        _TextRule(
            label=f"pattern:field:{name}",
            regex=re.compile(
                rf"(?P<prefix>(?<![A-Za-z0-9_])[\"']?{name}[\"']?\s*:\s*)(?P<quote>[\"']?)(?P<secret>[^\s,}}\]\"']+)(?P=quote)",
                re.IGNORECASE,
            ),
            replace=_replace_jsonish_field,
        )
        for name in _QUERY_NAMES
    ),
)


def _apply_exact_secret_redaction(
    text: str,
    candidates: tuple[_SecretCandidate, ...],
    acc: _RedactionAccumulator,
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


def _apply_pattern_redaction(text: str, acc: _RedactionAccumulator) -> str:
    """Apply common credential pattern redaction to a string."""
    redacted = text

    for rule in _TEXT_RULES:
        replacements = 0

        def _callback(match: re.Match[str]) -> str:
            nonlocal replacements
            secret_value = match.groupdict().get("secret") or ""
            if secret_value == REDACTED_TEXT:
                return match.group(0)
            replacements += 1
            return rule.replace(match)

        redacted = rule.regex.sub(_callback, redacted)
        acc.add(rule.label, replacements)

    return redacted


def _redact_text_with_candidates(
    text: str,
    candidates: tuple[_SecretCandidate, ...],
    acc: _RedactionAccumulator,
) -> str:
    redacted = _apply_exact_secret_redaction(text, candidates, acc)
    return _apply_pattern_redaction(redacted, acc)


def _prepare_redaction(config_store: ConfigSecretStore | None) -> tuple[_SecretCollection, _RedactionAccumulator]:
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
    redacted = _redact_text_with_candidates(str(text), collection.candidates, acc)
    return redacted, acc.metadata()


def _safe_key(
    value: object,
    candidates: tuple[_SecretCandidate, ...],
    acc: _RedactionAccumulator,
) -> object:
    if isinstance(value, str):
        return _redact_text_with_candidates(value, candidates, acc)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return f"[UnserializableKey:{type(value).__name__}]"


def _redact_entire_scalar(
    value: object,
    label: str,
    candidates: tuple[_SecretCandidate, ...],
    acc: _RedactionAccumulator,
) -> object:
    """Redact a scalar value because its field/header name is credential-like."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = stripped_text_or_none(value)
        if stripped is None:
            return value
        _apply_exact_secret_redaction(value, candidates, acc)
        acc.add(label)
        if label == "pattern:authorization_bearer" and stripped.lower().startswith("bearer "):
            return f"Bearer {REDACTED_TEXT}"
        return REDACTED_TEXT
    if isinstance(value, (int, float, bool)):
        return value
    acc.add(label)
    return REDACTED_TEXT


def _redact_payload_value(
    value: object,
    candidates: tuple[_SecretCandidate, ...],
    acc: _RedactionAccumulator,
    *,
    depth: int,
    seen: set[int],
) -> object:
    if depth < 0:
        return MAX_DEPTH_TEXT

    if isinstance(value, str):
        return _redact_text_with_candidates(value, candidates, acc)

    if value is None or isinstance(value, (int, float, bool)):
        return value

    value_id = id(value)
    if isinstance(value, _PAYLOAD_CONTAINER_TYPES):
        if value_id in seen:
            return CIRCULAR_TEXT
        seen.add(value_id)
        try:
            if isinstance(value, dict):
                redacted_dict: dict[object, object] = {}
                for raw_key in value:
                    raw_child = value[raw_key]
                    redacted_key = _safe_key(raw_key, candidates, acc)
                    stripped_key = stripped_text_or_none(raw_key) if isinstance(raw_key, str) else None
                    key_for_rules = stripped_key.lower() if stripped_key is not None else ""
                    if key_for_rules in _FIELD_NAMES:
                        child = _redact_entire_scalar(
                            raw_child,
                            f"pattern:field:{key_for_rules}",
                            candidates,
                            acc,
                        )
                    elif key_for_rules == "authorization":
                        child = _redact_entire_scalar(
                            raw_child,
                            "pattern:authorization_bearer",
                            candidates,
                            acc,
                        )
                    elif key_for_rules in _AUTH_HEADER_KEYS:
                        child = _redact_entire_scalar(
                            raw_child,
                            f"pattern:header:{key_for_rules}",
                            candidates,
                            acc,
                        )
                    else:
                        child = _redact_payload_value(
                            raw_child,
                            candidates,
                            acc,
                            depth=depth - 1,
                            seen=seen,
                        )
                    redacted_dict[redacted_key] = child
                return redacted_dict

            return _redact_payload_sequence(
                value,
                candidates,
                acc,
                depth=depth - 1,
                seen=seen,
            )
        finally:
            seen.remove(value_id)

    return f"[Unserializable:{type(value).__name__}]"


def _redact_payload_sequence(
    value: list[object] | tuple[object, ...],
    candidates: tuple[_SecretCandidate, ...],
    acc: _RedactionAccumulator,
    *,
    depth: int,
    seen: set[int],
) -> list[object]:
    value_count = len(value)
    if value_count == 0:
        return []
    if value_count == 1:
        return [_redact_payload_value(value[0], candidates, acc, depth=depth, seen=seen)]
    if value_count == 2:
        return [
            _redact_payload_value(value[0], candidates, acc, depth=depth, seen=seen),
            _redact_payload_value(value[1], candidates, acc, depth=depth, seen=seen),
        ]

    redacted_items: list[object] = []
    for child in value:
        redacted_items.append(
            _redact_payload_value(child, candidates, acc, depth=depth, seen=seen)
        )
    return redacted_items


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
    redacted = _redact_payload_value(
        payload,
        collection.candidates,
        acc,
        depth=max_depth,
        seen=set(),
    )
    return redacted, acc.metadata()
