"""Shared SQLite connection configuration for SentinelX stores."""
from __future__ import annotations

import os
import sqlite3
import stat
from contextlib import suppress
from pathlib import Path

__all__ = ("configure_connection", "prepare_private_path")


def prepare_private_path(db_path: str | Path) -> Path:
    """Prepare a private path before SQLite opens a local database.

    The function creates each missing parent directory with mode ``0700`` and
    atomically creates a missing database file with mode ``0600``. Existing
    database files and sidecars are tightened to ``0600`` during upgrade.
    SQLite's Unix VFS derives new WAL and shared-memory sidecar permissions
    from the main database file. The process umask can make these modes more
    restrictive.

    Existing parent directories are not changed because a configured database
    can live in a shared system directory. Store constructors must call this
    function before ``sqlite3.connect`` to get these guarantees.
    """
    path = Path(db_path)
    missing_parents: list[Path] = []
    parent = path.parent
    while not parent.exists():
        missing_parents.append(parent)
        if parent == parent.parent:
            break
        parent = parent.parent
    for directory in reversed(missing_parents):
        try:
            directory.mkdir(mode=0o700)
        except FileExistsError:
            pass

    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError(f"SQLite path must be a regular file: {path}") from None
        os.chmod(path, 0o600)
    else:
        os.close(fd)

    for suffix in ("-wal", "-shm"):
        sidecar = Path(f"{path}{suffix}")
        try:
            sidecar_mode = sidecar.lstat().st_mode
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(sidecar_mode):
            raise ValueError(f"SQLite sidecar must be a regular file: {sidecar}")
        os.chmod(sidecar, 0o600)
    return path


def _try_pragma(conn: sqlite3.Connection, statement: str) -> None:
    with suppress(sqlite3.OperationalError):
        conn.execute(statement)


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
