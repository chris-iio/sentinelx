"""ip-api.com GeoIP + rDNS + proxy flags adapter.

Implements IP context enrichment against the ip-api.com free API with full HTTP
safety controls matching the ShodanAdapter pattern:
  - SEC-04: timeout=(5, 30) on all requests
  - SEC-05: stream=True + byte counting, 1 MB response cap
  - SEC-06: allow_redirects=False on all requests
  - SEC-07/SEC-16: ALLOWED_API_HOSTS allowlist enforced before every network call

ip-api.com API behavior:
  - GET http://ip-api.com/json/{ip}?fields=status,message,countryCode,...
  - HTTP 200 + body.status == "success": IP data returned (public/routable IP)
  - HTTP 200 + body.status == "fail": Private/reserved IP or bad input
  - HTTP 429: Rate limited -> EnrichmentError("HTTP 429")
  - IMPORTANT: Always returns HTTP 200 for both success and fail cases.
    The status field in the JSON body is the authoritative indicator.

CRITICAL DESIGN NOTES:
  - Base URL is http:// (not https://) — the free tier does not support HTTPS.
  - This adapter provides contextual intelligence only; verdict is always no_data.
    IP geolocation/context is informational, not a threat verdict.
  - The 'geo' field is pre-formatted in Python as "CC · City · ASN (ISP)" using
    U+00B7 (middle dot) as separator, allowing the frontend to render it directly.
  - The 'flags' field is pre-filtered to contain only the names of boolean flags
    that are True (proxy, hosting, mobile), making frontend rendering trivial.

No API key required — ip-api.com free tier is a public zero-auth endpoint.
Rate limit: 45 requests/minute on free tier (HTTP 429 on violation).

Thread safety: a fresh requests.get call is used per lookup() call (no shared Session).
"""
from __future__ import annotations

import logging

import requests
import requests.exceptions

from app.enrichment.http_safety import TIMEOUT, read_limited, validate_endpoint
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)

IP_API_BASE = "http://ip-api.com/json"

# Fields requested from the API — minimizes response size and avoids unused data
_FIELDS = "status,message,countryCode,city,as,asname,reverse,proxy,hosting,mobile"

# Boolean flag field names extracted from the API response
_FLAG_FIELDS = ("proxy", "hosting", "mobile")


class IPApiAdapter:
    """Adapter for the ip-api.com GeoIP/rDNS/proxy detection API.

    Supports IP IOC lookups (IPv4 and IPv6) using the zero-auth ip-api.com
    public endpoint. Provides geographic location, reverse DNS, ASN, and
    proxy/hosting/mobile classification.

    This adapter NEVER assigns threat verdicts. All lookups return no_data
    because IP context is purely informational — it enriches the analyst's
    view without making a malicious/clean determination.

    - Public IP (status="success") -> verdict=no_data with full geo/rDNS/flags
    - Private/reserved IP (status="fail") -> verdict=no_data with empty raw_stats
    - HTTP errors -> EnrichmentError

    IMPORTANT: ip-api.com returns HTTP 200 for both success and fail cases.
    The JSON body's status field must be checked after parsing.

    No API key required — ip-api.com free tier is fully public.
    Rate limit: 45 requests/minute (429 response when exceeded).

    Thread safety: uses a standalone requests.get call per lookup() invocation.
    No shared session state between calls.

    Args:
        allowed_hosts: SSRF allowlist -- only these hostnames may be contacted.
    """

    supported_types: frozenset[IOCType] = frozenset({IOCType.IPV4, IOCType.IPV6})
    name = "IP Context"
    requires_api_key = False

    def __init__(self, allowed_hosts: list[str]) -> None:
        self._allowed_hosts = allowed_hosts

    def is_configured(self) -> bool:
        """Always returns True -- ip-api.com requires no API key."""
        return True

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        """Enrich a single IP IOC using the ip-api.com API.

        Returns EnrichmentError immediately for non-IP types.
        Validates the ip-api.com endpoint against the SSRF allowlist before any
        network call. Makes a GET request with full safety controls, parses the
        response, and checks the body.status field.

        Response semantics:
          - HTTP 200 + body.status == "success" -> EnrichmentResult(verdict=no_data)
            with geo/rDNS/ASN/flags populated in raw_stats
          - HTTP 200 + body.status == "fail"    -> EnrichmentResult(verdict=no_data)
            with empty raw_stats (private/reserved IP is not a lookup failure)
          - HTTP 429 (rate limit)               -> EnrichmentError("HTTP 429")
          - Network timeout                     -> EnrichmentError("Timeout")
          - Other HTTP errors                   -> EnrichmentError("HTTP {code}")

        Args:
            ioc: The IOC to look up. Must be IPv4 or IPv6.

        Returns:
            EnrichmentResult on success (including private IP no_data).
            EnrichmentError on unsupported type, SSRF block, or network failure.
        """
        if ioc.type not in self.supported_types:
            return EnrichmentError(
                ioc=ioc, provider=self.name, error="Unsupported type"
            )

        url = f"{IP_API_BASE}/{ioc.value}?fields={_FIELDS}"

        try:
            validate_endpoint(url, self._allowed_hosts)
        except ValueError as exc:
            return EnrichmentError(ioc=ioc, provider=self.name, error=str(exc))

        try:
            resp = requests.get(
                url,
                timeout=TIMEOUT,           # SEC-04
                allow_redirects=False,     # SEC-06
                stream=True,               # SEC-05 setup
            )
            resp.raise_for_status()
            body = read_limited(resp)     # SEC-05: byte cap enforced
            return _parse_response(ioc, body, self.name)
        except requests.exceptions.Timeout:
            return EnrichmentError(ioc=ioc, provider=self.name, error="Timeout")
        except requests.exceptions.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else "unknown"
            return EnrichmentError(ioc=ioc, provider=self.name, error=f"HTTP {code}")
        except Exception:
            logger.exception(
                "Unexpected error during ip-api.com lookup for %s", ioc.value
            )
            return EnrichmentError(
                ioc=ioc, provider=self.name, error="Unexpected error during lookup"
            )


def _parse_response(ioc: IOC, body: dict, provider_name: str) -> EnrichmentResult:
    """Parse an ip-api.com API response into an EnrichmentResult.

    Checks body.status to distinguish public IPs (success) from private/reserved
    IPs (fail). Both cases return verdict=no_data — private IPs are not errors.

    For successful responses, extracts geo/rDNS/ASN data and pre-formats:
    - geo: "CC · City · ASN (ISP)" string using middle dot (U+00B7) separators
    - flags: list of flag names where the flag value is True (e.g. ["proxy", "hosting"])

    Args:
        ioc:           The IOC that was queried.
        body:          Parsed JSON from ip-api.com API response.
        provider_name: Provider name string for result construction.

    Returns:
        EnrichmentResult with verdict "no_data" and populated raw_stats (or
        empty raw_stats for private/reserved IPs).
    """
    if body.get("status") != "success":
        # Private/reserved IP or malformed query — not a lookup failure
        return EnrichmentResult(
            ioc=ioc,
            provider=provider_name,
            verdict="no_data",
            detection_count=0,
            total_engines=0,
            scan_date=None,
            raw_stats={},
        )

    country_code = body.get("countryCode", "")
    city = body.get("city", "")
    as_full = body.get("as", "")   # e.g. "AS24940 Hetzner Online GmbH"
    asname = body.get("asname", "")
    reverse = body.get("reverse", "")
    proxy = body.get("proxy", False)
    hosting = body.get("hosting", False)
    mobile = body.get("mobile", False)

    # Pre-format geo string: "CC · City · AS12345 (ISP Name)"
    # Parse the 'as' field: split on first space to get "AS12345" and "ISP Name"
    if as_full:
        parts = as_full.split(" ", 1)
        asn_num = parts[0]  # e.g. "AS24940"
        isp_name = parts[1] if len(parts) > 1 else ""
        asn_display = f"{asn_num} ({isp_name})" if isp_name else asn_num
    else:
        asn_display = ""

    sep = " \u00b7 "  # middle dot with spaces (U+00B7)
    geo_parts = [p for p in (country_code, city, asn_display) if p]
    geo = sep.join(geo_parts)

    # Pre-filter flags: only include names of flags that are True
    flags = [flag for flag in _FLAG_FIELDS if body.get(flag, False)]

    return EnrichmentResult(
        ioc=ioc,
        provider=provider_name,
        verdict="no_data",
        detection_count=0,
        total_engines=0,
        scan_date=None,
        raw_stats={
            "country_code": country_code,
            "city": city,
            "as_info": as_full,
            "asname": asname,
            "reverse": reverse,
            "proxy": proxy,
            "hosting": hosting,
            "mobile": mobile,
            "geo": geo,
            "flags": flags,
        },
    )
