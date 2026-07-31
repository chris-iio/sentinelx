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

import inspect
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest

from app.enrichment.adapters.base import (
    BaseHTTPAdapter,
    _EMPTY_ALLOWED_HOSTS,
    _EMPTY_AUTH_HEADERS,
    append_auth_header_snapshot,
    _auth_headers_snapshot,
    _allowed_hosts_membership,
    _no_data_on_404_hook,
    _rate_limit_on_429,
)
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


class StubPolicyHookAdapter(StubAdapter):
    """Adapter stub that uses BaseHTTPAdapter generic status hook flags."""

    _no_data_on_404 = True
    _rate_limit_on_429 = True


class StubListBodyAdapter(BaseHTTPAdapter):
    """Adapter stub that parses successful JSON list bodies."""
    name = "ListBodyProvider"
    supported_types = frozenset({IOCType.DOMAIN})
    requires_api_key = False

    def _build_url(self, ioc: IOC) -> str:
        return f"https://api.list.test/{ioc.value}"

    def _parse_response(self, ioc: IOC, body) -> EnrichmentResult:
        return EnrichmentResult(
            ioc=ioc,
            provider=self.name,
            verdict="no_data",
            detection_count=0,
            total_engines=0,
            scan_date=None,
            raw_stats={"row_count": len(body)},
        )


class StubMappingHeaderAdapter(BaseHTTPAdapter):
    """Key-required adapter stub with a custom mapping header source."""
    name = "MappingHeaderProvider"
    supported_types = frozenset({IOCType.IPV4})
    requires_api_key = True

    def __init__(self, allowed_hosts, *, header_source, api_key: str = "k") -> None:
        self.header_source = header_source
        super().__init__(allowed_hosts, api_key=api_key)

    def _build_url(self, ioc: IOC) -> str:
        return f"https://api.header.test/{ioc.value}"

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

    def _auth_headers(self):
        return self.header_source


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

    @patch("app.enrichment.adapters.base.safe_request")
    def test_successful_json_list_body_is_parsed(self, mock_sr):
        """Successful JSON arrays should flow to _parse_response."""
        mock_sr.return_value = [{"id": 1}, {"id": 2}]

        adapter = StubListBodyAdapter(allowed_hosts=["api.list.test"])
        result = adapter.lookup(make_domain_ioc("example.com"))

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats == {"row_count": 2}

    @patch("app.enrichment.adapters.base.safe_request")
    def test_allowed_hosts_are_cached_as_membership_set(self, mock_sr):
        mock_sr.return_value = {"verdict": "clean"}
        allowed_hosts = ["api.stub.test", "unused.example"]
        adapter = StubAdapter(allowed_hosts=allowed_hosts)
        allowed_hosts.append("late-added.example")
        ioc = make_ipv4_ioc("8.8.4.4")

        result = adapter.lookup(ioc)

        call_args = mock_sr.call_args
        passed_allowed_hosts = call_args[0][2]
        assert isinstance(result, EnrichmentResult)
        assert passed_allowed_hosts == frozenset({"api.stub.test", "unused.example"})
        assert "late-added.example" not in passed_allowed_hosts

    def test_allowed_hosts_membership_reuses_existing_frozenset(self):
        allowed_hosts = frozenset(("api.stub.test", "unused.example"))
        adapter = StubAdapter(allowed_hosts=allowed_hosts)

        assert _allowed_hosts_membership(allowed_hosts) is allowed_hosts
        assert adapter._allowed_hosts is allowed_hosts

    @patch("app.enrichment.adapters.base.safe_request")
    def test_concurrent_lookup_uses_thread_local_sessions(self, mock_sr):
        barrier = threading.Barrier(2)
        session_ids: list[int] = []
        header_values: list[str | None] = []

        def capture_session(session, *_args, **_kwargs):
            session_ids.append(id(session))
            header_values.append(dict(session.headers).get("X-Api-Key"))
            barrier.wait(timeout=2)
            return {"verdict": "clean"}

        mock_sr.side_effect = capture_session
        adapter = StubKeyAdapter(allowed_hosts=["api.key.test"], api_key="thread-secret")

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(adapter.lookup, make_ipv4_ioc("8.8.8.8"))
            second = pool.submit(adapter.lookup, make_ipv4_ioc("1.1.1.1"))

        assert isinstance(first.result(), EnrichmentResult)
        assert isinstance(second.result(), EnrichmentResult)
        assert len(set(session_ids)) == 2
        assert header_values == ["thread-secret", "thread-secret"]

    def test_empty_allowed_hosts_reuse_shared_empty_snapshot(self, monkeypatch):
        class NoIterEmptyList(list):
            def __iter__(self):
                raise AssertionError("empty allowed_hosts should not be materialized")

        allowed_hosts = NoIterEmptyList()

        adapter = StubAdapter(allowed_hosts=allowed_hosts)

        assert _allowed_hosts_membership(allowed_hosts) is _EMPTY_ALLOWED_HOSTS
        assert adapter._allowed_hosts is _EMPTY_ALLOWED_HOSTS

    def test_single_pair_three_or_four_allowed_hosts_skip_general_iteration(self):
        class NoIterHosts(list):
            def __iter__(self):
                raise AssertionError("short allowed_hosts should use indexed fast paths")

            def __getitem__(self, index):
                if isinstance(index, slice):
                    raise AssertionError("allowed_hosts membership should not slice")
                return super().__getitem__(index)

        single = NoIterHosts(["api.stub.test"])
        pair = NoIterHosts(["api.stub.test", "unused.example"])
        three = NoIterHosts(["api.stub.test", "unused.example", "third.example"])
        four = NoIterHosts([
            "api.stub.test",
            "unused.example",
            "third.example",
            "fourth.example",
        ])

        single_membership = _allowed_hosts_membership(single)
        pair_membership = _allowed_hosts_membership(pair)
        three_membership = _allowed_hosts_membership(three)
        four_membership = _allowed_hosts_membership(four)
        adapter = StubAdapter(allowed_hosts=pair)
        pair.append("late-added.example")

        assert single_membership == frozenset(("api.stub.test",))
        assert pair_membership == frozenset(("api.stub.test", "unused.example"))
        assert three_membership == frozenset(("api.stub.test", "unused.example", "third.example"))
        assert four_membership == frozenset((
            "api.stub.test",
            "unused.example",
            "third.example",
            "fourth.example",
        ))
        assert adapter._allowed_hosts == frozenset(("api.stub.test", "unused.example"))
        assert "late-added.example" not in adapter._allowed_hosts

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
        assert adapter._auth_headers() is _EMPTY_AUTH_HEADERS

    def test_default_auth_headers_skip_empty_session_update(self, monkeypatch):
        class Headers(dict):
            def update(self, values=(), **kwargs):
                if not values and not kwargs:
                    raise AssertionError("empty auth headers should not update the session")
                return super().update(values, **kwargs)

        class Session:
            def __init__(self):
                self.headers = Headers()

        monkeypatch.setattr("app.enrichment.adapters.base.requests.Session", Session)

        adapter = StubAdapter(allowed_hosts=[])

        assert adapter._session.headers == {}

    def test_session_has_no_extra_headers_for_default(self):
        adapter = StubAdapter(allowed_hosts=[])
        # Default session won't have custom keys
        assert "X-Api-Key" not in dict(adapter._session.headers)

    def test_override_sets_session_headers(self):
        adapter = StubKeyAdapter(allowed_hosts=[], api_key="my-secret")
        assert dict(adapter._session.headers).get("X-Api-Key") == "my-secret"

    def test_auth_headers_snapshot_accumulates_without_constructor_copy(self):
        class HeaderSource(dict):
            def items(self):
                raise AssertionError("auth header snapshot should avoid items-view allocation")

            def copy(self):
                raise AssertionError("auth header snapshot should avoid mapping copy")

        headers = HeaderSource({"X-Api-Key": "initial-secret"})
        snapshot = _auth_headers_snapshot(headers)
        headers["X-Api-Key"] = "mutated-secret"

        assert snapshot["X-Api-Key"] == "initial-secret"
        assert _auth_headers_snapshot({}) is _EMPTY_AUTH_HEADERS
        source_names = _auth_headers_snapshot.__code__.co_names
        assert "dict" not in source_names
        assert "items" not in source_names
        assert "copy" not in source_names

    def test_auth_headers_snapshot_delegates_fallback_mutation(self):
        headers = {
            "X-Api-Key": "key",
            "Auth-Key": "auth",
            "X-Trace": "trace",
            "X-Tenant": "tenant",
            "X-Extra": "extra",
        }
        copied_headers: dict[str, str] = {}

        append_auth_header_snapshot(copied_headers, headers, "X-Extra")
        snapshot = _auth_headers_snapshot(headers)

        assert copied_headers == {"X-Extra": "extra"}
        assert snapshot["X-Extra"] == "extra"
        source = inspect.getsource(_auth_headers_snapshot)
        helper_source = inspect.getsource(append_auth_header_snapshot)
        assert "append_auth_header_snapshot(copied_headers, headers, key)" in source
        assert "copied_headers[key] = headers[key]" not in source
        assert "copied_headers[key] = headers[key]" in helper_source

    def test_auth_headers_snapshot_short_paths_skip_fallback_loop(self):
        class ShortHeaderSource(dict):
            iterations = 0

            def __iter__(self):
                for key in super().__iter__():
                    type(self).iterations += 1
                    if type(self).iterations > len(self):
                        raise AssertionError("short auth header snapshot should stop at length")
                    yield key

            def items(self):
                raise AssertionError("auth header snapshot should avoid items-view allocation")

        source = ShortHeaderSource({
            "X-Api-Key": "key",
            "Auth-Key": "auth",
            "X-Trace": "trace",
            "X-Tenant": "tenant",
        })
        snapshot = _auth_headers_snapshot(source)
        source["X-Api-Key"] = "mutated"

        assert snapshot == {
            "X-Api-Key": "key",
            "Auth-Key": "auth",
            "X-Trace": "trace",
            "X-Tenant": "tenant",
        }
        assert ShortHeaderSource.iterations == 4
        assert "header_count == 4" in inspect.getsource(_auth_headers_snapshot)

    def test_adapter_auth_header_cache_uses_immutable_snapshot(self):
        headers = {"X-Api-Key": "initial-secret"}
        adapter = StubMappingHeaderAdapter(allowed_hosts=[], header_source=headers)
        headers["X-Api-Key"] = "mutated-secret"

        assert adapter._auth_header_cache["X-Api-Key"] == "initial-secret"
        assert dict(adapter._session.headers).get("X-Api-Key") == "initial-secret"
        with pytest.raises(TypeError):
            adapter._auth_header_cache["X-Api-Key"] = "changed"  # type: ignore[index]


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

    def test_shared_404_hook_returns_no_data_result(self):
        ioc = make_ipv4_ioc("192.0.2.1")
        hook = _no_data_on_404_hook(ioc, "ExampleProvider")

        result = hook(make_mock_response(404))

        assert isinstance(result, EnrichmentResult)
        assert result.ioc is ioc
        assert result.provider == "ExampleProvider"
        assert result.verdict == "no_data"
        assert result.raw_stats == {}

    def test_shared_404_hook_ignores_other_statuses(self):
        hook = _no_data_on_404_hook(make_ipv4_ioc("192.0.2.1"), "ExampleProvider")

        assert hook(make_mock_response(500)) is None

    def test_shared_429_helper_returns_rate_limit_error(self):
        ioc = make_ipv4_ioc("192.0.2.1")

        result = _rate_limit_on_429(make_mock_response(429), ioc, "ExampleProvider")

        assert isinstance(result, EnrichmentError)
        assert result.ioc is ioc
        assert result.provider == "ExampleProvider"
        assert result.error == "Rate limit exceeded (429)"

    def test_shared_429_helper_ignores_other_statuses(self):
        result = _rate_limit_on_429(
            make_mock_response(500),
            make_ipv4_ioc("192.0.2.1"),
            "ExampleProvider",
        )

        assert result is None

    def test_generic_status_policy_flags_build_shared_hook(self):
        ioc = make_ipv4_ioc("192.0.2.1")
        adapter = StubPolicyHookAdapter(allowed_hosts=["api.test"])

        hook = adapter._make_pre_raise_hook(ioc)

        assert hook is not None
        no_data = hook(make_mock_response(404))
        rate_limit = hook(make_mock_response(429))
        pass_through = hook(make_mock_response(500))
        assert isinstance(no_data, EnrichmentResult)
        assert no_data.provider == "StubProvider"
        assert no_data.verdict == "no_data"
        assert isinstance(rate_limit, EnrichmentError)
        assert rate_limit.provider == "StubProvider"
        assert rate_limit.error == "Rate limit exceeded (429)"
        assert pass_through is None


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
