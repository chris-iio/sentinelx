"""ipinfo.io GeoIP + rDNS adapter."""
from __future__ import annotations

from typing import NamedTuple

from .base import BaseHTTPAdapter
from ..models import EnrichmentResult, no_data_result
from app.pipeline.models import IOC, IOCType

IPINFO_BASE = "https://ipinfo.io"
_GEO_SEPARATOR = " \u00b7 "


class IpContextSignals(NamedTuple):
    country_code: str
    city: str
    org: str
    reverse: str
    flags: list[str]


def _ip_context_signals(body: dict) -> IpContextSignals | None:
    country_code = body.get("country", "")
    if not country_code:
        return None
    return IpContextSignals(
        country_code=country_code,
        city=body.get("city", ""),
        org=body.get("org", ""),
        reverse=body.get("hostname", ""),
        flags=[],
    )


def _asn_context(org: str) -> tuple[str, str]:
    """Return display ASN context and ISP name parsed from ipinfo's org field."""
    if not org:
        return "", ""
    asn_num, _sep, isp_name = org.partition(" ")
    asn_display = f"{asn_num} ({isp_name})" if isp_name else asn_num
    return asn_display, isp_name


def _geo_context(country_code: str, city: str, asn_display: str) -> str:
    """Return the compact UI context string without building a temporary parts list."""
    geo = country_code
    if city:
        geo = f"{geo}{_GEO_SEPARATOR}{city}" if geo else city
    if asn_display:
        geo = f"{geo}{_GEO_SEPARATOR}{asn_display}" if geo else asn_display
    return geo


def _raw_stats(
    *,
    country_code: str,
    city: str,
    org: str,
    asname: str,
    reverse: str,
    geo: str,
    flags: list[str],
) -> dict[str, object]:
    """Return the stable IP Context raw_stats envelope."""
    return {
        "country_code": country_code,
        "city": city,
        "as_info": org,
        "asname": asname,
        "reverse": reverse,
        "proxy": False,
        "hosting": False,
        "mobile": False,
        "geo": geo,
        "flags": flags,
    }


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
    signals = _ip_context_signals(body)
    if signals is None:
        # Missing country field — malformed or incomplete response
        return _no_data_result(ioc, provider_name)

    # Pre-format geo string: "CC · City · AS12345 (ISP Name)"
    # Parse the 'org' field: split on first space to get "AS12345" and "ISP Name"
    asn_display, asname = _asn_context(signals.org)
    geo = _geo_context(signals.country_code, signals.city, asn_display)

    return _no_data_result(
        ioc=ioc,
        provider_name=provider_name,
        raw_stats=_raw_stats(
            country_code=signals.country_code,
            city=signals.city,
            org=signals.org,
            asname=asname,
            reverse=signals.reverse,
            geo=geo,
            flags=signals.flags,
        ),
    )


def _no_data_result(
    ioc: IOC,
    provider_name: str,
    raw_stats: dict | None = None,
) -> EnrichmentResult:
    return no_data_result(ioc, provider_name, raw_stats)
