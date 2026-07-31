"""CTF workspace package: events, challenges, notes, and flag vault.

Extends the SentinelX analyst loop for CTF events (e.g. HackTheBox Cyber
Apocalypse): track challenges per event, keep per-challenge notes, and
capture flags detected in pasted text into a local vault.
"""
from __future__ import annotations

from .flags import detect_flags
from .store import (
    CATEGORIES,
    DIFFICULTIES,
    STATUSES,
    CtfStore,
)

__all__ = (
    "CATEGORIES",
    "DIFFICULTIES",
    "STATUSES",
    "CtfStore",
    "detect_flags",
)
