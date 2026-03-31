"""Tests for the REST API blueprint (/api/analyze, /api/status/<job_id>)."""

from unittest.mock import MagicMock, patch

import pytest

from app import create_app
from app.enrichment.models import EnrichmentResult
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

        with patch("app.routes.api._enrichment_pool") as mock_pool:
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
        resp = client.get("/api/status/nonexistent")
        assert resp.status_code == 404
        assert "not found" in resp.get_json()["error"]

    def test_known_job(self, client):
        """Known job returns polling progress."""
        import app.routes._helpers as helpers

        mock_orch = MagicMock()
        ioc = make_ipv4_ioc()
        result = EnrichmentResult(
            ioc=ioc, provider="test", verdict="clean",
            detection_count=0, total_engines=10, scan_date=None,
            raw_stats={},
        )
        mock_orch.get_status.return_value = {
            "total": 1, "done": 1, "complete": True,
            "results": [result],
        }
        mock_orch.cached_markers = {}

        job_id = "test_job_123"
        helpers._orchestrators[job_id] = mock_orch
        try:
            resp = client.get(f"/api/status/{job_id}")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["total"] == 1
            assert data["done"] == 1
            assert data["complete"] is True
            assert len(data["results"]) == 1
            assert data["results"][0]["verdict"] == "clean"
        finally:
            helpers._orchestrators.pop(job_id, None)

    def test_since_cursor(self, client):
        """?since= cursor filters results."""
        import app.routes._helpers as helpers

        mock_orch = MagicMock()
        ioc = make_ipv4_ioc()
        results = [
            EnrichmentResult(ioc=ioc, provider="p1", verdict="clean", detection_count=0, total_engines=10, scan_date=None, raw_stats={}),
            EnrichmentResult(ioc=ioc, provider="p2", verdict="malicious", detection_count=5, total_engines=10, scan_date=None, raw_stats={}),
        ]
        mock_orch.get_status.return_value = {
            "total": 2, "done": 2, "complete": True,
            "results": results,
        }
        mock_orch.cached_markers = {}

        job_id = "cursor_test"
        helpers._orchestrators[job_id] = mock_orch
        try:
            resp = client.get(f"/api/status/{job_id}?since=1")
            data = resp.get_json()
            assert len(data["results"]) == 1
            assert data["results"][0]["provider"] == "p2"
            assert data["next_since"] == 2
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
