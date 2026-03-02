"""Provider protocol definition for SentinelX enrichment adapters.

Defines the structural interface that all TI provider adapters must satisfy.
Using @runtime_checkable allows isinstance() checks at runtime, which is
used by ProviderRegistry to verify adapter conformance.

All adapters that implement this protocol will be auto-discoverable
by the ProviderRegistry without requiring explicit subclassing.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType


@runtime_checkable
class Provider(Protocol):
    """Structural protocol for threat intelligence provider adapters.

    Any class that provides these attributes and methods satisfies this
    protocol without needing to inherit from it explicitly. Use
    isinstance(obj, Provider) to verify conformance at runtime.

    Attributes:
        name:             Human-readable provider name (e.g., "VirusTotal").
        supported_types:  Set of IOCType values this provider can enrich.
        requires_api_key: True if the provider requires an API key to operate.

    Methods:
        lookup:        Enrich a single IOC, returning a typed result or error.
        is_configured: Return True if the provider is ready to make requests.
    """

    name: str
    supported_types: set[IOCType] | frozenset[IOCType]
    requires_api_key: bool

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        """Enrich a single IOC.

        Args:
            ioc: The IOC to look up.

        Returns:
            EnrichmentResult on success, EnrichmentError on failure.
        """
        ...

    def is_configured(self) -> bool:
        """Return True if this provider is ready to make API requests.

        For key-required providers: True only when a non-empty API key is set.
        For public providers: always True.

        Returns:
            True if the provider can be used, False otherwise.
        """
        ...
