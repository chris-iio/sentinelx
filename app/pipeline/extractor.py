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

import iocextract
from iocsearcher.searcher import Searcher

from app.pipeline.classifier import classify
from app.pipeline.models import IOC, IOCType
from app.pipeline.normalizer import normalize

# Module-level Searcher — created once, reused across calls (per iocsearcher docs)
_searcher = Searcher()


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
    if not text:
        return []

    candidates: dict[str, dict] = {}  # keyed on raw value for dedup

    def _add(raw: str, type_hint: str) -> None:
        """Add candidate if not already present (dedup by raw value)."""
        raw = raw.strip()
        if raw and raw not in candidates:
            candidates[raw] = {"raw": raw, "type_hint": type_hint}

    # --- iocextract extractions ---
    try:
        for url in iocextract.extract_urls(text, refang=True):
            _add(url, "url")
    except Exception:
        pass

    try:
        for ip in iocextract.extract_ipv4s(text, refang=True):
            _add(ip, "ipv4")
    except Exception:
        pass

    try:
        for ip6 in iocextract.extract_ipv6s(text):
            _add(ip6, "ipv6")
    except Exception:
        pass

    try:
        for h in iocextract.extract_hashes(text):
            _add(h, "hash")
    except Exception:
        pass

    # --- iocsearcher extractions ---
    try:
        for ioc in _searcher.search_data(text):
            _add(ioc.value, ioc.name)
    except Exception:
        pass

    return list(candidates.values())


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
    candidates = extract_iocs(text)
    if not candidates:
        return []

    # Dedup dict keyed on (IOCType, normalized_value) — first occurrence wins
    deduped: dict[tuple[IOCType, str], IOC] = {}

    for candidate in candidates:
        raw = candidate["raw"]
        normalized_value = normalize(raw)
        ioc = classify(normalized_value, raw)
        if ioc is None:
            continue
        key = (ioc.type, ioc.value)
        if key not in deduped:
            deduped[key] = ioc

    return list(deduped.values())
