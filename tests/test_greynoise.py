"""Tests for GreyNoise Community API adapter.

Tests IP lookups, verdict logic (clean/malicious/suspicious/no_data), error handling,
and all HTTP safety controls (timeout, size cap, no redirects, SSRF allowlist).

Verdict priority (GreyNoise Community endpoint):
  1. riot == True  -> "clean" (known benign service: Google, Cloudflare, etc.)
  2. classification == "malicious" -> "malicious"
  3. noise == True AND classification != "malicious" -> "suspicious"
  4. Everything else -> "no_data"

Auth header: lowercase 'key' (NOT 'Key', 'Authorization', or 'X-Api-Key').

404 response: EnrichmentResult(verdict='no_data') — NOT EnrichmentError.
IP is simply not in GreyNoise's database.

All HTTP calls are mocked using unittest.mock.patch -- no real API calls.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import requests
import requests.exceptions

from app.pipeline.models import IOCType
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.adapters.greynoise import GreyNoiseAdapter
from app.enrichment.http_safety import MAX_RESPONSE_BYTES
from app.enrichment.provider import Provider
from tests.helpers import (
    make_mock_response,
    make_domain_ioc,
    make_ipv4_ioc,
    make_ipv6_ioc,
    make_url_ioc,
    mock_adapter_session,
)


ALLOWED_HOSTS = ["api.greynoise.io"]
TEST_API_KEY = "test-greynoise-key-123"

# Sample GreyNoise Community API response bodies

GREYNOISE_RIOT_RESPONSE = {
    "ip": "8.8.8.8",
    "noise": False,
    "riot": True,
    "classification": "benign",
    "name": "Google Public DNS",
    "link": "https://viz.greynoise.io/riot/8.8.8.8",
    "last_seen": "2024-01-15",
    "message": "This IP is commonly seen on the internet",
}

GREYNOISE_MALICIOUS_RESPONSE = {
    "ip": "1.2.3.4",
    "noise": True,
    "riot": False,
    "classification": "malicious",
    "name": "unknown",
    "link": "https://viz.greynoise.io/ip/1.2.3.4",
    "last_seen": "2024-01-14",
    "message": "This IP is actively scanning the internet",
}

GREYNOISE_SUSPICIOUS_RESPONSE = {
    "ip": "5.6.7.8",
    "noise": True,
    "riot": False,
    "classification": "benign",
    "name": "unknown",
    "link": "https://viz.greynoise.io/ip/5.6.7.8",
    "last_seen": "2024-01-13",
    "message": "This IP is actively scanning the internet",
}

GREYNOISE_NO_DATA_RESPONSE = {
    "ip": "10.0.0.1",
    "noise": False,
    "riot": False,
    "classification": "",
    "name": "",
    "link": "",
    "last_seen": None,
    "message": "No data",
}

GREYNOISE_404_RESPONSE = {
    "ip": "192.0.2.99",
    "noise": False,
    "riot": False,
    "message": "IP not observed scanning the internet or providing a legitimate service",
    "status": "unknown",
}




def _make_adapter(
    api_key: str = TEST_API_KEY,
    allowed_hosts: list[str] | None = None,
) -> GreyNoiseAdapter:
    if allowed_hosts is None:
        allowed_hosts = ALLOWED_HOSTS
    return GreyNoiseAdapter(api_key=api_key, allowed_hosts=allowed_hosts)


class TestGreyNoiseProtocol:
    """Tests that GreyNoiseAdapter satisfies the Provider protocol contract."""

    def test_name(self) -> None:
        """GreyNoiseAdapter.name must equal 'GreyNoise'."""
        assert GreyNoiseAdapter.name == "GreyNoise"

    def test_requires_api_key_true(self) -> None:
        """GreyNoiseAdapter.requires_api_key must be True (paid/free-key provider)."""
        assert GreyNoiseAdapter.requires_api_key is True

    def test_supported_types_contains_ipv4(self) -> None:
        """IOCType.IPV4 must be in GreyNoiseAdapter.supported_types."""
        assert IOCType.IPV4 in GreyNoiseAdapter.supported_types

    def test_supported_types_contains_ipv6(self) -> None:
        """IOCType.IPV6 must be in GreyNoiseAdapter.supported_types."""
        assert IOCType.IPV6 in GreyNoiseAdapter.supported_types

    def test_supported_types_excludes_domain(self) -> None:
        """IOCType.DOMAIN must NOT be in GreyNoiseAdapter.supported_types."""
        assert IOCType.DOMAIN not in GreyNoiseAdapter.supported_types

    def test_supported_types_excludes_md5(self) -> None:
        """IOCType.MD5 must NOT be in GreyNoiseAdapter.supported_types."""
        assert IOCType.MD5 not in GreyNoiseAdapter.supported_types

    def test_supported_types_excludes_url(self) -> None:
        """IOCType.URL must NOT be in GreyNoiseAdapter.supported_types."""
        assert IOCType.URL not in GreyNoiseAdapter.supported_types

    def test_is_configured_true_with_key(self) -> None:
        """is_configured() must return True when api_key is non-empty."""
        adapter = _make_adapter(api_key="somekey")
        assert adapter.is_configured() is True

    def test_is_configured_false_with_empty_key(self) -> None:
        """is_configured() must return False when api_key is empty string."""
        adapter = _make_adapter(api_key="")
        assert adapter.is_configured() is False

    def test_isinstance_provider(self) -> None:
        """GreyNoiseAdapter instance must satisfy the Provider protocol (isinstance check)."""
        adapter = _make_adapter()
        assert isinstance(adapter, Provider), (
            "GreyNoiseAdapter must satisfy the Provider protocol via @runtime_checkable"
        )


class TestGreyNoiseLookup:
    """Tests for GreyNoiseAdapter.lookup() verdict logic."""

    def test_riot_true_returns_clean(self) -> None:
        """riot=True IP -> verdict 'clean' (known benign service like Google DNS)."""
        ioc = make_ipv4_ioc("8.8.8.8")
        mock_resp = make_mock_response(200, GREYNOISE_RIOT_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult, got {type(result).__name__}: {result!r}"
        )
        assert result.provider == "GreyNoise"
        assert result.verdict == "clean"

    def test_classification_malicious_returns_malicious(self) -> None:
        """classification='malicious' IP -> verdict 'malicious'."""
        ioc = make_ipv4_ioc("1.2.3.4")
        mock_resp = make_mock_response(200, GREYNOISE_MALICIOUS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.provider == "GreyNoise"
        assert result.verdict == "malicious"

    def test_noise_true_benign_classification_returns_suspicious(self) -> None:
        """noise=True and classification='benign' -> verdict 'suspicious' (mass scanner, not malicious)."""
        ioc = make_ipv4_ioc("5.6.7.8")
        mock_resp = make_mock_response(200, GREYNOISE_SUSPICIOUS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.provider == "GreyNoise"
        assert result.verdict == "suspicious"

    def test_noise_false_riot_false_no_classification_returns_no_data(self) -> None:
        """noise=False, riot=False, no classification -> verdict 'no_data'."""
        ioc = make_ipv4_ioc("10.0.0.1")
        mock_resp = make_mock_response(200, GREYNOISE_NO_DATA_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.provider == "GreyNoise"
        assert result.verdict == "no_data"

    def test_404_returns_no_data_result_not_error(self) -> None:
        """404 response -> EnrichmentResult(verdict='no_data'), NOT EnrichmentError.

        GreyNoise 404 means the IP is not in their database, which is 'no data'
        — not an error condition.
        """
        ioc = make_ipv4_ioc("192.0.2.99")
        mock_resp = make_mock_response(404, GREYNOISE_404_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"404 must return EnrichmentResult (not EnrichmentError), got {type(result).__name__}: {result!r}"
        )
        assert result.verdict == "no_data"
        assert result.detection_count == 0

    def test_404_is_not_enrichment_error(self) -> None:
        """404 response -> not isinstance EnrichmentError."""
        ioc = make_ipv4_ioc("192.0.2.99")
        mock_resp = make_mock_response(404, GREYNOISE_404_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert not isinstance(result, EnrichmentError), (
            "404 from GreyNoise is not an error — it means 'no data', not 'failure'"
        )

    def test_ipv6_lookup_works(self) -> None:
        """IPv6 IOC with malicious classification -> verdict 'malicious'."""
        ipv6 = "2001:db8::bad"
        ioc = make_ipv6_ioc(ipv6)
        response_body = {
            "ip": ipv6,
            "noise": True,
            "riot": False,
            "classification": "malicious",
            "name": "unknown",
            "link": f"https://viz.greynoise.io/ip/{ipv6}",
            "last_seen": "2024-01-10",
        }
        mock_resp = make_mock_response(200, response_body)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"

    def test_raw_stats_content(self) -> None:
        """200 response -> raw_stats contains noise, riot, classification, name, link, last_seen."""
        ioc = make_ipv4_ioc("8.8.8.8")
        mock_resp = make_mock_response(200, GREYNOISE_RIOT_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        for key in ("noise", "riot", "classification", "name", "link", "last_seen"):
            assert key in result.raw_stats, f"raw_stats missing key: {key!r}"

    def test_detection_count_malicious_is_one(self) -> None:
        """Malicious verdict -> detection_count=1, total_engines=1."""
        ioc = make_ipv4_ioc("1.2.3.4")
        mock_resp = make_mock_response(200, GREYNOISE_MALICIOUS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.detection_count == 1
        assert result.total_engines == 1

    def test_detection_count_clean_is_zero(self) -> None:
        """Clean verdict (riot=True) -> detection_count=0, total_engines=1."""
        ioc = make_ipv4_ioc("8.8.8.8")
        mock_resp = make_mock_response(200, GREYNOISE_RIOT_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.detection_count == 0
        assert result.total_engines == 1

    def test_scan_date_is_last_seen(self) -> None:
        """scan_date should equal body.last_seen value."""
        ioc = make_ipv4_ioc("1.2.3.4")
        mock_resp = make_mock_response(200, GREYNOISE_MALICIOUS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.scan_date == GREYNOISE_MALICIOUS_RESPONSE["last_seen"]

    def test_auth_header_uses_lowercase_key(self) -> None:
        """CRITICAL: GreyNoise auth header must be lowercase 'key', NOT 'Key' or 'Authorization'."""
        # Headers are set on the persistent session in __init__
        adapter = _make_adapter(api_key="myapikey")
        headers = dict(adapter._session.headers)
        assert "key" in headers, (
            f"GreyNoise auth header must use lowercase 'key', got headers: {headers}"
        )
        assert headers["key"] == "myapikey"
        assert "Key" not in headers, "Header must be lowercase 'key', not capital 'Key'"
        assert "Authorization" not in headers, "Header must be 'key', not 'Authorization'"


class TestGreyNoiseErrors:
    """Tests for error handling in GreyNoiseAdapter.lookup()."""

    def test_unsupported_type_domain(self) -> None:
        """DOMAIN IOC -> EnrichmentError, provider='GreyNoise', error contains 'Unsupported'."""
        ioc = make_domain_ioc("evil.com")

        result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "GreyNoise"
        assert "unsupported" in result.error.lower() or "Unsupported" in result.error

    def test_unsupported_type_url(self) -> None:
        """URL IOC -> EnrichmentError (URLs not supported by GreyNoise IP endpoint)."""
        ioc = make_url_ioc("http://evil.com/path")

        result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "GreyNoise"

    def test_timeout(self) -> None:
        """Network timeout -> EnrichmentError with 'Timeout' in error."""
        ioc = make_ipv4_ioc("8.8.8.8")

        adapter = _make_adapter()
        mock_adapter_session(adapter, side_effect=requests.exceptions.Timeout("timed out"))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "GreyNoise"
        assert "timed out" in result.error.lower() or "Timeout" in result.error

    def test_http_500(self) -> None:
        """HTTP 500 -> EnrichmentError with 'HTTP 500' in error."""
        ioc = make_ipv4_ioc("8.8.8.8")
        mock_resp = make_mock_response(500)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "GreyNoise"
        assert "HTTP 500" in result.error

    def test_ssrf_validation_blocks_disallowed_host(self) -> None:
        """Adapter with allowed_hosts=[] -> EnrichmentError before network call."""
        ioc = make_ipv4_ioc("8.8.8.8")
        adapter = GreyNoiseAdapter(api_key=TEST_API_KEY, allowed_hosts=[])

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


class TestAllowedHosts:
    """Integration test: SSRF allowlist must include GreyNoise hostname."""

    def test_config_allows_greynoise(self) -> None:
        """'api.greynoise.io' must be in Config.ALLOWED_API_HOSTS (SSRF allowlist)."""
        from app.config import Config
        assert "api.greynoise.io" in Config.ALLOWED_API_HOSTS, (
            "api.greynoise.io missing from ALLOWED_API_HOSTS — "
            "GreyNoiseAdapter will always fail SSRF validation in production"
        )
