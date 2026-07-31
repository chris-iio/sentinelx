"""Route tests for the CTF workspace surfaces."""


def _create_event(client, name="Cyber Apocalypse 2026"):
    response = client.post("/ctf/events", data={"name": name, "url": ""})
    assert response.status_code == 302
    return response.headers["Location"].rsplit("/", 1)[-1]


def _create_challenge(client, event_id, name="Signal From Beyond", category="web"):
    response = client.post(
        f"/ctf/events/{event_id}/challenges",
        data={
            "name": name,
            "category": category,
            "difficulty": "easy",
            "points": "300",
            "description": "inspect the beacon",
        },
    )
    assert response.status_code == 302
    return response.headers["Location"].rsplit("/", 1)[-1]


def test_events_list_page(client):
    response = client.get("/ctf")
    assert response.status_code == 200
    assert b"CTF Events" in response.data


def test_create_event_and_detail(client):
    event_id = _create_event(client)
    response = client.get(f"/ctf/events/{event_id}")
    assert response.status_code == 200
    assert b"Cyber Apocalypse 2026" in response.data


def test_create_event_requires_name(client):
    response = client.post("/ctf/events", data={"name": "  ", "url": ""})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/ctf")


def test_create_event_rejects_non_http_url(client):
    response = client.post(
        "/ctf/events", data={"name": "CA26", "url": "javascript:alert(1)"}
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/ctf")


def test_event_detail_404(client):
    assert client.get("/ctf/events/missing").status_code == 404


def test_create_challenge_and_detail(client):
    event_id = _create_event(client)
    challenge_id = _create_challenge(client, event_id)
    response = client.get(f"/ctf/challenges/{challenge_id}")
    assert response.status_code == 200
    assert b"Signal From Beyond" in response.data
    assert b"inspect the beacon" in response.data


def test_create_challenge_rejects_bad_category(client):
    event_id = _create_event(client)
    response = client.post(
        f"/ctf/events/{event_id}/challenges",
        data={"name": "X", "category": "nope", "difficulty": "easy", "points": "1"},
    )
    assert response.status_code == 302
    assert f"/ctf/events/{event_id}" in response.headers["Location"]
    assert b"No challenges yet" in client.get(f"/ctf/events/{event_id}").data


def test_create_challenge_rejects_bad_points(client):
    event_id = _create_event(client)
    response = client.post(
        f"/ctf/events/{event_id}/challenges",
        data={"name": "X", "category": "web", "difficulty": "easy", "points": "abc"},
    )
    assert response.status_code == 302
    assert f"/ctf/events/{event_id}" in response.headers["Location"]


def test_challenge_detail_404(client):
    assert client.get("/ctf/challenges/missing").status_code == 404


def test_add_note_auto_captures_flag(client):
    event_id = _create_event(client)
    challenge_id = _create_challenge(client, event_id)
    response = client.post(
        f"/ctf/challenges/{challenge_id}/notes",
        data={"body": "decoded it: HTB{r0ut3_t3st_fl4g}"},
    )
    assert response.status_code == 302
    page = client.get(f"/ctf/challenges/{challenge_id}")
    assert b"HTB{r0ut3_t3st_fl4g}" in page.data
    assert b"decoded it" in page.data


def test_add_note_requires_body(client):
    event_id = _create_event(client)
    challenge_id = _create_challenge(client, event_id)
    response = client.post(
        f"/ctf/challenges/{challenge_id}/notes", data={"body": "   "}
    )
    assert response.status_code == 302
    page = client.get(f"/ctf/challenges/{challenge_id}")
    assert b"No flags captured yet" in page.data


def test_submit_flag_marks_solved(client):
    event_id = _create_event(client)
    challenge_id = _create_challenge(client, event_id)
    response = client.post(
        f"/ctf/challenges/{challenge_id}/flags", data={"flag": "HTB{s0lv3d_it}"}
    )
    assert response.status_code == 302
    page = client.get(f"/ctf/challenges/{challenge_id}")
    assert b"HTB{s0lv3d_it}" in page.data
    assert b'ctf-badge--solved' in page.data


def test_submit_flag_rejects_malformed(client):
    event_id = _create_event(client)
    challenge_id = _create_challenge(client, event_id)
    client.post(f"/ctf/challenges/{challenge_id}/flags", data={"flag": "not-a-flag"})
    page = client.get(f"/ctf/challenges/{challenge_id}")
    assert b"not-a-flag" not in page.data
    assert b'ctf-badge--solved' not in page.data


def test_set_status(client):
    event_id = _create_event(client)
    challenge_id = _create_challenge(client, event_id)
    response = client.post(
        f"/ctf/challenges/{challenge_id}/status", data={"status": "working"}
    )
    assert response.status_code == 302
    assert b'ctf-badge--working' in client.get(
        f"/ctf/challenges/{challenge_id}"
    ).data


def test_set_status_rejects_invalid(client):
    event_id = _create_event(client)
    challenge_id = _create_challenge(client, event_id)
    response = client.post(
        f"/ctf/challenges/{challenge_id}/status", data={"status": "pwned"}
    )
    assert response.status_code == 302
    assert b'ctf-badge--open' in client.get(
        f"/ctf/challenges/{challenge_id}"
    ).data


def test_delete_challenge(client):
    event_id = _create_event(client)
    challenge_id = _create_challenge(client, event_id)
    response = client.post(f"/ctf/challenges/{challenge_id}/delete")
    assert response.status_code == 302
    assert client.get(f"/ctf/challenges/{challenge_id}").status_code == 404


def test_delete_event(client):
    event_id = _create_event(client)
    response = client.post(f"/ctf/events/{event_id}/delete")
    assert response.status_code == 302
    assert client.get(f"/ctf/events/{event_id}").status_code == 404


def test_run_profile_records_output(client, monkeypatch):
    from app.ctf import runner

    class FakeResult:
        argv = ["/usr/bin/nmap", "-sV", "10.10.11.42"]
        exit_code = 0
        output = "80/tcp open http HTB{nmap_run_flag}"
        error = ""
        flags = ["HTB{nmap_run_flag}"]

    monkeypatch.setattr(runner, "run_profile", lambda *a, **k: FakeResult())
    event_id = _create_event(client)
    challenge_id = _create_challenge(client, event_id)
    response = client.post(
        f"/ctf/challenges/{challenge_id}/runs",
        data={"profile": "nmap-quick", "target": "10.10.11.42", "wordlist": ""},
    )
    assert response.status_code == 302
    page = client.get(f"/ctf/challenges/{challenge_id}")
    assert b"nmap-quick" in page.data
    assert b"80/tcp open http" in page.data
    assert b"HTB{nmap_run_flag}" in page.data


def test_run_profile_invalid_target_flashes(client):
    event_id = _create_event(client)
    challenge_id = _create_challenge(client, event_id)
    response = client.post(
        f"/ctf/challenges/{challenge_id}/runs",
        data={"profile": "nmap-quick", "target": "bad;target", "wordlist": ""},
    )
    assert response.status_code == 302
    page = client.get(f"/ctf/challenges/{challenge_id}")
    assert b"bad;target" not in page.data
