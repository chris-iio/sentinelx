"""Tests for SQLite analysis history store.

Covers save/load roundtrip, list_recent ordering and limit, missing ID
returns None, top_verdict computation, IOC serialization fidelity, and
concurrent write safety.
"""
from __future__ import annotations

import datetime
import inspect
import threading
import time
from unittest.mock import patch
from pathlib import Path
from types import MappingProxyType

import pytest

import app.enrichment.history_store as history_store_module
import app.enrichment.history_records as history_records_module
from app.enrichment.history_records import (
    _FALLBACK_VERDICT,
    _MAX_VERDICT,
    _VERDICT_PRIORITY,
    _analysis_insert_record,
    _compute_top_verdict,
)
from app.enrichment.history_store import DEFAULT_MAX_ROWS, HistoryStore


# -- Fixtures ---------------------------------------------------------------

@pytest.fixture()
def store(tmp_path: Path) -> HistoryStore:
    return HistoryStore(db_path=tmp_path / "history.db")


# -- Helpers ----------------------------------------------------------------

_SAMPLE_IOCS = [
    {"type": "ipv4", "value": "1.2.3.4", "raw_match": "1[.]2[.]3[.]4"},
    {"type": "domain", "value": "evil.com", "raw_match": "evil[.]com"},
]

_SAMPLE_RESULTS = [
    {
        "type": "result",
        "ioc_value": "1.2.3.4",
        "ioc_type": "ipv4",
        "provider": "VirusTotal",
        "verdict": "malicious",
        "detection_count": 12,
        "total_engines": 90,
        "scan_date": "2025-01-01T00:00:00",
        "raw_stats": {"malicious": 12, "undetected": 78},
    },
    {
        "type": "result",
        "ioc_value": "evil.com",
        "ioc_type": "domain",
        "provider": "VirusTotal",
        "verdict": "clean",
        "detection_count": 0,
        "total_engines": 90,
        "scan_date": "2025-01-01T00:00:00",
        "raw_stats": {"malicious": 0, "undetected": 90},
    },
]


# -- Test classes -----------------------------------------------------------

class TestPublicExports:
    """History store public facade tests."""

    def test_history_store_public_exports_exclude_record_private_helpers(self) -> None:
        assert history_store_module.__all__ == ("DEFAULT_MAX_ROWS", "HistoryStore")
        assert "_analysis_insert_record" not in history_store_module.__all__
        assert "_compute_top_verdict" not in history_store_module.__all__
        assert "_EMPTY_JSON_ARRAY" not in history_store_module.__all__
        assert "_VERDICT_PRIORITY" not in history_store_module.__all__
        assert not hasattr(history_store_module, "_EMPTY_JSON_ARRAY")
        assert not hasattr(history_store_module, "_FALLBACK_VERDICT")
        assert not hasattr(history_store_module, "_MAX_VERDICT")
        assert not hasattr(history_store_module, "_VERDICT_PRIORITY")
        assert not hasattr(history_store_module, "_compute_top_verdict")
        assert not hasattr(history_store_module, "_encode_json_array")
        assert not hasattr(history_store_module, "_decode_json_array")


class TestSaveAndLoad:
    """Roundtrip save → load tests."""

    def test_roundtrip(self, store: HistoryStore) -> None:
        """save_analysis() then load_analysis() returns full stored data."""
        row_id = store.save_analysis(
            "1.2.3.4 evil.com", "online", _SAMPLE_IOCS, _SAMPLE_RESULTS,
        )
        loaded = store.load_analysis(row_id)
        assert loaded is not None
        assert loaded["id"] == row_id
        assert loaded["input_text"] == "1.2.3.4 evil.com"
        assert loaded["mode"] == "online"
        assert loaded["total_count"] == 2
        assert loaded["iocs"] == _SAMPLE_IOCS
        assert loaded["results"] == _SAMPLE_RESULTS

    def test_workflow_metadata_roundtrip_is_separate_from_provider_results(
        self, store: HistoryStore
    ) -> None:
        provider_result = {"type": "result", "verdict": "suspicious", "provider": "ProviderA"}
        workflow = {
            "type": "workflow",
            "status": "failed",
            "complete": False,
            "terminal": True,
            "terminal_reason": "partial_failure",
            "error": "one lookup failed",
            "done": 2,
            "total": 2,
        }

        row_id = store.save_analysis(
            "test",
            "online",
            [],
            [provider_result, workflow],
        )
        loaded = store.load_analysis(row_id)

        assert loaded is not None
        assert loaded["results"] == [provider_result]
        assert loaded["workflow"] == workflow
        assert loaded["top_verdict"] == "suspicious"

    def test_load_returns_none_for_missing_id(self, store: HistoryStore) -> None:
        """load_analysis() returns None when the ID does not exist."""
        assert store.load_analysis("nonexistent") is None

    def test_save_returns_unique_ids(self, store: HistoryStore) -> None:
        """Each call to save_analysis() returns a distinct id."""
        id1 = store.save_analysis("a", "online", [], [])
        id2 = store.save_analysis("b", "online", [], [])
        assert id1 != id2

    def test_created_at_is_populated(self, store: HistoryStore) -> None:
        """Saved analysis includes a valid created_at ISO timestamp."""
        row_id = store.save_analysis("test", "online", [], [])
        loaded = store.load_analysis(row_id)
        assert loaded is not None
        assert "created_at" in loaded
        assert isinstance(loaded["created_at"], str)
        assert "T" in loaded["created_at"]  # basic ISO format check

    def test_history_clock_is_shared_for_created_at(self) -> None:
        """History timestamps should use one UTC clock helper."""
        now = history_store_module._utc_now()

        assert now.tzinfo is datetime.timezone.utc
        assert "utc_now" in history_store_module._utc_now.__code__.co_names
        assert "_utc_now" in HistoryStore.save_analysis.__code__.co_names

    def test_empty_payloads_skip_json_encoding(self, store: HistoryStore) -> None:
        """Empty IOC/result payloads should use the JSON literal without encoder work."""
        with patch("app.json_utils.json.dumps") as dumps:
            dumps.side_effect = AssertionError("empty history payloads should skip json.dumps")
            row_id = store.save_analysis("empty", "online", [], [])

        loaded = store.load_analysis(row_id)

        assert loaded is not None
        assert loaded["iocs"] == []
        assert loaded["results"] == []

    def test_empty_payloads_skip_json_decoding(self, store: HistoryStore) -> None:
        """Empty IOC/result payloads should load from the JSON literal without decoder work."""
        row_id = store.save_analysis("empty", "online", [], [])

        with patch("app.json_utils.json.loads") as loads:
            loads.side_effect = AssertionError("empty history payloads should skip json.loads")
            loaded = store.load_analysis(row_id)

        assert loaded is not None
        assert loaded["iocs"] == []
        assert loaded["results"] == []

    def test_empty_payloads_use_shared_json_literal_constant(self) -> None:
        """Empty history payload paths should share one literal constant."""
        from app.json_utils import EMPTY_JSON_ARRAY

        source = Path("app/enrichment/history_records.py").read_text(encoding="utf-8")

        assert EMPTY_JSON_ARRAY == "[]"
        assert "_EMPTY_JSON_ARRAY" not in source
        assert "encode_json_array" in source
        assert "decode_json_array" in source
        assert '== "[]"' not in source
        assert '= "[]" if' not in source

    def test_payload_encoding_and_decoding_share_empty_fast_path(self) -> None:
        """History payload helpers should centralize empty JSON fast paths."""
        from app.json_utils import EMPTY_JSON_ARRAY

        assert history_records_module._encode_json_array([]) == EMPTY_JSON_ARRAY
        assert history_records_module._decode_json_array(EMPTY_JSON_ARRAY) == []
        assert "_analysis_insert_record" in HistoryStore.save_analysis.__code__.co_names
        assert "_analysis_from_row" in HistoryStore.load_analysis.__code__.co_names
        assert "_decode_json_array" in history_records_module._analysis_from_row.__code__.co_names

    def test_save_analysis_delegates_insert_record_shaping(self) -> None:
        """HistoryStore should keep payload/count/verdict shaping in history_records."""
        record = _analysis_insert_record(
            row_id="analysis-1",
            input_text="1.2.3.4",
            mode="online",
            iocs=[{"type": "ipv4", "value": "1.2.3.4"}],
            results=[{"verdict": "clean"}],
            created_at="2026-01-02T03:04:05+00:00",
        )

        assert record.row_id == "analysis-1"
        assert record.values == (
            "analysis-1",
            "1.2.3.4",
            "online",
            '[{"type": "ipv4", "value": "1.2.3.4"}]',
            '[{"verdict": "clean"}]',
            1,
            "clean",
            "2026-01-02T03:04:05+00:00",
        )
        assert "_analysis_insert_record" in HistoryStore.save_analysis.__code__.co_names
        assert "_encode_json_array" not in HistoryStore.save_analysis.__code__.co_names
        assert "_compute_top_verdict" not in HistoryStore.save_analysis.__code__.co_names
        assert not hasattr(record, "__dict__")

    def test_sql_statements_are_shared_constants(self) -> None:
        """History SQL statements should be module constants, not method-local strings."""
        assert "_CREATE_CREATED_AT_INDEX" in HistoryStore.__init__.__code__.co_names
        assert "_INSERT_ANALYSIS_QUERY" in HistoryStore.save_analysis.__code__.co_names
        assert "_LIST_RECENT_QUERY" in HistoryStore.list_recent.__code__.co_names
        assert "_LOAD_ANALYSIS_QUERY" in HistoryStore.load_analysis.__code__.co_names


class TestListRecent:
    """list_recent() ordering and limit tests."""

    def test_returns_most_recent_first(self, store: HistoryStore) -> None:
        """list_recent() returns entries ordered by created_at DESC."""
        id1 = store.save_analysis("first", "online", [], [])
        time.sleep(0.01)  # ensure distinct timestamps
        id2 = store.save_analysis("second", "online", [], [])
        time.sleep(0.01)
        id3 = store.save_analysis("third", "online", [], [])

        recent = store.list_recent()
        assert len(recent) == 3
        assert recent[0]["id"] == id3
        assert recent[1]["id"] == id2
        assert recent[2]["id"] == id1

    def test_respects_limit(self, store: HistoryStore) -> None:
        """list_recent(limit=N) returns at most N entries."""
        for i in range(5):
            store.save_analysis(f"analysis {i}", "online", [], [])
        recent = store.list_recent(limit=3)
        assert len(recent) == 3

    def test_returns_empty_list_when_no_entries(self, store: HistoryStore) -> None:
        """list_recent() returns an empty list on fresh DB."""
        assert store.list_recent() == []

    def test_list_recent_empty_single_pair_and_three_paths_use_row_count(
        self, store: HistoryStore
    ) -> None:
        """Short recent-history reads should return before accumulator looping."""
        assert store.list_recent() == []

        row_id = store.save_analysis("single", "online", [], [])
        recent = store.list_recent()

        assert recent == [
            {
                "id": row_id,
                "input_text": "single",
                "mode": "online",
                "total_count": 0,
                "top_verdict": "error",
                "created_at": recent[0]["created_at"],
            }
        ]

        class NoIterRows(list):
            def __iter__(self):
                raise AssertionError("pair recent-history rows should not iterate")

        class FakeCursor:
            def fetchall(self):
                return NoIterRows([
                    ("new", "second", "online", 2, "clean", "2026-01-02T00:00:00Z"),
                    ("old", "first", "offline", 1, "error", "2026-01-01T00:00:00Z"),
                ])

        class FakeConn:
            def execute(self, *_args, **_kwargs):
                return FakeCursor()

        store._conn = FakeConn()  # type: ignore[assignment]
        pair_recent = store.list_recent()

        assert [entry["id"] for entry in pair_recent] == ["new", "old"]
        assert [entry["input_text"] for entry in pair_recent] == ["second", "first"]

        class ThreeCursor:
            def fetchall(self):
                return NoIterRows([
                    ("newest", "third", "online", 3, "malicious", "2026-01-03T00:00:00Z"),
                    ("middle", "second", "online", 2, "clean", "2026-01-02T00:00:00Z"),
                    ("oldest", "first", "offline", 1, "error", "2026-01-01T00:00:00Z"),
                ])

        class ThreeConn:
            def execute(self, *_args, **_kwargs):
                return ThreeCursor()

        store._conn = ThreeConn()  # type: ignore[assignment]
        three_recent = store.list_recent()

        assert [entry["id"] for entry in three_recent] == ["newest", "middle", "oldest"]
        assert [entry["input_text"] for entry in three_recent] == ["third", "second", "first"]

        class FourCursor:
            def fetchall(self):
                return NoIterRows([
                    ("newest", "fourth", "online", 4, "malicious", "2026-01-04T00:00:00Z"),
                    ("newer", "third", "online", 3, "suspicious", "2026-01-03T00:00:00Z"),
                    ("middle", "second", "online", 2, "clean", "2026-01-02T00:00:00Z"),
                    ("oldest", "first", "offline", 1, "error", "2026-01-01T00:00:00Z"),
                ])

        class FourConn:
            def execute(self, *_args, **_kwargs):
                return FourCursor()

        store._conn = FourConn()  # type: ignore[assignment]
        four_recent = store.list_recent()

        assert [entry["id"] for entry in four_recent] == ["newest", "newer", "middle", "oldest"]
        assert [entry["input_text"] for entry in four_recent] == ["fourth", "third", "second", "first"]
        assert "len" in HistoryStore.list_recent.__code__.co_names
        assert "_summary_from_row" in HistoryStore.list_recent.__code__.co_names
        assert "row_count == 4" in inspect.getsource(HistoryStore.list_recent)

    def test_truncates_input_text(self, store: HistoryStore) -> None:
        """list_recent() truncates input_text to 120 characters."""
        long_text = "x" * 200
        row_id = store.save_analysis(long_text, "online", [], [])
        recent = store.list_recent()
        assert len(recent[0]["input_text"]) == 120
        loaded = store.load_analysis(row_id)
        assert loaded is not None
        assert loaded["input_text"] == long_text

    def test_summary_fields_present(self, store: HistoryStore) -> None:
        """list_recent() entries have the expected summary keys."""
        store.save_analysis(
            "1.2.3.4", "online", _SAMPLE_IOCS, _SAMPLE_RESULTS,
        )
        entry = store.list_recent()[0]
        expected_keys = {"id", "input_text", "mode", "total_count", "top_verdict", "created_at"}
        assert set(entry.keys()) == expected_keys

    def test_list_recent_accumulates_summaries_without_list_comprehension(self) -> None:
        """list_recent() should not allocate a list-comprehension frame for rows."""
        assert "<listcomp>" not in HistoryStore.list_recent.__code__.co_consts
        assert "_append_history_summary" in HistoryStore.list_recent.__code__.co_names


class TestRetention:
    """Bounded history retention tests."""

    def test_default_retention_limit_is_precomputed(self) -> None:
        assert DEFAULT_MAX_ROWS == 500
        assert HistoryStore.__init__.__kwdefaults__ == {"max_rows": DEFAULT_MAX_ROWS}

    def test_save_prunes_oldest_rows_after_limit(self, tmp_path: Path) -> None:
        store = HistoryStore(db_path=tmp_path / "history.db", max_rows=3)

        for index in range(5):
            store.save_analysis(
                f"analysis {index}",
                "online",
                [],
                [],
                analysis_id=f"analysis-{index}",
            )
            time.sleep(0.01)

        recent = store.list_recent(limit=10)

        assert [row["id"] for row in recent] == ["analysis-4", "analysis-3", "analysis-2"]
        assert store.load_analysis("analysis-0") is None
        assert store.load_analysis("analysis-1") is None
        assert store.load_analysis("analysis-2") is not None

    def test_invalid_retention_limit_is_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="history max_rows must be a positive integer"):
            HistoryStore(db_path=tmp_path / "history.db", max_rows=0)


class TestTopVerdict:
    """top_verdict computation at save time."""

    def test_malicious_wins_over_clean(self, store: HistoryStore) -> None:
        """When mixed verdicts, most severe ('malicious') wins."""
        row_id = store.save_analysis(
            "test", "online", _SAMPLE_IOCS, _SAMPLE_RESULTS,
        )
        loaded = store.load_analysis(row_id)
        assert loaded is not None
        assert loaded["top_verdict"] == "malicious"

    def test_all_clean_results(self, store: HistoryStore) -> None:
        """When all verdicts are 'clean', top_verdict is 'clean'."""
        results = [
            {"type": "result", "verdict": "clean"},
            {"type": "result", "verdict": "clean"},
        ]
        row_id = store.save_analysis("test", "online", [], results)
        loaded = store.load_analysis(row_id)
        assert loaded is not None
        assert loaded["top_verdict"] == "clean"

    def test_error_only_results(self, store: HistoryStore) -> None:
        """When all results are errors (no verdict), top_verdict is 'error'."""
        results = [
            {"type": "error", "error": "timeout"},
            {"type": "error", "error": "auth fail"},
        ]
        row_id = store.save_analysis("test", "online", [], results)
        loaded = store.load_analysis(row_id)
        assert loaded is not None
        assert loaded["top_verdict"] == "error"

    def test_clean_over_no_data(self, store: HistoryStore) -> None:
        """A clean provider result has more weight than absent data."""
        results = [
            {"type": "result", "verdict": "clean"},
            {"type": "result", "verdict": "no_data"},
        ]
        row_id = store.save_analysis("test", "online", [], results)
        loaded = store.load_analysis(row_id)
        assert loaded is not None
        assert loaded["top_verdict"] == "clean"

    def test_known_good_does_not_erase_malicious_conflict(self, store: HistoryStore) -> None:
        results = [
            {"type": "result", "verdict": "known_good"},
            {"type": "result", "verdict": "malicious"},
        ]

        row_id = store.save_analysis("test", "online", [], results)
        loaded = store.load_analysis(row_id)

        assert loaded is not None
        assert loaded["top_verdict"] == "malicious"

    def test_empty_results(self, store: HistoryStore) -> None:
        """Empty results list produces 'error' verdict."""
        row_id = store.save_analysis("test", "online", [], [])
        loaded = store.load_analysis(row_id)
        assert loaded is not None
        assert loaded["top_verdict"] == "error"


class TestComputeTopVerdictUnit:
    """Direct tests for _compute_top_verdict helper."""

    def test_priority_order(self) -> None:
        """Verdicts follow malicious > suspicious > no_data > clean."""
        assert _compute_top_verdict([{"verdict": "clean"}, {"verdict": "suspicious"}]) == "suspicious"
        assert _compute_top_verdict([{"verdict": "no_data"}, {"verdict": "malicious"}]) == "malicious"

    def test_malicious_verdict_short_circuits_scan(self) -> None:
        """Once malicious is found, later result rows do not need inspection."""
        class ExplodingRow(dict):
            def get(self, key, default=None):
                raise AssertionError("top verdict scan should stop after malicious")

        assert _compute_top_verdict(
            [{"verdict": "clean"}, {"verdict": "malicious"}, ExplodingRow()]
        ) == "malicious"

    def test_error_entries_ignored(self) -> None:
        """Entries without 'verdict' key are skipped."""
        assert _compute_top_verdict([{"type": "error"}, {"verdict": "clean"}]) == "clean"

    def test_priority_map_is_precomputed(self) -> None:
        """Top-verdict computation reuses the module-level priority map."""
        assert isinstance(_VERDICT_PRIORITY, MappingProxyType)
        assert _VERDICT_PRIORITY == {
            "error": 0,
            "no_data": 1,
            "clean": 2,
            "known_good": 3,
            "suspicious": 4,
            "malicious": 5,
        }
        assert _compute_top_verdict([{"verdict": "clean"}, {"verdict": "suspicious"}]) == "suspicious"

    def test_top_verdict_terminal_constants_are_precomputed(self) -> None:
        """Maximum and fallback verdict strings should live in module constants."""
        source_names = _compute_top_verdict.__code__.co_names

        assert _MAX_VERDICT == "malicious"
        assert _FALLBACK_VERDICT == "error"
        assert "_MAX_VERDICT" in source_names
        assert "_FALLBACK_VERDICT" in source_names
        assert _compute_top_verdict([{"verdict": "malicious"}]) == _MAX_VERDICT
        assert _compute_top_verdict([]) == _FALLBACK_VERDICT

    def test_summary_precedence_is_stable_for_conflicts(self) -> None:
        """Saved verdicts use the same conflict precedence as live verdicts."""
        assert _compute_top_verdict([]) == "error"
        assert _compute_top_verdict([{"verdict": "known_good"}]) == "known_good"
        assert _compute_top_verdict(
            [{"verdict": "known_good"}, {"verdict": "suspicious"}]
        ) == "suspicious"
        assert _compute_top_verdict(
            [{"verdict": "known_good"}, {"verdict": "malicious"}]
        ) == "malicious"
        assert _compute_top_verdict(
            [{"verdict": "no_data"}, {"verdict": "clean"}]
        ) == "clean"


class TestIOCSerialization:
    """IOC serialization / deserialization fidelity tests."""

    def test_complex_iocs_survive_roundtrip(self, store: HistoryStore) -> None:
        """IOCs with special chars and all types survive JSON roundtrip."""
        iocs = [
            {"type": "ipv4", "value": "192.168.1.1", "raw_match": "192[.]168[.]1[.]1"},
            {"type": "url", "value": "https://evil.com/path?q=1&r=2", "raw_match": "hxxps://evil[.]com/path?q=1&r=2"},
            {"type": "sha256", "value": "a" * 64, "raw_match": "a" * 64},
            {"type": "email", "value": "user@evil.com", "raw_match": "user[@]evil[.]com"},
        ]
        row_id = store.save_analysis("test", "online", iocs, [])
        loaded = store.load_analysis(row_id)
        assert loaded is not None
        assert loaded["iocs"] == iocs

    def test_results_with_nested_dicts_survive_roundtrip(self, store: HistoryStore) -> None:
        """Results with nested raw_stats dicts survive JSON roundtrip."""
        results = [
            {
                "type": "result",
                "ioc_value": "1.2.3.4",
                "ioc_type": "ipv4",
                "provider": "VirusTotal",
                "verdict": "malicious",
                "detection_count": 5,
                "total_engines": 90,
                "scan_date": "2025-01-01T00:00:00",
                "raw_stats": {"malicious": 5, "suspicious": 2, "undetected": 83},
            },
        ]
        row_id = store.save_analysis("test", "online", [], results)
        loaded = store.load_analysis(row_id)
        assert loaded is not None
        assert loaded["results"] == results


class TestConcurrency:
    """Thread-safety for concurrent writes."""

    def test_concurrent_writes(self, store: HistoryStore) -> None:
        """Concurrent save_analysis() from multiple threads do not corrupt data."""
        errors: list[Exception] = []

        def writer(i: int) -> None:
            try:
                for j in range(10):
                    store.save_analysis(
                        f"analysis {i}-{j}",
                        "online",
                        [{"type": "ipv4", "value": f"10.0.{i}.{j}", "raw_match": f"10.0.{i}.{j}"}],
                        [{"type": "result", "verdict": "clean"}],
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Concurrent writes produced errors: {errors}"
        recent = store.list_recent(limit=100)
        assert len(recent) == 50  # 5 threads × 10 writes


class TestDBCreation:
    """Database auto-creation and WAL mode."""

    def test_creates_db_directory(self, tmp_path: Path) -> None:
        """HistoryStore creates parent directories if they don't exist."""
        db_path = tmp_path / "deep" / "nested" / "history.db"
        store = HistoryStore(db_path=db_path)
        assert db_path.parent.exists()
        # Verify it works by saving
        row_id = store.save_analysis("test", "online", [], [])
        assert store.load_analysis(row_id) is not None

    def test_uses_wal_mode_and_busy_timeout(self, store: HistoryStore) -> None:
        """HistoryStore keeps WAL mode and busy_timeout enabled on the live connection."""
        journal_mode = store._conn.execute("PRAGMA journal_mode").fetchone()[0]
        busy_timeout = store._conn.execute("PRAGMA busy_timeout").fetchone()[0]

        assert str(journal_mode).lower() == "wal"
        assert busy_timeout == 5000
