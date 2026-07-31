"""Tests for ConfigStore API key persistence.

Uses tmp_path fixture to isolate from real filesystem.
Verifies read/write behavior and directory creation.
"""
from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import patch

import app.enrichment.config_values as config_values
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

    def test_save_keeps_written_config_cached(self, tmp_path: Path) -> None:
        """Reads after a write reuse the in-memory parser instead of reparsing disk."""
        config_path = tmp_path / "config.ini"
        store = ConfigStore(config_path=config_path)

        with patch("configparser.ConfigParser.read") as read:
            store.set_vt_api_key("cached-after-save-key")
            read.reset_mock()
            assert store.get_vt_api_key() == "cached-after-save-key"

        read.assert_not_called()

    def test_save_uses_atomic_replace_with_owner_only_permissions(self, tmp_path: Path) -> None:
        """Writes should replace the destination atomically without leaving temp files."""
        import app.enrichment.config_files as config_files

        config_path = tmp_path / "config.ini"
        store = ConfigStore(config_path=config_path)
        replace_calls: list[tuple[Path, Path]] = []
        original_replace = config_files.os.replace

        def record_replace(source, destination) -> None:
            replace_calls.append((Path(source), Path(destination)))
            original_replace(source, destination)

        with patch("app.enrichment.config_files.os.replace", record_replace):
            store.set_vt_api_key("atomic-key")

        assert store.get_vt_api_key() == "atomic-key"
        assert replace_calls
        assert replace_calls[-1][1] == config_path
        assert not list(tmp_path.glob(".config.ini.*.tmp"))
        assert config_path.stat().st_mode & 0o777 == 0o600

    def test_failed_atomic_replace_preserves_disk_and_cache(self, tmp_path: Path) -> None:
        """A failed replace should leave the last saved config visible."""
        config_path = tmp_path / "config.ini"
        store = ConfigStore(config_path=config_path)
        store.set_vt_api_key("original-key")

        with patch(
            "app.enrichment.config_files.os.replace",
            side_effect=OSError("synthetic replace failure"),
        ):
            try:
                store.set_provider_key("greynoise", "new-key")
            except OSError:
                pass
            else:  # pragma: no cover - defensive assertion branch
                raise AssertionError("expected synthetic replace failure")

        assert store.get_vt_api_key() == "original-key"
        assert store.get_provider_key("greynoise") is None
        assert ConfigStore(config_path=config_path).get_provider_key("greynoise") is None
        assert not list(tmp_path.glob(".config.ini.*.tmp"))

    def test_config_store_delegates_file_mechanics_to_config_files(self) -> None:
        """ConfigStore should keep low-level lock/copy/write mechanics out of the domain class."""
        import inspect

        save_source = inspect.getsource(ConfigStore._save_config)
        set_source = inspect.getsource(ConfigStore._set_value)

        assert "config_files.config_lock_for_path(" in inspect.getsource(ConfigStore.__init__)
        assert "write_config_atomic(" in save_source
        assert "mkstemp" not in save_source
        assert "config_files.copy_config(" in set_source

    def test_config_copy_accumulates_sections_without_constructor_copies(self) -> None:
        """Config copies should avoid dict-comprehension and dict(section) copies."""
        import configparser
        import inspect

        import app.enrichment.config_files as config_files

        cfg = configparser.ConfigParser()
        cfg["virustotal"] = {"api_key": "vt-key"}
        cfg["providers"] = {"greynoise": "grey-key"}

        copied = config_files.copy_config(cfg)
        copied["providers"]["greynoise"] = "changed"
        source = inspect.getsource(config_files.copy_config)

        assert cfg["providers"]["greynoise"] == "grey-key"
        assert copied["providers"]["greynoise"] == "changed"
        assert "read_dict" not in source
        assert "dict(" not in source
        assert "append_config_section(copied, cfg, section)" in source
        assert "copied.add_section(section)" not in source
        assert "copied.add_section(section)" in inspect.getsource(
            config_files.append_config_section
        )
        assert "append_config_option" not in config_files.copy_config.__code__.co_names
        assert "append_config_option" in config_files.append_config_section.__code__.co_names
        assert "copied.set(section, option, source_section[option])" not in source
        assert "copied.set(section, option, source_section[option])" in inspect.getsource(
            config_files.append_config_option
        )
        assert all(
            getattr(const, "co_name", None) != "<dictcomp>"
            for const in config_files.copy_config.__code__.co_consts
        )

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

        assert config_values.configured_value("") is None
        assert config_values.configured_value(None) is None
        assert config_values.configured_value("key") == "key"
        assert "_configured_value" not in source
        assert source.count("config_values.configured_value(") == 2

    def test_config_store_delegates_value_helpers(self) -> None:
        """Config value normalization should live outside the persistence facade."""
        import inspect

        ttl_source = inspect.getsource(ConfigStore.get_cache_ttl)
        provider_keys_source = inspect.getsource(ConfigStore.all_provider_keys)
        provider_keys_helper_source = inspect.getsource(config_values.provider_keys_from_config)

        assert config_values.cache_ttl_hours("7", default=24) == 7
        assert config_values.cache_ttl_hours("bad", default=24) == 24
        assert "pass" not in inspect.getsource(config_values.cache_ttl_hours)
        assert "cache_ttl_hours(" in ttl_source
        assert "int(" not in ttl_source
        assert "provider_keys_from_config(" in provider_keys_source
        assert "for name in section" not in provider_keys_source
        assert "for name in section" in provider_keys_helper_source


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

    def test_provider_keys_with_percent_signs_roundtrip_literally(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.ini"
        key = "prefix%literal%(not-interpolation)s"

        ConfigStore(config_path=config_path).set_provider_key("greynoise", key)

        reopened = ConfigStore(config_path=config_path)
        assert reopened.get_provider_key("greynoise") == key
        assert reopened.all_provider_keys() == {"greynoise": key}

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
        calls: list[str] = []

        def normalize(name: str) -> str:
            calls.append(name)
            return name.lower()

        monkeypatch.setattr(config_values, "provider_option_name", normalize)

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
            def __init__(self, values: dict[str, str]) -> None:
                self.reads = 0
                self.iterations = 0
                self._values = values

            def __len__(self) -> int:
                return len(self._values)

            def __iter__(self):
                for key in self._values:
                    self.iterations += 1
                    if self.iterations > len(self._values):
                        raise AssertionError("provider key copy should stop at section length")
                    yield key

            def __getitem__(self, key: str) -> str:
                self.reads += 1
                return self._values[key]

            def keys(self):
                raise AssertionError("all_provider_keys should not copy the section via dict()")

        class FakeConfig:
            def __init__(self, values: dict[str, str]) -> None:
                self.section = ProviderSection(values)

            def __contains__(self, section: str) -> bool:
                return section == "providers"

            def __getitem__(self, section: str) -> ProviderSection:
                if section != "providers":
                    raise KeyError(section)
                return self.section

        fake_config = FakeConfig({
            "greynoise": "gn-key",
            "abuseipdb": "ab-key",
            "emailrep": "email-key",
            "urlhaus": "urlhaus-key",
        })
        store = ConfigStore(config_path=tmp_path / "config.ini")
        store._cached_cfg = fake_config  # type: ignore[assignment]

        assert store.all_provider_keys() == {
            "greynoise": "gn-key",
            "abuseipdb": "ab-key",
            "emailrep": "email-key",
            "urlhaus": "urlhaus-key",
        }
        assert fake_config.section.reads == 4
        assert fake_config.section.iterations == 4
        assert "len" in config_values.provider_keys_from_config.__code__.co_names
        assert "key_count == 4" in inspect.getsource(config_values.provider_keys_from_config)

    def test_provider_key_fallback_delegates_append_mutation(self) -> None:
        """Long provider-key copies should delegate the per-key mutation."""

        section = {
            "greynoise": "gn-key",
            "abuseipdb": "ab-key",
            "emailrep": "email-key",
            "urlhaus": "urlhaus-key",
            "otx": "otx-key",
        }
        provider_keys_source = inspect.getsource(config_values.provider_keys_from_config)
        fallback_source = provider_keys_source.split("keys: dict[str, str] = {}")[1]
        append_source = inspect.getsource(config_values.append_provider_key)

        assert config_values.provider_keys_from_config(
            {"providers": section},
            providers_section="providers",
        ) == section
        assert "append_provider_key(keys, section, name)" in fallback_source
        assert "keys[name] = section[name]" not in fallback_source
        assert "keys[name] = section[name]" in append_source


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
