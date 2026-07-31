"""Unit tests for CTF flag detection."""
from app.ctf.flags import detect_flags


def test_detects_htb_style_flag():
    assert detect_flags("the answer is HTB{cyb3r_apoc_2026}") == ["HTB{cyb3r_apoc_2026}"]


def test_detects_multiple_and_dedupes():
    text = "HTB{one} then CTF{two} and again HTB{one}"
    assert detect_flags(text) == ["HTB{one}", "CTF{two}"]


def test_ignores_text_without_flags():
    assert detect_flags("no flags here, just braces { } and code") == []


def test_empty_input():
    assert detect_flags("") == []


def test_rejects_whitespace_inside_braces():
    assert detect_flags("HTB{not a flag}") == []


def test_allows_common_flag_charsets():
    flags = detect_flags("flag{Th1s_1s.a-fake_fl4g!$%}")
    assert flags == ["flag{Th1s_1s.a-fake_fl4g!$%}"]
