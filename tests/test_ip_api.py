"""Tests for ip-api.com IP Context adapter.

Tests IP lookups (IPv4/IPv6), geo/rDNS/flags data extraction, error handling,
and all HTTP safety controls (timeout, size cap, no redirects, SSRF allowlist).

ip-api.com API behavior:
  - POST http://ip-api.com/json/{ip}?fields=...
  - 200 + status="success": IP data returned -> verdict=no_data with geo/rDNS/flags
  - 200 + status="fail": Private/reserved IP -> verdict=no_data with empty raw_stats
  - 429: Rate limited -> EnrichmentError("HTTP 429")
  - Timeout -> EnrichmentError("Timeout")

IMPORTANT: ip-api.com always returns HTTP 200. The status field in the JSON body
indicates success/failure, not the HTTP status code.

All HTTP calls are mocked using unittest.mock.patch -- no real API calls.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import requests
import requests.exceptions

from app.pipeline.models import IOC, IOCType
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.adapters.ip_api import IPApiAdapter
from app.enrichment.http_safety import MAX_RESPONSE_BYTES
from app.enrichment.provider import Provider


ALLOWED_HOSTS = ["ip-api.com"]

IP_API_PUBLIC_IP_RESPONSE = {
    "status": "success",
    "countryCode": "DE",
    "city": "Nuremberg",
    "as": "AS24940 Hetzner Online GmbH",
    "asname": "HETZNER-AS",
    "reverse": "static.24.185.172.95.clients.your-server.de",
    "proxy": False,
    "hosting": True,
    "mobile": False,
}

IP_API_PROXY_RESPONSE = {
    "status": "success",
    "countryCode": "US",
    "city": "Chicago",
    "as": "AS3356 Lumen Technologies Inc.",
    "asname": "LEVEL3",
    "reverse": "",
    "proxy": True,
    "hosting": False,
    "mobile": False,
}

IP_API_ALL_FLAGS_RESPONSE = {
    "status": "success",
    "countryCode": "RU",
    "city": "Moscow",
    "as": "AS12389 PJSC Rostelecom",
    "asname": "ROSTELECOM",
    "reverse": "host.example.ru",
    "proxy": True,
    "hosting": True,
    "mobile": True,
}

IP_API_NO_FLAGS_RESPONSE = {
    "status": "success",
    "countryCode": "GB",
    "city": "London",
    "as": "AS5089 Virgin Media Limited",
    "asname": "NTL",
    "reverse": "cpc1-ched.example.com",
    "proxy": False,
    "hosting": False,
    "mobile": False,
}

IP_API_PRIVATE_IP_RESPONSE = {
    "status": "fail",
    "message": "private range",
    "query": "192.168.1.1",
}

IP_API_MINIMAL_RESPONSE = {
    "status": "success",
    "countryCode": "",
    "city": "",
    "as": "",
    "asname": "",
    "reverse": "",
    "proxy": False,
    "hosting": False,
    "mobile": False,
}


def _make_mock_get_response(status_code: int, body: dict | None = None) -> MagicMock:
    """Build a mock requests.Response for GET requests."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if body is not None:
        raw_bytes = json.dumps(body).encode()
        mock_resp.iter_content = MagicMock(return_value=iter([raw_bytes]))
    if status_code >= 400:
        http_err = requests.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status = MagicMock(side_effect=http_err)
    else:
        mock_resp.raise_for_status = MagicMock()
    return mock_resp


def _make_adapter(allowed_hosts: list[str] | None = None) -> IPApiAdapter:
    if allowed_hosts is None:
        allowed_hosts = ALLOWED_HOSTS
    return IPApiAdapter(allowed_hosts=allowed_hosts)


class TestLookupPublicIP:

    def test_public_ip_returns_enrichment_result(self) -> None:
        """Public IP with status=success -> EnrichmentResult (not EnrichmentError)."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult, got {type(result).__name__}: {result!r}"
        )

    def test_public_ip_verdict_is_no_data(self) -> None:
        """IP Context never assigns threat verdicts — verdict is always no_data."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data", (
            f"IP Context must never set threat verdicts, got: {result.verdict!r}"
        )

    def test_public_ip_provider_name(self) -> None:
        """Result provider must be 'IP Context'."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.provider == "IP Context"

    def test_public_ip_detection_counts_always_zero(self) -> None:
        """IP Context is informational only — detection counts are always 0."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.detection_count == 0
        assert result.total_engines == 0

    def test_public_ip_scan_date_is_none(self) -> None:
        """IP Context provides no scan date."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.scan_date is None

    def test_raw_stats_contains_required_fields(self) -> None:
        """raw_stats must contain country_code, city, as_info, asname, reverse, proxy, hosting, mobile."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        for key in ("country_code", "city", "as_info", "asname", "reverse", "proxy", "hosting", "mobile"):
            assert key in result.raw_stats, f"raw_stats missing key: {key!r}"

    def test_raw_stats_country_code(self) -> None:
        """raw_stats['country_code'] populated from countryCode field."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["country_code"] == "DE"

    def test_raw_stats_city(self) -> None:
        """raw_stats['city'] populated from city field."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["city"] == "Nuremberg"

    def test_raw_stats_as_info(self) -> None:
        """raw_stats['as_info'] populated from the 'as' field (full ASN string)."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["as_info"] == "AS24940 Hetzner Online GmbH"

    def test_raw_stats_reverse(self) -> None:
        """raw_stats['reverse'] populated from reverse DNS field."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["reverse"] == "static.24.185.172.95.clients.your-server.de"

    def test_raw_stats_hosting_flag_true(self) -> None:
        """raw_stats['hosting'] is True when API reports hosting=true."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["hosting"] is True

    def test_raw_stats_proxy_flag_false(self) -> None:
        """raw_stats['proxy'] is False when API reports proxy=false."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["proxy"] is False


class TestGeoFormatting:

    def test_geo_field_present(self) -> None:
        """raw_stats must contain a 'geo' pre-formatted string."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "geo" in result.raw_stats

    def test_geo_contains_country_code(self) -> None:
        """geo string contains the country code."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "DE" in result.raw_stats["geo"]

    def test_geo_contains_city(self) -> None:
        """geo string contains the city."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "Nuremberg" in result.raw_stats["geo"]

    def test_geo_contains_asn(self) -> None:
        """geo string contains ASN number."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "AS24940" in result.raw_stats["geo"]

    def test_geo_uses_middle_dot_separator(self) -> None:
        """geo string uses middle-dot (U+00B7) as separator between fields."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "\u00b7" in result.raw_stats["geo"], (
            "geo separator must be middle dot (U+00B7)"
        )

    def test_geo_format_cc_city_asn_isp(self) -> None:
        """geo string is formatted as 'CC · City · ASN (ISP)'."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

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
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "flags" in result.raw_stats
        assert isinstance(result.raw_stats["flags"], list)

    def test_flags_contains_only_true_flags(self) -> None:
        """flags list contains only the names of flags that are True."""
        ioc = IOC(type=IOCType.IPV4, value="95.172.185.24", raw_match="95.172.185.24")
        # hosting=True, proxy=False, mobile=False
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        flags = result.raw_stats["flags"]
        assert "hosting" in flags
        assert "proxy" not in flags
        assert "mobile" not in flags

    def test_flags_all_true(self) -> None:
        """All three flags true -> flags list contains all three."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_get_response(200, IP_API_ALL_FLAGS_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        flags = result.raw_stats["flags"]
        assert set(flags) == {"proxy", "hosting", "mobile"}, (
            f"Expected all three flags, got: {flags!r}"
        )

    def test_flags_none_true(self) -> None:
        """All flags false -> flags list is empty."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_get_response(200, IP_API_NO_FLAGS_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["flags"] == [], (
            f"No flags set, expected empty list, got: {result.raw_stats['flags']!r}"
        )

    def test_flags_proxy_only(self) -> None:
        """Only proxy=True -> flags contains exactly ['proxy']."""
        ioc = IOC(type=IOCType.IPV4, value="5.6.7.8", raw_match="5.6.7.8")
        mock_resp = _make_mock_get_response(200, IP_API_PROXY_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["flags"] == ["proxy"]


class TestPrivateIP:

    def test_private_ip_returns_no_data_result(self) -> None:
        """status=fail (private IP) -> EnrichmentResult(verdict='no_data'), not EnrichmentError."""
        ioc = IOC(type=IOCType.IPV4, value="192.168.1.1", raw_match="192.168.1.1")
        mock_resp = _make_mock_get_response(200, IP_API_PRIVATE_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"Private IP must return EnrichmentResult (not EnrichmentError), got {type(result).__name__}"
        )
        assert result.verdict == "no_data"

    def test_private_ip_returns_empty_raw_stats(self) -> None:
        """status=fail -> raw_stats is empty dict."""
        ioc = IOC(type=IOCType.IPV4, value="192.168.1.1", raw_match="192.168.1.1")
        mock_resp = _make_mock_get_response(200, IP_API_PRIVATE_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats == {}, (
            f"Private IP must return empty raw_stats, got: {result.raw_stats!r}"
        )

    def test_private_ip_is_not_enrichment_error(self) -> None:
        """status=fail -> NOT an EnrichmentError (private IPs are not failures)."""
        ioc = IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10.0.0.1")
        mock_resp = _make_mock_get_response(200, IP_API_PRIVATE_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert not isinstance(result, EnrichmentError), (
            "Private IP status=fail must return EnrichmentResult, not EnrichmentError"
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
        mock_resp = _make_mock_get_response(429)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "IP Context"
        assert "HTTP 429" in result.error

    def test_timeout(self) -> None:
        """Network timeout -> EnrichmentError with 'Timeout' in error."""
        ioc = IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")

        with patch("requests.get", side_effect=requests.exceptions.Timeout("timed out")):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "IP Context"
        assert "Timeout" in result.error or "timeout" in result.error.lower()

    def test_ssrf_validation_blocks_disallowed_host(self) -> None:
        """Adapter with allowed_hosts=[] -> EnrichmentError before network call."""
        ioc = IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")
        adapter = IPApiAdapter(allowed_hosts=[])

        with patch("requests.get") as mock_get:
            mock_get.side_effect = AssertionError("Should not reach network")
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

    def test_request_url_includes_fields_param(self) -> None:
        """Request URL must include ?fields= query parameter."""
        ioc = IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp) as mock_get:
            _make_adapter().lookup(ioc)

        called_url = mock_get.call_args.args[0]
        assert "fields=" in called_url, f"URL must include ?fields= param, got: {called_url}"

    def test_request_url_includes_required_fields(self) -> None:
        """Request URL must include status, countryCode, city, as, asname, reverse, proxy, hosting, mobile in fields."""
        ioc = IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp) as mock_get:
            _make_adapter().lookup(ioc)

        called_url = mock_get.call_args.args[0]
        for field in ("status", "countryCode", "city", "as", "reverse", "proxy", "hosting", "mobile"):
            assert field in called_url, f"Required field {field!r} missing from URL: {called_url}"

    def test_request_url_includes_ip(self) -> None:
        """Request URL must include the IP value."""
        ioc = IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp) as mock_get:
            _make_adapter().lookup(ioc)

        called_url = mock_get.call_args.args[0]
        assert "8.8.8.8" in called_url

    def test_request_url_uses_http_not_https(self) -> None:
        """ip-api.com free tier is HTTP-only — URL must start with http://."""
        ioc = IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp) as mock_get:
            _make_adapter().lookup(ioc)

        called_url = mock_get.call_args.args[0]
        assert called_url.startswith("http://"), (
            f"ip-api.com free tier uses HTTP only, got: {called_url}"
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

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError), (
            f"Expected EnrichmentError for oversized response, got {type(result).__name__}"
        )

    def test_uses_allow_redirects_false(self) -> None:
        """SEC-06: requests.get must be called with allow_redirects=False."""
        ioc = IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp) as mock_get:
            _make_adapter().lookup(ioc)

        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs.get("allow_redirects") is False

    def test_uses_stream_true(self) -> None:
        """SEC-05: requests.get must be called with stream=True."""
        ioc = IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8")
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp) as mock_get:
            _make_adapter().lookup(ioc)

        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs.get("stream") is True


class TestIPv6Support:

    def test_ipv6_public_returns_enrichment_result(self) -> None:
        """IPv6 IOC is supported and returns EnrichmentResult."""
        ipv6 = "2001:db8::1"
        ioc = IOC(type=IOCType.IPV6, value=ipv6, raw_match=ipv6)
        mock_resp = _make_mock_get_response(200, IP_API_PUBLIC_IP_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

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

    def test_config_allows_ip_api(self) -> None:
        """'ip-api.com' must be in Config.ALLOWED_API_HOSTS (SSRF allowlist)."""
        from app.config import Config
        assert "ip-api.com" in Config.ALLOWED_API_HOSTS, (
            "ip-api.com missing from ALLOWED_API_HOSTS — "
            "IPApiAdapter will always fail SSRF validation in production"
        )
