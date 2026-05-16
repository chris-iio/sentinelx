"""SQLite enrichment result cache.

Caches enrichment results per (ioc_value, ioc_type, provider) with
configurable TTL. Thread-safe via threading.Lock on write operations.

Usage:
    cache = CacheStore()
    cache.put("1.2.3.4", "ipv4", "VirusTotal", {"verdict": "malicious", ...})
    result = cache.get("1.2.3.4", "ipv4", "VirusTotal", ttl_seconds=86400)

For tests, pass a tmp_path-based db_path to isolate from the real filesystem.
"""
from __future__ import annotations

import datetime
import sqlite3
import threading
from pathlib import Path

from app.json_utils import EMPTY_JSON_OBJECT, decode_json_object, encode_json_object
from app.sqlite import configure_connection
from app.time_utils import utc_now

DEFAULT_DB_PATH = Path.home() / ".sentinelx" / "cache.db"
_EMPTY_JSON_OBJECT = EMPTY_JSON_OBJECT

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS enrichment_cache (
    ioc_value   TEXT NOT NULL,
    ioc_type    TEXT NOT NULL,
    provider    TEXT NOT NULL,
    result_json TEXT NOT NULL,
    cached_at   TEXT NOT NULL,
    PRIMARY KEY (ioc_value, ioc_type, provider)
)
"""
_CREATE_CACHED_AT_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_cache_cached_at "
    "ON enrichment_cache (cached_at)"
)
_GET_ENTRY_QUERY = (
    "SELECT result_json, cached_at FROM enrichment_cache "
    "WHERE ioc_value = ? AND ioc_type = ? AND provider = ?"
)
_PUT_ENTRY_QUERY = (
    "INSERT OR REPLACE INTO enrichment_cache "
    "(ioc_value, ioc_type, provider, result_json, cached_at) "
    "VALUES (?, ?, ?, ?, ?)"
)
_CLEAR_QUERY = "DELETE FROM enrichment_cache"
_GET_ALL_FOR_IOC_QUERY = (
    "SELECT provider, result_json, cached_at FROM enrichment_cache "
    "WHERE ioc_value = ? AND ioc_type = ?"
)
_CACHE_STATS_QUERY = "SELECT COUNT(*), MIN(cached_at) FROM enrichment_cache"
_PURGE_EXPIRED_QUERY = "DELETE FROM enrichment_cache WHERE cached_at < ?"


def _utc_now() -> datetime.datetime:
    """Return the cache clock in timezone-aware UTC."""
    return utc_now()


def _encode_result_json(result_dict: dict) -> str:
    """Serialize a cached result, skipping JSON encoder work for empty payloads."""
    return encode_json_object(result_dict)


def _decode_result_json(result_json: str) -> dict:
    """Deserialize a cached result, skipping JSON decoder work for empty payloads."""
    return decode_json_object(result_json)


def _cache_entry(result_json: str, cached_at: str, provider: str | None = None) -> dict:
    """Hydrate a cached payload and attach cache metadata."""
    entry = _decode_result_json(result_json)
    if provider is not None:
        entry["provider"] = provider
    entry["cached_at"] = cached_at
    return entry


def _is_cache_fresh(cached_at: str, ttl_seconds: int) -> bool:
    """Return whether a cache timestamp is still inside the TTL window."""
    cached_at_dt = datetime.datetime.fromisoformat(cached_at)
    age_seconds = (_utc_now() - cached_at_dt).total_seconds()
    return age_seconds <= ttl_seconds


class CacheStore:
    """SQLite-backed enrichment result cache with TTL.

    Uses a persistent connection opened at construction time and WAL journal
    mode to allow concurrent readers without blocking writers.

    Args:
        db_path: Path to the SQLite database file.
                 Defaults to ~/.sentinelx/cache.db.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path if db_path is not None else DEFAULT_DB_PATH
        self._lock = threading.Lock()
        self._db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._conn = self._connect()
        configure_connection(self._conn)
        self._conn.execute(_CREATE_TABLE)
        self._conn.execute(_CREATE_CACHED_AT_INDEX)
        self._conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._db_path), check_same_thread=False)

    def get(
        self,
        ioc_value: str,
        ioc_type: str,
        provider: str,
        ttl_seconds: int,
    ) -> dict | None:
        """Retrieve a cached result if it exists and is within TTL.

        Returns the result dict with an added 'cached_at' key, or None
        if not found or expired.
        """
        if ttl_seconds <= 0:
            return None

        with self._lock:
            row = self._conn.execute(
                _GET_ENTRY_QUERY,
                (ioc_value, ioc_type, provider),
            ).fetchone()

        if row is None:
            return None

        result_json, cached_at_str = row
        if not _is_cache_fresh(cached_at_str, ttl_seconds):
            return None

        return _cache_entry(result_json, cached_at_str)

    def put(
        self,
        ioc_value: str,
        ioc_type: str,
        provider: str,
        result_dict: dict,
    ) -> None:
        """Store or update a cached enrichment result."""
        now = _utc_now().isoformat()
        result_json = _encode_result_json(result_dict)
        with self._lock:
            self._conn.execute(
                _PUT_ENTRY_QUERY,
                (ioc_value, ioc_type, provider, result_json, now),
            )
            self._conn.commit()

    def clear(self) -> None:
        """Remove all cached entries."""
        with self._lock:
            self._conn.execute(_CLEAR_QUERY)
            self._conn.commit()

    def get_all_for_ioc(self, ioc_value: str, ioc_type: str) -> list[dict]:
        """Return all cached results for one IOC across all providers.

        No TTL check — the detail page shows all historical data.

        Returns:
            List of dicts, each with provider, cached_at, and all result fields.
        """
        with self._lock:
            rows = self._conn.execute(
                _GET_ALL_FOR_IOC_QUERY,
                (ioc_value, ioc_type),
            ).fetchall()

        row_count = len(rows)
        if row_count == 0:
            return []
        if row_count == 1:
            provider, result_json, cached_at = rows[0]
            return [_cache_entry(result_json, cached_at, provider)]
        if row_count == 2:
            first_provider, first_json, first_cached_at = rows[0]
            second_provider, second_json, second_cached_at = rows[1]
            return [
                _cache_entry(first_json, first_cached_at, first_provider),
                _cache_entry(second_json, second_cached_at, second_provider),
            ]

        results: list[dict] = []
        for provider, result_json, cached_at in rows:
            results.append(_cache_entry(result_json, cached_at, provider))

        return results

    def stats(self) -> dict:
        """Return cache statistics.

        Returns:
            Dict with 'total_entries' (int) and 'oldest' (ISO string or None).
        """
        with self._lock:
            count, oldest = self._conn.execute(_CACHE_STATS_QUERY).fetchone()

        return {"total_entries": count, "oldest": oldest}

    def purge_expired(self, ttl_seconds: int) -> int:
        """Delete cache entries older than ttl_seconds.

        Args:
            ttl_seconds: Maximum age in seconds. Entries older than this
                         are deleted.

        Returns:
            Number of rows deleted.
        """
        cutoff = (_utc_now() - datetime.timedelta(seconds=ttl_seconds)).isoformat()
        with self._lock:
            cursor = self._conn.execute(
                _PURGE_EXPIRED_QUERY,
                (cutoff,),
            )
            self._conn.commit()
            return cursor.rowcount
