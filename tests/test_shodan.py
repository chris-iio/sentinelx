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

import inspect

from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.adapters.shodan import ShodanAdapter, _parse_response
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

    def test_result_helper_preserves_provider_envelope(self) -> None:
        """Shodan response branches should share one provider envelope."""
        from app.enrichment.adapters.shodan import _shodan_result

        ioc = make_ipv4_ioc("8.8.8.8")
        result = _shodan_result(
            ioc=ioc,
            provider_name="Shodan InternetDB",
            verdict="suspicious",
            detection_count=2,
            total_engines=1,
            raw_stats={"vulns": ["CVE-1", "CVE-2"]},
        )

        assert result.ioc is ioc
        assert result.provider == "Shodan InternetDB"
        assert result.verdict == "suspicious"
        assert result.detection_count == 2
        assert result.total_engines == 1
        assert result.scan_date is None
        assert result.raw_stats == {"vulns": ["CVE-1", "CVE-2"]}

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

    def test_malicious_tag_count_preserves_duplicate_bad_tags(self) -> None:
        """Bad tag counting should not rely on a temporary filtered tag list."""
        ioc = make_ipv4_ioc()
        response_body = {
            "ip": "1.2.3.4",
            "ports": [445],
            "hostnames": [],
            "cpes": [],
            "vulns": [],
            "tags": ["malware", "compromised", "malware", "benign"],
        }
        mock_resp = make_mock_response(200, response_body)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"
        assert result.detection_count == 3
        assert result.raw_stats["tags"] == response_body["tags"]

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

    def test_missing_list_fields_avoid_eager_default_lists(self) -> None:
        """Missing list fields should not allocate through body.get default arguments."""
        ioc = make_ipv4_ioc("10.0.0.1")

        class NoDefaultBody(dict):
            def get(self, key, default=None):
                if key in {"vulns", "tags", "ports", "hostnames", "cpes"} and default is not None:
                    raise AssertionError("Shodan list field parsing should avoid eager default list allocation")
                return super().get(key, default)

        result = _parse_response(ioc, NoDefaultBody(), "Shodan InternetDB")

        assert result.verdict == "no_data"
        assert result.raw_stats["vulns"] == []
        assert result.raw_stats["tags"] == []
        assert result.raw_stats["ports"] == []
        assert result.raw_stats["hostnames"] == []
        assert result.raw_stats["cpes"] == []
        assert type(result.raw_stats["vulns"]) is list

    def test_no_signal_response_skips_bad_tag_scan(self) -> None:
        """Responses without tags or vulns should return before iterating tags."""
        class NoIterEmptyList(list):
            def __iter__(self):
                raise AssertionError("no-signal Shodan responses should not scan tags")

        tags = NoIterEmptyList()
        result = _parse_response(
            make_ipv4_ioc("10.0.0.1"),
            {
                "ports": [53],
                "hostnames": ["resolver.local"],
                "cpes": [],
                "vulns": [],
                "tags": tags,
            },
            "Shodan InternetDB",
        )

        assert result.verdict == "no_data"
        assert result.detection_count == 0
        assert result.raw_stats["tags"] is tags
        assert "not tags" in inspect.getsource(_parse_response)

    def test_vuln_only_response_skips_bad_tag_scan(self) -> None:
        """Responses with vulns but no tags should not iterate an empty tag list."""
        class NoIterEmptyList(list):
            def __iter__(self):
                raise AssertionError("vuln-only Shodan responses should not scan tags")

        tags = NoIterEmptyList()
        result = _parse_response(
            make_ipv4_ioc("10.0.0.1"),
            {
                "ports": [445],
                "hostnames": [],
                "cpes": [],
                "vulns": ["CVE-2024-0001"],
                "tags": tags,
            },
            "Shodan InternetDB",
        )

        assert result.verdict == "suspicious"
        assert result.detection_count == 1
        assert result.raw_stats["tags"] is tags

    def test_short_tag_lists_skip_bad_tag_loop(self) -> None:
        """One-, two-, and three-tag Shodan responses should count bad tags directly."""
        class NoIterTags(list):
            def __iter__(self):
                raise AssertionError("short Shodan tag lists should not iterate")

        single = _parse_response(
            make_ipv4_ioc("10.0.0.1"),
            {"ports": [], "hostnames": [], "cpes": [], "vulns": [], "tags": NoIterTags(["malware"])},
            "Shodan InternetDB",
        )
        pair = _parse_response(
            make_ipv4_ioc("10.0.0.2"),
            {
                "ports": [],
                "hostnames": [],
                "cpes": [],
                "vulns": [],
                "tags": NoIterTags(["malware", "compromised"]),
            },
            "Shodan InternetDB",
        )
        three = _parse_response(
            make_ipv4_ioc("10.0.0.3"),
            {
                "ports": [],
                "hostnames": [],
                "cpes": [],
                "vulns": [],
                "tags": NoIterTags(["malware", "benign", "doublepulsar"]),
            },
            "Shodan InternetDB",
        )

        assert single.verdict == "malicious"
        assert single.detection_count == 1
        assert pair.verdict == "malicious"
        assert pair.detection_count == 2
        assert three.verdict == "malicious"
        assert three.detection_count == 2

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
        assert result.scan_date is None
        assert result.raw_stats == {}
        assert "no_data_result(ioc, self.name)" in inspect.getsource(
            ShodanAdapter._make_pre_raise_hook,
        )

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
