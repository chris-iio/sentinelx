"""Shared abuse.ch response parsing helpers."""
from __future__ import annotations


def abusech_query_status(body: dict) -> str:
    """Return the abuse.ch query_status value using the provider fallback."""
    return body.get("query_status", "")


def abusech_data_records(
    body: dict,
    *,
    no_data_status: str,
) -> list[dict] | None:
    """Return abuse.ch data records, or None when the response has no usable hits."""
    if abusech_query_status(body) == no_data_status:
        return None

    raw_data = body.get("data")
    data = raw_data if isinstance(raw_data, list) else []
    if not data:
        return None
    return data
