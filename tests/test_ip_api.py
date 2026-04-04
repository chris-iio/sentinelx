"""Tests for ipinfo.io IP Context adapter — geo/rDNS/ASN data extraction and parsing.

Contract tests (protocol, error handling, safety controls) are in test_adapter_contract.py.

All HTTP calls are mocked using unittest.mock — no real API calls.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.adapters.ip_api import IPApiAdapter
from tests.helpers import (
    make_mock_response,
    mock_adapter_session,
    make_ipv4_ioc,
    make_ipv6_ioc,
)


ALLOWED_HOSTS = ["ipinfo.io"]

# ipinfo.io response format: "org" field is "AS{num} {ISP Name}"
IPINFO_PUBLIC_IP_RESPONSE = {
    "ip": "95.172.185.24",
    "hostname": "static.24.185.172.95.clients.your-server.de",
    "city": "Nuremberg",
    "region": "Bavaria",
    "country": "DE",
    "loc": "49.4478,11.0683",
    "org": "AS24940 Hetzner Online GmbH",
    "postal": "90402",
    "timezone": "Europe/Berlin",
}

IPINFO_CHICAGO_RESPONSE = {
    "ip": "5.6.7.8",
    "city": "Chicago",
    "region": "Illinois",
    "country": "US",
    "loc": "41.8781,-87.6298",
    "org": "AS3356 Lumen Technologies Inc.",
    "postal": "60601",
    "timezone": "America/Chicago",
}

IPINFO_MOSCOW_RESPONSE = {
    "ip": "1.2.3.4",
    "hostname": "host.example.ru",
    "city": "Moscow",
    "region": "Moscow",
    "country": "RU",
    "loc": "55.7522,37.6156",
    "org": "AS12389 PJSC Rostelecom",
    "postal": "101000",
    "timezone": "Europe/Moscow",
}

IPINFO_LONDON_RESPONSE = {
    "ip": "1.2.3.4",
    "hostname": "cpc1-ched.example.com",
    "city": "London",
    "region": "England",
    "country": "GB",
    "loc": "51.5085,-0.1257",
    "org": "AS5089 Virgin Media Limited",
    "postal": "EC1A",
    "timezone": "Europe/London",
}

# Minimal response — present but empty strings for optional fields
IPINFO_MINIMAL_RESPONSE = {
    "ip": "8.8.8.8",
    "country": "US",
    "city": "",
    "org": "",
}




def _make_adapter(allowed_hosts: list[str] | None = None) -> IPApiAdapter:
    if allowed_hosts is None:
        allowed_hosts = ALLOWED_HOSTS
    return IPApiAdapter(allowed_hosts=allowed_hosts)


class TestLookupPublicIP:

    def test_public_ip_returns_enrichment_result(self) -> None:
        """Public IP with HTTP 200 + country field -> EnrichmentResult with correct shape."""
        ioc = make_ipv4_ioc("95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult, got {type(result).__name__}: {result!r}"
        )
        assert result.provider == "IP Context", "IP Context adapter — provider must be 'IP Context'"
        assert result.detection_count == 0, "informational adapter — detection_count must be 0"
        assert result.total_engines == 0, "informational adapter — total_engines must be 0"
        assert result.scan_date is None, "informational adapter — scan_date must be None"

    def test_public_ip_verdict_is_no_data(self) -> None:
        """IP Context never assigns threat verdicts — verdict is always no_data."""
        ioc = make_ipv4_ioc("95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data", (
            f"IP Context must never set threat verdicts, got: {result.verdict!r}"
        )

    def test_raw_stats_contains_required_fields(self) -> None:
        """raw_stats must contain country_code, city, as_info, asname, reverse, proxy, hosting, mobile."""
        ioc = make_ipv4_ioc("95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        for key in ("country_code", "city", "as_info", "asname", "reverse", "proxy", "hosting", "mobile"):
            assert key in result.raw_stats, f"raw_stats missing key: {key!r}"

    def test_raw_stats_country_code(self) -> None:
        """raw_stats['country_code'] populated from ipinfo.io 'country' field."""
        ioc = make_ipv4_ioc("95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["country_code"] == "DE"

    def test_raw_stats_city(self) -> None:
        """raw_stats['city'] populated from ipinfo.io 'city' field."""
        ioc = make_ipv4_ioc("95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["city"] == "Nuremberg"

    def test_raw_stats_as_info(self) -> None:
        """raw_stats['as_info'] populated from the 'org' field (full ASN string)."""
        ioc = make_ipv4_ioc("95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["as_info"] == "AS24940 Hetzner Online GmbH"

    def test_raw_stats_reverse_from_hostname(self) -> None:
        """raw_stats['reverse'] populated from ipinfo.io 'hostname' field."""
        ioc = make_ipv4_ioc("95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["reverse"] == "static.24.185.172.95.clients.your-server.de"

    def test_raw_stats_hosting_always_false(self) -> None:
        """raw_stats['hosting'] is always False — ipinfo.io free tier does not provide this."""
        ioc = make_ipv4_ioc("95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["hosting"] is False

    def test_raw_stats_proxy_always_false(self) -> None:
        """raw_stats['proxy'] is always False — ipinfo.io free tier does not provide this."""
        ioc = make_ipv4_ioc("95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["proxy"] is False


class TestGeoFormatting:

    def test_geo_field_present(self) -> None:
        """raw_stats must contain a 'geo' pre-formatted string."""
        ioc = make_ipv4_ioc("95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "geo" in result.raw_stats

    def test_geo_contains_country_code(self) -> None:
        """geo string contains the country code."""
        ioc = make_ipv4_ioc("95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "DE" in result.raw_stats["geo"]

    def test_geo_contains_city(self) -> None:
        """geo string contains the city."""
        ioc = make_ipv4_ioc("95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "Nuremberg" in result.raw_stats["geo"]

    def test_geo_contains_asn(self) -> None:
        """geo string contains ASN number."""
        ioc = make_ipv4_ioc("95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "AS24940" in result.raw_stats["geo"]

    def test_geo_uses_middle_dot_separator(self) -> None:
        """geo string uses middle-dot (U+00B7) as separator between fields."""
        ioc = make_ipv4_ioc("95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "\u00b7" in result.raw_stats["geo"], (
            "geo separator must be middle dot (U+00B7)"
        )

    def test_geo_format_cc_city_asn_isp(self) -> None:
        """geo string is formatted as 'CC · City · ASN (ISP)'."""
        ioc = make_ipv4_ioc("95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        geo = result.raw_stats["geo"]
        # Should be: "DE · Nuremberg · AS24940 (Hetzner Online GmbH)"
        assert "DE" in geo
        assert "Nuremberg" in geo
        assert "AS24940" in geo
        assert "Hetzner Online GmbH" in geo


class TestFlagsFiltering:

    def test_flags_field_present_as_list(self) -> None:
        """raw_stats must contain a 'flags' list."""
        ioc = make_ipv4_ioc("95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "flags" in result.raw_stats
        assert isinstance(result.raw_stats["flags"], list)

    @pytest.mark.parametrize("ip,response_body", [
        ("95.172.185.24", IPINFO_PUBLIC_IP_RESPONSE),
        ("1.2.3.4", IPINFO_MOSCOW_RESPONSE),
        ("1.2.3.4", IPINFO_LONDON_RESPONSE),
        ("8.8.8.8", IPINFO_MINIMAL_RESPONSE),
    ], ids=["germany", "moscow", "london", "minimal"])
    def test_flags_always_empty(self, ip: str, response_body: dict) -> None:
        """flags list is always empty — ipinfo.io free tier has no flag data."""
        ioc = make_ipv4_ioc(ip)
        mock_resp = make_mock_response(200, response_body)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["flags"] == [], (
            f"ipinfo.io free tier has no flag data — expected [], got: {result.raw_stats['flags']!r}"
        )


class TestPrivateIP:

    def test_private_ip_returns_no_data_with_empty_raw_stats(self) -> None:
        """HTTP 404 (private IP) -> EnrichmentResult(verdict='no_data', raw_stats={})."""
        ioc = make_ipv4_ioc("192.168.1.1")
        # ipinfo.io returns HTTP 404 for private/reserved IPs — do NOT call raise_for_status
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status = MagicMock()

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"Private IP must return EnrichmentResult (not EnrichmentError), got {type(result).__name__}"
        )
        assert result.verdict == "no_data"
        assert result.raw_stats == {}, (
            f"Private IP must return empty raw_stats, got: {result.raw_stats!r}"
        )


class TestLookupErrors:

    def test_http_429_rate_limit(self) -> None:
        """HTTP 429 -> EnrichmentError with 'HTTP 429' in error."""
        ioc = make_ipv4_ioc("8.8.8.8")
        mock_resp = make_mock_response(429)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "IP Context"
        assert "HTTP 429" in result.error


class TestRequestURL:

    def test_request_url_uses_https(self) -> None:
        """ipinfo.io uses HTTPS — URL must start with https://."""
        ioc = make_ipv4_ioc("8.8.8.8")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert called_url.startswith("https://"), (
            f"ipinfo.io requires HTTPS, got: {called_url}"
        )

    def test_request_url_uses_ipinfo_io(self) -> None:
        """Request URL must use ipinfo.io domain."""
        ioc = make_ipv4_ioc("8.8.8.8")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert "ipinfo.io" in called_url, f"URL must use ipinfo.io, got: {called_url}"

    def test_request_url_includes_ip(self) -> None:
        """Request URL must include the IP value."""
        ioc = make_ipv4_ioc("8.8.8.8")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert "8.8.8.8" in called_url

    def test_request_url_ends_with_json(self) -> None:
        """Request URL must end with /json (ipinfo.io JSON endpoint)."""
        ioc = make_ipv4_ioc("8.8.8.8")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert called_url.endswith("/json"), (
            f"ipinfo.io URL must end with /json, got: {called_url}"
        )


class TestIPv6Support:

    def test_ipv6_public_returns_enrichment_result(self) -> None:
        """IPv6 IOC is supported and returns EnrichmentResult."""
        ipv6 = "2001:db8::1"
        ioc = make_ipv6_ioc(ipv6)
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"
