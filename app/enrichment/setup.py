"""Provider setup factory: build the enrichment provider registry.

Static provider metadata and registration order live in provider_catalog. This
module owns runtime config reads, allowed-host snapshotting, and provider
construction.

Usage:
    from app.enrichment.setup import build_registry
    registry = build_registry(allowed_hosts=ALLOWED_HOSTS, config_store=store)
    providers = registry.providers_for_type(ioc.type)
"""
from __future__ import annotations

from collections.abc import Collection

from .adapters.base import _allowed_hosts_membership
from .config_store import ConfigStore
from .provider_catalog import (
    PROVIDER_REGISTRATION_PLAN,
    REGISTRATION_KIND_DIRECT,
    REGISTRATION_KIND_KEYED,
    REGISTRATION_KIND_VIRUSTOTAL,
    REGISTRATION_KIND_ZERO_AUTH,
    ProviderRegistration,
)
from .registry import ProviderRegistry


def _get_provider_keys(config_store: ConfigStore) -> dict[str, str]:
    """Return provider API keys, treating local config read failures as missing."""
    try:
        return config_store.all_provider_keys()
    except Exception:
        return {}


def _provider_key_or_empty(provider_keys: dict[str, str], provider_id: str) -> str:
    """Return a provider API key from a preloaded provider-key map."""
    return provider_keys.get(provider_id) or ""


def _register_keyed_provider(
    registry: ProviderRegistry,
    adapter_cls,
    provider_keys: dict[str, str],
    provider_id: str,
    allowed_hosts: Collection[str],
) -> None:
    """Register a key-requiring provider from the preloaded provider-key map."""
    api_key = _provider_key_or_empty(provider_keys, provider_id)
    registry.register(adapter_cls(api_key=api_key, allowed_hosts=allowed_hosts))


def _register_zero_auth_provider(
    registry: ProviderRegistry,
    adapter_cls,
    allowed_hosts: Collection[str],
) -> None:
    """Register a zero-auth HTTP provider that still needs SSRF allowlist state."""
    registry.register(adapter_cls(allowed_hosts=allowed_hosts))


def _register_direct_provider(registry: ProviderRegistry, adapter_cls) -> None:
    """Register a zero-auth non-HTTP provider with no unused allowlist argument."""
    registry.register(adapter_cls())


def _register_provider_from_plan(
    registry: ProviderRegistry,
    registration: ProviderRegistration,
    provider_keys: dict[str, str],
    vt_key: str,
    allowed_hosts: Collection[str],
) -> None:
    if registration.kind == REGISTRATION_KIND_VIRUSTOTAL:
        registry.register(
            registration.adapter_cls(api_key=vt_key, allowed_hosts=allowed_hosts)
        )
        return
    if registration.kind == REGISTRATION_KIND_KEYED:
        _register_keyed_provider(
            registry,
            registration.adapter_cls,
            provider_keys,
            registration.provider_id,
            allowed_hosts,
        )
        return
    if registration.kind == REGISTRATION_KIND_ZERO_AUTH:
        _register_zero_auth_provider(registry, registration.adapter_cls, allowed_hosts)
        return
    if registration.kind == REGISTRATION_KIND_DIRECT:
        _register_direct_provider(registry, registration.adapter_cls)
        return
    raise ValueError(f"Unknown provider registration kind: {registration.kind}")


def build_registry(
    allowed_hosts: list[str],
    config_store: ConfigStore,
) -> ProviderRegistry:
    """Build and return a ProviderRegistry with all 16 providers registered.

    Reads API keys from ConfigStore for key-requiring providers. Zero-auth providers
    (Shodan InternetDB, CIRCL Hashlookup, ipinfo.io IP Context, DNS Records,
    Cert History, ThreatMiner, ASN Intel, WHOIS) are registered unconditionally —
    they are always is_configured() == True.

    Registered providers:
        - VirusTotal        (requires key — via get_vt_api_key)
        - MalwareBazaar     (requires key — via provider-key map)
        - ThreatFox         (requires key — via provider-key map)
        - Shodan InternetDB (zero-auth — no key required)
        - URLhaus           (requires key — via provider-key map)
        - OTX AlienVault    (requires key — via provider-key map)
        - GreyNoise         (requires key — via provider-key map)
        - AbuseIPDB         (requires key — via provider-key map)
        - EmailRep          (requires key — via provider-key map)
        - CIRCL Hashlookup  (zero-auth — NSRL known-good hash detection)
        - IP Context        (zero-auth — GeoIP/rDNS via ipinfo.io)
        - DNS Records       (zero-auth — live DNS resolution via dnspython)
        - Cert History      (zero-auth — certificate transparency via crt.sh)
        - ThreatMiner       (zero-auth — passive DNS and related samples via ThreatMiner)
        - ASN Intel         (zero-auth — ASN/BGP context via Team Cymru DNS mapping)
        - WHOIS             (zero-auth — domain registration data via python-whois)

    Args:
        allowed_hosts: SSRF allowlist passed to each adapter for outbound calls.
        config_store: ConfigStore instance used to read provider API keys.

    Returns:
        ProviderRegistry with all 16 providers registered.
    """
    registry = ProviderRegistry()

    allowed_host_membership = _allowed_hosts_membership(allowed_hosts)
    vt_key = config_store.get_vt_api_key() or ""
    provider_keys = _get_provider_keys(config_store)

    for registration in PROVIDER_REGISTRATION_PLAN:
        _register_provider_from_plan(
            registry,
            registration,
            provider_keys,
            vt_key,
            allowed_host_membership,
        )

    return registry
