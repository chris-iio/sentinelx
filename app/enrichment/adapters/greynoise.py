"""GreyNoise Community API adapter."""
from __future__ import annotations

from typing import NamedTuple

from .base import BaseHTTPAdapter
from ..models import EnrichmentResult, provider_result
from app.pipeline.models import IOC, IOCType

GREYNOISE_BASE = "https://api.greynoise.io/v3/community"


class GreyNoiseSignals(NamedTuple):
    riot: bool
    noise: bool
    classification: str
    name: str
    link: str
    last_seen: str | None


def _greynoise_signals(body: dict) -> GreyNoiseSignals:
    return GreyNoiseSignals(
        riot=body.get("riot", False),
        noise=body.get("noise", False),
        classification=body.get("classification", "") or "",
        name=body.get("name", "") or "",
        link=body.get("link", "") or "",
        last_seen=body.get("last_seen"),
    )


class GreyNoiseAdapter(BaseHTTPAdapter):
    """GreyNoise Community endpoint — see BaseHTTPAdapter for the template pattern."""

    supported_types: frozenset[IOCType] = frozenset((IOCType.IPV4, IOCType.IPV6))
    name = "GreyNoise"
    requires_api_key = True
    _no_data_on_404 = True

    def _build_url(self, ioc: IOC) -> str:
        return f"{GREYNOISE_BASE}/{ioc.value}"

    def _auth_headers(self) -> dict:
        return {
            "key": self._api_key,  # CRITICAL: lowercase 'key' (GreyNoise convention)
        }

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return _parse_response(ioc, body, self.name)


def _parse_response(ioc: IOC, body: dict, provider_name: str) -> EnrichmentResult:
    signals = _greynoise_signals(body)
    verdict, detection_count = _greynoise_verdict(
        riot=signals.riot,
        noise=signals.noise,
        classification=signals.classification,
    )

    return _greynoise_result(
        ioc=ioc,
        provider_name=provider_name,
        verdict=verdict,
        detection_count=detection_count,
        scan_date=signals.last_seen,
        raw_stats=_greynoise_raw_stats(
            noise=signals.noise,
            riot=signals.riot,
            classification=signals.classification,
            name=signals.name,
            link=signals.link,
            last_seen=signals.last_seen,
        ),
    )


def _greynoise_verdict(*, riot: bool, noise: bool, classification: str) -> tuple[str, int]:
    if riot:
        return "clean", 0
    if classification == "malicious":
        return "malicious", 1
    if noise:
        return "suspicious", 1
    return "no_data", 0


def _greynoise_raw_stats(
    *,
    noise: bool,
    riot: bool,
    classification: str,
    name: str,
    link: str,
    last_seen: str | None,
) -> dict[str, object]:
    return {
        "noise": noise,
        "riot": riot,
        "classification": classification,
        "name": name,
        "link": link,
        "last_seen": last_seen,
    }


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
