"""IOC classifier — deterministic type detection from normalized strings.

Classifies a normalized IOC string into one of nine IOCType values using
compiled regex patterns in strict precedence order. Returns an IOC dataclass
or None if the string cannot be classified.

Precedence order:
1. CVE
2. SHA256 (64 hex chars)
3. SHA1   (40 hex chars)
4. MD5    (32 hex chars)
5. URL    (http:// or https://)
6. IPv6   (via ipaddress validation)
7. IPv4   (via ipaddress validation)
8. Email  (user@domain.tld — checked BEFORE domain to prevent mis-classification)
9. Domain (hostname with valid TLD)

Security:
- Pure function: no side effects, no network calls
- Strict precedence order prevents ambiguous classification
- Email is checked BEFORE domain to prevent `user@evil.com` being classified as domain
- ipaddress module used for IP validation (rejects invalid octets)
"""
from __future__ import annotations

import ipaddress
import re

from app.pipeline.models import IOC, IOCType
from app.text_utils import stripped_text_or_none

# ---------------------------------------------------------------------------
# Compiled patterns — more specific patterns MUST come before general ones.
# ---------------------------------------------------------------------------

# CVE: CVE-YYYY-NNNNN+ (at least 4-digit ID)
_RE_CVE = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)

# Hashes: strictly by hex character count
_RE_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_RE_SHA1 = re.compile(r"^[0-9a-fA-F]{40}$")
_RE_MD5 = re.compile(r"^[0-9a-fA-F]{32}$")

# URL: starts with http:// or https://
_RE_URL = re.compile(r"^https?://\S+", re.IGNORECASE)

# Email: local-part@domain.tld — checked before domain to prevent mis-classification
_RE_EMAIL = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Domain: hostname chars with at least one dot and a valid-looking TLD
# Rejects bare labels (no dot) and localhost
_RE_DOMAIN = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)"
    r"+[a-zA-Z]{2,}$"
)
# Domains to reject explicitly
_DOMAIN_BLACKLIST = frozenset(("localhost",))


def _looks_like_ip_literal(value: str) -> bool:
    """Return True when value has the shape of an IPv4 or IPv6 literal."""
    if ":" in value:
        return True
    if "." not in value:
        return False
    for char in value:
        if char != "." and not char.isdecimal():
            return False
    return True


def _classify_ip_type(value: str) -> IOCType | None:
    """Return the IOC type for a syntactically valid IP address."""
    try:
        addr = ipaddress.ip_address(value)
        return IOCType.IPV4 if addr.version == 4 else IOCType.IPV6
    except ValueError:
        return None


def classify(normalized_value: str, raw_match: str) -> IOC | None:
    """Classify a normalized IOC string and return a typed IOC dataclass.

    Uses strict precedence ordering to prevent ambiguous matches:
    1. CVE
    2. SHA256 (64 hex chars)
    3. SHA1  (40 hex chars)
    4. MD5   (32 hex chars)
    5. URL   (http:// or https://)
    6. IPv6  (via ipaddress validation)
    7. IPv4  (via ipaddress validation)
    8. Email (user@domain.tld — before domain to prevent mis-classification)
    9. Domain (hostname with valid TLD)

    Args:
        normalized_value: The canonical (refanged) IOC string.
        raw_match:        The original matched string from analyst input.

    Returns:
        IOC dataclass with assigned type, or None if unclassifiable.
    """
    v = stripped_text_or_none(normalized_value)
    if v is None:
        return None

    # 1. CVE
    if _RE_CVE.match(v):
        return IOC(type=IOCType.CVE, value=v.upper(), raw_match=raw_match)

    # 2. SHA256
    if _RE_SHA256.match(v):
        return IOC(type=IOCType.SHA256, value=v.lower(), raw_match=raw_match)

    # 3. SHA1
    if _RE_SHA1.match(v):
        return IOC(type=IOCType.SHA1, value=v.lower(), raw_match=raw_match)

    # 4. MD5
    if _RE_MD5.match(v):
        return IOC(type=IOCType.MD5, value=v.lower(), raw_match=raw_match)

    # 5. URL
    if _RE_URL.match(v):
        return IOC(type=IOCType.URL, value=v, raw_match=raw_match)

    # 6-7. IP address — parse once, preserving IPv6-before-IPv4 precedence.
    if _looks_like_ip_literal(v):
        ip_type = _classify_ip_type(v)
        if ip_type is not None:
            return IOC(type=ip_type, value=v, raw_match=raw_match)

    # 8. Email — must come before domain: user@evil.com would match domain regex
    if _RE_EMAIL.match(v):
        return IOC(type=IOCType.EMAIL, value=v.lower(), raw_match=raw_match)

    # 9. Domain
    lower_v = v.lower()
    if lower_v not in _DOMAIN_BLACKLIST and _RE_DOMAIN.match(v):
        return IOC(type=IOCType.DOMAIN, value=lower_v, raw_match=raw_match)

    return None
