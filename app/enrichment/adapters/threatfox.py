"""ThreatFox (abuse.ch) API adapter."""
from __future__ import annotations

from .abusech import abusech_data_records
from .base import BaseHTTPAdapter
from ..models import EnrichmentResult, no_data_result, provider_result
from app.pipeline.models import IOC, IOCType

TF_BASE = "https://threatfox-api.abuse.ch/api/v1/"
CONFIDENCE_THRESHOLD = 75  # >=75 = malicious, <75 = suspicious (per user decision)
MAX_CONFIDENCE_LEVEL = 100

# Hash types use a different ThreatFox query endpoint than domain/IP/URL types
_HASH_TYPES = frozenset((IOCType.MD5, IOCType.SHA1, IOCType.SHA256))


def _select_best_record(data: list[dict]) -> dict:
    record_count = len(data)
    if record_count == 0:
        if type(data) is list:
            return {}
    else:
        if record_count == 1:
            return data[0]
        first = data[0]
        second = data[1]
        if record_count == 2:
            return _higher_confidence_record(first, second)
        third = data[2]
        if record_count == 3:
            return _higher_confidence_record(_higher_confidence_record(first, second), third)
        fourth = data[3]
        if record_count == 4:
            return _higher_confidence_record(
                _higher_confidence_record(_higher_confidence_record(first, second), third),
                fourth,
            )

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


def _higher_confidence_record(first: dict, second: dict) -> dict:
    if first.get("confidence_level", 0) >= second.get("confidence_level", 0):
        return first
    return second


def _parse_response(ioc: IOC, body: dict) -> EnrichmentResult:
    data = abusech_data_records(body, no_data_status="no_result")
    if data is None:
        return no_data_result(ioc, "ThreatFox")
    best = _select_best_record(data)

    confidence_level: int = best.get("confidence_level", 0)

    return _threatfox_result(
        ioc=ioc,
        verdict=_threatfox_verdict(confidence_level),
        detection_count=1,
        total_engines=1,
        scan_date=best.get("first_seen"),
        raw_stats=_threatfox_raw_stats(best, confidence_level),
    )


def _threatfox_verdict(confidence_level: int) -> str:
    return "malicious" if confidence_level >= CONFIDENCE_THRESHOLD else "suspicious"


def _threatfox_raw_stats(record: dict, confidence_level: int) -> dict[str, object]:
    return {
        "threat_type": record.get("threat_type"),
        "malware_printable": record.get("malware_printable"),
        "confidence_level": confidence_level,
        "ioc_type_desc": record.get("ioc_type_desc"),
    }


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
