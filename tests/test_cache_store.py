"""Tests for SQLite enrichment result cache.

Covers put/get, TTL expiry, clear, stats, thread safety, upsert,
and no-error-caching contract.
"""
from __future__ import annotations

import datetime
import threading
from unittest.mock import patch
from pathlib import Path

import pytest

import app.cache.store as cache_store_module
from app.cache.store import CacheStore


@pytest.fixture()
def cache(tmp_path: Path) -> CacheStore:
    return CacheStore(db_path=tmp_path / "cache.db")


class TestPutAndGet:
    def test_roundtrip(self, cache: CacheStore) -> None:
        """put() then get() returns the stored dict."""
        data = {"verdict": "malicious", "detection_count": 5}
        cache.put("1.2.3.4", "ipv4", "VirusTotal", data)
        result = cache.get("1.2.3.4", "ipv4", "VirusTotal", ttl_seconds=3600)
        assert result is not None
        assert result["verdict"] == "malicious"
        assert result["detection_count"] == 5

    def test_get_returns_none_for_missing(self, cache: CacheStore) -> None:
        """get() returns None when no cached entry exists."""
        result = cache.get("1.2.3.4", "ipv4", "VirusTotal", ttl_seconds=3600)
        assert result is None

    def test_upsert_replaces_existing(self, cache: CacheStore) -> None:
        """put() with same key replaces the previous value."""
        cache.put("1.2.3.4", "ipv4", "VT", {"verdict": "clean"})
        cache.put("1.2.3.4", "ipv4", "VT", {"verdict": "malicious"})
        result = cache.get("1.2.3.4", "ipv4", "VT", ttl_seconds=3600)
        assert result is not None
        assert result["verdict"] == "malicious"

    def test_different_providers_separate_entries(self, cache: CacheStore) -> None:
        """Same IOC cached by different providers are independent entries."""
        cache.put("evil.com", "domain", "VT", {"verdict": "malicious"})
        cache.put("evil.com", "domain", "TF", {"verdict": "clean"})
        vt = cache.get("evil.com", "domain", "VT", ttl_seconds=3600)
        tf = cache.get("evil.com", "domain", "TF", ttl_seconds=3600)
        assert vt is not None and vt["verdict"] == "malicious"
        assert tf is not None and tf["verdict"] == "clean"

    def test_empty_payload_skips_json_encoding(self, cache: CacheStore) -> None:
        """Empty cache payloads should use the JSON literal without encoder work."""
        with patch("app.json_utils.json.dumps") as dumps:
            dumps.side_effect = AssertionError("empty cache payloads should skip json.dumps")
            cache.put("1.2.3.4", "ipv4", "EmptyProvider", {})

        result = cache.get("1.2.3.4", "ipv4", "EmptyProvider", ttl_seconds=3600)
        detail_results = cache.get_all_for_ioc("1.2.3.4", "ipv4")

        assert result is not None
        assert result == {"cached_at": result["cached_at"]}
        assert detail_results[0]["provider"] == "EmptyProvider"
        assert detail_results[0]["cached_at"] == result["cached_at"]

    def test_empty_payload_skips_json_decoding(self, cache: CacheStore) -> None:
        """Empty cache payloads should load from the JSON literal without decoder work."""
        cache.put("1.2.3.4", "ipv4", "EmptyProvider", {})

        with patch("app.json_utils.json.loads") as loads:
            loads.side_effect = AssertionError("empty cache payloads should skip json.loads")
            result = cache.get("1.2.3.4", "ipv4", "EmptyProvider", ttl_seconds=3600)
            detail_results = cache.get_all_for_ioc("1.2.3.4", "ipv4")

        assert result is not None
        assert result == {"cached_at": result["cached_at"]}
        assert detail_results[0]["provider"] == "EmptyProvider"
        assert detail_results[0]["cached_at"] == result["cached_at"]

    def test_empty_payload_uses_shared_json_literal_constant(self) -> None:
        """Empty cache payload paths should share one literal constant."""
        from app.json_utils import EMPTY_JSON_OBJECT

        source = Path("app/cache/store.py").read_text(encoding="utf-8")

        assert EMPTY_JSON_OBJECT == "{}"
        assert "_EMPTY_JSON_OBJECT" not in source
        assert "encode_json_object" in source
        assert "decode_json_object" in source
        assert 'result_json == "{}"' not in source
        assert 'result_json = "{}"' not in source

    def test_payload_encoding_and_decoding_share_empty_fast_path(self) -> None:
        """Cache payload helpers should centralize empty JSON fast paths."""
        from app.json_utils import EMPTY_JSON_OBJECT

        assert cache_store_module._encode_result_json({}) == EMPTY_JSON_OBJECT
        assert cache_store_module._decode_result_json(EMPTY_JSON_OBJECT) == {}
        assert "_encode_result_json" in CacheStore.put.__code__.co_names
        assert "_cache_entry" in CacheStore.get.__code__.co_names
        assert "_cache_entry" in CacheStore.get_all_for_ioc.__code__.co_names

    def test_cache_entry_hydrates_metadata_in_one_helper(self) -> None:
        """Cache get paths should share decoded-payload metadata hydration."""
        payload = cache_store_module._encode_result_json({"verdict": "clean"})

        get_entry = cache_store_module._cache_entry(payload, "2026-05-01T00:00:00Z")
        detail_entry = cache_store_module._cache_entry(
            payload,
            "2026-05-01T00:00:00Z",
            "VirusTotal",
        )

        assert get_entry == {
            "verdict": "clean",
            "cached_at": "2026-05-01T00:00:00Z",
        }
        assert detail_entry == {
            "verdict": "clean",
            "provider": "VirusTotal",
            "cached_at": "2026-05-01T00:00:00Z",
        }


class TestTTL:
    def test_expired_entry_returns_none(self, cache: CacheStore) -> None:
        """get() returns None for entries older than TTL."""
        cache.put("1.2.3.4", "ipv4", "VT", {"verdict": "clean"})
        # TTL of 0 seconds means it's already expired
        result = cache.get("1.2.3.4", "ipv4", "VT", ttl_seconds=0)
        assert result is None

    def test_nonpositive_ttl_skips_cache_lookup(self, cache: CacheStore) -> None:
        """TTL values that cannot be fresh return before reading SQLite."""
        cache.put("1.2.3.4", "ipv4", "VT", {"verdict": "clean"})
        statements: list[str] = []
        cache._conn.set_trace_callback(statements.append)

        try:
            result = cache.get("1.2.3.4", "ipv4", "VT", ttl_seconds=0)
        finally:
            cache._conn.set_trace_callback(None)

        assert result is None
        assert [
            statement
            for statement in statements
            if statement.lstrip().upper().startswith("SELECT")
        ] == []

    def test_fresh_entry_returns_data(self, cache: CacheStore) -> None:
        """get() returns data for entries within TTL."""
        cache.put("1.2.3.4", "ipv4", "VT", {"verdict": "clean"})
        result = cache.get("1.2.3.4", "ipv4", "VT", ttl_seconds=86400)
        assert result is not None

    def test_cache_clock_is_shared_across_ttl_paths(self) -> None:
        """Cache freshness paths should use one timezone-aware clock helper."""
        now = cache_store_module._utc_now()

        assert now.tzinfo is datetime.timezone.utc
        assert "utc_now" in cache_store_module._utc_now.__code__.co_names
        assert "_is_cache_fresh" in CacheStore.get.__code__.co_names
        assert "_utc_now" in CacheStore.put.__code__.co_names
        assert "_utc_now" in CacheStore.purge_expired.__code__.co_names

    def test_cache_freshness_helper_handles_boundary(self) -> None:
        """TTL freshness should be centralized and inclusive at the boundary."""
        now = cache_store_module._utc_now()
        cached_at = (now - datetime.timedelta(seconds=60)).isoformat()

        with patch("app.cache.store._utc_now", return_value=now):
            assert cache_store_module._is_cache_fresh(cached_at, 60) is True
            assert cache_store_module._is_cache_fresh(cached_at, 59) is False


class TestClear:
    def test_clear_removes_all(self, cache: CacheStore) -> None:
        """clear() removes all entries."""
        cache.put("1.2.3.4", "ipv4", "VT", {"verdict": "clean"})
        cache.put("evil.com", "domain", "TF", {"verdict": "malicious"})
        cache.clear()
        assert cache.get("1.2.3.4", "ipv4", "VT", ttl_seconds=3600) is None
        assert cache.get("evil.com", "domain", "TF", ttl_seconds=3600) is None


class TestStats:
    def test_stats_empty(self, cache: CacheStore) -> None:
        """stats() returns 0 entries and no oldest for empty cache."""
        s = cache.stats()
        assert s["total_entries"] == 0
        assert s["oldest"] is None

    def test_stats_with_entries(self, cache: CacheStore) -> None:
        """stats() returns correct count and oldest timestamp."""
        cache.put("1.2.3.4", "ipv4", "VT", {"verdict": "clean"})
        cache.put("evil.com", "domain", "TF", {"verdict": "malicious"})
        s = cache.stats()
        assert s["total_entries"] == 2
        assert s["oldest"] is not None

    def test_stats_uses_single_aggregate_query(self, cache: CacheStore) -> None:
        """stats() reads count and oldest timestamp in one SQLite query."""
        cache.put("1.2.3.4", "ipv4", "VT", {"verdict": "clean"})
        cache.put("evil.com", "domain", "TF", {"verdict": "malicious"})
        statements: list[str] = []
        cache._conn.set_trace_callback(statements.append)

        try:
            assert cache.stats()["total_entries"] == 2
        finally:
            cache._conn.set_trace_callback(None)

        select_statements = [
            statement
            for statement in statements
            if statement.lstrip().upper().startswith("SELECT")
        ]
        assert select_statements == [cache_store_module._CACHE_STATS_QUERY]

    def test_sql_statements_are_shared_constants(self) -> None:
        """CacheStore methods should use shared SQL statement constants."""
        assert "_GET_ENTRY_QUERY" in CacheStore.get.__code__.co_names
        assert "_PUT_ENTRY_QUERY" in CacheStore.put.__code__.co_names
        assert "_CLEAR_QUERY" in CacheStore.clear.__code__.co_names
        assert "_GET_ALL_FOR_IOC_QUERY" in CacheStore.get_all_for_ioc.__code__.co_names
        assert "_CACHE_STATS_QUERY" in CacheStore.stats.__code__.co_names
        assert "_PURGE_EXPIRED_QUERY" in CacheStore.purge_expired.__code__.co_names


class TestThreadSafety:
    def test_concurrent_writes(self, cache: CacheStore) -> None:
        """Concurrent put() calls from multiple threads do not corrupt data."""
        errors: list[Exception] = []

        def writer(i: int) -> None:
            try:
                for j in range(20):
                    cache.put(f"10.0.{i}.{j}", "ipv4", "VT", {"idx": i * 100 + j})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Concurrent writes produced errors: {errors}"
        s = cache.stats()
        assert s["total_entries"] == 100


class TestSqliteConfig:
    def test_uses_wal_mode_and_busy_timeout(self, cache: CacheStore) -> None:
        """CacheStore keeps WAL mode and busy_timeout enabled on the live connection."""
        journal_mode = cache._conn.execute("PRAGMA journal_mode").fetchone()[0]
        busy_timeout = cache._conn.execute("PRAGMA busy_timeout").fetchone()[0]

        assert str(journal_mode).lower() == "wal"
        assert busy_timeout == 5000


class TestGetCachedAt:
    def test_get_returns_cached_at(self, cache: CacheStore) -> None:
        """get() result includes a 'cached_at' key with ISO timestamp."""
        cache.put("1.2.3.4", "ipv4", "VT", {"verdict": "clean"})
        result = cache.get("1.2.3.4", "ipv4", "VT", ttl_seconds=3600)
        assert result is not None
        assert "cached_at" in result
        assert isinstance(result["cached_at"], str)


class TestGetAllForIoc:
    def test_get_all_for_ioc_returns_all_providers(self, cache: CacheStore) -> None:
        """get_all_for_ioc returns results from all providers for an IOC."""
        cache.put("1.2.3.4", "ipv4", "VirusTotal", {"verdict": "malicious"})
        cache.put("1.2.3.4", "ipv4", "AbuseIPDB", {"verdict": "suspicious"})
        cache.put("1.2.3.4", "ipv4", "GreyNoise", {"verdict": "clean"})

        results = cache.get_all_for_ioc("1.2.3.4", "ipv4")
        assert len(results) == 3
        providers = {r["provider"] for r in results}
        assert providers == {"VirusTotal", "AbuseIPDB", "GreyNoise"}

    def test_get_all_for_ioc_ignores_ttl(self, cache: CacheStore) -> None:
        """get_all_for_ioc returns results even if TTL would have expired them."""
        cache.put("1.2.3.4", "ipv4", "VT", {"verdict": "clean"})
        # TTL=0 would expire via get(), but get_all_for_ioc ignores TTL
        results = cache.get_all_for_ioc("1.2.3.4", "ipv4")
        assert len(results) == 1
        assert results[0]["verdict"] == "clean"

    def test_get_all_for_ioc_empty(self, cache: CacheStore) -> None:
        """get_all_for_ioc returns empty list for non-existent IOC."""
        results = cache.get_all_for_ioc("9.9.9.9", "ipv4")
        assert results == []

    def test_get_all_for_ioc_empty_single_pair_and_three_paths_use_row_count(
        self, cache: CacheStore
    ) -> None:
        """Short detail-cache reads should return before accumulator looping."""
        assert cache.get_all_for_ioc("9.9.9.9", "ipv4") == []

        cache.put("1.2.3.4", "ipv4", "VT", {"verdict": "clean"})
        results = cache.get_all_for_ioc("1.2.3.4", "ipv4")

        assert results[0]["provider"] == "VT"

        class NoIterRows(list):
            def __iter__(self):
                raise AssertionError("short cache detail rows should not iterate")

        class FakeCursor:
            def __init__(self, rows: NoIterRows) -> None:
                self._rows = rows

            def fetchall(self):
                return self._rows

        class FakeConn:
            def __init__(self, rows: NoIterRows) -> None:
                self._rows = rows

            def execute(self, *_args, **_kwargs):
                return FakeCursor(self._rows)

        cache._conn = FakeConn(NoIterRows([
            ("VT", '{"verdict":"clean"}', "2026-01-01T00:00:00Z"),
            ("OTX", '{"verdict":"no_data"}', "2026-01-01T00:00:01Z"),
        ]))  # type: ignore[assignment]
        pair_results = cache.get_all_for_ioc("1.2.3.4", "ipv4")

        assert [result["provider"] for result in pair_results] == ["VT", "OTX"]
        assert [result["verdict"] for result in pair_results] == ["clean", "no_data"]

        cache._conn = FakeConn(NoIterRows([
            ("VT", '{"verdict":"clean"}', "2026-01-01T00:00:00Z"),
            ("OTX", '{"verdict":"no_data"}', "2026-01-01T00:00:01Z"),
            ("GN", '{"verdict":"suspicious"}', "2026-01-01T00:00:02Z"),
        ]))  # type: ignore[assignment]
        three_results = cache.get_all_for_ioc("1.2.3.4", "ipv4")

        assert [result["provider"] for result in three_results] == ["VT", "OTX", "GN"]
        assert [result["verdict"] for result in three_results] == [
            "clean",
            "no_data",
            "suspicious",
        ]

        cache._conn = FakeConn(NoIterRows([
            ("VT", '{"verdict":"clean"}', "2026-01-01T00:00:00Z"),
            ("OTX", '{"verdict":"no_data"}', "2026-01-01T00:00:01Z"),
            ("GN", '{"verdict":"suspicious"}', "2026-01-01T00:00:02Z"),
            ("SHODAN", '{"verdict":"malicious"}', "2026-01-01T00:00:03Z"),
        ]))  # type: ignore[assignment]
        four_results = cache.get_all_for_ioc("1.2.3.4", "ipv4")

        assert [result["provider"] for result in four_results] == ["VT", "OTX", "GN", "SHODAN"]
        assert [result["verdict"] for result in four_results] == [
            "clean",
            "no_data",
            "suspicious",
            "malicious",
        ]
        assert "len" in CacheStore.get_all_for_ioc.__code__.co_names
        assert "row_count == 4" in Path("app/cache/store.py").read_text(encoding="utf-8")

    def test_get_all_for_ioc_delegates_long_path_append(self) -> None:
        source = Path("app/cache/store.py").read_text(encoding="utf-8")
        get_all_source = source.split("def get_all_for_ioc", 1)[1].split(
            "\n    def stats",
            1,
        )[0]
        append_source = source.split("def _append_cache_entry", 1)[1]

        assert "_append_cache_entry(results, result_json, cached_at, provider)" in get_all_source
        assert "results.append(_cache_entry(result_json, cached_at, provider))" not in get_all_source
        assert "results.append(_cache_entry(result_json, cached_at, provider))" in append_source

    def test_get_all_for_ioc_includes_cached_at_and_provider(
        self, cache: CacheStore
    ) -> None:
        """Each dict in the returned list has 'cached_at' and 'provider' keys."""
        cache.put("1.2.3.4", "ipv4", "VT", {"verdict": "malicious"})
        results = cache.get_all_for_ioc("1.2.3.4", "ipv4")
        assert len(results) == 1
        r = results[0]
        assert "cached_at" in r
        assert "provider" in r
        assert isinstance(r["cached_at"], str)
        assert r["provider"] == "VT"


class TestPurgeExpired:
    """Tests for purge_expired() TTL-based bulk deletion."""

    def test_purge_expired_deletes_old_entries(self, cache: CacheStore) -> None:
        """purge_expired() removes entries older than ttl_seconds, keeps newer ones."""
        import datetime
        import json

        # Insert a fresh entry via the normal API
        cache.put("1.2.3.4", "ipv4", "VT", {"verdict": "clean"})

        # Insert an "old" entry by writing directly to the DB with a past timestamp
        old_ts = (
            datetime.datetime.now(tz=datetime.timezone.utc)
            - datetime.timedelta(hours=2)
        ).isoformat()
        cache._conn.execute(
            "INSERT OR REPLACE INTO enrichment_cache "
            "(ioc_value, ioc_type, provider, result_json, cached_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("evil.com", "domain", "TF", json.dumps({"verdict": "malicious"}), old_ts),
        )
        cache._conn.commit()

        deleted = cache.purge_expired(ttl_seconds=3600)  # 1-hour TTL

        assert deleted == 1
        # Old entry gone
        assert cache.get_all_for_ioc("evil.com", "domain") == []
        # Fresh entry survives
        assert cache.get("1.2.3.4", "ipv4", "VT", ttl_seconds=3600) is not None

    def test_purge_expired_empty_db(self, cache: CacheStore) -> None:
        """purge_expired() on empty DB returns 0 without error."""
        result = cache.purge_expired(ttl_seconds=3600)
        assert result == 0

    def test_purge_expired_keeps_fresh_entries(self, cache: CacheStore) -> None:
        """purge_expired() returns 0 and keeps all entries when none are expired."""
        cache.put("1.2.3.4", "ipv4", "VT", {"verdict": "clean"})
        cache.put("evil.com", "domain", "TF", {"verdict": "malicious"})

        deleted = cache.purge_expired(ttl_seconds=86400)  # 24-hour TTL

        assert deleted == 0
        assert cache.stats()["total_entries"] == 2
