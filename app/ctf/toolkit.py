"""Offline crypto/forensics helper toolkit for CTF work.

Pure-stdlib, no network, no subprocess: encoding decoders, classical cipher
helpers, hash identification/computation, strings extraction, and file
signature sniffing. All functions return plain dicts/lists for templates.
"""
from __future__ import annotations

import base64
import binascii
import codecs
import hashlib
import itertools
import string
import urllib.parse

MAX_INPUT_CHARS = 512 * 1024
MAX_FILE_BYTES = 4 * 1024 * 1024
XOR_SCORE_MAX_BYTES = 64 * 1024

_PRINTABLE = set(string.printable)

_TOOLS = (
    "auto-decode",
    "base64",
    "base32",
    "hex",
    "url",
    "rot13",
    "caesar-brute",
    "xor-brute",
    "hash-identify",
    "hash-compute",
    "vigenere",
    "strings",
    "cyclic",
    "cyclic-offset",
    "pack",
)
TOOLS = _TOOLS

_HASH_BY_HEX_LENGTH = {
    32: ["md5", "ntlm", "md4"],
    40: ["sha1", "ripemd160"],
    56: ["sha224"],
    64: ["sha256", "sha3-256", "blake2s"],
    96: ["sha384"],
    128: ["sha512", "sha3-512", "blake2b", "whirlpool"],
}

_HASH_ALGOS = ("md5", "sha1", "sha224", "sha256", "sha384", "sha512")

_MAGIC_SIGNATURES = (
    (b"\x89PNG\r\n\x1a\n", "PNG image"),
    (b"\xff\xd8\xff", "JPEG image"),
    (b"GIF87a", "GIF image"),
    (b"GIF89a", "GIF image"),
    (b"%PDF", "PDF document"),
    (b"PK\x03\x04", "ZIP archive (or Office/JAR/APK)"),
    (b"Rar!\x1a\x07", "RAR archive"),
    (b"\x7fELF", "ELF executable"),
    (b"MZ", "Windows PE executable"),
    (b"\x1f\x8b", "gzip compressed data"),
    (b"BZh", "bzip2 compressed data"),
    (b"\xfd7zXZ\x00", "XZ compressed data"),
    (b"7z\xbc\xaf\x27\x1c", "7-Zip archive"),
    (b"SQLite format 3\x00", "SQLite database"),
    (b"\x00\x00\x00\x18ftyp", "MP4/MOV media"),
    (b"ID3", "MP3 audio (ID3)"),
    (b"OggS", "Ogg media"),
    (b"RIFF", "RIFF container (WAV/AVI/WEBP)"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "MS Compound Document (OLE)"),
    (b"\xd4\xc3\xb2\xa1", "pcap capture (little-endian)"),
    (b"\xa1\xb2\xc3\xd4", "pcap capture (big-endian)"),
    (b"\x0a\x0d\x0d\x0a", "pcapng capture"),
)

__all__ = (
    "MAX_FILE_BYTES",
    "MAX_INPUT_CHARS",
    "TOOLS",
    "auto_decode",
    "caesar_brute",
    "compute_hashes",
    "cyclic",
    "cyclic_offset",
    "decode_text",
    "extract_strings",
    "identify_file",
    "identify_hash",
    "pack",
    "vigenere",
    "xor_brute",
)


def _as_printable(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace")
    return "".join(ch if ch in _PRINTABLE or ch.isprintable() else "�" for ch in text)


def decode_text(text: str, encoding: str) -> str:
    """Decode *text* with a named encoding. Raises ValueError on failure."""
    raw = text.strip()
    if encoding == "base64":
        return _as_printable(base64.b64decode(raw, validate=True))
    if encoding == "base32":
        return _as_printable(base64.b32decode(raw.upper()))
    if encoding == "hex":
        return _as_printable(binascii.unhexlify("".join(raw.split())))
    if encoding == "url":
        return urllib.parse.unquote(raw)
    if encoding == "rot13":
        return codecs.decode(raw, "rot_13")
    raise ValueError(f"unsupported encoding: {encoding}")


def auto_decode(text: str) -> list[dict]:
    """Try every decoder and report the ones that succeed."""
    results = []
    for encoding in ("base64", "base32", "hex", "url", "rot13"):
        try:
            output = decode_text(text, encoding)
        except (ValueError, binascii.Error):
            continue
        if output and output != text.strip():
            results.append({"encoding": encoding, "output": output})
    return results


def caesar_brute(text: str) -> list[dict]:
    """Return all 25 non-identity Caesar shifts of *text*."""
    results = []
    for shift in range(1, 26):
        out_chars = []
        for ch in text:
            if "a" <= ch <= "z":
                out_chars.append(chr((ord(ch) - ord("a") + shift) % 26 + ord("a")))
            elif "A" <= ch <= "Z":
                out_chars.append(chr((ord(ch) - ord("A") + shift) % 26 + ord("A")))
            else:
                out_chars.append(ch)
        results.append({"shift": shift, "output": "".join(out_chars)})
    return results


def _printable_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    printable = sum(1 for b in data if chr(b) in _PRINTABLE)
    return printable / len(data)


_COMMON_CHARS = frozenset(" etaoinshrdluETAOINSHRDLU")


def _english_score(data: bytes) -> float:
    """Rank decodes: printable ratio with a common-character tiebreak bonus."""
    if not data:
        return 0.0
    ratio = _printable_ratio(data)
    common = sum(1 for b in data if chr(b) in _COMMON_CHARS) / len(data)
    return ratio + 0.5 * common


def xor_brute(text: str, limit: int = 10) -> list[dict]:
    """Single-byte XOR brute force ranked by printable ratio.

    Accepts hex input when it parses as hex, otherwise raw text bytes.
    """
    cleaned = "".join(text.strip().split())
    try:
        data = binascii.unhexlify(cleaned) if len(cleaned) % 2 == 0 else b""
    except (binascii.Error, ValueError):
        data = b""
    if not data:
        data = text.encode("utf-8", errors="replace")
    score_data = data[:XOR_SCORE_MAX_BYTES]
    scores = []
    for key in range(1, 256):
        decoded = bytes(byte ^ key for byte in score_data)
        scores.append((_english_score(decoded), key))
    scores.sort(key=lambda item: item[0], reverse=True)

    # Keep only scores during the sweep. Retaining every decoded candidate would
    # amplify a 512 KB request into about 127 MB of resident byte strings.
    return [
        {
            "key": f"0x{key:02x}",
            "score": round(score, 3),
            "output": _as_printable(bytes(byte ^ key for byte in data[:400])),
        }
        for score, key in scores[: max(0, limit)]
        if score > 0
    ]


def identify_hash(value: str) -> dict:
    """Best-effort hash algorithm identification by format."""
    candidate = value.strip()
    lower = candidate.lower()
    if lower.startswith(("$2a$", "$2b$", "$2y$")):
        return {"input_length": len(candidate), "candidates": ["bcrypt"]}
    if lower.startswith("$6$"):
        return {"input_length": len(candidate), "candidates": ["sha512crypt"]}
    if lower.startswith("$5$"):
        return {"input_length": len(candidate), "candidates": ["sha256crypt"]}
    if lower.startswith("$1$"):
        return {"input_length": len(candidate), "candidates": ["md5crypt"]}
    if lower.startswith("$argon2"):
        return {"input_length": len(candidate), "candidates": ["argon2"]}
    if candidate and all(ch in string.hexdigits for ch in candidate):
        return {
            "input_length": len(candidate),
            "candidates": _HASH_BY_HEX_LENGTH.get(len(candidate), ["unknown hex digest"]),
        }
    return {"input_length": len(candidate), "candidates": ["unrecognized format"]}


def compute_hashes(text: str) -> list[dict]:
    """Compute the common digest family for *text*."""
    data = text.encode("utf-8")
    return [
        {"algorithm": algo, "digest": hashlib.new(algo, data).hexdigest()}
        for algo in _HASH_ALGOS
    ]


def vigenere(text: str, key: str, mode: str = "decode") -> str:
    """Vigenere encode/decode over A-Z letters; other characters pass through."""
    shifts = [ord(ch.lower()) - ord("a") for ch in key if ch.isalpha()]
    if not shifts:
        raise ValueError("key must contain at least one letter")
    out_chars = []
    position = 0
    for ch in text:
        if not ch.isalpha():
            out_chars.append(ch)
            continue
        base = ord("a") if ch.islower() else ord("A")
        shift = shifts[position % len(shifts)]
        if mode == "decode":
            shift = -shift
        out_chars.append(chr((ord(ch) - base + shift) % 26 + base))
        position += 1
    return "".join(out_chars)


def extract_strings(data: bytes, min_length: int = 4, limit: int = 500) -> list[str]:
    """Extract printable ASCII/UTF-8 runs of at least *min_length* characters."""
    results: list[str] = []
    current = bytearray()
    for byte in data:
        if 0x20 <= byte < 0x7F or byte in (0x09,):
            current.append(byte)
        else:
            if len(current) >= min_length:
                results.append(current.decode("ascii"))
                if len(results) >= limit:
                    return results
            current = bytearray()
    if len(current) >= min_length and len(results) < limit:
        results.append(current.decode("ascii"))
    return results


def identify_file(data: bytes) -> dict:
    """Sniff a file signature and report size + sha256."""
    kind = "unknown"
    for signature, label in _MAGIC_SIGNATURES:
        if data.startswith(signature):
            kind = label
            break
    else:
        if data.strip() and _printable_ratio(data[:4096]) > 0.95:
            kind = "plain text"
    return {
        "kind": kind,
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


_CYCLIC_ALPHABETS = (string.ascii_lowercase, string.ascii_lowercase, string.digits)
CYCLIC_MAX_LENGTH = 10000


def cyclic(length: int = 200) -> str:
    """Generate a De Bruijn-style cyclic pattern (unique 3-char substrings).

    Same construction as pwntools' default cyclic(): triples over
    [a-z][a-z][0-9], so any 3-byte window appears at exactly one offset.
    """
    if length < 1 or length > CYCLIC_MAX_LENGTH:
        raise ValueError(f"length must be 1..{CYCLIC_MAX_LENGTH}")
    pattern = "".join(
        "".join(triple)
        for triple in itertools.product(*_CYCLIC_ALPHABETS)
    )
    return pattern[:length]


def cyclic_offset(needle: str) -> int:
    """Return the offset of a 3+ char (or hex-encoded little-endian) needle."""
    candidate = needle.strip()
    if candidate.lower().startswith("0x"):
        try:
            raw = binascii.unhexlify(candidate[2:])
        except (binascii.Error, ValueError):
            raise ValueError("Invalid hex needle.") from None
        candidate = raw[::-1].decode("ascii", errors="replace")
    if len(candidate) < 3:
        raise ValueError("Needle must be at least 3 characters (or 0x-prefixed hex).")
    haystack = cyclic(CYCLIC_MAX_LENGTH)
    offset = haystack.find(candidate[:3])
    if offset < 0:
        raise ValueError("Needle not found in the cyclic pattern.")
    return offset


def pack(value: str) -> dict:
    """Pack an integer as little-endian bytes (p32/p64-style).

    Accepts decimal or 0x-hex with an optional ``:32``/``:64`` width suffix.
    """
    text = value.strip()
    width = 0
    if ":" in text:
        text, _, suffix = text.rpartition(":")
        if suffix in ("32", "64"):
            width = int(suffix)
    try:
        number = int(text, 0)
    except ValueError:
        raise ValueError("Value must be an integer (decimal or 0x-hex).") from None
    if number < 0:
        raise ValueError("Value must be non-negative.")
    if width == 0:
        width = 32 if number <= 0xFFFFFFFF else 64
    size = width // 8
    if number >= 1 << (size * 8):
        raise ValueError(f"Value does not fit in {width} bits.")
    raw = number.to_bytes(size, "little")
    return {
        "width": width,
        "escaped": "".join(f"\\x{byte:02x}" for byte in raw),
        "hex": raw.hex(),
    }
