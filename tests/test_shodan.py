"""Tests for Shodan InternetDB adapter.

Tests IP lookups, verdict logic (malicious/suspicious/no_data), error handling,
and all HTTP safety controls (timeout, size cap, no redirects, SSRF allowlist).

Verdict priority:
  1. tags contains "malware", "compromised", or "doublepulsar" -> malicious
  2. vulns is non-empty -> suspicious
  3. has data but no vulns/bad tags -> no_data
  4. 404 response -> no_data (not an error)

All HTTP calls are mocked using unittest.mock.patch -- no real API calls.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import requests
import requests.exceptions

from app.pipeline.models import IOCType
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.adapters.shodan import ShodanAdapter
from app.enrichment.http_safety import MAX_RESPONSE_BYTES
from app.enrichment.provider import Provider
from tests.helpers import (
    make_mock_response,
    make_domain_ioc,
    make_ipv4_ioc,
    make_ipv6_ioc,
    make_md5_ioc,
    mock_adapter_session,
)


ALLOWED_HOSTS = ["internetdb.shodan.io"]

SHODAN_FOUND_VULNS_RESPONSE = {
    "ip": "8.8.8.8",
    "ports": [80, 443, 22],
    "hostnames": ["dns.google"],
    "cpes": ["cpe:/a:apache:http_server:2.4.41"],
    "vulns": ["CVE-2021-44228", "CVE-2022-0778"],
    "tags": [],
}

SHODAN_FOUND_MALWARE_TAG_RESPONSE = {
    "ip": "1.2.3.4",
    "ports": [445],
    "hostnames": [],
    "cpes": [],
    "vulns": [],
    "tags": ["malware"],
}

SHODAN_FOUND_COMPROMISED_TAG_RESPONSE = {
    "ip": "1.2.3.4",
    "ports": [22],
    "hostnames": [],
    "cpes": [],
    "vulns": [],
    "tags": ["compromised"],
}

SHODAN_FOUND_DOUBLEPULSAR_TAG_RESPONSE = {
    "ip": "1.2.3.4",
    "ports": [445],
    "hostnames": [],
    "cpes": [],
    "vulns": [],
    "tags": ["doublepulsar"],
}

SHODAN_FOUND_PORTS_ONLY_RESPONSE = {
    "ip": "10.0.0.1",
    "ports": [53],
    "hostnames": ["resolver.local"],
    "cpes": [],
    "vulns": [],
    "tags": [],
}

SHODAN_404_RESPONSE = {"detail": "No information available"}




def _make_adapter(allowed_hosts: list[str] | None = None) -> ShodanAdapter:
    if allowed_hosts is None:
        allowed_hosts = ALLOWED_HOSTS
    return ShodanAdapter(allowed_hosts=allowed_hosts)


class TestLookupFound:

    def test_vulns_present_returns_suspicious(self) -> None:
        """IPv4 IOC with vulns list -> verdict=suspicious, detection_count=len(vulns)."""
        ioc = make_ipv4_ioc("8.8.8.8")
        mock_resp = make_mock_response(200, SHODAN_FOUND_VULNS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult, got {type(result).__name__}: {result!r}"
        )
        assert result.provider == "Shodan InternetDB"
        assert result.verdict == "suspicious"
        assert result.detection_count == len(SHODAN_FOUND_VULNS_RESPONSE["vulns"])

    def test_malware_tag_returns_malicious(self) -> None:
        """IPv4 IOC with tags=['malware'] -> verdict=malicious, detection_count=1."""
        ioc = make_ipv4_ioc()
        mock_resp = make_mock_response(200, SHODAN_FOUND_MALWARE_TAG_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.provider == "Shodan InternetDB"
        assert result.verdict == "malicious"
        assert result.detection_count == 1

    def test_compromised_tag_returns_malicious(self) -> None:
        """IPv4 IOC with tags=['compromised'] -> verdict=malicious."""
        ioc = make_ipv4_ioc()
        mock_resp = make_mock_response(200, SHODAN_FOUND_COMPROMISED_TAG_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"

    def test_doublepulsar_tag_returns_malicious(self) -> None:
        """IPv4 IOC with tags=['doublepulsar'] -> verdict=malicious."""
        ioc = make_ipv4_ioc()
        mock_resp = make_mock_response(200, SHODAN_FOUND_DOUBLEPULSAR_TAG_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"

    def test_ports_only_no_vulns_returns_no_data(self) -> None:
        """IPv4 IOC with ports but empty vulns and tags -> verdict=no_data, detection_count=0."""
        ioc = make_ipv4_ioc("10.0.0.1")
        mock_resp = make_mock_response(200, SHODAN_FOUND_PORTS_ONLY_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"
        assert result.detection_count == 0

    def test_raw_stats_contains_ports_vulns_tags(self) -> None:
        """200 response -> raw_stats dict contains keys: ports, vulns, tags, hostnames, cpes."""
        ioc = make_ipv4_ioc("8.8.8.8")
        mock_resp = make_mock_response(200, SHODAN_FOUND_VULNS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        for key in ("ports", "vulns", "tags", "hostnames", "cpes"):
            assert key in result.raw_stats, f"raw_stats missing key: {key!r}"

    def test_ipv6_supported(self) -> None:
        """IPv6 IOC with vulns -> verdict=suspicious (IPv6 is in supported_types)."""
        ioc = make_ipv6_ioc("2001:db8::1")
        response_body = {
            "ip": "2001:db8::1",
            "ports": [80],
            "hostnames": [],
            "cpes": [],
            "vulns": ["CVE-2021-44228"],
            "tags": [],
        }
        mock_resp = make_mock_response(200, response_body)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "suspicious"


class TestLookupNotFound:

    def test_404_returns_no_data_result(self) -> None:
        """404 response -> EnrichmentResult(verdict='no_data'), detection_count=0, total_engines=0."""
        ioc = make_ipv4_ioc("192.0.2.1")
        mock_resp = make_mock_response(404, SHODAN_404_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"404 must return EnrichmentResult (not EnrichmentError), got {type(result).__name__}: {result!r}"
        )
        assert result.verdict == "no_data"
        assert result.detection_count == 0
        assert result.total_engines == 0

    def test_404_returns_result_not_error(self) -> None:
        """404 response -> isinstance(result, EnrichmentResult) is True, NOT EnrichmentError."""
        ioc = make_ipv4_ioc("192.0.2.1")
        mock_resp = make_mock_response(404, SHODAN_404_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            "404 from Shodan InternetDB is not an error — it means 'no data', not 'failure'"
        )
        assert not isinstance(result, EnrichmentError)


class TestLookupErrors:

    def test_unsupported_type_domain(self) -> None:
        """DOMAIN IOC -> EnrichmentError, provider='Shodan InternetDB', error contains 'Unsupported'."""
        ioc = make_domain_ioc()

        result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "Shodan InternetDB"
        assert "Unsupported" in result.error or "unsupported" in result.error.lower()

    def test_unsupported_type_md5(self) -> None:
        """MD5 IOC -> EnrichmentError (hashes not supported by InternetDB)."""
        ioc = make_md5_ioc("a" * 32)

        result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "Shodan InternetDB"

    def test_timeout(self) -> None:
        """Network timeout -> EnrichmentError with 'Timeout' in error."""
        ioc = make_ipv4_ioc("8.8.8.8")

        adapter = _make_adapter()
        mock_adapter_session(adapter, side_effect=requests.exceptions.Timeout("timed out"))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "Shodan InternetDB"
        assert "Timeout" in result.error or "timed out" in result.error.lower()

    def test_http_500(self) -> None:
        """HTTP 500 response -> EnrichmentError with 'HTTP 500' in error."""
        ioc = make_ipv4_ioc("8.8.8.8")
        mock_resp = make_mock_response(500)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "Shodan InternetDB"
        assert "HTTP 500" in result.error

    def test_http_422(self) -> None:
        """HTTP 422 response (validation error) -> EnrichmentError with 'HTTP 422' in error."""
        ioc = make_ipv4_ioc("8.8.8.8")
        mock_resp = make_mock_response(422)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "Shodan InternetDB"
        assert "HTTP 422" in result.error

    def test_ssrf_validation_blocks_disallowed_host(self) -> None:
        """Adapter with allowed_hosts=[] -> EnrichmentError before network call, error mentions SSRF/allowed."""
        ioc = make_ipv4_ioc("8.8.8.8")
        adapter = ShodanAdapter(allowed_hosts=[])

        mock_adapter_session(adapter, side_effect=AssertionError("Should not reach network"))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError), (
            "Expected EnrichmentError when host not in allowed_hosts (SSRF check)"
        )
        assert (
            "SSRF" in result.error
            or "allowed" in result.error.lower()
            or "allowlist" in result.error.lower()
        )


class TestHTTPSafetyControls:

    def test_response_size_limit(self) -> None:
        """SEC-05: Responses exceeding 1 MB must be rejected with EnrichmentError."""
        ioc = make_ipv4_ioc("8.8.8.8")

        oversized_chunk = b"x" * (MAX_RESPONSE_BYTES + 1)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.iter_content = MagicMock(return_value=iter([oversized_chunk]))

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError), (
            f"Expected EnrichmentError for oversized response, got {type(result).__name__}"
        )


class TestSupportedTypes:

    def test_supported_types_contains_ipv4(self) -> None:
        """IOCType.IPV4 must be in ShodanAdapter.supported_types."""
        assert IOCType.IPV4 in ShodanAdapter.supported_types

    def test_supported_types_contains_ipv6(self) -> None:
        """IOCType.IPV6 must be in ShodanAdapter.supported_types."""
        assert IOCType.IPV6 in ShodanAdapter.supported_types

    def test_supported_types_excludes_domain(self) -> None:
        """IOCType.DOMAIN must NOT be in ShodanAdapter.supported_types."""
        assert IOCType.DOMAIN not in ShodanAdapter.supported_types

    def test_supported_types_excludes_md5(self) -> None:
        """IOCType.MD5 must NOT be in ShodanAdapter.supported_types."""
        assert IOCType.MD5 not in ShodanAdapter.supported_types


class TestProtocolConformance:

    def test_shodan_adapter_is_provider(self) -> None:
        """ShodanAdapter instance must satisfy the Provider protocol (isinstance check)."""
        adapter = ShodanAdapter(allowed_hosts=[])
        assert isinstance(adapter, Provider), (
            "ShodanAdapter must satisfy the Provider protocol via @runtime_checkable"
        )

    def test_shodan_adapter_name(self) -> None:
        """ShodanAdapter.name must equal 'Shodan InternetDB'."""
        assert ShodanAdapter.name == "Shodan InternetDB"

    def test_shodan_requires_api_key_false(self) -> None:
        """ShodanAdapter.requires_api_key must be False (zero-auth provider)."""
        assert ShodanAdapter.requires_api_key is False

    def test_shodan_is_configured_always_true(self) -> None:
        """ShodanAdapter.is_configured() must always return True regardless of config."""
        adapter = ShodanAdapter(allowed_hosts=[])
        assert adapter.is_configured() is True


class TestAllowedHostsIntegration:

    def test_config_allows_shodan(self) -> None:
        """'internetdb.shodan.io' must be in Config.ALLOWED_API_HOSTS (SSRF allowlist)."""
        from app.config import Config
        assert "internetdb.shodan.io" in Config.ALLOWED_API_HOSTS, (
            "internetdb.shodan.io missing from ALLOWED_API_HOSTS — "
            "ShodanAdapter will always fail SSRF validation in production"
        )
