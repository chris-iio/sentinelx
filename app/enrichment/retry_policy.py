"""Retry/backoff policy helpers for enrichment lookups."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .models import EnrichmentError

BACKOFF_BASE = 15
BACKOFF_MULTIPLIER = 2
BACKOFF_JITTER = 2.0
MAX_RATE_LIMIT_RETRIES = 2
NON_RATE_LIMIT_RETRY_DELAY = 1


def rate_limit_backoff_delay(
    attempt: int,
    jitter: Callable[[float, float], float],
) -> float:
    """Return exponential 429 backoff delay for a retry attempt."""
    return (
        BACKOFF_BASE * (BACKOFF_MULTIPLIER ** (attempt - 1))
        + jitter(0, BACKOFF_JITTER)
    )


def is_rate_limit_error(result: Any) -> bool:
    """Return True if *result* is a rate-limit enrichment error."""
    if not isinstance(result, EnrichmentError):
        return False
    err = result.error.lower()
    return "429" in err or "rate limit" in err
