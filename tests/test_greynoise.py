"""Tests for GreyNoise Community API adapter — verdict logic and response parsing.

Contract tests (protocol, error handling, safety controls) are in test_adapter_contract.py.

Verdict priority (GreyNoise Community endpoint):
  1. riot == True  -> "clean" (known benign service)
  2. classification == "malicious" -> "malicious"
  3. noise == True AND classification != "malicious" -> "suspicious"
  4. Everything else -> "no_data"

All HTTP calls are mocked using unittest.mock.patch -- no real API calls.
"""
from __future__ import annotations

from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.adapters.greynoise import GreyNoiseAdapter
from tests.helpers import (
    make_mock_response,
    make_ipv4_ioc,
    make_ipv6_ioc,
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


