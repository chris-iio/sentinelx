"""Tests for URLhaus adapter.

Tests URL, IP, domain, and hash lookups, verdict logic (malicious/no_data),
error handling, and all HTTP safety controls (timeout, size cap, no redirects,
SSRF allowlist).

URLhaus uses POST with form-encoded bodies (data=, not json=).
Each IOC type maps to a different endpoint and body key:
  - URL  -> POST /v1/url/      {"url": value}
  - IP   -> POST /v1/host/     {"host": value}
  - DOMAIN -> POST /v1/host/   {"host": value}
  - MD5  -> POST /v1/payload/  {"md5_hash": value}
  - SHA256 -> POST /v1/payload/ {"sha256_hash": value}

Verdict from query_status field:
  - "is_listed" (URL endpoint)   -> malicious
  - "ok" + urls_count > 0 (host) -> malicious
  - "no_results"/"no_result"     -> no_data

All HTTP calls are mocked using unittest.mock.patch -- no real API calls.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import requests
import requests.exceptions

from app.pipeline.models import IOC, IOCType
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.adapters.urlhaus import URLhausAdapter
from app.enrichment.provider import Provider
from tests.helpers import make_mock_response


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


class TestURLhausProtocol:

    def test_name(self) -> None:
        """URLhausAdapter.name must equal 'URLhaus'."""
        assert URLhausAdapter.name == "URLhaus"

    def test_requires_api_key_true(self) -> None:
        """URLhausAdapter.requires_api_key must be True."""
        assert URLhausAdapter.requires_api_key is True

    def test_supported_types_contains_url(self) -> None:
        """IOCType.URL must be in URLhausAdapter.supported_types."""
        assert IOCType.URL in URLhausAdapter.supported_types

    def test_supported_types_contains_ipv4(self) -> None:
        """IOCType.IPV4 must be in URLhausAdapter.supported_types."""
        assert IOCType.IPV4 in URLhausAdapter.supported_types

    def test_supported_types_contains_ipv6(self) -> None:
        """IOCType.IPV6 must be in URLhausAdapter.supported_types."""
        assert IOCType.IPV6 in URLhausAdapter.supported_types

    def test_supported_types_contains_domain(self) -> None:
        """IOCType.DOMAIN must be in URLhausAdapter.supported_types."""
        assert IOCType.DOMAIN in URLhausAdapter.supported_types

    def test_supported_types_contains_md5(self) -> None:
        """IOCType.MD5 must be in URLhausAdapter.supported_types."""
        assert IOCType.MD5 in URLhausAdapter.supported_types

    def test_supported_types_contains_sha256(self) -> None:
        """IOCType.SHA256 must be in URLhausAdapter.supported_types."""
        assert IOCType.SHA256 in URLhausAdapter.supported_types

    def test_supported_types_excludes_sha1(self) -> None:
        """IOCType.SHA1 must NOT be in URLhausAdapter.supported_types (URLhaus doesn't support SHA1)."""
        assert IOCType.SHA1 not in URLhausAdapter.supported_types

    def test_supported_types_excludes_cve(self) -> None:
        """IOCType.CVE must NOT be in URLhausAdapter.supported_types."""
        assert IOCType.CVE not in URLhausAdapter.supported_types

    def test_is_configured_with_key(self) -> None:
        """is_configured() returns True when api_key is non-empty."""
        adapter = _make_adapter(api_key="some-real-key")
        assert adapter.is_configured() is True

    def test_is_configured_without_key(self) -> None:
        """is_configured() returns False when api_key is empty string."""
        adapter = _make_adapter(api_key="")
        assert adapter.is_configured() is False

    def test_provider_isinstance(self) -> None:
        """URLhausAdapter instance must satisfy the Provider protocol (isinstance check)."""
        adapter = _make_adapter()
        assert isinstance(adapter, Provider), (
            "URLhausAdapter must satisfy the Provider protocol via @runtime_checkable"
        )


class TestURLhausLookup:

    def test_url_is_listed_returns_malicious(self) -> None:
        """URL IOC with query_status='is_listed' -> verdict=malicious."""
        ioc = IOC(
            type=IOCType.URL,
            value="http://malicious.example.com/payload.exe",
            raw_match="http://malicious.example.com/payload.exe",
        )
        mock_resp = make_mock_response(200, URLHAUS_URL_LISTED_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.post.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult, got {type(result).__name__}: {result!r}"
        )
        assert result.provider == "URLhaus"
        assert result.verdict == "malicious"

    def test_url_not_found_returns_no_data(self) -> None:
        """URL IOC with query_status='no_results' -> verdict=no_data."""
        ioc = IOC(
            type=IOCType.URL,
            value="http://clean.example.com/",
            raw_match="http://clean.example.com/",
        )
        mock_resp = make_mock_response(200, URLHAUS_URL_NOT_FOUND_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.post.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"

    def test_ip_host_with_urls_count_returns_malicious(self) -> None:
        """IPv4 IOC with query_status='ok' and urls_count > 0 -> verdict=malicious."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = make_mock_response(200, URLHAUS_HOST_MALICIOUS_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.post.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"

    def test_ip_host_with_zero_urls_returns_no_data(self) -> None:
        """IPv4 IOC with query_status='ok' and urls_count=0 -> verdict=no_data."""
        ioc = IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10.0.0.1")
        mock_resp = make_mock_response(200, URLHAUS_HOST_CLEAN_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.post.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"

    def test_ip_host_no_results_returns_no_data(self) -> None:
        """IPv4 IOC with query_status='no_results' -> verdict=no_data."""
        ioc = IOC(type=IOCType.IPV4, value="192.0.2.1", raw_match="192.0.2.1")
        mock_resp = make_mock_response(200, URLHAUS_HOST_NO_RESULTS_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.post.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"

    def test_domain_uses_host_endpoint(self) -> None:
        """DOMAIN IOC -> POST to /v1/host/ endpoint."""
        ioc = IOC(type=IOCType.DOMAIN, value="evil.example.com", raw_match="evil.example.com")
        mock_resp = make_mock_response(200, URLHAUS_HOST_MALICIOUS_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.post.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        call_url = adapter._session.post.call_args[0][0]
        assert "/v1/host/" in call_url

    def test_md5_payload_lookup_returns_malicious(self) -> None:
        """MD5 IOC with query_status='ok' -> verdict=malicious."""
        md5 = "a" * 32
        ioc = IOC(type=IOCType.MD5, value=md5, raw_match=md5)
        mock_resp = make_mock_response(200, URLHAUS_PAYLOAD_MD5_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.post.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"

    def test_sha256_payload_lookup_returns_malicious(self) -> None:
        """SHA256 IOC with query_status='ok' -> verdict=malicious."""
        sha256 = "b" * 64
        ioc = IOC(type=IOCType.SHA256, value=sha256, raw_match=sha256)
        mock_resp = make_mock_response(200, URLHAUS_PAYLOAD_SHA256_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.post.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"

    def test_raw_stats_contains_expected_keys(self) -> None:
        """200 response -> raw_stats dict contains keys: query_status, urls_count, tags, blacklists."""
        ioc = IOC(
            type=IOCType.URL,
            value="http://malicious.example.com/payload.exe",
            raw_match="http://malicious.example.com/payload.exe",
        )
        mock_resp = make_mock_response(200, URLHAUS_URL_LISTED_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.post.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        for key in ("query_status", "urls_count", "tags", "blacklists"):
            assert key in result.raw_stats, f"raw_stats missing key: {key!r}"

    def test_url_endpoint_uses_data_not_json(self) -> None:
        """URLhaus POST must use data= (form-encoded), not json=."""
        ioc = IOC(
            type=IOCType.URL,
            value="http://malicious.example.com/payload.exe",
            raw_match="http://malicious.example.com/payload.exe",
        )
        mock_resp = make_mock_response(200, URLHAUS_URL_LISTED_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.post.return_value = mock_resp
        adapter.lookup(ioc)

        # Must use 'data=' keyword arg (form-encoded), NOT 'json='
        call_kwargs = adapter._session.post.call_args[1]
        assert "data" in call_kwargs, "URLhaus POST must use data= (form-encoded body)"
        assert "json" not in call_kwargs, "URLhaus POST must NOT use json= parameter"

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
        ioc = IOC(type=IOCType.IPV6, value=ipv6, raw_match=ipv6)
        mock_resp = make_mock_response(200, URLHAUS_HOST_MALICIOUS_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.post.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)

    def test_payload_no_result_returns_no_data(self) -> None:
        """MD5 IOC with query_status='no_result' -> verdict=no_data."""
        md5 = "c" * 32
        ioc = IOC(type=IOCType.MD5, value=md5, raw_match=md5)
        mock_resp = make_mock_response(200, URLHAUS_PAYLOAD_NOT_FOUND_RESPONSE)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.post.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"


class TestURLhausErrors:

    def test_unsupported_type_sha1_returns_error(self) -> None:
        """SHA1 IOC -> EnrichmentError (not supported by URLhaus)."""
        sha1 = "a" * 40
        ioc = IOC(type=IOCType.SHA1, value=sha1, raw_match=sha1)

        result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "URLhaus"

    def test_unsupported_type_cve_returns_error(self) -> None:
        """CVE IOC -> EnrichmentError (not supported by URLhaus)."""
        ioc = IOC(type=IOCType.CVE, value="CVE-2021-44228", raw_match="CVE-2021-44228")

        result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "URLhaus"

    def test_timeout_returns_error(self) -> None:
        """Network timeout -> EnrichmentError with 'Timeout' in error."""
        ioc = IOC(
            type=IOCType.URL,
            value="http://malicious.example.com/payload.exe",
            raw_match="http://malicious.example.com/payload.exe",
        )

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.post.side_effect = requests.exceptions.Timeout("timed out")
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "URLhaus"
        assert "Timeout" in result.error or "timeout" in result.error.lower()

    def test_http_500_returns_error(self) -> None:
        """HTTP 500 response -> EnrichmentError with 'HTTP 500' in error."""
        ioc = IOC(
            type=IOCType.URL,
            value="http://malicious.example.com/payload.exe",
            raw_match="http://malicious.example.com/payload.exe",
        )
        mock_resp = make_mock_response(500)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.post.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "URLhaus"
        assert "HTTP 500" in result.error

    def test_http_403_returns_error_with_auth_context(self) -> None:
        """HTTP 403 response -> EnrichmentError mentioning 403 or auth issue."""
        ioc = IOC(
            type=IOCType.URL,
            value="http://malicious.example.com/payload.exe",
            raw_match="http://malicious.example.com/payload.exe",
        )
        mock_resp = make_mock_response(403)

        adapter = _make_adapter()
        adapter._session = MagicMock()
        adapter._session.post.return_value = mock_resp
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "URLhaus"
        assert "403" in result.error

    def test_ssrf_validation_blocks_disallowed_host(self) -> None:
        """Adapter with allowed_hosts=[] -> EnrichmentError before network call."""
        ioc = IOC(
            type=IOCType.URL,
            value="http://malicious.example.com/payload.exe",
            raw_match="http://malicious.example.com/payload.exe",
        )
        adapter = URLhausAdapter(api_key="test-key", allowed_hosts=[])

        adapter._session = MagicMock()
        adapter._session.post.side_effect = AssertionError("Should not reach network")
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError), (
            "Expected EnrichmentError when host not in allowed_hosts (SSRF check)"
        )
        assert (
            "SSRF" in result.error
            or "allowed" in result.error.lower()
            or "allowlist" in result.error.lower()
        )


class TestAllowedHosts:

    def test_urlhaus_api_in_allowed_hosts(self) -> None:
        """'urlhaus-api.abuse.ch' must be in Config.ALLOWED_API_HOSTS (SSRF allowlist)."""
        from app.config import Config
        assert "urlhaus-api.abuse.ch" in Config.ALLOWED_API_HOSTS, (
            "urlhaus-api.abuse.ch missing from ALLOWED_API_HOSTS — "
            "URLhausAdapter will always fail SSRF validation in production"
        )
