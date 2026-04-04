"""Shared parametrized adapter contract tests.

Covers protocol conformance, error handling, type guards, and safety controls
once for all 15 adapters.  Per-adapter test files retain only verdict/parsing
tests.

Usage:
    python3 -m pytest tests/test_adapter_contract.py -v
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
from unittest.mock import MagicMock

import pytest
import requests.exceptions

from app.config import Config
from app.enrichment.adapters.abuseipdb import AbuseIPDBAdapter
from app.enrichment.adapters.asn_cymru import CymruASNAdapter
from app.enrichment.adapters.crtsh import CrtShAdapter
from app.enrichment.adapters.dns_lookup import DnsAdapter
from app.enrichment.adapters.greynoise import GreyNoiseAdapter
from app.enrichment.adapters.hashlookup import HashlookupAdapter
from app.enrichment.adapters.ip_api import IPApiAdapter
from app.enrichment.adapters.malwarebazaar import MBAdapter
from app.enrichment.adapters.otx import OTXAdapter
from app.enrichment.adapters.shodan import ShodanAdapter
from app.enrichment.adapters.threatfox import TFAdapter
from app.enrichment.adapters.threatminer import ThreatMinerAdapter
from app.enrichment.adapters.urlhaus import URLhausAdapter
from app.enrichment.adapters.virustotal import VTAdapter
from app.enrichment.adapters.whois_lookup import WhoisAdapter
from app.enrichment.http_safety import MAX_RESPONSE_BYTES
from app.enrichment.models import EnrichmentError
from app.enrichment.provider import Provider
from app.pipeline.models import IOC, IOCType
from tests.helpers import (
    make_domain_ioc,
    make_ipv4_ioc,
    make_md5_ioc,
    make_sha256_ioc,
    make_url_ioc,
    mock_adapter_session,
)


# ---------------------------------------------------------------------------
# Registry of all 15 adapters with expected contract values
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AdapterEntry:
    """One entry in the adapter registry — captures contract expectations."""

    adapter_class: type
    constructor_kwargs: dict = field(default_factory=dict)
    name: str = ""
    requires_api_key: bool = False
    supported_types: frozenset = field(default_factory=frozenset)
    excluded_types: list = field(default_factory=list)
    http_method: str | None = None  # 'get' or 'post'; None for non-HTTP
    is_http: bool = True
    allowed_hosts_config_entry: str | None = None
    sample_ioc_factory: Callable[[], IOC] = make_ipv4_ioc


# All 9 IOC types for computing excluded_types conveniently
_ALL_TYPES = frozenset(IOCType)


def _excluded(supported: frozenset[IOCType]) -> list[IOCType]:
    """Return types NOT in the supported set."""
    return sorted(_ALL_TYPES - supported, key=lambda t: t.value)


# --- HTTP adapter entries (12) -----------------------------------------------

_SHODAN = AdapterEntry(
    adapter_class=ShodanAdapter,
    constructor_kwargs={"allowed_hosts": ["internetdb.shodan.io"]},
    name="Shodan InternetDB",
    requires_api_key=False,
    supported_types=frozenset({IOCType.IPV4, IOCType.IPV6}),
    excluded_types=_excluded(frozenset({IOCType.IPV4, IOCType.IPV6})),
    http_method="get",
    is_http=True,
    allowed_hosts_config_entry="internetdb.shodan.io",
    sample_ioc_factory=make_ipv4_ioc,
)

_ABUSEIPDB = AdapterEntry(
    adapter_class=AbuseIPDBAdapter,
    constructor_kwargs={"allowed_hosts": ["api.abuseipdb.com"], "api_key": "test-key"},
    name="AbuseIPDB",
    requires_api_key=True,
    supported_types=frozenset({IOCType.IPV4, IOCType.IPV6}),
    excluded_types=_excluded(frozenset({IOCType.IPV4, IOCType.IPV6})),
    http_method="get",
    is_http=True,
    allowed_hosts_config_entry="api.abuseipdb.com",
    sample_ioc_factory=make_ipv4_ioc,
)

_GREYNOISE = AdapterEntry(
    adapter_class=GreyNoiseAdapter,
    constructor_kwargs={"allowed_hosts": ["api.greynoise.io"], "api_key": "test-key"},
    name="GreyNoise",
    requires_api_key=True,
    supported_types=frozenset({IOCType.IPV4, IOCType.IPV6}),
    excluded_types=_excluded(frozenset({IOCType.IPV4, IOCType.IPV6})),
    http_method="get",
    is_http=True,
    allowed_hosts_config_entry="api.greynoise.io",
    sample_ioc_factory=make_ipv4_ioc,
)

_HASHLOOKUP = AdapterEntry(
    adapter_class=HashlookupAdapter,
    constructor_kwargs={"allowed_hosts": ["hashlookup.circl.lu"]},
    name="CIRCL Hashlookup",
    requires_api_key=False,
    supported_types=frozenset({IOCType.MD5, IOCType.SHA1, IOCType.SHA256}),
    excluded_types=_excluded(frozenset({IOCType.MD5, IOCType.SHA1, IOCType.SHA256})),
    http_method="get",
    is_http=True,
    allowed_hosts_config_entry="hashlookup.circl.lu",
    sample_ioc_factory=make_md5_ioc,
)

_IP_API = AdapterEntry(
    adapter_class=IPApiAdapter,
    constructor_kwargs={"allowed_hosts": ["ipinfo.io"]},
    name="IP Context",
    requires_api_key=False,
    supported_types=frozenset({IOCType.IPV4, IOCType.IPV6}),
    excluded_types=_excluded(frozenset({IOCType.IPV4, IOCType.IPV6})),
    http_method="get",
    is_http=True,
    allowed_hosts_config_entry="ipinfo.io",
    sample_ioc_factory=make_ipv4_ioc,
)

_OTX = AdapterEntry(
    adapter_class=OTXAdapter,
    constructor_kwargs={"allowed_hosts": ["otx.alienvault.com"], "api_key": "test-key"},
    name="OTX AlienVault",
    requires_api_key=True,
    supported_types=frozenset({
        IOCType.IPV4, IOCType.IPV6, IOCType.DOMAIN, IOCType.URL,
        IOCType.MD5, IOCType.SHA1, IOCType.SHA256, IOCType.CVE,
    }),
    excluded_types=[IOCType.EMAIL],
    http_method="get",
    is_http=True,
    allowed_hosts_config_entry="otx.alienvault.com",
    sample_ioc_factory=make_ipv4_ioc,
)

_MALWAREBAZAAR = AdapterEntry(
    adapter_class=MBAdapter,
    constructor_kwargs={"allowed_hosts": ["mb-api.abuse.ch"], "api_key": "test-key"},
    name="MalwareBazaar",
    requires_api_key=True,
    supported_types=frozenset({IOCType.MD5, IOCType.SHA1, IOCType.SHA256}),
    excluded_types=_excluded(frozenset({IOCType.MD5, IOCType.SHA1, IOCType.SHA256})),
    http_method="post",
    is_http=True,
    allowed_hosts_config_entry="mb-api.abuse.ch",
    sample_ioc_factory=make_md5_ioc,
)

_THREATFOX = AdapterEntry(
    adapter_class=TFAdapter,
    constructor_kwargs={"allowed_hosts": ["threatfox-api.abuse.ch"], "api_key": "test-key"},
    name="ThreatFox",
    requires_api_key=True,
    supported_types=frozenset({
        IOCType.MD5, IOCType.SHA1, IOCType.SHA256,
        IOCType.DOMAIN, IOCType.IPV4, IOCType.IPV6, IOCType.URL,
    }),
    excluded_types=[IOCType.CVE, IOCType.EMAIL],
    http_method="post",
    is_http=True,
    allowed_hosts_config_entry="threatfox-api.abuse.ch",
    sample_ioc_factory=make_md5_ioc,
)

_URLHAUS = AdapterEntry(
    adapter_class=URLhausAdapter,
    constructor_kwargs={"allowed_hosts": ["urlhaus-api.abuse.ch"], "api_key": "test-key"},
    name="URLhaus",
    requires_api_key=True,
    supported_types=frozenset({
        IOCType.URL, IOCType.IPV4, IOCType.IPV6, IOCType.DOMAIN,
        IOCType.MD5, IOCType.SHA256,
    }),
    excluded_types=[IOCType.SHA1, IOCType.CVE, IOCType.EMAIL],
    http_method="post",
    is_http=True,
    allowed_hosts_config_entry="urlhaus-api.abuse.ch",
    sample_ioc_factory=make_url_ioc,
)

_CRTSH = AdapterEntry(
    adapter_class=CrtShAdapter,
    constructor_kwargs={"allowed_hosts": ["crt.sh"]},
    name="Cert History",
    requires_api_key=False,
    supported_types=frozenset({IOCType.DOMAIN}),
    excluded_types=_excluded(frozenset({IOCType.DOMAIN})),
    http_method="get",
    is_http=True,
    allowed_hosts_config_entry="crt.sh",
    sample_ioc_factory=make_domain_ioc,
)

_VIRUSTOTAL = AdapterEntry(
    adapter_class=VTAdapter,
    constructor_kwargs={"allowed_hosts": ["www.virustotal.com"], "api_key": "test-key"},
    name="VirusTotal",
    requires_api_key=True,
    supported_types=frozenset({
        IOCType.IPV4, IOCType.IPV6, IOCType.DOMAIN, IOCType.URL,
        IOCType.MD5, IOCType.SHA1, IOCType.SHA256,
    }),
    excluded_types=[IOCType.CVE, IOCType.EMAIL],
    http_method="get",
    is_http=True,
    allowed_hosts_config_entry="www.virustotal.com",
    sample_ioc_factory=make_ipv4_ioc,
)

_THREATMINER = AdapterEntry(
    adapter_class=ThreatMinerAdapter,
    constructor_kwargs={"allowed_hosts": ["api.threatminer.org"]},
    name="ThreatMiner",
    requires_api_key=False,
    supported_types=frozenset({
        IOCType.IPV4, IOCType.IPV6, IOCType.DOMAIN,
        IOCType.MD5, IOCType.SHA1, IOCType.SHA256,
    }),
    excluded_types=[IOCType.URL, IOCType.CVE, IOCType.EMAIL],
    http_method="get",
    is_http=True,
    allowed_hosts_config_entry="api.threatminer.org",
    sample_ioc_factory=make_ipv4_ioc,
)

# --- Non-HTTP adapter entries (3) --------------------------------------------

_DNS = AdapterEntry(
    adapter_class=DnsAdapter,
    constructor_kwargs={"allowed_hosts": []},
    name="DNS Records",
    requires_api_key=False,
    supported_types=frozenset({IOCType.DOMAIN}),
    excluded_types=_excluded(frozenset({IOCType.DOMAIN})),
    http_method=None,
    is_http=False,
    allowed_hosts_config_entry=None,
    sample_ioc_factory=make_domain_ioc,
)

_ASN_CYMRU = AdapterEntry(
    adapter_class=CymruASNAdapter,
    constructor_kwargs={"allowed_hosts": []},
    name="ASN Intel",
    requires_api_key=False,
    supported_types=frozenset({IOCType.IPV4, IOCType.IPV6}),
    excluded_types=_excluded(frozenset({IOCType.IPV4, IOCType.IPV6})),
    http_method=None,
    is_http=False,
    allowed_hosts_config_entry=None,
    sample_ioc_factory=make_ipv4_ioc,
)

_WHOIS = AdapterEntry(
    adapter_class=WhoisAdapter,
    constructor_kwargs={"allowed_hosts": []},
    name="WHOIS",
    requires_api_key=False,
    supported_types=frozenset({IOCType.DOMAIN}),
    excluded_types=_excluded(frozenset({IOCType.DOMAIN})),
    http_method=None,
    is_http=False,
    allowed_hosts_config_entry=None,
    sample_ioc_factory=make_domain_ioc,
)

# --- Aggregate registries ----------------------------------------------------

ADAPTER_REGISTRY: list[AdapterEntry] = [
    _SHODAN, _ABUSEIPDB, _GREYNOISE, _HASHLOOKUP, _IP_API, _OTX,
    _MALWAREBAZAAR, _THREATFOX, _URLHAUS, _CRTSH, _VIRUSTOTAL, _THREATMINER,
    _DNS, _ASN_CYMRU, _WHOIS,
]

HTTP_ADAPTERS: list[AdapterEntry] = [e for e in ADAPTER_REGISTRY if e.is_http]

ADAPTERS_WITH_CONFIG_HOSTS: list[AdapterEntry] = [
    e for e in ADAPTER_REGISTRY if e.allowed_hosts_config_entry is not None
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_adapter(entry: AdapterEntry):
    """Instantiate an adapter from its registry entry."""
    return entry.adapter_class(**entry.constructor_kwargs)


def _ioc_for_type(ioc_type: IOCType) -> IOC:
    """Build a representative IOC of the given type."""
    _FACTORIES = {
        IOCType.IPV4: lambda: IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4"),
        IOCType.IPV6: lambda: IOC(type=IOCType.IPV6, value="2001:db8::1", raw_match="2001:db8::1"),
        IOCType.DOMAIN: lambda: IOC(type=IOCType.DOMAIN, value="evil.com", raw_match="evil.com"),
        IOCType.URL: lambda: IOC(type=IOCType.URL, value="http://evil.com/path", raw_match="http://evil.com/path"),
        IOCType.MD5: lambda: IOC(type=IOCType.MD5, value="d41d8cd98f00b204e9800998ecf8427e", raw_match="d41d8cd98f00b204e9800998ecf8427e"),
        IOCType.SHA1: lambda: IOC(type=IOCType.SHA1, value="b" * 40, raw_match="b" * 40),
        IOCType.SHA256: lambda: IOC(type=IOCType.SHA256, value="abc123def456", raw_match="abc123def456"),
        IOCType.CVE: lambda: IOC(type=IOCType.CVE, value="CVE-2021-44228", raw_match="CVE-2021-44228"),
        IOCType.EMAIL: lambda: IOC(type=IOCType.EMAIL, value="user@evil.com", raw_match="user@evil.com"),
    }
    return _FACTORIES[ioc_type]()


def _adapter_id(entry: AdapterEntry) -> str:
    """Generate a pytest ID from the entry name."""
    return entry.name.lower().replace(" ", "-")


# ---------------------------------------------------------------------------
# Parametrize helpers
# ---------------------------------------------------------------------------

_all_ids = [_adapter_id(e) for e in ADAPTER_REGISTRY]
_http_ids = [_adapter_id(e) for e in HTTP_ADAPTERS]
_config_ids = [_adapter_id(e) for e in ADAPTERS_WITH_CONFIG_HOSTS]


# ---------------------------------------------------------------------------
# 1. Protocol conformance (all 15)
# ---------------------------------------------------------------------------

class TestProtocolConformance:

    @pytest.mark.parametrize("entry", ADAPTER_REGISTRY, ids=_all_ids)
    def test_isinstance_provider(self, entry: AdapterEntry) -> None:
        adapter = _make_adapter(entry)
        assert isinstance(adapter, Provider), (
            f"{entry.adapter_class.__name__} must satisfy the Provider protocol"
        )


# ---------------------------------------------------------------------------
# 1b. Protocol negative tests — non-conforming classes rejected
# ---------------------------------------------------------------------------

class TestProtocolNegative:

    def test_non_conforming_class_fails_isinstance(self) -> None:
        """A class missing the `name` attribute does not satisfy Provider."""
        class MissingName:
            supported_types = {IOCType.IPV4}
            requires_api_key = False

            def lookup(self, ioc):
                pass

            def is_configured(self) -> bool:
                return True

        obj = MissingName()
        assert not isinstance(obj, Provider), (
            "class missing 'name' must not satisfy the Provider protocol"
        )

    def test_non_conforming_class_missing_lookup_fails(self) -> None:
        """A class missing the `lookup` method does not satisfy Provider."""
        class MissingLookup:
            name = "Test"
            supported_types = {IOCType.IPV4}
            requires_api_key = False

            def is_configured(self) -> bool:
                return True

        obj = MissingLookup()
        assert not isinstance(obj, Provider), (
            "class missing 'lookup' must not satisfy the Provider protocol"
        )


# ---------------------------------------------------------------------------
# 2. Adapter name (all 15)
# ---------------------------------------------------------------------------

class TestAdapterName:

    @pytest.mark.parametrize("entry", ADAPTER_REGISTRY, ids=_all_ids)
    def test_name_matches(self, entry: AdapterEntry) -> None:
        adapter = _make_adapter(entry)
        assert adapter.name == entry.name


# ---------------------------------------------------------------------------
# 3. requires_api_key (all 15)
# ---------------------------------------------------------------------------

class TestRequiresApiKey:

    @pytest.mark.parametrize("entry", ADAPTER_REGISTRY, ids=_all_ids)
    def test_requires_api_key_matches(self, entry: AdapterEntry) -> None:
        adapter = _make_adapter(entry)
        assert adapter.requires_api_key is entry.requires_api_key


# ---------------------------------------------------------------------------
# 4. is_configured (all 15)
# ---------------------------------------------------------------------------

class TestIsConfigured:

    @pytest.mark.parametrize("entry", ADAPTER_REGISTRY, ids=_all_ids)
    def test_configured_when_key_provided_or_not_needed(self, entry: AdapterEntry) -> None:
        """Adapter is configured when api_key is provided (or not required)."""
        adapter = _make_adapter(entry)
        assert adapter.is_configured() is True

    @pytest.mark.parametrize(
        "entry",
        [e for e in ADAPTER_REGISTRY if e.requires_api_key],
        ids=[_adapter_id(e) for e in ADAPTER_REGISTRY if e.requires_api_key],
    )
    def test_not_configured_when_key_missing(self, entry: AdapterEntry) -> None:
        """Adapter with requires_api_key=True and empty key -> not configured."""
        kwargs = dict(entry.constructor_kwargs)
        kwargs["api_key"] = ""
        adapter = entry.adapter_class(**kwargs)
        assert adapter.is_configured() is False


# ---------------------------------------------------------------------------
# 5. supported_types contains (all 15)
# ---------------------------------------------------------------------------

class TestSupportedTypesContains:

    @pytest.mark.parametrize("entry", ADAPTER_REGISTRY, ids=_all_ids)
    def test_all_expected_types_present(self, entry: AdapterEntry) -> None:
        adapter = _make_adapter(entry)
        for ioc_type in entry.supported_types:
            assert ioc_type in adapter.supported_types, (
                f"{entry.name}: {ioc_type} should be in supported_types"
            )


# ---------------------------------------------------------------------------
# 6. supported_types excludes (all 15)
# ---------------------------------------------------------------------------

class TestSupportedTypesExcludes:

    @pytest.mark.parametrize("entry", ADAPTER_REGISTRY, ids=_all_ids)
    def test_excluded_types_absent(self, entry: AdapterEntry) -> None:
        adapter = _make_adapter(entry)
        for ioc_type in entry.excluded_types:
            assert ioc_type not in adapter.supported_types, (
                f"{entry.name}: {ioc_type} should NOT be in supported_types"
            )


# ---------------------------------------------------------------------------
# 7. Unsupported type rejection (all 15)
# ---------------------------------------------------------------------------

class TestUnsupportedTypeRejection:

    @pytest.mark.parametrize("entry", ADAPTER_REGISTRY, ids=_all_ids)
    def test_lookup_returns_enrichment_error(self, entry: AdapterEntry) -> None:
        """lookup(unsupported_type) -> EnrichmentError mentioning 'Unsupported'."""
        adapter = _make_adapter(entry)
        # Pick the first excluded type to test
        if not entry.excluded_types:
            pytest.skip(f"{entry.name} has no excluded types")
        unsupported_type = entry.excluded_types[0]
        ioc = _ioc_for_type(unsupported_type)

        # For HTTP adapters, mock session to ensure no network call
        if entry.is_http:
            mock_adapter_session(
                adapter, method=entry.http_method or "get",
                side_effect=AssertionError("Should not reach network"),
            )

        result = adapter.lookup(ioc)
        assert isinstance(result, EnrichmentError), (
            f"{entry.name}: lookup of unsupported {unsupported_type} should return EnrichmentError"
        )
        assert "Unsupported" in result.error or "unsupported" in result.error.lower()


# ---------------------------------------------------------------------------
# 8. Timeout handling (12 HTTP only)
# ---------------------------------------------------------------------------

class TestTimeoutHandling:

    @pytest.mark.parametrize("entry", HTTP_ADAPTERS, ids=_http_ids)
    def test_timeout_returns_enrichment_error(self, entry: AdapterEntry) -> None:
        """Timeout side_effect -> EnrichmentError mentioning 'Timeout' or 'timed out'."""
        adapter = _make_adapter(entry)
        ioc = entry.sample_ioc_factory()
        mock_adapter_session(
            adapter, method=entry.http_method or "get",
            side_effect=requests.exceptions.Timeout("connect timed out"),
        )
        result = adapter.lookup(ioc)
        assert isinstance(result, EnrichmentError), (
            f"{entry.name}: Timeout should produce EnrichmentError"
        )
        assert "timeout" in result.error.lower() or "timed out" in result.error.lower(), (
            f"{entry.name}: error message should mention timeout, got: {result.error}"
        )


# ---------------------------------------------------------------------------
# 9. HTTP 500 error (12 HTTP only)
# ---------------------------------------------------------------------------

class TestHTTP500Error:

    @pytest.mark.parametrize("entry", HTTP_ADAPTERS, ids=_http_ids)
    def test_http_500_returns_enrichment_error(self, entry: AdapterEntry) -> None:
        """Mock 500 response -> EnrichmentError with 'HTTP 500'."""
        adapter = _make_adapter(entry)
        ioc = entry.sample_ioc_factory()

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        http_err = requests.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status = MagicMock(side_effect=http_err)
        mock_resp.iter_content = MagicMock(return_value=iter([b'{"error": "server"}']))

        mock_adapter_session(adapter, method=entry.http_method or "get", response=mock_resp)
        result = adapter.lookup(ioc)
        assert isinstance(result, EnrichmentError), (
            f"{entry.name}: HTTP 500 should produce EnrichmentError"
        )
        assert "500" in result.error, (
            f"{entry.name}: error should mention 500, got: {result.error}"
        )


# ---------------------------------------------------------------------------
# 10. SSRF validation (12 HTTP only)
# ---------------------------------------------------------------------------

class TestSSRFValidation:

    @pytest.mark.parametrize("entry", HTTP_ADAPTERS, ids=_http_ids)
    def test_empty_allowed_hosts_returns_error(self, entry: AdapterEntry) -> None:
        """allowed_hosts=[] -> EnrichmentError mentioning SSRF/allowed."""
        kwargs = dict(entry.constructor_kwargs)
        kwargs["allowed_hosts"] = []
        if "api_key" in entry.constructor_kwargs:
            kwargs["api_key"] = entry.constructor_kwargs["api_key"]
        adapter = entry.adapter_class(**kwargs)

        ioc = entry.sample_ioc_factory()
        mock_adapter_session(
            adapter, method=entry.http_method or "get",
            side_effect=AssertionError("Should not reach network"),
        )
        result = adapter.lookup(ioc)
        assert isinstance(result, EnrichmentError), (
            f"{entry.name}: empty allowed_hosts should produce EnrichmentError"
        )
        assert (
            "SSRF" in result.error
            or "allowed" in result.error.lower()
            or "allowlist" in result.error.lower()
        ), f"{entry.name}: error should mention SSRF/allowed, got: {result.error}"


# ---------------------------------------------------------------------------
# 11. Response size limit (12 HTTP only)
# ---------------------------------------------------------------------------

class TestResponseSizeLimit:

    @pytest.mark.parametrize("entry", HTTP_ADAPTERS, ids=_http_ids)
    def test_oversized_response_returns_error(self, entry: AdapterEntry) -> None:
        """SEC-05: response > MAX_RESPONSE_BYTES -> EnrichmentError."""
        adapter = _make_adapter(entry)
        ioc = entry.sample_ioc_factory()

        oversized_chunk = b"x" * (MAX_RESPONSE_BYTES + 1)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.iter_content = MagicMock(return_value=iter([oversized_chunk]))

        mock_adapter_session(adapter, method=entry.http_method or "get", response=mock_resp)
        result = adapter.lookup(ioc)
        assert isinstance(result, EnrichmentError), (
            f"{entry.name}: oversized response should produce EnrichmentError"
        )


# ---------------------------------------------------------------------------
# 12. Allowed hosts config entry (adapters with config entries)
# ---------------------------------------------------------------------------

class TestAllowedHostsConfig:

    @pytest.mark.parametrize("entry", ADAPTERS_WITH_CONFIG_HOSTS, ids=_config_ids)
    def test_hostname_in_config_allowed_hosts(self, entry: AdapterEntry) -> None:
        """Adapter's expected hostname must appear in Config.ALLOWED_API_HOSTS."""
        assert entry.allowed_hosts_config_entry in Config.ALLOWED_API_HOSTS, (
            f"{entry.name}: {entry.allowed_hosts_config_entry} not in Config.ALLOWED_API_HOSTS"
        )
