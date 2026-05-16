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
from types import MappingProxyType
from unittest.mock import MagicMock, patch

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
    from app.routes._helpers import _reset_history_save_diagnostics

    _reset_history_save_diagnostics()
    yield
    _reset_history_save_diagnostics()


# ---------------------------------------------------------------------------
# _run_enrichment_and_save wrapper tests
# ---------------------------------------------------------------------------


class TestEnrichmentSaveWrapper:
    """Tests for _run_enrichment_and_save integration."""

    def test_save_called_after_enrichment(self):
        """The wrapper calls enrich_all then saves to HistoryStore."""
        from app.routes._helpers import (
            _run_enrichment_and_save,
            get_history_save_diagnostics,
        )

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
        from app.routes._helpers import _run_enrichment_and_save

        ioc_a = IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10[.]0[.]0[.]1")
        ioc_b = IOC(type=IOCType.DOMAIN, value="example.com", raw_match="example[.]com")
        ioc_c = IOC(type=IOCType.URL, value="http://evil.example", raw_match="hxxp://evil[.]example")
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
        assert [item["provider"] for item in save_kwargs["results"]] == ["ProviderA"]

    def test_save_failure_does_not_break_enrichment(self):
        """If HistoryStore.save_analysis raises, enrichment still completes."""
        from app.routes._helpers import (
            _run_enrichment_and_save,
            get_history_save_diagnostics,
        )

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
        from app.routes._helpers import (
            _run_enrichment_and_save,
            get_history_save_diagnostics,
        )

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
        from app.routes import _helpers

        source = inspect.getsource(_helpers._coerce_history_save_diagnostics)
        assert "dict(_HISTORY_SAVE_DIAGNOSTICS_DEFAULTS)" not in source
        assert '("attempts", "successes", "failures", "skipped")' not in source
        assert '("last_attempt_at", "last_success_at", "last_failure_at")' not in source
        accessor_source = inspect.getsource(_helpers.get_history_save_diagnostics)
        assert "dict(_history_save_diagnostics)" not in accessor_source
        assert isinstance(_helpers._HISTORY_SAVE_OUTCOMES, frozenset)
        assert isinstance(_helpers._HISTORY_SAVE_RECORDABLE_OUTCOMES, frozenset)
        assert isinstance(_helpers._HISTORY_SAVE_DIAGNOSTICS_DEFAULTS, MappingProxyType)

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
        from app.routes import _helpers

        class NoStripText(str):
            def strip(self, *_args, **_kwargs):
                raise AssertionError("timestamp presence should scan directly")

        raw = {
            "last_attempt_at": NoStripText("2026-01-01T00:00:00Z"),
            "last_success_at": NoStripText("   "),
            "last_failure_at": NoStripText("2026-01-01T00:00:01Z"),
        }

        diagnostics = _helpers._coerce_history_save_diagnostics(raw)

        assert diagnostics["last_attempt_at"] == "2026-01-01T00:00:00Z"
        assert diagnostics["last_success_at"] is None
        assert diagnostics["last_failure_at"] == "2026-01-01T00:00:01Z"

    def test_history_save_diagnostics_error_summary_avoids_strip_allocation(self):
        """Error summaries should trim through the shared bounded index helper."""
        from app.routes import _helpers

        class MeasuredStripText(str):
            def strip(self, *_args, **_kwargs):
                raise AssertionError("history error summaries should not allocate through strip()")

        diagnostics = _helpers._coerce_history_save_diagnostics({
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
        import app.routes.history as history_module

        store, analysis_id, _, results = seeded_store
        client.application.history_store = store
        response = client.get(f"/history/{analysis_id}")
        html = response.get_data(as_text=True)

        assert response.status_code == 200
        assert 'data-job-id="history"' in html
        assert 'data-mode="online"' in html
        assert 'data-results-owner="history"' in html
        assert f'data-provider-counts="{history_module._EMPTY_JSON_OBJECT}"' in html
        assert 'id="export-btn"' in html
        assert 'id="enrich-progress"' in html
        assert f"0/{len(results)} providers complete" in html
        assert 'data-results-owner="live"' not in html
        assert history_module._EMPTY_JSON_OBJECT == "{}"

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
        import app.routes.history as history_module

        store, analysis_id, _, _ = seeded_store
        client.application.history_store = store

        def fail_group_by_type(_iocs):
            raise AssertionError("history reload should group persisted IOCs in one pass")

        monkeypatch.setattr(history_module, "group_by_type", fail_group_by_type, raising=False)

        response = client.get(f"/history/{analysis_id}")

        assert response.status_code == 200
        assert b"10.0.0.1" in response.data
        assert b"evil.com" in response.data
        assert "setdefault" not in history_module._group_history_iocs.__code__.co_names

    def test_group_history_iocs_skips_iteration_for_empty_single_pair_or_three_rows(self):
        """Short history IOC groups should avoid the accumulator loop."""
        import app.routes.history as history_module

        class NoIterList(list):
            def __iter__(self):
                raise AssertionError("short history IOC grouping should not iterate")

            def __getitem__(self, index):
                if isinstance(index, slice):
                    raise AssertionError("history IOC grouping should not slice")
                return super().__getitem__(index)

        assert history_module._group_history_iocs(NoIterList()) == {}

        grouped = history_module._group_history_iocs(
            NoIterList([{"type": "ipv4", "value": "10.0.0.1", "raw_match": "10[.]0[.]0[.]1"}])
        )

        assert list(grouped) == [IOCType.IPV4]
        assert grouped[IOCType.IPV4] == [
            IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10[.]0[.]0[.]1")
        ]
        same_type_grouped = history_module._group_history_iocs(
            NoIterList([
                {"type": "ipv4", "value": "10.0.0.1", "raw_match": "10[.]0[.]0[.]1"},
                {"type": "ipv4", "value": "10.0.0.2", "raw_match": "10[.]0[.]0[.]2"},
            ])
        )
        mixed_type_grouped = history_module._group_history_iocs(
            NoIterList([
                {"type": "ipv4", "value": "10.0.0.1", "raw_match": "10[.]0[.]0[.]1"},
                {"type": "domain", "value": "evil.com", "raw_match": "evil[.]com"},
            ])
        )
        three_grouped = history_module._group_history_iocs(
            NoIterList([
                {"type": "ipv4", "value": "10.0.0.1", "raw_match": "10[.]0[.]0[.]1"},
                {"type": "domain", "value": "evil.com", "raw_match": "evil[.]com"},
                {"type": "ipv4", "value": "10.0.0.2", "raw_match": "10[.]0[.]0[.]2"},
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
        assert "len" in history_module._group_history_iocs.__code__.co_names

    def test_empty_history_skips_ioc_grouping(self, client, monkeypatch):
        """Empty history reloads should not rebuild/group unused IOC template data."""
        import app.routes.history as history_module

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

        monkeypatch.setattr(history_module, "_group_history_iocs", fail_group_history_iocs)

        response = client.get("/history/empty-analysis")

        assert response.status_code == 200
        assert b"No IOCs found" in response.data

    def test_empty_history_results_skip_json_dumps(self):
        """Empty history replay payloads should not invoke the JSON encoder."""
        import app.routes.history as history_module

        with patch("app.json_utils.json.dumps", side_effect=AssertionError):
            assert history_module._history_results_json([]) == history_module._EMPTY_JSON_ARRAY
        assert history_module._EMPTY_JSON_ARRAY == "[]"

    def test_nonempty_history_results_use_json_dumps(self):
        """Non-empty history replay payloads still use the JSON encoder."""
        import app.routes.history as history_module

        results = [{"ioc_value": "10.0.0.1", "verdict": "clean"}]

        with patch("app.json_utils.json.dumps", return_value="encoded") as dumps:
            assert history_module._history_results_json(results) == "encoded"

        dumps.assert_called_once_with(results)


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

    def test_history_list_error_propagates(self, client):
        """GET /history propagates when history_store.list_recent raises."""
        mock_store = MagicMock()
        mock_store.list_recent.side_effect = Exception("DB corrupt")
        client.application.history_store = mock_store
        with pytest.raises(Exception, match="DB corrupt"):
            client.get("/history")

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
        from app.routes._helpers import _serialize_ioc

        ioc = IOC(type=IOCType.DOMAIN, value="example.com", raw_match="example[.]com")
        result = _serialize_ioc(ioc)
        assert result == {
            "type": "domain",
            "value": "example.com",
            "raw_match": "example[.]com",
        }

    def test_serialize_iocs_uses_shared_helper_and_small_list_fast_paths(self, monkeypatch):
        """Batch IOC serialization should share the per-IOC serializer path."""
        import app.routes._helpers as helpers

        calls = []

        def serialize_ioc(ioc):
            calls.append(ioc.value)
            return {"value": ioc.value}

        monkeypatch.setattr(helpers, "_serialize_ioc", serialize_ioc)

        ioc_a = IOC(type=IOCType.IPV4, value="10.0.0.1", raw_match="10[.]0[.]0[.]1")
        ioc_b = IOC(type=IOCType.DOMAIN, value="example.com", raw_match="example[.]com")
        ioc_c = IOC(type=IOCType.URL, value="http://evil.example", raw_match="hxxp://evil[.]example")

        class NoIterIocs(list):
            def __iter__(self):
                raise AssertionError("short IOC serialization should not iterate")

        assert helpers._serialize_iocs([]) == []
        assert helpers._serialize_iocs(NoIterIocs([ioc_a])) == [{"value": "10.0.0.1"}]
        assert helpers._serialize_iocs(NoIterIocs([ioc_a, ioc_b])) == [
            {"value": "10.0.0.1"},
            {"value": "example.com"},
        ]
        assert helpers._serialize_iocs(NoIterIocs([ioc_a, ioc_b, ioc_c])) == [
            {"value": "10.0.0.1"},
            {"value": "example.com"},
            {"value": "http://evil.example"},
        ]
        assert calls == [
            "10.0.0.1",
            "10.0.0.1",
            "example.com",
            "10.0.0.1",
            "example.com",
            "http://evil.example",
        ]
        assert "len" in helpers._serialize_iocs.__code__.co_names
