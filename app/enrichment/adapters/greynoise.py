"""GreyNoise Community API adapter."""
from __future__ import annotations

import logging

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)

GREYNOISE_BASE = "https://api.greynoise.io/v3/community"


class GreyNoiseAdapter(BaseHTTPAdapter):
    """GreyNoise Community endpoint — see BaseHTTPAdapter for the template pattern."""

    supported_types: frozenset[IOCType] = frozenset({IOCType.IPV4, IOCType.IPV6})
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
                return EnrichmentResult(
                    ioc=ioc,
                    provider=self.name,
                    verdict="no_data",
                    detection_count=0,
                    total_engines=1,
                    scan_date=None,
                    raw_stats={},
                )
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

    return EnrichmentResult(
        ioc=ioc,
        provider=provider_name,
        verdict=verdict,
        detection_count=detection_count,
        total_engines=1,
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
