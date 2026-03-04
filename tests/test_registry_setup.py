"""Tests for app/enrichment/setup.py — build_registry() factory.

Verifies that build_registry() returns a ProviderRegistry with all eight
providers registered, using the correct API key from ConfigStore.
"""
from unittest.mock import MagicMock, call

import pytest

from app.enrichment.registry import ProviderRegistry


def _make_config_store(
    vt_key: str | None = "test-api-key",
    provider_key: str | None = None,
) -> MagicMock:
    """Return a mock ConfigStore with get_vt_api_key() and get_provider_key() configured."""
    mock_store = MagicMock()
    mock_store.get_vt_api_key.return_value = vt_key
    mock_store.get_provider_key.return_value = provider_key
    return mock_store


def _make_allowed_hosts() -> list[str]:
    return [
        "www.virustotal.com",
        "mb-api.abuse.ch",
        "threatfox-api.abuse.ch",
        "internetdb.shodan.io",
        "urlhaus-api.abuse.ch",
        "otx.alienvault.com",
        "api.greynoise.io",
        "api.abuseipdb.com",
    ]


class TestBuildRegistry:
    """Tests for the build_registry() factory function."""

    def test_returns_provider_registry(self):
        """build_registry() returns a ProviderRegistry instance."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(),
        )
        assert isinstance(registry, ProviderRegistry)

    def test_registry_has_eight_providers(self):
        """build_registry() registers exactly 8 providers."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(),
        )
        assert len(registry.all()) == 8

    def test_registry_contains_virustotal(self):
        """build_registry() registers a provider named 'VirusTotal'."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store("fake-vt-key"),
        )
        names = [p.name for p in registry.all()]
        assert "VirusTotal" in names

    def test_registry_contains_malwarebazaar(self):
        """build_registry() registers a provider named 'MalwareBazaar'."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(),
        )
        names = [p.name for p in registry.all()]
        assert "MalwareBazaar" in names

    def test_registry_contains_threatfox(self):
        """build_registry() registers a provider named 'ThreatFox'."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(),
        )
        names = [p.name for p in registry.all()]
        assert "ThreatFox" in names

    def test_registry_contains_shodan(self):
        """build_registry() registers a provider named 'Shodan InternetDB'."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(),
        )
        names = [p.name for p in registry.all()]
        assert "Shodan InternetDB" in names

    def test_registry_contains_urlhaus(self):
        """build_registry() registers a provider named 'URLhaus'."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(),
        )
        names = [p.name for p in registry.all()]
        assert "URLhaus" in names

    def test_registry_contains_otx(self):
        """build_registry() registers a provider named 'OTX AlienVault'."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(),
        )
        names = [p.name for p in registry.all()]
        assert "OTX AlienVault" in names

    def test_registry_contains_greynoise(self):
        """build_registry() registers a provider named 'GreyNoise'."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(),
        )
        names = [p.name for p in registry.all()]
        assert "GreyNoise" in names

    def test_registry_contains_abuseipdb(self):
        """build_registry() registers a provider named 'AbuseIPDB'."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(),
        )
        names = [p.name for p in registry.all()]
        assert "AbuseIPDB" in names

    def test_shodan_is_always_configured(self):
        """ShodanAdapter is configured even without any API key (zero-auth)."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(None),
        )
        shodan = next(p for p in registry.all() if p.name == "Shodan InternetDB")
        assert shodan.is_configured() is True

    def test_vt_adapter_receives_api_key_from_config_store(self):
        """VTAdapter in the registry uses the key returned by config_store.get_vt_api_key()."""
        from app.enrichment.setup import build_registry

        config_store = _make_config_store("my-secret-vt-key")
        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=config_store,
        )

        # VTAdapter.is_configured() returns True only when key is set
        vt = next(p for p in registry.all() if p.name == "VirusTotal")
        assert vt.is_configured() is True

    def test_vt_adapter_receives_empty_string_when_config_store_returns_none(self):
        """When config_store returns None for VT key, VTAdapter is not configured."""
        from app.enrichment.setup import build_registry

        config_store = _make_config_store(None)
        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=config_store,
        )

        vt = next(p for p in registry.all() if p.name == "VirusTotal")
        # Empty string → is_configured() returns False
        assert vt.is_configured() is False

    def test_abuse_ch_providers_unconfigured_without_keys(self):
        """MalwareBazaar and ThreatFox are not configured without API keys."""
        from app.enrichment.setup import build_registry

        config_store = _make_config_store(None, provider_key=None)
        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=config_store,
        )

        mb = next(p for p in registry.all() if p.name == "MalwareBazaar")
        tf = next(p for p in registry.all() if p.name == "ThreatFox")
        assert mb.is_configured() is False
        assert tf.is_configured() is False

    def test_config_store_get_vt_api_key_is_called(self):
        """build_registry() calls config_store.get_vt_api_key() exactly once."""
        from app.enrichment.setup import build_registry

        config_store = _make_config_store("some-key")
        build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=config_store,
        )
        config_store.get_vt_api_key.assert_called_once()

    def test_key_providers_unconfigured_without_keys(self):
        """All key-requiring providers are not configured when no keys are set."""
        from app.enrichment.setup import build_registry

        # get_provider_key returns None for all providers (default)
        config_store = _make_config_store(None, provider_key=None)
        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=config_store,
        )

        key_provider_names = {
            "MalwareBazaar", "ThreatFox", "URLhaus",
            "OTX AlienVault", "GreyNoise", "AbuseIPDB",
        }
        for provider in registry.all():
            if provider.name in key_provider_names:
                assert provider.is_configured() is False, (
                    f"{provider.name} should not be configured without an API key"
                )

    def test_new_provider_configured_with_key(self):
        """URLhausAdapter is_configured() returns True when a key is provided."""
        from app.enrichment.setup import build_registry

        config_store = _make_config_store(None)
        # Return a key only for "urlhaus"
        def _get_provider_key(name: str) -> str | None:
            return "my-urlhaus-key" if name == "urlhaus" else None

        config_store.get_provider_key.side_effect = _get_provider_key
        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=config_store,
        )

        urlhaus = next(p for p in registry.all() if p.name == "URLhaus")
        assert urlhaus.is_configured() is True

    def test_config_store_get_provider_key_called_for_each_new_provider(self):
        """build_registry() calls get_provider_key() once per new key-requiring provider."""
        from app.enrichment.setup import build_registry

        config_store = _make_config_store("vt-key")
        build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=config_store,
        )

        # Should be called for malwarebazaar, threatfox, urlhaus, otx, greynoise, abuseipdb = 6 times
        assert config_store.get_provider_key.call_count == 6
        called_names = {c.args[0] for c in config_store.get_provider_key.call_args_list}
        assert called_names == {"malwarebazaar", "threatfox", "urlhaus", "otx", "greynoise", "abuseipdb"}
