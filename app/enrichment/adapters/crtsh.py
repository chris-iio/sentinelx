"""CrtSh certificate transparency adapter.

Implements domain enrichment via the crt.sh Certificate Transparency search API.
Returns CT history (cert count, date range, subdomains from SANs) without requiring
an API key. Applies all HTTP safety controls matching the provider pattern:
  - SEC-04: timeout=(5, 30) on all requests
  - SEC-05: stream=True + byte counting, 1 MB response cap via read_limited()
  - SEC-06: allow_redirects=False on all requests
  - SEC-16: SSRF allowlist enforced via validate_endpoint() before every network call

crt.sh API behavior:
  - GET https://crt.sh/?q={domain}&output=json
  - 200 + list: Returns certificate records with name_value (SANs), not_before dates
  - 200 + empty list: No certs found -> verdict=no_data, raw_stats={}
  - 502: Common transient error -> EnrichmentError("HTTP 502")
  - Other HTTP errors: -> EnrichmentError("HTTP {code}")
  - Timeout: -> EnrichmentError("Timeout")

Verdict semantics:
  - All responses: verdict=no_data — CT history is informational (not a threat signal)
  - detection_count=0, total_engines=0, scan_date=None always

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

CRTSH_BASE = "https://crt.sh"

# Maximum number of unique subdomains to include in raw_stats
_SUBDOMAIN_CAP = 50


class CrtShAdapter:
    """Adapter for the crt.sh Certificate Transparency search API.

    Supports domain IOC lookups using the zero-auth crt.sh public endpoint.
    Returns CT history data: certificate count, first/last issuance dates, and
    a deduplicated list of subdomains observed in Subject Alternative Names.

    All responses produce verdict=no_data — CT history is informational context
    for analysts, not a threat detection signal.

    No API key required — crt.sh is fully public.

    Thread safety: uses a persistent requests.Session (self._session) created in __init__.
    The session is reused across lookup() calls for TCP connection pooling.

    Args:
        allowed_hosts: SSRF allowlist -- only these hostnames may be contacted.
                       Must include "crt.sh" for production use.
    """

    supported_types: frozenset[IOCType] = frozenset({IOCType.DOMAIN})
    name = "Cert History"
    requires_api_key = False

    def __init__(self, allowed_hosts: list[str]) -> None:
        self._allowed_hosts = allowed_hosts
        self._session = requests.Session()

    def is_configured(self) -> bool:
        """Always returns True -- crt.sh requires no API key."""
        return True

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        """Enrich a single domain IOC via the crt.sh CT search API.

        Returns EnrichmentError immediately for non-domain types.
        Validates the crt.sh endpoint against the SSRF allowlist before any
        network call. Makes a GET request with full safety controls and
        parses the certificate records.

        Response semantics:
          - Non-empty list: cert_count, date range, subdomains extracted
          - Empty list []:  verdict=no_data, raw_stats={}
          - HTTP error:     EnrichmentError("HTTP {code}")
          - Timeout:        EnrichmentError("Timeout")

        Args:
            ioc: The IOC to look up. Must be DOMAIN type.

        Returns:
            EnrichmentResult on success (always verdict=no_data).
            EnrichmentError on unsupported type, SSRF block, or network failure.
        """
        if ioc.type not in self.supported_types:
            return EnrichmentError(
                ioc=ioc, provider=self.name, error="Unsupported type"
            )

        url = f"{CRTSH_BASE}/?q={ioc.value}&output=json"

        try:
            validate_endpoint(url, self._allowed_hosts)
        except ValueError as exc:
            return EnrichmentError(ioc=ioc, provider=self.name, error=str(exc))

        try:
            resp = self._session.get(
                url,
                timeout=TIMEOUT,           # SEC-04
                allow_redirects=False,     # SEC-06
                stream=True,               # SEC-05 setup
            )
            resp.raise_for_status()
            body = read_limited(resp)      # SEC-05: byte cap enforced; returns parsed JSON list
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
                "Unexpected error during crt.sh lookup for %s", ioc.value
            )
            return EnrichmentError(
                ioc=ioc, provider=self.name, error="Unexpected error during lookup"
            )


def _parse_response(ioc: IOC, body: list, provider_name: str) -> EnrichmentResult:
    """Parse a crt.sh API response into an EnrichmentResult.

    Extracts certificate count, issuance date range, and a normalized
    subdomain list from all Subject Alternative Name (name_value) fields.

    Subdomain normalization:
      - Wildcards (*.example.com) are stripped to bare domain (example.com)
      - All entries are lowercased
      - Duplicates are removed
      - Results are sorted alphabetically
      - Capped at _SUBDOMAIN_CAP (50) entries

    Args:
        ioc:           The IOC that was queried.
        body:          Parsed JSON list from crt.sh API response.
        provider_name: Provider name string for result construction.

    Returns:
        EnrichmentResult with verdict "no_data" always.
        raw_stats is {} for empty responses, or contains cert_count/earliest/latest/subdomains.
    """
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
