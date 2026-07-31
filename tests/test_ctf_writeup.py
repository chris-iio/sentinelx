"""Tests for writeup export and hint checklists."""
from app.ctf.hints import hints_for
from app.ctf.writeup import challenge_writeup, event_writeup


def test_hints_cover_all_categories():
    from app.ctf.store import CATEGORIES

    for category in CATEGORIES:
        assert hints_for(category), category


def test_challenge_writeup_structure():
    body = challenge_writeup(
        {"name": "CA26"},
        {
            "name": "Signal",
            "category": "web",
            "difficulty": "easy",
            "points": 300,
            "status": "solved",
            "description": "inspect the beacon",
        },
        [{"body": "tried sqli", "created_at": "2026-03-20T10:00:00Z"}],
        [{"flag": "HTB{x}", "source": "note", "created_at": "2026-03-20T10:05:00Z"}],
        [
            {
                "profile": "nmap-quick",
                "argv": ["/usr/bin/nmap", "-sV", "10.10.11.42"],
                "exit_code": 0,
                "output": "80/tcp open http",
                "error": "",
                "created_at": "2026-03-20T09:00:00Z",
            }
        ],
    )
    assert body.startswith("# Signal")
    assert "HTB{x}" in body
    assert "tried sqli" in body
    assert "80/tcp open http" in body
    assert "nmap-quick" in body


def test_challenge_writeup_fence_escapes_backticks():
    body = challenge_writeup(
        None,
        {
            "name": "X",
            "category": "misc",
            "difficulty": "easy",
            "points": 0,
            "status": "open",
            "description": "",
        },
        [{"body": "payload: ```evil```", "created_at": "2026-03-20T10:00:00Z"}],
        [],
        [],
    )
    assert "````\npayload: ```evil```\n````" in body


def test_event_writeup_header():
    body = event_writeup(
        {"name": "CA26", "url": "https://example.com"},
        ["# Chall\n\nbody"],
        {"solved": 1, "total": 2, "points": 300},
    )
    assert "# CA26 — writeup" in body
    assert "Solved: 1/2" in body
    assert "# Chall" in body


def test_challenge_writeup_route(client):
    response = client.post("/ctf/events", data={"name": "CA26", "url": ""})
    event_id = response.headers["Location"].rsplit("/", 1)[-1]
    response = client.post(
        f"/ctf/events/{event_id}/challenges",
        data={"name": "Signal", "category": "web", "difficulty": "easy",
              "points": "300", "description": ""},
    )
    challenge_id = response.headers["Location"].rsplit("/", 1)[-1]
    response = client.get(f"/ctf/challenges/{challenge_id}/writeup.md")
    assert response.status_code == 200
    assert response.mimetype == "text/markdown"
    assert b"# Signal" in response.data
    assert "attachment" in response.headers["Content-Disposition"]


def test_event_writeup_route(client):
    response = client.post("/ctf/events", data={"name": "CA26", "url": ""})
    event_id = response.headers["Location"].rsplit("/", 1)[-1]
    response = client.get(f"/ctf/events/{event_id}/writeup.md")
    assert response.status_code == 200
    assert b"# CA26" in response.data


def test_writeup_404(client):
    assert client.get("/ctf/challenges/missing/writeup.md").status_code == 404
    assert client.get("/ctf/events/missing/writeup.md").status_code == 404


def test_challenge_page_shows_hints(client):
    response = client.post("/ctf/events", data={"name": "CA26", "url": ""})
    event_id = response.headers["Location"].rsplit("/", 1)[-1]
    response = client.post(
        f"/ctf/events/{event_id}/challenges",
        data={"name": "Webby", "category": "web", "difficulty": "easy",
              "points": "100", "description": ""},
    )
    challenge_id = response.headers["Location"].rsplit("/", 1)[-1]
    page = client.get(f"/ctf/challenges/{challenge_id}")
    assert b"Methodology hints" in page.data
    assert b"Enumerate directories" in page.data
