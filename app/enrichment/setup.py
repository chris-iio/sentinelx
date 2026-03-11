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

from app.enrichment.adapters.abuseipdb import AbuseIPDBAdapter
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

# Metadata for the settings page — one entry per key-requiring provider.
# Shodan InternetDB is omitted because it requires no configuration (zero-auth).
PROVIDER_INFO: list[dict[str, str | bool]] = [
    {
        "id": "virustotal",
        "name": "VirusTotal",
        "requires_key": True,
        "signup_url": "https://www.virustotal.com/gui/join-us",
        "description": "IP, domain, URL, hash enrichment",
        "ioc_types": "IP · domain · URL · hash",
    },
    {
        "id": "malwarebazaar",
        "name": "MalwareBazaar",
        "requires_key": True,
        "signup_url": "https://auth.abuse.ch/",
        "description": "Hash only, malware sample database",
        "ioc_types": "hash",
    },
    {
        "id": "threatfox",
        "name": "ThreatFox",
        "requires_key": True,
        "signup_url": "https://auth.abuse.ch/",
        "description": "IP, domain, URL, hash, IOC sharing platform",
        "ioc_types": "IP · domain · URL · hash",
    },
    {
        "id": "urlhaus",
        "name": "URLhaus",
        "requires_key": True,
        "signup_url": "https://auth.abuse.ch/",
        "description": "URL, hash, IP, domain, malware distribution tracking",
        "ioc_types": "URL · hash · IP · domain",
    },
    {
        "id": "otx",
        "name": "OTX AlienVault",
        "requires_key": True,
        "signup_url": "https://otx.alienvault.com/api",
        "description": "All IOC types including CVE, community threat intel",
        "ioc_types": "IP · domain · URL · hash · CVE",
    },
    {
        "id": "greynoise",
        "name": "GreyNoise",
        "requires_key": True,
        "signup_url": "https://www.greynoise.io/",
        "description": "IP only, internet scanner noise classification",
        "ioc_types": "IP",
    },
    {
        "id": "abuseipdb",
        "name": "AbuseIPDB",
        "requires_key": True,
        "signup_url": "https://www.abuseipdb.com/register",
        "description": "IP only, crowd-sourced abuse reporting",
        "ioc_types": "IP",
    },
]


def build_registry(
    allowed_hosts: list[str],
    config_store: ConfigStore,
) -> ProviderRegistry:
    """Build and return a ProviderRegistry with all 10 providers registered.

    Reads API keys from ConfigStore for key-requiring providers. Zero-auth providers
    (Shodan InternetDB, CIRCL Hashlookup, ip-api.com IP Context) are registered
    unconditionally — they are always is_configured() == True.

    Registered providers:
        - VirusTotal        (requires key — via get_vt_api_key)
        - MalwareBazaar     (requires key — via get_provider_key("malwarebazaar"))
        - ThreatFox         (requires key — via get_provider_key("threatfox"))
        - Shodan InternetDB (zero-auth — no key required)
        - URLhaus           (requires key — via get_provider_key("urlhaus"))
        - OTX AlienVault    (requires key — via get_provider_key("otx"))
        - GreyNoise         (requires key — via get_provider_key("greynoise"))
        - AbuseIPDB         (requires key — via get_provider_key("abuseipdb"))
        - CIRCL Hashlookup  (zero-auth — NSRL known-good hash detection)
        - IP Context        (zero-auth — GeoIP/rDNS/proxy flags via ip-api.com)

    Args:
        allowed_hosts: SSRF allowlist passed to each adapter for outbound calls.
        config_store: ConfigStore instance used to read provider API keys.

    Returns:
        ProviderRegistry with all 10 providers registered.
    """
    registry = ProviderRegistry()

    vt_key = config_store.get_vt_api_key() or ""
    registry.register(VTAdapter(api_key=vt_key, allowed_hosts=allowed_hosts))

    mb_key = config_store.get_provider_key("malwarebazaar") or ""
    registry.register(MBAdapter(api_key=mb_key, allowed_hosts=allowed_hosts))

    tf_key = config_store.get_provider_key("threatfox") or ""
    registry.register(TFAdapter(api_key=tf_key, allowed_hosts=allowed_hosts))
    registry.register(ShodanAdapter(allowed_hosts=allowed_hosts))

    urlhaus_key = config_store.get_provider_key("urlhaus") or ""
    registry.register(URLhausAdapter(api_key=urlhaus_key, allowed_hosts=allowed_hosts))

    otx_key = config_store.get_provider_key("otx") or ""
    registry.register(OTXAdapter(api_key=otx_key, allowed_hosts=allowed_hosts))

    gn_key = config_store.get_provider_key("greynoise") or ""
    registry.register(GreyNoiseAdapter(api_key=gn_key, allowed_hosts=allowed_hosts))

    abuseipdb_key = config_store.get_provider_key("abuseipdb") or ""
    registry.register(AbuseIPDBAdapter(api_key=abuseipdb_key, allowed_hosts=allowed_hosts))

    # Zero-auth providers — no key needed, always configured
    registry.register(HashlookupAdapter(allowed_hosts=allowed_hosts))
    registry.register(IPApiAdapter(allowed_hosts=allowed_hosts))

    return registry
