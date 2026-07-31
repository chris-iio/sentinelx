"""Local analyst review package: scoped IOC decisions and review memory.

The provider verdict says what the threat-intel sources claim; the review
axis records what the analyst decided about it in one required scope.

Records can contain verbatim IOC values and analyst reasons. Do not send them
to an external model without explicit redaction and analyst consent.
"""
from __future__ import annotations

from .memory import DECIDED, annotate, memory_context, summarize
from .store import (
    DEFAULT_DB_PATH,
    DISPOSITIONS,
    LEGACY_SCOPE,
    ReviewStore,
    normalize_key,
)

__all__ = (
    "DECIDED",
    "DEFAULT_DB_PATH",
    "DISPOSITIONS",
    "LEGACY_SCOPE",
    "ReviewStore",
    "annotate",
    "memory_context",
    "normalize_key",
    "summarize",
)
