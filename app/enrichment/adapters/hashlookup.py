"""CIRCL Hashlookup NSRL adapter."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from .base import BaseHTTPAdapter
from ..models import EnrichmentResult, provider_result
from app.pipeline.models import IOC, IOCType

HASHLOOKUP_BASE = "https://hashlookup.circl.lu"

# Maps IOCType to the URL path segment used by the API
_HASH_TYPE_PATH = MappingProxyType({
    IOCType.MD5: "md5",
    IOCType.SHA1: "sha1",
    IOCType.SHA256: "sha256",
})


@dataclass(frozen=True)
class HashlookupSignals:
    file_name: str
    source: str
    db: str


class HashlookupAdapter(BaseHTTPAdapter):
    """CIRCL Hashlookup NSRL endpoint — see BaseHTTPAdapter for the template pattern."""

    supported_types: frozenset[IOCType] = frozenset(_HASH_TYPE_PATH)
    name = "CIRCL Hashlookup"
    requires_api_key = False
    _no_data_on_404 = True

    def _build_url(self, ioc: IOC) -> str:
        hash_path = _HASH_TYPE_PATH[ioc.type]
        return f"{HASHLOOKUP_BASE}/lookup/{hash_path}/{ioc.value}"

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return _parse_response(ioc, body, self.name)


def _parse_response(ioc: IOC, body: dict, provider_name: str) -> EnrichmentResult:
    signals = _hashlookup_signals(body)
    # 200 always means known_good (hash found in NSRL)
    return _hashlookup_result(
        ioc=ioc,
        provider_name=provider_name,
        verdict="known_good",
        detection_count=1,
        total_engines=1,
        raw_stats=_hashlookup_raw_stats(signals),
    )


def _hashlookup_signals(body: dict) -> HashlookupSignals:
    return HashlookupSignals(
        file_name=body.get("FileName", ""),
        source=body.get("source", "NSRL"),
        db=body.get("db", ""),
    )


def _hashlookup_raw_stats(signals: HashlookupSignals) -> dict:
    return {
        "file_name": signals.file_name,
        "source": signals.source,
        "db": signals.db,
    }


def _hashlookup_result(
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
