"""Tests for the REST API blueprint (/api/analyze, /api/status/<job_id>)."""

import inspect
import re
from pathlib import Path
from types import MappingProxyType
from unittest.mock import MagicMock, patch

import pytest

from app import create_app
from app.enrichment.models import EnrichmentResult
from app.health_contract import (
    _EMPTY_HEALTH_CHECK,
    HEALTH_CHECKS,
    HEALTH_CHECK_ORDER,
    HEALTH_PAYLOAD,
    HEALTH_PATH,
    HEALTH_STATUSES,
    build_health_payload,
    is_valid_health_payload,
)
from app.pipeline.models import IOCType

from tests.helpers import make_ipv4_ioc


@pytest.fixture()
def client():
    """Test client with CSRF disabled (as in other test files)."""
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    # Provide required app attributes
    app.history_store = MagicMock()  # type: ignore[attr-defined]
    app.cache_store = MagicMock()  # type: ignore[attr-defined]
    app.registry = MagicMock()  # type: ignore[attr-defined]
    app.registry.configured.return_value = []  # type: ignore[attr-defined]
    app.registry.all.return_value = []  # type: ignore[attr-defined]
    with app.test_client() as c:
        yield c


@pytest.fixture()
def client_with_csrf():
    """Test client with CSRF enabled — verifies API is exempt."""
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": True})
    app.history_store = MagicMock()  # type: ignore[attr-defined]
    app.cache_store = MagicMock()  # type: ignore[attr-defined]
    app.registry = MagicMock()  # type: ignore[attr-defined]
    app.registry.configured.return_value = []  # type: ignore[attr-defined]
    with app.test_client() as c:
        yield c


def _build_incremental_snapshot_orchestrator(
    results,
    *,
    total=None,
    done=None,
    complete=True,
    status=None,
    terminal=False,
    terminal_reason=None,
    error=None,
    cached_markers=None,
):
    """Return a mock orchestrator exposing only the incremental polling API."""
    full_results = list(results)
    marker_map = dict(cached_markers or {})
    mock_orch = MagicMock(spec_set=["get_incremental_status", "get_status"])

    def _get_incremental_status(_job_id, since=0):
        tail_results = list(full_results[since:])
        tail_markers = {}
        for result in tail_results:
            ioc = getattr(result, "ioc", None)
            provider = getattr(result, "provider", None)
            ioc_value = getattr(ioc, "value", None)
            if not ioc_value or not provider:
                continue
            cache_key = f"{ioc_value}|{provider}"
            cached_at = marker_map.get(cache_key)
            if cached_at:
                tail_markers[cache_key] = cached_at
        return {
            "total": len(full_results) if total is None else total,
            "done": len(full_results) if done is None else done,
            "complete": complete,
            "results": tail_results,
            "next_since": since if terminal else len(full_results),
            "status": status or ("failed" if terminal else "complete" if complete else "running"),
            "terminal": terminal,
            "terminal_reason": terminal_reason,
            "error": error,
            "cached_markers": tail_markers,
        }

    mock_orch.get_incremental_status.side_effect = _get_incremental_status
    mock_orch.get_status.side_effect = AssertionError(
        "_get_enrichment_status should use get_incremental_status() for polling"
    )
    return mock_orch


# ---------- GET /api/health ----------


class TestApiHealth:
    """Local liveness/readiness contract for the dev-server manager."""

    def test_health_contract_constants_stay_secret_free(self):
        assert HEALTH_PATH == "/api/health"
        assert "provider_key" not in HEALTH_CHECKS
        assert HEALTH_CHECK_ORDER == ("cache", "history", "registry")
        assert HEALTH_STATUSES == frozenset(("ok", "degraded"))
        assert isinstance(HEALTH_PAYLOAD, MappingProxyType)
        assert HEALTH_PAYLOAD == {"service": "sentinelx", "status": "ok", "ready": True}
        assert is_valid_health_payload(dict(HEALTH_PAYLOAD))
        source = Path("app/health_contract.py").read_text(encoding="utf-8")
        assert "HEALTH_CHECK_ORDER = tuple(sorted(" not in source
        assert 'HEALTH_CHECK_ORDER = ("cache", "history", "registry")' in source
        assert 'HEALTH_STATUSES = frozenset(("ok", "degraded"))' in source
        assert "HEALTH_PAYLOAD = {" not in source
        assert '{"ok", "degraded"}' not in source
        assert re.search(r"frozenset\s*\(\s*\{", source) is None

    def test_health_returns_secret_free_schema(self, client):
        resp = client.get(HEALTH_PATH)

        assert resp.status_code == 200
        assert resp.is_json is True
        payload = resp.get_json()
        assert is_valid_health_payload(payload)
        assert payload["service"] == "sentinelx"
        assert payload["ready"] is True
        assert set(payload["checks"]) == set(HEALTH_CHECKS)
        assert "provider_key" not in str(payload)

    def test_health_payload_uses_precomputed_check_order(self, monkeypatch):
        def fail_sorted(_value):
            raise AssertionError("build_health_payload should not sort checks per call")

        monkeypatch.setattr("builtins.sorted", fail_sorted)

        payload = build_health_payload({
            "cache": {"status": "ok", "detail": "available"},
            "history": {"status": "ok", "detail": "available"},
            "registry": {"status": "ok", "detail": "available"},
        })

        assert list(payload["checks"]) == ["cache", "history", "registry"]
        assert is_valid_health_payload(payload)

    def test_health_payload_detail_presence_skips_strip_allocation(self):
        class NoStripDetail(str):
            def strip(self, *_args, **_kwargs):
                raise AssertionError("health detail presence should scan directly")

        payload = build_health_payload({
            "cache": {"status": "ok", "detail": NoStripDetail("available")},
            "history": {"status": "ok", "detail": NoStripDetail("history ok")},
            "registry": {"status": "degraded", "detail": NoStripDetail("   ")},
        })

        assert payload["checks"]["cache"]["detail"] == "available"
        assert payload["checks"]["history"]["detail"] == "history ok"
        assert payload["checks"]["registry"]["detail"] == "unavailable"
        assert payload["status"] == "degraded"
        assert is_valid_health_payload(payload)

    def test_health_payload_validation_uses_precomputed_key_sets(self, monkeypatch):
        def fail_set(_value):
            raise AssertionError("is_valid_health_payload should not allocate sets per validation")

        class NoKeyViewDict(dict):
            def keys(self):
                raise AssertionError("is_valid_health_payload should validate keys by direct membership")

            def values(self):
                raise AssertionError("is_valid_health_payload should validate checks by known keys")

        payload = build_health_payload({
            "cache": {"status": "ok", "detail": "available"},
            "history": {"status": "ok", "detail": "available"},
            "registry": {"status": "ok", "detail": "available"},
        })
        payload["checks"] = NoKeyViewDict({
            name: NoKeyViewDict(value)
            for name, value in payload["checks"].items()
        })
        payload = NoKeyViewDict(payload)
        monkeypatch.setattr("builtins.set", fail_set)

        assert is_valid_health_payload(payload)
        assert "_has_only_keys" in is_valid_health_payload.__code__.co_names
        assert "_has_exact_keys" in is_valid_health_payload.__code__.co_names

    def test_health_payload_uses_precomputed_status_set(self, monkeypatch):
        class NoContainsSet(set):
            def __contains__(self, _value):
                raise AssertionError("health status validation should not build set literals")

        monkeypatch.setattr("builtins.set", NoContainsSet)

        payload = build_health_payload({
            "cache": {"status": "ok", "detail": "available"},
            "history": {"status": "invalid", "detail": "bad"},
            "registry": {"status": "degraded", "detail": "slow"},
        })

        assert payload["status"] == "degraded"
        assert payload["checks"]["history"]["status"] == "degraded"
        assert is_valid_health_payload(payload)

    def test_health_payload_reuses_empty_missing_check_default(self):
        class MissingChecks(dict):
            defaults: list[object] = []

            def get(self, key, default=None):
                self.defaults.append(default)
                return default

        checks = MissingChecks()

        payload = build_health_payload(checks)

        assert payload["status"] == "degraded"
        assert checks.defaults == [_EMPTY_HEALTH_CHECK, _EMPTY_HEALTH_CHECK, _EMPTY_HEALTH_CHECK]
        assert all(default is _EMPTY_HEALTH_CHECK for default in checks.defaults)
        assert is_valid_health_payload(payload)

    def test_health_reports_degraded_dependency_without_secret_text(self, client):
        client.application.cache_store.stats.side_effect = RuntimeError(
            "secret path /tmp/sentinelx-provider-key"
        )

        resp = client.get(HEALTH_PATH)

        assert resp.status_code == 200
        payload = resp.get_json()
        assert is_valid_health_payload(payload)
        assert payload["status"] == "degraded"
        assert payload["checks"]["cache"] == {
            "status": "degraded",
            "detail": "RuntimeError",
        }
        assert "sentinelx-provider-key" not in str(payload)

    def test_health_touches_only_aggregate_provider_configuration(self, client):
        client.application.registry.configured_count.return_value = 1
        client.application.registry.registered_count.return_value = 2
        client.application.registry.all.side_effect = AssertionError(
            "health should not allocate registered providers for count-only detail"
        )
        client.application.registry.configured.side_effect = AssertionError(
            "health should not allocate configured providers for count-only detail"
        )

        resp = client.get(HEALTH_PATH)

        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["checks"]["registry"]["detail"] == "1/2 providers configured"
        client.application.registry.configured_count.assert_called_once()
        client.application.registry.registered_count.assert_called_once()
        assert client.application.registry.configured.call_count == 0
        assert client.application.registry.all.call_count == 0


# ---------- POST /api/analyze — validation ----------


class TestApiAnalyzeValidation:
    """Input validation for POST /api/analyze."""

    def test_text_presence_helper_scans_without_strip_allocation(self):
        from app.text_utils import has_non_whitespace

        class NoStripText(str):
            def strip(self, *_args, **_kwargs):
                raise AssertionError("text presence should scan directly")

        assert has_non_whitespace(NoStripText("  8.8.8.8  ")) is True
        assert has_non_whitespace(NoStripText("  \n\t  ")) is False

    def test_no_json_body(self, client):
        resp = client.post("/api/analyze", data="not json", content_type="text/plain")
        assert resp.status_code == 400
        assert "must be JSON" in resp.get_json()["error"]

    def test_empty_text(self, client):
        resp = client.post("/api/analyze", json={"text": ""})
        assert resp.status_code == 400
        assert "'text' is required" in resp.get_json()["error"]

    def test_missing_text_field(self, client):
        resp = client.post("/api/analyze", json={"mode": "offline"})
        assert resp.status_code == 400
        assert "'text' is required" in resp.get_json()["error"]

    def test_whitespace_only_text(self, client):
        resp = client.post("/api/analyze", json={"text": "   \n\t  "})
        assert resp.status_code == 400

    def test_invalid_mode(self, client):
        from app.routes import api as api_routes

        resp = client.post("/api/analyze", json={"text": "8.8.8.8", "mode": "turbo"})
        assert resp.status_code == 400
        assert "Invalid mode" in resp.get_json()["error"]
        assert api_routes._VALID_MODES == frozenset(("offline", "online"))
        assert isinstance(api_routes._VALID_MODES, frozenset)
        assert '{"offline", "online"}' not in Path("app/routes/api.py").read_text(
            encoding="utf-8"
        )

    def test_text_not_string(self, client):
        resp = client.post("/api/analyze", json={"text": 12345})
        assert resp.status_code == 400

    def test_api_analyze_uses_shared_text_presence_check(self, client, monkeypatch):
        from app.routes import api as api_routes

        calls: list[str] = []

        def record_presence(value: str) -> bool:
            calls.append(value)
            return True

        monkeypatch.setattr(api_routes, "has_non_whitespace", record_presence)
        monkeypatch.setattr(api_routes, "run_pipeline", lambda _text: [])

        resp = client.post("/api/analyze", json={"text": "no indicators here"})

        assert resp.status_code == 200
        assert calls == ["no indicators here"]


# ---------- POST /api/analyze — offline success ----------


class TestApiAnalyzeOffline:
    """Offline mode (default) — extract IOCs, return JSON."""

    def test_extracts_ipv4(self, client):
        resp = client.post("/api/analyze", json={"text": "Check 8.8.8.8 and 1.1.1.1"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["mode"] == "offline"
        assert data["total_count"] >= 2
        values = [ioc["value"] for ioc in data["iocs"]]
        assert "8.8.8.8" in values
        assert "1.1.1.1" in values

    def test_default_mode_is_offline(self, client):
        resp = client.post("/api/analyze", json={"text": "8.8.8.8"})
        data = resp.get_json()
        assert data["mode"] == "offline"
        assert "job_id" not in data

    def test_returns_grouped(self, client):
        resp = client.post("/api/analyze", json={"text": "8.8.8.8 and example.com"})
        data = resp.get_json()
        assert "grouped" in data
        assert isinstance(data["grouped"], dict)

    def test_groups_serialized_iocs_in_one_pass(self, client, monkeypatch):
        from app.pipeline.models import IOC
        from app.routes import api as api_routes
        from app.routes import _helpers as route_helpers

        iocs = [
            IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8"),
            IOC(type=IOCType.IPV4, value="1.1.1.1", raw_match="1.1.1.1"),
        ]
        serialize_calls: list[str] = []

        monkeypatch.setattr(api_routes, "run_pipeline", lambda _text: iocs)

        def serialize_once(seen_ioc):
            serialize_calls.append(seen_ioc.value)
            return {
                "type": seen_ioc.type.value,
                "value": seen_ioc.value,
                "raw_match": seen_ioc.raw_match,
            }

        monkeypatch.setattr(route_helpers, "_serialize_ioc", serialize_once)

        resp = client.post("/api/analyze", json={"text": "8.8.8.8"})
        data = resp.get_json()

        assert resp.status_code == 200
        assert serialize_calls == ["8.8.8.8", "1.1.1.1"]
        assert data["iocs"] == data["grouped"]["ipv4"]
        assert "setdefault" not in api_routes.api_analyze.__code__.co_names
        assert "_serialized_ioc_response_payload" in inspect.getsource(api_routes.api_analyze)
        assert "setdefault" not in route_helpers._append_serialized_ioc_by_type.__code__.co_names

    def test_serialized_ioc_response_payload_uses_tiny_batch_paths(self, monkeypatch):
        from app.pipeline.models import IOC
        from app.routes import api as api_routes
        from app.routes import _helpers as route_helpers

        class NoIterIocs(list):
            def __iter__(self):
                raise AssertionError("tiny API response batches should not iterate")

            def __getitem__(self, index):
                if isinstance(index, slice):
                    raise AssertionError("tiny API response batches should not slice")
                return super().__getitem__(index)

        def serialize_once(ioc):
            return {
                "type": ioc.type.value,
                "value": ioc.value,
                "raw_match": ioc.raw_match,
            }

        monkeypatch.setattr(route_helpers, "_serialize_ioc", serialize_once)

        single_iocs = NoIterIocs([
            IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8"),
        ])
        single_rows, single_grouped = api_routes._serialized_ioc_response_payload(single_iocs)

        assert single_rows == [{"type": "ipv4", "value": "8.8.8.8", "raw_match": "8.8.8.8"}]
        assert single_grouped == {"ipv4": single_rows}

        pair_iocs = NoIterIocs([
            IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8"),
            IOC(type=IOCType.DOMAIN, value="example.com", raw_match="example.com"),
        ])
        pair_rows, pair_grouped = api_routes._serialized_ioc_response_payload(pair_iocs)

        assert pair_rows == [
            {"type": "ipv4", "value": "8.8.8.8", "raw_match": "8.8.8.8"},
            {"type": "domain", "value": "example.com", "raw_match": "example.com"},
        ]
        assert pair_grouped == {
            "ipv4": [pair_rows[0]],
            "domain": [pair_rows[1]],
        }

        same_type_rows, same_type_grouped = api_routes._serialized_ioc_response_payload(
            NoIterIocs([
                IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8"),
                IOC(type=IOCType.IPV4, value="1.1.1.1", raw_match="1.1.1.1"),
            ])
        )

        assert same_type_grouped == {"ipv4": same_type_rows}

        three_iocs = NoIterIocs([
            IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8"),
            IOC(type=IOCType.DOMAIN, value="example.com", raw_match="example.com"),
            IOC(type=IOCType.IPV4, value="1.1.1.1", raw_match="1.1.1.1"),
        ])
        three_rows, three_grouped = api_routes._serialized_ioc_response_payload(three_iocs)

        assert three_rows == [
            {"type": "ipv4", "value": "8.8.8.8", "raw_match": "8.8.8.8"},
            {"type": "domain", "value": "example.com", "raw_match": "example.com"},
            {"type": "ipv4", "value": "1.1.1.1", "raw_match": "1.1.1.1"},
        ]
        assert three_grouped == {
            "ipv4": [three_rows[0], three_rows[2]],
            "domain": [three_rows[1]],
        }

        same_type_three_rows, same_type_three_grouped = api_routes._serialized_ioc_response_payload(
            NoIterIocs([
                IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8"),
                IOC(type=IOCType.IPV4, value="1.1.1.1", raw_match="1.1.1.1"),
                IOC(type=IOCType.IPV4, value="9.9.9.9", raw_match="9.9.9.9"),
            ])
        )

        assert same_type_three_grouped == {"ipv4": same_type_three_rows}

    def test_serialized_ioc_group_append_preserves_existing_group_order(self):
        from app.routes.api import _append_serialized_ioc_by_type

        first = {"type": "ipv4", "value": "8.8.8.8"}
        second = {"type": "ipv4", "value": "1.1.1.1"}
        grouped: dict[str, list[dict]] = {}

        _append_serialized_ioc_by_type(grouped, "ipv4", first)
        _append_serialized_ioc_by_type(grouped, "ipv4", second)

        assert grouped == {"ipv4": [first, second]}

    def test_no_iocs_found(self, client):
        resp = client.post("/api/analyze", json={"text": "no indicators here"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total_count"] == 0
        assert data["iocs"] == []
        assert data["grouped"] == {}

    def test_online_no_iocs_skips_enrichment_setup(self, client, monkeypatch):
        from app.routes import api as api_routes

        client.application.registry.configured.side_effect = AssertionError(
            "zero-IOC online analysis should not check provider configuration"
        )

        def fail_serialize(_ioc):
            raise AssertionError("zero-IOC API analysis should not serialize IOC payloads")

        def fail_group_append(*_args):
            raise AssertionError("zero-IOC API analysis should not group serialized payloads")

        monkeypatch.setattr(api_routes, "_serialize_ioc", fail_serialize)
        monkeypatch.setattr(api_routes, "_append_serialized_ioc_by_type", fail_group_append)

        with patch("app.routes._helpers._enrichment_pool") as mock_pool:
            resp = client.post(
                "/api/analyze",
                json={"text": "no indicators here", "mode": "online"},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["mode"] == "online"
        assert data["total_count"] == 0
        assert data["iocs"] == []
        assert data["grouped"] == {}
        assert "job_id" not in data
        mock_pool.submit.assert_not_called()
        assert "total_count == 0" in inspect.getsource(api_routes.api_analyze)

    def test_ioc_structure(self, client):
        resp = client.post("/api/analyze", json={"text": "8.8.8.8"})
        data = resp.get_json()
        if data["total_count"] > 0:
            ioc = data["iocs"][0]
            assert "type" in ioc
            assert "value" in ioc
            assert "raw_match" in ioc

    def test_serialized_response_public_shape_preserves_duplicates_by_type_order(self, client, monkeypatch):
        """API responses should keep flat rows and grouped rows in the same route-visible shape."""
        from app.pipeline.models import IOC
        from app.routes import api as api_routes

        iocs = [
            IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8[.]8[.]8[.]8"),
            IOC(type=IOCType.DOMAIN, value="evil.example", raw_match="evil[.]example"),
            IOC(type=IOCType.IPV4, value="1.1.1.1", raw_match="1[.]1[.]1[.]1"),
        ]
        monkeypatch.setattr(api_routes, "run_pipeline", lambda _text: iocs)

        resp = client.post("/api/analyze", json={"text": "synthetic grouped indicators"})
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["mode"] == "offline"
        assert data["total_count"] == 3
        assert data["iocs"] == [
            {"type": "ipv4", "value": "8.8.8.8", "raw_match": "8[.]8[.]8[.]8"},
            {"type": "domain", "value": "evil.example", "raw_match": "evil[.]example"},
            {"type": "ipv4", "value": "1.1.1.1", "raw_match": "1[.]1[.]1[.]1"},
        ]
        assert data["grouped"] == {
            "ipv4": [data["iocs"][0], data["iocs"][2]],
            "domain": [data["iocs"][1]],
        }


# ---------- POST /api/analyze — online mode ----------


class TestApiAnalyzeOnline:
    """Online mode — extract IOCs and launch background enrichment."""

    def test_online_no_providers(self, client):
        """Online mode with no configured providers returns 400."""
        client.application.registry.configured.return_value = []
        resp = client.post("/api/analyze", json={"text": "8.8.8.8", "mode": "online"})
        assert resp.status_code == 400
        assert "No provider" in resp.get_json()["error"]

    def test_online_no_providers_skips_ioc_serialization(self, client, monkeypatch):
        """Rejected online requests should not serialize IOC response payloads."""
        from app.routes import api as api_routes

        client.application.registry.configured.return_value = []

        def fail_serialize(_ioc):
            raise AssertionError("online rejection should not serialize IOCs")

        monkeypatch.setattr(api_routes, "_serialize_ioc", fail_serialize)

        resp = client.post("/api/analyze", json={"text": "8.8.8.8", "mode": "online"})

        assert resp.status_code == 400
        assert "No provider" in resp.get_json()["error"]

    def test_online_with_provider(self, client):
        """Online mode with a configured provider returns job_id."""
        mock_provider = MagicMock()
        mock_provider.name = "test_provider"
        mock_provider.supported_types = frozenset({IOCType.IPV4})
        client.application.registry.configured.return_value = [mock_provider]
        client.application.registry.all.return_value = [mock_provider]
        client.application.registry.providers_for_type.return_value = [mock_provider]
        client.application.registry.provider_count_for_type.return_value = 1

        with patch("app.routes._helpers._enrichment_pool") as mock_pool:
            resp = client.post("/api/analyze", json={"text": "8.8.8.8", "mode": "online"})
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["mode"] == "online"
            assert "job_id" in data
            assert "status_url" in data
            assert data["status_url"].startswith("/api/status/")
            mock_pool.submit.assert_called_once()
            assert client.application.registry.configured.call_count == 1


    def test_online_rejects_ioc_limit_before_launch(self, client):
        """Online mode rejects oversized IOC batches before submitting work."""
        mock_provider = MagicMock()
        mock_provider.name = "test_provider"
        mock_provider.supported_types = frozenset({IOCType.IPV4})
        client.application.registry.configured.return_value = [mock_provider]
        client.application.registry.all.return_value = [mock_provider]
        client.application.registry.providers_for_type.return_value = [mock_provider]
        client.application.registry.provider_count_for_type.return_value = 1
        client.application.config["ONLINE_MAX_IOCS"] = 1
        client.application.config["ONLINE_MAX_DISPATCHES"] = 200

        with patch("app.routes._helpers._enrichment_pool") as mock_pool:
            resp = client.post(
                "/api/analyze",
                json={"text": "8.8.8.8 and 1.1.1.1", "mode": "online"},
            )

        assert resp.status_code == 413
        data = resp.get_json()
        assert data["code"] == "online_limit_exceeded"
        assert data["observed"]["ioc_count"] >= 2
        assert "8.8.8.8" not in str(data)
        mock_pool.submit.assert_not_called()

    def test_online_uses_shared_limit_config_helper(self, client):
        """API online admission should read limits through the shared helper."""
        mock_provider = MagicMock()
        mock_provider.name = "test_provider"
        mock_provider.supported_types = frozenset({IOCType.IPV4})
        client.application.registry.configured.return_value = [mock_provider]
        client.application.registry.all.return_value = [mock_provider]
        client.application.registry.providers_for_type.return_value = [mock_provider]
        client.application.registry.provider_count_for_type.return_value = 1
        client.application.config["ONLINE_MAX_IOCS"] = 50
        client.application.config["ONLINE_MAX_DISPATCHES"] = 200

        with (
            patch("app.routes.api._online_limits_from_config", return_value=(1, 200)) as limits,
            patch("app.routes._helpers._enrichment_pool") as mock_pool,
        ):
            resp = client.post(
                "/api/analyze",
                json={"text": "8.8.8.8 and 1.1.1.1", "mode": "online"},
            )

        assert resp.status_code == 413
        data = resp.get_json()
        assert data["code"] == "online_limit_exceeded"
        limits.assert_called_once_with()
        mock_pool.submit.assert_not_called()

    def test_online_rejects_dispatch_limit_before_launch(self, client):
        """Online mode rejects excessive provider fanout before submitting work."""
        mock_provider_a = MagicMock()
        mock_provider_b = MagicMock()
        providers = [mock_provider_a, mock_provider_b]
        client.application.registry.configured.return_value = providers
        client.application.registry.all.return_value = providers
        client.application.registry.providers_for_type.return_value = providers
        client.application.registry.provider_count_for_type.return_value = 2
        client.application.config["ONLINE_MAX_IOCS"] = 50
        client.application.config["ONLINE_MAX_DISPATCHES"] = 1

        with patch("app.routes._helpers._enrichment_pool") as mock_pool:
            resp = client.post("/api/analyze", json={"text": "8.8.8.8", "mode": "online"})

        assert resp.status_code == 413
        data = resp.get_json()
        assert data["code"] == "online_limit_exceeded"
        assert data["observed"]["dispatch_count"] == 2
        mock_pool.submit.assert_not_called()


# ---------- GET /api/status/<job_id> ----------


class TestApiStatus:
    """Enrichment polling via GET /api/status/<job_id>."""

    def test_unknown_job(self, client):
        resp = client.get("/api/status/nonexistent?since=2")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"] == "Enrichment job was not found."
        assert data["status"] == "failed"
        assert data["terminal"] is True
        assert data["terminal_reason"] == "unknown"
        assert data["next_since"] == 2

    def test_known_job(self, client):
        """Known job returns polling progress."""
        import app.routes._helpers as helpers

        ioc = make_ipv4_ioc()
        result = EnrichmentResult(
            ioc=ioc,
            provider="test",
            verdict="clean",
            detection_count=0,
            total_engines=10,
            scan_date=None,
            raw_stats={},
        )
        mock_orch = _build_incremental_snapshot_orchestrator([result])

        job_id = "test_job_123"
        helpers._orchestrators[job_id] = mock_orch
        try:
            resp = client.get(f"/api/status/{job_id}")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["total"] == 1
            assert data["done"] == 1
            assert data["complete"] is True
            assert data["status"] == "complete"
            assert data["terminal"] is False
            assert data["terminal_reason"] is None
            assert len(data["results"]) == 1
            assert data["results"][0]["verdict"] == "clean"
            mock_orch.get_incremental_status.assert_called_once_with(job_id, since=0)
            mock_orch.get_status.assert_not_called()
        finally:
            helpers._orchestrators.pop(job_id, None)

    def test_since_cursor(self, client):
        """?since= cursor filters results."""
        import app.routes._helpers as helpers

        ioc = make_ipv4_ioc()
        results = [
            EnrichmentResult(
                ioc=ioc,
                provider="p1",
                verdict="clean",
                detection_count=0,
                total_engines=10,
                scan_date=None,
                raw_stats={},
            ),
            EnrichmentResult(
                ioc=ioc,
                provider="p2",
                verdict="malicious",
                detection_count=5,
                total_engines=10,
                scan_date=None,
                raw_stats={},
            ),
        ]
        mock_orch = _build_incremental_snapshot_orchestrator(results)

        job_id = "cursor_test"
        helpers._orchestrators[job_id] = mock_orch
        try:
            resp = client.get(f"/api/status/{job_id}?since=1")
            assert resp.status_code == 200
            data = resp.get_json()
            assert len(data["results"]) == 1
            assert data["results"][0]["provider"] == "p2"
            assert data["next_since"] == 2
            assert data["status"] == "complete"
            assert data["terminal"] is False
            mock_orch.get_incremental_status.assert_called_once_with(job_id, since=1)
            mock_orch.get_status.assert_not_called()
        finally:
            helpers._orchestrators.pop(job_id, None)

    def test_cached_delta_rows_preserve_cached_at(self, client):
        """Cached results keep cached_at on the API polling surface."""
        import app.routes._helpers as helpers

        fresh_result = EnrichmentResult(
            ioc=make_ipv4_ioc("1.1.1.1"),
            provider="fresh",
            verdict="clean",
            detection_count=0,
            total_engines=5,
            scan_date=None,
            raw_stats={},
        )
        cached_ioc = make_ipv4_ioc("2.2.2.2")
        cached_result = EnrichmentResult(
            ioc=cached_ioc,
            provider="cached",
            verdict="clean",
            detection_count=0,
            total_engines=5,
            scan_date=None,
            raw_stats={},
        )
        cache_key = f"{cached_ioc.value}|{cached_result.provider}"
        mock_orch = _build_incremental_snapshot_orchestrator(
            [fresh_result, cached_result],
            cached_markers={cache_key: "2026-04-25T00:00:00Z"},
        )

        job_id = "cached_delta_job"
        helpers._orchestrators[job_id] = mock_orch
        try:
            resp = client.get(f"/api/status/{job_id}")
            assert resp.status_code == 200
            data = resp.get_json()
            assert "cached_at" not in data["results"][0]
            assert data["results"][1]["cached_at"] == "2026-04-25T00:00:00Z"
        finally:
            helpers._orchestrators.pop(job_id, None)

    def test_negative_since_exact_length_and_empty_tail_preserve_cursor(self, client):
        """Negative, exact-length, and beyond-range since values preserve polling cursor semantics."""
        import app.routes._helpers as helpers

        ioc = make_ipv4_ioc()
        results = [
            EnrichmentResult(
                ioc=ioc,
                provider="p1",
                verdict="clean",
                detection_count=0,
                total_engines=10,
                scan_date=None,
                raw_stats={},
            ),
            EnrichmentResult(
                ioc=ioc,
                provider="p2",
                verdict="malicious",
                detection_count=1,
                total_engines=10,
                scan_date=None,
                raw_stats={},
            ),
        ]
        mock_orch = _build_incremental_snapshot_orchestrator(results)

        job_id = "cursor_edges"
        helpers._orchestrators[job_id] = mock_orch
        try:
            negative = client.get(f"/api/status/{job_id}?since=-1")
            assert negative.status_code == 200
            negative_data = negative.get_json()
            assert len(negative_data["results"]) == 1
            assert negative_data["results"][0]["provider"] == "p2"
            assert negative_data["next_since"] == 2

            exact = client.get(f"/api/status/{job_id}?since=2")
            assert exact.status_code == 200
            exact_data = exact.get_json()
            assert exact_data["results"] == []
            assert exact_data["next_since"] == 2

            empty = client.get(f"/api/status/{job_id}?since=99")
            assert empty.status_code == 200
            empty_data = empty.get_json()
            assert empty_data["results"] == []
            assert empty_data["next_since"] == 2
        finally:
            helpers._orchestrators.pop(job_id, None)

    def test_api_and_html_status_routes_stay_in_parity(self, client):
        """The API and HTML polling wrappers expose identical payloads for the same job."""
        import app.routes._helpers as helpers

        ioc = make_ipv4_ioc()
        cached_result = EnrichmentResult(
            ioc=ioc,
            provider="p2",
            verdict="clean",
            detection_count=0,
            total_engines=10,
            scan_date=None,
            raw_stats={},
        )
        cache_key = f"{ioc.value}|{cached_result.provider}"
        mock_orch = _build_incremental_snapshot_orchestrator(
            [
                EnrichmentResult(
                    ioc=ioc,
                    provider="p1",
                    verdict="clean",
                    detection_count=0,
                    total_engines=10,
                    scan_date=None,
                    raw_stats={},
                ),
                cached_result,
            ],
            cached_markers={cache_key: "2026-04-25T00:00:00Z"},
        )

        job_id = "parity_job"
        helpers._orchestrators[job_id] = mock_orch
        try:
            api_resp = client.get(f"/api/status/{job_id}?since=1")
            html_resp = client.get(f"/enrichment/status/{job_id}?since=1")
            assert api_resp.status_code == 200
            assert html_resp.status_code == 200
            assert api_resp.get_json() == html_resp.get_json()
        finally:
            helpers._orchestrators.pop(job_id, None)


# ---------- CSRF exemption ----------


class TestApiCsrfExemption:
    """API routes work without CSRF tokens."""

    def test_api_post_without_csrf(self, client_with_csrf):
        """POST /api/analyze succeeds without CSRF token."""
        resp = client_with_csrf.post(
            "/api/analyze",
            json={"text": "8.8.8.8"},
        )
        # Should NOT be 400 with CSRF error
        assert resp.status_code == 200

    def test_browser_post_requires_csrf(self, client_with_csrf):
        """POST /analyze (browser route) fails without CSRF token."""
        resp = client_with_csrf.post(
            "/analyze",
            data={"text": "8.8.8.8", "mode": "offline"},
        )
        # Flask-WTF returns 400 for missing CSRF
        assert resp.status_code == 400
