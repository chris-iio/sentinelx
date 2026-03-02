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

from app.enrichment.provider import Provider
from app.pipeline.models import IOCType


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
        return list(self._providers.values())

    def configured(self) -> list[Provider]:
        """Return providers that are ready to make API requests.

        Filters by is_configured() — only providers that return True are
        included. Unconfigured providers (e.g., missing API key) are excluded.

        Returns:
            List of configured Provider objects.
        """
        return [p for p in self._providers.values() if p.is_configured()]

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
        return [
            p for p in self._providers.values()
            if p.is_configured() and ioc_type in p.supported_types
        ]

    def provider_count_for_type(self, ioc_type: IOCType) -> int:
        """Return number of configured providers supporting the given IOC type.

        Convenience method — equivalent to len(providers_for_type(ioc_type)).

        Args:
            ioc_type: The IOC type to count providers for.

        Returns:
            Count of configured providers that can enrich this IOC type.
        """
        return len(self.providers_for_type(ioc_type))
