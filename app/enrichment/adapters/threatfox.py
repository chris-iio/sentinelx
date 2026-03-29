"""ThreatFox (abuse.ch) API adapter.

Implements IOC enrichment against the ThreatFox API v1. Delegates all HTTP safety
controls to safe_request() in http_safety.py.

ThreatFox uses a POST-based JSON API. Hash lookups use "search_hash" query type;
domain/IP/URL lookups use "search_ioc" query type (per ThreatFox API v1 docs).

Confidence-based verdict mapping (per user decision):
  - confidence_level >= 75  ->  verdict="malicious"
  - confidence_level < 75   ->  verdict="suspicious"
  - query_status="no_result" -> verdict="no_data"

Auth-Key header required (abuse.ch policy change — previously public search).
"""
from __future__ import annotations

import logging

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.models import EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)

TF_BASE = "https://threatfox-api.abuse.ch/api/v1/"
CONFIDENCE_THRESHOLD = 75  # >=75 = malicious, <75 = suspicious (per user decision)

# Hash types use a different ThreatFox query endpoint than domain/IP/URL types
_HASH_TYPES = {IOCType.MD5, IOCType.SHA1, IOCType.SHA256}


def _select_best_record(data: list[dict]) -> dict:
    """Return the record with the highest confidence_level.

    ThreatFox may return multiple records for one IOC query. Uses the
    highest-confidence entry for verdict determination.

    Args:
        data: Non-empty list of ThreatFox IOC records.

    Returns:
        The record dict with the maximum confidence_level value.
    """
    return max(data, key=lambda r: r.get("confidence_level", 0))


def _parse_response(ioc: IOC, body: dict) -> EnrichmentResult:
    """Parse a ThreatFox API success response into an EnrichmentResult.

    Maps query_status to verdicts:
      - "no_result"  -> verdict="no_data"
      - "ok"         -> confidence-based verdict (>=75 malicious, <75 suspicious)

    For "ok" responses with multiple records, uses the highest-confidence entry.

    Args:
        ioc:  The IOC that was queried.
        body: Parsed JSON from ThreatFox API response.

    Returns:
        EnrichmentResult with verdict, counts, timestamp, and raw stats.
    """
    query_status = body.get("query_status", "")

    if query_status == "no_result":
        return EnrichmentResult(
            ioc=ioc,
            provider="ThreatFox",
            verdict="no_data",
            detection_count=0,
            total_engines=0,
            scan_date=None,
            raw_stats={},
        )

    # query_status == "ok" with results
    data: list[dict] = body.get("data", [])
    best = _select_best_record(data)

    confidence_level: int = best.get("confidence_level", 0)
    verdict = "malicious" if confidence_level >= CONFIDENCE_THRESHOLD else "suspicious"

    raw_stats = {
        "threat_type": best.get("threat_type"),
        "malware_printable": best.get("malware_printable"),
        "confidence_level": confidence_level,
        "ioc_type_desc": best.get("ioc_type_desc"),
    }

    return EnrichmentResult(
        ioc=ioc,
        provider="ThreatFox",
        verdict=verdict,
        detection_count=1,
        total_engines=1,
        scan_date=best.get("first_seen"),
        raw_stats=raw_stats,
    )


class TFAdapter(BaseHTTPAdapter):
    """Adapter for the ThreatFox (abuse.ch) API v1.

    Extends BaseHTTPAdapter for IOC enrichment. Maps IOC types to appropriate
    ThreatFox query endpoints:
      - Hash types (MD5, SHA1, SHA256): POST {"query": "search_hash", "hash": value}
      - Other types (IP, domain, URL): POST {"query": "search_ioc", "search_term": value}

    Verdict mapping: confidence_level >= 75 -> malicious, < 75 -> suspicious.
    Handles all 7 enrichable IOC types; CVE is not supported by ThreatFox.

    Auth-Key header required (abuse.ch policy change — previously public).

    Thread safety: a persistent requests.Session is created by BaseHTTPAdapter.__init__
    and reused across lookup() calls for TCP connection pooling.

    Args:
        allowed_hosts: SSRF allowlist — only these hostnames may be contacted.
        api_key:       abuse.ch API key for the Auth-Key header (keyword-only).
    """

    supported_types: frozenset[IOCType] = frozenset({
        IOCType.MD5, IOCType.SHA1, IOCType.SHA256,
        IOCType.DOMAIN, IOCType.IPV4, IOCType.IPV6, IOCType.URL,
    })

    name = "ThreatFox"
    requires_api_key = True
    _http_method = "POST"

    def _build_url(self, ioc: IOC) -> str:
        return TF_BASE

    def _auth_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Auth-Key": self._api_key,
        }

    def _build_request_body(self, ioc: IOC) -> tuple[dict | None, dict | None]:
        # JSON payload (not form-encoded): (None, json_dict)
        if ioc.type in _HASH_TYPES:
            payload = {"query": "search_hash", "hash": ioc.value}
        else:
            payload = {"query": "search_ioc", "search_term": ioc.value}
        return (None, payload)

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return _parse_response(ioc, body)
