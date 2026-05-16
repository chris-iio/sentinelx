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
from types import MappingProxyType

from app.json_utils import EMPTY_JSON_ARRAY, decode_json_array, encode_json_array
from app.sqlite import configure_connection
from app.time_utils import utc_now

DEFAULT_DB_PATH = Path.home() / ".sentinelx" / "history.db"
_EMPTY_JSON_ARRAY = EMPTY_JSON_ARRAY

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
    "ON analysis_history (created_at DESC)"
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

_VERDICT_PRIORITY = MappingProxyType({
    "malicious": 4,
    "suspicious": 3,
    "no_data": 2,
    "clean": 1,
})
_MAX_VERDICT = "malicious"
_FALLBACK_VERDICT = "error"


def _summary_from_row(row) -> dict:
    return {
        "id": row[0],
        "input_text": row[1],
        "mode": row[2],
        "total_count": row[3],
        "top_verdict": row[4],
        "created_at": row[5],
    }


def _utc_now() -> datetime.datetime:
    """Return the current UTC datetime for persisted history timestamps."""
    return utc_now()


def _encode_json_array(payload: list[dict]) -> str:
    """Serialize a history payload, skipping JSON encoder work for empty lists."""
    return encode_json_array(payload)


def _decode_json_array(payload_json: str) -> list[dict]:
    """Deserialize a history payload, skipping JSON decoder work for empty lists."""
    return decode_json_array(payload_json)


def _compute_top_verdict(results: list[dict]) -> str:
    """Derive the most severe verdict from a list of serialized results.

    Priority: malicious > suspicious > no_data > clean > unknown.
    Error-only results (type == "error") are ignored for verdict
    computation; if *all* results are errors the verdict is "error".
    """
    result_count = len(results)
    if result_count == 0:
        return _FALLBACK_VERDICT
    if result_count == 1:
        verdict = results[0].get("verdict")
        return verdict if verdict is not None else _FALLBACK_VERDICT

    best: str | None = None
    best_rank = -1

    for r in results:
        verdict = r.get("verdict")
        if verdict is None:
            continue  # error entries have no verdict
        rank = _VERDICT_PRIORITY.get(verdict, 0)
        if rank > best_rank:
            best_rank = rank
            best = verdict
            if verdict == _MAX_VERDICT:
                return verdict

    return best if best is not None else _FALLBACK_VERDICT


class HistoryStore:
    """SQLite-backed analysis history store.

    Each row captures a full analysis run: the raw input text, parsed
    IOCs, enrichment results, computed verdict, and a timestamp.

    Args:
        db_path: Path to the SQLite database file.
                 Defaults to ~/.sentinelx/history.db.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path if db_path is not None else DEFAULT_DB_PATH
        self._lock = threading.Lock()
        self._db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
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
        now = _utc_now().isoformat()
        iocs_json = _encode_json_array(iocs)
        results_json = _encode_json_array(results)
        total_count = len(iocs)
        top_verdict = _compute_top_verdict(results)

        with self._lock:
            self._conn.execute(
                _INSERT_ANALYSIS_QUERY,
                (
                    row_id,
                    input_text,
                    mode,
                    iocs_json,
                    results_json,
                    total_count,
                    top_verdict,
                    now,
                ),
            )
            self._conn.commit()

        return row_id

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

        summaries: list[dict] = []
        for row in rows:
            summaries.append(_summary_from_row(row))
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

        iocs = _decode_json_array(row[3])
        results = _decode_json_array(row[4])

        return {
            "id": row[0],
            "input_text": row[1],
            "mode": row[2],
            "iocs": iocs,
            "results": results,
            "total_count": row[5],
            "top_verdict": row[6],
            "created_at": row[7],
        }
