"""Focused tests for private local SQLite paths."""
from __future__ import annotations

import sqlite3
import stat
from pathlib import Path

import pytest

from app.audit.store import AuditStore
from app.cache.store import CacheStore
from app.ctf.store import CtfStore
from app.enrichment.history_store import HistoryStore
from app.review.store import ReviewStore
from app.sqlite import configure_connection, prepare_private_path


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_prepare_private_path_creates_private_parents_and_database(tmp_path):
    db_path = tmp_path / "state" / "nested" / "store.db"

    assert prepare_private_path(db_path) == db_path

    assert _mode(db_path.parent.parent) == 0o700
    assert _mode(db_path.parent) == 0o700
    assert _mode(db_path) == 0o600


def test_prepare_private_path_tightens_existing_database_and_sidecars(tmp_path):
    db_path = tmp_path / "store.db"
    db_path.write_bytes(b"existing")
    db_path.chmod(0o644)
    sidecars = (Path(f"{db_path}-wal"), Path(f"{db_path}-shm"))
    for sidecar in sidecars:
        sidecar.write_bytes(b"existing")
        sidecar.chmod(0o644)

    prepare_private_path(db_path)

    assert db_path.read_bytes() == b"existing"
    assert _mode(db_path) == 0o600
    assert all(_mode(sidecar) == 0o600 for sidecar in sidecars)


def test_prepare_private_path_rejects_existing_symlink(tmp_path):
    target = tmp_path / "target.db"
    target.write_bytes(b"existing")
    link = tmp_path / "store.db"
    link.symlink_to(target)

    with pytest.raises(ValueError, match="regular file"):
        prepare_private_path(link)


@pytest.mark.parametrize(
    "store_type",
    (CacheStore, HistoryStore, CtfStore, AuditStore, ReviewStore),
)
def test_every_local_store_creates_a_private_database(tmp_path, store_type):
    db_path = tmp_path / store_type.__name__ / "store.db"

    store = store_type(db_path)
    try:
        assert _mode(db_path.parent) == 0o700
        assert _mode(db_path) == 0o600
    finally:
        store.close()


def test_sqlite_wal_sidecars_inherit_private_database_mode(tmp_path):
    db_path = prepare_private_path(tmp_path / "private" / "store.db")
    conn = sqlite3.connect(db_path)
    try:
        configure_connection(conn)
        conn.execute("CREATE TABLE records (value TEXT NOT NULL)")
        conn.execute("INSERT INTO records VALUES ('x')")
        conn.commit()

        assert _mode(db_path) == 0o600
        assert _mode(Path(f"{db_path}-wal")) == 0o600
        assert _mode(Path(f"{db_path}-shm")) == 0o600
    finally:
        conn.close()
