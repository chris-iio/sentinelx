"""Provider setup factory — single registration point for all enrichment providers.

This module is the ONLY place where adapter classes are imported and registered.
To add a new provider: create an adapter in app/enrichment/adapters/, then add
one register() call here. No other files need to change.

Usage:
    from app.enrichment.setup import build_registry
    registry = build_registry(allowed_hosts=ALLOWED_HOSTS, config_store=store)
    providers = registry.providers_for_type(ioc.type)
"""
from __future__ import annotations

from app.enrichment.adapters.malwarebazaar import MBAdapter
from app.enrichment.adapters.shodan import ShodanAdapter
from app.enrichment.adapters.threatfox import TFAdapter
from app.enrichment.adapters.virustotal import VTAdapter
from app.enrichment.config_store import ConfigStore
from app.enrichment.registry import ProviderRegistry


def build_registry(
    allowed_hosts: list[str],
    config_store: ConfigStore,
) -> ProviderRegistry:
    """Build and return a ProviderRegistry with all providers registered.

    Reads the VirusTotal API key from ConfigStore. Public providers
    (MalwareBazaar, ThreatFox) are registered unconditionally — they are
    always is_configured() == True.

    Args:
        allowed_hosts: SSRF allowlist passed to each adapter for outbound calls.
        config_store: ConfigStore instance used to read provider API keys.

    Returns:
        ProviderRegistry with VTAdapter, MBAdapter, TFAdapter, and ShodanAdapter registered.
    """
    registry = ProviderRegistry()

    vt_key = config_store.get_vt_api_key() or ""

    registry.register(VTAdapter(api_key=vt_key, allowed_hosts=allowed_hosts))
    registry.register(MBAdapter(allowed_hosts=allowed_hosts))
    registry.register(TFAdapter(allowed_hosts=allowed_hosts))
    registry.register(ShodanAdapter(allowed_hosts=allowed_hosts))

    return registry
