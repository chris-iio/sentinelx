"""Route tests for the CTF toolkit pages."""
import io


def test_toolkit_page(client):
    response = client.get("/ctf/toolkit")
    assert response.status_code == 200
    assert b"CTF Toolkit" in response.data


def test_run_base64_decode(client):
    response = client.post(
        "/ctf/toolkit/run", data={"tool": "base64", "input": "aGVsbG8="}
    )
    assert response.status_code == 200
    assert b"hello" in response.data


def test_run_auto_decode(client):
    response = client.post(
        "/ctf/toolkit/run", data={"tool": "auto-decode", "input": "aGVsbG8="}
    )
    assert response.status_code == 200
    assert b"base64" in response.data
    assert b"hello" in response.data


def test_run_caesar_brute(client):
    response = client.post(
        "/ctf/toolkit/run", data={"tool": "caesar-brute", "input": "khoor"}
    )
    assert response.status_code == 200
    assert b"hello" in response.data


def test_run_xor_brute(client):
    data = bytes(b ^ 0x23 for b in b"the quick brown fox jumps over")
    response = client.post(
        "/ctf/toolkit/run", data={"tool": "xor-brute", "input": data.hex()}
    )
    assert response.status_code == 200
    assert b"0x23" in response.data
    assert b"quick brown fox" in response.data


def test_run_hash_identify(client):
    response = client.post(
        "/ctf/toolkit/run",
        data={"tool": "hash-identify", "input": "5f4dcc3b5aa765d61d8327deb882cf99"},
    )
    assert response.status_code == 200
    assert b"md5" in response.data


def test_run_hash_compute(client):
    response = client.post(
        "/ctf/toolkit/run", data={"tool": "hash-compute", "input": "password"}
    )
    assert response.status_code == 200
    assert b"5f4dcc3b5aa765d61d8327deb882cf99" in response.data


def test_run_vigenere_decode(client):
    response = client.post(
        "/ctf/toolkit/run",
        data={
            "tool": "vigenere",
            "input": "lxfopvefrnhr",
            "key": "lemon",
            "mode": "decode",
        },
    )
    assert response.status_code == 200
    assert b"attackatdawn" in response.data


def test_run_strings(client):
    response = client.post(
        "/ctf/toolkit/run",
        data={"tool": "strings", "input": "aa hidden_flag_here bb"},
    )
    assert response.status_code == 200
    assert b"hidden_flag_here" in response.data


def test_run_rejects_unknown_tool(client):
    response = client.post(
        "/ctf/toolkit/run", data={"tool": "rm-rf", "input": "x"}
    )
    assert response.status_code == 302


def test_run_rejects_empty_input(client):
    response = client.post("/ctf/toolkit/run", data={"tool": "base64", "input": "  "})
    assert response.status_code == 302


def test_run_invalid_base64_redirects_with_flash(client):
    response = client.post(
        "/ctf/toolkit/run", data={"tool": "base64", "input": "!!!nope!!!"}
    )
    assert response.status_code == 302


def test_file_inspect(client):
    payload = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + b"some_visible_string\x00"
    response = client.post(
        "/ctf/toolkit/run",
        data={"tool": "file-inspect"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 302
    response = client.post(
        "/ctf/toolkit/run",
        data={
            "tool": "file-inspect",
            "file": (io.BytesIO(payload), "challenge.bin"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert b"PNG image" in response.data
    assert b"some_visible_string" in response.data
