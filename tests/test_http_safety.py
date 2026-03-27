"""Tests for safe_request() — canonical HTTP path for all enrichment adapters.

Covers: success paths (GET/POST), SSRF rejection, every exception type in the
chain, pre_raise_hook short-circuit and pass-through, and stream/redirect flags.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
import requests

from app.enrichment.http_safety import safe_request, validate_endpoint, read_limited
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
