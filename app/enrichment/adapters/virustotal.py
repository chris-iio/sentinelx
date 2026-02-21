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
import json
from urllib.parse import urlparse

import requests
import requests.exceptions

from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType

VT_BASE = "https://www.virustotal.com/api/v3"
TIMEOUT = (5, 30)  # (connect, read) — SEC-04
MAX_RESPONSE_BYTES = 1 * 1024 * 1024  # 1 MB cap — SEC-05

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


def _validate_endpoint(url: str, allowed_hosts: list[str]) -> None:
    """Raise ValueError if endpoint hostname is not on the SSRF allowlist.

    Enforces SEC-16: no outbound calls to hosts outside ALLOWED_API_HOSTS.
    Called before every network request.
    """
    parsed = urlparse(url)
    if parsed.hostname not in allowed_hosts:
        raise ValueError(
            f"Endpoint hostname {parsed.hostname!r} not in allowed_hosts "
            f"(SSRF allowlist SEC-16). Allowed: {allowed_hosts!r}"
        )


def _read_limited(resp: requests.Response) -> dict:
    """Read streaming response with byte cap (SEC-05).

    Reads response body in 8 KB chunks. Raises ValueError if total
    exceeds MAX_RESPONSE_BYTES before completing. Returns parsed JSON.

    Args:
        resp: An open streaming requests.Response.

    Raises:
        ValueError: If response body exceeds MAX_RESPONSE_BYTES.
        json.JSONDecodeError: If body is not valid JSON.
    """
    chunks: list[bytes] = []
    total = 0
    for chunk in resp.iter_content(chunk_size=8192):
        total += len(chunk)
        if total > MAX_RESPONSE_BYTES:
            raise ValueError(
                f"Response exceeded size limit of {MAX_RESPONSE_BYTES} bytes (SEC-05)"
            )
        chunks.append(chunk)
    return json.loads(b"".join(chunks))


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

    return EnrichmentResult(
        ioc=ioc,
        provider="VirusTotal",
        verdict=verdict,
        detection_count=malicious,
        total_engines=total,
        scan_date=scan_date,
        raw_stats=stats,
    )


def _map_http_error(ioc: IOC, err: requests.exceptions.HTTPError) -> EnrichmentResult | EnrichmentError:
    """Map HTTP error codes to typed enrichment results.

    VT 404 semantics: "VirusTotal has never seen this IOC" — not an error.
    Returns EnrichmentResult(verdict="no_data") for 404 (Pitfall 1).

    Args:
        ioc: The IOC that was queried.
        err: The HTTPError raised by raise_for_status().

    Returns:
        EnrichmentResult for 404; EnrichmentError for all other codes.
    """
    response = err.response
    code: int | str = response.status_code if response is not None else "unknown"

    if code == 404:
        # 404 = VT has no record — meaningful information, not a failure
        return EnrichmentResult(
            ioc=ioc,
            provider="VirusTotal",
            verdict="no_data",
            detection_count=0,
            total_engines=0,
            scan_date=None,
            raw_stats={},
        )
    if code == 429:
        return EnrichmentError(ioc=ioc, provider="VirusTotal", error="Rate limit exceeded (429)")
    if code in (401, 403):
        return EnrichmentError(
            ioc=ioc, provider="VirusTotal", error=f"Authentication error ({code})"
        )
    return EnrichmentError(ioc=ioc, provider="VirusTotal", error=f"HTTP {code}")


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

    def __init__(self, api_key: str, allowed_hosts: list[str]) -> None:
        self._api_key = api_key
        self._allowed_hosts = allowed_hosts

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

        try:
            _validate_endpoint(url, self._allowed_hosts)
        except ValueError as exc:
            return EnrichmentError(ioc=ioc, provider="VirusTotal", error=str(exc))

        session = requests.Session()
        session.headers.update({"x-apikey": self._api_key, "Accept": "application/json"})

        try:
            resp = session.get(
                url,
                timeout=TIMEOUT,          # SEC-04
                allow_redirects=False,    # SEC-06
                stream=True,              # SEC-05 setup
            )
            # Handle error status codes before reading body (avoids JSON parse
            # errors on error responses that have no/invalid body).
            # 404 is special: check it first and return "no_data" (Pitfall 1).
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
            # For other 4xx/5xx: raise before reading body so _map_http_error fires
            resp.raise_for_status()
            body = _read_limited(resp)  # SEC-05: byte cap enforced here (success only)
            return _parse_response(ioc, body)
        except requests.exceptions.Timeout:
            return EnrichmentError(ioc=ioc, provider="VirusTotal", error="Timeout")
        except requests.exceptions.HTTPError as exc:
            return _map_http_error(ioc, exc)
        except Exception as exc:
            return EnrichmentError(ioc=ioc, provider="VirusTotal", error=str(exc))
