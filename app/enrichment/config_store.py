"""API key config store using Python stdlib configparser.

Stores and retrieves the VirusTotal API key in an INI-format config file
at ~/.sentinelx/config.ini (outside repo tree — never accidentally committed).

Satisfies user decision: "Settings page in the app where the analyst pastes
their VT API key — no env var requirement."

Usage:
    store = ConfigStore()
    store.set_vt_api_key("my-api-key")
    key = store.get_vt_api_key()  # -> "my-api-key"

For tests, pass a tmp_path to isolate from the real filesystem:
    store = ConfigStore(config_path=tmp_path / "config.ini")
"""
from __future__ import annotations

import configparser
import os
from pathlib import Path

CONFIG_PATH = Path.home() / ".sentinelx" / "config.ini"
_SECTION = "virustotal"
_KEY_NAME = "api_key"


class ConfigStore:
    """Persists and retrieves provider API keys using configparser INI format.

    Args:
        config_path: Path to config file. Defaults to ~/.sentinelx/config.ini.
                     Pass a tmp_path in tests for filesystem isolation.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_path = config_path if config_path is not None else CONFIG_PATH

    def get_vt_api_key(self) -> str | None:
        """Read the VirusTotal API key from config file.

        Returns:
            The API key string, or None if not configured.
        """
        cfg = configparser.ConfigParser()
        cfg.read(self._config_path)
        value = cfg.get(_SECTION, _KEY_NAME, fallback=None)
        return value or None

    def set_vt_api_key(self, key: str) -> None:
        """Write the VirusTotal API key to config file.

        Creates the parent directory if it does not exist.

        Args:
            key: The API key to store.
        """
        self._config_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        cfg = configparser.ConfigParser()
        cfg.read(self._config_path)
        if _SECTION not in cfg:
            cfg[_SECTION] = {}
        cfg[_SECTION][_KEY_NAME] = key
        # SEC-17: Write with owner-only permissions (0o600) to protect API key
        fd = os.open(str(self._config_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as fh:
            cfg.write(fh)
