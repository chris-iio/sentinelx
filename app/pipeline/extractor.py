"""IOC extractor — raw text to candidate IOC list.

Entry point of the offline pipeline. Takes free-form analyst text and returns
raw IOC candidates using two complementary libraries:
- iocextract: URLs (with refanging), IPv4, IPv6, all hash types
- iocsearcher: CVEs and supplementary types

The Searcher is created once at module level (per iocsearcher docs) and
reused across calls for performance.

Security:
- Pure functions: no side effects, no network calls (offline only)
- Input text is not persisted (SEC-14)
- No Flask imports — pipeline/ is isolated from web layer
"""
from __future__ import annotations

import logging
from collections.abc import Callable, Iterable

import iocextract
from iocsearcher.searcher import Searcher

from app.pipeline.classifier import classify
from app.pipeline.models import IOC, IOCType
from app.pipeline.normalizer import normalize
from app.text_utils import has_non_whitespace, stripped_text_or_none

logger = logging.getLogger(__name__)

# Module-level Searcher — created once, reused across calls (per iocsearcher docs)
_searcher = Searcher()
_EXPECTED_EXTRACTION_ERRORS = (ValueError, TypeError, AttributeError, UnicodeError)


def _consume_extraction_source(
    source_name: str,
    type_hint: str,
    source_factory: Callable[[], Iterable[str]],
    add_candidate: Callable[[str, str], None],
) -> None:
    """Consume one extraction iterable using the shared error policy."""
    try:
        for value in source_factory():
            add_candidate(value, type_hint)
    except _EXPECTED_EXTRACTION_ERRORS:
        pass
    except Exception:
        logger.warning("Unexpected error in %s extraction", source_name, exc_info=True)


def extract_iocs(text: str) -> list[dict]:
    """Extract raw IOC candidates from free-form text.

    Uses iocextract for URLs, IPs, and hashes; iocsearcher for CVEs and
    supplementary types. Results from both are merged and deduplicated by
    raw value.

    Args:
        text: Free-form analyst text (SIEM alert, threat report, paste).
              May contain defanged IOCs — iocextract handles refanging.

    Returns:
        List of dicts with keys:
          - 'raw': str — the extracted (possibly refanged) string
          - 'type_hint': str — library-provided type hint (e.g. 'url', 'ipv4')
        Deduplicated by raw value — same string appears at most once.
        Returns empty list if text is empty or no IOCs found.
    """
    if not text or not has_non_whitespace(text):
        return []

    candidates: list[dict] = []
    seen_raw: set[str] = set()

    def _add(raw: str, type_hint: str) -> None:
        """Add candidate if not already present (dedup by raw value)."""
        stripped_raw = stripped_text_or_none(raw)
        if stripped_raw is not None and stripped_raw not in seen_raw:
            seen_raw.add(stripped_raw)
            candidates.append({"raw": stripped_raw, "type_hint": type_hint})

    # --- iocextract extractions ---
    _consume_extraction_source(
        "iocextract URL", "url", lambda: iocextract.extract_urls(text, refang=True), _add
    )
    _consume_extraction_source(
        "iocextract IPv4", "ipv4", lambda: iocextract.extract_ipv4s(text, refang=True), _add
    )
    _consume_extraction_source(
        "iocextract IPv6", "ipv6", lambda: iocextract.extract_ipv6s(text), _add
    )
    _consume_extraction_source(
        "iocextract hash", "hash", lambda: iocextract.extract_hashes(text), _add
    )

    # --- iocsearcher extractions ---
    try:
        for ioc in _searcher.search_data(text):
            _add(ioc.value, ioc.name)
    except _EXPECTED_EXTRACTION_ERRORS:
        pass
    except Exception:
        logger.warning("Unexpected error in iocsearcher extraction", exc_info=True)

    return candidates


def run_pipeline(text: str) -> list[IOC]:
    """Run the complete offline IOC pipeline on free-form text.

    Chains: extract -> normalize -> classify -> deduplicate

    Each candidate is normalized (defanging removed), classified into a typed
    IOC dataclass, and deduplicated by (type, normalized_value). If a candidate
    cannot be classified, it is silently discarded.

    Args:
        text: Free-form analyst text (SIEM alert, threat report, paste).

    Returns:
        Deduplicated list of IOC dataclass objects, each with:
        - type:      IOCType enum value
        - value:     Canonical (refanged, normalized) string
        - raw_match: Original matched string from input
        Returns empty list if text is empty or no classifiable IOCs found.
    """
    if not text or not has_non_whitespace(text):
        return []

    candidates = extract_iocs(text)
    if not candidates:
        return []
    if len(candidates) == 1:
        raw = candidates[0]["raw"]
        normalized_value = normalize(raw)
        ioc = classify(normalized_value, raw)
        return [] if ioc is None else [ioc]
    if len(candidates) == 2:
        first_raw = candidates[0]["raw"]
        first_normalized = normalize(first_raw)
        first_ioc = classify(first_normalized, first_raw)

        second_raw = candidates[1]["raw"]
        second_normalized = normalize(second_raw)
        if second_normalized == first_normalized:
            return [] if first_ioc is None else [first_ioc]

        second_ioc = classify(second_normalized, second_raw)
        if first_ioc is None:
            return [] if second_ioc is None else [second_ioc]
        if second_ioc is None or (
            first_ioc.type == second_ioc.type and first_ioc.value == second_ioc.value
        ):
            return [first_ioc]
        return [first_ioc, second_ioc]

    # Dedup keyed on (IOCType, normalized_value) — first occurrence wins
    results: list[IOC] = []
    seen_keys: set[tuple[IOCType, str]] = set()
    seen_normalized: set[str] = set()

    for candidate in candidates:
        raw = candidate["raw"]
        normalized_value = normalize(raw)
        if normalized_value in seen_normalized:
            continue
        seen_normalized.add(normalized_value)

        ioc = classify(normalized_value, raw)
        if ioc is None:
            continue
        key = (ioc.type, ioc.value)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        results.append(ioc)

    return results
