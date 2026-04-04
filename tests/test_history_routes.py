"""Integration tests for analysis history routes.

Tests cover:
- History save is invoked after enrichment via _run_enrichment_and_save wrapper
- GET /history/<id> returns 200 with seeded data and correct template variables
- GET /history/<unknown_id> returns 404
- GET / includes recent analyses when history exists
- GET / works with no history (empty list)
- History results are embedded as data-history-results attribute
"""
import json
from unittest.mock import MagicMock

import pytest

from app.enrichment.history_store import HistoryStore
from app.pipeline.models import IOC, IOCType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def history_store(tmp_path):
    """Create a HistoryStore with a temporary database."""
    return HistoryStore(db_path=tmp_path / "test_history.db")


@pytest.fixture()
def seeded_store(history_store):
    """HistoryStore with one analysis already persisted."""
    iocs = [
        {"type": "ipv4", "value": "10.0.0.1", "raw_match": "10[.]0[.]0[.]1"},
        {"type": "domain", "value": "evil.com", "raw_match": "evil[.]com"},
    ]
    results = [
        {
            "type": "result",
            "ioc_value": "10.0.0.1",
            "ioc_type": "ipv4",
            "provider": "TestProvider",
            "verdict": "malicious",
            "detection_count": 5,
            "total_engines": 70,
            "scan_date": "2025-01-01T00:00:00",
            "raw_stats": {},
        },
        {
            "type": "result",
            "ioc_value": "evil.com",
            "ioc_type": "domain",
            "provider": "TestProvider",
            "verdict": "clean",
            "detection_count": 0,
            "total_engines": 70,
            "scan_date": "2025-01-01T00:00:00",
            "raw_stats": {},
        },
    ]
    analysis_id = history_store.save_analysis(
        input_text="Alert from 10[.]0[.]0[.]1 calling evil[.]com",
        mode="online",
        iocs=iocs,
        results=results,
        analysis_id="abc123deadbeef",
    )
    return history_store, analysis_id, iocs, results


# ---------------------------------------------------------------------------
# _run_enrichment_and_save wrapper tests
# ---------------------------------------------------------------------------


class TestEnrichmentSaveWrapper:
    """Tests for _run_enrichment_and_save integration."""

    def test_save_called_after_enrichment(self):
        """The wrapper calls enrich_all then saves to HistoryStore."""
        from app.routes._helpers import _run_enrichment_and_save

        mock_orch = MagicMock()
        mock_orch.enrich_all.return_value = None
        mock_orch.get_status.return_value = {
            "total": 1,
            "done": 1,
            "complete": True,
            "results": [],
        }

        iocs = [IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10[.]0[.]0[.]1")]
        mock_store = MagicMock()

        _run_enrichment_and_save(
            mock_orch, "test_job_id", iocs, "test input", "online", mock_store
        )

        mock_orch.enrich_all.assert_called_once_with("test_job_id", iocs)
        mock_store.save_analysis.assert_called_once()
        call_kwargs = mock_store.save_analysis.call_args
        assert call_kwargs[1]["input_text"] == "test input"
        assert call_kwargs[1]["mode"] == "online"
        assert call_kwargs[1]["analysis_id"] == "test_job_id"

    def test_save_failure_does_not_break_enrichment(self):
        """If HistoryStore.save_analysis raises, enrichment still completes."""
        from app.routes._helpers import _run_enrichment_and_save

        mock_orch = MagicMock()
        mock_orch.enrich_all.return_value = None
        mock_orch.get_status.return_value = {
            "total": 1,
            "done": 1,
            "complete": True,
            "results": [],
        }

        iocs = [IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10[.]0[.]0[.]1")]
        mock_store = MagicMock()
        mock_store.save_analysis.side_effect = Exception("DB error")

        # Should not raise
        _run_enrichment_and_save(
            mock_orch, "test_job_id", iocs, "test input", "online", mock_store
        )

        # enrich_all was still called
        mock_orch.enrich_all.assert_called_once()

    def test_save_skipped_when_status_none(self):
        """If orchestrator.get_status returns None, save is skipped."""
        from app.routes._helpers import _run_enrichment_and_save

        mock_orch = MagicMock()
        mock_orch.enrich_all.return_value = None
        mock_orch.get_status.return_value = None

        iocs = [IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10[.]0[.]0[.]1")]
        mock_store = MagicMock()

        _run_enrichment_and_save(
            mock_orch, "test_job_id", iocs, "test input", "online", mock_store
        )

        mock_store.save_analysis.assert_not_called()


# ---------------------------------------------------------------------------
# GET /history/<analysis_id> tests
# ---------------------------------------------------------------------------


class TestHistoryDetailRoute:
    """Tests for GET /history/<analysis_id>."""

    def test_history_returns_200_with_seeded_data(self, client, seeded_store):
        """GET /history/<id> returns 200 and renders results page."""
        store, analysis_id, _, _ = seeded_store
        client.application.history_store = store
        response = client.get(f"/history/{analysis_id}")
        assert response.status_code == 200
        # Should contain IOC values from the seeded data
        assert b"10.0.0.1" in response.data
        assert b"evil.com" in response.data

    def test_history_returns_404_for_unknown_id(self, client):
        """GET /history/<unknown_id> returns 404."""
        mock_store = MagicMock()
        mock_store.load_analysis.return_value = None
        client.application.history_store = mock_store
        response = client.get("/history/nonexistent_id_12345")
        assert response.status_code == 404

    def test_history_contains_history_results_attribute(self, client, seeded_store):
        """Response HTML includes data-history-results attribute for JS replay."""
        store, analysis_id, _, _ = seeded_store
        client.application.history_store = store
        response = client.get(f"/history/{analysis_id}")
        assert response.status_code == 200
        assert b"data-history-results" in response.data

    def test_history_renders_online_mode(self, client, seeded_store):
        """History page renders in online mode with job_id='history'."""
        store, analysis_id, _, _ = seeded_store
        client.application.history_store = store
        response = client.get(f"/history/{analysis_id}")
        assert response.status_code == 200
        assert b'data-job-id="history"' in response.data
        assert b'data-mode="online"' in response.data

    def test_history_shows_correct_ioc_count(self, client, seeded_store):
        """History page shows the correct total IOC count."""
        store, analysis_id, _, _ = seeded_store
        client.application.history_store = store
        response = client.get(f"/history/{analysis_id}")
        assert response.status_code == 200
        assert b"2 unique IOCs" in response.data


# ---------------------------------------------------------------------------
# GET / with recent analyses tests
# ---------------------------------------------------------------------------


class TestHistoryListRoute:
    """Tests for GET /history listing recent analyses."""

    def test_history_list_shows_analyses(self, client, seeded_store):
        """GET /history lists recent analyses when history exists."""
        store, _, _, _ = seeded_store
        client.application.history_store = store
        response = client.get("/history")
        assert response.status_code == 200
        assert b"Recent Analyses" in response.data
        assert b"abc123deadbeef" in response.data  # link contains analysis id

    def test_history_list_empty(self, client):
        """GET /history shows empty-state message with no history."""
        mock_store = MagicMock()
        mock_store.list_recent.return_value = []
        client.application.history_store = mock_store
        response = client.get("/history")
        assert response.status_code == 200
        assert b"No analyses yet" in response.data

    def test_history_list_shows_verdict_badge(self, client, seeded_store):
        """GET /history shows verdict badge for each analysis."""
        store, _, _, _ = seeded_store
        client.application.history_store = store
        response = client.get("/history")
        assert response.status_code == 200
        assert b"malicious" in response.data

    def test_index_no_recent_analyses(self, client, seeded_store):
        """GET / no longer shows recent analyses section."""
        store, _, _, _ = seeded_store
        client.application.history_store = store
        response = client.get("/")
        assert response.status_code == 200
        assert b"Recent Analyses" not in response.data


# ---------------------------------------------------------------------------
# IOC serialization helper test
# ---------------------------------------------------------------------------


class TestSerializeIoc:
    """Tests for _serialize_ioc helper."""

    def test_serialize_ioc(self):
        """_serialize_ioc returns a dict with type, value, raw_match."""
        from app.routes._helpers import _serialize_ioc

        ioc = IOC(type=IOCType.DOMAIN, value="example.com", raw_match="example[.]com")
        result = _serialize_ioc(ioc)
        assert result == {
            "type": "domain",
            "value": "example.com",
            "raw_match": "example[.]com",
        }
