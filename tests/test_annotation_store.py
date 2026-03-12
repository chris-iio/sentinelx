"""Tests for AnnotationStore — persistent notes and tags per IOC.

Covers CRUD, upsert, deduplication, defaults, bulk read,
and survival across CacheStore.clear() calls.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.annotations.store import AnnotationStore
from app.cache.store import CacheStore


@pytest.fixture()
def store(tmp_path: Path) -> AnnotationStore:
    return AnnotationStore(db_path=tmp_path / "annotations.db")


class TestInit:
    def test_init_creates_db_file(self, tmp_path: Path) -> None:
        """AnnotationStore creates annotations.db on disk."""
        db_path = tmp_path / "annotations.db"
        AnnotationStore(db_path=db_path)
        assert db_path.exists()

    def test_init_creates_table(self, store: AnnotationStore) -> None:
        """ioc_annotations table is created on init."""
        import sqlite3
        with sqlite3.connect(str(store._db_path)) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='ioc_annotations'"
            ).fetchall()
        assert len(rows) == 1


class TestNotesRoundTrip:
    def test_notes_round_trip(self, store: AnnotationStore) -> None:
        """set_notes then get returns the stored note."""
        store.set_notes("1.2.3.4", "ipv4", "test note")
        result = store.get("1.2.3.4", "ipv4")
        assert result["notes"] == "test note"
        assert result["tags"] == []

    def test_upsert_notes(self, store: AnnotationStore) -> None:
        """Calling set_notes twice updates the existing row, not inserts a second."""
        store.set_notes("1.2.3.4", "ipv4", "first note")
        store.set_notes("1.2.3.4", "ipv4", "second note")
        result = store.get("1.2.3.4", "ipv4")
        assert result["notes"] == "second note"

        import sqlite3
        with sqlite3.connect(str(store._db_path)) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM ioc_annotations WHERE ioc_value=? AND ioc_type=?",
                ("1.2.3.4", "ipv4"),
            ).fetchone()[0]
        assert count == 1


class TestTagsRoundTrip:
    def test_tags_round_trip(self, store: AnnotationStore) -> None:
        """set_tags then get returns the stored tags."""
        store.set_tags("1.2.3.4", "ipv4", ["apt29", "c2"])
        result = store.get("1.2.3.4", "ipv4")
        assert result["notes"] == ""
        assert sorted(result["tags"]) == ["apt29", "c2"]

    def test_no_duplicate_tags(self, store: AnnotationStore) -> None:
        """Duplicate tags are deduplicated before storage."""
        store.set_tags("1.2.3.4", "ipv4", ["apt29", "apt29"])
        result = store.get("1.2.3.4", "ipv4")
        assert result["tags"] == ["apt29"]

    def test_upsert_tags(self, store: AnnotationStore) -> None:
        """Calling set_tags twice updates the existing row, not inserts a second."""
        store.set_tags("1.2.3.4", "ipv4", ["apt29"])
        store.set_tags("1.2.3.4", "ipv4", ["c2"])
        result = store.get("1.2.3.4", "ipv4")
        assert result["tags"] == ["c2"]

        import sqlite3
        with sqlite3.connect(str(store._db_path)) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM ioc_annotations WHERE ioc_value=? AND ioc_type=?",
                ("1.2.3.4", "ipv4"),
            ).fetchone()[0]
        assert count == 1


class TestMissingReturnsDefaults:
    def test_get_missing_returns_defaults(self, store: AnnotationStore) -> None:
        """get() for a non-existent IOC returns empty defaults."""
        result = store.get("9.9.9.9", "ipv4")
        assert result == {"notes": "", "tags": []}


class TestDelete:
    def test_delete_removes_row(self, store: AnnotationStore) -> None:
        """delete() removes the annotation; get returns defaults afterwards."""
        store.set_notes("1.2.3.4", "ipv4", "to be deleted")
        store.delete("1.2.3.4", "ipv4")
        result = store.get("1.2.3.4", "ipv4")
        assert result == {"notes": "", "tags": []}

    def test_delete_nonexistent_is_noop(self, store: AnnotationStore) -> None:
        """delete() on a non-existent IOC does not raise."""
        store.delete("9.9.9.9", "ipv4")  # should not raise
        result = store.get("9.9.9.9", "ipv4")
        assert result == {"notes": "", "tags": []}


class TestNotesAndTagsTogether:
    def test_notes_and_tags_independent(self, store: AnnotationStore) -> None:
        """set_notes and set_tags each preserve the other field via upsert."""
        store.set_notes("1.2.3.4", "ipv4", "my note")
        store.set_tags("1.2.3.4", "ipv4", ["apt29"])
        result = store.get("1.2.3.4", "ipv4")
        assert result["notes"] == "my note"
        assert result["tags"] == ["apt29"]


class TestSurvivesCacheClear:
    def test_notes_survive_cache_clear(self, tmp_path: Path) -> None:
        """Notes survive CacheStore.clear() — annotations use a separate DB file."""
        annotation_store = AnnotationStore(db_path=tmp_path / "annotations.db")
        cache_store = CacheStore(db_path=tmp_path / "cache.db")

        # Put data in both
        annotation_store.set_notes("1.2.3.4", "ipv4", "important note")
        cache_store.put("1.2.3.4", "ipv4", "VT", {"verdict": "malicious"})

        # Clear cache — should not affect annotations
        cache_store.clear()

        result = annotation_store.get("1.2.3.4", "ipv4")
        assert result["notes"] == "important note"
        assert cache_store.get("1.2.3.4", "ipv4", "VT", ttl_seconds=3600) is None


class TestGetAllForIocValues:
    def test_get_all_for_ioc_values_returns_dict(self, store: AnnotationStore) -> None:
        """get_all_for_ioc_values returns a dict keyed by 'value|type'."""
        store.set_notes("1.2.3.4", "ipv4", "note1")
        store.set_tags("evil.com", "domain", ["c2"])
        result = store.get_all_for_ioc_values([
            ("1.2.3.4", "ipv4"),
            ("evil.com", "domain"),
            ("9.9.9.9", "ipv4"),  # not in DB
        ])
        assert "1.2.3.4|ipv4" in result
        assert result["1.2.3.4|ipv4"]["notes"] == "note1"
        assert "evil.com|domain" in result
        assert result["evil.com|domain"]["tags"] == ["c2"]
        # Missing IOC should still have a default entry
        assert "9.9.9.9|ipv4" in result
        assert result["9.9.9.9|ipv4"] == {"notes": "", "tags": []}

    def test_get_all_for_ioc_values_empty_input(self, store: AnnotationStore) -> None:
        """get_all_for_ioc_values with empty list returns empty dict."""
        result = store.get_all_for_ioc_values([])
        assert result == {}
