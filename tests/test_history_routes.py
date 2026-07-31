"""Integration tests for analysis history routes.

Tests cover:
- History save is invoked after enrichment via _run_enrichment_and_save wrapper
- GET /history/<id> returns 200 with seeded data and correct template variables
- GET /history/<unknown_id> returns 404
- GET / includes recent analyses when history exists
- GET / works with no history (empty list)
- History results are embedded as data-history-results attribute
"""
import builtins
import inspect
from pathlib import Path
from types import MappingProxyType
from unittest.mock import MagicMock, call, patch

import pytest

from app.enrichment.models import EnrichmentResult
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


@pytest.fixture(autouse=True)
def reset_history_save_diagnostics():
    """Reset helper diagnostics so each test observes a fresh aggregate snapshot."""
    from app.enrichment.history_diagnostics import reset_history_save_diagnostics

    reset_history_save_diagnostics()
    yield
    reset_history_save_diagnostics()


# ---------------------------------------------------------------------------
# _run_enrichment_and_save wrapper tests
# ---------------------------------------------------------------------------


class TestEnrichmentSaveWrapper:
    """Tests for _run_enrichment_and_save integration."""

    def test_save_called_after_enrichment(self):
        """The wrapper calls enrich_all then saves to HistoryStore."""
        from app.enrichment.history_diagnostics import get_history_save_diagnostics
        from app.routes.enrichment_jobs import _run_enrichment_and_save

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
        assert call_kwargs[1]["results"] == [
            {
                "type": "workflow",
                "status": "complete",
                "complete": True,
                "terminal": False,
                "terminal_reason": None,
                "error": None,
                "done": 1,
                "total": 1,
            }
        ]

        diagnostics = get_history_save_diagnostics()
        assert diagnostics["attempts"] == 1
        assert diagnostics["successes"] == 1
        assert diagnostics["failures"] == 0
        assert diagnostics["skipped"] == 0
        assert diagnostics["last_outcome"] == "saved"
        assert diagnostics["last_attempt_at"] is not None
        assert diagnostics["last_success_at"] is not None
        assert diagnostics["last_failure_at"] is None
        assert diagnostics["last_error_summary"] is None

    def test_save_serializes_results_and_iocs_with_direct_loops(self, monkeypatch):
        """History-save serialization should preserve order without map-based helpers."""
        from app.routes.enrichment_jobs import _run_enrichment_and_save

        ioc_a = IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10[.]0[.]0[.]1")
        ioc_b = IOC(type=IOCType.DOMAIN, value="example.com", raw_match="example[.]com")
        result = EnrichmentResult(
            ioc=ioc_a,
            provider="ProviderA",
            verdict="clean",
            detection_count=0,
            total_engines=1,
            scan_date=None,
            raw_stats={"ok": True},
        )
        mock_orch = MagicMock()
        mock_orch.enrich_all.return_value = None
        mock_orch.get_status.return_value = {
            "total": 1,
            "done": 1,
            "complete": True,
            "results": [result],
        }
        mock_store = MagicMock()

        def fail_map(*_args, **_kwargs):
            raise AssertionError("history-save serialization should use direct loops")

        monkeypatch.setattr(builtins, "map", fail_map)

        _run_enrichment_and_save(
            mock_orch,
            "test_job_id",
            [ioc_a, ioc_b],
            "test input",
            "online",
            mock_store,
        )

        save_kwargs = mock_store.save_analysis.call_args.kwargs
        assert [ioc["value"] for ioc in save_kwargs["iocs"]] == ["10.0.0.1", "example.com"]
        assert save_kwargs["results"][0]["provider"] == "ProviderA"
        assert save_kwargs["results"][1]["type"] == "workflow"

    def test_history_save_status_helper_delegates_serialization_helper(self, monkeypatch):
        """Completed status saves should delegate persistence payload construction."""
        from app.routes import enrichment_history, enrichment_jobs

        ioc = IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10[.]0[.]0[.]1")
        result = EnrichmentResult(
            ioc=ioc,
            provider="ProviderA",
            verdict="clean",
            detection_count=0,
            total_engines=1,
            scan_date=None,
            raw_stats={"ok": True},
        )
        mock_store = MagicMock()
        calls: list[str] = []
        route_source = inspect.getsource(enrichment_jobs)
        helper_source = inspect.getsource(enrichment_history.save_enrichment_status_history)
        persistence_source = inspect.getsource(enrichment_history.save_enrichment_history)

        def record_attempt():
            calls.append("attempt")

        def record_save(**kwargs):
            calls.append("save")
            assert kwargs == {
                "history_store": mock_store,
                "input_text": "test input",
                "mode": "online",
                "iocs": [ioc],
                "results": [result],
                "workflow": {
                    "type": "workflow",
                    "status": "complete",
                    "complete": True,
                    "terminal": False,
                    "terminal_reason": None,
                    "error": None,
                    "done": 1,
                    "total": 1,
                },
                "analysis_id": "test_job_id",
            }

        monkeypatch.setattr(enrichment_history, "record_history_save_attempt", record_attempt)
        monkeypatch.setattr(enrichment_history, "save_enrichment_history", record_save)

        outcome = enrichment_history.save_enrichment_status_history(
            status={
                "total": 1,
                "done": 1,
                "complete": True,
                "results": [result],
            },
            history_store=mock_store,
            input_text="test input",
            mode="online",
            iocs=[ioc],
            analysis_id="test_job_id",
        )

        assert outcome == "saved"
        assert calls == ["attempt", "save"]
        assert "save_enrichment_history(" in helper_source
        assert "save_analysis(" not in helper_source
        assert "_serialize_iocs(iocs)" in persistence_source
        assert "enrichment_status.serialize_results(results)" in persistence_source
        assert "def _serialize_results(" not in inspect.getsource(enrichment_jobs)
        assert "def _save_enrichment_history(" not in route_source
        assert "def _save_enrichment_status_history(" not in route_source

    def test_run_enrichment_delegates_status_save_decision(self, monkeypatch):
        """Background runner should leave status save branching in one helper."""
        from app.routes import enrichment_jobs

        ioc = IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10[.]0[.]0[.]1")
        status = {
            "total": 1,
            "done": 1,
            "complete": True,
            "results": [],
        }
        mock_orch = MagicMock()
        mock_orch.enrich_all.return_value = None
        mock_orch.get_status.return_value = status
        mock_store = MagicMock()
        calls: list[tuple[str, object]] = []
        runner_source = inspect.getsource(enrichment_jobs._run_enrichment_and_save)
        save_source = inspect.getsource(enrichment_jobs._save_job_history)

        def record_status_save(**kwargs):
            calls.append(("save-status", kwargs))

        monkeypatch.setattr(enrichment_jobs, "save_enrichment_status_history", record_status_save)

        enrichment_jobs._run_enrichment_and_save(
            mock_orch,
            "test_job_id",
            [ioc],
            "test input",
            "online",
            mock_store,
        )

        assert calls == [
            (
                "save-status",
                {
                    "status": status,
                    "history_store": mock_store,
                    "input_text": "test input",
                    "mode": "online",
                    "iocs": [ioc],
                    "analysis_id": "test_job_id",
                },
            )
        ]
        assert "_save_job_history(" in runner_source
        assert "save_enrichment_status_history(" in save_source
        assert "record_history_save_attempt()" not in runner_source
        assert 'record_history_save_outcome("skipped")' not in runner_source

    def test_history_save_status_helper_records_skipped_without_persistence(self, monkeypatch):
        """Missing completed status should record a skip without a save attempt."""
        from app.routes import enrichment_history

        mock_store = MagicMock()
        calls: list[tuple[str, object]] = []

        def record_outcome(outcome, **_kwargs):
            calls.append(("outcome", outcome))

        def fail_attempt():
            raise AssertionError("skipped history save should not record an attempt")

        def fail_save(**_kwargs):
            raise AssertionError("skipped history save should not persist")

        monkeypatch.setattr(enrichment_history, "record_history_save_outcome", record_outcome)
        monkeypatch.setattr(enrichment_history, "record_history_save_attempt", fail_attempt)
        monkeypatch.setattr(enrichment_history, "save_enrichment_history", fail_save)

        outcome = enrichment_history.save_enrichment_status_history(
            status=None,
            history_store=mock_store,
            input_text="test input",
            mode="online",
            iocs=[],
            analysis_id="test_job_id",
        )

        assert outcome == "skipped"
        assert calls == [("outcome", "skipped")]

    def test_offline_extraction_is_not_saved(self):
        """Offline extraction does not enter Online enrichment history."""
        from app.routes.enrichment_history import save_enrichment_status_history

        mock_store = MagicMock()

        outcome = save_enrichment_status_history(
            status={
                "total": 0,
                "done": 0,
                "complete": True,
                "status": "complete",
                "results": [],
            },
            history_store=mock_store,
            input_text="offline input",
            mode="offline",
            iocs=[],
            analysis_id="offline-analysis",
        )

        assert outcome == "skipped"
        mock_store.save_analysis.assert_not_called()

    def test_failed_job_history_keeps_provider_evidence_and_workflow_metadata_separate(self):
        """A failed workflow is saved without inventing provider evidence."""
        from app.routes.enrichment_history import save_enrichment_status_history

        ioc = IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10[.]0[.]0[.]1")
        result = EnrichmentResult(
            ioc=ioc,
            provider="ProviderA",
            verdict="clean",
            detection_count=0,
            total_engines=1,
            scan_date=None,
            raw_stats={},
        )
        mock_store = MagicMock()

        outcome = save_enrichment_status_history(
            status={
                "total": 2,
                "done": 2,
                "complete": False,
                "status": "failed",
                "terminal": True,
                "terminal_reason": "partial_failure",
                "error": "1 of 2 enrichment lookups failed",
                "results": [result],
            },
            history_store=mock_store,
            input_text="test input",
            mode="online",
            iocs=[ioc],
            analysis_id="partial-job",
        )

        assert outcome == "saved"
        saved_results = mock_store.save_analysis.call_args.kwargs["results"]
        assert saved_results[0]["type"] == "result"
        assert saved_results[0]["provider"] == "ProviderA"
        assert saved_results[1] == {
            "type": "workflow",
            "status": "failed",
            "complete": False,
            "terminal": True,
            "terminal_reason": "partial_failure",
            "error": "1 of 2 enrichment lookups failed",
            "done": 2,
            "total": 2,
        }
        assert all(item.get("provider") != "SentinelX workflow" for item in saved_results)

    def test_save_failure_does_not_break_enrichment(self):
        """If HistoryStore.save_analysis raises, enrichment still completes."""
        from app.enrichment.history_diagnostics import get_history_save_diagnostics
        from app.routes.enrichment_jobs import _run_enrichment_and_save

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
        diagnostics = get_history_save_diagnostics()
        assert diagnostics["attempts"] == 1
        assert diagnostics["successes"] == 0
        assert diagnostics["failures"] == 1
        assert diagnostics["skipped"] == 0
        assert diagnostics["last_outcome"] == "failed"
        assert diagnostics["last_attempt_at"] is not None
        assert diagnostics["last_failure_at"] is not None
        assert diagnostics["last_error_summary"] == "Exception while saving analysis history"

    def test_save_skipped_when_status_none(self):
        """If orchestrator.get_status returns None, save is skipped."""
        from app.enrichment.history_diagnostics import get_history_save_diagnostics
        from app.routes.enrichment_jobs import _run_enrichment_and_save

        mock_orch = MagicMock()
        mock_orch.enrich_all.return_value = None
        mock_orch.get_status.return_value = None

        iocs = [IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10[.]0[.]0[.]1")]
        mock_store = MagicMock()

        _run_enrichment_and_save(
            mock_orch, "test_job_id", iocs, "test input", "online", mock_store
        )

        mock_store.save_analysis.assert_not_called()
        diagnostics = get_history_save_diagnostics()
        assert diagnostics["attempts"] == 0
        assert diagnostics["successes"] == 0
        assert diagnostics["failures"] == 0
        assert diagnostics["skipped"] == 1
        assert diagnostics["last_outcome"] == "skipped"
        assert diagnostics["last_attempt_at"] is None
        assert diagnostics["last_error_summary"] is None

    def test_history_save_diagnostics_falls_back_to_safe_defaults(self):
        """Malformed helper state is coerced to safe aggregate defaults."""
        from app.enrichment import history_diagnostics as _helpers

        source = inspect.getsource(_helpers.coerce_history_save_diagnostics)
        assert "dict(_HISTORY_SAVE_DIAGNOSTICS_DEFAULTS)" not in source
        assert '("attempts", "successes", "failures", "skipped")' not in source
        assert '("last_attempt_at", "last_success_at", "last_failure_at")' not in source
        assert "for field in _HISTORY_SAVE_COUNTER_FIELDS" not in source
        assert "for field in _HISTORY_SAVE_TIMESTAMP_FIELDS" not in source
        assert 'coerce_history_save_counter(diagnostics, data, "attempts")' in source
        assert 'coerce_history_save_timestamp(diagnostics, data, "last_failure_at")' in source
        accessor_source = inspect.getsource(_helpers.get_history_save_diagnostics)
        assert "dict(_history_save_diagnostics)" not in accessor_source
        assert isinstance(_helpers._HISTORY_SAVE_OUTCOMES, frozenset)
        assert isinstance(_helpers._HISTORY_SAVE_RECORDABLE_OUTCOMES, frozenset)
        assert isinstance(_helpers._HISTORY_SAVE_DIAGNOSTICS_DEFAULTS, MappingProxyType)
        import app.routes.enrichment_diagnostics as route_diagnostics

        assert not hasattr(route_diagnostics, "_history_save_diagnostics")

        malformed = {
            "attempts": "oops",
            "successes": -1,
            "failures": True,
            "skipped": 3,
            "last_outcome": "mystery",
            "last_attempt_at": "",
            "last_error_summary": {"raw": "payload"},
        }

        with patch.object(_helpers, "_history_save_diagnostics", malformed):
            diagnostics = _helpers.get_history_save_diagnostics()

        assert diagnostics == {
            "attempts": 0,
            "successes": 0,
            "failures": 0,
            "skipped": 3,
            "last_outcome": "never",
            "last_attempt_at": None,
            "last_success_at": None,
            "last_failure_at": None,
            "last_error_summary": None,
        }

    def test_history_save_diagnostics_presence_checks_avoid_timestamp_strip(self):
        """Timestamp presence checks should not allocate stripped copies."""
        from app.enrichment import history_diagnostics as _helpers

        class NoStripText(str):
            def strip(self, *_args, **_kwargs):
                raise AssertionError("timestamp presence should scan directly")

        raw = {
            "last_attempt_at": NoStripText("2026-01-01T00:00:00Z"),
            "last_success_at": NoStripText("   "),
            "last_failure_at": NoStripText("2026-01-01T00:00:01Z"),
        }

        diagnostics = _helpers.coerce_history_save_diagnostics(raw)

        assert diagnostics["last_attempt_at"] == "2026-01-01T00:00:00Z"
        assert diagnostics["last_success_at"] is None
        assert diagnostics["last_failure_at"] == "2026-01-01T00:00:01Z"

    def test_history_save_diagnostics_error_summary_avoids_strip_allocation(self):
        """Error summaries should trim through the shared bounded index helper."""
        from app.enrichment import history_diagnostics as _helpers

        class MeasuredStripText(str):
            def strip(self, *_args, **_kwargs):
                raise AssertionError("history error summaries should not allocate through strip()")

        diagnostics = _helpers.coerce_history_save_diagnostics({
            "last_error_summary": MeasuredStripText("  failed summary  "),
        })

        assert diagnostics["last_error_summary"] == "failed summary"


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

    def test_history_renders_online_mode_with_history_owner(self, client, seeded_store):
        """History page keeps online-mode DOM shape but advertises history ownership."""
        from app.json_utils import EMPTY_JSON_OBJECT

        store, analysis_id, _, results = seeded_store
        client.application.history_store = store
        response = client.get(f"/history/{analysis_id}")
        html = response.get_data(as_text=True)

        assert response.status_code == 200
        assert 'data-job-id="history"' in html
        assert 'data-mode="online"' in html
        assert 'data-results-owner="history"' in html
        assert f'data-provider-counts="{EMPTY_JSON_OBJECT}"' in html
        assert 'id="export-btn"' in html
        assert 'id="enrich-progress"' in html
        assert f"0/{len(results)} lookups complete" in html
        assert 'data-results-owner="live"' not in html
        assert EMPTY_JSON_OBJECT == "{}"

    def test_history_shows_correct_ioc_count(self, client, seeded_store):
        """History page shows the correct total IOC count."""
        store, analysis_id, _, _ = seeded_store
        client.application.history_store = store
        response = client.get(f"/history/{analysis_id}")
        assert response.status_code == 200
        assert b"2 unique IOCs" in response.data

    def test_history_replay_preserves_grouping_empty_payload_and_escaped_rows(self, client, history_store):
        """History replay should render grouped cards and an empty replay JSON payload safely."""
        iocs = [
            {"type": "ipv4", "value": "10.0.0.1", "raw_match": "10[.]0[.]0[.]1"},
            {"type": "domain", "value": "evil.example", "raw_match": "<script>alert(1)</script>"},
            {"type": "ipv4", "value": "10.0.0.2", "raw_match": "10[.]0[.]0[.]2"},
        ]
        analysis_id = history_store.save_analysis(
            input_text="persisted grouped indicators",
            mode="online",
            iocs=iocs,
            results=[],
            analysis_id="grouped-history-safe",
        )
        client.application.history_store = history_store

        response = client.get(f"/history/{analysis_id}")
        html = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "Found 3 unique IOCs" in html
        assert "10.0.0.1" in html
        assert "10.0.0.2" in html
        assert "evil.example" in html
        assert "data-history-results='[]'" in html
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
        assert "<script>alert(1)</script>" not in html

    def test_history_groups_iocs_while_rebuilding_models(self, client, seeded_store, monkeypatch):
        """History reload should not rescan rebuilt IOC objects just to group them."""
        from app.routes import ioc_payloads

        store, analysis_id, _, _ = seeded_store
        client.application.history_store = store

        def fail_group_by_type(_iocs):
            raise AssertionError("history reload should group persisted IOCs in one pass")

        monkeypatch.setattr(ioc_payloads, "group_by_type", fail_group_by_type)

        response = client.get(f"/history/{analysis_id}")

        assert response.status_code == 200
        assert b"10.0.0.1" in response.data
        assert b"evil.com" in response.data
        assert "setdefault" not in ioc_payloads._group_history_iocs.__code__.co_names

    def test_group_history_iocs_skips_iteration_for_empty_single_pair_three_or_four_rows(self):
        """Short history IOC groups should avoid the accumulator loop."""
        from app.routes import ioc_payloads

        class NoIterList(list):
            def __iter__(self):
                raise AssertionError("short history IOC grouping should not iterate")

            def __getitem__(self, index):
                if isinstance(index, slice):
                    raise AssertionError("history IOC grouping should not slice")
                return super().__getitem__(index)

        assert ioc_payloads._group_history_iocs(NoIterList()) == {}

        grouped = ioc_payloads._group_history_iocs(
            NoIterList([{"type": "ipv4", "value": "10.0.0.1", "raw_match": "10[.]0[.]0[.]1"}])
        )

        assert list(grouped) == [IOCType.IPV4]
        assert grouped[IOCType.IPV4] == [
            IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10[.]0[.]0[.]1")
        ]
        same_type_grouped = ioc_payloads._group_history_iocs(
            NoIterList([
                {"type": "ipv4", "value": "10.0.0.1", "raw_match": "10[.]0[.]0[.]1"},
                {"type": "ipv4", "value": "10.0.0.2", "raw_match": "10[.]0[.]0[.]2"},
            ])
        )
        mixed_type_grouped = ioc_payloads._group_history_iocs(
            NoIterList([
                {"type": "ipv4", "value": "10.0.0.1", "raw_match": "10[.]0[.]0[.]1"},
                {"type": "domain", "value": "evil.com", "raw_match": "evil[.]com"},
            ])
        )
        three_grouped = ioc_payloads._group_history_iocs(
            NoIterList([
                {"type": "ipv4", "value": "10.0.0.1", "raw_match": "10[.]0[.]0[.]1"},
                {"type": "domain", "value": "evil.com", "raw_match": "evil[.]com"},
                {"type": "ipv4", "value": "10.0.0.2", "raw_match": "10[.]0[.]0[.]2"},
            ])
        )
        same_type_three_grouped = ioc_payloads._group_history_iocs(
            NoIterList([
                {"type": "ipv4", "value": "10.0.0.1", "raw_match": "10[.]0[.]0[.]1"},
                {"type": "ipv4", "value": "10.0.0.2", "raw_match": "10[.]0[.]0[.]2"},
                {"type": "ipv4", "value": "10.0.0.3", "raw_match": "10[.]0[.]0[.]3"},
            ])
        )
        four_grouped = ioc_payloads._group_history_iocs(
            NoIterList([
                {"type": "ipv4", "value": "10.0.0.1", "raw_match": "10[.]0[.]0[.]1"},
                {"type": "domain", "value": "evil.com", "raw_match": "evil[.]com"},
                {"type": "ipv4", "value": "10.0.0.2", "raw_match": "10[.]0[.]0[.]2"},
                {"type": "domain", "value": "good.com", "raw_match": "good[.]com"},
            ])
        )
        same_type_four_grouped = ioc_payloads._group_history_iocs(
            NoIterList([
                {"type": "ipv4", "value": "10.0.0.1", "raw_match": "10[.]0[.]0[.]1"},
                {"type": "ipv4", "value": "10.0.0.2", "raw_match": "10[.]0[.]0[.]2"},
                {"type": "ipv4", "value": "10.0.0.3", "raw_match": "10[.]0[.]0[.]3"},
                {"type": "ipv4", "value": "10.0.0.4", "raw_match": "10[.]0[.]0[.]4"},
            ])
        )

        assert same_type_grouped[IOCType.IPV4] == [
            IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10[.]0[.]0[.]1"),
            IOC(type=IOCType.IPV4, value="10.0.0.2", raw_match="10[.]0[.]0[.]2"),
        ]
        assert mixed_type_grouped[IOCType.IPV4] == [
            IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10[.]0[.]0[.]1")
        ]
        assert mixed_type_grouped[IOCType.DOMAIN] == [
            IOC(type=IOCType.DOMAIN, value="evil.com", raw_match="evil[.]com")
        ]
        assert three_grouped[IOCType.IPV4] == [
            IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10[.]0[.]0[.]1"),
            IOC(type=IOCType.IPV4, value="10.0.0.2", raw_match="10[.]0[.]0[.]2"),
        ]
        assert three_grouped[IOCType.DOMAIN] == [
            IOC(type=IOCType.DOMAIN, value="evil.com", raw_match="evil[.]com")
        ]
        assert same_type_three_grouped[IOCType.IPV4] == [
            IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10[.]0[.]0[.]1"),
            IOC(type=IOCType.IPV4, value="10.0.0.2", raw_match="10[.]0[.]0[.]2"),
            IOC(type=IOCType.IPV4, value="10.0.0.3", raw_match="10[.]0[.]0[.]3"),
        ]
        assert four_grouped[IOCType.IPV4] == [
            IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10[.]0[.]0[.]1"),
            IOC(type=IOCType.IPV4, value="10.0.0.2", raw_match="10[.]0[.]0[.]2"),
        ]
        assert four_grouped[IOCType.DOMAIN] == [
            IOC(type=IOCType.DOMAIN, value="evil.com", raw_match="evil[.]com"),
            IOC(type=IOCType.DOMAIN, value="good.com", raw_match="good[.]com"),
        ]
        assert same_type_four_grouped[IOCType.IPV4] == [
            IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10[.]0[.]0[.]1"),
            IOC(type=IOCType.IPV4, value="10.0.0.2", raw_match="10[.]0[.]0[.]2"),
            IOC(type=IOCType.IPV4, value="10.0.0.3", raw_match="10[.]0[.]0[.]3"),
            IOC(type=IOCType.IPV4, value="10.0.0.4", raw_match="10[.]0[.]0[.]4"),
        ]
        assert "len" in ioc_payloads._group_history_iocs.__code__.co_names
        assert "raw_count == 4" in Path("app/routes/ioc_payloads.py").read_text(encoding="utf-8")
        assert "first.type == second.type == third.type" in Path(
            "app/routes/ioc_payloads.py"
        ).read_text(encoding="utf-8")

    def test_history_ioc_row_append_owns_rebuild_and_group_mutation(self):
        """Persisted IOC row rebuild and grouped append should live in one helper."""
        from app.routes import ioc_payloads

        grouped: dict[IOCType, list[IOC]] = {}
        row = {"type": "ipv4", "value": "10.0.0.1", "raw_match": "10[.]0[.]0[.]1"}

        ioc_payloads._append_history_ioc_row(grouped, row)

        assert grouped == {
            IOCType.IPV4: [
                IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10[.]0[.]0[.]1")
            ]
        }

    def test_group_history_iocs_delegates_rebuild_group_append(self):
        """Long history grouping should share the row append helper after short paths rebuild once."""
        from app.routes import ioc_payloads

        source = inspect.getsource(ioc_payloads._group_history_iocs)

        assert "first = _ioc_from_history_row(raw_iocs[0])" in source
        assert "append_ioc_by_type(grouped, first)" in source
        assert "_append_history_ioc_row(grouped, data)" in source

    def test_empty_history_skips_ioc_grouping(self, client, monkeypatch):
        """Empty history reloads should not rebuild/group unused IOC template data."""
        from app.routes import ioc_payloads

        mock_store = MagicMock()
        mock_store.load_analysis.return_value = {
            "id": "empty-analysis",
            "input_text": "no indicators here",
            "mode": "online",
            "iocs": [],
            "results": [],
            "total_count": 0,
            "top_verdict": "unknown",
            "created_at": "2026-01-01T00:00:00",
        }
        client.application.history_store = mock_store

        def fail_group_history_iocs(_raw_iocs):
            raise AssertionError("empty history reload should skip IOC grouping")

        monkeypatch.setattr(ioc_payloads, "_group_history_iocs", fail_group_history_iocs)

        response = client.get("/history/empty-analysis")

        assert response.status_code == 200
        assert b"No IOCs found" in response.data

    def test_empty_history_results_skip_json_dumps(self):
        """Empty history replay payloads should not invoke the JSON encoder."""
        import app.routes.history_replay as history_replay
        from app.json_utils import EMPTY_JSON_ARRAY

        with patch("app.json_utils.json.dumps", side_effect=AssertionError):
            assert history_replay.history_results_json([]) == EMPTY_JSON_ARRAY
        assert EMPTY_JSON_ARRAY == "[]"

    def test_nonempty_history_results_use_json_dumps(self):
        """Non-empty history replay payloads still use the JSON encoder."""
        import app.routes.history_replay as history_replay

        results = [{"ioc_value": "10.0.0.1", "verdict": "clean"}]

        with patch("app.json_utils.json.dumps", return_value="encoded") as dumps:
            assert history_replay.history_results_json(results) == "encoded"

        dumps.assert_called_once_with(results)

    def test_history_route_delegates_replay_context_helpers(self):
        """History detail should leave replay template shape outside the route body."""
        import app.routes.history as history_module
        import app.routes.analysis_modes as analysis_modes
        import app.routes.history_replay as history_replay

        mock_store = MagicMock()
        record = {
            "iocs": [{"type": "ipv4", "value": "10.0.0.1", "raw_match": "10[.]0[.]0[.]1"}],
            "results": [{"ioc_value": "10.0.0.1", "verdict": "clean"}],
            "total_count": 1,
        }
        mock_store.load_analysis.side_effect = [record, None, record, None]
        context = history_replay.history_replay_context(record)
        loaded_context = history_replay.load_history_replay_context(mock_store, "analysis-1")
        missing_context = history_replay.load_history_replay_context(mock_store, "missing")
        found_result = history_replay.history_detail_result(mock_store, "analysis-1")
        missing_result = history_replay.history_detail_result(mock_store, "missing")
        source = inspect.getsource(history_module.history_detail)
        result_helper_source = inspect.getsource(history_replay.history_detail_result)
        route_helper_source = inspect.getsource(history_replay.history_detail_route_response)

        assert loaded_context == context
        assert missing_context is None
        import app.routes.template_results as template_results

        assert found_result == template_results.TemplateResult("results.html", context, 200)
        assert missing_result == template_results.TemplateResult(None, None, 404)
        assert found_result.found is True
        assert missing_result.found is False
        assert [args for args, _kwargs in mock_store.load_analysis.call_args_list] == [
            ("analysis-1",),
            ("missing",),
            ("analysis-1",),
            ("missing",),
        ]
        assert context["mode"] == "online"
        assert context["mode"] == analysis_modes.ANALYSIS_MODE_ONLINE
        assert '"online"' not in inspect.getsource(history_replay.history_replay_context)
        assert context["job_id"] == "history"
        assert context["enrichable_count"] == 1
        assert context["provider_counts"] == "{}"
        assert context["provider_coverage"] == {"registered": 0, "configured": 0, "needs_key": 0}
        assert context["results_owner"] == "history"
        assert "history_detail_route_response(" in source
        assert "current_app.history_store" in source
        assert "abort_request=abort" in source
        assert "render_template=render_template" in source
        assert "history_detail_result(" not in source
        assert "apply_template_result(" not in source
        assert "abort(result.status)" not in source
        assert "render_template(result.template_name" not in source
        assert "load_analysis" not in source
        assert "load_history_replay_context(" not in source
        assert "load_history_replay_context(history_store, analysis_id)" in result_helper_source
        assert "TemplateResult(None, None, 404)" in result_helper_source
        assert "apply_template_result(" in route_helper_source
        assert "history_detail_result(history_store, analysis_id)" in route_helper_source
        assert "abort_request=abort_request" in route_helper_source
        assert "render_template=render_template" in route_helper_source
        assert not hasattr(history_replay, "HistoryDetailResult")
        assert "**history_replay_context(" not in source
        assert "_history_ioc_template_context" not in source
        assert "provider_coverage" not in source
        assert "history_results" not in source
        assert "results.html" not in source

    def test_template_result_helper_owns_abort_or_render_application(self):
        """Template result abort/render application should be shared across routes."""
        import app.routes.template_results as template_results

        calls: list[tuple[str, object]] = []

        def abort_request(status: int):
            calls.append(("abort", status))
            raise RuntimeError(f"abort {status}")

        def render_template(template_name: str | None, **context):
            calls.append(("render", (template_name, context)))
            return ("rendered", template_name, context)

        rendered = template_results.apply_template_result(
            template_results.TemplateResult("results.html", {"mode": "online"}, 200),
            abort_request=abort_request,
            render_template=render_template,
        )

        with pytest.raises(RuntimeError, match="abort 404"):
            template_results.apply_template_result(
                template_results.TemplateResult(None, None, 404),
                abort_request=abort_request,
                render_template=render_template,
            )

        helper_source = inspect.getsource(template_results.apply_template_result)
        assert rendered == (("rendered", "results.html", {"mode": "online"}), 200)
        assert calls == [
            ("render", ("results.html", {"mode": "online"})),
            ("abort", 404),
        ]
        assert "if not result.found:" in helper_source
        assert "abort_request is None" in helper_source
        assert "abort_request(result.status)" in helper_source
        assert "render_template(result.template_name" in helper_source
        assert "), result.status" in helper_source


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
        assert b"Saved Online Enrichment History" in response.data
        assert (
            b"Successful, partial, and failed Online enrichment attempts can be saved here."
            in response.data
        )
        assert b"Offline extractions are not saved." in response.data
        assert b"abc123deadbeef" in response.data  # link contains analysis id

    def test_history_list_empty(self, client):
        """GET /history shows empty-state message with no history."""
        mock_store = MagicMock()
        mock_store.list_recent.return_value = []
        client.application.history_store = mock_store
        response = client.get("/history")
        assert response.status_code == 200
        assert b"No saved Online enrichment attempts yet." in response.data
        assert b"Offline extractions are not saved." in response.data

    def test_history_list_shows_verdict_badge(self, client, seeded_store):
        """GET /history shows verdict badge for each analysis."""
        store, _, _, _ = seeded_store
        client.application.history_store = store
        response = client.get("/history")
        assert response.status_code == 200
        assert b"malicious" in response.data

    def test_history_list_error_propagates(self, client):
        """GET /history propagates when history_store.list_recent raises."""
        mock_store = MagicMock()
        mock_store.list_recent.side_effect = Exception("DB corrupt")
        client.application.history_store = mock_store
        with pytest.raises(Exception, match="DB corrupt"):
            client.get("/history")

    def test_history_list_delegates_template_context_helper(self):
        """History list template shape and query limit should live outside the route body."""
        import app.routes.history as history_module
        import app.routes.history_replay as history_replay

        mock_store = MagicMock()
        analyses = [{"id": "analysis-1", "top_verdict": "clean"}]
        mock_store.list_recent.return_value = analyses

        context = history_replay.history_list_context(mock_store)
        result = history_replay.history_list_result(mock_store)
        route_source = inspect.getsource(history_module.history_list)
        helper_source = inspect.getsource(history_replay.history_list_context)
        result_source = inspect.getsource(history_replay.history_list_result)
        route_helper_source = inspect.getsource(history_replay.history_list_route_response)

        assert context == {"analyses": analyses}
        assert result.template_name == "history.html"
        assert result.context == {"analyses": analyses}
        assert result.status == 200
        assert mock_store.list_recent.call_args_list == [
            call(limit=history_replay.HISTORY_LIST_LIMIT),
            call(limit=history_replay.HISTORY_LIST_LIMIT),
        ]
        assert history_replay.HISTORY_LIST_LIMIT == 50
        assert "history_list_route_response(" in route_source
        assert "current_app.history_store" in route_source
        assert "render_template=render_template" in route_source
        assert "history_list_result(" not in route_source
        assert "apply_template_result(" not in route_source
        assert "list_recent" not in route_source
        assert "limit=50" not in route_source
        assert "analyses=" not in route_source
        assert "list_recent(limit=limit)" in helper_source
        assert "TemplateResult(\"history.html\"" in result_source
        assert "apply_template_result(" in route_helper_source
        assert "history_list_result(history_store)" in route_helper_source
        assert "render_template=render_template" in route_helper_source

    def test_index_shows_compact_recent_analyses(self, client, seeded_store):
        """GET / shows a compact recent analyses rail when history exists."""
        store, _, _, _ = seeded_store
        client.application.history_store = store
        response = client.get("/")
        assert response.status_code == 200
        assert b"Recent Analyses" in response.data
        assert b"recent-analyses-rail" in response.data
        assert b"recent-analysis-row" in response.data
        assert b"/history/abc123deadbeef" in response.data


# ---------------------------------------------------------------------------
# IOC serialization helper test
# ---------------------------------------------------------------------------


class TestSerializeIoc:
    """Tests for _serialize_ioc helper."""

    def test_serialize_ioc(self):
        """_serialize_ioc returns a dict with type, value, raw_match."""
        from app.routes.ioc_payloads import _serialize_ioc

        ioc = IOC(type=IOCType.DOMAIN, value="example.com", raw_match="example[.]com")
        result = _serialize_ioc(ioc)
        assert result == {
            "type": "domain",
            "value": "example.com",
            "raw_match": "example[.]com",
        }

    def test_serialize_iocs_uses_shared_helper_and_small_list_fast_paths(self, monkeypatch):
        """Batch IOC serialization should share the per-IOC serializer path."""
        import app.routes.ioc_payloads as ioc_payloads

        calls = []

        def serialize_ioc(ioc):
            calls.append(ioc.value)
            return {"value": ioc.value}

        monkeypatch.setattr(ioc_payloads, "_serialize_ioc", serialize_ioc)

        ioc_a = IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10[.]0[.]0[.]1")
        ioc_b = IOC(type=IOCType.DOMAIN, value="example.com", raw_match="example[.]com")
        ioc_c = IOC(type=IOCType.URL, value="http://evil.example", raw_match="hxxp://evil[.]example")
        ioc_d = IOC(type=IOCType.EMAIL, value="analyst@example.com", raw_match="analyst@example[.]com")

        class NoIterIocs(list):
            def __iter__(self):
                raise AssertionError("short IOC serialization should not iterate")

        assert ioc_payloads._serialize_iocs([]) == []
        assert ioc_payloads._serialize_iocs(NoIterIocs([ioc_a])) == [{"value": "10.0.0.1"}]
        assert ioc_payloads._serialize_iocs(NoIterIocs([ioc_a, ioc_b])) == [
            {"value": "10.0.0.1"},
            {"value": "example.com"},
        ]
        assert ioc_payloads._serialize_iocs(NoIterIocs([ioc_a, ioc_b, ioc_c])) == [
            {"value": "10.0.0.1"},
            {"value": "example.com"},
            {"value": "http://evil.example"},
        ]
        assert ioc_payloads._serialize_iocs(NoIterIocs([ioc_a, ioc_b, ioc_c, ioc_d])) == [
            {"value": "10.0.0.1"},
            {"value": "example.com"},
            {"value": "http://evil.example"},
            {"value": "analyst@example.com"},
        ]
        assert calls == [
            "10.0.0.1",
            "10.0.0.1",
            "example.com",
            "10.0.0.1",
            "example.com",
            "http://evil.example",
            "10.0.0.1",
            "example.com",
            "http://evil.example",
            "analyst@example.com",
        ]
        assert "len" in ioc_payloads._serialize_iocs.__code__.co_names
        assert "_append_serialized_ioc" in ioc_payloads._serialize_iocs.__code__.co_names

    def test_serialize_iocs_delegates_long_path_append(self):
        """Long history IOC serialization should share one append helper."""
        import app.routes.ioc_payloads as ioc_payloads

        ioc = IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10[.]0[.]0[.]1")
        serialized: list[dict] = []

        ioc_payloads._append_serialized_ioc(serialized, ioc)
        source = inspect.getsource(ioc_payloads._serialize_iocs)

        assert serialized == [ioc_payloads._serialize_ioc(ioc)]
        assert "_append_serialized_ioc(serialized, ioc)" in source
        assert "serialized.append(_serialize_ioc(ioc))" not in source
