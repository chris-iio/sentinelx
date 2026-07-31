"""Shared analysis mode constants."""

ANALYSIS_MODE_OFFLINE = "offline"
ANALYSIS_MODE_ONLINE = "online"
DEFAULT_ANALYSIS_MODE = ANALYSIS_MODE_OFFLINE
VALID_ANALYSIS_MODES = frozenset((ANALYSIS_MODE_OFFLINE, ANALYSIS_MODE_ONLINE))


def valid_analysis_modes_label() -> str:
    """Return the public label for supported analysis modes."""
    return f"'{ANALYSIS_MODE_OFFLINE}' or '{ANALYSIS_MODE_ONLINE}'"
