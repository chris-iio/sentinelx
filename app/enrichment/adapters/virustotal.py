"""VirusTotal API v3 adapter.

Implements IOC enrichment against the VT API v3 with full HTTP safety controls:
  - SEC-04: timeout=(5, 30) on all requests
  - SEC-05: stream=True + byte counting, 1 MB response cap
  - SEC-06: allow_redirects=False on all requests
  - SEC-07/SEC-16: ALLOWED_API_HOSTS allowlist enforced before every network call

Thread safety: each VTAdapter.__init__() stores state only; a fresh requests.Session
is created inside each lookup() call to avoid shared session race conditions under
ThreadPoolExecutor (Pitfall 3 from research).
"""
from __future__ import annotations

import base64
import datetime
import logging

import requests

from app.enrichment.http_safety import safe_request
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)

VT_BASE = "https://www.virustotal.com/api/v3"

ENDPOINT_MAP: dict[IOCType, object] = {
    IOCType.IPV4: lambda v: f"{VT_BASE}/ip_addresses/{v}",
    IOCType.IPV6: lambda v: f"{VT_BASE}/ip_addresses/{v}",
    IOCType.DOMAIN: lambda v: f"{VT_BASE}/domains/{v}",
    IOCType.URL: lambda v: f"{VT_BASE}/urls/{_url_id(v)}",
    IOCType.MD5: lambda v: f"{VT_BASE}/files/{v}",
    IOCType.SHA1: lambda v: f"{VT_BASE}/files/{v}",
    IOCType.SHA256: lambda v: f"{VT_BASE}/files/{v}",
    # CVE is NOT in ENDPOINT_MAP — VT has no CVE endpoint (Pitfall 5)
}


def _url_id(url: str) -> str:
    """Base64url-encode URL without padding — VT URL identifier format.

    VT URL lookup requires the URL encoded as base64url without trailing '='
    padding. Raw URLs cannot be used as path segments (contain slashes).

    Source: https://docs.virustotal.com/reference/url
    """
    return base64.urlsafe_b64encode(url.encode()).decode().strip("=")


def _parse_response(ioc: IOC, body: dict) -> EnrichmentResult:
    """Parse a VT API v3 success response into an EnrichmentResult.

    Extracts last_analysis_stats and last_analysis_date from response body.
    Converts Unix epoch timestamp to ISO8601. Computes verdict:
      - malicious > 0  -> "malicious"
      - total == 0     -> "no_data"
      - else           -> "clean"

    Args:
        ioc:  The IOC that was queried.
        body: Parsed JSON from VT API response.

    Returns:
        EnrichmentResult with verdict, counts, timestamp, and raw stats.
    """
    attrs = body["data"]["attributes"]
    stats: dict = attrs.get("last_analysis_stats", {})
    last_analysis_date = attrs.get("last_analysis_date")

    scan_date: str | None = None
    if last_analysis_date is not None:
        scan_date = datetime.datetime.fromtimestamp(
            last_analysis_date, tz=datetime.timezone.utc
        ).isoformat()

    malicious = stats.get("malicious", 0)
    # Exclude timeout and type-unsupported from total engine count
    total = sum(stats.values()) - stats.get("timeout", 0) - stats.get("type-unsupported", 0)

    if malicious > 0:
        verdict = "malicious"
    elif total == 0:
        verdict = "no_data"
    else:
        verdict = "clean"

    # Extract top 5 unique malicious detection names from full analysis results
    analysis_results: dict = attrs.get("last_analysis_results", {})
    seen: set[str] = set()
    top_detections: list[str] = []
    for engine_result in analysis_results.values():
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

    return EnrichmentResult(
        ioc=ioc,
        provider="VirusTotal",
        verdict=verdict,
        detection_count=malicious,
        total_engines=total,
        scan_date=scan_date,
        raw_stats=enriched_stats,
    )


class VTAdapter:
    """Adapter for the VirusTotal API v3.

    Maps IOC types to VT API v3 endpoints, enforces all HTTP safety controls,
    and returns typed EnrichmentResult or EnrichmentError objects.

    Thread safety: creates a fresh requests.Session per lookup() call.
    Do NOT share one VTAdapter instance across threads with a shared Session.
    The recommended pattern is one adapter per enrichment job.

    Args:
        api_key:       VirusTotal API key for x-apikey header.
        allowed_hosts: SSRF allowlist — only these hostnames may be contacted.
    """

    # Types supported by VT API v3 (derived from ENDPOINT_MAP keys)
    # CVE is excluded — VT has no CVE endpoint (Pitfall 5)
    supported_types = {
        IOCType.IPV4, IOCType.IPV6, IOCType.DOMAIN, IOCType.URL,
        IOCType.MD5, IOCType.SHA1, IOCType.SHA256,
    }

    name = "VirusTotal"
    requires_api_key = True

    def __init__(self, api_key: str, allowed_hosts: list[str]) -> None:
        self._api_key = api_key
        self._allowed_hosts = allowed_hosts
        self._session = requests.Session()
        self._session.headers.update({
            "x-apikey": self._api_key,
            "Accept": "application/json",
        })

    def is_configured(self) -> bool:
        """Return True when a non-empty API key has been provided."""
        return bool(self._api_key)

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        """Enrich a single IOC using the VirusTotal API v3.

        Returns EnrichmentError immediately for CVE (not supported by VT).
        For all other supported types: builds the VT endpoint URL, validates
        against the SSRF allowlist, makes a request with full safety controls,
        and parses the response.

        Args:
            ioc: The IOC to look up.

        Returns:
            EnrichmentResult on success or 404 (no_data).
            EnrichmentError on unsupported type, network failure, or HTTP error.
        """
        if ioc.type not in ENDPOINT_MAP:
            return EnrichmentError(
                ioc=ioc, provider="VirusTotal", error="Unsupported type"
            )

        endpoint_fn = ENDPOINT_MAP[ioc.type]
        url = endpoint_fn(ioc.value)  # type: ignore[call-arg]

        def _vt_hook(resp):
            if resp.status_code == 404:
                return EnrichmentResult(
                    ioc=ioc,
                    provider="VirusTotal",
                    verdict="no_data",
                    detection_count=0,
                    total_engines=0,
                    scan_date=None,
                    raw_stats={},
                )
            if resp.status_code == 429:
                return EnrichmentError(
                    ioc=ioc, provider="VirusTotal",
                    error="Rate limit exceeded (429)",
                )
            if resp.status_code in (401, 403):
                return EnrichmentError(
                    ioc=ioc, provider="VirusTotal",
                    error=f"Authentication error ({resp.status_code})",
                )
            return None

        result = safe_request(
            self._session, url, self._allowed_hosts, ioc, "VirusTotal",
            pre_raise_hook=_vt_hook,
        )
        if not isinstance(result, dict):
            return result
        return _parse_response(ioc, result)
