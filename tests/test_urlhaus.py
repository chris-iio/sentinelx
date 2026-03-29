"""Tests for URLhaus adapter — verdict logic, type routing, and response parsing.

Contract tests (protocol, error handling, safety controls) are in test_adapter_contract.py.

All HTTP calls are mocked using unittest.mock.patch -- no real API calls.
"""
from __future__ import annotations

from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.adapters.urlhaus import URLhausAdapter
from tests.helpers import (
    make_mock_response,
    mock_adapter_session,
    make_domain_ioc,
    make_ipv4_ioc,
    make_ipv6_ioc,
    make_md5_ioc,
    make_sha256_ioc,
    make_url_ioc,
)


ALLOWED_HOSTS = ["urlhaus-api.abuse.ch"]

URLHAUS_URL_LISTED_RESPONSE = {
    "query_status": "is_listed",
    "id": "12345",
    "url": "http://malicious.example.com/payload.exe",
    "url_status": "online",
    "date_added": "2024-01-15 12:00:00",
    "threat": "malware_download",
    "blacklists": {"spamhaus_dbl": "not listed", "surbl": "not listed"},
    "tags": ["exe", "emotet"],
    "urls_count": 1,
}

URLHAUS_URL_NOT_FOUND_RESPONSE = {
    "query_status": "no_results",
}

URLHAUS_HOST_MALICIOUS_RESPONSE = {
    "query_status": "ok",
    "urlhaus_reference": "https://urlhaus.abuse.ch/host/1.2.3.4/",
    "blacklists": {"spamhaus_dbl": "not listed"},
    "urls_count": 3,
    "tags": ["emotet"],
    "urls": [
        {"id": "1", "url": "http://1.2.3.4/malware.exe", "url_status": "online"}
    ],
}

URLHAUS_HOST_CLEAN_RESPONSE = {
    "query_status": "ok",
    "urls_count": 0,
    "urls": [],
    "blacklists": {},
    "tags": None,
}

URLHAUS_HOST_NO_RESULTS_RESPONSE = {
    "query_status": "no_results",
}

URLHAUS_PAYLOAD_MD5_RESPONSE = {
    "query_status": "ok",
    "md5_hash": "a" * 32,
    "sha256_hash": "b" * 64,
    "file_type": "exe",
    "file_size": 102400,
    "signature": "Emotet",
    "urls_count": 2,
    "urlhaus_download": "https://urlhaus-api.abuse.ch/v1/download/abc/",
    "tags": ["exe"],
    "urls": [],
}

URLHAUS_PAYLOAD_SHA256_RESPONSE = {
    "query_status": "ok",
    "md5_hash": "a" * 32,
    "sha256_hash": "b" * 64,
    "file_type": "dll",
    "file_size": 65536,
    "signature": "Trickbot",
    "urls_count": 1,
    "tags": ["dll"],
    "urls": [],
}

URLHAUS_PAYLOAD_NOT_FOUND_RESPONSE = {
    "query_status": "no_result",
}




def _make_adapter(api_key: str = "test-api-key", allowed_hosts: list[str] | None = None) -> URLhausAdapter:
    if allowed_hosts is None:
        allowed_hosts = ALLOWED_HOSTS
    return URLhausAdapter(api_key=api_key, allowed_hosts=allowed_hosts)


class TestURLhausLookup:

    def test_url_is_listed_returns_malicious(self) -> None:
        """URL IOC with query_status='is_listed' -> verdict=malicious."""
        ioc = make_url_ioc("http://malicious.example.com/payload.exe")
        mock_resp = make_mock_response(200, URLHAUS_URL_LISTED_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult, got {type(result).__name__}: {result!r}"
        )
        assert result.provider == "URLhaus"
        assert result.verdict == "malicious"

    def test_url_not_found_returns_no_data(self) -> None:
        """URL IOC with query_status='no_results' -> verdict=no_data."""
        ioc = make_url_ioc("http://clean.example.com/")
        mock_resp = make_mock_response(200, URLHAUS_URL_NOT_FOUND_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"

    def test_ip_host_with_urls_count_returns_malicious(self) -> None:
        """IPv4 IOC with query_status='ok' and urls_count > 0 -> verdict=malicious."""
        ioc = make_ipv4_ioc("1.2.3.4")
        mock_resp = make_mock_response(200, URLHAUS_HOST_MALICIOUS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"

    def test_ip_host_with_zero_urls_returns_no_data(self) -> None:
        """IPv4 IOC with query_status='ok' and urls_count=0 -> verdict=no_data."""
        ioc = make_ipv4_ioc("10.0.0.1")
        mock_resp = make_mock_response(200, URLHAUS_HOST_CLEAN_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"

    def test_ip_host_no_results_returns_no_data(self) -> None:
        """IPv4 IOC with query_status='no_results' -> verdict=no_data."""
        ioc = make_ipv4_ioc("192.0.2.1")
        mock_resp = make_mock_response(200, URLHAUS_HOST_NO_RESULTS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"

    def test_domain_uses_host_endpoint(self) -> None:
        """DOMAIN IOC -> POST to /v1/host/ endpoint."""
        ioc = make_domain_ioc("evil.example.com")
        mock_resp = make_mock_response(200, URLHAUS_HOST_MALICIOUS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        call_url = adapter._session.post.call_args[0][0]
        assert "/v1/host/" in call_url

    def test_md5_payload_lookup_returns_malicious(self) -> None:
        """MD5 IOC with query_status='ok' -> verdict=malicious."""
        md5 = "a" * 32
        ioc = make_md5_ioc(md5)
        mock_resp = make_mock_response(200, URLHAUS_PAYLOAD_MD5_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"

    def test_sha256_payload_lookup_returns_malicious(self) -> None:
        """SHA256 IOC with query_status='ok' -> verdict=malicious."""
        sha256 = "b" * 64
        ioc = make_sha256_ioc(sha256)
        mock_resp = make_mock_response(200, URLHAUS_PAYLOAD_SHA256_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"

    def test_raw_stats_contains_expected_keys(self) -> None:
        """200 response -> raw_stats dict contains keys: query_status, urls_count, tags, blacklists."""
        ioc = make_url_ioc("http://malicious.example.com/payload.exe")
        mock_resp = make_mock_response(200, URLHAUS_URL_LISTED_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        for key in ("query_status", "urls_count", "tags", "blacklists"):
            assert key in result.raw_stats, f"raw_stats missing key: {key!r}"

    def test_url_endpoint_uses_data_not_json(self) -> None:
        """URLhaus POST must use data= (form-encoded), not json=."""
        ioc = make_url_ioc("http://malicious.example.com/payload.exe")
        mock_resp = make_mock_response(200, URLHAUS_URL_LISTED_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)
        adapter.lookup(ioc)

        # Must use 'data=' keyword arg (form-encoded), NOT 'json='
        call_kwargs = adapter._session.post.call_args[1]
        assert "data" in call_kwargs, "URLhaus POST must use data= (form-encoded body)"
        assert call_kwargs.get("json") is None, "URLhaus POST must NOT send a json body"

    def test_url_post_sends_auth_key_header(self) -> None:
        """URLhaus POST must include Auth-Key header with the API key."""
        # Headers are set on the persistent session in __init__
        adapter = _make_adapter(api_key="my-secret-key")
        headers = dict(adapter._session.headers)
        assert "Auth-Key" in headers, "URLhaus POST must include Auth-Key header"
        assert headers["Auth-Key"] == "my-secret-key"

    def test_ipv6_host_lookup(self) -> None:
        """IPv6 IOC -> POST to /v1/host/ endpoint, can return malicious."""
        ipv6 = "2001:db8::1"
        ioc = make_ipv6_ioc(ipv6)
        mock_resp = make_mock_response(200, URLHAUS_HOST_MALICIOUS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)

    def test_payload_no_result_returns_no_data(self) -> None:
        """MD5 IOC with query_status='no_result' -> verdict=no_data."""
        md5 = "c" * 32
        ioc = make_md5_ioc(md5)
        mock_resp = make_mock_response(200, URLHAUS_PAYLOAD_NOT_FOUND_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"


class TestURLhausErrors:

    def test_http_500_returns_error(self) -> None:
        """HTTP 500 response -> EnrichmentError with 'HTTP 500' in error."""
        ioc = make_url_ioc("http://malicious.example.com/payload.exe")
        mock_resp = make_mock_response(500)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "URLhaus"
        assert "HTTP 500" in result.error

    def test_http_403_returns_error_with_auth_context(self) -> None:
        """HTTP 403 response -> EnrichmentError mentioning 403 or auth issue."""
        ioc = make_url_ioc("http://malicious.example.com/payload.exe")
        mock_resp = make_mock_response(403)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "URLhaus"
        assert "403" in result.error

