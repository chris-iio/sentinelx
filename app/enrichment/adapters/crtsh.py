"""crt.sh certificate transparency adapter."""
from __future__ import annotations

import logging

from app.enrichment.adapters.base import BaseHTTPAdapter
from app.enrichment.http_safety import safe_request
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)

CRTSH_BASE = "https://crt.sh"

# Maximum number of unique subdomains to include in raw_stats
_SUBDOMAIN_CAP = 50


class CrtShAdapter(BaseHTTPAdapter):
    """crt.sh CT search endpoint — overrides lookup() for JSON-list responses."""

    supported_types: frozenset[IOCType] = frozenset({IOCType.DOMAIN})
    name = "Cert History"
    requires_api_key = False

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        if ioc.type not in self.supported_types:
            return EnrichmentError(
                ioc=ioc, provider=self.name, error="Unsupported type",
            )

        url = self._build_url(ioc)
        result = safe_request(
            self._session, url, self._allowed_hosts, ioc, self.name,
        )
        if isinstance(result, EnrichmentError):
            return result
        return _parse_response(ioc, result, self.name)

    def _build_url(self, ioc: IOC) -> str:
        return f"{CRTSH_BASE}/?q={ioc.value}&output=json"

    def _parse_response(self, ioc: IOC, body: dict) -> EnrichmentResult:
        # Not called by our lookup() override, but required by the abstract interface.
        return _parse_response(ioc, body, self.name)  # type: ignore[arg-type]


def _parse_response(ioc: IOC, body: list, provider_name: str) -> EnrichmentResult:
    # Empty response: no certificates found
    if not body:
        return EnrichmentResult(
            ioc=ioc,
            provider=provider_name,
            verdict="no_data",
            detection_count=0,
            total_engines=0,
            scan_date=None,
            raw_stats={},
        )

    cert_count = len(body)

    # Collect dates from not_before field (skip null/missing entries)
    dates: list[str] = [
        entry["not_before"][:10]
        for entry in body
        if entry.get("not_before")
    ]
    earliest = min(dates) if dates else ""
    latest = max(dates) if dates else ""

    # Collect subdomains from name_value (SANs), normalizing each entry
    subdomain_set: set[str] = set()
    for entry in body:
        name_value = entry.get("name_value")
        if not name_value:
            continue
        for raw_name in name_value.split("\n"):
            cleaned = raw_name.strip().lstrip("*.").lower()
            if cleaned:
                subdomain_set.add(cleaned)

    # Sort alphabetically, cap at _SUBDOMAIN_CAP
    subdomains: list[str] = sorted(subdomain_set)[:_SUBDOMAIN_CAP]

    return EnrichmentResult(
        ioc=ioc,
        provider=provider_name,
        verdict="no_data",
        detection_count=0,
        total_engines=0,
        scan_date=None,
        raw_stats={
            "cert_count": cert_count,
            "earliest": earliest,
            "latest": latest,
            "subdomains": subdomains,
        },
    )
