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
    EMAIL = "email"


IOC_TYPE_VALUES = (
    IOCType.IPV4.value,
    IOCType.IPV6.value,
    IOCType.DOMAIN.value,
    IOCType.URL.value,
    IOCType.MD5.value,
    IOCType.SHA1.value,
    IOCType.SHA256.value,
    IOCType.CVE.value,
    IOCType.EMAIL.value,
)


@dataclass(frozen=True, slots=True)
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
    ioc_count = len(iocs)
    if ioc_count == 0:
        return {}
    if ioc_count == 1:
        ioc = iocs[0]
        return {ioc.type: [ioc]}
    if ioc_count == 2:
        first = iocs[0]
        second = iocs[1]
        if first.type == second.type:
            return {first.type: [first, second]}
        return {first.type: [first], second.type: [second]}
    if ioc_count == 3:
        first = iocs[0]
        second = iocs[1]
        third = iocs[2]
        if first.type == second.type == third.type:
            return {first.type: [first, second, third]}
        result: dict[IOCType, list[IOC]] = {}
        append_ioc_by_type(result, first)
        append_ioc_by_type(result, second)
        append_ioc_by_type(result, third)
        return result
    if ioc_count == 4:
        first = iocs[0]
        second = iocs[1]
        third = iocs[2]
        fourth = iocs[3]
        if first.type == second.type == third.type == fourth.type:
            return {first.type: [first, second, third, fourth]}
        result: dict[IOCType, list[IOC]] = {}
        append_ioc_by_type(result, first)
        append_ioc_by_type(result, second)
        append_ioc_by_type(result, third)
        append_ioc_by_type(result, fourth)
        return result

    result: dict[IOCType, list[IOC]] = {}
    for ioc in iocs:
        append_ioc_by_type(result, ioc)
    return result


def append_ioc_by_type(grouped: dict[IOCType, list[IOC]], ioc: IOC) -> None:
    """Append an IOC to a type grouping without setdefault's eager list allocation."""
    group = grouped.get(ioc.type)
    if group is None:
        group = []
        grouped[ioc.type] = group
    group.append(ioc)
