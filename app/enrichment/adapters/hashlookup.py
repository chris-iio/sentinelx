"""CIRCL Hashlookup NSRL adapter.

Implements hash enrichment against the CIRCL Hashlookup API. Delegates all HTTP
safety controls to safe_request() in http_safety.py.

CIRCL Hashlookup API behavior:
  - GET https://hashlookup.circl.lu/lookup/{type}/{hash}
  - 200: Hash found in NSRL -> {FileName, SHA-1, SHA-256, source, db, ...}
  - 404: Hash not found in NSRL -> no_data (NOT an error)
  - 400: Malformed hash -> EnrichmentError("HTTP 400")
  - 500: Server error -> EnrichmentError("HTTP 500")

Verdict behavior:
  - 200 (hash found in NSRL): verdict=known_good, detection_count=1, total_engines=1
  - 404 (hash not in NSRL): verdict=no_data, detection_count=0, total_engines=0

No API key required — CIRCL Hashlookup is a public zero-auth endpoint.
"""
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
    """Adapter for the CIRCL Hashlookup NSRL API.

    Extends BaseHTTPAdapter for hash enrichment against the CIRCL Hashlookup
    API. All HTTP safety controls (SSRF allowlist, size cap, timeouts) are
    inherited.

    Supports hash IOC lookups (MD5, SHA1, SHA256) using the zero-auth CIRCL
    Hashlookup public endpoint. A successful lookup indicates the hash is in
    the NIST NSRL (National Software Reference Library), implying the file is
    a known-legitimate software artifact.

    - Hash found in NSRL (200) -> verdict=known_good
    - Hash not in NSRL (404) -> verdict=no_data (not an error — absence of
      NSRL record does not imply maliciousness)
    - Other HTTP errors -> EnrichmentError

    No API key required — CIRCL Hashlookup is fully public.

    Thread safety: a persistent requests.Session is created by BaseHTTPAdapter.__init__
    and reused across lookup() calls for TCP connection pooling.

    Args:
        allowed_hosts: SSRF allowlist -- only these hostnames may be contacted.
    """

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
    """Parse a CIRCL Hashlookup API response into an EnrichmentResult.

    Extracts FileName, source, and db from the response body.
    A 200 response always indicates the hash is in the NSRL, so verdict
    is always known_good for successful responses.

    Args:
        ioc:           The IOC that was queried.
        body:          Parsed JSON from Hashlookup API response.
        provider_name: Provider name string for result construction.

    Returns:
        EnrichmentResult with verdict "known_good".
    """
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
