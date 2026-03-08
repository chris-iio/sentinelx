"""Bulk IOC parser -- one IOC per line input mode.

Splits text on newlines, normalizes and classifies each line individually.
Reuses the existing pipeline normalize() and classify() functions.
"""
from __future__ import annotations

from app.pipeline.classifier import classify
from app.pipeline.models import IOC, IOCType
from app.pipeline.normalizer import normalize


def parse_bulk_iocs(text: str) -> list[IOC]:
    """Parse one-IOC-per-line text into a deduplicated IOC list.

    Each non-blank line is normalized, classified, and deduplicated
    by (type, value). Lines that fail classification are skipped.

    Args:
        text: Newline-separated IOC strings.

    Returns:
        Deduplicated list of IOC objects.
    """
    if not text:
        return []

    deduped: dict[tuple[IOCType, str], IOC] = {}

    for line in text.splitlines():
        raw = line.strip()
        if not raw:
            continue
        normalized = normalize(raw)
        ioc = classify(normalized, raw)
        if ioc is None:
            continue
        key = (ioc.type, ioc.value)
        if key not in deduped:
            deduped[key] = ioc

    return list(deduped.values())
