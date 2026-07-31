"""VirusTotal API v3 adapter."""
from __future__ import annotations

import base64
import datetime
from collections.abc import Mapping
from types import MappingProxyType

from .base import (
    BaseHTTPAdapter,
    _no_data_on_404_hook,
    _rate_limit_on_429,
)
from ..models import (
    EnrichmentResult,
    error_result,
    provider_result,
)
from app.pipeline.models import IOC, IOCType

VT_BASE = "https://www.virustotal.com/api/v3"

ENDPOINT_MAP = MappingProxyType({
    IOCType.IPV4: lambda v: f"{VT_BASE}/ip_addresses/{v}",
    IOCType.IPV6: lambda v: f"{VT_BASE}/ip_addresses/{v}",
    IOCType.DOMAIN: lambda v: f"{VT_BASE}/domains/{v}",
    IOCType.URL: lambda v: f"{VT_BASE}/urls/{_url_id(v)}",
    IOCType.MD5: lambda v: f"{VT_BASE}/files/{v}",
    IOCType.SHA1: lambda v: f"{VT_BASE}/files/{v}",
    IOCType.SHA256: lambda v: f"{VT_BASE}/files/{v}",
    # CVE is NOT in ENDPOINT_MAP — VT has no CVE endpoint (Pitfall 5)
})
_EXCLUDED_ENGINE_STATUSES = frozenset(("timeout", "type-unsupported"))
_EMPTY_ANALYSIS_MAP = MappingProxyType({})


def _url_id(url: str) -> str:
    # Base64url-encode URL without padding — VT URL identifier format
    return _trim_base64_padding(base64.urlsafe_b64encode(url.encode()).decode())


def _trim_base64_padding(value: str) -> str:
    if not value.endswith("="):
        return value
    if not value.endswith("=="):
        return value[:-1]
    if len(value) < 3 or value[-3] != "=":
        return value[:-2]

    end = len(value)
    while end > 0 and value[end - 1] == "=":
        end -= 1
    return value[:end]


def _parse_response(ioc: IOC, body: dict) -> EnrichmentResult:
    attrs = body["data"]["attributes"]
    stats = _analysis_map(attrs, "last_analysis_stats")
    malicious, total = _engine_counts(stats)

    return _virustotal_result(
        ioc=ioc,
        verdict=_virustotal_verdict(malicious=malicious, total=total),
        detection_count=malicious,
        total_engines=total,
        scan_date=_scan_date(attrs),
        raw_stats=_virustotal_raw_stats(attrs=attrs, stats=stats),
    )


def _virustotal_result(
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
        provider="VirusTotal",
        verdict=verdict,
        detection_count=detection_count,
        total_engines=total_engines,
        scan_date=scan_date,
        raw_stats=raw_stats,
    )


def _analysis_map(attrs: Mapping, key: str) -> Mapping:
    value = attrs.get(key)
    if isinstance(value, dict):
        return value
    return _EMPTY_ANALYSIS_MAP


def _engine_counts(stats: Mapping) -> tuple[int, int]:
    malicious = 0
    total = 0
    for stat_name in stats:
        stat_count = stats[stat_name]
        if stat_name == "malicious":
            malicious = stat_count
        if stat_name not in _EXCLUDED_ENGINE_STATUSES:
            total += stat_count
    return malicious, total


def _virustotal_verdict(*, malicious: int, total: int) -> str:
    if malicious > 0:
        return "malicious"
    if total == 0:
        return "no_data"
    return "clean"


def _scan_date(attrs: Mapping) -> str | None:
    last_analysis_date = attrs.get("last_analysis_date")
    if last_analysis_date is None:
        return None
    return datetime.datetime.fromtimestamp(
        last_analysis_date, tz=datetime.timezone.utc
    ).isoformat()


def _top_detections(attrs: Mapping) -> list[str]:
    # Extract top 5 unique malicious detection names from full analysis results.
    analysis_results = _analysis_map(attrs, "last_analysis_results")
    top_detections: list[str] = []
    if not analysis_results:
        return top_detections

    seen: set[str] = set()
    for engine_name in analysis_results:
        engine_result = analysis_results[engine_name]
        if len(top_detections) >= 5:
            break
        _append_top_detection(top_detections, seen, engine_result)
    return top_detections


def _append_top_detection(
    top_detections: list[str],
    seen: set[str],
    engine_result: object,
) -> None:
    if not isinstance(engine_result, dict):
        return
    if engine_result.get("category") != "malicious":
        return
    name = engine_result.get("result")
    if name and name not in seen:
        seen.add(name)
        top_detections.append(name)


def _virustotal_raw_stats(*, attrs: Mapping, stats: Mapping) -> dict:
    return {
        **stats,
        "top_detections": _top_detections(attrs),
        "reputation": attrs.get("reputation", 0),
    }


class VTAdapter(BaseHTTPAdapter):
    """VirusTotal API v3 endpoint — overrides lookup() for ENDPOINT_MAP dispatch."""

    # Types supported by VT API v3 (derived from ENDPOINT_MAP keys)
    # CVE is excluded — VT has no CVE endpoint (Pitfall 5)
    supported_types: frozenset[IOCType] = frozenset(ENDPOINT_MAP)

    name = "VirusTotal"
    requires_api_key = True

    def _auth_headers(self) -> dict:
        return {
            "x-apikey": self._api_key,
            "Accept": "application/json",
        }

    def _make_pre_raise_hook(self, ioc: IOC):
        no_data_on_404 = _no_data_on_404_hook(ioc, self.name)

        def _vt_hook(resp):
            no_data = no_data_on_404(resp)
            if no_data is not None:
                return no_data
            rate_limit = _rate_limit_on_429(resp, ioc, self.name)
            if rate_limit is not None:
                return rate_limit
            if resp.status_code in (401, 403):
                return error_result(ioc, self.name, f"Authentication error ({resp.status_code})")
            return None

        return _vt_hook

    def _build_url(self, ioc: IOC) -> str:
        endpoint_fn = ENDPOINT_MAP[ioc.type]
        return endpoint_fn(ioc.value)  # type: ignore[call-arg]

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return _parse_response(ioc, body)
