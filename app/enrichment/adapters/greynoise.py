"""GreyNoise Community API adapter."""
from __future__ import annotations

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.models import EnrichmentResult, provider_result
from app.pipeline.models import IOC, IOCType

GREYNOISE_BASE = "https://api.greynoise.io/v3/community"


class GreyNoiseAdapter(BaseHTTPAdapter):
    """GreyNoise Community endpoint — see BaseHTTPAdapter for the template pattern."""

    supported_types: frozenset[IOCType] = frozenset((IOCType.IPV4, IOCType.IPV6))
    name = "GreyNoise"
    requires_api_key = True

    def _build_url(self, ioc: IOC) -> str:
        return f"{GREYNOISE_BASE}/{ioc.value}"

    def _auth_headers(self) -> dict:
        return {
            "key": self._api_key,  # CRITICAL: lowercase 'key' (GreyNoise convention)
        }

    def _make_pre_raise_hook(self, ioc: IOC):
        def _404_hook(resp):
            if resp.status_code == 404:
                return _greynoise_result(ioc=ioc, provider_name=self.name, verdict="no_data")
            return None
        return _404_hook

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return _parse_response(ioc, body, self.name)


def _parse_response(ioc: IOC, body: dict, provider_name: str) -> EnrichmentResult:
    riot: bool = body.get("riot", False)
    noise: bool = body.get("noise", False)
    classification: str = body.get("classification", "") or ""
    name: str = body.get("name", "") or ""
    link: str = body.get("link", "") or ""
    last_seen: str | None = body.get("last_seen")

    if riot:
        verdict = "clean"
        detection_count = 0
    elif classification == "malicious":
        verdict = "malicious"
        detection_count = 1
    elif noise:
        verdict = "suspicious"
        detection_count = 1
    else:
        verdict = "no_data"
        detection_count = 0

    return _greynoise_result(
        ioc=ioc,
        provider_name=provider_name,
        verdict=verdict,
        detection_count=detection_count,
        scan_date=last_seen,
        raw_stats={
            "noise": noise,
            "riot": riot,
            "classification": classification,
            "name": name,
            "link": link,
            "last_seen": last_seen,
        },
    )


def _greynoise_result(
    *,
    ioc: IOC,
    provider_name: str,
    verdict: str,
    detection_count: int = 0,
    scan_date: str | None = None,
    raw_stats: dict | None = None,
) -> EnrichmentResult:
    return provider_result(
        ioc=ioc,
        provider=provider_name,
        verdict=verdict,
        detection_count=detection_count,
        total_engines=1,
        scan_date=scan_date,
        raw_stats=raw_stats,
    )
