"""ipinfo.io GeoIP + rDNS adapter."""
from __future__ import annotations

import logging

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.models import EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)

IPINFO_BASE = "https://ipinfo.io"


class IPApiAdapter(BaseHTTPAdapter):
    """ipinfo.io GeoIP/rDNS — see _make_pre_raise_hook for private-IP handling."""

    supported_types: frozenset[IOCType] = frozenset({IOCType.IPV4, IOCType.IPV6})
    name = "IP Context"
    requires_api_key = False

    def _build_url(self, ioc: IOC) -> str:
        return f"{IPINFO_BASE}/{ioc.value}/json"

    def _make_pre_raise_hook(self, ioc: IOC):
        def _404_hook(resp):
            # HTTP 404 for private/reserved IPs → no_data (not an error)
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
    """Parse an ipinfo.io API response into an EnrichmentResult."""
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
