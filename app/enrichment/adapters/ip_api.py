"""ipinfo.io GeoIP + rDNS adapter."""
from __future__ import annotations

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.models import EnrichmentResult, no_data_result
from app.pipeline.models import IOC, IOCType

IPINFO_BASE = "https://ipinfo.io"
_GEO_SEPARATOR = " \u00b7 "


class IPApiAdapter(BaseHTTPAdapter):
    """ipinfo.io GeoIP/rDNS — see _make_pre_raise_hook for private-IP handling."""

    supported_types: frozenset[IOCType] = frozenset((IOCType.IPV4, IOCType.IPV6))
    name = "IP Context"
    requires_api_key = False

    def _build_url(self, ioc: IOC) -> str:
        return f"{IPINFO_BASE}/{ioc.value}/json"

    def _make_pre_raise_hook(self, ioc: IOC):
        def _404_hook(resp):
            # HTTP 404 for private/reserved IPs → no_data (not an error)
            if resp.status_code == 404:
                return _no_data_result(ioc, self.name)
            return None
        return _404_hook

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        return _parse_response(ioc, body, self.name)


def _parse_response(ioc: IOC, body: dict, provider_name: str) -> EnrichmentResult:
    """Parse an ipinfo.io API response into an EnrichmentResult."""
    if not body.get("country"):
        # Missing country field — malformed or incomplete response
        return _no_data_result(ioc, provider_name)

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
        asn_num, _sep, isp_name = org.partition(" ")  # e.g. "AS24940", "ISP Name"
        asn_display = f"{asn_num} ({isp_name})" if isp_name else asn_num
        asname = isp_name
    else:
        asn_display = ""
        asname = ""

    geo = country_code
    if city:
        geo = f"{geo}{_GEO_SEPARATOR}{city}" if geo else city
    if asn_display:
        geo = f"{geo}{_GEO_SEPARATOR}{asn_display}" if geo else asn_display

    return _no_data_result(
        ioc=ioc,
        provider_name=provider_name,
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


def _no_data_result(
    ioc: IOC,
    provider_name: str,
    raw_stats: dict | None = None,
) -> EnrichmentResult:
    return no_data_result(ioc, provider_name, raw_stats)
