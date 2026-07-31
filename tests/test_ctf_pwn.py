"""Unit tests for pwn helpers (cyclic pattern, pack)."""
import pytest

from app.ctf import toolkit


def test_cyclic_length():
    assert len(toolkit.cyclic(50)) == 50


def test_cyclic_offset_roundtrip():
    pattern = toolkit.cyclic(500)
    needle = pattern[123:126]
    assert toolkit.cyclic_offset(needle) == 123


def test_cyclic_offset_hex_needle():
    pattern = toolkit.cyclic(500)
    needle = pattern[100:104]
    little_endian_hex = "0x" + needle[::-1].encode().hex()
    assert toolkit.cyclic_offset(little_endian_hex) == 100


def test_cyclic_offset_not_found():
    with pytest.raises(ValueError):
        toolkit.cyclic_offset("ZZZ9")


def test_cyclic_rejects_bad_length():
    with pytest.raises(ValueError):
        toolkit.cyclic(0)
    with pytest.raises(ValueError):
        toolkit.cyclic(toolkit.CYCLIC_MAX_LENGTH + 1)


def test_pack_p32():
    result = toolkit.pack("0x41424344")
    assert result["width"] == 32
    assert result["escaped"] == "\\x44\\x43\\x42\\x41"
    assert result["hex"] == "44434241"


def test_pack_p64_suffix():
    result = toolkit.pack("0xdeadbeef:64")
    assert result["width"] == 64
    assert result["hex"] == "efbeadde00000000"


def test_pack_decimal():
    assert toolkit.pack("16909060")["hex"] == "04030201"


def test_pack_rejects_overflow_and_garbage():
    with pytest.raises(ValueError):
        toolkit.pack("0x1ffffffff:32")
    with pytest.raises(ValueError):
        toolkit.pack("not-a-number")
    with pytest.raises(ValueError):
        toolkit.pack("-1")
