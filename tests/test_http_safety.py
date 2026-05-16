"""Tests for safe_request() — canonical HTTP path for all enrichment adapters.

Covers: success paths (GET/POST), SSRF rejection, every exception type in the
chain, pre_raise_hook short-circuit and pass-through, and stream/redirect flags.
"""
from __future__ import annotations

import builtins
from unittest.mock import MagicMock

import pytest
import requests

from app.enrichment import http_safety
from app.enrichment.http_safety import read_limited, safe_request, validate_endpoint
from app.enrichment.models import EnrichmentError, EnrichmentResult
from tests.helpers import make_mock_response, make_ipv4_ioc


ALLOWED = ["api.example.com"]
URL = "https://api.example.com/v1/check"
IOC = make_ipv4_ioc("1.2.3.4")
PROVIDER = "TestProvider"


def _make_session_with(mock_resp: MagicMock, method: str = "get") -> MagicMock:
    """Build a mock session whose get/post returns the given response."""
    session = MagicMock()
    getattr(session, method).return_value = mock_resp
    return session


# ── Success paths ──────────────────────────────────────────────────────────


class TestSafeRequestSuccess:
    def test_get_success(self):
        body = {"status": "ok", "data": [1, 2, 3]}
        resp = make_mock_response(200, body)
        session = _make_session_with(resp)

        result = safe_request(session, URL, ALLOWED, IOC, PROVIDER)

        assert result == body
        session.get.assert_called_once()

    def test_post_json(self):
        body = {"result": "found"}
        resp = make_mock_response(200, body)
        session = _make_session_with(resp, method="post")
        payload = {"query": "malware", "hash": "abc123"}

        result = safe_request(
            session, URL, ALLOWED, IOC, PROVIDER,
            method="POST", json_payload=payload,
        )

        assert result == body
        session.post.assert_called_once()
        call_kwargs = session.post.call_args
        assert call_kwargs.kwargs.get("json") == payload or call_kwargs[1].get("json") == payload

    def test_post_data(self):
        body = {"submitted": True}
        resp = make_mock_response(200, body)
        session = _make_session_with(resp, method="post")
        form_data = {"key": "value"}

        result = safe_request(
            session, URL, ALLOWED, IOC, PROVIDER,
            method="POST", data=form_data,
        )

        assert result == body
        session.post.assert_called_once()
        call_kwargs = session.post.call_args
        assert call_kwargs.kwargs.get("data") == form_data or call_kwargs[1].get("data") == form_data

    def test_stream_true_and_no_redirects(self):
        """Verify stream=True and allow_redirects=False are always passed."""
        resp = make_mock_response(200, {"ok": True})
        session = _make_session_with(resp)

        safe_request(session, URL, ALLOWED, IOC, PROVIDER)

        _, kwargs = session.get.call_args
        assert kwargs["stream"] is True
        assert kwargs["allow_redirects"] is False
        assert kwargs["timeout"] == (5, 30)


class TestReadLimited:
    def test_read_limited_parses_chunked_json(self):
        resp = MagicMock()
        resp.iter_content.return_value = [
            b'{"status":',
            b'"ok","items":',
            b"[1,2,3]}",
        ]

        assert read_limited(resp) == {"status": "ok", "items": [1, 2, 3]}
        resp.iter_content.assert_called_once_with(chunk_size=8192)

    def test_read_limited_single_chunk_skips_bytearray_buffer(self, monkeypatch):
        """Single-chunk JSON responses should decode without allocating a bytearray buffer."""
        resp = MagicMock()
        resp.iter_content.return_value = [b'{"ok":true}']

        def fail_bytearray(*_args, **_kwargs):
            raise AssertionError("single-chunk responses should decode directly")

        monkeypatch.setattr(builtins, "bytearray", fail_bytearray)

        assert read_limited(resp) == {"ok": True}

    def test_read_limited_multi_chunk_uses_bytearray_buffer(self, monkeypatch):
        """Multi-chunk JSON responses still use one growable buffer after the second chunk."""
        resp = MagicMock()
        resp.iter_content.return_value = [b'{"ok":', b"true}"]
        original_bytearray = builtins.bytearray

        class CountingBytearray(original_bytearray):
            calls = 0

            def __new__(cls, *args, **kwargs):
                cls.calls += 1
                return super().__new__(cls, *args, **kwargs)

        monkeypatch.setattr(builtins, "bytearray", CountingBytearray)

        assert read_limited(resp) == {"ok": True}
        assert CountingBytearray.calls == 1

    def test_read_limited_uses_shared_chunk_size_constant(self, monkeypatch):
        resp = MagicMock()
        resp.iter_content.return_value = [b'{"ok":true}']
        monkeypatch.setattr(http_safety, "RESPONSE_CHUNK_SIZE", 4)

        assert read_limited(resp) == {"ok": True}
        resp.iter_content.assert_called_once_with(chunk_size=4)


# ── SSRF rejection ─────────────────────────────────────────────────────────


class TestSafeRequestSSRF:
    def test_ssrf_rejection(self):
        session = MagicMock()
        bad_url = "https://evil.internal/secrets"

        result = safe_request(session, bad_url, ALLOWED, IOC, PROVIDER)

        assert isinstance(result, EnrichmentError)
        assert "not in allowed_hosts" in result.error or "SSRF" in result.error
        # Must NOT make any network call
        session.get.assert_not_called()

    def test_empty_allowed_hosts_skips_urlparse(self, monkeypatch):
        """Empty allowlists should fail closed before URL parsing."""
        def fail_urlparse(_url):
            raise AssertionError("empty allowlist validation should not parse URLs")

        monkeypatch.setattr(http_safety, "urlparse", fail_urlparse)

        result = safe_request(MagicMock(), URL, [], IOC, PROVIDER)

        assert isinstance(result, EnrichmentError)
        assert "allowed_hosts is empty" in result.error

        with pytest.raises(ValueError, match="allowed_hosts is empty"):
            validate_endpoint(URL, [])


# ── Exception chain ────────────────────────────────────────────────────────


class TestSafeRequestExceptions:
    def test_timeout(self):
        session = MagicMock()
        session.get.side_effect = requests.exceptions.Timeout()

        result = safe_request(session, URL, ALLOWED, IOC, PROVIDER)

        assert isinstance(result, EnrichmentError)
        assert "timed out" in result.error

    def test_http_error(self):
        resp = make_mock_response(500, None)
        session = _make_session_with(resp)

        result = safe_request(session, URL, ALLOWED, IOC, PROVIDER)

        assert isinstance(result, EnrichmentError)
        assert "HTTP 500" in result.error

    def test_http_403(self):
        resp = make_mock_response(403, None)
        session = _make_session_with(resp)

        result = safe_request(session, URL, ALLOWED, IOC, PROVIDER)

        assert isinstance(result, EnrichmentError)
        assert "HTTP 403" in result.error

    def test_ssl_error(self):
        session = MagicMock()
        session.get.side_effect = requests.exceptions.SSLError()

        result = safe_request(session, URL, ALLOWED, IOC, PROVIDER)

        assert isinstance(result, EnrichmentError)
        assert "SSL/TLS" in result.error

    def test_connection_error(self):
        session = MagicMock()
        session.get.side_effect = requests.exceptions.ConnectionError()

        result = safe_request(session, URL, ALLOWED, IOC, PROVIDER)

        assert isinstance(result, EnrichmentError)
        assert "Connection failed" in result.error

    def test_ssl_error_before_connection_error(self):
        """SSLError is a subclass of ConnectionError — verify correct ordering."""
        session = MagicMock()
        # Raise SSLError (which IS-A ConnectionError)
        session.get.side_effect = requests.exceptions.SSLError("cert verify failed")

        result = safe_request(session, URL, ALLOWED, IOC, PROVIDER)

        # Must be caught as SSL, not Connection
        assert isinstance(result, EnrichmentError)
        assert "SSL/TLS" in result.error
        assert "Connection" not in result.error

    def test_generic_exception(self):
        session = MagicMock()
        session.get.side_effect = RuntimeError("something broke")

        result = safe_request(session, URL, ALLOWED, IOC, PROVIDER)

        assert isinstance(result, EnrichmentError)
        assert "something broke" in result.error


# ── pre_raise_hook ─────────────────────────────────────────────────────────


class TestSafeRequestPreRaiseHook:
    def test_hook_returns_result_short_circuits(self):
        """When hook returns a non-None value, skip raise_for_status and return it."""
        resp = make_mock_response(404, None)
        # Override raise_for_status to not raise — hook should fire first
        resp.raise_for_status = MagicMock()
        session = _make_session_with(resp)

        no_data_result = EnrichmentResult(
            ioc=IOC, provider=PROVIDER, verdict="no_data",
            detection_count=0, total_engines=0, scan_date=None, raw_stats={},
        )
        hook = MagicMock(return_value=no_data_result)

        result = safe_request(
            session, URL, ALLOWED, IOC, PROVIDER,
            pre_raise_hook=hook,
        )

        assert result is no_data_result
        hook.assert_called_once_with(resp)
        # raise_for_status should NOT have been called
        resp.raise_for_status.assert_not_called()

    def test_hook_returns_none_continues(self):
        """When hook returns None, proceed to raise_for_status and read body."""
        body = {"data": "value"}
        resp = make_mock_response(200, body)
        session = _make_session_with(resp)

        hook = MagicMock(return_value=None)

        result = safe_request(
            session, URL, ALLOWED, IOC, PROVIDER,
            pre_raise_hook=hook,
        )

        assert result == body
        hook.assert_called_once_with(resp)
        resp.raise_for_status.assert_called_once()
