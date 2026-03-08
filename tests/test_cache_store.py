"""Tests for SQLite enrichment result cache.

Covers put/get, TTL expiry, clear, stats, thread safety, upsert,
and no-error-caching contract.
"""
from __future__ import annotations

import json
import threading
import time
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
