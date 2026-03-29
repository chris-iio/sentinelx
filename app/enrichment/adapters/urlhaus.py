"""URLhaus API adapter.

Implements URL, IP, domain, and hash enrichment against the URLhaus API
(abuse.ch). Delegates all HTTP safety controls to safe_request() in http_safety.py.

URLhaus API behavior (all endpoints are POST with form-encoded bodies):
  - POST /v1/url/      {"url": value}        Auth-Key header required
  - POST /v1/host/     {"host": value}       Auth-Key header required
  - POST /v1/payload/  {"md5_hash": value}   Auth-Key header required
  - POST /v1/payload/  {"sha256_hash": value} Auth-Key header required
  - All endpoints return HTTP 200 (not 404) for missing data —
    "no_results"/"no_result" in query_status
  - Auth-Key header contains the API key

Verdict logic:
  - query_status == "is_listed" (URL endpoint)       -> malicious
  - query_status == "ok" + urls_count > 0 (host)     -> malicious
  - query_status == "ok" + urls (payload endpoint)   -> malicious
  - query_status "no_results" or "no_result"         -> no_data

Supported IOC types: URL, IPv4, IPv6, DOMAIN, MD5, SHA256
NOT supported: SHA1, CVE
"""
from __future__ import annotations

import logging

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.models import EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)

URLHAUS_BASE = "https://urlhaus-api.abuse.ch"

# Maps IOCType to (url_path, body_key) for POST requests
_ENDPOINT_MAP: dict[IOCType, tuple[str, str]] = {
    IOCType.URL: ("/v1/url/", "url"),
    IOCType.IPV4: ("/v1/host/", "host"),
    IOCType.IPV6: ("/v1/host/", "host"),
    IOCType.DOMAIN: ("/v1/host/", "host"),
    IOCType.MD5: ("/v1/payload/", "md5_hash"),
    IOCType.SHA256: ("/v1/payload/", "sha256_hash"),
}


class URLhausAdapter(BaseHTTPAdapter):
    """Adapter for the URLhaus API (abuse.ch).

    Extends BaseHTTPAdapter for URL, IP (v4/v6), domain, MD5, and SHA256 IOC
    lookups via POST requests with form-encoded bodies. An Auth-Key header is
    required.

    Verdict is derived from the query_status field in the response:
    - "is_listed"                   -> malicious (URL endpoint)
    - "ok" + urls_count > 0         -> malicious (host/payload endpoint)
    - "no_results" or "no_result"   -> no_data

    SHA1 and CVE are not supported by URLhaus.

    Thread safety: a persistent requests.Session is created by BaseHTTPAdapter.__init__
    and reused across lookup() calls for TCP connection pooling.

    Args:
        allowed_hosts: SSRF allowlist -- only these hostnames may be contacted.
        api_key:       URLhaus API key for the Auth-Key header (keyword-only).
    """

    supported_types: frozenset[IOCType] = frozenset({
        IOCType.URL,
        IOCType.IPV4,
        IOCType.IPV6,
        IOCType.DOMAIN,
        IOCType.MD5,
        IOCType.SHA256,
    })
    name = "URLhaus"
    requires_api_key = True
    _http_method = "POST"

    def _build_url(self, ioc: IOC) -> str:
        url_path, _ = _ENDPOINT_MAP[ioc.type]
        return f"{URLHAUS_BASE}{url_path}"

    def _auth_headers(self) -> dict:
        return {
            "Auth-Key": self._api_key,
            "Accept": "application/json",
        }

    def _build_request_body(self, ioc: IOC) -> tuple[dict | None, dict | None]:
        # Form-encoded POST: data dict, no JSON payload
        _, body_key = _ENDPOINT_MAP[ioc.type]
        return ({body_key: ioc.value}, None)

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return _parse_response(ioc, body, self.name)


def _parse_response(ioc: IOC, body: dict, provider_name: str) -> EnrichmentResult:
    """Parse a URLhaus API response into an EnrichmentResult.

    Inspects query_status and urls_count to determine verdict.
    Extracts tags, blacklists, and urls_count for raw_stats.

    Verdict rules:
      - "is_listed"                   -> malicious (URL endpoint response)
      - "ok" + urls_count > 0         -> malicious (host or payload endpoint)
      - "no_results" or "no_result"   -> no_data
      - "ok" + urls_count == 0        -> no_data (IP/domain not active on URLhaus)

    Args:
        ioc:           The IOC that was queried.
        body:          Parsed JSON from URLhaus API response.
        provider_name: Provider name string for result construction.

    Returns:
        EnrichmentResult with verdict "malicious" or "no_data".
    """
    query_status: str = body.get("query_status", "")
    urls_count: int = body.get("urls_count", 0) or 0
    tags: list[str] | None = body.get("tags")
    blacklists: dict = body.get("blacklists", {}) or {}
    signature: str | None = body.get("signature")

    if query_status == "is_listed":
        verdict = "malicious"
        detection_count = 1
    elif query_status == "ok" and urls_count > 0:
        verdict = "malicious"
        detection_count = urls_count
    elif query_status in ("no_results", "no_result"):
        verdict = "no_data"
        detection_count = 0
    else:
        # "ok" with urls_count == 0 — IP/domain seen but no active URLs
        verdict = "no_data"
        detection_count = 0

    return EnrichmentResult(
        ioc=ioc,
        provider=provider_name,
        verdict=verdict,
        detection_count=detection_count,
        total_engines=1,
        scan_date=None,
        raw_stats={
            "query_status": query_status,
            "urls_count": urls_count,
            "tags": tags,
            "blacklists": blacklists,
            "signature": signature,
        },
    )
