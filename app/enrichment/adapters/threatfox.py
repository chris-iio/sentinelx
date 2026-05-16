"""ThreatFox (abuse.ch) API adapter."""
from __future__ import annotations

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.models import EnrichmentResult, no_data_result, provider_result
from app.pipeline.models import IOC, IOCType

TF_BASE = "https://threatfox-api.abuse.ch/api/v1/"
CONFIDENCE_THRESHOLD = 75  # >=75 = malicious, <75 = suspicious (per user decision)
MAX_CONFIDENCE_LEVEL = 100

# Hash types use a different ThreatFox query endpoint than domain/IP/URL types
_HASH_TYPES = frozenset((IOCType.MD5, IOCType.SHA1, IOCType.SHA256))


def _select_best_record(data: list[dict]) -> dict:
    best: dict = {}
    best_confidence = -1
    for record in data:
        confidence = record.get("confidence_level", 0)
        if confidence <= best_confidence:
            continue
        best = record
        best_confidence = confidence
        if confidence >= MAX_CONFIDENCE_LEVEL:
            break
    return best


def _parse_response(ioc: IOC, body: dict) -> EnrichmentResult:
    query_status = body.get("query_status", "")

    if query_status == "no_result":
        return no_data_result(ioc, "ThreatFox")

    # query_status == "ok" with results
    raw_data = body.get("data")
    data = raw_data if isinstance(raw_data, list) else []
    if not data:
        return no_data_result(ioc, "ThreatFox")
    best = _select_best_record(data)

    confidence_level: int = best.get("confidence_level", 0)
    verdict = "malicious" if confidence_level >= CONFIDENCE_THRESHOLD else "suspicious"

    raw_stats = {
        "threat_type": best.get("threat_type"),
        "malware_printable": best.get("malware_printable"),
        "confidence_level": confidence_level,
        "ioc_type_desc": best.get("ioc_type_desc"),
    }

    return _threatfox_result(
        ioc=ioc,
        verdict=verdict,
        detection_count=1,
        total_engines=1,
        scan_date=best.get("first_seen"),
        raw_stats=raw_stats,
    )


def _threatfox_result(
    *,
    ioc: IOC,
    verdict: str,
    detection_count: int,
    total_engines: int,
    scan_date: str | None,
    raw_stats: dict,
) -> EnrichmentResult:
    return provider_result(
        ioc=ioc,
        provider="ThreatFox",
        verdict=verdict,
        detection_count=detection_count,
        total_engines=total_engines,
        scan_date=scan_date,
        raw_stats=raw_stats,
    )


class TFAdapter(BaseHTTPAdapter):
    """ThreatFox (abuse.ch) POST endpoint — see BaseHTTPAdapter for the template pattern."""

    supported_types: frozenset[IOCType] = frozenset((
        IOCType.MD5, IOCType.SHA1, IOCType.SHA256,
        IOCType.DOMAIN, IOCType.IPV4, IOCType.IPV6, IOCType.URL,
    ))

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
