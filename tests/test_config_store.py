"""Tests for ConfigStore API key persistence.

Uses tmp_path fixture to isolate from real filesystem.
Verifies read/write behavior and directory creation.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


from app.enrichment.config_store import ConfigStore, _configured_value


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

    def test_save_keeps_written_config_cached(self, tmp_path: Path) -> None:
        """Reads after a write reuse the in-memory parser instead of reparsing disk."""
        config_path = tmp_path / "config.ini"
        store = ConfigStore(config_path=config_path)

        with patch("configparser.ConfigParser.read") as read:
            store.set_vt_api_key("cached-after-save-key")
            read.reset_mock()
            assert store.get_vt_api_key() == "cached-after-save-key"

        read.assert_not_called()

    def test_getters_share_cached_value_helper(self, tmp_path: Path, monkeypatch) -> None:
        """Config getters should route through one cached value-read helper."""
        store = ConfigStore(config_path=tmp_path / "config.ini")
        calls: list[tuple[str, str, str | None]] = []

        def get_value(section: str, key: str, fallback: str | None = None) -> str | None:
            calls.append((section, key, fallback))
            if section == "virustotal":
                return "vt-key"
            if section == "providers":
                return "provider-key"
            if section == "cache":
                return "7"
            if section == "ssh":
                return fallback
            return fallback

        monkeypatch.setattr(store, "_get_value", get_value)

        assert store.get_vt_api_key() == "vt-key"
        assert store.get_provider_key("GreyNoise") == "provider-key"
        assert store.get_cache_ttl() == 7
        assert store.get_ssh_normal_hours() == "06:00-22:00"
        assert calls == [
            ("virustotal", "api_key", None),
            ("providers", "greynoise", None),
            ("cache", "ttl_hours", None),
            ("ssh", "normal_hours", "06:00-22:00"),
        ]

    def test_api_key_getters_share_empty_value_normalization(self) -> None:
        """API-key getters should share one empty-string normalization helper."""
        source = Path("app/enrichment/config_store.py").read_text(encoding="utf-8")

        assert _configured_value("") is None
        assert _configured_value(None) is None
        assert _configured_value("key") == "key"
        assert source.count("_configured_value(") == 3


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

    def test_provider_key_get_and_set_share_option_normalization(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Provider get/set should use one normalization helper for option names."""
        import app.enrichment.config_store as config_store

        calls: list[str] = []

        def normalize(name: str) -> str:
            calls.append(name)
            return name.lower()

        monkeypatch.setattr(config_store, "_provider_option_name", normalize)

        store = ConfigStore(config_path=tmp_path / "config.ini")
        store.set_provider_key("GreyNoise", "key-xyz")

        assert store.get_provider_key("GREYNOISE") == "key-xyz"
        assert calls == ["GreyNoise", "GREYNOISE"]

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

    def test_all_provider_keys_accumulates_directly_from_section(self, tmp_path: Path) -> None:
        """all_provider_keys should not rely on constructor-style section copying."""

        class ProviderSection:
            def __init__(self) -> None:
                self.reads = 0
                self._values = {
                    "greynoise": "gn-key",
                    "abuseipdb": "ab-key",
                }

            def __iter__(self):
                return iter(self._values)

            def __getitem__(self, key: str) -> str:
                self.reads += 1
                return self._values[key]

            def keys(self):
                raise AssertionError("all_provider_keys should not copy the section via dict()")

        class FakeConfig:
            def __init__(self) -> None:
                self.section = ProviderSection()

            def __contains__(self, section: str) -> bool:
                return section == "providers"

            def __getitem__(self, section: str) -> ProviderSection:
                if section != "providers":
                    raise KeyError(section)
                return self.section

        fake_config = FakeConfig()
        store = ConfigStore(config_path=tmp_path / "config.ini")
        store._cached_cfg = fake_config  # type: ignore[assignment]

        assert store.all_provider_keys() == {
            "greynoise": "gn-key",
            "abuseipdb": "ab-key",
        }
        assert fake_config.section.reads == 2


class TestSshSection:
    """Tests for SSH normal-hours configuration via get/set_ssh_normal_hours."""

    def test_get_ssh_normal_hours_returns_default_when_no_config_file(self, tmp_path: Path) -> None:
        """get_ssh_normal_hours returns '06:00-22:00' when no config file exists."""
        store = ConfigStore(config_path=tmp_path / "nonexistent" / "config.ini")
        assert store.get_ssh_normal_hours() == "06:00-22:00"

    def test_get_ssh_normal_hours_returns_default_when_no_ssh_section(self, tmp_path: Path) -> None:
        """get_ssh_normal_hours returns '06:00-22:00' when config file has no [ssh] section."""
        config_path = tmp_path / "config.ini"
        config_path.write_text("[virustotal]\napi_key = vt-key\n")
        store = ConfigStore(config_path=config_path)
        assert store.get_ssh_normal_hours() == "06:00-22:00"

    def test_set_and_get_ssh_normal_hours_roundtrip(self, tmp_path: Path) -> None:
        """set_ssh_normal_hours then get_ssh_normal_hours returns the stored value."""
        store = ConfigStore(config_path=tmp_path / "config.ini")
        store.set_ssh_normal_hours("08:00-20:00")
        assert store.get_ssh_normal_hours() == "08:00-20:00"

    def test_set_ssh_normal_hours_overwrites_previous_value(self, tmp_path: Path) -> None:
        """Calling set_ssh_normal_hours twice returns the latest value."""
        store = ConfigStore(config_path=tmp_path / "config.ini")
        store.set_ssh_normal_hours("07:00-21:00")
        store.set_ssh_normal_hours("09:00-18:00")
        assert store.get_ssh_normal_hours() == "09:00-18:00"

    def test_ssh_normal_hours_persisted_to_disk(self, tmp_path: Path) -> None:
        """SSH normal hours survive creating a new ConfigStore instance (disk persistence)."""
        config_path = tmp_path / "config.ini"
        store1 = ConfigStore(config_path=config_path)
        store1.set_ssh_normal_hours("08:00-20:00")
        store2 = ConfigStore(config_path=config_path)
        assert store2.get_ssh_normal_hours() == "08:00-20:00"

    def test_ssh_section_coexists_with_other_sections(self, tmp_path: Path) -> None:
        """SSH section coexists with [virustotal], [providers], and [cache] sections."""
        store = ConfigStore(config_path=tmp_path / "config.ini")
        store.set_vt_api_key("vt-key")
        store.set_provider_key("greynoise", "gn-key")
        store.set_cache_ttl(48)
        store.set_ssh_normal_hours("08:00-20:00")
        # All values remain independently accessible
        assert store.get_vt_api_key() == "vt-key"
        assert store.get_provider_key("greynoise") == "gn-key"
        assert store.get_cache_ttl() == 48
        assert store.get_ssh_normal_hours() == "08:00-20:00"

    def test_get_ssh_normal_hours_returns_default_when_key_absent_in_ssh_section(
        self, tmp_path: Path
    ) -> None:
        """get_ssh_normal_hours returns '06:00-22:00' when [ssh] section exists but normal_hours key is absent."""
        config_path = tmp_path / "config.ini"
        config_path.write_text("[ssh]\nother_key = other_value\n")
        store = ConfigStore(config_path=config_path)
        assert store.get_ssh_normal_hours() == "06:00-22:00"
