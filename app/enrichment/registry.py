"""ProviderRegistry — central registry for threat intelligence provider adapters.

Providers are registered once at startup (via setup.py) and can be looked up
by IOC type or configuration status. The registry is the single source of truth
for which providers are available and which are ready to accept requests.

Usage:
    registry = ProviderRegistry()
    registry.register(VTAdapter(api_key="...", allowed_hosts=ALLOWED_HOSTS))
    registry.register(MBAdapter(allowed_hosts=ALLOWED_HOSTS))

    # Get only configured providers that support IPv4 enrichment
    providers = registry.providers_for_type(IOCType.IPV4)
"""
from __future__ import annotations

from .provider import Provider
from app.pipeline.models import IOCType


def _provider_supports_configured_type(provider: Provider, ioc_type: IOCType) -> bool:
    return provider.is_configured() and ioc_type in provider.supported_types


def append_registered_provider(
    providers: list[Provider],
    registry: dict[str, Provider],
    name: str,
) -> None:
    """Append one provider from the registry map."""
    providers.append(registry[name])


def append_configured_provider(providers: list[Provider], provider: Provider) -> None:
    """Append a provider when it is configured."""
    if provider.is_configured():
        providers.append(provider)


def increment_configured_provider_count(count: int, provider: Provider) -> int:
    """Return the updated configured-provider count."""
    if provider.is_configured():
        return count + 1
    return count


def append_provider_for_type(
    providers: list[Provider],
    provider: Provider,
    ioc_type: IOCType,
) -> None:
    """Append a provider when it is configured and supports the IOC type."""
    if _provider_supports_configured_type(provider, ioc_type):
        providers.append(provider)


def increment_provider_type_count(
    count: int,
    provider: Provider,
    ioc_type: IOCType,
) -> int:
    """Return the updated count for configured providers supporting an IOC type."""
    if _provider_supports_configured_type(provider, ioc_type):
        return count + 1
    return count


class ProviderRegistry:
    """Central registry for threat intelligence provider adapters.

    Providers are stored by name. Registration fails if a provider with the
    same name is already registered (prevents accidental double-registration).

    All query methods filter by configuration status — unconfigured providers
    (those where is_configured() returns False) are excluded from results that
    would trigger actual API requests.
    """

    def __init__(self) -> None:
        self._providers: dict[str, Provider] = {}

    def register(self, provider: Provider) -> None:
        """Register a provider adapter.

        Args:
            provider: Any object satisfying the Provider protocol.

        Raises:
            ValueError: If a provider with the same name is already registered.
        """
        if provider.name in self._providers:
            raise ValueError(
                f"Provider '{provider.name}' is already registered. "
                "Each provider name must be unique."
            )
        self._providers[provider.name] = provider

    def all(self) -> list[Provider]:
        """Return all registered providers regardless of configuration status.

        Returns a new list — callers may mutate the list without affecting
        registry state.

        Returns:
            List of all registered Provider objects.
        """
        if not self._providers:
            return []

        providers: list[Provider] = []
        for name in self._providers:
            append_registered_provider(providers, self._providers, name)
        return providers

    def registered_count(self) -> int:
        """Return the number of registered providers without copying them."""
        return len(self._providers)

    def configured(self) -> list[Provider]:
        """Return providers that are ready to make API requests.

        Filters by is_configured() — only providers that return True are
        included. Unconfigured providers (e.g., missing API key) are excluded.

        Returns:
            List of configured Provider objects.
        """
        if not self._providers:
            return []

        providers: list[Provider] = []
        for name in self._providers:
            append_configured_provider(providers, self._providers[name])
        return providers

    def configured_count(self) -> int:
        """Return the number of configured providers without copying them."""
        if not self._providers:
            return 0

        count = 0
        for name in self._providers:
            count = increment_configured_provider_count(count, self._providers[name])
        return count

    def providers_for_type(self, ioc_type: IOCType) -> list[Provider]:
        """Return configured providers that support the given IOC type.

        Combines configuration filter with type support filter. A provider
        must be both configured (is_configured() == True) and support the
        given IOC type (ioc_type in provider.supported_types) to be included.

        Args:
            ioc_type: The IOC type to look up providers for.

        Returns:
            List of configured providers that can enrich this IOC type.
        """
        if not self._providers:
            return []

        providers: list[Provider] = []
        for name in self._providers:
            append_provider_for_type(providers, self._providers[name], ioc_type)
        return providers

    def provider_count_for_type(self, ioc_type: IOCType) -> int:
        """Return number of configured providers supporting the given IOC type.

        Convenience method — equivalent to len(providers_for_type(ioc_type)).

        Args:
            ioc_type: The IOC type to count providers for.

        Returns:
            Count of configured providers that can enrich this IOC type.
        """
        if not self._providers:
            return 0

        count = 0
        for name in self._providers:
            provider = self._providers[name]
            count = increment_provider_type_count(count, provider, ioc_type)
        return count
