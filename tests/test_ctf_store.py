"""Unit tests for the CTF workspace SQLite store."""
import pytest

from app.ctf.store import CtfStore


@pytest.fixture()
def store(tmp_path):
    return CtfStore(tmp_path / "ctf.db")


def _make_challenge(store, event_name="Cyber Apocalypse 2026"):
    event_id = store.create_event(event_name, "https://www.hackthebox.com/")
    challenge_id = store.create_challenge(
        event_id, "Signal From Beyond", "web", "easy", 300, "inspect the beacon"
    )
    return event_id, challenge_id


def test_event_lifecycle(store):
    event_id = store.create_event("CA26", "https://example.com")
    events = store.list_events()
    assert [e["id"] for e in events] == [event_id]
    assert events[0]["challenge_count"] == 0
    assert store.get_event(event_id)["name"] == "CA26"
    assert store.delete_event(event_id) is True
    assert store.get_event(event_id) is None


def test_event_url_defaults_empty(store):
    event_id = store.create_event("CA26")
    assert store.get_event(event_id)["url"] == ""


def test_challenge_lifecycle(store):
    event_id, challenge_id = _make_challenge(store)
    challenges = store.list_challenges(event_id)
    assert len(challenges) == 1
    assert challenges[0]["status"] == "open"
    assert challenges[0]["points"] == 300

    assert store.set_challenge_status(challenge_id, "working") is True
    assert store.get_challenge(challenge_id)["status"] == "working"

    assert store.delete_challenge(challenge_id) is True
    assert store.get_challenge(challenge_id) is None


def test_delete_event_cascades_challenges(store):
    event_id, challenge_id = _make_challenge(store)
    store.add_note(challenge_id, "found HTB{cascade_test}")
    store.delete_event(event_id)
    assert store.get_challenge(challenge_id) is None
    assert store.list_notes(challenge_id) == []
    assert store.list_flags(challenge_id) == []


def test_note_auto_captures_flags(store):
    _, challenge_id = _make_challenge(store)
    note_id, detected = store.add_note(
        challenge_id, "decoded the payload: HTB{n0t_s0_h1dd3n} nice"
    )
    assert note_id
    assert detected == ["HTB{n0t_s0_h1dd3n}"]
    flags = store.list_flags(challenge_id)
    assert [f["flag"] for f in flags] == ["HTB{n0t_s0_h1dd3n}"]
    assert flags[0]["source"] == "note"


def test_note_without_flags_captures_nothing(store):
    _, challenge_id = _make_challenge(store)
    _, detected = store.add_note(challenge_id, "just a plain note")
    assert detected == []
    assert store.list_flags(challenge_id) == []


def test_flag_dedupe(store):
    _, challenge_id = _make_challenge(store)
    assert store.add_flag(challenge_id, "HTB{dup}") is True
    assert store.add_flag(challenge_id, "HTB{dup}") is False
    assert len(store.list_flags(challenge_id)) == 1


def test_event_stats(store):
    event_id, challenge_id = _make_challenge(store)
    other_id = store.create_challenge(event_id, "Looney Tunes", "pwn", "medium", 400)
    assert store.event_stats(event_id) == {"total": 2, "solved": 0, "points": 0}
    store.set_challenge_status(challenge_id, "solved")
    assert store.event_stats(event_id) == {"total": 2, "solved": 1, "points": 300}
    store.set_challenge_status(other_id, "solved")
    assert store.event_stats(event_id) == {"total": 2, "solved": 2, "points": 700}


def test_missing_rows(store):
    assert store.get_event("nope") is None
    assert store.get_challenge("nope") is None
    assert store.delete_event("nope") is False
    assert store.delete_challenge("nope") is False
    assert store.set_challenge_status("nope", "solved") is False
