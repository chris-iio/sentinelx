"""CIRCL Hashlookup NSRL adapter."""
from __future__ import annotations

import logging

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.models import EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)

HASHLOOKUP_BASE = "https://hashlookup.circl.lu"

# Maps IOCType to the URL path segment used by the API
_HASH_TYPE_PATH: dict[IOCType, str] = {
    IOCType.MD5: "md5",
    IOCType.SHA1: "sha1",
    IOCType.SHA256: "sha256",
}


class HashlookupAdapter(BaseHTTPAdapter):
    """CIRCL Hashlookup NSRL endpoint — see BaseHTTPAdapter for the template pattern."""

    supported_types: frozenset[IOCType] = frozenset({IOCType.MD5, IOCType.SHA1, IOCType.SHA256})
    name = "CIRCL Hashlookup"
    requires_api_key = False

    def _build_url(self, ioc: IOC) -> str:
        hash_path = _HASH_TYPE_PATH[ioc.type]
        return f"{HASHLOOKUP_BASE}/lookup/{hash_path}/{ioc.value}"

    def _make_pre_raise_hook(self, ioc: IOC):
        def _404_hook(resp):
            if resp.status_code == 404:
                return EnrichmentResult(
                    ioc=ioc,
                    provider=self.name,
                    verdict="no_data",
                    detection_count=0,
                    total_engines=0,
                    scan_date=None,
                    raw_stats={},
                )
            return None
        return _404_hook

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return _parse_response(ioc, body, self.name)


def _parse_response(ioc: IOC, body: dict, provider_name: str) -> EnrichmentResult:
    # 200 always means known_good (hash found in NSRL)
    return EnrichmentResult(
        ioc=ioc,
        provider=provider_name,
        verdict="known_good",
        detection_count=1,
        total_engines=1,
        scan_date=None,
        raw_stats={
            "file_name": body.get("FileName", ""),
            "source": body.get("source", "NSRL"),
            "db": body.get("db", ""),
        },
    )
