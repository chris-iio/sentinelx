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
import json
import sqlite3
import threading
from pathlib import Path

DEFAULT_DB_PATH = Path.home() / ".sentinelx" / "cache.db"

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
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")  # safe with WAL; avoids fsync per commit
        self._conn.execute("PRAGMA busy_timeout=5000")    # retry on lock instead of instant error
        self._conn.execute("PRAGMA cache_size=-8000")     # 8MB page cache
        self._conn.execute("PRAGMA temp_store=MEMORY")
        self._conn.execute(_CREATE_TABLE)
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cache_cached_at "
            "ON enrichment_cache (cached_at)"
        )
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
        with self._lock:
            row = self._conn.execute(
                "SELECT result_json, cached_at FROM enrichment_cache "
                "WHERE ioc_value = ? AND ioc_type = ? AND provider = ?",
                (ioc_value, ioc_type, provider),
            ).fetchone()

        if row is None:
            return None

        result_json, cached_at_str = row
        cached_at = datetime.datetime.fromisoformat(cached_at_str)
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        age_seconds = (now - cached_at).total_seconds()

        if age_seconds > ttl_seconds:
            return None

        result: dict = json.loads(result_json)
        result["cached_at"] = cached_at_str
        return result

    def put(
        self,
        ioc_value: str,
        ioc_type: str,
        provider: str,
        result_dict: dict,
    ) -> None:
        """Store or update a cached enrichment result."""
        now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
        result_json = json.dumps(result_dict)
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO enrichment_cache "
                "(ioc_value, ioc_type, provider, result_json, cached_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (ioc_value, ioc_type, provider, result_json, now),
            )
            self._conn.commit()

    def clear(self) -> None:
        """Remove all cached entries."""
        with self._lock:
            self._conn.execute("DELETE FROM enrichment_cache")
            self._conn.commit()

    def get_all_for_ioc(self, ioc_value: str, ioc_type: str) -> list[dict]:
        """Return all cached results for one IOC across all providers.

        No TTL check — the detail page shows all historical data.

        Returns:
            List of dicts, each with provider, cached_at, and all result fields.
        """
        with self._lock:
            rows = self._conn.execute(
                "SELECT provider, result_json, cached_at FROM enrichment_cache "
                "WHERE ioc_value = ? AND ioc_type = ?",
                (ioc_value, ioc_type),
            ).fetchall()

        results: list[dict] = []
        for provider, result_json, cached_at in rows:
            entry: dict = json.loads(result_json)
            entry["provider"] = provider
            entry["cached_at"] = cached_at
            results.append(entry)

        return results

    def stats(self) -> dict:
        """Return cache statistics.

        Returns:
            Dict with 'total_entries' (int) and 'oldest' (ISO string or None).
        """
        with self._lock:
            count = self._conn.execute(
                "SELECT COUNT(*) FROM enrichment_cache"
            ).fetchone()[0]
            oldest_row = self._conn.execute(
                "SELECT MIN(cached_at) FROM enrichment_cache"
            ).fetchone()

        oldest = oldest_row[0] if oldest_row else None
        return {"total_entries": count, "oldest": oldest}

    def purge_expired(self, ttl_seconds: int) -> int:
        """Delete cache entries older than ttl_seconds.

        Args:
            ttl_seconds: Maximum age in seconds. Entries older than this
                         are deleted.

        Returns:
            Number of rows deleted.
        """
        cutoff = (
            datetime.datetime.now(tz=datetime.timezone.utc)
            - datetime.timedelta(seconds=ttl_seconds)
        ).isoformat()
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM enrichment_cache WHERE cached_at < ?",
                (cutoff,),
            )
            self._conn.commit()
            return cursor.rowcount
