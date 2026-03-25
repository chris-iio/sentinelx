"""Tests for SQLite analysis history store.

Covers save/load roundtrip, list_recent ordering and limit, missing ID
returns None, top_verdict computation, IOC serialization fidelity, and
concurrent write safety.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from app.enrichment.history_store import HistoryStore, _compute_top_verdict


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

    def test_truncates_input_text(self, store: HistoryStore) -> None:
        """list_recent() truncates input_text to 120 characters."""
        long_text = "x" * 200
        store.save_analysis(long_text, "online", [], [])
        recent = store.list_recent()
        assert len(recent[0]["input_text"]) == 120

    def test_summary_fields_present(self, store: HistoryStore) -> None:
        """list_recent() entries have the expected summary keys."""
        store.save_analysis(
            "1.2.3.4", "online", _SAMPLE_IOCS, _SAMPLE_RESULTS,
        )
        entry = store.list_recent()[0]
        expected_keys = {"id", "input_text", "mode", "total_count", "top_verdict", "created_at"}
        assert set(entry.keys()) == expected_keys


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

    def test_no_data_over_clean(self, store: HistoryStore) -> None:
        """'no_data' is more severe than 'clean'."""
        results = [
            {"type": "result", "verdict": "clean"},
            {"type": "result", "verdict": "no_data"},
        ]
        row_id = store.save_analysis("test", "online", [], results)
        loaded = store.load_analysis(row_id)
        assert loaded is not None
        assert loaded["top_verdict"] == "no_data"

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

    def test_error_entries_ignored(self) -> None:
        """Entries without 'verdict' key are skipped."""
        assert _compute_top_verdict([{"type": "error"}, {"verdict": "clean"}]) == "clean"


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
