"""Contract tests for BaseHTTPAdapter.

Tests the abstract base class via minimal stub subclasses that define only
the required abstract methods and class attributes. Verifies:

  1. Provider protocol conformance (isinstance check)
  2. is_configured() logic for zero-auth and key-required adapters
  3. lookup() rejects unsupported IOC types
  4. lookup() dispatches to safe_request with correct URL and returns parsed result
  5. _auth_headers() default returns empty dict; override sets session headers
  6. POST adapter variant: _http_method="POST" + _build_request_body() passes to safe_request
  7. _make_pre_raise_hook() integration (short-circuit on 404)
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.provider import Provider
from app.pipeline.models import IOC, IOCType

from tests.helpers import make_ipv4_ioc, make_domain_ioc, make_mock_response, mock_adapter_session


# ---------------------------------------------------------------------------
# Stub subclasses
# ---------------------------------------------------------------------------

class StubAdapter(BaseHTTPAdapter):
    """Minimal zero-auth GET adapter stub."""
    name = "StubProvider"
    supported_types = frozenset({IOCType.IPV4})
    requires_api_key = False

    def _build_url(self, ioc: IOC) -> str:
        return f"https://api.stub.test/{ioc.value}"

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return EnrichmentResult(
            ioc=ioc,
            provider=self.name,
            verdict=body.get("verdict", "clean"),
            detection_count=0,
            total_engines=1,
            scan_date=None,
            raw_stats=body,
        )


class StubKeyAdapter(BaseHTTPAdapter):
    """Key-required adapter stub with custom auth headers."""
    name = "KeyProvider"
    supported_types = frozenset({IOCType.IPV4, IOCType.DOMAIN})
    requires_api_key = True

    def _build_url(self, ioc: IOC) -> str:
        return f"https://api.key.test/lookup/{ioc.value}"

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return EnrichmentResult(
            ioc=ioc,
            provider=self.name,
            verdict="clean",
            detection_count=0,
            total_engines=1,
            scan_date=None,
            raw_stats=body,
        )

    def _auth_headers(self) -> dict:
        return {"X-Api-Key": self._api_key}


class StubPostAdapter(BaseHTTPAdapter):
    """POST adapter stub with request body."""
    name = "PostProvider"
    supported_types = frozenset({IOCType.SHA256})
    requires_api_key = True
    _http_method = "POST"

    def _build_url(self, ioc: IOC) -> str:
        return "https://api.post.test/query"

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return EnrichmentResult(
            ioc=ioc,
            provider=self.name,
            verdict="malicious",
            detection_count=1,
            total_engines=1,
            scan_date=None,
            raw_stats=body,
        )

    def _build_request_body(self, ioc: IOC) -> tuple[dict | None, dict | None]:
        return (None, {"hash": ioc.value})

    def _auth_headers(self) -> dict:
        return {"Auth-Key": self._api_key}


class StubHookAdapter(BaseHTTPAdapter):
    """Adapter stub with a pre-raise hook (404 → no_data)."""
    name = "HookProvider"
    supported_types = frozenset({IOCType.IPV4})
    requires_api_key = False

    def _build_url(self, ioc: IOC) -> str:
        return f"https://api.hook.test/{ioc.value}"

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return EnrichmentResult(
            ioc=ioc,
            provider=self.name,
            verdict="clean",
            detection_count=0,
            total_engines=1,
            scan_date=None,
            raw_stats=body,
        )

    def _make_pre_raise_hook(self, ioc: IOC):
        def _hook(resp):
            if resp.status_code == 404:
                return EnrichmentResult(
                    ioc=ioc,
                    provider=self.name,
                    verdict="no_data",
                    detection_count=0,
                    total_engines=0,
                    scan_date=None,
                    raw_stats={},
                )
            return None
        return _hook


# ---------------------------------------------------------------------------
# 1. Provider protocol conformance
# ---------------------------------------------------------------------------

class TestProtocolConformance:

    def test_stub_satisfies_provider_protocol(self):
        adapter = StubAdapter(allowed_hosts=["api.stub.test"])
        assert isinstance(adapter, Provider)

    def test_key_adapter_satisfies_provider_protocol(self):
        adapter = StubKeyAdapter(allowed_hosts=["api.key.test"], api_key="k")
        assert isinstance(adapter, Provider)

    def test_post_adapter_satisfies_provider_protocol(self):
        adapter = StubPostAdapter(allowed_hosts=["api.post.test"], api_key="k")
        assert isinstance(adapter, Provider)


# ---------------------------------------------------------------------------
# 2. is_configured() logic
# ---------------------------------------------------------------------------

class TestIsConfigured:

    def test_zero_auth_always_configured(self):
        adapter = StubAdapter(allowed_hosts=[])
        assert adapter.is_configured() is True

    def test_key_adapter_configured_with_key(self):
        adapter = StubKeyAdapter(allowed_hosts=[], api_key="secret")
        assert adapter.is_configured() is True

    def test_key_adapter_not_configured_without_key(self):
        adapter = StubKeyAdapter(allowed_hosts=[])
        assert adapter.is_configured() is False

    def test_key_adapter_not_configured_with_empty_key(self):
        adapter = StubKeyAdapter(allowed_hosts=[], api_key="")
        assert adapter.is_configured() is False


# ---------------------------------------------------------------------------
# 3. lookup() rejects unsupported IOC types
# ---------------------------------------------------------------------------

class TestTypeGuard:

    def test_rejects_unsupported_type(self):
        adapter = StubAdapter(allowed_hosts=[])
        domain_ioc = make_domain_ioc()
        result = adapter.lookup(domain_ioc)
        assert isinstance(result, EnrichmentError)
        assert result.error == "Unsupported type"
        assert result.provider == "StubProvider"

    def test_accepts_supported_type(self):
        adapter = StubAdapter(allowed_hosts=["api.stub.test"])
        mock_adapter_session(adapter, response=make_mock_response(200, {"verdict": "clean"}))
        ioc = make_ipv4_ioc()
        result = adapter.lookup(ioc)
        assert isinstance(result, EnrichmentResult)


# ---------------------------------------------------------------------------
# 4. lookup() dispatches to safe_request and returns parsed result
# ---------------------------------------------------------------------------

class TestLookupDispatch:

    @patch("app.enrichment.adapters.base.safe_request")
    def test_get_dispatch_url_and_result(self, mock_sr):
        body = {"verdict": "clean", "extra": 42}
        mock_sr.return_value = body

        adapter = StubAdapter(allowed_hosts=["api.stub.test"])
        ioc = make_ipv4_ioc("8.8.8.8")
        result = adapter.lookup(ioc)

        mock_sr.assert_called_once()
        call_kwargs = mock_sr.call_args
        # Positional: session, url, allowed_hosts, ioc, provider
        assert call_kwargs[0][1] == "https://api.stub.test/8.8.8.8"
        assert call_kwargs[0][3] is ioc
        assert call_kwargs[0][4] == "StubProvider"
        # Keyword args
        assert call_kwargs[1]["method"] == "GET"
        assert call_kwargs[1]["data"] is None
        assert call_kwargs[1]["json_payload"] is None

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "clean"
        assert result.raw_stats == body

    @patch("app.enrichment.adapters.base.safe_request")
    def test_propagates_enrichment_error(self, mock_sr):
        ioc = make_ipv4_ioc()
        error = EnrichmentError(ioc=ioc, provider="StubProvider", error="HTTP 429")
        mock_sr.return_value = error

        adapter = StubAdapter(allowed_hosts=["api.stub.test"])
        result = adapter.lookup(ioc)

        assert result is error


# ---------------------------------------------------------------------------
# 5. _auth_headers() default and override
# ---------------------------------------------------------------------------

class TestAuthHeaders:

    def test_default_auth_headers_empty(self):
        adapter = StubAdapter(allowed_hosts=[])
        assert adapter._auth_headers() == {}

    def test_session_has_no_extra_headers_for_default(self):
        adapter = StubAdapter(allowed_hosts=[])
        # Default session won't have custom keys
        assert "X-Api-Key" not in dict(adapter._session.headers)

    def test_override_sets_session_headers(self):
        adapter = StubKeyAdapter(allowed_hosts=[], api_key="my-secret")
        assert dict(adapter._session.headers).get("X-Api-Key") == "my-secret"


# ---------------------------------------------------------------------------
# 6. POST adapter variant
# ---------------------------------------------------------------------------

class TestPostAdapter:

    @patch("app.enrichment.adapters.base.safe_request")
    def test_post_dispatch_with_json_body(self, mock_sr):
        body = {"status": "found"}
        mock_sr.return_value = body

        adapter = StubPostAdapter(allowed_hosts=["api.post.test"], api_key="k")
        ioc = IOC(type=IOCType.SHA256, value="abc123", raw_match="abc123")
        result = adapter.lookup(ioc)

        mock_sr.assert_called_once()
        call_kwargs = mock_sr.call_args
        assert call_kwargs[1]["method"] == "POST"
        assert call_kwargs[1]["json_payload"] == {"hash": "abc123"}
        assert call_kwargs[1]["data"] is None

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"

    @patch("app.enrichment.adapters.base.safe_request")
    def test_post_adapter_auth_header(self, mock_sr):
        mock_sr.return_value = {}
        adapter = StubPostAdapter(allowed_hosts=["api.post.test"], api_key="secret-key")
        assert dict(adapter._session.headers).get("Auth-Key") == "secret-key"


# ---------------------------------------------------------------------------
# 7. Pre-raise hook integration
# ---------------------------------------------------------------------------

class TestPreRaiseHook:

    def test_default_hook_is_none(self):
        adapter = StubAdapter(allowed_hosts=[])
        ioc = make_ipv4_ioc()
        assert adapter._make_pre_raise_hook(ioc) is None

    @patch("app.enrichment.adapters.base.safe_request")
    def test_hook_passed_to_safe_request(self, mock_sr):
        mock_sr.return_value = {"data": 1}

        adapter = StubHookAdapter(allowed_hosts=["api.hook.test"])
        ioc = make_ipv4_ioc()
        adapter.lookup(ioc)

        call_kwargs = mock_sr.call_args
        hook = call_kwargs[1]["pre_raise_hook"]
        assert hook is not None
        assert callable(hook)

    @patch("app.enrichment.adapters.base.safe_request")
    def test_hook_short_circuits_on_404(self, mock_sr):
        """When safe_request invokes the hook and hook returns a result,
        that result is returned directly (not passed to _parse_response)."""
        no_data_result = EnrichmentResult(
            ioc=make_ipv4_ioc(),
            provider="HookProvider",
            verdict="no_data",
            detection_count=0,
            total_engines=0,
            scan_date=None,
            raw_stats={},
        )
        mock_sr.return_value = no_data_result

        adapter = StubHookAdapter(allowed_hosts=["api.hook.test"])
        result = adapter.lookup(make_ipv4_ioc())

        # safe_request returned an EnrichmentResult (not dict), so lookup
        # should propagate it without calling _parse_response
        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"


# ---------------------------------------------------------------------------
# 8. _build_request_body default
# ---------------------------------------------------------------------------

class TestBuildRequestBody:

    def test_default_returns_none_none(self):
        adapter = StubAdapter(allowed_hosts=[])
        ioc = make_ipv4_ioc()
        data, json_payload = adapter._build_request_body(ioc)
        assert data is None
        assert json_payload is None


# ---------------------------------------------------------------------------
# 9. BaseHTTPAdapter is abstract — cannot be instantiated directly
# ---------------------------------------------------------------------------

class TestAbstractEnforcement:

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BaseHTTPAdapter(allowed_hosts=[])
