"""Tests for ipinfo.io IP Context adapter.

Tests IP lookups (IPv4/IPv6), geo/rDNS/ASN data extraction, error handling,
and all HTTP safety controls (timeout, size cap, no redirects, SSRF allowlist).

ipinfo.io API behavior:
  - GET https://ipinfo.io/{ip}/json
  - 200 + "country" in body: IP data returned -> verdict=no_data with geo/rDNS/ASN
  - 404: Private/reserved IP -> verdict=no_data with empty raw_stats
  - 429: Rate limited -> EnrichmentError("HTTP 429")
  - Timeout -> EnrichmentError("Timeout")

IMPORTANT: ipinfo.io uses HTTP status codes (not a JSON "status" field) to
distinguish public IPs from private/reserved ones. HTTP 404 means no data
(private range) — not a network failure.

All HTTP calls are mocked using unittest.mock — no real API calls.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import requests
import requests.exceptions

from app.pipeline.models import IOC, IOCType
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.adapters.ip_api import IPApiAdapter
from app.enrichment.http_safety import MAX_RESPONSE_BYTES
from app.enrichment.provider import Provider
from tests.helpers import make_mock_response


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
        """Public IP with HTTP 200 + country field -> EnrichmentResult (not EnrichmentError)."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult, got {type(result).__name__}: {result!r}"
        )

    def test_public_ip_verdict_is_no_data(self) -> None:
        """IP Context never assigns threat verdicts — verdict is always no_data."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data", (
            f"IP Context must never set threat verdicts, got: {result.verdict!r}"
        )

    def test_public_ip_provider_name(self) -> None:
        """Result provider must be 'IP Context'."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.provider == "IP Context"

    def test_public_ip_detection_counts_always_zero(self) -> None:
        """IP Context is informational only — detection counts are always 0."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.detection_count == 0
        assert result.total_engines == 0

    def test_public_ip_scan_date_is_none(self) -> None:
        """IP Context provides no scan date."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.scan_date is None

    def test_raw_stats_contains_required_fields(self) -> None:
        """raw_stats must contain country_code, city, as_info, asname, reverse, proxy, hosting, mobile."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        for key in ("country_code", "city", "as_info", "asname", "reverse", "proxy", "hosting", "mobile"):
            assert key in result.raw_stats, f"raw_stats missing key: {key!r}"

    def test_raw_stats_country_code(self) -> None:
        """raw_stats['country_code'] populated from ipinfo.io 'country' field."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["country_code"] == "DE"

    def test_raw_stats_city(self) -> None:
        """raw_stats['city'] populated from ipinfo.io 'city' field."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["city"] == "Nuremberg"

    def test_raw_stats_as_info(self) -> None:
        """raw_stats['as_info'] populated from the 'org' field (full ASN string)."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["as_info"] == "AS24940 Hetzner Online GmbH"

    def test_raw_stats_reverse_from_hostname(self) -> None:
        """raw_stats['reverse'] populated from ipinfo.io 'hostname' field."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["reverse"] == "static.24.185.172.95.clients.your-server.de"

    def test_raw_stats_hosting_always_false(self) -> None:
        """raw_stats['hosting'] is always False — ipinfo.io free tier does not provide this."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["hosting"] is False

    def test_raw_stats_proxy_always_false(self) -> None:
        """raw_stats['proxy'] is always False — ipinfo.io free tier does not provide this."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["proxy"] is False


class TestGeoFormatting:

    def test_geo_field_present(self) -> None:
        """raw_stats must contain a 'geo' pre-formatted string."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "geo" in result.raw_stats

    def test_geo_contains_country_code(self) -> None:
        """geo string contains the country code."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "DE" in result.raw_stats["geo"]

    def test_geo_contains_city(self) -> None:
        """geo string contains the city."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "Nuremberg" in result.raw_stats["geo"]

    def test_geo_contains_asn(self) -> None:
        """geo string contains ASN number."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "AS24940" in result.raw_stats["geo"]

    def test_geo_uses_middle_dot_separator(self) -> None:
        """geo string uses middle-dot (U+00B7) as separator between fields."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "\u00b7" in result.raw_stats["geo"], (
            "geo separator must be middle dot (U+00B7)"
        )

    def test_geo_format_cc_city_asn_isp(self) -> None:
        """geo string is formatted as 'CC · City · ASN (ISP)'."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        geo = result.raw_stats["geo"]
        # Should be: "DE · Nuremberg · AS24940 (Hetzner Online GmbH)"
        assert "DE" in geo
        assert "Nuremberg" in geo
        assert "AS24940" in geo
        assert "Hetzner Online GmbH" in geo


class TestFlagsFiltering:

    def test_flags_field_present(self) -> None:
        """raw_stats must contain a 'flags' list."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "flags" in result.raw_stats
        assert isinstance(result.raw_stats["flags"], list)

    def test_flags_always_empty(self) -> None:
        """flags list is always empty — ipinfo.io free tier has no flag data."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["flags"] == [], (
            f"ipinfo.io free tier has no flag data — expected [], got: {result.raw_stats['flags']!r}"
        )

    def test_flags_empty_for_moscow_response(self) -> None:
        """flags list is empty even for non-US IPs."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = make_mock_response(200, IPINFO_MOSCOW_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["flags"] == []

    def test_flags_empty_for_london_response(self) -> None:
        """flags list is always [] regardless of IP origin."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = make_mock_response(200, IPINFO_LONDON_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["flags"] == []

    def test_flags_empty_for_minimal_response(self) -> None:
        """flags list is empty when response has minimal fields."""
        ioc = IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")
        mock_resp = make_mock_response(200, IPINFO_MINIMAL_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["flags"] == []


class TestPrivateIP:

    def test_private_ip_returns_no_data_result(self) -> None:
        """HTTP 404 (private IP) -> EnrichmentResult(verdict='no_data'), not EnrichmentError."""
        ioc = IOC(type=IOCType.IPV4, value="192.168.1.1", raw_match="192.168.1.1")
        # ipinfo.io returns HTTP 404 for private/reserved IPs — do NOT call raise_for_status
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status = MagicMock()

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"Private IP must return EnrichmentResult (not EnrichmentError), got {type(result).__name__}"
        )
        assert result.verdict == "no_data"

    def test_private_ip_returns_empty_raw_stats(self) -> None:
        """HTTP 404 -> raw_stats is empty dict."""
        ioc = IOC(type=IOCType.IPV4, value="192.168.1.1", raw_match="192.168.1.1")
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status = MagicMock()

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats == {}, (
            f"Private IP must return empty raw_stats, got: {result.raw_stats!r}"
        )

    def test_private_ip_is_not_enrichment_error(self) -> None:
        """HTTP 404 -> NOT an EnrichmentError (private IPs are not lookup failures)."""
        ioc = IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10.0.0.1")
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status = MagicMock()

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert not isinstance(result, EnrichmentError), (
            "Private IP HTTP 404 must return EnrichmentResult, not EnrichmentError"
        )


class TestLookupErrors:

    def test_unsupported_type_domain(self) -> None:
        """DOMAIN IOC -> EnrichmentError with 'Unsupported' in error."""
        ioc = IOC(type=IOCType.DOMAIN, value="evil.com", raw_match="evil.com")

        result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "IP Context"
        assert "Unsupported" in result.error or "unsupported" in result.error.lower()

    def test_unsupported_type_md5(self) -> None:
        """MD5 IOC -> EnrichmentError (hashes not supported by IPApiAdapter)."""
        md5 = "a" * 32
        ioc = IOC(type=IOCType.MD5, value=md5, raw_match=md5)

        result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "IP Context"

    def test_http_429_rate_limit(self) -> None:
        """HTTP 429 -> EnrichmentError with 'HTTP 429' in error."""
        ioc = IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")
        mock_resp = make_mock_response(429)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "IP Context"
        assert "HTTP 429" in result.error

    def test_timeout(self) -> None:
        """Network timeout -> EnrichmentError with 'Timeout' in error."""
        ioc = IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.side_effect = requests.exceptions.Timeout("timed out")
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "IP Context"
        assert "Timeout" in result.error or "timeout" in result.error.lower()

    def test_ssrf_validation_blocks_disallowed_host(self) -> None:
        """Adapter with allowed_hosts=[] -> EnrichmentError before network call."""
        ioc = IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")
        adapter = IPApiAdapter(allowed_hosts=[])

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


class TestRequestURL:

    def test_request_url_uses_https(self) -> None:
        """ipinfo.io uses HTTPS — URL must start with https://."""
        ioc = IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert called_url.startswith("https://"), (
            f"ipinfo.io requires HTTPS, got: {called_url}"
        )

    def test_request_url_uses_ipinfo_io(self) -> None:
        """Request URL must use ipinfo.io domain."""
        ioc = IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert "ipinfo.io" in called_url, f"URL must use ipinfo.io, got: {called_url}"

    def test_request_url_includes_ip(self) -> None:
        """Request URL must include the IP value."""
        ioc = IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert "8.8.8.8" in called_url

    def test_request_url_ends_with_json(self) -> None:
        """Request URL must end with /json (ipinfo.io JSON endpoint)."""
        ioc = IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert called_url.endswith("/json"), (
            f"ipinfo.io URL must end with /json, got: {called_url}"
        )


class TestHTTPSafetyControls:

    def test_response_size_limit(self) -> None:
        """SEC-05: Responses exceeding 1 MB must be rejected with EnrichmentError."""
        ioc = IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")

        oversized_chunk = b"x" * (MAX_RESPONSE_BYTES + 1)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.iter_content = MagicMock(return_value=iter([oversized_chunk]))

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError), (
            f"Expected EnrichmentError for oversized response, got {type(result).__name__}"
        )

    def test_uses_allow_redirects_false(self) -> None:
        """SEC-06: requests.get must be called with allow_redirects=False."""
        ioc = IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        adapter.lookup(ioc)

        call_kwargs = adapter._session.get.call_args.kwargs
        assert call_kwargs.get("allow_redirects") is False

    def test_uses_stream_true(self) -> None:
        """SEC-05: requests.get must be called with stream=True."""
        ioc = IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        adapter.lookup(ioc)

        call_kwargs = adapter._session.get.call_args.kwargs
        assert call_kwargs.get("stream") is True


class TestIPv6Support:

    def test_ipv6_public_returns_enrichment_result(self) -> None:
        """IPv6 IOC is supported and returns EnrichmentResult."""
        ipv6 = "2001:db8::1"
        ioc = IOC(type=IOCType.IPV6, value=ipv6, raw_match=ipv6)
        mock_resp = make_mock_response(200, IPINFO_PUBLIC_IP_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.get.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"


class TestSupportedTypes:

    def test_supported_types_contains_ipv4(self) -> None:
        """IOCType.IPV4 must be in IPApiAdapter.supported_types."""
        assert IOCType.IPV4 in IPApiAdapter.supported_types

    def test_supported_types_contains_ipv6(self) -> None:
        """IOCType.IPV6 must be in IPApiAdapter.supported_types."""
        assert IOCType.IPV6 in IPApiAdapter.supported_types

    def test_supported_types_excludes_domain(self) -> None:
        """IOCType.DOMAIN must NOT be in IPApiAdapter.supported_types."""
        assert IOCType.DOMAIN not in IPApiAdapter.supported_types

    def test_supported_types_excludes_md5(self) -> None:
        """IOCType.MD5 must NOT be in IPApiAdapter.supported_types."""
        assert IOCType.MD5 not in IPApiAdapter.supported_types

    def test_supported_types_is_frozenset(self) -> None:
        """supported_types must be a frozenset."""
        assert isinstance(IPApiAdapter.supported_types, frozenset)


class TestProtocolConformance:

    def test_ip_api_adapter_is_provider(self) -> None:
        """IPApiAdapter instance must satisfy the Provider protocol."""
        adapter = IPApiAdapter(allowed_hosts=[])
        assert isinstance(adapter, Provider), (
            "IPApiAdapter must satisfy the Provider protocol via @runtime_checkable"
        )

    def test_ip_api_adapter_name(self) -> None:
        """IPApiAdapter.name must equal 'IP Context'."""
        assert IPApiAdapter.name == "IP Context"

    def test_ip_api_requires_api_key_false(self) -> None:
        """IPApiAdapter.requires_api_key must be False (zero-auth provider)."""
        assert IPApiAdapter.requires_api_key is False

    def test_ip_api_is_configured_always_true(self) -> None:
        """IPApiAdapter.is_configured() must always return True regardless of config."""
        adapter = IPApiAdapter(allowed_hosts=[])
        assert adapter.is_configured() is True


class TestAllowedHostsIntegration:

    def test_config_allows_ipinfo(self) -> None:
        """'ipinfo.io' must be in Config.ALLOWED_API_HOSTS (SSRF allowlist)."""
        from app.config import Config
        assert "ipinfo.io" in Config.ALLOWED_API_HOSTS, (
            "ipinfo.io missing from ALLOWED_API_HOSTS — "
            "IPApiAdapter will always fail SSRF validation in production"
        )

    def test_config_does_not_allow_ip_api_com(self) -> None:
        """'ip-api.com' must NOT be in Config.ALLOWED_API_HOSTS (removed in D032 migration)."""
        from app.config import Config
        assert "ip-api.com" not in Config.ALLOWED_API_HOSTS, (
            "ip-api.com must be removed from ALLOWED_API_HOSTS — adapter now uses ipinfo.io"
        )
