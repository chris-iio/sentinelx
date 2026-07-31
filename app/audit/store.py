"""SQLite audit-engagement workbench store.

Persists security-review engagements (audit contests, bug bounties, supply
chain reviews) and their findings so researchers can triage a queue from
intake through submission without leaving the local workbench.

Thread-safe via threading.Lock on write operations. Uses the shared WAL
pragma configuration (same pattern as CtfStore).

For tests, pass a tmp_path-based db_path to isolate from the real filesystem.
"""
from __future__ import annotations

import sqlite3
import threading
import uuid
from pathlib import Path

from app.sqlite import configure_connection, prepare_private_path
from app.time_utils import utc_iso

DEFAULT_DB_PATH = Path.home() / ".sentinelx" / "audit.db"

PLATFORMS = (
    "code4rena",
    "codehawks",
    "immunefi",
    "hackenproof",
    "sherlock",
    "cantina",
    "self",
    "other",
)
SEVERITIES = ("critical", "high", "medium", "low", "info", "gas")
ENGAGEMENT_STATUSES = ("active", "submitted", "closed")
FINDING_STATUSES = (
    "draft",
    "triaged",
    "submitted",
    "accepted",
    "rejected",
    "duplicate",
)

__all__ = (
    "PLATFORMS",
    "SEVERITIES",
    "ENGAGEMENT_STATUSES",
    "FINDING_STATUSES",
    "AuditStore",
)

_CREATE_ENGAGEMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS audit_engagements (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    platform    TEXT NOT NULL DEFAULT 'other',
    url         TEXT NOT NULL DEFAULT '',
    scope       TEXT NOT NULL DEFAULT '',
    prize_pool  TEXT NOT NULL DEFAULT '',
    deadline    TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'active',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
)
"""
_CREATE_FINDINGS_TABLE = """
CREATE TABLE IF NOT EXISTS audit_findings (
    id            TEXT PRIMARY KEY,
    engagement_id TEXT NOT NULL REFERENCES audit_engagements(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    severity      TEXT NOT NULL DEFAULT 'info',
    status        TEXT NOT NULL DEFAULT 'draft',
    target        TEXT NOT NULL DEFAULT '',
    description   TEXT NOT NULL DEFAULT '',
    impact        TEXT NOT NULL DEFAULT '',
    poc           TEXT NOT NULL DEFAULT '',
    remediation   TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
)
"""
_CREATE_FINDINGS_ENGAGEMENT_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_audit_findings_engagement "
    "ON audit_findings (engagement_id, severity, status)"
)


def _new_id() -> str:
    return uuid.uuid4().hex


def _engagement_from_row(row: tuple) -> dict:
    return {
        "id": row[0],
        "name": row[1],
        "platform": row[2],
        "url": row[3],
        "scope": row[4],
        "prize_pool": row[5],
        "deadline": row[6],
        "status": row[7],
        "created_at": row[8],
        "updated_at": row[9],
    }


def _finding_from_row(row: tuple) -> dict:
    return {
        "id": row[0],
        "engagement_id": row[1],
        "title": row[2],
        "severity": row[3],
        "status": row[4],
        "target": row[5],
        "description": row[6],
        "impact": row[7],
        "poc": row[8],
        "remediation": row[9],
        "created_at": row[10],
        "updated_at": row[11],
    }


_FINDING_COLUMNS = (
    "id, engagement_id, title, severity, status, target, description, "
    "impact, poc, remediation, created_at, updated_at"
)


class AuditStore:
    """SQLite-backed audit engagement workbench store.

    Args:
        db_path: Path to the SQLite database file.
                 Defaults to ~/.sentinelx/audit.db.
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
            _CREATE_ENGAGEMENTS_TABLE,
            _CREATE_FINDINGS_TABLE,
            _CREATE_FINDINGS_ENGAGEMENT_INDEX,
        ):
            self._conn.execute(statement)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Engagements

    def create_engagement(
        self,
        name: str,
        platform: str = "other",
        url: str = "",
        scope: str = "",
        prize_pool: str = "",
        deadline: str = "",
    ) -> str:
        """Create an engagement and return its id."""
        if platform not in PLATFORMS:
            platform = "other"
        engagement_id = _new_id()
        now = utc_iso()
        with self._lock:
            self._conn.execute(
                "INSERT INTO audit_engagements "
                "(id, name, platform, url, scope, prize_pool, deadline, status, "
                " created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)",
                (engagement_id, name, platform, url, scope, prize_pool,
                 deadline, now, now),
            )
            self._conn.commit()
        return engagement_id

    def list_engagements(self) -> list[dict]:
        """Return all engagements, newest first, with per-engagement finding counts."""
        cursor = self._conn.execute(
            "SELECT e.id, e.name, e.platform, e.url, e.scope, e.prize_pool, "
            "       e.deadline, e.status, e.created_at, e.updated_at, "
            "       COUNT(f.id) "
            "FROM audit_engagements e "
            "LEFT JOIN audit_findings f ON f.engagement_id = e.id "
            "GROUP BY e.id "
            "ORDER BY e.created_at DESC"
        )
        engagements = []
        for row in cursor.fetchall():
            engagement = _engagement_from_row(row[:10])
            engagement["finding_count"] = row[10]
            engagements.append(engagement)
        return engagements

    def get_engagement(self, engagement_id: str) -> dict | None:
        """Return one engagement by id, or None."""
        cursor = self._conn.execute(
            "SELECT id, name, platform, url, scope, prize_pool, deadline, status, "
            "       created_at, updated_at "
            "FROM audit_engagements WHERE id = ?",
            (engagement_id,),
        )
        row = cursor.fetchone()
        return _engagement_from_row(row) if row else None

    def set_engagement_status(self, engagement_id: str, status: str) -> bool:
        """Update an engagement's status. Returns whether it existed."""
        if status not in ENGAGEMENT_STATUSES:
            return False
        with self._lock:
            cursor = self._conn.execute(
                "UPDATE audit_engagements SET status = ?, updated_at = ? WHERE id = ?",
                (status, utc_iso(), engagement_id),
            )
            self._conn.commit()
        return cursor.rowcount > 0

    def delete_engagement(self, engagement_id: str) -> bool:
        """Delete an engagement and (via cascade) its findings."""
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM audit_engagements WHERE id = ?", (engagement_id,)
            )
            self._conn.commit()
        return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Findings

    def create_finding(
        self,
        engagement_id: str,
        title: str,
        severity: str = "info",
        status: str = "draft",
        target: str = "",
        description: str = "",
        impact: str = "",
        poc: str = "",
        remediation: str = "",
    ) -> str | None:
        """Create a finding under an engagement. Returns id, or None if the
        engagement does not exist or severity/status are invalid."""
        if severity not in SEVERITIES or status not in FINDING_STATUSES:
            return None
        if self.get_engagement(engagement_id) is None:
            return None
        finding_id = _new_id()
        now = utc_iso()
        with self._lock:
            self._conn.execute(
                "INSERT INTO audit_findings "
                "(id, engagement_id, title, severity, status, target, description, "
                " impact, poc, remediation, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (finding_id, engagement_id, title, severity, status, target,
                 description, impact, poc, remediation, now, now),
            )
            self._conn.commit()
        return finding_id

    def list_findings(
        self,
        engagement_id: str,
        severity: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        """Return findings for an engagement, worst severity first, optionally
        filtered by severity and/or status."""
        # The interpolated column list is a module constant. Values stay parameterized.
        query = f"SELECT {_FINDING_COLUMNS} FROM audit_findings WHERE engagement_id = ?"  # noqa: S608  # nosec B608
        params: list = [engagement_id]
        if severity is not None:
            query += " AND severity = ?"
            params.append(severity)
        if status is not None:
            query += " AND status = ?"
            params.append(status)
        query += (
            " ORDER BY CASE severity "
            "WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 "
            "WHEN 'low' THEN 3 WHEN 'info' THEN 4 ELSE 5 END, "
            "updated_at DESC"
        )
        cursor = self._conn.execute(query, params)
        return [_finding_from_row(row) for row in cursor.fetchall()]

    def get_finding(self, finding_id: str) -> dict | None:
        """Return one finding by id, or None."""
        # The interpolated column list is a module constant. Values stay parameterized.
        cursor = self._conn.execute(
            f"SELECT {_FINDING_COLUMNS} FROM audit_findings WHERE id = ?",  # noqa: S608  # nosec B608
            (finding_id,),
        )
        row = cursor.fetchone()
        return _finding_from_row(row) if row else None

    def update_finding(self, finding_id: str, fields: dict) -> bool:
        """Update editable fields of a finding. Returns whether it existed.

        Only known fields with valid values are applied; unknown keys are
        ignored.
        """
        allowed = {
            "title": None,
            "severity": SEVERITIES,
            "status": FINDING_STATUSES,
            "target": None,
            "description": None,
            "impact": None,
            "poc": None,
            "remediation": None,
        }
        updates = []
        params: list = []
        for key, constraint in allowed.items():
            if key not in fields:
                continue
            value = fields[key]
            if constraint is not None and value not in constraint:
                continue
            updates.append(f"{key} = ?")
            params.append(value)
        if not updates:
            return self.get_finding(finding_id) is not None
        updates.append("updated_at = ?")
        params.append(utc_iso())
        params.append(finding_id)
        with self._lock:
            # Only keys from the local allowed map can enter this SQL fragment.
            cursor = self._conn.execute(
                f"UPDATE audit_findings SET {', '.join(updates)} WHERE id = ?",  # noqa: S608  # nosec B608
                params,
            )
            self._conn.commit()
        return cursor.rowcount > 0

    def delete_finding(self, finding_id: str) -> bool:
        """Delete a finding. Returns whether one existed."""
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM audit_findings WHERE id = ?", (finding_id,)
            )
            self._conn.commit()
        return cursor.rowcount > 0

    def engagement_stats(self, engagement_id: str) -> dict:
        """Return per-severity and per-status counts for an engagement."""
        cursor = self._conn.execute(
            "SELECT severity, COUNT(*) FROM audit_findings "
            "WHERE engagement_id = ? GROUP BY severity",
            (engagement_id,),
        )
        by_severity = {severity: 0 for severity in SEVERITIES}
        for severity, count in cursor.fetchall():
            by_severity[severity] = count
        cursor = self._conn.execute(
            "SELECT status, COUNT(*) FROM audit_findings "
            "WHERE engagement_id = ? GROUP BY status",
            (engagement_id,),
        )
        by_status = {status: 0 for status in FINDING_STATUSES}
        for status, count in cursor.fetchall():
            by_status[status] = count
        return {
            "total": sum(by_severity.values()),
            "by_severity": by_severity,
            "by_status": by_status,
        }

    def close(self) -> None:
        """Close the persistent SQLite connection."""
        self._conn.close()
