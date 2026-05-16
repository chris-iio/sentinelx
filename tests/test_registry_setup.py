"""Tests for app/enrichment/setup.py — build_registry() factory.

Verifies that build_registry() returns a ProviderRegistry with all registered
providers, using the correct API key from ConfigStore.
"""
from unittest.mock import MagicMock

from app.enrichment.registry import ProviderRegistry


def _make_config_store(
    vt_key: str | None = "test-api-key",
    provider_key: str | None = None,
    provider_keys: dict[str, str | None] | None = None,
) -> MagicMock:
    """Return a mock ConfigStore with VT and provider keys configured."""
    mock_store = MagicMock()
    mock_store.get_vt_api_key.return_value = vt_key
    mock_store.get_provider_key.return_value = provider_key
    if provider_keys is not None:
        mock_store.all_provider_keys.return_value = provider_keys
    elif provider_key is not None:
        mock_store.all_provider_keys.return_value = {
            "malwarebazaar": provider_key,
            "threatfox": provider_key,
            "urlhaus": provider_key,
            "otx": provider_key,
            "greynoise": provider_key,
            "abuseipdb": provider_key,
            "emailrep": provider_key,
        }
    else:
        mock_store.all_provider_keys.return_value = {}
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
        "emailrep.io",
        "ip-api.com",
        "hashlookup.circl.lu",
        "crt.sh",
        "api.threatminer.org",
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

    def test_registry_has_sixteen_providers(self):
        """build_registry() registers exactly 16 providers."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(),
        )
        assert len(registry.all()) == 16

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

    def test_registry_contains_emailrep(self):
        """build_registry() registers a provider named 'EmailRep'."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(),
        )
        names = [p.name for p in registry.all()]
        assert "EmailRep" in names

    def test_shodan_is_always_configured(self):
        """ShodanAdapter is configured even without any API key (zero-auth)."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(None),
        )
        shodan = next(p for p in registry.all() if p.name == "Shodan InternetDB")
        assert shodan.is_configured() is True

    def test_registry_contains_hashlookup(self):
        """build_registry() registers a provider named 'CIRCL Hashlookup'."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(),
        )
        names = [p.name for p in registry.all()]
        assert "CIRCL Hashlookup" in names

    def test_registry_contains_ip_context(self):
        """build_registry() registers a provider named 'IP Context'."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(),
        )
        names = [p.name for p in registry.all()]
        assert "IP Context" in names

    def test_hashlookup_is_always_configured(self):
        """HashlookupAdapter is configured even without any API key (zero-auth)."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(None),
        )
        hashlookup = next(p for p in registry.all() if p.name == "CIRCL Hashlookup")
        assert hashlookup.is_configured() is True

    def test_ip_context_is_always_configured(self):
        """IPApiAdapter is configured even without any API key (zero-auth)."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(None),
        )
        ip_context = next(p for p in registry.all() if p.name == "IP Context")
        assert ip_context.is_configured() is True

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
            "OTX AlienVault", "GreyNoise", "AbuseIPDB", "EmailRep",
        }
        for provider in registry.all():
            if provider.name in key_provider_names:
                assert provider.is_configured() is False, (
                    f"{provider.name} should not be configured without an API key"
                )

    def test_new_provider_configured_with_key(self):
        """URLhausAdapter is_configured() returns True when a key is provided."""
        from app.enrichment.setup import build_registry

        config_store = _make_config_store(None, provider_keys={"urlhaus": "my-urlhaus-key"})
        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=config_store,
        )

        urlhaus = next(p for p in registry.all() if p.name == "URLhaus")
        assert urlhaus.is_configured() is True

    def test_config_store_all_provider_keys_called_once_for_key_providers(self):
        """build_registry() reads the provider-key map once for key-requiring providers."""
        from app.enrichment.setup import build_registry

        config_store = _make_config_store("vt-key")
        build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=config_store,
        )

        config_store.all_provider_keys.assert_called_once_with()
        config_store.get_provider_key.assert_not_called()

    def test_build_registry_reuses_allowed_host_membership_snapshot(self):
        """Provider setup should snapshot the allowlist once and share it across HTTP adapters."""
        from app.enrichment.setup import build_registry

        allowed_hosts = _make_allowed_hosts()
        registry = build_registry(
            allowed_hosts=allowed_hosts,
            config_store=_make_config_store("vt-key", provider_key="shared-key"),
        )
        allowed_hosts.append("late-added.example")

        memberships = [
            provider._allowed_hosts
            for provider in registry.all()
            if hasattr(provider, "_allowed_hosts")
        ]

        assert memberships
        assert len({id(membership) for membership in memberships}) == 1
        assert "late-added.example" not in memberships[0]
        assert isinstance(memberships[0], frozenset)

    def test_key_required_providers_share_registration_helper(self, monkeypatch):
        """Key-requiring non-VT providers should share one registration path."""
        import app.enrichment.setup as setup_module

        calls: list[tuple[str, str]] = []
        original = setup_module._register_keyed_provider

        def register_keyed_provider(
            registry,
            adapter_cls,
            provider_keys,
            provider_id,
            allowed_hosts,
        ):
            calls.append((provider_id, adapter_cls.__name__))
            original(registry, adapter_cls, provider_keys, provider_id, allowed_hosts)

        monkeypatch.setattr(setup_module, "_register_keyed_provider", register_keyed_provider)

        registry = setup_module.build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store("vt-key", provider_key="shared-key"),
        )

        assert len(registry.all()) == 16
        assert calls == [
            ("malwarebazaar", "MBAdapter"),
            ("threatfox", "TFAdapter"),
            ("urlhaus", "URLhausAdapter"),
            ("otx", "OTXAdapter"),
            ("greynoise", "GreyNoiseAdapter"),
            ("abuseipdb", "AbuseIPDBAdapter"),
            ("emailrep", "EmailRepAdapter"),
        ]

    def test_zero_auth_providers_share_registration_helper(self, monkeypatch):
        """Zero-auth providers should share one registration path."""
        import app.enrichment.setup as setup_module

        calls: list[str] = []
        original = setup_module._register_zero_auth_provider

        def register_zero_auth_provider(registry, adapter_cls, allowed_hosts):
            calls.append(adapter_cls.__name__)
            original(registry, adapter_cls, allowed_hosts)

        monkeypatch.setattr(
            setup_module,
            "_register_zero_auth_provider",
            register_zero_auth_provider,
        )

        registry = setup_module.build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store("vt-key", provider_key="shared-key"),
        )

        assert len(registry.all()) == 16
        assert calls == [
            "HashlookupAdapter",
            "IPApiAdapter",
            "DnsAdapter",
            "CrtShAdapter",
            "ThreatMinerAdapter",
            "CymruASNAdapter",
            "WhoisAdapter",
        ]

    def test_provider_registration_tables_preserve_order_without_slices(self):
        """Provider setup should scan static registration tables in provider order."""
        import dis

        import app.enrichment.setup as setup_module

        keyed = (
            setup_module._PRE_SHODAN_KEYED_PROVIDER_REGISTRATIONS
            + setup_module._POST_SHODAN_KEYED_PROVIDER_REGISTRATIONS
        )
        keyed_names = [
            (provider_id, adapter_cls.__name__)
            for provider_id, adapter_cls in keyed
        ]
        assert keyed_names == [
            ("malwarebazaar", "MBAdapter"),
            ("threatfox", "TFAdapter"),
            ("urlhaus", "URLhausAdapter"),
            ("otx", "OTXAdapter"),
            ("greynoise", "GreyNoiseAdapter"),
            ("abuseipdb", "AbuseIPDBAdapter"),
            ("emailrep", "EmailRepAdapter"),
        ]
        zero_auth_names = [
            adapter_cls.__name__
            for adapter_cls in setup_module._ZERO_AUTH_PROVIDER_CLASSES
        ]
        assert zero_auth_names == [
            "HashlookupAdapter",
            "IPApiAdapter",
            "DnsAdapter",
            "CrtShAdapter",
            "ThreatMinerAdapter",
            "CymruASNAdapter",
            "WhoisAdapter",
        ]
        assert {
            instruction.opname
            for instruction in dis.get_instructions(setup_module.build_registry)
        }.isdisjoint({"BUILD_SLICE", "BINARY_SLICE"})

    def test_registry_contains_dns_records(self):
        """build_registry() registers a provider named 'DNS Records'."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(),
        )
        names = [p.name for p in registry.all()]
        assert "DNS Records" in names

    def test_registry_contains_cert_history(self):
        """build_registry() registers a provider named 'Cert History'."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(),
        )
        names = [p.name for p in registry.all()]
        assert "Cert History" in names

    def test_dns_records_is_always_configured(self):
        """DnsAdapter is configured even without any API key (zero-auth)."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(None),
        )
        dns = next(p for p in registry.all() if p.name == "DNS Records")
        assert dns.is_configured() is True

    def test_cert_history_is_always_configured(self):
        """CrtShAdapter is configured even without any API key (zero-auth)."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(None),
        )
        cert = next(p for p in registry.all() if p.name == "Cert History")
        assert cert.is_configured() is True

    def test_registry_contains_threatminer(self):
        """build_registry() registers a provider named 'ThreatMiner'."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(),
        )
        names = [p.name for p in registry.all()]
        assert "ThreatMiner" in names

    def test_threatminer_is_always_configured(self):
        """ThreatMinerAdapter is configured even without any API key (zero-auth)."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(None),
        )
        threatminer = next(p for p in registry.all() if p.name == "ThreatMiner")
        assert threatminer.is_configured() is True

    def test_registry_contains_asn_intel(self):
        """build_registry() registers a provider named 'ASN Intel'."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(),
        )
        names = [p.name for p in registry.all()]
        assert "ASN Intel" in names

    def test_asn_intel_is_always_configured(self):
        """CymruASNAdapter is configured even without any API key (zero-auth)."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(None),
        )
        asn_intel = next(p for p in registry.all() if p.name == "ASN Intel")
        assert asn_intel.is_configured() is True

    def test_asn_intel_supports_ipv4_and_ipv6(self):
        """CymruASNAdapter supports IPV4 and IPV6 IOC types (zero-auth, DNS-based)."""
        from app.enrichment.setup import build_registry
        from app.pipeline.models import IOCType

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(None),
        )
        asn_intel = next(p for p in registry.all() if p.name == "ASN Intel")
        assert IOCType.IPV4 in asn_intel.supported_types
        assert IOCType.IPV6 in asn_intel.supported_types

    def test_registry_contains_whois(self):
        """build_registry() registers a provider named 'WHOIS'."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(),
        )
        names = [p.name for p in registry.all()]
        assert "WHOIS" in names

    def test_whois_is_always_configured(self):
        """WhoisAdapter is configured even without any API key (zero-auth)."""
        from app.enrichment.setup import build_registry

        registry = build_registry(
            allowed_hosts=_make_allowed_hosts(),
            config_store=_make_config_store(None),
        )
        whois = next(p for p in registry.all() if p.name == "WHOIS")
        assert whois.is_configured() is True
