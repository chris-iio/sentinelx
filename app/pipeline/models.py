"""IOC data models.

Provides the typed data structures used throughout the extraction pipeline.
All models are immutable (frozen dataclass) to prevent accidental mutation.

Security:
- IOC.value contains the canonical (refanged) form — safe to display after Jinja2 escaping
- IOC.raw_match contains the original input string — always render via {{ var }}, never | safe
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IOCType(Enum):
    """Enumeration of all supported IOC types.

    Values are lowercase strings used in templates and API responses.
    """

    IPV4 = "ipv4"
    IPV6 = "ipv6"
    DOMAIN = "domain"
    URL = "url"
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    CVE = "cve"


@dataclass(frozen=True)
class IOC:
    """An immutable, typed indicator of compromise.

    Frozen dataclass ensures IOCs cannot be mutated after creation,
    making them safe to share across functions and templates.

    Attributes:
        type:       Classification of this IOC (e.g., IOCType.IPV4)
        value:      Canonical (refanged) form — used for deduplication key and display
        raw_match:  Original string from input — shown in "original" column in UI
    """

    type: IOCType
    value: str  # canonical/refanged form
    raw_match: str  # original string from analyst paste


def group_by_type(iocs: list[IOC]) -> dict[IOCType, list[IOC]]:
    """Group a list of IOCs by type for template rendering.

    Args:
        iocs: Deduplicated list of IOC objects.

    Returns:
        Dict mapping each present IOCType to its list of IOCs.
        Types with no IOCs are omitted from the result.
    """
    result: dict[IOCType, list[IOC]] = {}
    for ioc in iocs:
        result.setdefault(ioc.type, []).append(ioc)
    return result
