"""Scoped, local read models for analyst review decisions.

These helpers do not transmit data. Their output can contain verbatim IOC
values and analyst reasons. Keep it local by default. Do not send it to an
external model without explicit redaction and analyst consent.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.time_utils import utc_now

from .store import DISPOSITIONS, normalize_key

__all__ = ("DECIDED", "annotate", "memory_context", "summarize")

DECIDED = tuple(disposition for disposition in DISPOSITIONS if disposition != "unreviewed")

_SECTIONS = (
    ("false_positive", "Known false positives"),
    ("confirmed", "Confirmed indicators"),
    ("acknowledged", "Acknowledged indicators"),
)


def _parse_timestamp(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _active_in_scope(record: dict, scope: str, as_of: datetime) -> bool:
    expires_at = record.get("expires_at")
    if record.get("scope", "").strip() != scope:
        return False
    if not expires_at:
        return True
    expiry = _parse_timestamp(expires_at)
    return expiry is not None and expiry > as_of


def _as_of(timestamp: datetime | None) -> datetime:
    if timestamp is None:
        return utc_now()
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def summarize(
    records: list[dict], *, scope: str, as_of: datetime | None = None
) -> dict:
    """Count active records in one required scope.

    This helper is local only. Do not send verbatim record data to an external
    model without explicit redaction and analyst consent.
    """
    normalized_scope = scope.strip()
    counts = {disposition: 0 for disposition in DISPOSITIONS}
    if not normalized_scope:
        return {**counts, "total": 0}
    timestamp = _as_of(as_of)
    for record in records:
        if not _active_in_scope(record, normalized_scope, timestamp):
            continue
        disposition = record.get("disposition")
        if disposition in counts:
            counts[disposition] += 1
    counts["total"] = sum(counts.values())
    return counts


def _line(record: dict) -> str:
    label = f"{record['ioc_type']}:{record['value']}"
    detail = record.get("reason") or record.get("note")
    return f"- {label} — {detail}" if detail else f"- {label}"


def memory_context(
    records: list[dict],
    *,
    scope: str,
    max_entries: int = 20,
    as_of: datetime | None = None,
) -> str:
    """Render active decisions from one required scope for local reuse.

    The result contains verbatim IOC values and reasons. Do not send it to an
    external model without explicit redaction and analyst consent.
    """
    normalized_scope = scope.strip()
    if not normalized_scope:
        return ""
    timestamp = _as_of(as_of)
    decided = [
        record
        for record in records
        if record.get("disposition") in DECIDED
        and _active_in_scope(record, normalized_scope, timestamp)
    ]
    decided.sort(key=lambda record: record.get("updated_at", ""), reverse=True)
    lines: list[str] = []
    budget = max(max_entries, 0)
    for disposition, heading in _SECTIONS:
        group = [record for record in decided if record["disposition"] == disposition]
        shown = group[:budget]
        if not shown:
            continue
        budget -= len(shown)
        lines.append(f"## {heading}")
        lines.extend(_line(record) for record in shown)
    if not lines:
        return ""
    return "\n".join(
        [f"# Analyst review memory for scope: {normalized_scope}", "", *lines]
    )


def annotate(
    items: list[dict],
    records: list[dict],
    *,
    scope: str,
    as_of: datetime | None = None,
) -> list[dict]:
    """Attach active reviews from one required scope to IOC rows.

    Inputs are not mutated. The annotation can contain verbatim IOC reasons.
    Do not send it to an external model without explicit redaction and analyst
    consent.
    """
    normalized_scope = scope.strip()
    if not normalized_scope:
        return list(items)
    timestamp = _as_of(as_of)
    index = {
        normalize_key(
            normalized_scope,
            str(record["ioc_type"]),
            str(record["value"]),
        )[1:]: record
        for record in records
        if record.get("disposition") in DECIDED
        and _active_in_scope(record, normalized_scope, timestamp)
    }
    annotated: list[dict] = []
    for item in items:
        key = normalize_key(
            normalized_scope,
            str(item.get("type", "")),
            str(item.get("value", "")),
        )[1:]
        record = index.get(key)
        if record is None:
            annotated.append(item)
            continue
        merged = dict(item)
        merged["review"] = {
            "scope": normalized_scope,
            "disposition": record["disposition"],
            "reason": record["reason"],
            "note": record["note"],
            "author": record.get("author", ""),
            "source": record.get("source", ""),
            "expires_at": record.get("expires_at"),
            "updated_at": record["updated_at"],
        }
        annotated.append(merged)
    return annotated
