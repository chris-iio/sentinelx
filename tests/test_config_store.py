"""Tests for ConfigStore API key persistence.

Uses tmp_path fixture to isolate from real filesystem.
Verifies read/write behavior and directory creation.
"""
from __future__ import annotations

from pathlib import Path


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


class TestConfigStoreMultiProvider:
    """Tests for multi-provider key storage via get/set_provider_key."""

    def test_get_provider_key_returns_none_for_missing_key(self, tmp_path: Path) -> None:
        """get_provider_key returns None when no key has been set for that provider."""
        store = ConfigStore(config_path=tmp_path / "config.ini")
        assert store.get_provider_key("greynoise") is None

    def test_get_provider_key_returns_none_when_no_config_file(self, tmp_path: Path) -> None:
        """get_provider_key returns None when config file does not exist."""
        store = ConfigStore(config_path=tmp_path / "nonexistent" / "config.ini")
        assert store.get_provider_key("abuseipdb") is None

    def test_set_and_get_provider_key_roundtrip(self, tmp_path: Path) -> None:
        """set_provider_key + get_provider_key returns the stored value."""
        store = ConfigStore(config_path=tmp_path / "config.ini")
        store.set_provider_key("greynoise", "key123")
        assert store.get_provider_key("greynoise") == "key123"

    def test_set_provider_key_overwrites_existing(self, tmp_path: Path) -> None:
        """Calling set_provider_key twice uses the latest value."""
        store = ConfigStore(config_path=tmp_path / "config.ini")
        store.set_provider_key("abuseipdb", "old-key")
        store.set_provider_key("abuseipdb", "new-key")
        assert store.get_provider_key("abuseipdb") == "new-key"

    def test_provider_key_case_insensitive(self, tmp_path: Path) -> None:
        """Provider name is stored lowercase; mixed-case input is normalized."""
        store = ConfigStore(config_path=tmp_path / "config.ini")
        store.set_provider_key("GreyNoise", "key-xyz")
        # Retrieval with lowercase works
        assert store.get_provider_key("greynoise") == "key-xyz"
        # Retrieval with original case also works (normalized internally)
        assert store.get_provider_key("GreyNoise") == "key-xyz"

    def test_all_provider_keys_returns_empty_dict_when_none_set(self, tmp_path: Path) -> None:
        """all_provider_keys returns empty dict when no provider keys are stored."""
        store = ConfigStore(config_path=tmp_path / "config.ini")
        assert store.all_provider_keys() == {}

    def test_all_provider_keys_returns_all_stored_keys(self, tmp_path: Path) -> None:
        """all_provider_keys returns dict of all provider keys set."""
        store = ConfigStore(config_path=tmp_path / "config.ini")
        store.set_provider_key("greynoise", "gn-key")
        store.set_provider_key("abuseipdb", "ab-key")
        result = store.all_provider_keys()
        assert result == {"greynoise": "gn-key", "abuseipdb": "ab-key"}

    def test_provider_key_persisted_to_disk(self, tmp_path: Path) -> None:
        """Provider keys survive creating a new ConfigStore instance."""
        config_path = tmp_path / "config.ini"
        store1 = ConfigStore(config_path=config_path)
        store1.set_provider_key("otx", "otx-api-key-123")
        store2 = ConfigStore(config_path=config_path)
        assert store2.get_provider_key("otx") == "otx-api-key-123"

    def test_provider_keys_coexist_with_vt_key(self, tmp_path: Path) -> None:
        """Multi-provider keys in [providers] section do not conflict with VT key in [virustotal]."""
        store = ConfigStore(config_path=tmp_path / "config.ini")
        store.set_vt_api_key("vt-key")
        store.set_provider_key("greynoise", "gn-key")
        # Both keys remain independently accessible
        assert store.get_vt_api_key() == "vt-key"
        assert store.get_provider_key("greynoise") == "gn-key"

    def test_all_provider_keys_does_not_include_vt_key(self, tmp_path: Path) -> None:
        """all_provider_keys only returns keys from [providers] section, not [virustotal]."""
        store = ConfigStore(config_path=tmp_path / "config.ini")
        store.set_vt_api_key("vt-key")
        store.set_provider_key("urlhaus", "uh-key")
        result = store.all_provider_keys()
        # [virustotal] section key must not appear here
        assert "api_key" not in result
        assert result == {"urlhaus": "uh-key"}
