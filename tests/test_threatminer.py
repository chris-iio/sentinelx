"""Tests for ThreatMinerAdapter — passive DNS history and related samples via ThreatMiner API v2.

Tests all IOC type routing (IP, domain, hash), passive DNS extraction, related samples extraction,
no_data handling (body status_code "404"), HTTP error handling, and all HTTP safety controls.

All HTTP calls are mocked using unittest.mock.patch -- no real API calls.

ThreatMiner API behavior:
  - GET https://api.threatminer.org/v2/host.php?q={ip}&rt=2 -> IP passive DNS (domains that resolved to IP)
  - GET https://api.threatminer.org/v2/domain.php?q={domain}&rt=2 -> Domain passive DNS (IPs domain resolved to)
  - GET https://api.threatminer.org/v2/domain.php?q={domain}&rt=4 -> Domain related samples
  - GET https://api.threatminer.org/v2/sample.php?q={hash}&rt=4 -> Hash related samples
  - HTTP 200 + body status_code "200": Results found
  - HTTP 200 + body status_code "404": No results -> verdict=no_data (NOT an HTTP error)
  - HTTP 429: Rate limited -> EnrichmentError("HTTP 429")
  - HTTP 403: Blocked -> EnrichmentError("HTTP 403")
  - Timeout: -> EnrichmentError("Timeout")
"""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import requests
import requests.exceptions

from app.enrichment.adapters.threatminer import ThreatMinerAdapter
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.provider import Provider
from app.pipeline.models import IOC, IOCType


ALLOWED_HOSTS = ["api.threatminer.org"]


# --- Sample API responses ---

IP_PASSIVE_DNS_RESPONSE = {
    "status_code": "200",
    "status_message": "Results found.",
    "results": [
        {"domain": "evil.com", "first_seen": "2022-01-01 00:00:00", "last_seen": "2023-01-01 00:00:00"},
        {"domain": "malware.net", "first_seen": "2021-06-01 00:00:00", "last_seen": "2022-06-01 00:00:00"},
        {"domain": "bad.org", "first_seen": "2023-01-01 00:00:00", "last_seen": "2024-01-01 00:00:00"},
    ],
}

DOMAIN_PASSIVE_DNS_RESPONSE = {
    "status_code": "200",
    "status_message": "Results found.",
    "results": [
        {"ip": "1.2.3.4", "first_seen": "2022-01-01 00:00:00", "last_seen": "2023-01-01 00:00:00"},
        {"ip": "5.6.7.8", "first_seen": "2021-06-01 00:00:00", "last_seen": "2022-06-01 00:00:00"},
    ],
}

DOMAIN_SAMPLES_RESPONSE = {
    "status_code": "200",
    "status_message": "Results found.",
    "results": [
        "dd0418c01b7196e967a63fedda70eaf6de4fffb5296a24b9ec13f7a09c2f7bc1",
        "abf736e1a8e0508b6dd840b012d4231cf13f8b48c2dcb3ed18ce92a59dba7109",
    ],
}

HASH_SAMPLES_RESPONSE = {
    "status_code": "200",
    "status_message": "Results found.",
    "results": [
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    ],
}

NO_DATA_RESPONSE = {
    "status_code": "404",
    "status_message": "Results not found.",
    "results": [],
}

EMPTY_RESULTS_RESPONSE = {
    "status_code": "200",
    "status_message": "Results found.",
    "results": [],
}


# --- Helpers ---

def _make_adapter(allowed_hosts: list[str] | None = None) -> ThreatMinerAdapter:
    if allowed_hosts is None:
        allowed_hosts = ALLOWED_HOSTS
    return ThreatMinerAdapter(allowed_hosts=allowed_hosts)


def _make_ioc(ioc_type: IOCType, value: str) -> IOC:
    return IOC(type=ioc_type, value=value, raw_match=value)


def _make_ip_ioc(value: str = "1.2.3.4") -> IOC:
    return _make_ioc(IOCType.IPV4, value)


def _make_domain_ioc(value: str = "evil.com") -> IOC:
    return _make_ioc(IOCType.DOMAIN, value)


def _make_sha256_ioc(value: str = "dd0418c01b7196e967a63fedda70eaf6de4fffb5296a24b9ec13f7a09c2f7bc1") -> IOC:
    return _make_ioc(IOCType.SHA256, value)


def _make_md5_ioc(value: str = "d41d8cd98f00b204e9800998ecf8427e") -> IOC:
    return _make_ioc(IOCType.MD5, value)


def _mock_get_returning(response_body: dict) -> MagicMock:
    """Return a requests.get mock that returns the given response body via read_limited."""
    return MagicMock(status_code=200, raise_for_status=MagicMock())


# ===================================================================
# TestProviderProtocol
# ===================================================================

class TestProviderProtocol:

    def test_is_provider(self) -> None:
        """ThreatMinerAdapter instance must satisfy the Provider protocol (@runtime_checkable)."""
        adapter = ThreatMinerAdapter(allowed_hosts=[])
        assert isinstance(adapter, Provider), (
            "ThreatMinerAdapter must satisfy the Provider protocol via @runtime_checkable"
        )

    def test_name_is_threatminer(self) -> None:
        """ThreatMinerAdapter.name must equal 'ThreatMiner'."""
        assert ThreatMinerAdapter.name == "ThreatMiner"

    def test_requires_api_key_false(self) -> None:
        """ThreatMinerAdapter.requires_api_key must be False (zero-auth provider)."""
        assert ThreatMinerAdapter.requires_api_key is False

    def test_is_configured_always_true(self) -> None:
        """ThreatMinerAdapter.is_configured() must always return True (no key required)."""
        adapter = ThreatMinerAdapter(allowed_hosts=[])
        assert adapter.is_configured() is True

    def test_supported_types_is_frozenset(self) -> None:
        """supported_types must be a frozenset."""
        assert isinstance(ThreatMinerAdapter.supported_types, frozenset)

    def test_supported_types_contains_ipv4(self) -> None:
        """IOCType.IPV4 must be in supported_types."""
        assert IOCType.IPV4 in ThreatMinerAdapter.supported_types

    def test_supported_types_contains_ipv6(self) -> None:
        """IOCType.IPV6 must be in supported_types."""
        assert IOCType.IPV6 in ThreatMinerAdapter.supported_types

    def test_supported_types_contains_domain(self) -> None:
        """IOCType.DOMAIN must be in supported_types."""
        assert IOCType.DOMAIN in ThreatMinerAdapter.supported_types

    def test_supported_types_contains_md5(self) -> None:
        """IOCType.MD5 must be in supported_types."""
        assert IOCType.MD5 in ThreatMinerAdapter.supported_types

    def test_supported_types_contains_sha1(self) -> None:
        """IOCType.SHA1 must be in supported_types."""
        assert IOCType.SHA1 in ThreatMinerAdapter.supported_types

    def test_supported_types_contains_sha256(self) -> None:
        """IOCType.SHA256 must be in supported_types."""
        assert IOCType.SHA256 in ThreatMinerAdapter.supported_types

    def test_supported_types_excludes_url(self) -> None:
        """IOCType.URL must NOT be in supported_types."""
        assert IOCType.URL not in ThreatMinerAdapter.supported_types

    def test_supported_types_excludes_cve(self) -> None:
        """IOCType.CVE must NOT be in supported_types."""
        assert IOCType.CVE not in ThreatMinerAdapter.supported_types

    def test_supported_types_has_six_types(self) -> None:
        """supported_types has exactly 6 entries: IPV4, IPV6, DOMAIN, MD5, SHA1, SHA256."""
        assert len(ThreatMinerAdapter.supported_types) == 6

    def test_unsupported_type_returns_error(self) -> None:
        """URL IOC -> EnrichmentError('Unsupported type') without any network call."""
        ioc = IOC(type=IOCType.URL, value="http://example.com", raw_match="http://example.com")

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.side_effect = AssertionError("Should not reach network")
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "ThreatMiner"
        assert "Unsupported" in result.error or "unsupported" in result.error.lower()

    def test_unsupported_type_cve_returns_error(self) -> None:
        """CVE IOC -> EnrichmentError without any network call."""
        ioc = IOC(type=IOCType.CVE, value="CVE-2021-44228", raw_match="CVE-2021-44228")

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.side_effect = AssertionError("Should not reach network")
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert "Unsupported" in result.error or "unsupported" in result.error.lower()


# ===================================================================
# TestIPLookup
# ===================================================================

class TestIPLookup:

    def test_ip_lookup_returns_enrichment_result(self) -> None:
        """IPv4 lookup returns EnrichmentResult (not EnrichmentError)."""
        ioc = _make_ip_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=IP_PASSIVE_DNS_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(IP_PASSIVE_DNS_RESPONSE)
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult, got {type(result).__name__}: {result!r}"
        )

    def test_ip_lookup_returns_passive_dns_list(self) -> None:
        """IPv4 lookup returns passive_dns list in raw_stats."""
        ioc = _make_ip_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=IP_PASSIVE_DNS_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(IP_PASSIVE_DNS_RESPONSE)
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "passive_dns" in result.raw_stats
        assert isinstance(result.raw_stats["passive_dns"], list)

    def test_ip_lookup_passive_dns_contains_domains(self) -> None:
        """IPv4 passive_dns list contains the domain names from API response."""
        ioc = _make_ip_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=IP_PASSIVE_DNS_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(IP_PASSIVE_DNS_RESPONSE)
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        passive_dns = result.raw_stats["passive_dns"]
        assert "evil.com" in passive_dns
        assert "malware.net" in passive_dns
        assert "bad.org" in passive_dns

    def test_ip_lookup_uses_host_php_endpoint(self) -> None:
        """IP lookup must call host.php endpoint (not domain.php or sample.php)."""
        ioc = _make_ip_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=IP_PASSIVE_DNS_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(IP_PASSIVE_DNS_RESPONSE)
            adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert "host.php" in called_url, f"Expected host.php in URL, got: {called_url}"

    def test_ip_lookup_uses_rt_2(self) -> None:
        """IP lookup must use rt=2 (passive DNS)."""
        ioc = _make_ip_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=IP_PASSIVE_DNS_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(IP_PASSIVE_DNS_RESPONSE)
            adapter.lookup(ioc)

        call_kwargs = adapter._session.get.call_args
        params = call_kwargs.kwargs.get("params", {}) or (call_kwargs.args[1] if len(call_kwargs.args) > 1 else {})
        assert params.get("rt") == "2", f"Expected rt='2', got: {params}"

    def test_ip_lookup_passive_dns_capped_at_25(self) -> None:
        """passive_dns list is capped at 25 entries."""
        ioc = _make_ip_ioc()
        # Create 30 domain results
        many_results = {
            "status_code": "200",
            "status_message": "Results found.",
            "results": [
                {"domain": f"sub{i}.example.com", "first_seen": "2022-01-01", "last_seen": "2023-01-01"}
                for i in range(30)
            ],
        }

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=many_results):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(many_results)
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert len(result.raw_stats["passive_dns"]) <= 25, (
            f"Expected at most 25 passive_dns entries (cap), got {len(result.raw_stats['passive_dns'])}"
        )

    def test_ip_lookup_verdict_is_no_data(self) -> None:
        """IP lookup verdict is always 'no_data' (informational context, not threat signal)."""
        ioc = _make_ip_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=IP_PASSIVE_DNS_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(IP_PASSIVE_DNS_RESPONSE)
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"

    def test_ip_lookup_detection_count_always_zero(self) -> None:
        """detection_count is always 0 for ThreatMiner results."""
        ioc = _make_ip_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=IP_PASSIVE_DNS_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(IP_PASSIVE_DNS_RESPONSE)
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.detection_count == 0

    def test_ip_lookup_total_engines_always_zero(self) -> None:
        """total_engines is always 0 for ThreatMiner results."""
        ioc = _make_ip_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=IP_PASSIVE_DNS_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(IP_PASSIVE_DNS_RESPONSE)
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.total_engines == 0

    def test_ip_lookup_scan_date_always_none(self) -> None:
        """scan_date is always None for ThreatMiner results."""
        ioc = _make_ip_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=IP_PASSIVE_DNS_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(IP_PASSIVE_DNS_RESPONSE)
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.scan_date is None

    def test_ipv6_lookup_uses_host_php(self) -> None:
        """IPv6 lookup also uses host.php (same endpoint as IPv4)."""
        ioc = IOC(type=IOCType.IPV6, value="2001:db8::1", raw_match="2001:db8::1")

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=NO_DATA_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(NO_DATA_RESPONSE)
            result = adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert "host.php" in called_url, f"Expected host.php for IPv6, got: {called_url}"


# ===================================================================
# TestDomainLookup
# ===================================================================

class TestDomainLookup:

    def test_domain_lookup_returns_enrichment_result(self) -> None:
        """Domain lookup returns EnrichmentResult (not EnrichmentError)."""
        ioc = _make_domain_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited") as mock_read:
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning({})
            mock_read.side_effect = [DOMAIN_PASSIVE_DNS_RESPONSE, DOMAIN_SAMPLES_RESPONSE]
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult, got {type(result).__name__}: {result!r}"
        )

    def test_domain_lookup_makes_two_api_calls(self) -> None:
        """Domain lookup makes exactly 2 API calls (rt=2 passive DNS + rt=4 related samples)."""
        ioc = _make_domain_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited") as mock_read:
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning({})
            mock_read.side_effect = [DOMAIN_PASSIVE_DNS_RESPONSE, DOMAIN_SAMPLES_RESPONSE]
            adapter.lookup(ioc)

        assert adapter._session.get.call_count == 2, (
            f"Domain lookup must make exactly 2 API calls (rt=2 + rt=4), got {adapter._session.get.call_count}"
        )

    def test_domain_lookup_first_call_uses_rt_2(self) -> None:
        """First API call for domain must use rt=2 (passive DNS)."""
        ioc = _make_domain_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited") as mock_read:
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning({})
            mock_read.side_effect = [DOMAIN_PASSIVE_DNS_RESPONSE, DOMAIN_SAMPLES_RESPONSE]
            adapter.lookup(ioc)

        first_call = adapter._session.get.call_args_list[0]
        params = first_call.kwargs.get("params", {})
        assert params.get("rt") == "2", f"First call must use rt='2', got: {params}"

    def test_domain_lookup_second_call_uses_rt_4(self) -> None:
        """Second API call for domain must use rt=4 (related samples)."""
        ioc = _make_domain_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited") as mock_read:
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning({})
            mock_read.side_effect = [DOMAIN_PASSIVE_DNS_RESPONSE, DOMAIN_SAMPLES_RESPONSE]
            adapter.lookup(ioc)

        second_call = adapter._session.get.call_args_list[1]
        params = second_call.kwargs.get("params", {})
        assert params.get("rt") == "4", f"Second call must use rt='4', got: {params}"

    def test_domain_lookup_uses_domain_php_endpoint(self) -> None:
        """Domain lookup must call domain.php endpoint."""
        ioc = _make_domain_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited") as mock_read:
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning({})
            mock_read.side_effect = [DOMAIN_PASSIVE_DNS_RESPONSE, DOMAIN_SAMPLES_RESPONSE]
            adapter.lookup(ioc)

        for call_args in adapter._session.get.call_args_list:
            called_url = call_args.args[0]
            assert "domain.php" in called_url, f"Domain lookup must use domain.php, got: {called_url}"

    def test_domain_lookup_returns_merged_passive_dns_and_samples(self) -> None:
        """Domain lookup result contains both passive_dns and samples in raw_stats."""
        ioc = _make_domain_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited") as mock_read:
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning({})
            mock_read.side_effect = [DOMAIN_PASSIVE_DNS_RESPONSE, DOMAIN_SAMPLES_RESPONSE]
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "passive_dns" in result.raw_stats, "raw_stats must contain 'passive_dns'"
        assert "samples" in result.raw_stats, "raw_stats must contain 'samples'"

    def test_domain_lookup_passive_dns_contains_ips(self) -> None:
        """Domain lookup passive_dns list contains IP addresses."""
        ioc = _make_domain_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited") as mock_read:
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning({})
            mock_read.side_effect = [DOMAIN_PASSIVE_DNS_RESPONSE, DOMAIN_SAMPLES_RESPONSE]
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        passive_dns = result.raw_stats["passive_dns"]
        assert "1.2.3.4" in passive_dns
        assert "5.6.7.8" in passive_dns

    def test_domain_lookup_samples_contains_hashes(self) -> None:
        """Domain lookup samples list contains SHA-256 hashes."""
        ioc = _make_domain_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited") as mock_read:
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning({})
            mock_read.side_effect = [DOMAIN_PASSIVE_DNS_RESPONSE, DOMAIN_SAMPLES_RESPONSE]
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        samples = result.raw_stats["samples"]
        assert "dd0418c01b7196e967a63fedda70eaf6de4fffb5296a24b9ec13f7a09c2f7bc1" in samples

    def test_domain_lookup_passive_dns_capped_at_25(self) -> None:
        """Domain passive_dns list is capped at 25 entries."""
        ioc = _make_domain_ioc()
        many_ips = {
            "status_code": "200",
            "status_message": "Results found.",
            "results": [
                {"ip": f"10.0.{i}.1", "first_seen": "2022-01-01", "last_seen": "2023-01-01"}
                for i in range(30)
            ],
        }

        with patch("app.enrichment.adapters.threatminer.read_limited") as mock_read:
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning({})
            mock_read.side_effect = [many_ips, DOMAIN_SAMPLES_RESPONSE]
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert len(result.raw_stats["passive_dns"]) <= 25, (
            f"Expected at most 25 passive_dns entries, got {len(result.raw_stats['passive_dns'])}"
        )

    def test_domain_lookup_samples_capped_at_20(self) -> None:
        """Domain samples list is capped at 20 entries."""
        ioc = _make_domain_ioc()
        many_samples = {
            "status_code": "200",
            "status_message": "Results found.",
            "results": [f"{'a' * 63}{i:01d}" for i in range(25)],
        }

        with patch("app.enrichment.adapters.threatminer.read_limited") as mock_read:
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning({})
            mock_read.side_effect = [DOMAIN_PASSIVE_DNS_RESPONSE, many_samples]
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert len(result.raw_stats["samples"]) <= 20, (
            f"Expected at most 20 samples entries, got {len(result.raw_stats['samples'])}"
        )

    def test_domain_lookup_verdict_is_no_data(self) -> None:
        """Domain lookup verdict is always 'no_data'."""
        ioc = _make_domain_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited") as mock_read:
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning({})
            mock_read.side_effect = [DOMAIN_PASSIVE_DNS_RESPONSE, DOMAIN_SAMPLES_RESPONSE]
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"


# ===================================================================
# TestHashLookup
# ===================================================================

class TestHashLookup:

    def test_hash_lookup_returns_enrichment_result(self) -> None:
        """SHA256 lookup returns EnrichmentResult."""
        ioc = _make_sha256_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=HASH_SAMPLES_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(HASH_SAMPLES_RESPONSE)
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult, got {type(result).__name__}: {result!r}"
        )

    def test_hash_lookup_returns_samples_list(self) -> None:
        """SHA256 lookup returns samples list in raw_stats."""
        ioc = _make_sha256_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=HASH_SAMPLES_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(HASH_SAMPLES_RESPONSE)
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "samples" in result.raw_stats
        assert isinstance(result.raw_stats["samples"], list)

    def test_hash_lookup_samples_contains_hashes(self) -> None:
        """SHA256 lookup samples list contains the related hashes from API response."""
        ioc = _make_sha256_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=HASH_SAMPLES_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(HASH_SAMPLES_RESPONSE)
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        samples = result.raw_stats["samples"]
        assert "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" in samples
        assert "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" in samples

    def test_hash_lookup_uses_sample_php_endpoint(self) -> None:
        """Hash lookup must call sample.php endpoint."""
        ioc = _make_sha256_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=HASH_SAMPLES_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(HASH_SAMPLES_RESPONSE)
            adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert "sample.php" in called_url, f"Expected sample.php, got: {called_url}"

    def test_hash_lookup_uses_rt_4(self) -> None:
        """Hash lookup must use rt=4 (related samples)."""
        ioc = _make_sha256_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=HASH_SAMPLES_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(HASH_SAMPLES_RESPONSE)
            adapter.lookup(ioc)

        call_kwargs = adapter._session.get.call_args
        params = call_kwargs.kwargs.get("params", {})
        assert params.get("rt") == "4", f"Expected rt='4', got: {params}"

    def test_hash_lookup_samples_capped_at_20(self) -> None:
        """Hash samples list is capped at 20 entries."""
        ioc = _make_sha256_ioc()
        many_samples = {
            "status_code": "200",
            "status_message": "Results found.",
            "results": [f"{'a' * 63}{i:01d}" for i in range(25)],
        }

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=many_samples):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(many_samples)
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert len(result.raw_stats["samples"]) <= 20, (
            f"Expected at most 20 sample entries, got {len(result.raw_stats['samples'])}"
        )

    def test_md5_lookup_uses_sample_php(self) -> None:
        """MD5 hash lookup also uses sample.php."""
        ioc = _make_md5_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=HASH_SAMPLES_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(HASH_SAMPLES_RESPONSE)
            adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert "sample.php" in called_url

    def test_sha1_lookup_uses_sample_php(self) -> None:
        """SHA1 hash lookup also uses sample.php."""
        ioc = IOC(type=IOCType.SHA1, value="da39a3ee5e6b4b0d3255bfef95601890afd80709", raw_match="da39a3ee5e6b4b0d3255bfef95601890afd80709")

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=HASH_SAMPLES_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(HASH_SAMPLES_RESPONSE)
            adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert "sample.php" in called_url

    def test_hash_lookup_verdict_is_no_data(self) -> None:
        """Hash lookup verdict is always 'no_data'."""
        ioc = _make_sha256_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=HASH_SAMPLES_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(HASH_SAMPLES_RESPONSE)
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"

    def test_hash_lookup_defensive_dict_handling(self) -> None:
        """Hash results that are dicts (unexpected) are handled defensively."""
        ioc = _make_sha256_ioc()
        dict_results = {
            "status_code": "200",
            "status_message": "Results found.",
            "results": [
                {"sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
                "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            ],
        }

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=dict_results):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(dict_results)
            # Should not raise an exception
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        # At minimum the plain string result should be included
        assert "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" in result.raw_stats.get("samples", [])


# ===================================================================
# TestNoDataHandling
# ===================================================================

class TestNoDataHandling:

    def test_ip_body_404_returns_no_data(self) -> None:
        """IP lookup with body status_code '404' returns EnrichmentResult(verdict='no_data')."""
        ioc = _make_ip_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=NO_DATA_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(NO_DATA_RESPONSE)
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"status_code '404' in body must return EnrichmentResult (no_data), not EnrichmentError. Got: {result!r}"
        )
        assert result.verdict == "no_data"

    def test_ip_body_404_returns_empty_raw_stats(self) -> None:
        """IP lookup with body status_code '404' returns empty raw_stats."""
        ioc = _make_ip_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=NO_DATA_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(NO_DATA_RESPONSE)
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats == {}

    def test_ip_empty_results_returns_no_data(self) -> None:
        """IP lookup with status_code '200' but empty results returns no_data."""
        ioc = _make_ip_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=EMPTY_RESULTS_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(EMPTY_RESULTS_RESPONSE)
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"

    def test_domain_both_404_returns_no_data(self) -> None:
        """Domain lookup with both calls returning status_code '404' returns no_data."""
        ioc = _make_domain_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited") as mock_read:
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning({})
            mock_read.side_effect = [NO_DATA_RESPONSE, NO_DATA_RESPONSE]
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"
        assert result.raw_stats == {}

    def test_domain_first_404_second_has_data(self) -> None:
        """Domain with passive DNS '404' but samples data -> samples included, passive_dns absent or empty."""
        ioc = _make_domain_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited") as mock_read:
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning({})
            mock_read.side_effect = [NO_DATA_RESPONSE, DOMAIN_SAMPLES_RESPONSE]
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        # samples should be populated from the second call
        assert result.raw_stats.get("samples"), "samples should be present when rt=4 has data"

    def test_domain_second_404_first_has_data(self) -> None:
        """Domain with passive DNS data but samples '404' -> passive_dns included, samples absent or empty."""
        ioc = _make_domain_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited") as mock_read:
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning({})
            mock_read.side_effect = [DOMAIN_PASSIVE_DNS_RESPONSE, NO_DATA_RESPONSE]
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        # passive_dns should be populated from the first call
        assert result.raw_stats.get("passive_dns"), "passive_dns should be present when rt=2 has data"

    def test_hash_body_404_returns_no_data(self) -> None:
        """Hash lookup with body status_code '404' returns EnrichmentResult(verdict='no_data')."""
        ioc = _make_sha256_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=NO_DATA_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(NO_DATA_RESPONSE)
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"Body '404' must return EnrichmentResult, got {type(result).__name__}: {result!r}"
        )
        assert result.verdict == "no_data"

    def test_hash_body_404_returns_empty_raw_stats(self) -> None:
        """Hash lookup with body status_code '404' returns empty raw_stats."""
        ioc = _make_sha256_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=NO_DATA_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(NO_DATA_RESPONSE)
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats == {}


# ===================================================================
# TestHTTPErrors
# ===================================================================

class TestHTTPErrors:

    def test_http_429_ip_returns_enrichment_error(self) -> None:
        """HTTP 429 for IP lookup -> EnrichmentError('HTTP 429')."""
        ioc = _make_ip_ioc()
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        http_err = requests.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status = MagicMock(side_effect=http_err)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError), (
            f"HTTP 429 must return EnrichmentError, got {type(result).__name__}: {result!r}"
        )
        assert result.provider == "ThreatMiner"
        assert "429" in result.error

    def test_http_403_ip_returns_enrichment_error(self) -> None:
        """HTTP 403 for IP lookup -> EnrichmentError('HTTP 403')."""
        ioc = _make_ip_ioc()
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        http_err = requests.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status = MagicMock(side_effect=http_err)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert "403" in result.error

    def test_timeout_ip_returns_enrichment_error(self) -> None:
        """Network timeout for IP lookup -> EnrichmentError('Timeout')."""
        ioc = _make_ip_ioc()

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.side_effect = requests.exceptions.Timeout("timed out")
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "ThreatMiner"
        assert "Timeout" in result.error or "timeout" in result.error.lower()

    def test_unexpected_exception_ip_returns_enrichment_error(self) -> None:
        """Unexpected exception for IP lookup -> EnrichmentError('Unexpected error')."""
        ioc = _make_ip_ioc()

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.side_effect = RuntimeError("boom")
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert "Unexpected" in result.error or "unexpected" in result.error.lower()

    def test_http_429_domain_first_call_skips_second(self) -> None:
        """HTTP 429 on domain's first API call (rt=2) -> return error, do NOT make second call."""
        ioc = _make_domain_ioc()
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        http_err = requests.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status = MagicMock(side_effect=http_err)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError), (
            f"HTTP 429 on first domain call must return EnrichmentError, got {type(result).__name__}"
        )
        assert "429" in result.error
        assert adapter._session.get.call_count == 1, (
            f"After 429 on first domain call, must NOT make second call. Got {adapter._session.get.call_count} calls."
        )

    def test_ssrf_validation_blocks_disallowed_host(self) -> None:
        """allowed_hosts=[] -> EnrichmentError from SSRF check before network call."""
        ioc = _make_ip_ioc()
        adapter = ThreatMinerAdapter(allowed_hosts=[])

        adapter._session = MagicMock()
        adapter._session.get.side_effect = AssertionError("Should not reach network")
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError), (
            "Expected EnrichmentError when host not in allowed_hosts (SSRF check)"
        )
        assert (
            "SSRF" in result.error
            or "allowed" in result.error.lower()
            or "allowlist" in result.error.lower()
        )

    def test_http_500_returns_enrichment_error(self) -> None:
        """HTTP 500 for IP lookup -> EnrichmentError with 'HTTP 500' in error."""
        ioc = _make_ip_ioc()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        http_err = requests.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status = MagicMock(side_effect=http_err)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert "500" in result.error


# ===================================================================
# TestHTTPSafetyControls
# ===================================================================

class TestHTTPSafetyControls:

    def test_uses_timeout(self) -> None:
        """requests.get must be called with timeout=TIMEOUT (SEC-04)."""
        from app.enrichment.http_safety import TIMEOUT
        ioc = _make_ip_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=IP_PASSIVE_DNS_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(IP_PASSIVE_DNS_RESPONSE)
            adapter.lookup(ioc)

        call_kwargs = adapter._session.get.call_args.kwargs
        assert call_kwargs.get("timeout") == TIMEOUT, (
            f"Expected timeout={TIMEOUT!r} (SEC-04), got {call_kwargs.get('timeout')!r}"
        )

    def test_uses_allow_redirects_false(self) -> None:
        """requests.get must be called with allow_redirects=False (SEC-06)."""
        ioc = _make_ip_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=IP_PASSIVE_DNS_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(IP_PASSIVE_DNS_RESPONSE)
            adapter.lookup(ioc)

        call_kwargs = adapter._session.get.call_args.kwargs
        assert call_kwargs.get("allow_redirects") is False, (
            "allow_redirects must be False (SEC-06)"
        )

    def test_uses_stream_true(self) -> None:
        """requests.get must be called with stream=True (SEC-05)."""
        ioc = _make_ip_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=IP_PASSIVE_DNS_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(IP_PASSIVE_DNS_RESPONSE)
            adapter.lookup(ioc)

        call_kwargs = adapter._session.get.call_args.kwargs
        assert call_kwargs.get("stream") is True, "stream must be True (SEC-05)"

    def test_validate_endpoint_called_for_ip(self) -> None:
        """validate_endpoint must be called before making the HTTP request for IP lookup (SEC-16)."""
        ioc = _make_ip_ioc()

        with patch("app.enrichment.adapters.threatminer.validate_endpoint") as mock_validate, \
             patch("app.enrichment.adapters.threatminer.read_limited", return_value=IP_PASSIVE_DNS_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(IP_PASSIVE_DNS_RESPONSE)
            adapter.lookup(ioc)

        mock_validate.assert_called_once()
        called_url = mock_validate.call_args.args[0]
        assert "threatminer" in called_url

    def test_validate_endpoint_called_for_domain_both_calls(self) -> None:
        """validate_endpoint must be called for BOTH domain API calls (SEC-16)."""
        ioc = _make_domain_ioc()

        with patch("app.enrichment.adapters.threatminer.validate_endpoint") as mock_validate, \
             patch("app.enrichment.adapters.threatminer.read_limited") as mock_read:
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning({})
            mock_read.side_effect = [DOMAIN_PASSIVE_DNS_RESPONSE, DOMAIN_SAMPLES_RESPONSE]
            adapter.lookup(ioc)

        assert mock_validate.call_count == 2, (
            f"validate_endpoint must be called twice for domain lookup (once per API call). Got {mock_validate.call_count}"
        )

    def test_uses_params_not_fstring_url(self) -> None:
        """requests.get must be called with params dict (NOT f-string URL with value embedded)."""
        ioc = _make_ip_ioc()

        with patch("app.enrichment.adapters.threatminer.read_limited", return_value=IP_PASSIVE_DNS_RESPONSE):
            adapter = _make_adapter()
            adapter._session = MagicMock()
            adapter._session.get.return_value = _mock_get_returning(IP_PASSIVE_DNS_RESPONSE)
            adapter.lookup(ioc)

        call_kwargs = adapter._session.get.call_args.kwargs
        assert "params" in call_kwargs, "requests.get must be called with params= kwarg (not f-string URL)"
        assert "q" in call_kwargs["params"], "params must contain 'q' key"
        assert call_kwargs["params"]["q"] == "1.2.3.4"
