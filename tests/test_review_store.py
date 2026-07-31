"""Tests for the analyst IOC review store."""

import sqlite3

import pytest

from app.review.store import DISPOSITIONS, LEGACY_SCOPE, ReviewStore

SCOPE = "incident/acme-42"


def _store(tmp_path):
    return ReviewStore(tmp_path / "review.db")


def test_set_and_get_roundtrip(tmp_path):
    store = _store(tmp_path)
    assert store.set_disposition(
        SCOPE,
        "ipv4",
        "203.0.113.10",
        "confirmed",
        note="C2 in the ACME incident",
        author="analyst@example.test",
        source="manual",
    )
    record = store.get(SCOPE, "ipv4", "203.0.113.10")
    assert record is not None
    assert record["scope"] == SCOPE
    assert record["disposition"] == "confirmed"
    assert record["note"] == "C2 in the ACME incident"
    assert record["reason"] == ""
    assert record["author"] == "analyst@example.test"
    assert record["source"] == "manual"
    assert record["created_at"]
    assert record["updated_at"] >= record["created_at"]


def test_get_unknown_indicator_returns_none(tmp_path):
    store = _store(tmp_path)
    assert store.get(SCOPE, "ipv4", "198.51.100.7") is None


def test_unknown_disposition_rejected(tmp_path):
    store = _store(tmp_path)
    assert store.set_disposition(SCOPE, "ipv4", "203.0.113.10", "bogus") is False
    assert store.get(SCOPE, "ipv4", "203.0.113.10") is None


def test_false_positive_requires_a_reason(tmp_path):
    store = _store(tmp_path)
    assert store.set_disposition(SCOPE, "domain", "example.com", "false_positive") is False
    assert (
        store.set_disposition(
            SCOPE, "domain", "example.com", "false_positive", reason="  "
        )
        is False
    )
    assert store.get(SCOPE, "domain", "example.com") is None


def test_false_positive_reason_stored_verbatim(tmp_path):
    store = _store(tmp_path)
    reason = "Internal DNS resolver; expected noise in every paste."
    assert store.set_disposition(
        SCOPE, "domain", "resolver.internal", "false_positive", reason=reason
    )
    assert store.get(SCOPE, "domain", "resolver.internal")["reason"] == reason


def test_empty_key_rejected(tmp_path):
    store = _store(tmp_path)
    assert store.set_disposition("", "ipv4", "203.0.113.10", "confirmed") is False
    assert store.set_disposition(SCOPE, "", "203.0.113.10", "confirmed") is False
    assert store.set_disposition(SCOPE, "ipv4", "   ", "confirmed") is False


def test_keys_are_trimmed(tmp_path):
    store = _store(tmp_path)
    assert store.set_disposition(
        f" {SCOPE} ", " ipv4 ", " 203.0.113.10 ", "confirmed"
    )
    assert store.get(SCOPE, "ipv4", "203.0.113.10") is not None


def test_identical_indicator_decisions_do_not_cross_scopes(tmp_path):
    store = _store(tmp_path)
    assert store.set_disposition(
        "incident/alpha",
        "domain",
        "shared.example",
        "false_positive",
        reason="Owned test host",
    )
    assert store.set_disposition(
        "incident/bravo", "domain", "shared.example", "confirmed"
    )

    alpha = store.get("incident/alpha", "domain", "shared.example")
    bravo = store.get("incident/bravo", "domain", "shared.example")
    assert alpha["disposition"] == "false_positive"
    assert bravo["disposition"] == "confirmed"
    assert store.counts("incident/alpha")["total"] == 1
    assert store.counts("incident/bravo")["total"] == 1


def test_update_keeps_created_at_and_moves_updated_at(tmp_path):
    store = _store(tmp_path)
    assert store.set_disposition(
        SCOPE, "md5", "d41d8cd98f00b204e9800998ecf8427e", "confirmed"
    )
    first = store.get(SCOPE, "md5", "d41d8cd98f00b204e9800998ecf8427e")
    assert store.set_disposition(
        SCOPE,
        "md5",
        "d41d8cd98f00b204e9800998ecf8427e",
        "acknowledged",
        note="accepted risk",
    )
    second = store.get(SCOPE, "md5", "d41d8cd98f00b204e9800998ecf8427e")
    assert second["disposition"] == "acknowledged"
    assert second["created_at"] == first["created_at"]
    assert second["updated_at"] >= first["updated_at"]


def test_reset_to_unreviewed_clears_reason_and_note(tmp_path):
    store = _store(tmp_path)
    assert store.set_disposition(
        SCOPE,
        "url",
        "https://example.test/x",
        "false_positive",
        reason="honeypot",
        note="seen twice",
        expires_at="2999-01-01T00:00:00Z",
    )
    assert store.set_disposition(
        SCOPE, "url", "https://example.test/x", "unreviewed"
    )
    record = store.get(SCOPE, "url", "https://example.test/x")
    assert record["disposition"] == "unreviewed"
    assert record["reason"] == ""
    assert record["note"] == ""
    assert record["expires_at"] is None


def test_get_many_returns_only_known_pairs(tmp_path):
    store = _store(tmp_path)
    assert store.set_disposition(SCOPE, "ipv4", "203.0.113.10", "confirmed")
    records = store.get_many(
        SCOPE,
        [("ipv4", "203.0.113.10"), ("ipv4", "198.51.100.7"), (" ipv4 ", " 203.0.113.10 ")]
    )
    assert set(records) == {("ipv4", "203.0.113.10")}


def test_list_by_disposition_filters_and_validates(tmp_path):
    store = _store(tmp_path)
    assert store.set_disposition(SCOPE, "ipv4", "203.0.113.10", "confirmed")
    assert store.set_disposition(
        SCOPE, "domain", "example.com", "false_positive", reason="noise"
    )
    confirmed = store.list_by_disposition(SCOPE, "confirmed")
    assert [r["value"] for r in confirmed] == ["203.0.113.10"]
    assert store.list_by_disposition(SCOPE, "bogus") == []


def test_counts_zero_filled_with_total(tmp_path):
    store = _store(tmp_path)
    assert store.counts(SCOPE) == {
        "unreviewed": 0,
        "confirmed": 0,
        "false_positive": 0,
        "acknowledged": 0,
        "total": 0,
    }
    assert store.set_disposition(SCOPE, "ipv4", "203.0.113.10", "confirmed")
    assert store.set_disposition(
        SCOPE, "domain", "example.com", "false_positive", reason="noise"
    )
    counts = store.counts(SCOPE)
    assert counts["confirmed"] == 1
    assert counts["false_positive"] == 1
    assert counts["acknowledged"] == 0
    assert counts["total"] == 2
    assert set(DISPOSITIONS) <= set(counts)


@pytest.mark.parametrize("disposition", DISPOSITIONS)
def test_every_disposition_roundtrips(tmp_path, disposition):
    store = _store(tmp_path)
    reason = "why" if disposition == "false_positive" else ""
    assert store.set_disposition(
        SCOPE, "ipv4", "203.0.113.10", disposition, reason=reason
    )
    assert store.get(SCOPE, "ipv4", "203.0.113.10")["disposition"] == disposition


def test_expired_decisions_are_inactive_in_every_read_api(tmp_path):
    store = _store(tmp_path)
    assert store.set_disposition(
        SCOPE,
        "domain",
        "old.example",
        "false_positive",
        reason="Old lab host",
        expires_at="2000-01-01T00:00:00Z",
    )

    assert store.get(SCOPE, "domain", "old.example") is None
    assert store.get_many(SCOPE, [("domain", "old.example")]) == {}
    assert store.list_all(SCOPE) == []
    assert store.list_by_disposition(SCOPE, "false_positive") == []
    assert store.counts(SCOPE)["total"] == 0


def test_invalid_review_timestamp_is_rejected(tmp_path):
    store = _store(tmp_path)
    assert (
        store.set_disposition(
            SCOPE,
            "domain",
            "example.com",
            "confirmed",
            expires_at="next Tuesday",
        )
        is False
    )


def test_legacy_schema_migrates_to_isolated_scope(tmp_path):
    db_path = tmp_path / "review.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE ioc_reviews (
            ioc_type TEXT NOT NULL,
            value TEXT NOT NULL,
            disposition TEXT NOT NULL,
            reason TEXT NOT NULL,
            note TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (ioc_type, value)
        )
        """
    )
    conn.execute(
        "INSERT INTO ioc_reviews VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "domain",
            "legacy.example",
            "false_positive",
            "Old test host",
            "",
            "2026-01-01T00:00:00Z",
            "2026-01-02T00:00:00Z",
        ),
    )
    conn.commit()
    conn.close()

    store = ReviewStore(db_path)
    assert store.get(SCOPE, "domain", "legacy.example") is None
    migrated = store.get(LEGACY_SCOPE, "domain", "legacy.example")
    assert migrated is not None
    assert migrated["source"] == "legacy_migration"
    primary_key = store._conn.execute("PRAGMA table_info(ioc_reviews)").fetchall()
    assert [row["name"] for row in primary_key if row["pk"]] == [
        "scope",
        "ioc_type",
        "value",
    ]
