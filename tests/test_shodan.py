"""Tests for Shodan InternetDB adapter — verdict logic and response parsing.

Contract tests (protocol, error handling, safety controls) are in test_adapter_contract.py.

Verdict priority:
  1. tags contains "malware", "compromised", or "doublepulsar" -> malicious
  2. vulns is non-empty -> suspicious
  3. has data but no vulns/bad tags -> no_data
  4. 404 response -> no_data (not an error)

All HTTP calls are mocked using unittest.mock.patch -- no real API calls.
"""
from __future__ import annotations

from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.adapters.shodan import ShodanAdapter
from tests.helpers import (
    make_mock_response,
    make_ipv4_ioc,
    make_ipv6_ioc,
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



