"""OTX AlienVault API adapter."""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.models import EnrichmentResult, no_data_result, provider_result
from app.pipeline.models import IOC, IOCType

OTX_BASE = "https://otx.alienvault.com/api/v1/indicators"

# Maps IOCType to the OTX path segment used in the URL
# CRITICAL: MD5, SHA1, SHA256 ALL map to "file" — not "md5"/"sha1"/"sha256"
_OTX_TYPE_MAP = MappingProxyType({
    IOCType.IPV4: "IPv4",
    IOCType.IPV6: "IPv6",
    IOCType.DOMAIN: "domain",
    IOCType.URL: "url",
    IOCType.MD5: "file",
    IOCType.SHA1: "file",
    IOCType.SHA256: "file",
    IOCType.CVE: "cve",
})

# Threshold for verdict classification
_MALICIOUS_THRESHOLD = 5  # pulse_info.count >= this -> malicious
_SUSPICIOUS_MIN = 1       # pulse_info.count >= this -> suspicious (below malicious threshold)
_EMPTY_PULSE_INFO: Mapping[str, object] = MappingProxyType({})


class OTXAdapter(BaseHTTPAdapter):
    """OTX AlienVault v1 endpoint — see BaseHTTPAdapter for the template pattern."""

    supported_types: frozenset[IOCType] = frozenset(_OTX_TYPE_MAP)  # EMAIL excluded — OTX has no email lookup endpoint
    name = "OTX AlienVault"
    requires_api_key = True

    def _build_url(self, ioc: IOC) -> str:
        otx_type = _OTX_TYPE_MAP[ioc.type]
        return f"{OTX_BASE}/{otx_type}/{ioc.value}/general"

    def _auth_headers(self) -> dict:
        return {
            "X-OTX-API-KEY": self._api_key,
            "Accept": "application/json",
        }

    def _make_pre_raise_hook(self, ioc: IOC):
        def _404_hook(resp):
            if resp.status_code == 404:
                return no_data_result(ioc, self.name)
            return None
        return _404_hook

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return _parse_response(ioc, body, self.name)


def _parse_response(ioc: IOC, body: dict, provider_name: str) -> EnrichmentResult:
    raw_pulse_info = body.get("pulse_info")
    pulse_info = raw_pulse_info if isinstance(raw_pulse_info, Mapping) else _EMPTY_PULSE_INFO
    pulse_count: int = pulse_info.get("count", 0) or 0
    reputation: int = body.get("reputation", 0) or 0
    type_title: str = body.get("type_title", "") or ""

    if pulse_count >= _MALICIOUS_THRESHOLD:
        verdict = "malicious"
    elif pulse_count >= _SUSPICIOUS_MIN:
        verdict = "suspicious"
    else:
        verdict = "no_data"

    return _otx_result(
        ioc=ioc,
        provider_name=provider_name,
        verdict=verdict,
        detection_count=pulse_count,
        total_engines=1,
        raw_stats={
            "pulse_count": pulse_count,
            "reputation": reputation,
            "type_title": type_title,
        },
    )


def _otx_result(
    *,
    ioc: IOC,
    provider_name: str,
    verdict: str,
    detection_count: int,
    total_engines: int,
    raw_stats: dict | None = None,
) -> EnrichmentResult:
    return provider_result(
        ioc=ioc,
        provider=provider_name,
        verdict=verdict,
        detection_count=detection_count,
        total_engines=total_engines,
        scan_date=None,
        raw_stats=raw_stats,
    )
