"""URLhaus API adapter.

Implements URL, IP, domain, and hash enrichment against the URLhaus API
(abuse.ch) with full HTTP safety controls matching the ShodanAdapter pattern:
  - SEC-04: timeout=(5, 30) on all requests
  - SEC-05: stream=True + byte counting, 1 MB response cap
  - SEC-06: allow_redirects=False on all requests
  - SEC-07/SEC-16: ALLOWED_API_HOSTS allowlist enforced before every network call

URLhaus API behavior (all endpoints are POST with form-encoded bodies):
  - POST /v1/url/      {"url": value}        Auth-Key header required
  - POST /v1/host/     {"host": value}       Auth-Key header required
  - POST /v1/payload/  {"md5_hash": value}   Auth-Key header required
  - POST /v1/payload/  {"sha256_hash": value} Auth-Key header required
  - All endpoints return HTTP 200 (not 404) for missing data — "no_results"/"no_result" in query_status
  - Auth-Key header contains the API key

Verdict logic:
  - query_status == "is_listed" (URL endpoint)       -> malicious
  - query_status == "ok" + urls_count > 0 (host)     -> malicious
  - query_status == "ok" + urls (payload endpoint)   -> malicious
  - query_status "no_results" or "no_result"         -> no_data

Supported IOC types: URL, IPv4, IPv6, DOMAIN, MD5, SHA256
NOT supported: SHA1, CVE

Thread safety: a persistent requests.Session is created in __init__ and reused across
lookup() calls (TCP connection pooling).
"""
from __future__ import annotations

import logging

import requests
import requests.exceptions

from app.enrichment.http_safety import TIMEOUT, read_limited, validate_endpoint
from app.enrichment.models import EnrichmentError, EnrichmentResult
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


class URLhausAdapter:
    """Adapter for the URLhaus API (abuse.ch).

    Supports URL, IP (v4/v6), domain, MD5, and SHA256 IOC lookups via POST
    requests with form-encoded bodies. An Auth-Key header is required.

    Verdict is derived from the query_status field in the response:
    - "is_listed"                   -> malicious (URL endpoint)
    - "ok" + urls_count > 0         -> malicious (host/payload endpoint)
    - "no_results" or "no_result"   -> no_data

    SHA1 and CVE are not supported by URLhaus.

    Args:
        api_key:       URLhaus API key for the Auth-Key header.
        allowed_hosts: SSRF allowlist -- only these hostnames may be contacted.
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

    def __init__(self, api_key: str, allowed_hosts: list[str]) -> None:
        self._api_key = api_key
        self._allowed_hosts = allowed_hosts
        self._session = requests.Session()
        self._session.headers.update({
            "Auth-Key": self._api_key,
            "Accept": "application/json",
        })

    def is_configured(self) -> bool:
        """Return True if a non-empty API key is set."""
        return bool(self._api_key)

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        """Enrich a single IOC using the URLhaus API.

        Returns EnrichmentError immediately for unsupported types (SHA1, CVE).
        Validates the URLhaus endpoint against the SSRF allowlist before any
        network call. Makes a POST request with full safety controls and
        parses the query_status field for verdict.

        Response semantics:
          - query_status="is_listed"              -> verdict=malicious (URL endpoint)
          - query_status="ok" + urls_count > 0    -> verdict=malicious (host/payload)
          - query_status="no_results"/"no_result" -> verdict=no_data
          - HTTP 400+ error                       -> EnrichmentError

        IMPORTANT: URLhaus always returns HTTP 200 for both found and not-found
        results. The query_status field distinguishes the two cases.

        Args:
            ioc: The IOC to look up.

        Returns:
            EnrichmentResult on success (including no_data cases).
            EnrichmentError on unsupported type, SSRF block, or network failure.
        """
        if ioc.type not in self.supported_types:
            return EnrichmentError(
                ioc=ioc, provider=self.name, error="Unsupported type"
            )

        url_path, body_key = _ENDPOINT_MAP[ioc.type]
        url = f"{URLHAUS_BASE}{url_path}"

        try:
            validate_endpoint(url, self._allowed_hosts)
        except ValueError as exc:
            return EnrichmentError(ioc=ioc, provider=self.name, error=str(exc))

        try:
            resp = self._session.post(
                url,
                data={body_key: ioc.value},           # form-encoded (not JSON)
                timeout=TIMEOUT,                       # SEC-04
                allow_redirects=False,                 # SEC-06
                stream=True,                           # SEC-05 setup
            )
            resp.raise_for_status()
            body = read_limited(resp)                  # SEC-05: byte cap enforced
            return _parse_response(ioc, body, self.name)
        except requests.exceptions.Timeout:
            return EnrichmentError(ioc=ioc, provider=self.name, error="Timeout")
        except requests.exceptions.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else "unknown"
            return EnrichmentError(ioc=ioc, provider=self.name, error=f"HTTP {code}")
        except requests.exceptions.SSLError:
            return EnrichmentError(ioc=ioc, provider=self.name, error="SSL/TLS error")
        except requests.exceptions.ConnectionError:
            return EnrichmentError(ioc=ioc, provider=self.name, error="Connection failed")
        except Exception:
            logger.exception(
                "Unexpected error during URLhaus lookup for %s", ioc.value
            )
            return EnrichmentError(
                ioc=ioc, provider=self.name, error="Unexpected error during lookup"
            )


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
