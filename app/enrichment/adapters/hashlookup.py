"""CIRCL Hashlookup NSRL adapter."""
from __future__ import annotations

from types import MappingProxyType

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.models import EnrichmentResult, no_data_result, provider_result
from app.pipeline.models import IOC, IOCType

HASHLOOKUP_BASE = "https://hashlookup.circl.lu"

# Maps IOCType to the URL path segment used by the API
_HASH_TYPE_PATH = MappingProxyType({
    IOCType.MD5: "md5",
    IOCType.SHA1: "sha1",
    IOCType.SHA256: "sha256",
})


class HashlookupAdapter(BaseHTTPAdapter):
    """CIRCL Hashlookup NSRL endpoint — see BaseHTTPAdapter for the template pattern."""

    supported_types: frozenset[IOCType] = frozenset(_HASH_TYPE_PATH)
    name = "CIRCL Hashlookup"
    requires_api_key = False

    def _build_url(self, ioc: IOC) -> str:
        hash_path = _HASH_TYPE_PATH[ioc.type]
        return f"{HASHLOOKUP_BASE}/lookup/{hash_path}/{ioc.value}"

    def _make_pre_raise_hook(self, ioc: IOC):
        def _404_hook(resp):
            if resp.status_code == 404:
                return no_data_result(ioc, self.name)
            return None
        return _404_hook

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return _parse_response(ioc, body, self.name)


def _parse_response(ioc: IOC, body: dict, provider_name: str) -> EnrichmentResult:
    # 200 always means known_good (hash found in NSRL)
    return _hashlookup_result(
        ioc=ioc,
        provider_name=provider_name,
        verdict="known_good",
        detection_count=1,
        total_engines=1,
        raw_stats={
            "file_name": body.get("FileName", ""),
            "source": body.get("source", "NSRL"),
            "db": body.get("db", ""),
        },
    )


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
