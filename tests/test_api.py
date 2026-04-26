"""Tests for the REST API blueprint (/api/analyze, /api/status/<job_id>)."""

from unittest.mock import MagicMock, patch

import pytest

from app import create_app
from app.enrichment.models import EnrichmentResult
from app.health_contract import HEALTH_PATH, HEALTH_PAYLOAD
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

    def test_health_contract_constants_stay_fixed_and_secret_free(self):
        assert HEALTH_PATH == "/api/health"
        assert HEALTH_PAYLOAD == {
            "service": "sentinelx",
            "status": "ok",
            "ready": True,
        }
        assert "provider_key" not in HEALTH_PAYLOAD

    def test_health_returns_fixed_secret_free_json(self, client):
        resp = client.get(HEALTH_PATH)

        assert resp.status_code == 200
        assert resp.is_json is True
        assert resp.get_json() == HEALTH_PAYLOAD

    def test_health_does_not_touch_provider_configuration(self, client):
        resp = client.get(HEALTH_PATH)

        assert resp.status_code == 200
        client.application.registry.configured.assert_not_called()
        client.application.registry.all.assert_not_called()


# ---------- POST /api/analyze — validation ----------


class TestApiAnalyzeValidation:
    """Input validation for POST /api/analyze."""

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
        resp = client.post("/api/analyze", json={"text": "8.8.8.8", "mode": "turbo"})
        assert resp.status_code == 400
        assert "Invalid mode" in resp.get_json()["error"]

    def test_text_not_string(self, client):
        resp = client.post("/api/analyze", json={"text": 12345})
        assert resp.status_code == 400


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

    def test_no_iocs_found(self, client):
        resp = client.post("/api/analyze", json={"text": "no indicators here"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total_count"] == 0
        assert data["iocs"] == []

    def test_ioc_structure(self, client):
        resp = client.post("/api/analyze", json={"text": "8.8.8.8"})
        data = resp.get_json()
        if data["total_count"] > 0:
            ioc = data["iocs"][0]
            assert "type" in ioc
            assert "value" in ioc
            assert "raw_match" in ioc


# ---------- POST /api/analyze — online mode ----------


class TestApiAnalyzeOnline:
    """Online mode — extract IOCs and launch background enrichment."""

    def test_online_no_providers(self, client):
        """Online mode with no configured providers returns 400."""
        client.application.registry.configured.return_value = []
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

        with patch("app.routes._helpers._enrichment_pool") as mock_pool:
            resp = client.post("/api/analyze", json={"text": "8.8.8.8", "mode": "online"})
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["mode"] == "online"
            assert "job_id" in data
            assert "status_url" in data
            assert data["status_url"].startswith("/api/status/")
            mock_pool.submit.assert_called_once()


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
