"""WHOIS registration data lookup adapter (port 43, not HTTP — no SSRF surface)."""
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

from app.enrichment.models import EnrichmentError, EnrichmentResult, error_result, no_data_result
from app.pipeline.models import IOC, IOCType

logger = logging.getLogger(__name__)


def _normalise_datetime(value: datetime | list[datetime] | str | None) -> str | None:
    """Normalise a WHOIS date field (datetime | list | str | None) to ISO-8601 string or None."""
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


def _normalise_name_servers(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        value_count = len(value)
        if value_count == 0:
            return []
        if value_count == 1:
            return [value[0]]
        if value_count == 2:
            return [value[0], value[1]]
        if value_count == 3:
            return [value[0], value[1], value[2]]
    name_servers: list[str] = []
    for item in value:
        name_servers.append(item)
    return name_servers


def _empty_whois_raw_stats(lookup_errors: list[str] | None = None) -> dict:
    return {
        "registrar": None,
        "creation_date": None,
        "expiration_date": None,
        "name_servers": [],
        "org": None,
        "lookup_errors": [] if lookup_errors is None else lookup_errors,
    }


class WhoisAdapter:
    """WHOIS domain registration data — port 43, not HTTP.

    See _normalise_datetime for date polymorphism handling.
    """

    name = "WHOIS"
    supported_types: frozenset[IOCType] = frozenset((IOCType.DOMAIN,))
    requires_api_key = False

    def __init__(self, allowed_hosts: list[str]) -> None:
        # Accepted for API compatibility with Provider protocol; intentionally unused.
        # WHOIS uses port 43 directly — no HTTP, no SSRF surface.
        pass

    def is_configured(self) -> bool:
        return True

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        if ioc.type not in self.supported_types:
            return error_result(ioc, self.name, "Unsupported type")

        try:
            w = whois.whois(ioc.value)
        except WhoisDomainNotFoundError:
            # Domain not found in WHOIS — expected outcome, not an error.
            return _whois_result(
                ioc=ioc,
                provider=self.name,
                raw_stats=_empty_whois_raw_stats(),
            )
        except (FailedParsingWhoisOutputError, UnknownTldError) as exc:
            # Parse/TLD issues — return result with error noted, not a hard failure.
            return _whois_result(
                ioc=ioc,
                provider=self.name,
                raw_stats=_empty_whois_raw_stats([str(exc)]),
            )
        except WhoisQuotaExceededError:
            return error_result(ioc, self.name, "WHOIS quota exceeded")
        except WhoisCommandFailedError:
            return error_result(ioc, self.name, "WHOIS command failed")
        except Exception:
            logger.exception(
                "Unexpected error during WHOIS lookup for %s",
                ioc.value,
            )
            return error_result(ioc, self.name, "Unexpected WHOIS lookup error")

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
            name_servers = _normalise_name_servers(raw_ns)
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

        return _whois_result(
            ioc=ioc,
            provider=self.name,
            raw_stats=raw_stats,
        )


def _whois_result(*, ioc: IOC, provider: str, raw_stats: dict) -> EnrichmentResult:
    return no_data_result(ioc, provider, raw_stats)
