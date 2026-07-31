"""Tests for URLhaus adapter — verdict logic, type routing, and response parsing.

Contract tests (protocol, error handling, safety controls) are in test_adapter_contract.py.

All HTTP calls are mocked using unittest.mock.patch -- no real API calls.
"""
from __future__ import annotations

import inspect
from types import MappingProxyType

from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.adapters.urlhaus import (
    URLhausAdapter,
    _parse_response,
    _urlhaus_raw_stats,
    _urlhaus_signals,
    _urlhaus_verdict,
)
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


def test_supported_types_derive_from_endpoint_map() -> None:
    """Supported URLhaus types should stay locked to the endpoint map keys."""
    from app.enrichment.adapters.urlhaus import _ENDPOINT_MAP

    assert isinstance(_ENDPOINT_MAP, MappingProxyType)
    assert URLhausAdapter.supported_types == frozenset(_ENDPOINT_MAP)


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

    def test_result_helper_preserves_provider_envelope(self) -> None:
        """Parsed URLhaus results should keep the provider envelope centralized."""
        from app.enrichment.adapters.urlhaus import _urlhaus_result

        ioc = make_url_ioc("http://malicious.example.com/payload.exe")
        raw_stats = {"query_status": "is_listed", "urls_count": 1}

        result = _urlhaus_result(
            ioc=ioc,
            provider="URLhaus",
            verdict="malicious",
            detection_count=1,
            raw_stats=raw_stats,
        )

        assert result.ioc is ioc
        assert result.provider == "URLhaus"
        assert result.verdict == "malicious"
        assert result.detection_count == 1
        assert result.total_engines == 1
        assert result.scan_date is None
        assert result.raw_stats is raw_stats

    def test_missing_blacklists_avoids_eager_default_dict(self) -> None:
        """Missing blacklist data should not allocate through body.get's default argument."""
        ioc = make_url_ioc("http://clean.example.com/")

        class NoDefaultBody(dict):
            def get(self, key, default=None):
                if key == "blacklists" and default is not None:
                    raise AssertionError("URLhaus blacklist parsing should avoid eager default dict allocation")
                return super().get(key, default)

        result = _parse_response(ioc, NoDefaultBody({"query_status": "no_results"}), "URLhaus")

        assert result.verdict == "no_data"
        assert result.raw_stats["blacklists"] == {}
        assert type(result.raw_stats["blacklists"]) is dict

    def test_parse_response_delegates_verdict_and_raw_stats_helpers(self) -> None:
        """Parser should not own URLhaus verdict or raw_stats mechanics."""
        source = inspect.getsource(_parse_response)

        assert "_urlhaus_signals(body)" in source
        assert "_urlhaus_verdict(signals.query_status, signals.urls_count)" in source
        assert "_urlhaus_raw_stats(" in source
        assert 'body.get("query_status"' not in source
        assert 'body.get("urls_count"' not in source
        assert '"is_listed"' not in source
        assert '"blacklists"' not in source
        assert '"signature"' not in source

    def test_signal_helper_preserves_defaults_and_metadata_identity(self) -> None:
        """URLhaus response-field extraction should live in one signal helper."""
        class NoDefaultBody(dict):
            def get(self, key, default=None):
                expected_defaults = {
                    "query_status": "",
                    "urls_count": 0,
                    "tags": None,
                    "blacklists": None,
                    "signature": None,
                }
                if default != expected_defaults[key]:
                    raise AssertionError("URLhaus signal defaults should stay provider-specific")
                return super().get(key, default)

        tags = ["exe"]
        blacklists = {"spamhaus_dbl": "not listed"}
        signals = _urlhaus_signals(
            NoDefaultBody({
                "query_status": "ok",
                "urls_count": None,
                "tags": tags,
                "blacklists": blacklists,
                "signature": "Emotet",
            })
        )
        missing = _urlhaus_signals(NoDefaultBody({}))

        assert signals.query_status == "ok"
        assert signals.urls_count == 0
        assert signals.tags is tags
        assert signals.blacklists is blacklists
        assert signals.signature == "Emotet"
        assert missing.query_status == ""
        assert missing.urls_count == 0
        assert missing.blacklists == {}
        assert type(missing.blacklists) is dict

    def test_verdict_helper_preserves_status_and_count_semantics(self) -> None:
        """URLhaus verdict helper should preserve listed, host, and no-result behavior."""
        assert _urlhaus_verdict("is_listed", 0) == ("malicious", 1)
        assert _urlhaus_verdict("ok", 3) == ("malicious", 3)
        assert _urlhaus_verdict("ok", 0) == ("no_data", 0)
        assert _urlhaus_verdict("no_results", 7) == ("no_data", 0)
        assert _urlhaus_verdict("no_result", 7) == ("no_data", 0)

    def test_raw_stats_helper_preserves_key_order_and_blacklist_identity(self) -> None:
        """Raw stats helper should preserve URLhaus metadata shape."""
        blacklists = {"spamhaus_dbl": "not listed"}
        tags = ["exe"]
        raw_stats = _urlhaus_raw_stats(
            signals=_urlhaus_signals({
                "query_status": "ok",
                "blacklists": blacklists,
                "tags": tags,
                "signature": "Emotet",
                "urls_count": 3,
            }),
        )

        assert list(raw_stats) == [
            "query_status",
            "urls_count",
            "tags",
            "blacklists",
            "signature",
        ]
        assert raw_stats["blacklists"] is blacklists
        assert raw_stats["tags"] is tags
        assert raw_stats["signature"] == "Emotet"

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
