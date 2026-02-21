"""IOC classifier — deterministic type detection from normalized strings.

Classifies a normalized IOC string into one of eight IOCType values using
compiled regex patterns in strict precedence order. Returns an IOC dataclass
or None if the string cannot be classified.

Security:
- Pure function: no side effects, no network calls
- Strict precedence order prevents ambiguous classification
- ipaddress module used for IP validation (rejects invalid octets)
"""
from __future__ import annotations

import ipaddress
import re

from app.pipeline.models import IOC, IOCType

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

# Domain: hostname chars with at least one dot and a valid-looking TLD
# Rejects bare labels (no dot) and localhost
_RE_DOMAIN = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)"
    r"+[a-zA-Z]{2,}$"
)
# Domains to reject explicitly
_DOMAIN_BLACKLIST = {"localhost"}


def _is_valid_ipv4(value: str) -> bool:
    """Return True if value is a syntactically valid IPv4 address."""
    try:
        addr = ipaddress.ip_address(value)
        return addr.version == 4
    except ValueError:
        return False


def _is_valid_ipv6(value: str) -> bool:
    """Return True if value is a syntactically valid IPv6 address."""
    try:
        addr = ipaddress.ip_address(value)
        return addr.version == 6
    except ValueError:
        return False


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
    8. Domain (hostname with valid TLD)

    Args:
        normalized_value: The canonical (refanged) IOC string.
        raw_match:        The original matched string from analyst input.

    Returns:
        IOC dataclass with assigned type, or None if unclassifiable.
    """
    if not normalized_value:
        return None

    v = normalized_value.strip()

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

    # 6. IPv6
    if _is_valid_ipv6(v):
        return IOC(type=IOCType.IPV6, value=v, raw_match=raw_match)

    # 7. IPv4
    if _is_valid_ipv4(v):
        return IOC(type=IOCType.IPV4, value=v, raw_match=raw_match)

    # 8. Domain
    if v.lower() not in _DOMAIN_BLACKLIST and _RE_DOMAIN.match(v):
        return IOC(type=IOCType.DOMAIN, value=v.lower(), raw_match=raw_match)

    return None
