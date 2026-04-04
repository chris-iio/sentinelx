"""Tests for WHOIS registration data lookup adapter.

Tests registrar/creation_date/expiration_date/name_servers/org extraction,
datetime polymorphism handling, error mapping, protocol conformance, and the
critical design invariants:
  - WHOIS uses port 43, NOT HTTP -- no http_safety imports
  - Domain not found is no_data, NOT EnrichmentError
  - Quota/command failures are EnrichmentError
  - Parse/TLD failures are graceful degrades (EnrichmentResult + lookup_errors)
  - verdict is always "no_data" -- WHOIS records are informational, not threat signals

All WHOIS calls are mocked using unittest.mock.patch -- no real WHOIS queries.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from whois.exceptions import (
    FailedParsingWhoisOutputError,
    UnknownTldError,
    WhoisCommandFailedError,
    WhoisDomainNotFoundError,
    WhoisQuotaExceededError,
)

from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DOMAIN_IOC = IOC(type=IOCType.DOMAIN, value="example.com", raw_match="example.com")
IPV4_IOC = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")


def _make_adapter(allowed_hosts: list[str] | None = None):
    """Construct a WhoisAdapter. allowed_hosts is accepted but unused (WHOIS is port 43)."""
    from app.enrichment.adapters.whois_lookup import WhoisAdapter

    return WhoisAdapter(allowed_hosts=allowed_hosts or [])


def _make_whois_response(
    *,
    registrar: str | None = "Example Registrar Inc.",
    creation_date: datetime | list[datetime] | str | None = None,
    expiration_date: datetime | list[datetime] | str | None = None,
    name_servers: list[str] | None = None,
    org: str | None = "Example Org",
) -> MagicMock:
    """Build a mock whois response object with the given attributes."""
    mock = MagicMock()
    mock.registrar = registrar
    mock.creation_date = creation_date
    mock.expiration_date = expiration_date
    mock.name_servers = name_servers if name_servers is not None else ["NS1.EXAMPLE.COM", "NS2.EXAMPLE.COM"]
    mock.org = org
    return mock


# ---------------------------------------------------------------------------
# Unsupported IOC type — WHOIS-specific behavior
# ---------------------------------------------------------------------------


class TestUnsupportedType:

    def test_ipv4_does_not_call_whois(self) -> None:
        """IPV4 IOC -> no WHOIS query attempted."""
        with patch("app.enrichment.adapters.whois_lookup.whois.whois") as mock_whois:
            _make_adapter().lookup(IPV4_IOC)
        mock_whois.assert_not_called()


# ---------------------------------------------------------------------------
# Successful lookups
# ---------------------------------------------------------------------------


class TestSuccessfulLookup:

    def test_successful_lookup_returns_enrichment_result(self) -> None:
        """Successful WHOIS lookup returns EnrichmentResult with correct response shape."""
        mock_resp = _make_whois_response(
            creation_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
            expiration_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", return_value=mock_resp):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult, got {type(result).__name__}: {result!r}"
        )
        assert result.provider == "WHOIS", "WHOIS adapter — provider must be 'WHOIS'"
        assert result.detection_count == 0, "informational adapter — detection_count must be 0"
        assert result.total_engines == 0, "informational adapter — total_engines must be 0"
        assert result.scan_date is None, "informational adapter — scan_date must be None"

    def test_successful_lookup_verdict_is_no_data(self) -> None:
        """WHOIS adapter always returns verdict='no_data' — records are informational."""
        mock_resp = _make_whois_response()
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", return_value=mock_resp):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"


# ---------------------------------------------------------------------------
# raw_stats field extraction
# ---------------------------------------------------------------------------


class TestRawStatsExtraction:

    def test_registrar_extracted(self) -> None:
        """raw_stats['registrar'] must contain the registrar name."""
        mock_resp = _make_whois_response(registrar="GoDaddy.com LLC")
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", return_value=mock_resp):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["registrar"] == "GoDaddy.com LLC"

    def test_registrar_none_when_missing(self) -> None:
        """raw_stats['registrar'] is None when WHOIS returns None."""
        mock_resp = _make_whois_response(registrar=None)
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", return_value=mock_resp):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["registrar"] is None

    def test_org_extracted(self) -> None:
        """raw_stats['org'] must contain the organisation name."""
        mock_resp = _make_whois_response(org="Example Corp")
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", return_value=mock_resp):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["org"] == "Example Corp"

    def test_org_none_when_missing(self) -> None:
        """raw_stats['org'] is None when WHOIS returns None."""
        mock_resp = _make_whois_response(org=None)
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", return_value=mock_resp):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["org"] is None

    def test_name_servers_extracted_as_list(self) -> None:
        """raw_stats['name_servers'] must be a list of nameserver strings."""
        mock_resp = _make_whois_response(name_servers=["NS1.EXAMPLE.COM", "NS2.EXAMPLE.COM"])
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", return_value=mock_resp):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["name_servers"] == ["NS1.EXAMPLE.COM", "NS2.EXAMPLE.COM"]

    def test_name_servers_empty_when_none(self) -> None:
        """raw_stats['name_servers'] defaults to [] when WHOIS returns None."""
        mock_resp = _make_whois_response()
        mock_resp.name_servers = None
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", return_value=mock_resp):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["name_servers"] == []

    def test_raw_stats_has_all_keys(self) -> None:
        """raw_stats must contain registrar, creation_date, expiration_date, name_servers, org, lookup_errors."""
        mock_resp = _make_whois_response()
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", return_value=mock_resp):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        for key in ("registrar", "creation_date", "expiration_date", "name_servers", "org", "lookup_errors"):
            assert key in result.raw_stats, f"raw_stats missing key: {key!r}"

    def test_lookup_errors_empty_on_success(self) -> None:
        """lookup_errors must be empty list on successful extraction."""
        mock_resp = _make_whois_response()
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", return_value=mock_resp):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["lookup_errors"] == []


# ---------------------------------------------------------------------------
# Datetime polymorphism
# ---------------------------------------------------------------------------


class TestDatetimePolymorphism:

    def test_single_datetime_normalised_to_iso(self) -> None:
        """Single datetime -> ISO-8601 string."""
        dt = datetime(2020, 6, 15, 12, 30, 0, tzinfo=timezone.utc)
        mock_resp = _make_whois_response(creation_date=dt)
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", return_value=mock_resp):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["creation_date"] == dt.isoformat()

    def test_list_of_datetimes_takes_first(self) -> None:
        """List of datetimes -> first element normalised to ISO-8601."""
        dt1 = datetime(2020, 1, 1, tzinfo=timezone.utc)
        dt2 = datetime(2019, 6, 1, tzinfo=timezone.utc)
        mock_resp = _make_whois_response(creation_date=[dt1, dt2])
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", return_value=mock_resp):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["creation_date"] == dt1.isoformat()

    def test_empty_list_returns_none(self) -> None:
        """Empty list -> None."""
        mock_resp = _make_whois_response(creation_date=[])
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", return_value=mock_resp):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["creation_date"] is None

    def test_none_remains_none(self) -> None:
        """None -> None."""
        mock_resp = _make_whois_response(creation_date=None)
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", return_value=mock_resp):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["creation_date"] is None

    def test_string_returned_as_is(self) -> None:
        """String date -> returned as-is (str fallback)."""
        mock_resp = _make_whois_response(creation_date="2020-01-01")
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", return_value=mock_resp):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["creation_date"] == "2020-01-01"

    def test_expiration_date_single_datetime(self) -> None:
        """expiration_date with single datetime -> ISO-8601."""
        dt = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        mock_resp = _make_whois_response(expiration_date=dt)
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", return_value=mock_resp):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["expiration_date"] == dt.isoformat()

    def test_expiration_date_list_takes_first(self) -> None:
        """expiration_date with list -> first element."""
        dt1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        dt2 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        mock_resp = _make_whois_response(expiration_date=[dt1, dt2])
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", return_value=mock_resp):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["expiration_date"] == dt1.isoformat()


# ---------------------------------------------------------------------------
# Domain not found handling
# ---------------------------------------------------------------------------


class TestDomainNotFound:

    def test_not_found_returns_enrichment_result(self) -> None:
        """WhoisDomainNotFoundError must return EnrichmentResult, NOT EnrichmentError."""
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", side_effect=WhoisDomainNotFoundError("example.com")):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult), (
            f"Domain not found must return EnrichmentResult, got {type(result).__name__}"
        )

    def test_not_found_verdict_is_no_data(self) -> None:
        """WhoisDomainNotFoundError -> verdict='no_data'."""
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", side_effect=WhoisDomainNotFoundError("example.com")):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"

    def test_not_found_raw_stats_has_empty_defaults(self) -> None:
        """Domain not found -> raw_stats has None/empty defaults."""
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", side_effect=WhoisDomainNotFoundError("example.com")):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["registrar"] is None
        assert result.raw_stats["creation_date"] is None
        assert result.raw_stats["expiration_date"] is None
        assert result.raw_stats["name_servers"] == []
        assert result.raw_stats["org"] is None
        assert result.raw_stats["lookup_errors"] == []


# ---------------------------------------------------------------------------
# Quota exceeded handling
# ---------------------------------------------------------------------------


class TestQuotaExceeded:

    def test_quota_exceeded_returns_enrichment_error(self) -> None:
        """WhoisQuotaExceededError -> EnrichmentError mentioning 'quota' from WHOIS provider."""
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", side_effect=WhoisQuotaExceededError("rate limited")):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "WHOIS"
        assert "quota" in result.error.lower()


# ---------------------------------------------------------------------------
# Command failed handling
# ---------------------------------------------------------------------------


class TestCommandFailed:

    def test_command_failed_returns_enrichment_error(self) -> None:
        """WhoisCommandFailedError -> EnrichmentError mentioning 'command' or 'failed'."""
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", side_effect=WhoisCommandFailedError("whois: not found")):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentError)
        assert "command" in result.error.lower() or "failed" in result.error.lower()


# ---------------------------------------------------------------------------
# Parse failure and unknown TLD handling (graceful degrade)
# ---------------------------------------------------------------------------


class TestGracefulDegrade:

    @pytest.mark.parametrize("exception", [
        FailedParsingWhoisOutputError("bad output"),
        UnknownTldError(".xyz"),
    ], ids=["parse-failure", "unknown-tld"])
    def test_graceful_degrade_returns_result_with_lookup_errors(self, exception) -> None:
        """Parse failures and unknown TLDs -> EnrichmentResult(verdict='no_data') with lookup_errors."""
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", side_effect=exception):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult), (
            f"{type(exception).__name__} should degrade gracefully, got {type(result).__name__}"
        )
        assert result.verdict == "no_data"
        assert len(result.raw_stats["lookup_errors"]) > 0


# ---------------------------------------------------------------------------
# Unexpected exception handling
# ---------------------------------------------------------------------------


class TestUnexpectedException:

    def test_unexpected_exception_returns_enrichment_error(self) -> None:
        """Unexpected exceptions -> EnrichmentError mentioning 'unexpected'."""
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", side_effect=RuntimeError("socket exploded")):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentError)
        assert "unexpected" in result.error.lower() or "Unexpected" in result.error

    def test_unexpected_exception_logs_via_logger(self) -> None:
        """Unexpected exceptions are logged via logger.exception()."""
        with patch("app.enrichment.adapters.whois_lookup.whois.whois", side_effect=RuntimeError("boom")):
            with patch("app.enrichment.adapters.whois_lookup.logger") as mock_logger:
                _make_adapter().lookup(DOMAIN_IOC)

        mock_logger.exception.assert_called_once()


# ---------------------------------------------------------------------------
# No HTTP safety imports
# ---------------------------------------------------------------------------


class TestNoHTTPSafety:

    def test_whois_adapter_does_not_import_http_safety(self) -> None:
        """WhoisAdapter must NOT import http_safety.py (WHOIS is port 43, not HTTP).

        This test inspects the adapter module's globals to confirm no http_safety
        symbols are present (validate_endpoint, TIMEOUT, read_limited).
        """
        import app.enrichment.adapters.whois_lookup as whois_module

        http_safety_symbols = {"validate_endpoint", "read_limited", "TIMEOUT", "http_safety"}
        module_attrs = set(dir(whois_module))
        imported_safety = http_safety_symbols.intersection(module_attrs)
        assert not imported_safety, (
            f"WhoisAdapter must NOT import http_safety symbols (WHOIS is port 43): {imported_safety}"
        )

    def test_whois_adapter_does_not_use_requests(self) -> None:
        """WhoisAdapter must NOT import requests (WHOIS is not HTTP).

        WHOIS uses python-whois directly — no HTTP calls.
        """
        import app.enrichment.adapters.whois_lookup as whois_module

        assert "requests" not in dir(whois_module), (
            "WhoisAdapter must not import 'requests' — WHOIS uses port 43 directly"
        )


# ---------------------------------------------------------------------------
# _normalise_datetime unit tests
# ---------------------------------------------------------------------------


class TestNormaliseDatetime:

    def test_normalise_datetime_none(self) -> None:
        """None -> None."""
        from app.enrichment.adapters.whois_lookup import _normalise_datetime
        assert _normalise_datetime(None) is None

    def test_normalise_datetime_single(self) -> None:
        """Single datetime -> isoformat string."""
        from app.enrichment.adapters.whois_lookup import _normalise_datetime
        dt = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert _normalise_datetime(dt) == dt.isoformat()

    def test_normalise_datetime_list(self) -> None:
        """List of datetimes -> first element isoformat."""
        from app.enrichment.adapters.whois_lookup import _normalise_datetime
        dt1 = datetime(2020, 1, 1, tzinfo=timezone.utc)
        dt2 = datetime(2019, 1, 1, tzinfo=timezone.utc)
        assert _normalise_datetime([dt1, dt2]) == dt1.isoformat()

    def test_normalise_datetime_empty_list(self) -> None:
        """Empty list -> None."""
        from app.enrichment.adapters.whois_lookup import _normalise_datetime
        assert _normalise_datetime([]) is None

    def test_normalise_datetime_string(self) -> None:
        """String -> returned as-is."""
        from app.enrichment.adapters.whois_lookup import _normalise_datetime
        assert _normalise_datetime("2020-01-01") == "2020-01-01"
