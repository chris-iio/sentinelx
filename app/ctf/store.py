"""SQLite CTF workspace store.

Persists CTF events, challenges, per-challenge notes, and captured flags so
analysts can track progress across an event such as HackTheBox Cyber
Apocalypse without leaving the local workbench.

Thread-safe via threading.Lock on write operations. Uses the shared WAL
pragma configuration (same pattern as CacheStore/HistoryStore).

For tests, pass a tmp_path-based db_path to isolate from the real filesystem.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from pathlib import Path

from app.sqlite import configure_connection, prepare_private_path
from app.time_utils import utc_iso

from .flags import detect_flags

DEFAULT_DB_PATH = Path.home() / ".sentinelx" / "ctf.db"

CATEGORIES = (
    "web",
    "crypto",
    "pwn",
    "rev",
    "forensics",
    "osint",
    "misc",
    "hardware",
    "blockchain",
    "ml",
)
DIFFICULTIES = ("easy", "medium", "hard", "insane", "unknown")
STATUSES = ("open", "working", "solved")

__all__ = (
    "CATEGORIES",
    "DIFFICULTIES",
    "STATUSES",
    "CtfStore",
)

_CREATE_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS ctf_events (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    url        TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
)
"""
_CREATE_CHALLENGES_TABLE = """
CREATE TABLE IF NOT EXISTS ctf_challenges (
    id          TEXT PRIMARY KEY,
    event_id    TEXT NOT NULL REFERENCES ctf_events(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,
    difficulty  TEXT NOT NULL DEFAULT 'unknown',
    points      INTEGER NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'open',
    description TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
)
"""
_CREATE_NOTES_TABLE = """
CREATE TABLE IF NOT EXISTS ctf_notes (
    id           TEXT PRIMARY KEY,
    challenge_id TEXT NOT NULL REFERENCES ctf_challenges(id) ON DELETE CASCADE,
    body         TEXT NOT NULL,
    created_at   TEXT NOT NULL
)
"""
_CREATE_FLAGS_TABLE = """
CREATE TABLE IF NOT EXISTS ctf_flags (
    id           TEXT PRIMARY KEY,
    challenge_id TEXT NOT NULL REFERENCES ctf_challenges(id) ON DELETE CASCADE,
    flag         TEXT NOT NULL,
    source       TEXT NOT NULL DEFAULT 'manual',
    created_at   TEXT NOT NULL,
    UNIQUE (challenge_id, flag)
)
"""
_CREATE_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS ctf_runs (
    id           TEXT PRIMARY KEY,
    challenge_id TEXT NOT NULL REFERENCES ctf_challenges(id) ON DELETE CASCADE,
    profile      TEXT NOT NULL,
    argv_json    TEXT NOT NULL,
    exit_code    INTEGER NOT NULL,
    output       TEXT NOT NULL,
    error        TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL
)
"""
_CREATE_CHALLENGES_EVENT_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_ctf_challenges_event "
    "ON ctf_challenges (event_id, created_at)"
)
_CREATE_NOTES_CHALLENGE_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_ctf_notes_challenge "
    "ON ctf_notes (challenge_id, created_at)"
)
_CREATE_FLAGS_CHALLENGE_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_ctf_flags_challenge "
    "ON ctf_flags (challenge_id, created_at)"
)
_CREATE_RUNS_CHALLENGE_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_ctf_runs_challenge "
    "ON ctf_runs (challenge_id, created_at)"
)


def _new_id() -> str:
    return uuid.uuid4().hex


def _event_from_row(row: tuple) -> dict:
    return {"id": row[0], "name": row[1], "url": row[2], "created_at": row[3]}


def _challenge_from_row(row: tuple) -> dict:
    return {
        "id": row[0],
        "event_id": row[1],
        "name": row[2],
        "category": row[3],
        "difficulty": row[4],
        "points": row[5],
        "status": row[6],
        "description": row[7],
        "created_at": row[8],
        "updated_at": row[9],
    }


def _note_from_row(row: tuple) -> dict:
    return {"id": row[0], "challenge_id": row[1], "body": row[2], "created_at": row[3]}


def _flag_from_row(row: tuple) -> dict:
    return {
        "id": row[0],
        "challenge_id": row[1],
        "flag": row[2],
        "source": row[3],
        "created_at": row[4],
    }


def _run_from_row(row: tuple) -> dict:
    return {
        "id": row[0],
        "challenge_id": row[1],
        "profile": row[2],
        "argv": json.loads(row[3]),
        "exit_code": row[4],
        "output": row[5],
        "error": row[6],
        "created_at": row[7],
    }


class CtfStore:
    """SQLite-backed CTF workspace store.

    Args:
        db_path: Path to the SQLite database file.
                 Defaults to ~/.sentinelx/ctf.db.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = prepare_private_path(
            db_path if db_path is not None else DEFAULT_DB_PATH
        )
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        configure_connection(self._conn)
        self._conn.execute("PRAGMA foreign_keys=ON")
        for statement in (
            _CREATE_EVENTS_TABLE,
            _CREATE_CHALLENGES_TABLE,
            _CREATE_NOTES_TABLE,
            _CREATE_FLAGS_TABLE,
            _CREATE_RUNS_TABLE,
            _CREATE_CHALLENGES_EVENT_INDEX,
            _CREATE_NOTES_CHALLENGE_INDEX,
            _CREATE_FLAGS_CHALLENGE_INDEX,
            _CREATE_RUNS_CHALLENGE_INDEX,
        ):
            self._conn.execute(statement)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Events

    def create_event(self, name: str, url: str = "") -> str:
        """Create an event and return its id."""
        event_id = _new_id()
        with self._lock:
            self._conn.execute(
                "INSERT INTO ctf_events (id, name, url, created_at) VALUES (?, ?, ?, ?)",
                (event_id, name, url, utc_iso()),
            )
            self._conn.commit()
        return event_id

    def list_events(self) -> list[dict]:
        """Return all events, newest first, with per-event challenge counts."""
        cursor = self._conn.execute(
            "SELECT e.id, e.name, e.url, e.created_at, "
            "       COUNT(c.id), "
            "       COALESCE(SUM(CASE WHEN c.status = 'solved' THEN 1 ELSE 0 END), 0) "
            "FROM ctf_events e "
            "LEFT JOIN ctf_challenges c ON c.event_id = e.id "
            "GROUP BY e.id "
            "ORDER BY e.created_at DESC"
        )
        events = []
        for row in cursor.fetchall():
            event = _event_from_row(row[:4])
            event["challenge_count"] = row[4]
            event["solved_count"] = row[5]
            events.append(event)
        return events

    def get_event(self, event_id: str) -> dict | None:
        """Return one event by id, or None."""
        cursor = self._conn.execute(
            "SELECT id, name, url, created_at FROM ctf_events WHERE id = ?",
            (event_id,),
        )
        row = cursor.fetchone()
        return _event_from_row(row) if row else None

    def delete_event(self, event_id: str) -> bool:
        """Delete an event and (via cascade) its challenges. Returns whether one existed."""
        with self._lock:
            cursor = self._conn.execute("DELETE FROM ctf_events WHERE id = ?", (event_id,))
            self._conn.commit()
        return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Challenges

    def create_challenge(
        self,
        event_id: str,
        name: str,
        category: str,
        difficulty: str = "unknown",
        points: int = 0,
        description: str = "",
    ) -> str:
        """Create a challenge under an event and return its id."""
        challenge_id = _new_id()
        now = utc_iso()
        with self._lock:
            self._conn.execute(
                "INSERT INTO ctf_challenges "
                "(id, event_id, name, category, difficulty, points, status, "
                " description, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?, ?)",
                (challenge_id, event_id, name, category, difficulty, points,
                 description, now, now),
            )
            self._conn.commit()
        return challenge_id

    def list_challenges(self, event_id: str) -> list[dict]:
        """Return challenges for an event, ordered by category then name."""
        cursor = self._conn.execute(
            "SELECT id, event_id, name, category, difficulty, points, status, "
            "       description, created_at, updated_at "
            "FROM ctf_challenges WHERE event_id = ? "
            "ORDER BY category ASC, name ASC",
            (event_id,),
        )
        return [_challenge_from_row(row) for row in cursor.fetchall()]

    def get_challenge(self, challenge_id: str) -> dict | None:
        """Return one challenge by id, or None."""
        cursor = self._conn.execute(
            "SELECT id, event_id, name, category, difficulty, points, status, "
            "       description, created_at, updated_at "
            "FROM ctf_challenges WHERE id = ?",
            (challenge_id,),
        )
        row = cursor.fetchone()
        return _challenge_from_row(row) if row else None

    def set_challenge_status(self, challenge_id: str, status: str) -> bool:
        """Update a challenge's status. Returns whether the challenge existed."""
        with self._lock:
            cursor = self._conn.execute(
                "UPDATE ctf_challenges SET status = ?, updated_at = ? WHERE id = ?",
                (status, utc_iso(), challenge_id),
            )
            self._conn.commit()
        return cursor.rowcount > 0

    def delete_challenge(self, challenge_id: str) -> bool:
        """Delete a challenge and its notes/flags. Returns whether one existed."""
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM ctf_challenges WHERE id = ?", (challenge_id,)
            )
            self._conn.commit()
        return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Notes

    def add_note(self, challenge_id: str, body: str) -> tuple[str, list[str]]:
        """Add a note; auto-capture flag-shaped tokens into the flag vault.

        Returns:
            (note_id, detected_flags) — flags newly seen in this note body,
            whether or not they were already in the vault.
        """
        note_id = _new_id()
        detected = detect_flags(body)
        with self._lock:
            self._conn.execute(
                "INSERT INTO ctf_notes (id, challenge_id, body, created_at) "
                "VALUES (?, ?, ?, ?)",
                (note_id, challenge_id, body, utc_iso()),
            )
            for flag in detected:
                self._insert_flag_locked(challenge_id, flag, source="note")
            self._conn.commit()
        return note_id, detected

    def list_notes(self, challenge_id: str) -> list[dict]:
        """Return notes for a challenge, newest first."""
        cursor = self._conn.execute(
            "SELECT id, challenge_id, body, created_at FROM ctf_notes "
            "WHERE challenge_id = ? ORDER BY created_at DESC",
            (challenge_id,),
        )
        return [_note_from_row(row) for row in cursor.fetchall()]

    # ------------------------------------------------------------------
    # Flags

    def _insert_flag_locked(self, challenge_id: str, flag: str, source: str) -> bool:
        cursor = self._conn.execute(
            "INSERT OR IGNORE INTO ctf_flags (id, challenge_id, flag, source, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (_new_id(), challenge_id, flag, source, utc_iso()),
        )
        return cursor.rowcount > 0

    def add_flag(self, challenge_id: str, flag: str, source: str = "manual") -> bool:
        """Record a flag in the vault. Returns False when it was already stored."""
        with self._lock:
            inserted = self._insert_flag_locked(challenge_id, flag, source=source)
            self._conn.commit()
        return inserted

    def list_flags(self, challenge_id: str) -> list[dict]:
        """Return flags captured for a challenge, newest first."""
        cursor = self._conn.execute(
            "SELECT id, challenge_id, flag, source, created_at FROM ctf_flags "
            "WHERE challenge_id = ? ORDER BY created_at DESC",
            (challenge_id,),
        )
        return [_flag_from_row(row) for row in cursor.fetchall()]

    # ------------------------------------------------------------------
    # Runs

    def add_run(
        self,
        challenge_id: str,
        profile: str,
        argv: list[str],
        exit_code: int,
        output: str,
        error: str = "",
    ) -> str:
        """Record one allowlisted tool run; auto-capture flags in its output."""
        run_id = _new_id()
        with self._lock:
            self._conn.execute(
                "INSERT INTO ctf_runs "
                "(id, challenge_id, profile, argv_json, exit_code, output, error, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, challenge_id, profile, json.dumps(argv), exit_code,
                 output, error, utc_iso()),
            )
            for flag in detect_flags(output):
                self._insert_flag_locked(challenge_id, flag, source="run")
            self._conn.commit()
        return run_id

    def list_runs(self, challenge_id: str) -> list[dict]:
        """Return recorded tool runs for a challenge, newest first."""
        cursor = self._conn.execute(
            "SELECT id, challenge_id, profile, argv_json, exit_code, output, error, created_at "
            "FROM ctf_runs WHERE challenge_id = ? ORDER BY created_at DESC",
            (challenge_id,),
        )
        return [_run_from_row(row) for row in cursor.fetchall()]

    def event_stats(self, event_id: str) -> dict:
        """Return solved/open counts and points for an event."""
        cursor = self._conn.execute(
            "SELECT COUNT(*), "
            "       COALESCE(SUM(CASE WHEN status = 'solved' THEN 1 ELSE 0 END), 0), "
            "       COALESCE(SUM(CASE WHEN status = 'solved' THEN points ELSE 0 END), 0) "
            "FROM ctf_challenges WHERE event_id = ?",
            (event_id,),
        )
        total, solved, points = cursor.fetchone()
        return {"total": total, "solved": solved, "points": points}

    def close(self) -> None:
        """Close the persistent SQLite connection."""
        self._conn.close()
