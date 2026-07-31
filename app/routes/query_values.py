"""Shared route query-value normalization helpers."""
from __future__ import annotations

from typing import Any

from .enrichment_status import coerce_status_cursor


def status_cursor_from_query(args: Any) -> int:
    """Return the normalized enrichment status cursor from request query args."""
    return coerce_status_cursor(args.get("since", 0, type=int))
