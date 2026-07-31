"""Secret-free diagnostics for enrichment history saves."""

from __future__ import annotations

from collections.abc import Mapping
from threading import Lock
from types import MappingProxyType

from app.text_utils import (
    has_non_whitespace,
    stripped_bounded_non_whitespace,
)
from app.time_utils import utcnow_iso

_HISTORY_SAVE_OUTCOMES = frozenset(("never", "saved", "failed", "skipped"))
_HISTORY_SAVE_RECORDABLE_OUTCOMES = frozenset(("saved", "failed", "skipped"))
_HISTORY_SAVE_COUNTER_FIELDS = ("attempts", "successes", "failures", "skipped")
_HISTORY_SAVE_TIMESTAMP_FIELDS = ("last_attempt_at", "last_success_at", "last_failure_at")
_HISTORY_SAVE_DIAGNOSTICS_DEFAULTS = MappingProxyType({
    "attempts": 0,
    "successes": 0,
    "failures": 0,
    "skipped": 0,
    "last_outcome": "never",
    "last_attempt_at": None,
    "last_success_at": None,
    "last_failure_at": None,
    "last_error_summary": None,
})
_history_save_diag_lock = Lock()
_history_save_diagnostics: dict[str, object] = {}


def copy_mapping(source: Mapping[str, object] | None) -> dict[str, object]:
    """Return a shallow dict snapshot without constructor-copying live state."""
    if source is None:
        return {}
    source_count = len(source)
    if source_count == 0:
        return {}
    if source_count == 1:
        for key in source:
            return {key: source[key]}
    if source_count == 2:
        key_iter = iter(source)
        first = next(key_iter)
        second = next(key_iter)
        return {first: source[first], second: source[second]}
    if source_count == 3:
        key_iter = iter(source)
        first = next(key_iter)
        second = next(key_iter)
        third = next(key_iter)
        return {
            first: source[first],
            second: source[second],
            third: source[third],
        }
    if source_count == 4:
        key_iter = iter(source)
        first = next(key_iter)
        second = next(key_iter)
        third = next(key_iter)
        fourth = next(key_iter)
        return {
            first: source[first],
            second: source[second],
            third: source[third],
            fourth: source[fourth],
        }

    snapshot: dict[str, object] = {}
    for key in source:
        append_mapping_value(snapshot, source, key)
    return snapshot


def append_mapping_value(
    snapshot: dict[str, object],
    source: Mapping[str, object],
    key: str,
) -> None:
    snapshot[key] = source[key]


def history_save_diagnostics_defaults() -> dict[str, object]:
    return copy_mapping(_HISTORY_SAVE_DIAGNOSTICS_DEFAULTS)


def _utcnow_iso() -> str:
    """Return the current UTC timestamp in ISO-8601 Zulu form."""
    return utcnow_iso()


def coerce_history_save_diagnostics(raw: object) -> dict[str, object]:
    """Return a safe diagnostics snapshot even if module state is malformed."""
    data = raw if isinstance(raw, dict) else {}
    diagnostics = history_save_diagnostics_defaults()

    coerce_history_save_counter(diagnostics, data, "attempts")
    coerce_history_save_counter(diagnostics, data, "successes")
    coerce_history_save_counter(diagnostics, data, "failures")
    coerce_history_save_counter(diagnostics, data, "skipped")

    outcome = data.get("last_outcome")
    if outcome in _HISTORY_SAVE_OUTCOMES:
        diagnostics["last_outcome"] = outcome

    coerce_history_save_timestamp(diagnostics, data, "last_attempt_at")
    coerce_history_save_timestamp(diagnostics, data, "last_success_at")
    coerce_history_save_timestamp(diagnostics, data, "last_failure_at")

    error_summary = data.get("last_error_summary")
    if isinstance(error_summary, str):
        diagnostics["last_error_summary"] = stripped_bounded_non_whitespace(
            error_summary,
            max_chars=120,
        )

    return diagnostics


def coerce_history_save_counter(
    diagnostics: dict[str, object],
    data: dict[str, object],
    field: str,
) -> None:
    value = data.get(field)
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        diagnostics[field] = value


def coerce_history_save_timestamp(
    diagnostics: dict[str, object],
    data: dict[str, object],
    field: str,
) -> None:
    value = data.get(field)
    if isinstance(value, str) and has_non_whitespace(value):
        diagnostics[field] = value


def replace_history_save_diagnostics(diagnostics: dict[str, object]) -> None:
    """Replace helper-level history diagnostics while preserving dict identity."""
    _history_save_diagnostics.clear()
    _history_save_diagnostics.update(diagnostics)


def reset_history_save_diagnostics() -> None:
    """Reset helper-level history save diagnostics for focused tests."""
    with _history_save_diag_lock:
        replace_history_save_diagnostics(history_save_diagnostics_defaults())


def record_history_save_attempt() -> None:
    """Increment bounded aggregate diagnostics before save_analysis() runs."""
    timestamp = _utcnow_iso()
    with _history_save_diag_lock:
        diagnostics = coerce_history_save_diagnostics(_history_save_diagnostics)
        diagnostics["attempts"] += 1
        diagnostics["last_attempt_at"] = timestamp
        replace_history_save_diagnostics(diagnostics)


def record_history_save_outcome(outcome: str, error: Exception | None = None) -> None:
    """Record the last bounded outcome for helper-owned history persistence."""
    if outcome not in _HISTORY_SAVE_RECORDABLE_OUTCOMES:
        return

    timestamp = _utcnow_iso()
    with _history_save_diag_lock:
        diagnostics = coerce_history_save_diagnostics(_history_save_diagnostics)
        diagnostics["last_outcome"] = outcome
        if outcome == "saved":
            diagnostics["successes"] += 1
            diagnostics["last_success_at"] = timestamp
            diagnostics["last_error_summary"] = None
        elif outcome == "failed":
            diagnostics["failures"] += 1
            diagnostics["last_failure_at"] = timestamp
            diagnostics["last_error_summary"] = (
                f"{error.__class__.__name__} while saving analysis history"
                if error is not None
                else "History save failed"
            )
        else:
            diagnostics["skipped"] += 1
            diagnostics["last_error_summary"] = None

        replace_history_save_diagnostics(diagnostics)


def get_history_save_diagnostics() -> dict[str, object]:
    """Return a safe snapshot of helper-level history save diagnostics."""
    with _history_save_diag_lock:
        snapshot = copy_mapping(_history_save_diagnostics)
    return coerce_history_save_diagnostics(snapshot)


reset_history_save_diagnostics()
