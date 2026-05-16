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

from collections.abc import Collection, Mapping
from types import MappingProxyType

from app.enrichment.adapters.abuseipdb import AbuseIPDBAdapter
from app.enrichment.adapters.asn_cymru import CymruASNAdapter
from app.enrichment.adapters.base import _allowed_hosts_membership
from app.enrichment.adapters.crtsh import CrtShAdapter
from app.enrichment.adapters.threatminer import ThreatMinerAdapter
from app.enrichment.adapters.dns_lookup import DnsAdapter
from app.enrichment.adapters.emailrep import EmailRepAdapter
from app.enrichment.adapters.whois_lookup import WhoisAdapter
from app.enrichment.adapters.greynoise import GreyNoiseAdapter
from app.enrichment.adapters.hashlookup import HashlookupAdapter
from app.enrichment.adapters.ip_api import IPApiAdapter
from app.enrichment.adapters.malwarebazaar import MBAdapter
from app.enrichment.adapters.otx import OTXAdapter
from app.enrichment.adapters.shodan import ShodanAdapter
from app.enrichment.adapters.threatfox import TFAdapter
from app.enrichment.adapters.urlhaus import URLhausAdapter
from app.enrichment.adapters.virustotal import VTAdapter
from app.enrichment.config_store import ConfigStore
from app.enrichment.registry import ProviderRegistry


def _provider_info(
    *,
    provider_id: str,
    name: str,
    signup_url: str,
    description: str,
    ioc_types: str,
) -> Mapping[str, str | bool]:
    """Return one immutable settings metadata entry."""
    return MappingProxyType(
        {
            "id": provider_id,
            "name": name,
            "requires_key": True,
            "signup_url": signup_url,
            "description": description,
            "ioc_types": ioc_types,
        }
    )


# Metadata for the settings page — one entry per key-requiring provider.
# Shodan InternetDB is omitted because it requires no configuration (zero-auth).
PROVIDER_INFO: tuple[Mapping[str, str | bool], ...] = (
    _provider_info(
        provider_id="virustotal",
        name="VirusTotal",
        signup_url="https://www.virustotal.com/gui/join-us",
        description="IP, domain, URL, hash enrichment",
        ioc_types="IP · domain · URL · hash",
    ),
    _provider_info(
        provider_id="malwarebazaar",
        name="MalwareBazaar",
        signup_url="https://auth.abuse.ch/",
        description="Hash only, malware sample database",
        ioc_types="hash",
    ),
    _provider_info(
        provider_id="threatfox",
        name="ThreatFox",
        signup_url="https://auth.abuse.ch/",
        description="IP, domain, URL, hash, IOC sharing platform",
        ioc_types="IP · domain · URL · hash",
    ),
    _provider_info(
        provider_id="urlhaus",
        name="URLhaus",
        signup_url="https://auth.abuse.ch/",
        description="URL, hash, IP, domain, malware distribution tracking",
        ioc_types="URL · hash · IP · domain",
    ),
    _provider_info(
        provider_id="otx",
        name="OTX AlienVault",
        signup_url="https://otx.alienvault.com/api",
        description="All IOC types including CVE, community threat intel",
        ioc_types="IP · domain · URL · hash · CVE",
    ),
    _provider_info(
        provider_id="greynoise",
        name="GreyNoise",
        signup_url="https://www.greynoise.io/",
        description="IP only, internet scanner noise classification",
        ioc_types="IP",
    ),
    _provider_info(
        provider_id="abuseipdb",
        name="AbuseIPDB",
        signup_url="https://www.abuseipdb.com/register",
        description="IP only, crowd-sourced abuse reporting",
        ioc_types="IP",
    ),
    _provider_info(
        provider_id="emailrep",
        name="EmailRep",
        signup_url="https://emailrep.io/key",
        description="Email only, reputation and account-risk signals",
        ioc_types="email",
    ),
)
PROVIDER_IDS = (
    "virustotal",
    "malwarebazaar",
    "threatfox",
    "urlhaus",
    "otx",
    "greynoise",
    "abuseipdb",
    "emailrep",
)

_PRE_SHODAN_KEYED_PROVIDER_REGISTRATIONS = (
    ("malwarebazaar", MBAdapter),
    ("threatfox", TFAdapter),
)

_POST_SHODAN_KEYED_PROVIDER_REGISTRATIONS = (
    ("urlhaus", URLhausAdapter),
    ("otx", OTXAdapter),
    ("greynoise", GreyNoiseAdapter),
    ("abuseipdb", AbuseIPDBAdapter),
    ("emailrep", EmailRepAdapter),
)

_ZERO_AUTH_PROVIDER_CLASSES = (
    HashlookupAdapter,
    IPApiAdapter,
    DnsAdapter,
    CrtShAdapter,
    ThreatMinerAdapter,
    CymruASNAdapter,
    WhoisAdapter,
)


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
    """Register a provider that needs no API key."""
    registry.register(adapter_cls(allowed_hosts=allowed_hosts))


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

    registry.register(VTAdapter(api_key=vt_key, allowed_hosts=allowed_host_membership))

    for provider_id, adapter_cls in _PRE_SHODAN_KEYED_PROVIDER_REGISTRATIONS:
        _register_keyed_provider(
            registry,
            adapter_cls,
            provider_keys,
            provider_id,
            allowed_host_membership,
        )

    registry.register(ShodanAdapter(allowed_hosts=allowed_host_membership))

    for provider_id, adapter_cls in _POST_SHODAN_KEYED_PROVIDER_REGISTRATIONS:
        _register_keyed_provider(
            registry,
            adapter_cls,
            provider_keys,
            provider_id,
            allowed_host_membership,
        )

    # Zero-auth providers — no key needed, always configured
    for adapter_cls in _ZERO_AUTH_PROVIDER_CLASSES:
        _register_zero_auth_provider(registry, adapter_cls, allowed_host_membership)

    return registry
