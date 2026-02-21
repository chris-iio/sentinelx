"""API key config store — STUB for TDD RED phase.

All methods raise NotImplementedError so tests fail cleanly.
"""
from __future__ import annotations

from pathlib import Path

CONFIG_PATH = Path.home() / ".sentinelx" / "config.ini"


class ConfigStore:
    """Persists and retrieves provider API keys using configparser INI format."""

    def __init__(self, config_path: Path | None = None) -> None:
        raise NotImplementedError

    def get_vt_api_key(self) -> str | None:
        raise NotImplementedError

    def set_vt_api_key(self, key: str) -> None:
        raise NotImplementedError
