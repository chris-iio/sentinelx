"""Tests for ConfigStore API key persistence.

Uses tmp_path fixture to isolate from real filesystem.
Verifies read/write behavior and directory creation.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.enrichment.config_store import ConfigStore


class TestConfigStoreGetKey:
    def test_get_vt_api_key_returns_none_when_no_config(self, tmp_path: Path) -> None:
        """ConfigStore returns None when no config file exists."""
        config_path = tmp_path / "nonexistent" / "config.ini"
        store = ConfigStore(config_path=config_path)
        assert store.get_vt_api_key() is None

    def test_get_vt_api_key_returns_none_when_file_empty(self, tmp_path: Path) -> None:
        """ConfigStore returns None when config file exists but has no VT key."""
        config_path = tmp_path / "config.ini"
        config_path.write_text("[other_section]\nfoo = bar\n")
        store = ConfigStore(config_path=config_path)
        assert store.get_vt_api_key() is None


class TestConfigStoreSetAndGet:
    def test_set_and_get_vt_api_key(self, tmp_path: Path) -> None:
        """Written key can be read back and matches exactly."""
        config_path = tmp_path / "config.ini"
        store = ConfigStore(config_path=config_path)

        store.set_vt_api_key("my-secret-api-key-xyz789")
        retrieved = store.get_vt_api_key()

        assert retrieved == "my-secret-api-key-xyz789"

    def test_set_vt_api_key_creates_directory(self, tmp_path: Path) -> None:
        """set_vt_api_key creates the parent directory if it does not exist."""
        config_path = tmp_path / "nested" / "deeper" / "config.ini"
        assert not config_path.parent.exists()

        store = ConfigStore(config_path=config_path)
        store.set_vt_api_key("new-key-abc")

        assert config_path.parent.exists()
        assert config_path.exists()

    def test_set_vt_api_key_overwrites_existing(self, tmp_path: Path) -> None:
        """Calling set_vt_api_key twice uses the latest value."""
        config_path = tmp_path / "config.ini"
        store = ConfigStore(config_path=config_path)

        store.set_vt_api_key("first-key")
        store.set_vt_api_key("second-key")

        assert store.get_vt_api_key() == "second-key"

    def test_config_persisted_to_disk(self, tmp_path: Path) -> None:
        """Config survives creating a new ConfigStore instance (disk persistence)."""
        config_path = tmp_path / "config.ini"
        store1 = ConfigStore(config_path=config_path)
        store1.set_vt_api_key("persistent-key-123")

        # Create a fresh instance pointing to the same file
        store2 = ConfigStore(config_path=config_path)
        assert store2.get_vt_api_key() == "persistent-key-123"
