"""VirusTotal API v3 adapter."""
from __future__ import annotations

import base64
import datetime
from types import MappingProxyType

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.http_safety import safe_request
from app.enrichment.models import (
    EnrichmentError,
    EnrichmentResult,
    error_result,
    no_data_result,
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


def _url_id(url: str) -> str:
    # Base64url-encode URL without padding — VT URL identifier format
    return _trim_base64_padding(base64.urlsafe_b64encode(url.encode()).decode())


def _trim_base64_padding(value: str) -> str:
    end = len(value)
    while end > 0 and value[end - 1] == "=":
        end -= 1
    return value[:end]


def _parse_response(ioc: IOC, body: dict) -> EnrichmentResult:
    attrs = body["data"]["attributes"]
    raw_stats = attrs.get("last_analysis_stats")
    stats = raw_stats if isinstance(raw_stats, dict) else {}
    last_analysis_date = attrs.get("last_analysis_date")

    scan_date: str | None = None
    if last_analysis_date is not None:
        scan_date = datetime.datetime.fromtimestamp(
            last_analysis_date, tz=datetime.timezone.utc
        ).isoformat()

    # Exclude timeout and type-unsupported from total engine count
    malicious = 0
    total = 0
    for stat_name in stats:
        stat_count = stats[stat_name]
        if stat_name == "malicious":
            malicious = stat_count
        if stat_name not in _EXCLUDED_ENGINE_STATUSES:
            total += stat_count

    if malicious > 0:
        verdict = "malicious"
    elif total == 0:
        verdict = "no_data"
    else:
        verdict = "clean"

    # Extract top 5 unique malicious detection names from full analysis results
    raw_analysis_results = attrs.get("last_analysis_results")
    analysis_results = raw_analysis_results if isinstance(raw_analysis_results, dict) else {}
    top_detections: list[str] = []
    if analysis_results:
        seen: set[str] = set()
        for engine_name in analysis_results:
            engine_result = analysis_results[engine_name]
            if len(top_detections) >= 5:
                break
            if not isinstance(engine_result, dict):
                continue
            if engine_result.get("category") == "malicious":
                name = engine_result.get("result")
                if name and name not in seen:
                    seen.add(name)
                    top_detections.append(name)

    enriched_stats = {
        **stats,
        "top_detections": top_detections,
        "reputation": attrs.get("reputation", 0),
    }

    return _virustotal_result(
        ioc=ioc,
        verdict=verdict,
        detection_count=malicious,
        total_engines=total,
        scan_date=scan_date,
        raw_stats=enriched_stats,
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

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        if ioc.type not in ENDPOINT_MAP:
            return error_result(ioc, "VirusTotal", "Unsupported type")

        endpoint_fn = ENDPOINT_MAP[ioc.type]
        url = endpoint_fn(ioc.value)  # type: ignore[call-arg]

        def _vt_hook(resp):
            if resp.status_code == 404:
                return no_data_result(ioc, "VirusTotal")
            if resp.status_code == 429:
                return error_result(ioc, "VirusTotal", "Rate limit exceeded (429)")
            if resp.status_code in (401, 403):
                return error_result(ioc, "VirusTotal", f"Authentication error ({resp.status_code})")
            return None

        result = safe_request(
            self._session, url, self._allowed_hosts, ioc, "VirusTotal",
            pre_raise_hook=_vt_hook,
        )
        if not isinstance(result, dict):
            return result
        return _parse_response(ioc, result)

    def _build_url(self, ioc: IOC) -> str:
        endpoint_fn = ENDPOINT_MAP[ioc.type]
        return endpoint_fn(ioc.value)  # type: ignore[call-arg]

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return _parse_response(ioc, body)
