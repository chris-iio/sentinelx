"""SQLite annotation store for per-IOC notes and tags.

Stores analyst annotations (free-text notes and structured tags) keyed by
(ioc_value, ioc_type). Annotations are persisted separately from the
enrichment cache so CacheStore.clear() never erases analyst work.

Thread-safe via threading.Lock on write operations. Notes capped at 10000
chars; tags capped at 100 chars each with a max of 50 tags per IOC.

Usage:
    store = AnnotationStore()
    store.set_notes("1.2.3.4", "ipv4", "Seen in incident #42")
    store.set_tags("1.2.3.4", "ipv4", ["apt29", "c2"])
    annotation = store.get("1.2.3.4", "ipv4")
    # {"notes": "Seen in incident #42", "tags": ["apt29", "c2"]}

For tests, pass a tmp_path-based db_path to isolate from the real filesystem.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path

DEFAULT_ANNOTATIONS_PATH = Path.home() / ".sentinelx" / "annotations.db"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS ioc_annotations (
    ioc_value   TEXT NOT NULL,
    ioc_type    TEXT NOT NULL,
    notes       TEXT NOT NULL DEFAULT '',
    tags        TEXT NOT NULL DEFAULT '[]',
    updated_at  TEXT NOT NULL,
    PRIMARY KEY (ioc_value, ioc_type)
)
"""

_NOTES_MAX_CHARS = 10_000
_TAG_MAX_CHARS = 100
_TAGS_MAX_COUNT = 50


class AnnotationStore:
    """SQLite-backed annotation store for per-IOC notes and tags.

    Args:
        db_path: Path to the SQLite database file.
                 Defaults to ~/.sentinelx/annotations.db.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path if db_path is not None else DEFAULT_ANNOTATIONS_PATH
        self._lock = threading.Lock()
        # Create parent dir with restricted permissions (SEC-17)
        self._db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        conn = self._connect()
        conn.execute(_CREATE_TABLE)
        conn.commit()
        conn.close()
        # Restrict DB file permissions after creation (SEC-17)
        if self._db_path.exists():
            os.chmod(self._db_path, 0o600)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._db_path), check_same_thread=False)

    def get(self, ioc_value: str, ioc_type: str) -> dict:
        """Return annotation for an IOC.

        Returns:
            Dict with "notes" (str) and "tags" (list[str]).
            Defaults to {"notes": "", "tags": []} if not found.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT notes, tags FROM ioc_annotations "
                "WHERE ioc_value = ? AND ioc_type = ?",
                (ioc_value, ioc_type),
            ).fetchone()

        if row is None:
            return {"notes": "", "tags": []}

        notes, tags_json = row
        return {"notes": notes, "tags": json.loads(tags_json)}

    def set_notes(self, ioc_value: str, ioc_type: str, notes: str) -> None:
        """Set or update the notes for an IOC.

        If a row already exists for this IOC, preserves existing tags.
        Notes are truncated to _NOTES_MAX_CHARS if necessary.
        """
        import datetime
        notes = notes[:_NOTES_MAX_CHARS]
        now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()

        with self._lock, self._connect() as conn:
            # Fetch existing tags to preserve them on upsert
            row = conn.execute(
                "SELECT tags FROM ioc_annotations WHERE ioc_value = ? AND ioc_type = ?",
                (ioc_value, ioc_type),
            ).fetchone()
            existing_tags = row[0] if row else "[]"

            conn.execute(
                "INSERT OR REPLACE INTO ioc_annotations "
                "(ioc_value, ioc_type, notes, tags, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (ioc_value, ioc_type, notes, existing_tags, now),
            )
            conn.commit()

    def set_tags(self, ioc_value: str, ioc_type: str, tags: list[str]) -> None:
        """Set or update the tags for an IOC.

        Deduplicates tags, caps each at _TAG_MAX_CHARS, limits to _TAGS_MAX_COUNT.
        If a row already exists, preserves existing notes.
        """
        import datetime
        # Deduplicate while preserving order; cap each tag; limit total count
        seen: set[str] = set()
        deduped: list[str] = []
        for tag in tags:
            tag = tag[:_TAG_MAX_CHARS]
            if tag not in seen:
                seen.add(tag)
                deduped.append(tag)
            if len(deduped) >= _TAGS_MAX_COUNT:
                break

        tags_json = json.dumps(deduped)
        now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()

        with self._lock, self._connect() as conn:
            # Fetch existing notes to preserve them on upsert
            row = conn.execute(
                "SELECT notes FROM ioc_annotations WHERE ioc_value = ? AND ioc_type = ?",
                (ioc_value, ioc_type),
            ).fetchone()
            existing_notes = row[0] if row else ""

            conn.execute(
                "INSERT OR REPLACE INTO ioc_annotations "
                "(ioc_value, ioc_type, notes, tags, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (ioc_value, ioc_type, existing_notes, tags_json, now),
            )
            conn.commit()

    def delete(self, ioc_value: str, ioc_type: str) -> None:
        """Remove annotation for an IOC. No-op if not found."""
        with self._lock, self._connect() as conn:
            conn.execute(
                "DELETE FROM ioc_annotations WHERE ioc_value = ? AND ioc_type = ?",
                (ioc_value, ioc_type),
            )
            conn.commit()

    def get_all_for_ioc_values(
        self, ioc_pairs: list[tuple[str, str]]
    ) -> dict[str, dict]:
        """Bulk read annotations for multiple IOCs.

        Args:
            ioc_pairs: List of (ioc_value, ioc_type) tuples to look up.

        Returns:
            Dict keyed by "value|type" mapping to annotation dicts.
            Each entry has "notes" and "tags". Missing IOCs get default values.
        """
        if not ioc_pairs:
            return {}

        result: dict[str, dict] = {}

        with self._connect() as conn:
            for ioc_value, ioc_type in ioc_pairs:
                key = f"{ioc_value}|{ioc_type}"
                row = conn.execute(
                    "SELECT notes, tags FROM ioc_annotations "
                    "WHERE ioc_value = ? AND ioc_type = ?",
                    (ioc_value, ioc_type),
                ).fetchone()

                if row is None:
                    result[key] = {"notes": "", "tags": []}
                else:
                    notes, tags_json = row
                    result[key] = {"notes": notes, "tags": json.loads(tags_json)}

        return result
