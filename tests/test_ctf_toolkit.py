"""Unit tests for the offline CTF toolkit helpers."""
import base64

import pytest

from app.ctf import toolkit


def test_decode_base64():
    assert toolkit.decode_text("aGVsbG8=", "base64") == "hello"


def test_decode_hex():
    assert toolkit.decode_text("48656c6c6f", "hex") == "Hello"


def test_decode_url():
    assert toolkit.decode_text("hello%20world%21", "url") == "hello world!"


def test_decode_rot13():
    assert toolkit.decode_text("uryyb", "rot13") == "hello"


def test_decode_invalid_base64_raises():
    with pytest.raises(Exception):
        toolkit.decode_text("!!!not-b64!!!", "base64")


def test_auto_decode_finds_base64():
    blob = base64.b64encode(b"flag{test}").decode()
    results = toolkit.auto_decode(blob)
    assert any(item["encoding"] == "base64" and "flag{test}" in item["output"]
               for item in results)


def test_caesar_brute_recovers_plaintext():
    rows = toolkit.caesar_brute("khoor")
    assert any(row["output"] == "hello" for row in rows)
    assert len(rows) == 25


def test_xor_brute_recovers_plaintext():
    data = bytes(b ^ 0x42 for b in b"hello world, this is a test message!")
    rows = toolkit.xor_brute(data.hex())
    assert rows[0]["key"] == "0x42"
    assert "hello world" in rows[0]["output"]


def test_xor_brute_accepts_raw_text():
    rows = toolkit.xor_brute("plain input")
    assert rows


def test_xor_brute_bounds_each_scored_candidate(monkeypatch):
    scored_lengths = []

    def score(data: bytes) -> float:
        scored_lengths.append(len(data))
        return 1.0

    monkeypatch.setattr(toolkit, "_english_score", score)
    toolkit.xor_brute("a" * (toolkit.XOR_SCORE_MAX_BYTES + 1), limit=1)

    assert len(scored_lengths) == 255
    assert set(scored_lengths) == {toolkit.XOR_SCORE_MAX_BYTES}


def test_identify_hash_md5():
    result = toolkit.identify_hash("5f4dcc3b5aa765d61d8327deb882cf99")
    assert "md5" in result["candidates"]


def test_identify_hash_sha256():
    result = toolkit.identify_hash("a" * 64)
    assert "sha256" in result["candidates"]


def test_identify_hash_bcrypt():
    result = toolkit.identify_hash("$2b$12$" + "x" * 53)
    assert result["candidates"] == ["bcrypt"]


def test_identify_hash_unrecognized():
    result = toolkit.identify_hash("not a hash at all!")
    assert result["candidates"] == ["unrecognized format"]


def test_compute_hashes():
    digests = {d["algorithm"]: d["digest"] for d in toolkit.compute_hashes("password")}
    assert digests["md5"] == "5f4dcc3b5aa765d61d8327deb882cf99"
    assert digests["sha256"].startswith("5e884898")


def test_vigenere_roundtrip():
    encoded = toolkit.vigenere("attackatdawn", "lemon", mode="encode")
    assert encoded == "lxfopvefrnhr"
    assert toolkit.vigenere(encoded, "lemon", mode="decode") == "attackatdawn"


def test_vigenere_rejects_empty_key():
    with pytest.raises(ValueError):
        toolkit.vigenere("text", "123")


def test_extract_strings():
    data = b"\x00\x01hello world\x00\x02ab\x00secret_password\x00"
    strings = toolkit.extract_strings(data)
    assert "hello world" in strings
    assert "secret_password" in strings
    assert "ab" not in strings


def test_identify_file_png():
    data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    result = toolkit.identify_file(data)
    assert result["kind"] == "PNG image"
    assert result["size_bytes"] == 40
    assert len(result["sha256"]) == 64


def test_identify_file_text():
    result = toolkit.identify_file(b"just some plain ascii text\n" * 4)
    assert result["kind"] == "plain text"


def test_identify_file_unknown():
    result = toolkit.identify_file(b"\x00\x01\x02\x03\x04\x05\x06\x07")
    assert result["kind"] == "unknown"
