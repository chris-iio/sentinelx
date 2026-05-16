"""Tests for shared SQLite store configuration."""
from __future__ import annotations

import sqlite3

from app.sqlite import configure_connection


def test_configure_connection_applies_local_store_pragmas(tmp_path):
    conn = sqlite3.connect(tmp_path / "store.db")

    configure_connection(conn)

    assert str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower() == "wal"
    assert conn.execute("PRAGMA synchronous").fetchone()[0] == 1
    assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    assert conn.execute("PRAGMA cache_size").fetchone()[0] == -8000
    assert conn.execute("PRAGMA temp_store").fetchone()[0] == 2


def test_configure_connection_falls_back_when_wal_sidecar_is_unavailable(monkeypatch):
    calls: list[str] = []

    class FakeConnection:
        def execute(self, statement: str):
            calls.append(statement)
            if statement == "PRAGMA journal_mode=WAL":
                raise sqlite3.OperationalError("unable to open database file")
            return self

    configure_connection(FakeConnection())  # type: ignore[arg-type]

    assert calls == [
        "PRAGMA journal_mode=WAL",
        "PRAGMA journal_mode=DELETE",
        "PRAGMA synchronous=NORMAL",
        "PRAGMA busy_timeout=5000",
        "PRAGMA cache_size=-8000",
        "PRAGMA temp_store=MEMORY",
    ]


def test_configure_connection_continues_when_all_journal_modes_are_unavailable():
    calls: list[str] = []

    class FakeConnection:
        def execute(self, statement: str):
            calls.append(statement)
            if statement.startswith("PRAGMA journal_mode="):
                raise sqlite3.OperationalError("unable to open database file")
            return self

    configure_connection(FakeConnection())  # type: ignore[arg-type]

    assert calls == [
        "PRAGMA journal_mode=WAL",
        "PRAGMA journal_mode=DELETE",
        "PRAGMA synchronous=NORMAL",
        "PRAGMA busy_timeout=5000",
        "PRAGMA cache_size=-8000",
        "PRAGMA temp_store=MEMORY",
    ]
