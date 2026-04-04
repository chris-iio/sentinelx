"""ThreatFox (abuse.ch) API adapter."""
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
    return max(data, key=lambda r: r.get("confidence_level", 0))


def _parse_response(ioc: IOC, body: dict) -> EnrichmentResult:
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
    """ThreatFox (abuse.ch) POST endpoint — see BaseHTTPAdapter for the template pattern."""

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
