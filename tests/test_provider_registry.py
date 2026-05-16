"""Tests for ProviderRegistry.

Verifies register, lookup, filtering by configuration status,
and filtering by IOC type support. Uses stub provider classes to
avoid coupling tests to real adapter implementations.
"""
from __future__ import annotations

import builtins

import pytest

import app.enrichment.registry as registry_module
from app.enrichment.registry import ProviderRegistry
from app.pipeline.models import IOCType


# ---------------------------------------------------------------------------
# Stub provider helpers
# ---------------------------------------------------------------------------

class _StubProvider:
    """Minimal stub that satisfies Provider protocol for testing."""

    def __init__(
        self,
        name: str,
        supported_types: set[IOCType],
        requires_api_key: bool = False,
        configured: bool = True,
    ) -> None:
        self.name = name
        self.supported_types = supported_types
        self.requires_api_key = requires_api_key
        self._configured = configured

    def lookup(self, ioc):
        raise NotImplementedError

    def is_configured(self) -> bool:
        return self._configured


def _make_ip_provider(name: str = "IPProvider", configured: bool = True) -> _StubProvider:
    return _StubProvider(
        name=name,
        supported_types={IOCType.IPV4, IOCType.IPV6},
        configured=configured,
    )


def _make_hash_provider(name: str = "HashProvider", configured: bool = True) -> _StubProvider:
    return _StubProvider(
        name=name,
        supported_types={IOCType.MD5, IOCType.SHA1, IOCType.SHA256},
        configured=configured,
    )


def _make_all_provider(name: str = "AllProvider", configured: bool = True) -> _StubProvider:
    return _StubProvider(
        name=name,
        supported_types={IOCType.IPV4, IOCType.MD5, IOCType.DOMAIN},
        configured=configured,
    )


class _NoValuesDict(dict):
    def values(self):
        raise AssertionError("ProviderRegistry should scan provider keys directly")


class _NoIterEmptyDict(dict):
    def __iter__(self):
        raise AssertionError("empty registry helpers should return before provider iteration")


# ---------------------------------------------------------------------------
# Empty registry edge cases
# ---------------------------------------------------------------------------

class TestEmptyRegistry:
    def test_all_returns_empty_list(self) -> None:
        """Empty registry.all() returns an empty list."""
        registry = ProviderRegistry()
        assert registry.all() == []

    def test_configured_returns_empty_list(self) -> None:
        """Empty registry.configured() returns an empty list."""
        registry = ProviderRegistry()
        assert registry.configured() == []

    def test_providers_for_type_returns_empty_list(self) -> None:
        """Empty registry.providers_for_type() returns an empty list."""
        registry = ProviderRegistry()
        assert registry.providers_for_type(IOCType.IPV4) == []

    def test_provider_count_for_type_returns_zero(self) -> None:
        """Empty registry.provider_count_for_type() returns 0."""
        registry = ProviderRegistry()
        assert registry.provider_count_for_type(IOCType.IPV4) == 0

    def test_empty_registry_helpers_skip_provider_iteration(self) -> None:
        """Empty list/count helpers should return before scanning provider keys."""
        registry = ProviderRegistry()
        registry._providers = _NoIterEmptyDict()

        assert registry.all() == []
        assert registry.configured() == []
        assert registry.configured_count() == 0
        assert registry.providers_for_type(IOCType.IPV4) == []
        assert registry.provider_count_for_type(IOCType.IPV4) == 0


# ---------------------------------------------------------------------------
# Register and retrieve
# ---------------------------------------------------------------------------

class TestRegistryRegister:
    def test_register_and_all_returns_provider(self) -> None:
        """register() adds provider; all() returns it."""
        registry = ProviderRegistry()
        provider = _make_ip_provider()
        registry.register(provider)
        assert provider in registry.all()

    def test_register_multiple_providers(self) -> None:
        """register() multiple providers; all() returns all of them."""
        registry = ProviderRegistry()
        p1 = _make_ip_provider(name="IP")
        p2 = _make_hash_provider(name="Hash")
        registry.register(p1)
        registry.register(p2)
        providers = registry.all()
        assert p1 in providers
        assert p2 in providers
        assert len(providers) == 2

    def test_register_duplicate_name_raises_value_error(self) -> None:
        """register() with a duplicate name raises ValueError."""
        registry = ProviderRegistry()
        p1 = _make_ip_provider(name="Duplicate")
        p2 = _make_ip_provider(name="Duplicate")
        registry.register(p1)
        with pytest.raises(ValueError, match="Duplicate"):
            registry.register(p2)

    def test_all_returns_list_not_original_dict(self) -> None:
        """all() returns a list; mutating it does not affect registry state."""
        registry = ProviderRegistry()
        provider = _make_ip_provider()
        registry.register(provider)
        returned = registry.all()
        returned.clear()
        # Registry still has the provider after caller clears the returned list
        assert len(registry.all()) == 1

    def test_all_accumulates_without_values_view(self) -> None:
        """all() should copy providers directly without allocating a dict-values view."""
        registry = ProviderRegistry()
        provider = _make_ip_provider()
        registry._providers = _NoValuesDict({"IPProvider": provider})

        assert registry.all() == [provider]

    def test_registered_count_does_not_allocate_provider_list(self, monkeypatch) -> None:
        """registered_count() should count registry entries without copying providers."""
        registry = ProviderRegistry()
        registry.register(_make_ip_provider())

        def fail_all():
            raise AssertionError("registered_count should not allocate all providers")

        monkeypatch.setattr(registry, "all", fail_all)

        assert registry.registered_count() == 1


# ---------------------------------------------------------------------------
# configured() filtering
# ---------------------------------------------------------------------------

class TestRegistryConfigured:
    def test_configured_returns_only_configured_providers(self) -> None:
        """configured() excludes providers where is_configured() is False."""
        registry = ProviderRegistry()
        configured = _make_ip_provider(name="Configured", configured=True)
        not_configured = _make_hash_provider(name="NotConfigured", configured=False)
        registry.register(configured)
        registry.register(not_configured)
        result = registry.configured()
        assert configured in result
        assert not_configured not in result

    def test_configured_returns_all_when_all_configured(self) -> None:
        """configured() returns all providers when all are configured."""
        registry = ProviderRegistry()
        p1 = _make_ip_provider(name="A", configured=True)
        p2 = _make_hash_provider(name="B", configured=True)
        registry.register(p1)
        registry.register(p2)
        assert len(registry.configured()) == 2

    def test_configured_returns_empty_when_none_configured(self) -> None:
        """configured() returns empty when no providers are configured."""
        registry = ProviderRegistry()
        p1 = _make_ip_provider(name="A", configured=False)
        p2 = _make_hash_provider(name="B", configured=False)
        registry.register(p1)
        registry.register(p2)
        assert registry.configured() == []

    def test_configured_count_does_not_allocate_provider_list(self, monkeypatch) -> None:
        """configured_count() should count configured providers without copying them."""
        registry = ProviderRegistry()
        registry.register(_make_ip_provider(name="Configured", configured=True))
        registry.register(_make_hash_provider(name="Unconfigured", configured=False))

        def fail_configured():
            raise AssertionError("configured_count should not allocate configured providers")

        monkeypatch.setattr(registry, "configured", fail_configured)

        assert registry.configured_count() == 1


# ---------------------------------------------------------------------------
# providers_for_type() filtering
# ---------------------------------------------------------------------------

class TestRegistryProvidersForType:
    def test_providers_for_type_returns_configured_supporting_type(self) -> None:
        """providers_for_type() returns configured providers supporting the type."""
        registry = ProviderRegistry()
        ip_provider = _make_ip_provider(name="IP", configured=True)
        hash_provider = _make_hash_provider(name="Hash", configured=True)
        registry.register(ip_provider)
        registry.register(hash_provider)
        result = registry.providers_for_type(IOCType.IPV4)
        assert ip_provider in result
        assert hash_provider not in result

    def test_providers_for_type_excludes_unconfigured(self) -> None:
        """providers_for_type() excludes unconfigured providers even if they support the type."""
        registry = ProviderRegistry()
        configured_ip = _make_ip_provider(name="ConfiguredIP", configured=True)
        unconfigured_ip = _make_ip_provider(name="UnconfiguredIP", configured=False)
        registry.register(configured_ip)
        registry.register(unconfigured_ip)
        result = registry.providers_for_type(IOCType.IPV4)
        assert configured_ip in result
        assert unconfigured_ip not in result

    def test_providers_for_type_returns_multiple_matching(self) -> None:
        """providers_for_type() returns all configured providers that support the type."""
        registry = ProviderRegistry()
        all1 = _make_all_provider(name="All1", configured=True)
        all2 = _make_all_provider(name="All2", configured=True)
        registry.register(all1)
        registry.register(all2)
        result = registry.providers_for_type(IOCType.MD5)
        assert all1 in result
        assert all2 in result

    def test_providers_for_type_returns_empty_when_no_match(self) -> None:
        """providers_for_type() returns empty when no configured providers support the type."""
        registry = ProviderRegistry()
        hash_provider = _make_hash_provider(name="Hash", configured=True)
        registry.register(hash_provider)
        result = registry.providers_for_type(IOCType.IPV4)
        assert result == []

    def test_providers_for_type_returns_empty_for_all_unconfigured(self) -> None:
        """providers_for_type() returns empty when matching providers are unconfigured."""
        registry = ProviderRegistry()
        ip_provider = _make_ip_provider(name="IP", configured=False)
        registry.register(ip_provider)
        result = registry.providers_for_type(IOCType.IPV4)
        assert result == []

    def test_providers_for_type_uses_shared_eligibility_predicate(self, monkeypatch) -> None:
        """providers_for_type() should share configured/type eligibility logic."""
        provider = _make_ip_provider(name="IP", configured=True)
        calls: list[tuple[str, IOCType]] = []

        def eligible(candidate, ioc_type: IOCType):
            calls.append((candidate.name, ioc_type))
            return candidate.name == "IP" and ioc_type == IOCType.IPV4

        monkeypatch.setattr(registry_module, "_provider_supports_configured_type", eligible)
        registry = ProviderRegistry()
        registry.register(provider)

        assert registry.providers_for_type(IOCType.IPV4) == [provider]
        assert calls == [("IP", IOCType.IPV4)]


# ---------------------------------------------------------------------------
# Registry list-returning filters
# ---------------------------------------------------------------------------

class TestRegistryListReturningFilters:
    def test_list_filters_do_not_allocate_comprehension_frames(self) -> None:
        """Registry list filters should accumulate directly during the provider scan."""
        for method in (
            ProviderRegistry.configured,
            ProviderRegistry.providers_for_type,
        ):
            nested_code_names = {
                const.co_name
                for const in method.__code__.co_consts
                if hasattr(const, "co_name")
            }
            assert "<listcomp>" not in nested_code_names

    def test_list_filters_scan_without_values_view(self) -> None:
        """List-returning filters should scan provider keys without dict-values views."""
        configured = _make_ip_provider(name="Configured", configured=True)
        unconfigured = _make_hash_provider(name="Unconfigured", configured=False)
        registry = ProviderRegistry()
        registry._providers = _NoValuesDict(
            {
                configured.name: configured,
                unconfigured.name: unconfigured,
            }
        )

        assert registry.configured() == [configured]
        assert registry.providers_for_type(IOCType.IPV4) == [configured]


# ---------------------------------------------------------------------------
# provider_count_for_type()
# ---------------------------------------------------------------------------

class TestRegistryProviderCountForType:
    def test_count_returns_correct_value(self) -> None:
        """provider_count_for_type() returns number of configured providers for type."""
        registry = ProviderRegistry()
        p1 = _make_all_provider(name="All1", configured=True)
        p2 = _make_all_provider(name="All2", configured=True)
        p3 = _make_all_provider(name="All3", configured=False)
        registry.register(p1)
        registry.register(p2)
        registry.register(p3)
        # p3 is unconfigured, so only p1 and p2 count
        assert registry.provider_count_for_type(IOCType.MD5) == 2

    def test_count_returns_zero_for_no_matching(self) -> None:
        """provider_count_for_type() returns 0 when no configured provider supports type."""
        registry = ProviderRegistry()
        hash_provider = _make_hash_provider(name="Hash", configured=True)
        registry.register(hash_provider)
        assert registry.provider_count_for_type(IOCType.IPV4) == 0

    def test_count_does_not_allocate_provider_list(self, monkeypatch) -> None:
        """provider_count_for_type() counts directly instead of building provider objects."""
        registry = ProviderRegistry()
        registry.register(_make_ip_provider(name="IP", configured=True))

        def fail_providers_for_type(ioc_type: IOCType):
            raise AssertionError("provider_count_for_type should count directly")

        monkeypatch.setattr(registry, "providers_for_type", fail_providers_for_type)

        assert registry.provider_count_for_type(IOCType.IPV4) == 1

    def test_count_does_not_use_sum_generator(self, monkeypatch) -> None:
        """provider_count_for_type() should count in the registry scan directly."""
        registry = ProviderRegistry()
        registry.register(_make_ip_provider(name="IP", configured=True))
        registry.register(_make_hash_provider(name="Hash", configured=True))

        def fail_sum(*_args, **_kwargs):
            raise AssertionError("provider_count_for_type should not build a sum generator")

        monkeypatch.setattr(builtins, "sum", fail_sum)

        assert registry.provider_count_for_type(IOCType.IPV4) == 1

    def test_count_scans_without_values_view(self) -> None:
        """provider_count_for_type() should scan provider keys without a values view."""
        registry = ProviderRegistry()
        provider = _make_ip_provider(name="IP", configured=True)
        registry._providers = _NoValuesDict({provider.name: provider})

        assert registry.provider_count_for_type(IOCType.IPV4) == 1

    def test_count_uses_shared_eligibility_predicate(self, monkeypatch) -> None:
        """provider_count_for_type() should share configured/type eligibility logic."""
        provider = _make_ip_provider(name="IP", configured=True)
        calls: list[tuple[str, IOCType]] = []

        def eligible(candidate, ioc_type: IOCType):
            calls.append((candidate.name, ioc_type))
            return candidate.name == "IP" and ioc_type == IOCType.IPV4

        monkeypatch.setattr(registry_module, "_provider_supports_configured_type", eligible)
        registry = ProviderRegistry()
        registry.register(provider)

        assert registry.provider_count_for_type(IOCType.IPV4) == 1
        assert calls == [("IP", IOCType.IPV4)]
