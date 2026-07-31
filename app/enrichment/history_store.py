"""SQLite analysis history store.

Persists every online analysis run so analysts can review past results
from the home page and reload full analysis detail via /history/<id>.

Thread-safe via threading.Lock on write operations.  Uses WAL journal
mode for concurrent readers without blocking writers (same pattern as
CacheStore).

Usage:
    store = HistoryStore()
    row_id = store.save_analysis(input_text, mode, iocs, results)
    recent = store.list_recent(limit=20)
    full   = store.load_analysis(row_id)

For tests, pass a tmp_path-based db_path to isolate from the real filesystem.
"""
from __future__ import annotations

import datetime
import sqlite3
import threading
import uuid
from pathlib import Path

from .history_records import (
    _analysis_insert_record,
    _analysis_from_row,
    _coerce_max_rows,
    _summary_from_row,
)
from app.sqlite import configure_connection, prepare_private_path
from app.time_utils import utc_now

DEFAULT_DB_PATH = Path.home() / ".sentinelx" / "history.db"
DEFAULT_MAX_ROWS = 500

__all__ = (
    "DEFAULT_MAX_ROWS",
    "HistoryStore",
)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS analysis_history (
    id          TEXT    PRIMARY KEY,
    input_text  TEXT    NOT NULL,
    mode        TEXT    NOT NULL,
    iocs_json   TEXT    NOT NULL,
    results_json TEXT   NOT NULL,
    total_count INTEGER NOT NULL,
    top_verdict TEXT    NOT NULL,
    created_at  TEXT    NOT NULL
)
"""
_CREATE_CREATED_AT_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_history_created_at "
    "ON analysis_history (created_at DESC, id DESC)"
)
_INSERT_ANALYSIS_QUERY = (
    "INSERT INTO analysis_history "
    "(id, input_text, mode, iocs_json, results_json, "
    " total_count, top_verdict, created_at) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
)
_LIST_RECENT_QUERY = (
    "SELECT id, substr(input_text, 1, 120), mode, total_count, top_verdict, created_at "
    "FROM analysis_history "
    "ORDER BY created_at DESC "
    "LIMIT ?"
)
_LOAD_ANALYSIS_QUERY = (
    "SELECT id, input_text, mode, iocs_json, results_json, "
    "       total_count, top_verdict, created_at "
    "FROM analysis_history "
    "WHERE id = ?"
)
_PRUNE_OLD_HISTORY_QUERY = (
    "DELETE FROM analysis_history "
    "WHERE id IN ("
    "    SELECT id FROM analysis_history "
    "    ORDER BY created_at DESC, id DESC "
    "    LIMIT -1 OFFSET ?"
    ")"
)

def _utc_now() -> datetime.datetime:
    """Return the current UTC datetime for persisted history timestamps."""
    return utc_now()


def _append_history_summary(summaries: list[dict], row: tuple) -> None:
    summaries.append(_summary_from_row(row))


class HistoryStore:
    """SQLite-backed analysis history store.

    Each row captures a full analysis run: the raw input text, parsed
    IOCs, enrichment results, computed verdict, and a timestamp.

    Args:
        db_path: Path to the SQLite database file.
                 Defaults to ~/.sentinelx/history.db.
    """

    def __init__(self, db_path: Path | None = None, *, max_rows: int = DEFAULT_MAX_ROWS) -> None:
        self._db_path = prepare_private_path(
            db_path if db_path is not None else DEFAULT_DB_PATH
        )
        self._max_rows = _coerce_max_rows(max_rows)
        self._lock = threading.Lock()
        self._conn = self._connect()
        configure_connection(self._conn)
        self._conn.execute(_CREATE_TABLE)
        self._conn.execute(_CREATE_CREATED_AT_INDEX)
        self._conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._db_path), check_same_thread=False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save_analysis(
        self,
        input_text: str,
        mode: str,
        iocs: list[dict],
        results: list[dict],
        analysis_id: str | None = None,
    ) -> str:
        """Persist a completed analysis run.

        Args:
            input_text: Raw analyst-pasted text.
            mode:       Analysis mode ("online" or "offline").
            iocs:       Serialized IOC dicts (type, value, raw_match).
            results:    Serialized result/error dicts from _serialize_result().
            analysis_id: Optional explicit row id.  When omitted a UUID4 hex
                         string is generated automatically.

        Returns:
            The generated row id (UUID4 hex string).
        """
        row_id = analysis_id if analysis_id is not None else uuid.uuid4().hex
        record = _analysis_insert_record(
            row_id=row_id,
            input_text=input_text,
            mode=mode,
            iocs=iocs,
            results=results,
            created_at=_utc_now().isoformat(),
        )

        with self._lock:
            self._conn.execute(
                _INSERT_ANALYSIS_QUERY,
                record.values,
            )
            self._prune_old_rows_locked()
            self._conn.commit()

        return record.row_id

    def _prune_old_rows_locked(self) -> None:
        """Remove rows beyond the configured retention count."""
        self._conn.execute(_PRUNE_OLD_HISTORY_QUERY, (self._max_rows,))

    def list_recent(self, limit: int = 20) -> list[dict]:
        """Return the most recent analysis summaries.

        Returns lightweight dicts (no full results_json) suitable for
        the home-page recent-analyses list.

        Returns:
            List of dicts with keys: id, input_text (truncated to 120
            chars), mode, total_count, top_verdict, created_at.
        """
        with self._lock:
            rows = self._conn.execute(
                _LIST_RECENT_QUERY,
                (limit,),
            ).fetchall()

        row_count = len(rows)
        if row_count == 0:
            return []
        if row_count == 1:
            return [_summary_from_row(rows[0])]
        if row_count == 2:
            return [_summary_from_row(rows[0]), _summary_from_row(rows[1])]
        if row_count == 3:
            return [
                _summary_from_row(rows[0]),
                _summary_from_row(rows[1]),
                _summary_from_row(rows[2]),
            ]
        if row_count == 4:
            return [
                _summary_from_row(rows[0]),
                _summary_from_row(rows[1]),
                _summary_from_row(rows[2]),
                _summary_from_row(rows[3]),
            ]

        summaries: list[dict] = []
        for row in rows:
            _append_history_summary(summaries, row)
        return summaries

    def load_analysis(self, analysis_id: str) -> dict | None:
        """Load a full analysis row by id.

        Returns:
            Dict with all columns (iocs and results deserialized from
            JSON), or None if the id does not exist.
        """
        with self._lock:
            row = self._conn.execute(
                _LOAD_ANALYSIS_QUERY,
                (analysis_id,),
            ).fetchone()

        if row is None:
            return None

        return _analysis_from_row(row)

    def close(self) -> None:
        """Close the persistent SQLite connection."""
        self._conn.close()
