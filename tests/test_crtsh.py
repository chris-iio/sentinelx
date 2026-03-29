"""Tests for CrtShAdapter — certificate transparency history via crt.sh.

Contract tests (protocol, error handling, safety controls) are in test_adapter_contract.py.

All HTTP calls are mocked using unittest.mock.patch -- no real API calls.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests
import requests.exceptions

from app.enrichment.adapters.crtsh import CrtShAdapter
from tests.helpers import (
    make_mock_response,
    mock_adapter_session,
    make_domain_ioc,
)
from app.enrichment.models import EnrichmentError, EnrichmentResult


ALLOWED_HOSTS = ["crt.sh"]

SAMPLE_CERTS = [
    {
        "id": 1,
        "issuer_name": "C=US, O=Let's Encrypt, CN=R3",
        "common_name": "example.com",
        "name_value": "example.com\n*.example.com\nwww.example.com",
        "not_before": "2024-01-01T00:00:00",
        "not_after": "2024-04-01T00:00:00",
        "entry_timestamp": "2024-01-01T01:23:45",
    },
    {
        "id": 2,
        "issuer_name": "C=US, O=Let's Encrypt, CN=R3",
        "common_name": "example.com",
        "name_value": "example.com\nmail.example.com",
        "not_before": "2023-06-01T00:00:00",
        "not_after": "2023-09-01T00:00:00",
        "entry_timestamp": "2023-06-01T01:23:45",
    },
    {
        "id": 3,
        "issuer_name": "C=US, O=DigiCert, CN=R3",
        "common_name": "example.com",
        "name_value": "example.com\napi.example.com",
        "not_before": "2024-02-01T00:00:00",
        "not_after": "2024-05-01T00:00:00",
        "entry_timestamp": "2024-02-01T01:23:45",
    },
]


def _make_adapter(allowed_hosts: list[str] | None = None) -> CrtShAdapter:
    if allowed_hosts is None:
        allowed_hosts = ALLOWED_HOSTS
    return CrtShAdapter(allowed_hosts=allowed_hosts)


class TestCertDataExtraction:

    def test_cert_count_matches_response_length(self) -> None:
        """3 cert records -> cert_count=3 in raw_stats."""
        ioc = make_domain_ioc("example.com")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, SAMPLE_CERTS))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["cert_count"] == 3

    def test_earliest_date_is_min_not_before(self) -> None:
        """earliest date is the minimum not_before (first 10 chars) across all certs."""
        ioc = make_domain_ioc("example.com")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, SAMPLE_CERTS))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["earliest"] == "2023-06-01"

    def test_latest_date_is_max_not_before(self) -> None:
        """latest date is the maximum not_before (first 10 chars) across all certs."""
        ioc = make_domain_ioc("example.com")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, SAMPLE_CERTS))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["latest"] == "2024-02-01"

    def test_subdomains_extracted_from_name_value(self) -> None:
        """Subdomains from all name_value fields are collected."""
        ioc = make_domain_ioc("example.com")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, SAMPLE_CERTS))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        subdomains = result.raw_stats["subdomains"]
        assert "example.com" in subdomains
        assert "www.example.com" in subdomains
        assert "mail.example.com" in subdomains
        assert "api.example.com" in subdomains

    def test_wildcard_prefix_stripped(self) -> None:
        """*.example.com in name_value is stripped to example.com."""
        ioc = make_domain_ioc("example.com")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, SAMPLE_CERTS))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        subdomains = result.raw_stats["subdomains"]
        # *.example.com should become example.com (already present), never "*.example.com"
        assert "*.example.com" not in subdomains

    def test_subdomains_deduplicated(self) -> None:
        """Duplicate subdomains across multiple cert records are deduplicated."""
        ioc = make_domain_ioc("example.com")
        # All 3 certs contain "example.com" — should appear only once
        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, SAMPLE_CERTS))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        subdomains = result.raw_stats["subdomains"]
        assert subdomains.count("example.com") == 1

    def test_subdomains_lowercased(self) -> None:
        """Subdomains are always lowercased."""
        ioc = make_domain_ioc("example.com")
        certs_with_uppercase = [
        {
                "id": 1,
                "common_name": "Example.Com",
                "name_value": "EXAMPLE.COM\nWWW.Example.Com",
                "not_before": "2024-01-01T00:00:00",
            }
        ]

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, certs_with_uppercase))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        subdomains = result.raw_stats["subdomains"]
        assert "example.com" in subdomains
        assert "www.example.com" in subdomains
        assert "EXAMPLE.COM" not in subdomains
        assert "WWW.Example.Com" not in subdomains

    def test_subdomains_sorted_alphabetically(self) -> None:
        """Subdomain list is in alphabetical order."""
        ioc = make_domain_ioc("example.com")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, SAMPLE_CERTS))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        subdomains = result.raw_stats["subdomains"]
        assert subdomains == sorted(subdomains), (
        f"Subdomains not sorted alphabetically: {subdomains}"
        )

    def test_subdomains_capped_at_50(self) -> None:
        """More than 50 unique subdomains -> capped at 50 in raw_stats."""
        ioc = make_domain_ioc("example.com")
        # Create cert with 60 unique subdomains in name_value
        name_values = "\n".join(f"sub{i:03d}.example.com" for i in range(60))
        many_subs_cert = [
        {
                "id": 1,
                "common_name": "example.com",
                "name_value": name_values,
                "not_before": "2024-01-01T00:00:00",
            }
        ]

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, many_subs_cert))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert len(result.raw_stats["subdomains"]) == 50, (
        f"Expected 50 subdomains (cap), got {len(result.raw_stats['subdomains'])}"
        )

    def test_null_not_before_skipped_in_date_range(self) -> None:
        """Cert entries with null/missing not_before are skipped when computing date range."""
        ioc = make_domain_ioc("example.com")
        certs_with_null = [
        {
                "id": 1,
                "common_name": "example.com",
                "name_value": "example.com",
                "not_before": None,
            },
            {
                "id": 2,
                "common_name": "example.com",
                "name_value": "example.com",
                "not_before": "2024-01-01T00:00:00",
            },
        ]

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, certs_with_null))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        # Only the cert with valid date should contribute
        assert result.raw_stats["earliest"] == "2024-01-01"
        assert result.raw_stats["latest"] == "2024-01-01"

    def test_null_name_value_cert_skipped(self) -> None:
        """Cert entries with null/missing name_value are skipped without error."""
        ioc = make_domain_ioc("example.com")
        certs_with_null_name = [
        {
                "id": 1,
                "common_name": "example.com",
                "name_value": None,
                "not_before": "2024-01-01T00:00:00",
            },
            {
                "id": 2,
                "common_name": "example.com",
                "name_value": "sub.example.com",
                "not_before": "2024-02-01T00:00:00",
            },
        ]

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, certs_with_null_name))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "sub.example.com" in result.raw_stats["subdomains"]

    def test_dates_formatted_yyyy_mm_dd(self) -> None:
        """Dates in raw_stats use YYYY-MM-DD format (first 10 chars of ISO 8601)."""
        ioc = make_domain_ioc("example.com")
        certs = [
        {
                "id": 1,
                "common_name": "example.com",
                "name_value": "example.com",
                "not_before": "2024-03-15T10:30:00",
            }
        ]

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, certs))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["earliest"] == "2024-03-15"
        assert result.raw_stats["latest"] == "2024-03-15"

    def test_verdict_is_no_data(self) -> None:
        """verdict is always 'no_data' for crt.sh (CT history, not a threat verdict)."""
        ioc = make_domain_ioc("example.com")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, SAMPLE_CERTS))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"

    def test_detection_count_always_zero(self) -> None:
        """detection_count is always 0 (crt.sh doesn't provide threat detection)."""
        ioc = make_domain_ioc("example.com")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, SAMPLE_CERTS))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.detection_count == 0

    def test_total_engines_always_zero(self) -> None:
        """total_engines is always 0 (crt.sh is a certificate registry, not a scanner)."""
        ioc = make_domain_ioc("example.com")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, SAMPLE_CERTS))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.total_engines == 0

    def test_scan_date_always_none(self) -> None:
        """scan_date is always None (crt.sh doesn't have a scan date concept)."""
        ioc = make_domain_ioc("example.com")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, SAMPLE_CERTS))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.scan_date is None


class TestEmptyResponse:

    def test_empty_array_returns_no_data(self) -> None:
        """Empty [] response -> EnrichmentResult(verdict='no_data')."""
        ioc = make_domain_ioc("example.com")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, []))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
        f"Empty response must return EnrichmentResult, got {type(result).__name__}: {result!r}"
        )
        assert result.verdict == "no_data"

    def test_empty_array_returns_empty_raw_stats(self) -> None:
        """Empty [] response -> raw_stats is {} (empty dict)."""
        ioc = make_domain_ioc("example.com")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, []))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats == {}

    def test_empty_array_detection_count_zero(self) -> None:
        """Empty [] response -> detection_count=0."""
        ioc = make_domain_ioc("example.com")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, []))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.detection_count == 0


class TestHTTPErrors:

    def test_http_502_returns_enrichment_error(self) -> None:
        """HTTP 502 (common crt.sh transient error) -> EnrichmentError('HTTP 502')."""
        ioc = make_domain_ioc("example.com")
        mock_resp = MagicMock()
        mock_resp.status_code = 502
        http_err = requests.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status = MagicMock(side_effect=http_err)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError), (
        f"HTTP 502 must return EnrichmentError, got {type(result).__name__}: {result!r}"
        )
        assert result.provider == "Cert History"
        assert "HTTP 502" in result.error

    def test_http_500_returns_enrichment_error(self) -> None:
        """HTTP 500 -> EnrichmentError with 'HTTP 500' in error."""
        ioc = make_domain_ioc("example.com")
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        http_err = requests.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status = MagicMock(side_effect=http_err)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert "HTTP 500" in result.error


class TestHTTPSafetyControls:

    def test_uses_timeout(self) -> None:
        """requests.get must be called with timeout=TIMEOUT (SEC-04)."""
        from app.enrichment.http_safety import TIMEOUT
        ioc = make_domain_ioc("example.com")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, SAMPLE_CERTS))
        adapter.lookup(ioc)

        call_kwargs = adapter._session.get.call_args.kwargs
        assert call_kwargs.get("timeout") == TIMEOUT, (
        f"Expected timeout={TIMEOUT!r} (SEC-04), got {call_kwargs.get('timeout')!r}"
        )

    def test_uses_allow_redirects_false(self) -> None:
        """requests.get must be called with allow_redirects=False (SEC-06)."""
        ioc = make_domain_ioc("example.com")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, SAMPLE_CERTS))
        adapter.lookup(ioc)

        call_kwargs = adapter._session.get.call_args.kwargs
        assert call_kwargs.get("allow_redirects") is False, (
        "allow_redirects must be False (SEC-06)"
        )

    def test_uses_stream_true(self) -> None:
        """requests.get must be called with stream=True (SEC-05)."""
        ioc = make_domain_ioc("example.com")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, SAMPLE_CERTS))
        adapter.lookup(ioc)

        call_kwargs = adapter._session.get.call_args.kwargs
        assert call_kwargs.get("stream") is True, "stream must be True (SEC-05)"

    def test_validate_endpoint_called(self) -> None:
        """validate_endpoint must be called before making the HTTP request (SEC-16)."""
        ioc = make_domain_ioc("example.com")

        with patch("app.enrichment.http_safety.validate_endpoint") as mock_validate:
            adapter = _make_adapter()
            mock_adapter_session(adapter, response=make_mock_response(200, SAMPLE_CERTS))
            adapter.lookup(ioc)

        mock_validate.assert_called_once()
        called_url = mock_validate.call_args.args[0]
        assert "crt.sh" in called_url

    def test_url_contains_domain_and_output_json(self) -> None:
        """URL must contain the domain value and &output=json query params."""
        ioc = make_domain_ioc("evil.com")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, []))
        adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert "evil.com" in called_url
        assert "output=json" in called_url
        assert "crt.sh" in called_url

