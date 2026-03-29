"""ipinfo.io GeoIP + rDNS adapter.

Implements IP context enrichment against the ipinfo.io free API. Delegates all
HTTP safety controls to safe_request() in http_safety.py.

ipinfo.io API behavior:
  - GET https://ipinfo.io/{ip}/json
  - HTTP 200 + body contains "country": IP data returned (public/routable IP)
  - HTTP 404: Private/reserved IP or invalid input (not a JSON "status" field)
  - HTTP 429: Rate limited -> EnrichmentError("HTTP 429")
  - IMPORTANT: Unlike ip-api.com, there is no "status" field in the response.
    The presence of the "country" key indicates a successful public IP lookup.
    404 is the authoritative indicator for private/reserved IPs.

CRITICAL DESIGN NOTES:
  - Base URL is https:// — ipinfo.io free tier supports HTTPS.
  - This adapter provides contextual intelligence only; verdict is always no_data.
    IP geolocation/context is informational, not a threat verdict.
  - The 'geo' field is pre-formatted in Python as "CC · City · ASN (ISP)" using
    U+00B7 (middle dot) as separator, allowing the frontend to render it directly.

No API key required — ipinfo.io free tier is a public zero-auth endpoint.
Rate limit: 50,000 requests/month on free tier (HTTP 429 on violation).
"""
from __future__ import annotations

import logging

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.models import EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)

IPINFO_BASE = "https://ipinfo.io"


class IPApiAdapter(BaseHTTPAdapter):
    """Adapter for the ipinfo.io GeoIP/rDNS API.

    Extends BaseHTTPAdapter for IP context enrichment against the ipinfo.io
    free API. All HTTP safety controls (SSRF allowlist, size cap, timeouts) are
    inherited.

    Supports IP IOC lookups (IPv4 and IPv6) using the zero-auth ipinfo.io
    public HTTPS endpoint. Provides geographic location, reverse DNS, and ASN
    information.

    This adapter NEVER assigns threat verdicts. All lookups return no_data
    because IP context is purely informational — it enriches the analyst's
    view without making a malicious/clean determination.

    - Public IP (HTTP 200 with 'country' field) -> verdict=no_data with geo/rDNS/ASN
    - Private/reserved IP (HTTP 404)            -> verdict=no_data with empty raw_stats
    - HTTP errors                               -> EnrichmentError

    IMPORTANT: ipinfo.io does not use a "status" field in its JSON response.
    Success is determined by HTTP 200 + presence of the "country" key.
    Private/reserved IPs return HTTP 404 (not HTTP 200 with a failure status).

    No API key required — ipinfo.io free tier is fully public.
    Rate limit: 50,000 requests/month (429 response when exceeded).

    Thread safety: a persistent requests.Session is created by BaseHTTPAdapter.__init__
    and reused across lookup() calls for TCP connection pooling.

    Args:
        allowed_hosts: SSRF allowlist -- only these hostnames may be contacted.
    """

    supported_types: frozenset[IOCType] = frozenset({IOCType.IPV4, IOCType.IPV6})
    name = "IP Context"
    requires_api_key = False

    def _build_url(self, ioc: IOC) -> str:
        return f"{IPINFO_BASE}/{ioc.value}/json"

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
    """Parse an ipinfo.io API response into an EnrichmentResult.

    Checks for the presence of the "country" key to distinguish public IPs
    (success) from malformed/incomplete responses. Both cases return
    verdict=no_data — absent country data is not a hard error.

    Note: HTTP 404 responses (private/reserved IPs) are handled in lookup()
    before this function is called. This function only processes HTTP 200 bodies.

    For successful responses, extracts geo/rDNS/ASN data and pre-formats:
    - geo: "CC · City · ASN (ISP)" string using middle dot (U+00B7) separators
    - flags: always [] (ipinfo.io free tier does not provide flag classification)
    - proxy/hosting/mobile: always False (not available in free tier)

    The "org" field from ipinfo.io is "AS{number} {ISP Name}" — split on first
    space to extract the ASN number and ISP name, same as ip-api.com's "as" field.

    Args:
        ioc:           The IOC that was queried.
        body:          Parsed JSON from ipinfo.io API response.
        provider_name: Provider name string for result construction.

    Returns:
        EnrichmentResult with verdict "no_data" and populated raw_stats (or
        empty raw_stats for responses missing the "country" field).
    """
    if not body.get("country"):
        # Missing country field — malformed or incomplete response
        return EnrichmentResult(
            ioc=ioc,
            provider=provider_name,
            verdict="no_data",
            detection_count=0,
            total_engines=0,
            scan_date=None,
            raw_stats={},
        )

    country_code = body.get("country", "")
    city = body.get("city", "")
    org = body.get("org", "")   # e.g. "AS24940 Hetzner Online GmbH"
    reverse = body.get("hostname", "")

    # ipinfo.io free tier does not provide proxy/hosting/mobile classification
    proxy = False
    hosting = False
    mobile = False
    flags: list[str] = []

    # Pre-format geo string: "CC · City · AS12345 (ISP Name)"
    # Parse the 'org' field: split on first space to get "AS12345" and "ISP Name"
    if org:
        parts = org.split(" ", 1)
        asn_num = parts[0]  # e.g. "AS24940"
        isp_name = parts[1] if len(parts) > 1 else ""
        asn_display = f"{asn_num} ({isp_name})" if isp_name else asn_num
        asname = isp_name
    else:
        asn_display = ""
        asname = ""

    sep = " \u00b7 "  # middle dot with spaces (U+00B7)
    geo_parts = [p for p in (country_code, city, asn_display) if p]
    geo = sep.join(geo_parts)

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
            "as_info": org,
            "asname": asname,
            "reverse": reverse,
            "proxy": proxy,
            "hosting": hosting,
            "mobile": mobile,
            "geo": geo,
            "flags": flags,
        },
    )
