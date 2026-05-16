"""Shared UTC clock helpers."""
from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(tz=timezone.utc)


def utc_iso(timestamp: datetime | None = None) -> str:
    """Return an ISO-8601 UTC timestamp using the app's Zulu convention."""
    value = utc_now() if timestamp is None else timestamp.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def utc_iso_seconds(timestamp: datetime | None = None) -> str:
    """Return a Zulu UTC timestamp rounded down to whole seconds."""
    value = utc_now() if timestamp is None else timestamp.astimezone(timezone.utc)
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_timestamp_slug(timestamp: datetime | None = None) -> str:
    """Return a filesystem-safe UTC timestamp slug."""
    value = utc_now() if timestamp is None else timestamp.astimezone(timezone.utc)
    return value.replace(microsecond=0).strftime("%Y%m%dT%H%M%SZ")


def utc_display_seconds(timestamp: datetime | None = None) -> str:
    """Return a human-readable UTC timestamp at whole-second precision."""
    value = utc_now() if timestamp is None else timestamp.astimezone(timezone.utc)
    return value.replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC")


def utcnow_iso() -> str:
    """Return the current UTC timestamp using the app's Zulu convention."""
    return utc_iso()
