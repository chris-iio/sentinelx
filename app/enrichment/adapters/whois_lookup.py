"""WHOIS registration data lookup adapter.

Implements WHOIS lookups for domain IOCs using python-whois, returning
registrar, creation date, expiry date, name servers, and org in raw_stats.

Design notes:
  - WHOIS uses port 43 directly — NOT HTTP. Do NOT import or use the HTTP
    safety module. Its endpoint validation, timeout, and read-limiting controls
    are HTTP-specific and irrelevant here.
  - No API key required — queries public WHOIS servers.
  - allowed_hosts parameter is accepted for API compatibility with the Provider
    protocol (other adapters pass it in from setup.py) but is intentionally
    ignored here. WHOIS does not make HTTP calls; there is no SSRF surface.
  - verdict is always 'no_data' — WHOIS records are informational context, not
    threat signals.
  - Datetime polymorphism: creation_date and expiration_date can be a datetime,
    a list of datetimes, None, or a string. This adapter normalises them to
    ISO-8601 strings (first element if list) or None.
  - name_servers can be None (default to empty list) or a list of strings.

Error handling mapping:
  - WhoisDomainNotFoundError → EnrichmentResult(verdict='no_data')
  - WhoisQuotaExceededError  → EnrichmentError
  - WhoisCommandFailedError  → EnrichmentError
  - FailedParsingWhoisOutputError → EnrichmentResult with lookup_errors
  - UnknownTldError          → EnrichmentResult with lookup_errors
  - Any other exception      → EnrichmentError (logged)

Thread safety: each lookup() call creates a fresh whois.whois() request
(no shared state).
"""
from __future__ import annotations

import logging
from datetime import datetime

import whois
from whois.exceptions import (
    FailedParsingWhoisOutputError,
    UnknownTldError,
    WhoisCommandFailedError,
    WhoisDomainNotFoundError,
    WhoisQuotaExceededError,
)

from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)


def _normalise_datetime(value: datetime | list[datetime] | str | None) -> str | None:
    """Normalise a WHOIS date field to an ISO-8601 string or None.

    python-whois returns date fields as:
      - a single datetime object
      - a list of datetime objects (takes the first)
      - a string (returned as-is)
      - None

    Returns:
        ISO-8601 formatted string, the raw string value, or None.
    """
    if value is None:
        return None
    if isinstance(value, list):
        if not value:
            return None
        value = value[0]
    if isinstance(value, datetime):
        return value.isoformat()
    # str fallback — return as-is
    return str(value)


class WhoisAdapter:
    """Adapter for WHOIS registration data lookups using python-whois.

    Supports DOMAIN IOC type only. Returns registrar, creation date, expiry
    date, name servers, and organisation in raw_stats; never assigns a threat
    verdict (verdict is always 'no_data').

    No API key required — queries public WHOIS servers on port 43. No HTTP
    calls are made.

    WHOIS resolution goes directly to port 43. This adapter intentionally does
    NOT use HTTP safety controls (endpoint validation, timeout tuples, read
    limiting), which apply only to HTTP/HTTPS traffic.

    Args:
        allowed_hosts: Accepted for API compatibility with the Provider protocol
            but unused. WHOIS does not make HTTP calls, so SSRF allowlisting is
            not applicable.
    """

    name = "WHOIS"
    supported_types: frozenset[IOCType] = frozenset({IOCType.DOMAIN})
    requires_api_key = False

    def __init__(self, allowed_hosts: list[str]) -> None:
        # Accepted for API compatibility with Provider protocol; intentionally unused.
        # WHOIS uses port 43 directly — no HTTP, no SSRF surface.
        pass

    def is_configured(self) -> bool:
        """Always returns True — no API key or configuration required."""
        return True

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        """Perform WHOIS lookup for a domain IOC.

        Queries WHOIS registration data for the domain using python-whois.
        Extracts registrar, creation_date, expiration_date, name_servers,
        and org from the response.

        Error handling:
          - WhoisDomainNotFoundError → no_data result (not an error)
          - WhoisQuotaExceededError  → EnrichmentError (rate limited)
          - WhoisCommandFailedError  → EnrichmentError (command failure)
          - FailedParsingWhoisOutputError → result with lookup_errors
          - UnknownTldError          → result with lookup_errors
          - Any other exception      → EnrichmentError (logged)

        Returns:
            EnrichmentResult with verdict='no_data' and raw_stats containing
            'registrar', 'creation_date', 'expiration_date', 'name_servers',
            'org', and 'lookup_errors'.

            EnrichmentError for unsupported IOC types, quota/command failures,
            or unexpected errors.
        """
        if ioc.type not in self.supported_types:
            return EnrichmentError(
                ioc=ioc,
                provider=self.name,
                error="Unsupported type",
            )

        try:
            w = whois.whois(ioc.value)
        except WhoisDomainNotFoundError:
            # Domain not found in WHOIS — expected outcome, not an error.
            return EnrichmentResult(
                ioc=ioc,
                provider=self.name,
                verdict="no_data",
                detection_count=0,
                total_engines=0,
                scan_date=None,
                raw_stats={
                    "registrar": None,
                    "creation_date": None,
                    "expiration_date": None,
                    "name_servers": [],
                    "org": None,
                    "lookup_errors": [],
                },
            )
        except (FailedParsingWhoisOutputError, UnknownTldError) as exc:
            # Parse/TLD issues — return result with error noted, not a hard failure.
            return EnrichmentResult(
                ioc=ioc,
                provider=self.name,
                verdict="no_data",
                detection_count=0,
                total_engines=0,
                scan_date=None,
                raw_stats={
                    "registrar": None,
                    "creation_date": None,
                    "expiration_date": None,
                    "name_servers": [],
                    "org": None,
                    "lookup_errors": [str(exc)],
                },
            )
        except WhoisQuotaExceededError:
            return EnrichmentError(
                ioc=ioc,
                provider=self.name,
                error="WHOIS quota exceeded",
            )
        except WhoisCommandFailedError:
            return EnrichmentError(
                ioc=ioc,
                provider=self.name,
                error="WHOIS command failed",
            )
        except Exception:
            logger.exception(
                "Unexpected error during WHOIS lookup for %s",
                ioc.value,
            )
            return EnrichmentError(
                ioc=ioc,
                provider=self.name,
                error="Unexpected WHOIS lookup error",
            )

        lookup_errors: list[str] = []

        # Extract and normalise fields, handling parse/TLD errors gracefully.
        try:
            registrar = w.registrar
        except Exception:
            registrar = None
            lookup_errors.append("registrar: parse error")

        try:
            creation_date = _normalise_datetime(w.creation_date)
        except Exception:
            creation_date = None
            lookup_errors.append("creation_date: parse error")

        try:
            expiration_date = _normalise_datetime(w.expiration_date)
        except Exception:
            expiration_date = None
            lookup_errors.append("expiration_date: parse error")

        try:
            raw_ns = w.name_servers
            name_servers = list(raw_ns) if raw_ns is not None else []
        except Exception:
            name_servers = []
            lookup_errors.append("name_servers: parse error")

        try:
            org = w.org
        except Exception:
            org = None
            lookup_errors.append("org: parse error")

        raw_stats: dict = {
            "registrar": registrar,
            "creation_date": creation_date,
            "expiration_date": expiration_date,
            "name_servers": name_servers,
            "org": org,
            "lookup_errors": lookup_errors,
        }

        return EnrichmentResult(
            ioc=ioc,
            provider=self.name,
            verdict="no_data",
            detection_count=0,
            total_engines=0,
            scan_date=None,
            raw_stats=raw_stats,
        )
