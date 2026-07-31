"""Tests for the review-memory read models."""

from datetime import datetime, timezone

from app.review.memory import annotate, memory_context, summarize

SCOPE = "incident/acme-42"
NOW = datetime(2026, 7, 31, 10, 0, tzinfo=timezone.utc)


def _record(
    disposition,
    value,
    *,
    scope=SCOPE,
    reason="",
    note="",
    expires_at=None,
    updated_at="2026-07-31T10:00:00Z",
):
    return {
        "scope": scope,
        "ioc_type": "ipv4",
        "value": value,
        "disposition": disposition,
        "reason": reason,
        "note": note,
        "author": "analyst@example.test",
        "source": "manual",
        "expires_at": expires_at,
        "created_at": "2026-07-30T10:00:00Z",
        "updated_at": updated_at,
    }


def test_summarize_zero_filled_with_total():
    assert summarize([], scope=SCOPE, as_of=NOW) == {
        "unreviewed": 0,
        "confirmed": 0,
        "false_positive": 0,
        "acknowledged": 0,
        "total": 0,
    }
    records = [
        _record("confirmed", "203.0.113.10"),
        _record("false_positive", "203.0.113.11", reason="noise"),
        _record("unreviewed", "203.0.113.12"),
    ]
    counts = summarize(records, scope=SCOPE, as_of=NOW)
    assert counts["confirmed"] == 1
    assert counts["false_positive"] == 1
    assert counts["unreviewed"] == 1
    assert counts["total"] == 3


def test_memory_context_empty_without_decisions():
    assert memory_context([], scope=SCOPE, as_of=NOW) == ""
    assert (
        memory_context(
            [_record("unreviewed", "203.0.113.12")], scope=SCOPE, as_of=NOW
        )
        == ""
    )


def test_memory_context_sections_in_priority_order():
    records = [
        _record("confirmed", "203.0.113.10", note="C2 in the ACME incident"),
        _record("false_positive", "203.0.113.11", reason="internal resolver"),
        _record("acknowledged", "203.0.113.12", note="accepted until Q3"),
    ]
    context = memory_context(records, scope=SCOPE, as_of=NOW)
    assert context.startswith(f"# Analyst review memory for scope: {SCOPE}\n")
    fp = context.index("## Known false positives")
    confirmed = context.index("## Confirmed indicators")
    ack = context.index("## Acknowledged indicators")
    assert fp < confirmed < ack
    assert "- ipv4:203.0.113.11 — internal resolver" in context
    assert "- ipv4:203.0.113.10 — C2 in the ACME incident" in context


def test_memory_context_newest_first_inside_a_section():
    records = [
        _record("confirmed", "203.0.113.10", updated_at="2026-07-30T09:00:00Z"),
        _record("confirmed", "203.0.113.11", updated_at="2026-07-31T09:00:00Z"),
    ]
    context = memory_context(records, scope=SCOPE, as_of=NOW)
    assert context.index("203.0.113.11") < context.index("203.0.113.10")


def test_memory_context_cap_prefers_false_positives():
    records = [
        _record("confirmed", "203.0.113.10"),
        _record("confirmed", "203.0.113.11"),
        _record("false_positive", "203.0.113.12", reason="noise"),
    ]
    context = memory_context(records, scope=SCOPE, max_entries=1, as_of=NOW)
    assert "203.0.113.12" in context
    assert "203.0.113.10" not in context


def test_memory_context_line_falls_back_to_note_then_bare_label():
    records = [
        _record("confirmed", "203.0.113.10", note="watch this"),
        _record("confirmed", "203.0.113.11"),
    ]
    context = memory_context(records, scope=SCOPE, as_of=NOW)
    assert "- ipv4:203.0.113.10 — watch this" in context
    assert "- ipv4:203.0.113.11\n" in context + "\n"


def test_annotate_attaches_only_decided_reviews():
    items = [
        {"type": "ipv4", "value": "203.0.113.10", "verdict": "malicious"},
        {"type": "ipv4", "value": "203.0.113.11", "verdict": "clean"},
        {"type": "ipv4", "value": "203.0.113.12", "verdict": "unknown"},
    ]
    records = [
        _record("false_positive", "203.0.113.11", reason="internal resolver"),
        _record("unreviewed", "203.0.113.12"),
    ]
    out = annotate(items, records, scope=SCOPE, as_of=NOW)
    assert "review" not in out[0]
    assert out[1]["review"]["disposition"] == "false_positive"
    assert out[1]["review"]["reason"] == "internal resolver"
    assert out[1]["review"]["scope"] == SCOPE
    assert out[1]["review"]["author"] == "analyst@example.test"
    assert "review" not in out[2]


def test_annotate_does_not_mutate_inputs():
    item = {"type": "ipv4", "value": "203.0.113.11"}
    out = annotate(
        [item], [_record("confirmed", "203.0.113.11")], scope=SCOPE, as_of=NOW
    )
    assert item == {"type": "ipv4", "value": "203.0.113.11"}
    assert out[0] is not item


def test_annotate_trims_keys_like_the_store():
    items = [{"type": " ipv4 ", "value": " 203.0.113.11 "}]
    out = annotate(
        items, [_record("confirmed", "203.0.113.11")], scope=SCOPE, as_of=NOW
    )
    assert out[0]["review"]["disposition"] == "confirmed"


def test_memory_apis_ignore_records_from_other_scopes():
    records = [
        _record(
            "false_positive",
            "203.0.113.11",
            scope="incident/other",
            reason="Owned host elsewhere",
        )
    ]
    item = {"type": "ipv4", "value": "203.0.113.11"}

    assert summarize(records, scope=SCOPE, as_of=NOW)["total"] == 0
    assert memory_context(records, scope=SCOPE, as_of=NOW) == ""
    assert annotate([item], records, scope=SCOPE, as_of=NOW) == [item]


def test_expired_decisions_are_not_memory_or_annotations():
    expired = _record(
        "false_positive",
        "203.0.113.11",
        reason="Old lab host",
        expires_at="2026-07-31T09:59:59Z",
    )
    item = {"type": "ipv4", "value": "203.0.113.11"}

    assert summarize([expired], scope=SCOPE, as_of=NOW)["total"] == 0
    assert memory_context([expired], scope=SCOPE, as_of=NOW) == ""
    assert annotate([item], [expired], scope=SCOPE, as_of=NOW) == [item]


def test_expiry_uses_the_timestamp_offset_not_text_order():
    expired = _record(
        "false_positive",
        "203.0.113.11",
        reason="Old lab host",
        expires_at="2026-07-31T18:59:59+09:00",
    )

    assert summarize([expired], scope=SCOPE, as_of=NOW)["total"] == 0
