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

    Args:
        db_path: Path to the SQLite database file.
                 Defaults to ~/.sentinelx/cache.db.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path if db_path is not None else DEFAULT_DB_PATH
        self._lock = threading.Lock()
        self._db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        conn = self._connect()
        conn.execute(_CREATE_TABLE)
        conn.commit()
        conn.close()

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
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT result_json, cached_at FROM enrichment_cache "
                "WHERE ioc_value = ? AND ioc_type = ? AND provider = ?",
                (ioc_value, ioc_type, provider),
            ).fetchone()
        finally:
            conn.close()

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
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO enrichment_cache "
                    "(ioc_value, ioc_type, provider, result_json, cached_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (ioc_value, ioc_type, provider, result_json, now),
                )
                conn.commit()
            finally:
                conn.close()

    def clear(self) -> None:
        """Remove all cached entries."""
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM enrichment_cache")
                conn.commit()
            finally:
                conn.close()

    def stats(self) -> dict:
        """Return cache statistics.

        Returns:
            Dict with 'total_entries' (int) and 'oldest' (ISO string or None).
        """
        conn = self._connect()
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM enrichment_cache"
            ).fetchone()[0]
            oldest_row = conn.execute(
                "SELECT MIN(cached_at) FROM enrichment_cache"
            ).fetchone()
        finally:
            conn.close()

        oldest = oldest_row[0] if oldest_row else None
        return {"total_entries": count, "oldest": oldest}
