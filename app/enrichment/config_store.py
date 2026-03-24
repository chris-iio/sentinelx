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
_PROVIDERS_SECTION = "providers"
_CACHE_SECTION = "cache"
_CACHE_TTL_KEY = "ttl_hours"
_CACHE_TTL_DEFAULT = 24


class ConfigStore:
    """Persists and retrieves provider API keys using configparser INI format.

    Args:
        config_path: Path to config file. Defaults to ~/.sentinelx/config.ini.
                     Pass a tmp_path in tests for filesystem isolation.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_path = config_path if config_path is not None else CONFIG_PATH
        self._cached_cfg: configparser.ConfigParser | None = None

    def _read_config(self) -> configparser.ConfigParser:
        """Read and return the config file as a ConfigParser instance.

        The parsed result is cached in memory. Subsequent calls return the
        cached parser without re-reading the file. The cache is invalidated
        by _save_config() so writes are always reflected on the next read.
        """
        if self._cached_cfg is not None:
            return self._cached_cfg
        cfg = configparser.ConfigParser()
        cfg.read(self._config_path)
        self._cached_cfg = cfg
        return cfg

    def _save_config(self, cfg: configparser.ConfigParser) -> None:
        """Write config to disk with owner-only permissions (SEC-17: 0o600)."""
        self._config_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(str(self._config_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as fh:
            cfg.write(fh)
        self._cached_cfg = None

    def _set_value(self, section: str, key: str, value: str) -> None:
        """Set a single value in the config file, creating the section if needed."""
        cfg = self._read_config()
        if section not in cfg:
            cfg[section] = {}
        cfg[section][key] = value
        self._save_config(cfg)

    def get_vt_api_key(self) -> str | None:
        """Read the VirusTotal API key from config file.

        Returns:
            The API key string, or None if not configured.
        """
        value = self._read_config().get(_SECTION, _KEY_NAME, fallback=None)
        return value or None

    def set_vt_api_key(self, key: str) -> None:
        """Write the VirusTotal API key to config file.

        Args:
            key: The API key to store.
        """
        self._set_value(_SECTION, _KEY_NAME, key)

    def get_provider_key(self, name: str) -> str | None:
        """Read an API key for any provider from the [providers] INI section.

        Provider names are normalized to lowercase for consistent storage.

        Args:
            name: Provider name (e.g., "greynoise", "abuseipdb"). Case-insensitive.

        Returns:
            The stored API key string, or None if not configured.
        """
        value = self._read_config().get(_PROVIDERS_SECTION, name.lower(), fallback=None)
        return value or None

    def set_provider_key(self, name: str, key: str) -> None:
        """Write an API key for any provider to the [providers] INI section.

        Provider names are normalized to lowercase.

        Args:
            name: Provider name (e.g., "GreyNoise", "abuseipdb"). Case-insensitive.
            key:  The API key to store.
        """
        self._set_value(_PROVIDERS_SECTION, name.lower(), key)

    def get_cache_ttl(self) -> int:
        """Read the cache TTL in hours from config file.

        Returns:
            TTL in hours. Defaults to 24 if not configured.
        """
        value = self._read_config().get(_CACHE_SECTION, _CACHE_TTL_KEY, fallback=None)
        if value is not None:
            try:
                return int(value)
            except ValueError:
                pass
        return _CACHE_TTL_DEFAULT

    def set_cache_ttl(self, hours: int) -> None:
        """Write the cache TTL in hours to config file.

        Args:
            hours: TTL in hours. Must be a positive integer.
        """
        self._set_value(_CACHE_SECTION, _CACHE_TTL_KEY, str(hours))

    def all_provider_keys(self) -> dict[str, str]:
        """Read all provider API keys from the [providers] INI section.

        Returns only keys from the [providers] section -- does not include
        the VirusTotal key stored in the [virustotal] section.

        Returns:
            Dict mapping provider name (lowercase) to API key. Empty dict if
            no provider keys have been stored.
        """
        cfg = self._read_config()
        if _PROVIDERS_SECTION not in cfg:
            return {}
        return dict(cfg[_PROVIDERS_SECTION])
