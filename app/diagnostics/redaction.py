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

REDACTED_TEXT = "[REDACTED]"
CIRCULAR_TEXT = "[Circular]"
MAX_DEPTH_TEXT = "[MaxDepth]"
MIN_CONFIGURED_SECRET_CHARS = 8
DEFAULT_MAX_REDACTION_DEPTH = 20


class ConfigSecretStore(Protocol):
    """Minimal ConfigStore surface needed for diagnostic redaction."""

    def get_vt_api_key(self) -> str | None: ...

    def all_provider_keys(self) -> dict[str, str]: ...


@dataclass(frozen=True)
class ConfiguredSecretInventory:
    """Safe ConfigStore secret inventory metadata.

    This public helper result intentionally contains labels only.  Raw secret
    values are retained only in private in-process redaction candidates and are
    never exposed through metadata or package exports.
    """

    secret_labels: tuple[str, ...] = field(default_factory=tuple)
    provider_labels: tuple[str, ...] = field(default_factory=tuple)
    config_error: str | None = None


@dataclass(frozen=True)
class RedactionMetadata:
    """Secret-free metadata describing redaction work performed."""

    redaction_count: int
    redaction_labels: tuple[str, ...]
    config_error: str | None = None


@dataclass(frozen=True)
class _SecretCandidate:
    """Internal exact-match redaction candidate.

    The raw value is excluded from repr/str as a defense-in-depth measure, even
    though this class is private and never returned from public helpers.
    """

    label: str
    value: str = field(repr=False, compare=False)


@dataclass(frozen=True)
class _SecretCollection:
    candidates: tuple[_SecretCandidate, ...]
    inventory: ConfiguredSecretInventory


@dataclass
class _RedactionAccumulator:
    count: int = 0
    labels: set[str] = field(default_factory=set)
    config_error: str | None = None

    def add(self, label: str, count: int = 1) -> None:
        if count <= 0:
            return
        self.count += count
        self.labels.add(label)

    def note(self, label: str) -> None:
        self.labels.add(label)

    def metadata(self) -> RedactionMetadata:
        return RedactionMetadata(
            redaction_count=self.count,
            redaction_labels=tuple(sorted(self.labels)),
            config_error=self.config_error,
        )


@dataclass(frozen=True)
class _TextRule:
    label: str
    regex: re.Pattern[str]
    replace: Any


_QUERY_NAMES = ("api_key", "apikey", "token", "secret")
_FIELD_NAMES = frozenset(_QUERY_NAMES)
_AUTH_HEADER_KEYS = frozenset({"authorization", "x-api-key", "auth-key", "key"})


def _normalize_label_part(value: object) -> str:
    """Return a bounded label component without secret-bearing punctuation."""
    if not isinstance(value, str):
        value = str(value)
    label = re.sub(r"[^a-z0-9_.-]+", "_", value.strip().lower()).strip("_")
    return label[:64] or "unknown"


def _is_usable_configured_secret(value: object) -> bool:
    return isinstance(value, str) and len(value.strip()) >= MIN_CONFIGURED_SECRET_CHARS


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
    if _is_usable_configured_secret(vt_key):
        candidates.append(_SecretCandidate(label="configured_secret:virustotal", value=vt_key.strip()))

    provider_labels: list[str] = []
    for raw_provider_name, raw_secret in sorted(provider_keys.items(), key=lambda item: item[0]):
        provider_label = _normalize_label_part(raw_provider_name)
        if _is_usable_configured_secret(raw_secret):
            provider_labels.append(provider_label)
            candidates.append(
                _SecretCandidate(
                    label=f"configured_secret:provider:{provider_label}",
                    value=raw_secret.strip(),
                )
            )

    secret_labels = tuple(sorted(candidate.label for candidate in candidates))
    return _SecretCollection(
        candidates=tuple(candidates),
        inventory=ConfiguredSecretInventory(
            secret_labels=secret_labels,
            provider_labels=tuple(sorted(set(provider_labels))),
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
    for secret in sorted(candidates, key=lambda item: len(item.value), reverse=True):
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
        stripped = value.strip()
        if not stripped:
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
    if isinstance(value, (dict, list, tuple)):
        if value_id in seen:
            return CIRCULAR_TEXT
        seen.add(value_id)
        try:
            if isinstance(value, dict):
                redacted_dict: dict[object, object] = {}
                for raw_key, raw_child in value.items():
                    redacted_key = _safe_key(raw_key, candidates, acc)
                    key_for_rules = raw_key.lower().strip() if isinstance(raw_key, str) else ""
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

            return [
                _redact_payload_value(child, candidates, acc, depth=depth - 1, seen=seen)
                for child in value
            ]
        finally:
            seen.remove(value_id)

    return f"[Unserializable:{type(value).__name__}]"


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
