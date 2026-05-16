"""Shared SQLite connection configuration for SentinelX stores."""
from __future__ import annotations

import sqlite3


def _try_pragma(conn: sqlite3.Connection, statement: str) -> None:
    try:
        conn.execute(statement)
    except sqlite3.OperationalError:
        pass


def configure_connection(conn: sqlite3.Connection) -> None:
    """Apply the common WAL-backed local-store pragmas."""
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        _try_pragma(conn, "PRAGMA journal_mode=DELETE")
    _try_pragma(conn, "PRAGMA synchronous=NORMAL")
    _try_pragma(conn, "PRAGMA busy_timeout=5000")
    _try_pragma(conn, "PRAGMA cache_size=-8000")
    _try_pragma(conn, "PRAGMA temp_store=MEMORY")
