"""Tests for VirusTotal API v3 adapter.

Tests endpoint mapping, response parsing, error handling, and all four
HTTP safety controls (SEC-04, SEC-05, SEC-06, SEC-07/SEC-16).

All HTTP calls are mocked using unittest.mock.patch — no real API calls.
"""
from __future__ import annotations

import base64
import json
from unittest.mock import MagicMock, patch, call

import pytest
import requests

from app.pipeline.models import IOC, IOCType
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.adapters.virustotal import VTAdapter, VT_BASE
from app.enrichment.http_safety import MAX_RESPONSE_BYTES, TIMEOUT


ALLOWED_HOSTS = ["www.virustotal.com"]
FAKE_API_KEY = "test-api-key-abc123"

VT_IP_RESPONSE = {
    "data": {
        "type": "ip_address",
        "id": "1.2.3.4",
        "attributes": {
            "last_analysis_stats": {
                "malicious": 5,
                "suspicious": 0,
                "harmless": 60,
                "undetected": 8,
                "timeout": 0,
            },
            "last_analysis_date": 1700000000,
        },
    }
}

VT_CLEAN_RESPONSE = {
    "data": {
        "type": "domain",
        "id": "example.com",
        "attributes": {
            "last_analysis_stats": {
                "malicious": 0,
                "suspicious": 0,
                "harmless": 70,
                "undetected": 3,
                "timeout": 0,
            },
            "last_analysis_date": 1700000000,
        },
    }
}

VT_HASH_RESPONSE = {
    "data": {
        "type": "file",
        "id": "abc123",
        "attributes": {
            "last_analysis_stats": {
                "malicious": 10,
                "suspicious": 2,
                "harmless": 55,
                "undetected": 3,
                "timeout": 0,
            },
            "last_analysis_date": 1700000000,
        },
    }
}


def _make_mock_response(status_code: int, body: dict | None = None) -> MagicMock:
    """Build a mock requests.Response object."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if body is not None:
        raw_bytes = json.dumps(body).encode()
        # iter_content yields the full body in one chunk
        mock_resp.iter_content = MagicMock(return_value=iter([raw_bytes]))
    if status_code >= 400:
        http_err = requests.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status = MagicMock(side_effect=http_err)
    else:
        mock_resp.raise_for_status = MagicMock()
    return mock_resp


def _make_adapter() -> VTAdapter:
    return VTAdapter(api_key=FAKE_API_KEY, allowed_hosts=ALLOWED_HOSTS)


class TestLookupSuccess:
    def test_lookup_ipv4_success(self) -> None:
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_response(200, VT_IP_RESPONSE)

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.return_value = mock_resp

            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"
        assert result.detection_count == 5
        assert result.provider == "VirusTotal"
        assert result.scan_date is not None
        # scan_date must be ISO8601
        assert "T" in result.scan_date

    def test_lookup_ipv4_uses_correct_endpoint(self) -> None:
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_response(200, VT_IP_RESPONSE)

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.return_value = mock_resp

            _make_adapter().lookup(ioc)

        call_url = mock_session.get.call_args[0][0]
        assert "/ip_addresses/1.2.3.4" in call_url

    def test_lookup_domain_success(self) -> None:
        ioc = IOC(type=IOCType.DOMAIN, value="example.com", raw_match="example.com")
        mock_resp = _make_mock_response(200, VT_CLEAN_RESPONSE)

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.return_value = mock_resp

            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "clean"
        call_url = mock_session.get.call_args[0][0]
        assert "/domains/example.com" in call_url

    def test_lookup_url_uses_base64_id(self) -> None:
        url_value = "https://evil.com/malware"
        expected_id = base64.urlsafe_b64encode(url_value.encode()).decode().strip("=")
        ioc = IOC(type=IOCType.URL, value=url_value, raw_match=url_value)
        mock_resp = _make_mock_response(200, VT_IP_RESPONSE)

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.return_value = mock_resp

            _make_adapter().lookup(ioc)

        call_url = mock_session.get.call_args[0][0]
        # Must use base64 ID — never the raw URL
        assert f"/urls/{expected_id}" in call_url
        assert "evil.com" not in call_url

    def test_lookup_hash_sha256(self) -> None:
        sha256 = "a" * 64
        ioc = IOC(type=IOCType.SHA256, value=sha256, raw_match=sha256)
        mock_resp = _make_mock_response(200, VT_HASH_RESPONSE)

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.return_value = mock_resp

            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        call_url = mock_session.get.call_args[0][0]
        assert f"/files/{sha256}" in call_url

    def test_lookup_md5_uses_files_endpoint(self) -> None:
        md5 = "d" * 32
        ioc = IOC(type=IOCType.MD5, value=md5, raw_match=md5)
        mock_resp = _make_mock_response(200, VT_HASH_RESPONSE)

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.return_value = mock_resp

            _make_adapter().lookup(ioc)

        call_url = mock_session.get.call_args[0][0]
        assert f"/files/{md5}" in call_url

    def test_lookup_sha1_uses_files_endpoint(self) -> None:
        sha1 = "e" * 40
        ioc = IOC(type=IOCType.SHA1, value=sha1, raw_match=sha1)
        mock_resp = _make_mock_response(200, VT_HASH_RESPONSE)

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.return_value = mock_resp

            _make_adapter().lookup(ioc)

        call_url = mock_session.get.call_args[0][0]
        assert f"/files/{sha1}" in call_url


class TestLookupErrors:
    def test_lookup_cve_returns_error(self) -> None:
        ioc = IOC(type=IOCType.CVE, value="CVE-2024-1234", raw_match="CVE-2024-1234")
        result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "VirusTotal"
        assert "Unsupported" in result.error or "unsupported" in result.error.lower()

    def test_lookup_404_returns_no_data(self) -> None:
        ioc = IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10.0.0.1")
        mock_resp = _make_mock_response(404)

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.return_value = mock_resp

            result = _make_adapter().lookup(ioc)

        # 404 = VT has no record — must be EnrichmentResult, NOT EnrichmentError
        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult for 404, got {type(result).__name__}: "
            f"{result!r}"
        )
        assert result.verdict == "no_data"

    def test_lookup_429_returns_rate_limit_error(self) -> None:
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_response(429)

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.return_value = mock_resp

            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert "Rate limit" in result.error or "429" in result.error

    def test_lookup_401_returns_auth_error(self) -> None:
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_response(401)

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.return_value = mock_resp

            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert "Authentication" in result.error or "auth" in result.error.lower() or "401" in result.error

    def test_timeout_returns_error(self) -> None:
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.side_effect = requests.exceptions.Timeout("Connection timed out")

            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert "Timeout" in result.error or "timeout" in result.error.lower()


class TestHTTPSafetyControls:
    """Verify SEC-04 through SEC-07 HTTP safety controls."""

    def test_no_redirects_enforced(self) -> None:
        """SEC-06: allow_redirects=False must be passed."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_response(200, VT_IP_RESPONSE)

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.return_value = mock_resp

            _make_adapter().lookup(ioc)

        kwargs = mock_session.get.call_args[1]
        assert kwargs.get("allow_redirects") is False, (
            f"Expected allow_redirects=False (SEC-06), got {kwargs.get('allow_redirects')!r}"
        )

    def test_timeout_params_enforced(self) -> None:
        """SEC-04: timeout=(5, 30) must be passed."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_response(200, VT_IP_RESPONSE)

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.return_value = mock_resp

            _make_adapter().lookup(ioc)

        kwargs = mock_session.get.call_args[1]
        assert kwargs.get("timeout") == (5, 30), (
            f"Expected timeout=(5, 30) (SEC-04), got {kwargs.get('timeout')!r}"
        )

    def test_stream_enabled(self) -> None:
        """SEC-05 setup: stream=True must be passed."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_response(200, VT_IP_RESPONSE)

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.return_value = mock_resp

            _make_adapter().lookup(ioc)

        kwargs = mock_session.get.call_args[1]
        assert kwargs.get("stream") is True, (
            f"Expected stream=True (SEC-05), got {kwargs.get('stream')!r}"
        )

    def test_response_size_limit(self) -> None:
        """SEC-05: Responses exceeding 1 MB must be rejected."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")

        # Build a mock that yields >1 MB of data
        oversized_chunk = b"x" * (MAX_RESPONSE_BYTES + 1)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.iter_content = MagicMock(return_value=iter([oversized_chunk]))

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.return_value = mock_resp

            result = _make_adapter().lookup(ioc)

        # Oversized response must return an EnrichmentError, not crash or return data
        assert isinstance(result, EnrichmentError), (
            f"Expected EnrichmentError for oversized response, got {type(result).__name__}"
        )

    def test_allowed_hosts_enforced(self) -> None:
        """SEC-07/SEC-16: Requests to non-allowlisted hosts must be rejected."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")

        # Adapter with empty allowlist — should reject ALL outbound requests
        adapter = VTAdapter(api_key=FAKE_API_KEY, allowed_hosts=[])

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            # Session.get should NOT be called — allowlist blocks before network call
            mock_session.get.side_effect = AssertionError("Should not reach network")

            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError), (
            "Expected EnrichmentError when host not in allowed_hosts (SEC-07/SEC-16)"
        )
