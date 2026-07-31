"""Local SQLite store for scoped IOC review decisions.

Review data can contain verbatim IOC values and analyst reasons. Keep the
database local by default. Do not send these values or reasons to an external
model without explicit redaction and analyst consent.

For tests, pass a tmp_path-based db_path to isolate the database.
"""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.sqlite import configure_connection, prepare_private_path
from app.time_utils import utc_iso

DEFAULT_DB_PATH = Path.home() / ".sentinelx" / "review.db"
LEGACY_SCOPE = "legacy"

DISPOSITIONS = ("unreviewed", "confirmed", "false_positive", "acknowledged")

__all__ = (
    "DEFAULT_DB_PATH",
    "DISPOSITIONS",
    "LEGACY_SCOPE",
    "ReviewStore",
    "normalize_key",
)

_CREATE_REVIEWS_TABLE = """
CREATE TABLE IF NOT EXISTS ioc_reviews (
    scope       TEXT NOT NULL,
    ioc_type    TEXT NOT NULL,
    value       TEXT NOT NULL,
    disposition TEXT NOT NULL DEFAULT 'unreviewed',
    reason      TEXT NOT NULL DEFAULT '',
    note        TEXT NOT NULL DEFAULT '',
    author      TEXT NOT NULL DEFAULT '',
    source      TEXT NOT NULL DEFAULT '',
    expires_at  TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    PRIMARY KEY (scope, ioc_type, value)
)
"""

def normalize_key(scope: str, ioc_type: str, value: str) -> tuple[str, str, str]:
    """Return the scoped canonical key for one indicator."""
    return scope.strip(), ioc_type.strip(), value.strip()


def _normalize_timestamp(value: str | None) -> str | None:
    """Return a UTC timestamp, or raise ValueError for an invalid value."""
    if value is None or not value.strip():
        return None
    text = value.strip()
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return utc_iso(parsed)


class ReviewStore:
    """SQLite-backed local analyst review store.

    All decision APIs require a scope. This prevents a false-positive decision
    from one workspace or investigation from affecting another.

    Stored IOC values and reasons are verbatim sensitive data. Do not send them
    to an external model without explicit redaction and analyst consent.

    Args:
        db_path: Database path. Defaults to ~/.sentinelx/review.db.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path if db_path is not None else DEFAULT_DB_PATH
        self._lock = threading.Lock()
        prepare_private_path(self._db_path)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        configure_connection(self._conn)
        self._migrate_legacy_schema()
        self._conn.execute(_CREATE_REVIEWS_TABLE)
        self._conn.commit()

    def _migrate_legacy_schema(self) -> None:
        """Move the old unscoped schema into the reserved legacy scope."""
        columns = self._conn.execute("PRAGMA table_info(ioc_reviews)").fetchall()
        if not columns:
            return
        primary_key = [
            row["name"]
            for row in sorted(columns, key=lambda row: row["pk"])
            if row["pk"]
        ]
        if primary_key != ["ioc_type", "value"] or any(
            row["name"] == "scope" for row in columns
        ):
            return
        with self._conn:
            self._conn.execute("ALTER TABLE ioc_reviews RENAME TO ioc_reviews_legacy")
            self._conn.execute(_CREATE_REVIEWS_TABLE)
            self._conn.execute(
                """
                INSERT INTO ioc_reviews (
                    scope, ioc_type, value, disposition, reason, note,
                    author, source, expires_at, created_at, updated_at
                )
                SELECT ?, ioc_type, value, disposition, reason, note,
                       '', 'legacy_migration', NULL, created_at, updated_at
                FROM ioc_reviews_legacy
                """,
                (LEGACY_SCOPE,),
            )
            self._conn.execute("DROP TABLE ioc_reviews_legacy")

    # ------------------------------------------------------------------
    # Writes

    def set_disposition(
        self,
        scope: str,
        ioc_type: str,
        value: str,
        disposition: str,
        *,
        reason: str = "",
        note: str = "",
        author: str = "",
        source: str = "",
        expires_at: str | None = None,
    ) -> bool:
        """Record one scoped analyst disposition.

        A false positive requires a reason. ``author`` and ``source`` record
        simple provenance. ``expires_at`` makes a decision inactive at that
        time.

        IOC values and reasons remain local. Do not send them to an external
        model without explicit redaction and analyst consent.

        Returns False for invalid input.
        """
        if disposition not in DISPOSITIONS:
            return False
        key = normalize_key(scope, ioc_type, value)
        if not all(key):
            return False
        reason = reason.strip()
        note = note.strip()
        author = author.strip()
        source = source.strip()
        if disposition == "false_positive" and not reason:
            return False
        try:
            normalized_expiry = _normalize_timestamp(expires_at)
        except ValueError:
            return False
        if disposition == "unreviewed":
            reason, note = "", ""
            normalized_expiry = None
        now = utc_iso()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO ioc_reviews (
                    scope, ioc_type, value, disposition, reason, note,
                    author, source, expires_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (scope, ioc_type, value) DO UPDATE SET
                    disposition = excluded.disposition,
                    reason      = excluded.reason,
                    note        = excluded.note,
                    author      = excluded.author,
                    source      = excluded.source,
                    expires_at  = excluded.expires_at,
                    updated_at  = excluded.updated_at
                """,
                (
                    *key,
                    disposition,
                    reason,
                    note,
                    author,
                    source,
                    normalized_expiry,
                    now,
                    now,
                ),
            )
            self._conn.commit()
        return True

    # ------------------------------------------------------------------
    # Reads

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        return {
            "scope": row["scope"],
            "ioc_type": row["ioc_type"],
            "value": row["value"],
            "disposition": row["disposition"],
            "reason": row["reason"],
            "note": row["note"],
            "author": row["author"],
            "source": row["source"],
            "expires_at": row["expires_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def get(self, scope: str, ioc_type: str, value: str) -> dict | None:
        """Return one active scoped review record, or None."""
        key = normalize_key(scope, ioc_type, value)
        if not all(key):
            return None
        cursor = self._conn.execute(
            "SELECT * FROM ioc_reviews "
            "WHERE scope = ? AND ioc_type = ? AND value = ? "
            "AND (expires_at IS NULL OR expires_at > ?)",
            (*key, utc_iso()),
        )
        row = cursor.fetchone()
        return self._row_to_dict(row) if row is not None else None

    def get_many(
        self, scope: str, pairs: list[tuple[str, str]]
    ) -> dict[tuple[str, str], dict]:
        """Return active records for IOC pairs in one required scope."""
        normalized_scope = scope.strip()
        if not normalized_scope:
            return {}
        records: dict[tuple[str, str], dict] = {}
        for ioc_type, value in pairs:
            key = normalize_key(normalized_scope, ioc_type, value)
            record = self.get(*key)
            if record is not None:
                records[(key[1], key[2])] = record
        return records

    def list_all(self, scope: str, *, limit: int = 500) -> list[dict]:
        """Return active records in one required scope, newest first."""
        normalized_scope = scope.strip()
        if not normalized_scope:
            return []
        cursor = self._conn.execute(
            "SELECT * FROM ioc_reviews WHERE scope = ? "
            "AND (expires_at IS NULL OR expires_at > ?) "
            "ORDER BY updated_at DESC LIMIT ?",
            (normalized_scope, utc_iso(), limit),
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def list_by_disposition(
        self, scope: str, disposition: str, *, limit: int = 200
    ) -> list[dict]:
        """Return active records for one scope and disposition."""
        normalized_scope = scope.strip()
        if not normalized_scope or disposition not in DISPOSITIONS:
            return []
        cursor = self._conn.execute(
            "SELECT * FROM ioc_reviews WHERE scope = ? AND disposition = ? "
            "AND (expires_at IS NULL OR expires_at > ?) "
            "ORDER BY updated_at DESC LIMIT ?",
            (normalized_scope, disposition, utc_iso(), limit),
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def counts(self, scope: str) -> dict:
        """Return active per-disposition counts for one required scope."""
        result = {disposition: 0 for disposition in DISPOSITIONS}
        normalized_scope = scope.strip()
        if not normalized_scope:
            return {**result, "total": 0}
        cursor = self._conn.execute(
            "SELECT disposition, COUNT(*) AS n FROM ioc_reviews "
            "WHERE scope = ? AND (expires_at IS NULL OR expires_at > ?) "
            "GROUP BY disposition",
            (normalized_scope, utc_iso()),
        )
        for row in cursor.fetchall():
            if row["disposition"] in result:
                result[row["disposition"]] = row["n"]
        result["total"] = sum(result.values())
        return result

    def close(self) -> None:
        """Close the local database connection."""
        self._conn.close()
