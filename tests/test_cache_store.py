"""Tests for SQLite enrichment result cache.

Covers put/get, TTL expiry, clear, stats, thread safety, upsert,
and no-error-caching contract.
"""
from __future__ import annotations

import threading
from pathlib import Path

import pytest

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


class TestTTL:
    def test_expired_entry_returns_none(self, cache: CacheStore) -> None:
        """get() returns None for entries older than TTL."""
        cache.put("1.2.3.4", "ipv4", "VT", {"verdict": "clean"})
        # TTL of 0 seconds means it's already expired
        result = cache.get("1.2.3.4", "ipv4", "VT", ttl_seconds=0)
        assert result is None

    def test_fresh_entry_returns_data(self, cache: CacheStore) -> None:
        """get() returns data for entries within TTL."""
        cache.put("1.2.3.4", "ipv4", "VT", {"verdict": "clean"})
        result = cache.get("1.2.3.4", "ipv4", "VT", ttl_seconds=86400)
        assert result is not None


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
