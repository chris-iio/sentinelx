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

from ..models import EnrichmentError, EnrichmentResult, error_result, no_data_result
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
        if value_count == 4:
            return [value[0], value[1], value[2], value[3]]
    name_servers: list[str] = []
    for item in value:
        _append_name_server(name_servers, item)
    return name_servers


def _append_name_server(name_servers: list[str], item: str) -> None:
    name_servers.append(item)


def _empty_whois_raw_stats(lookup_errors: list[str] | None = None) -> dict:
    return {
        "registrar": None,
        "creation_date": None,
        "expiration_date": None,
        "name_servers": [],
        "org": None,
        "lookup_errors": [] if lookup_errors is None else lookup_errors,
    }


def _safe_whois_field(
    whois_response: object,
    field_name: str,
    lookup_errors: list[str],
    *,
    normalizer=None,
    default=None,
):
    """Read one WHOIS field, recording parse errors without failing the lookup."""
    try:
        value = getattr(whois_response, field_name)
        if normalizer is not None:
            return normalizer(value)
        return value
    except Exception:
        _append_lookup_parse_error(lookup_errors, field_name)
        return default


def _append_lookup_parse_error(lookup_errors: list[str], field_name: str) -> None:
    lookup_errors.append(f"{field_name}: parse error")


def _whois_raw_stats(whois_response: object) -> dict:
    """Extract the stable successful WHOIS raw_stats envelope."""
    lookup_errors: list[str] = []
    registrar = _safe_whois_field(whois_response, "registrar", lookup_errors)
    creation_date = _safe_whois_field(
        whois_response,
        "creation_date",
        lookup_errors,
        normalizer=_normalise_datetime,
    )
    expiration_date = _safe_whois_field(
        whois_response,
        "expiration_date",
        lookup_errors,
        normalizer=_normalise_datetime,
    )
    name_servers = _safe_whois_field(
        whois_response,
        "name_servers",
        lookup_errors,
        normalizer=_normalise_name_servers,
        default=[],
    )
    org = _safe_whois_field(whois_response, "org", lookup_errors)

    return {
        "registrar": registrar,
        "creation_date": creation_date,
        "expiration_date": expiration_date,
        "name_servers": name_servers,
        "org": org,
        "lookup_errors": lookup_errors,
    }


class WhoisAdapter:
    """WHOIS domain registration data — port 43, not HTTP.

    See _normalise_datetime for date polymorphism handling.
    """

    name = "WHOIS"
    supported_types: frozenset[IOCType] = frozenset((IOCType.DOMAIN,))
    requires_api_key = False

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

        return _whois_result(
            ioc=ioc,
            provider=self.name,
            raw_stats=_whois_raw_stats(w),
        )


def _whois_result(*, ioc: IOC, provider: str, raw_stats: dict) -> EnrichmentResult:
    return no_data_result(ioc, provider, raw_stats)
