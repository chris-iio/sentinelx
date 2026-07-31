"""Tests for CrtShAdapter — certificate transparency history via crt.sh.

Contract tests (protocol, error handling, safety controls) are in test_adapter_contract.py.

All HTTP calls are mocked using unittest.mock.patch -- no real API calls.
"""
from __future__ import annotations

import builtins
import inspect
from unittest.mock import MagicMock, patch

import requests
import requests.exceptions

from app.enrichment.adapters.crtsh import (
    CrtShAdapter,
    _capped_sorted_subdomains,
    _clean_name_value,
    _crtsh_raw_stats,
    _crtsh_result,
    _iter_name_values,
    _parse_response,
    _trim_wildcard_prefix,
    add_name_value_subdomains,
    append_ordered_subdomain,
)
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


class _SinglePassCertBody:
    def __init__(self, rows):
        self._rows = rows
        self.iterations = 0

    def __bool__(self) -> bool:
        return bool(self._rows)

    def __len__(self) -> int:
        return len(self._rows)

    def __iter__(self):
        self.iterations += 1
        if self.iterations > 1:
            raise AssertionError("crt.sh parsing should scan certificate rows once")
        return iter(self._rows)


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

    def test_subdomain_cap_avoids_full_sorted_list(self, monkeypatch) -> None:
        """Oversized subdomain sets should select the first 50 without full sorting."""
        values = {f"sub{i:03d}.example.com" for i in range(60)}

        def fail_sorted(*_args, **_kwargs):
            raise AssertionError("oversized crt.sh subdomain caps should not sort the full set")

        monkeypatch.setattr(builtins, "sorted", fail_sorted)

        subdomains = _capped_sorted_subdomains(values)

        assert len(subdomains) == 50
        assert subdomains[0] == "sub000.example.com"
        assert subdomains[-1] == "sub049.example.com"

    def test_empty_or_single_subdomain_sets_skip_sorting(self, monkeypatch) -> None:
        """Empty and single-value subdomain sets do not need deterministic sorting."""
        def fail_sorted(*_args, **_kwargs):
            raise AssertionError("empty/single crt.sh subdomain sets should not sort")

        monkeypatch.setattr(builtins, "sorted", fail_sorted)

        assert _capped_sorted_subdomains(set()) == []
        assert _capped_sorted_subdomains({"only.example.com"}) == ["only.example.com"]

    def test_two_subdomain_sets_skip_sorting(self, monkeypatch) -> None:
        """Two-value subdomain sets can be ordered by direct comparison."""
        def fail_sorted(*_args, **_kwargs):
            raise AssertionError("two-value crt.sh subdomain sets should not sort")

        monkeypatch.setattr(builtins, "sorted", fail_sorted)

        assert _capped_sorted_subdomains({"z.example.com", "a.example.com"}) == [
            "a.example.com",
            "z.example.com",
        ]

    def test_three_subdomain_sets_skip_sorting(self, monkeypatch) -> None:
        """Three-value subdomain sets can be ordered by direct comparisons."""
        def fail_sorted(*_args, **_kwargs):
            raise AssertionError("three-value crt.sh subdomain sets should not sort")

        monkeypatch.setattr(builtins, "sorted", fail_sorted)

        assert _capped_sorted_subdomains({
            "z.example.com",
            "a.example.com",
            "m.example.com",
        }) == [
            "a.example.com",
            "m.example.com",
            "z.example.com",
        ]

    def test_four_subdomain_sets_skip_sorting(self, monkeypatch) -> None:
        """Four-value subdomain sets can be ordered by direct comparisons."""
        def fail_sorted(*_args, **_kwargs):
            raise AssertionError("four-value crt.sh subdomain sets should not sort")

        monkeypatch.setattr(builtins, "sorted", fail_sorted)

        assert _capped_sorted_subdomains({
            "z.example.com",
            "a.example.com",
            "m.example.com",
            "b.example.com",
        }) == [
            "a.example.com",
            "b.example.com",
            "m.example.com",
            "z.example.com",
        ]
        assert "subdomain_count == 4" in inspect.getsource(_capped_sorted_subdomains)

    def test_capped_subdomain_sets_use_direct_ordered_insertion(self, monkeypatch) -> None:
        """Capped crt.sh subdomain sets should not allocate a full sorted list."""
        def fail_sorted(*_args, **_kwargs):
            raise AssertionError("capped crt.sh subdomain sets should not call sorted")

        monkeypatch.setattr(builtins, "sorted", fail_sorted)

        assert _capped_sorted_subdomains({
            "z.example.com",
            "a.example.com",
            "m.example.com",
            "b.example.com",
        }) == [
            "a.example.com",
            "b.example.com",
            "m.example.com",
            "z.example.com",
        ]

        ordered: list[str] = []
        append_ordered_subdomain(ordered, "z.example.com")
        append_ordered_subdomain(ordered, "a.example.com")
        append_ordered_subdomain(ordered, "m.example.com")
        append_ordered_subdomain(ordered, "b.example.com")
        assert ordered == [
            "a.example.com",
            "b.example.com",
            "m.example.com",
            "z.example.com",
        ]

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

    def test_date_range_and_subdomains_computed_in_one_body_scan(self) -> None:
        """Date range and SAN extraction should share one certificate scan."""
        ioc = make_domain_ioc("example.com")
        body = _SinglePassCertBody(SAMPLE_CERTS)

        result = _parse_response(ioc, body, "Cert History")  # type: ignore[arg-type]

        assert isinstance(result, EnrichmentResult)
        assert body.iterations == 1
        assert result.raw_stats["earliest"] == "2023-06-01"
        assert result.raw_stats["latest"] == "2024-02-01"
        assert "www.example.com" in result.raw_stats["subdomains"]

    def test_parse_response_delegates_raw_stats_helper(self) -> None:
        """crt.sh parser should not own certificate raw_stats mechanics."""
        source = inspect.getsource(_parse_response)

        assert "_crtsh_raw_stats(body=body, cert_count=cert_count)" in source
        assert "subdomain_set" not in source
        assert '"cert_count"' not in source
        assert '"subdomains"' not in source

    def test_raw_stats_helper_preserves_key_order_and_values(self) -> None:
        """crt.sh raw_stats helper should preserve public metadata shape."""
        raw_stats = _crtsh_raw_stats(body=SAMPLE_CERTS, cert_count=len(SAMPLE_CERTS))

        assert list(raw_stats) == ["cert_count", "earliest", "latest", "subdomains"]
        assert raw_stats["cert_count"] == 3
        assert raw_stats["earliest"] == "2023-06-01"
        assert raw_stats["latest"] == "2024-02-01"
        assert raw_stats["subdomains"] == [
            "api.example.com",
            "example.com",
            "mail.example.com",
            "www.example.com",
        ]

    def test_raw_stats_delegates_san_collection(self) -> None:
        """crt.sh raw_stats should delegate SAN parsing and subdomain deduplication."""
        subdomains: set[str] = set()

        add_name_value_subdomains(subdomains, "WWW.Example.com\n*.Example.com\n\n")

        raw_stats_source = inspect.getsource(_crtsh_raw_stats)
        helper_source = inspect.getsource(add_name_value_subdomains)
        assert subdomains == {"www.example.com", "example.com"}
        assert "add_name_value_subdomains(subdomain_set, name_value)" in raw_stats_source
        assert "_iter_name_values(name_value)" not in raw_stats_source
        assert "_clean_name_value(raw_name)" not in raw_stats_source
        assert "_iter_name_values(name_value)" in helper_source
        assert "_clean_name_value(raw_name)" in helper_source

    def test_name_value_parsing_does_not_allocate_split_list(self) -> None:
        """SAN name parsing should stream newline-delimited values."""
        class NoSplitName(str):
            def split(self, *_args, **_kwargs):
                raise AssertionError("crt.sh SAN parsing should not allocate split lists")

        assert list(_iter_name_values(NoSplitName("a.example\n\n*.b.example"))) == [
            "a.example",
            "",
            "*.b.example",
        ]

    def test_name_value_cleanup_uses_index_trim_without_strip(self) -> None:
        """SAN value cleanup should avoid direct strip allocation."""
        class NoStripName(str):
            def strip(self, *_args, **_kwargs):
                raise AssertionError("crt.sh SAN cleanup should avoid direct strip allocation")

        class NoLStripName(str):
            def lstrip(self, *_args, **_kwargs):
                raise AssertionError("crt.sh wildcard cleanup should scan directly")

        assert _clean_name_value(NoStripName("  *.Example.COM  ")) == "example.com"
        assert _clean_name_value(NoStripName(" \n\t ")) is None
        assert _trim_wildcard_prefix(NoLStripName("...*.example.com")) == "example.com"
        assert "lstrip" not in _clean_name_value.__code__.co_names
        assert "lstrip" not in _trim_wildcard_prefix.__code__.co_names

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
        """verdict is always 'no_data' for crt.sh; detection/scan fields are informational defaults."""
        ioc = make_domain_ioc("example.com")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, SAMPLE_CERTS))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"
        assert result.detection_count == 0, "informational adapter — detection_count must be 0"
        assert result.total_engines == 0, "informational adapter — total_engines must be 0"
        assert result.scan_date is None, "informational adapter — scan_date must be None"

    def test_result_helper_preserves_provider_envelope(self) -> None:
        """crt.sh result construction should keep the informational envelope centralized."""
        ioc = make_domain_ioc("example.com")
        raw_stats = {
            "cert_count": 3,
            "earliest": "2023-06-01",
            "latest": "2024-02-01",
            "subdomains": ["example.com"],
        }

        result = _crtsh_result(
            ioc=ioc,
            provider="Cert History",
            raw_stats=raw_stats,
        )

        assert result.ioc is ioc
        assert result.provider == "Cert History"
        assert result.verdict == "no_data"
        assert result.detection_count == 0
        assert result.total_engines == 0
        assert result.scan_date is None
        assert result.raw_stats is raw_stats
        assert "no_data_result(ioc, provider, raw_stats)" in inspect.getsource(_crtsh_result)

    def test_adapter_uses_base_lookup_for_json_list_response(self) -> None:
        """crt.sh should share the BaseHTTPAdapter lookup pipeline."""
        from app.enrichment.adapters.base import BaseHTTPAdapter

        assert CrtShAdapter.lookup is BaseHTTPAdapter.lookup


class TestEmptyResponse:

    def test_empty_array_returns_no_data_with_empty_raw_stats(self) -> None:
        """Empty [] response -> EnrichmentResult(verdict='no_data', raw_stats={})."""
        ioc = make_domain_ioc("example.com")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, []))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
        f"Empty response must return EnrichmentResult, got {type(result).__name__}: {result!r}"
        )
        assert result.verdict == "no_data"
        assert result.detection_count == 0, "empty response — detection_count must be 0"
        assert result.raw_stats == {}


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
