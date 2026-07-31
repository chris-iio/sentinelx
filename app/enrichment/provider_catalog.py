"""Static provider catalog metadata and registry order."""

from __future__ import annotations

from collections.abc import Mapping
from typing import NamedTuple
from types import MappingProxyType

from .adapters.abuseipdb import AbuseIPDBAdapter as _AbuseIPDBAdapter
from .adapters.asn_cymru import CymruASNAdapter as _CymruASNAdapter
from .adapters.crtsh import CrtShAdapter as _CrtShAdapter
from .adapters.threatminer import ThreatMinerAdapter as _ThreatMinerAdapter
from .adapters.dns_lookup import DnsAdapter as _DnsAdapter
from .adapters.emailrep import EmailRepAdapter as _EmailRepAdapter
from .adapters.whois_lookup import WhoisAdapter as _WhoisAdapter
from .adapters.greynoise import GreyNoiseAdapter as _GreyNoiseAdapter
from .adapters.hashlookup import HashlookupAdapter as _HashlookupAdapter
from .adapters.ip_api import IPApiAdapter as _IPApiAdapter
from .adapters.malwarebazaar import MBAdapter as _MBAdapter
from .adapters.otx import OTXAdapter as _OTXAdapter
from .adapters.shodan import ShodanAdapter as _ShodanAdapter
from .adapters.threatfox import TFAdapter as _TFAdapter
from .adapters.urlhaus import URLhausAdapter as _URLhausAdapter
from .adapters.virustotal import VTAdapter as _VTAdapter


__all__ = (
    "PROVIDER_REGISTRATION_PLAN",
    "PROVIDER_INFO",
    "ProviderRegistration",
    "REGISTRATION_KIND_DIRECT",
    "REGISTRATION_KIND_KEYED",
    "REGISTRATION_KIND_VIRUSTOTAL",
    "REGISTRATION_KIND_ZERO_AUTH",
    "valid_provider_ids",
)

REGISTRATION_KIND_VIRUSTOTAL = "vt"
REGISTRATION_KIND_KEYED = "keyed"
REGISTRATION_KIND_ZERO_AUTH = "zero"
REGISTRATION_KIND_DIRECT = "direct"


class ProviderRegistration(NamedTuple):
    """One provider registration step in the static registry setup plan."""

    kind: str
    provider_id: str
    adapter_cls: object


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


# Metadata for the settings page: one entry per key-requiring provider.
# Shodan InternetDB is omitted because it requires no configuration.
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
def valid_provider_ids() -> frozenset[str]:
    """Return the settings-valid provider IDs from provider metadata."""
    return frozenset((
        "virustotal",
        "malwarebazaar",
        "threatfox",
        "urlhaus",
        "otx",
        "greynoise",
        "abuseipdb",
        "emailrep",
    ))

PROVIDER_REGISTRATION_PLAN = (
    ProviderRegistration(REGISTRATION_KIND_VIRUSTOTAL, "virustotal", _VTAdapter),
    ProviderRegistration(REGISTRATION_KIND_KEYED, "malwarebazaar", _MBAdapter),
    ProviderRegistration(REGISTRATION_KIND_KEYED, "threatfox", _TFAdapter),
    ProviderRegistration(REGISTRATION_KIND_ZERO_AUTH, "shodan", _ShodanAdapter),
    ProviderRegistration(REGISTRATION_KIND_KEYED, "urlhaus", _URLhausAdapter),
    ProviderRegistration(REGISTRATION_KIND_KEYED, "otx", _OTXAdapter),
    ProviderRegistration(REGISTRATION_KIND_KEYED, "greynoise", _GreyNoiseAdapter),
    ProviderRegistration(REGISTRATION_KIND_KEYED, "abuseipdb", _AbuseIPDBAdapter),
    ProviderRegistration(REGISTRATION_KIND_KEYED, "emailrep", _EmailRepAdapter),
    ProviderRegistration(REGISTRATION_KIND_ZERO_AUTH, "hashlookup", _HashlookupAdapter),
    ProviderRegistration(REGISTRATION_KIND_ZERO_AUTH, "ip_api", _IPApiAdapter),
    ProviderRegistration(REGISTRATION_KIND_DIRECT, "dns", _DnsAdapter),
    ProviderRegistration(REGISTRATION_KIND_ZERO_AUTH, "crtsh", _CrtShAdapter),
    ProviderRegistration(REGISTRATION_KIND_ZERO_AUTH, "threatminer", _ThreatMinerAdapter),
    ProviderRegistration(REGISTRATION_KIND_DIRECT, "asn_cymru", _CymruASNAdapter),
    ProviderRegistration(REGISTRATION_KIND_DIRECT, "whois", _WhoisAdapter),
)
