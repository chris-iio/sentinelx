"""Tests for CIRCL Hashlookup NSRL adapter.

Tests hash lookups (MD5/SHA1/SHA256), verdict logic (known_good/no_data), error
handling, and all HTTP safety controls (timeout, size cap, no redirects, SSRF allowlist).

CIRCL Hashlookup behavior:
  - 200: Hash found in NSRL -> verdict=known_good
  - 404: Hash not found in NSRL -> verdict=no_data (NOT an error)
  - 400: Malformed hash -> EnrichmentError
  - 500: Server error -> EnrichmentError with "HTTP 500"

All HTTP calls are mocked using unittest.mock.patch -- no real API calls.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import requests
import requests.exceptions

from app.pipeline.models import IOCType
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.adapters.hashlookup import HashlookupAdapter
from app.enrichment.http_safety import MAX_RESPONSE_BYTES
from app.enrichment.provider import Provider
from tests.helpers import (
    make_mock_response,
    make_domain_ioc,
    make_ipv4_ioc,
    make_md5_ioc,
    make_sha1_ioc,
    make_sha256_ioc,
    mock_adapter_session,
)


ALLOWED_HOSTS = ["hashlookup.circl.lu"]

HASHLOOKUP_FOUND_MD5_RESPONSE = {
    "FileName": "calc.exe",
    "MD5": "a" * 32,
    "SHA-1": "b" * 40,
    "SHA-256": "c" * 64,
    "source": "NSRL",
    "db": "RDS_2022.09.1_Modern",
}

HASHLOOKUP_FOUND_SHA1_RESPONSE = {
    "FileName": "notepad.exe",
    "SHA-1": "b" * 40,
    "SHA-256": "c" * 64,
    "source": "NSRL",
    "db": "RDS_2022.09.1_Modern",
}

HASHLOOKUP_FOUND_SHA256_RESPONSE = {
    "FileName": "explorer.exe",
    "SHA-256": "c" * 64,
    "source": "NSRL",
    "db": "RDS_2022.09.1_Modern",
}




def _make_adapter(allowed_hosts: list[str] | None = None) -> HashlookupAdapter:
    if allowed_hosts is None:
        allowed_hosts = ALLOWED_HOSTS
    return HashlookupAdapter(allowed_hosts=allowed_hosts)


class TestLookupFound:

    def test_md5_found_returns_known_good(self) -> None:
        """MD5 hash found (200) -> verdict=known_good, detection_count=1, total_engines=1."""
        ioc = make_md5_ioc("a" * 32)
        mock_resp = make_mock_response(200, HASHLOOKUP_FOUND_MD5_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult, got {type(result).__name__}: {result!r}"
        )
        assert result.provider == "CIRCL Hashlookup"
        assert result.verdict == "known_good"
        assert result.detection_count == 1
        assert result.total_engines == 1

    def test_sha1_found_returns_known_good(self) -> None:
        """SHA1 hash found (200) -> verdict=known_good."""
        ioc = make_sha1_ioc("b" * 40)
        mock_resp = make_mock_response(200, HASHLOOKUP_FOUND_SHA1_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.provider == "CIRCL Hashlookup"
        assert result.verdict == "known_good"

    def test_sha256_found_returns_known_good(self) -> None:
        """SHA256 hash found (200) -> verdict=known_good."""
        ioc = make_sha256_ioc("c" * 64)
        mock_resp = make_mock_response(200, HASHLOOKUP_FOUND_SHA256_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "known_good"

    def test_raw_stats_contains_file_name_and_source(self) -> None:
        """200 response -> raw_stats contains file_name and source keys."""
        ioc = make_md5_ioc("a" * 32)
        mock_resp = make_mock_response(200, HASHLOOKUP_FOUND_MD5_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "file_name" in result.raw_stats, "raw_stats missing 'file_name'"
        assert "source" in result.raw_stats, "raw_stats missing 'source'"

    def test_raw_stats_file_name_from_response(self) -> None:
        """raw_stats['file_name'] is populated from API FileName field."""
        ioc = make_md5_ioc("a" * 32)
        mock_resp = make_mock_response(200, HASHLOOKUP_FOUND_MD5_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["file_name"] == "calc.exe"

    def test_raw_stats_source_from_response(self) -> None:
        """raw_stats['source'] is populated from API source field."""
        ioc = make_md5_ioc("a" * 32)
        mock_resp = make_mock_response(200, HASHLOOKUP_FOUND_MD5_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["source"] == "NSRL"

    def test_raw_stats_contains_db(self) -> None:
        """raw_stats['db'] is populated from API db field."""
        ioc = make_md5_ioc("a" * 32)
        mock_resp = make_mock_response(200, HASHLOOKUP_FOUND_MD5_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "db" in result.raw_stats
        assert result.raw_stats["db"] == "RDS_2022.09.1_Modern"

    def test_raw_stats_defaults_when_fields_missing(self) -> None:
        """raw_stats uses empty strings for missing FileName, source, db fields."""
        ioc = make_md5_ioc("a" * 32)
        minimal_response = {"MD5": "a" * 32}  # No FileName, source, db
        mock_resp = make_mock_response(200, minimal_response)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["file_name"] == ""
        assert result.raw_stats["source"] == "NSRL"  # default fallback
        assert result.raw_stats["db"] == ""


class TestLookupNotFound:

    def test_404_returns_no_data_result(self) -> None:
        """404 response -> EnrichmentResult(verdict='no_data'), detection_count=0, total_engines=0."""
        ioc = make_sha256_ioc("c" * 64)
        mock_resp = make_mock_response(404)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"404 must return EnrichmentResult (not EnrichmentError), got {type(result).__name__}: {result!r}"
        )
        assert result.verdict == "no_data"
        assert result.detection_count == 0
        assert result.total_engines == 0

    def test_404_returns_result_not_error(self) -> None:
        """404 response -> isinstance(result, EnrichmentResult) is True, NOT EnrichmentError."""
        ioc = make_sha1_ioc("b" * 40)
        mock_resp = make_mock_response(404)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            "404 from CIRCL Hashlookup is not an error — it means 'hash not in NSRL', not 'failure'"
        )
        assert not isinstance(result, EnrichmentError)

    def test_404_returns_empty_raw_stats(self) -> None:
        """404 -> raw_stats is empty dict {}."""
        ioc = make_md5_ioc("a" * 32)
        mock_resp = make_mock_response(404)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats == {}


class TestLookupErrors:

    def test_unsupported_type_ipv4(self) -> None:
        """IPV4 IOC -> EnrichmentError, provider='CIRCL Hashlookup', error contains 'Unsupported'."""
        ioc = make_ipv4_ioc("8.8.8.8")

        result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "CIRCL Hashlookup"
        assert "Unsupported" in result.error or "unsupported" in result.error.lower()

    def test_unsupported_type_domain(self) -> None:
        """DOMAIN IOC -> EnrichmentError (domains not supported by Hashlookup)."""
        ioc = make_domain_ioc("evil.com")

        result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "CIRCL Hashlookup"

    def test_http_400_malformed_hash(self) -> None:
        """HTTP 400 (malformed hash) -> EnrichmentError with 'HTTP 400'."""
        ioc = make_md5_ioc("not-a-valid-hash")
        mock_resp = make_mock_response(400)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "CIRCL Hashlookup"
        assert "HTTP 400" in result.error

    def test_http_500(self) -> None:
        """HTTP 500 response -> EnrichmentError with 'HTTP 500' in error."""
        ioc = make_md5_ioc("a" * 32)
        mock_resp = make_mock_response(500)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "CIRCL Hashlookup"
        assert "HTTP 500" in result.error

    def test_timeout(self) -> None:
        """Network timeout -> EnrichmentError with 'Timeout' in error."""
        ioc = make_md5_ioc("a" * 32)

        adapter = _make_adapter()
        mock_adapter_session(adapter, side_effect=requests.exceptions.Timeout("timed out"))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "CIRCL Hashlookup"
        assert "Timeout" in result.error or "timed out" in result.error.lower()

    def test_ssrf_validation_blocks_disallowed_host(self) -> None:
        """Adapter with allowed_hosts=[] -> EnrichmentError before network call."""
        ioc = make_md5_ioc("a" * 32)
        adapter = HashlookupAdapter(allowed_hosts=[])

        mock_adapter_session(adapter, side_effect=AssertionError("Should not reach network"))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError), (
            "Expected EnrichmentError when host not in allowed_hosts (SSRF check)"
        )
        assert (
            "SSRF" in result.error
            or "allowed" in result.error.lower()
            or "allowlist" in result.error.lower()
        )


class TestHTTPSafetyControls:

    def test_response_size_limit(self) -> None:
        """SEC-05: Responses exceeding 1 MB must be rejected with EnrichmentError."""
        ioc = make_md5_ioc("a" * 32)

        oversized_chunk = b"x" * (MAX_RESPONSE_BYTES + 1)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.iter_content = MagicMock(return_value=iter([oversized_chunk]))

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError), (
            f"Expected EnrichmentError for oversized response, got {type(result).__name__}"
        )

    def test_uses_allow_redirects_false(self) -> None:
        """SEC-06: requests.get must be called with allow_redirects=False."""
        ioc = make_md5_ioc("a" * 32)
        mock_resp = make_mock_response(200, HASHLOOKUP_FOUND_MD5_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        adapter.lookup(ioc)

        call_kwargs = adapter._session.get.call_args.kwargs
        assert call_kwargs.get("allow_redirects") is False, (
            "allow_redirects must be False (SEC-06)"
        )

    def test_uses_stream_true(self) -> None:
        """SEC-05: requests.get must be called with stream=True."""
        ioc = make_md5_ioc("a" * 32)
        mock_resp = make_mock_response(200, HASHLOOKUP_FOUND_MD5_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        adapter.lookup(ioc)

        call_kwargs = adapter._session.get.call_args.kwargs
        assert call_kwargs.get("stream") is True, "stream must be True (SEC-05)"


class TestURLPattern:

    def test_md5_url_uses_md5_path_segment(self) -> None:
        """MD5 lookup URL uses /lookup/md5/{hash} path."""
        ioc = make_md5_ioc("a" * 32)
        mock_resp = make_mock_response(200, HASHLOOKUP_FOUND_MD5_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert "/lookup/md5/" in called_url, f"Expected /lookup/md5/ in URL, got: {called_url}"
        assert "a" * 32 in called_url

    def test_sha1_url_uses_sha1_path_segment(self) -> None:
        """SHA1 lookup URL uses /lookup/sha1/{hash} path."""
        ioc = make_sha1_ioc("b" * 40)
        mock_resp = make_mock_response(200, HASHLOOKUP_FOUND_SHA1_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert "/lookup/sha1/" in called_url, f"Expected /lookup/sha1/ in URL, got: {called_url}"

    def test_sha256_url_uses_sha256_path_segment(self) -> None:
        """SHA256 lookup URL uses /lookup/sha256/{hash} path."""
        ioc = make_sha256_ioc("c" * 64)
        mock_resp = make_mock_response(200, HASHLOOKUP_FOUND_SHA256_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert "/lookup/sha256/" in called_url, f"Expected /lookup/sha256/ in URL, got: {called_url}"


class TestSupportedTypes:

    def test_supported_types_contains_md5(self) -> None:
        """IOCType.MD5 must be in HashlookupAdapter.supported_types."""
        assert IOCType.MD5 in HashlookupAdapter.supported_types

    def test_supported_types_contains_sha1(self) -> None:
        """IOCType.SHA1 must be in HashlookupAdapter.supported_types."""
        assert IOCType.SHA1 in HashlookupAdapter.supported_types

    def test_supported_types_contains_sha256(self) -> None:
        """IOCType.SHA256 must be in HashlookupAdapter.supported_types."""
        assert IOCType.SHA256 in HashlookupAdapter.supported_types

    def test_supported_types_excludes_ipv4(self) -> None:
        """IOCType.IPV4 must NOT be in HashlookupAdapter.supported_types."""
        assert IOCType.IPV4 not in HashlookupAdapter.supported_types

    def test_supported_types_excludes_domain(self) -> None:
        """IOCType.DOMAIN must NOT be in HashlookupAdapter.supported_types."""
        assert IOCType.DOMAIN not in HashlookupAdapter.supported_types

    def test_supported_types_is_frozenset(self) -> None:
        """supported_types must be a frozenset."""
        assert isinstance(HashlookupAdapter.supported_types, frozenset)


class TestProtocolConformance:

    def test_hashlookup_adapter_is_provider(self) -> None:
        """HashlookupAdapter instance must satisfy the Provider protocol."""
        adapter = HashlookupAdapter(allowed_hosts=[])
        assert isinstance(adapter, Provider), (
            "HashlookupAdapter must satisfy the Provider protocol via @runtime_checkable"
        )

    def test_hashlookup_adapter_name(self) -> None:
        """HashlookupAdapter.name must equal 'CIRCL Hashlookup'."""
        assert HashlookupAdapter.name == "CIRCL Hashlookup"

    def test_hashlookup_requires_api_key_false(self) -> None:
        """HashlookupAdapter.requires_api_key must be False (zero-auth provider)."""
        assert HashlookupAdapter.requires_api_key is False

    def test_hashlookup_is_configured_always_true(self) -> None:
        """HashlookupAdapter.is_configured() must always return True regardless of config."""
        adapter = HashlookupAdapter(allowed_hosts=[])
        assert adapter.is_configured() is True


class TestAllowedHostsIntegration:

    def test_config_allows_hashlookup(self) -> None:
        """'hashlookup.circl.lu' must be in Config.ALLOWED_API_HOSTS (SSRF allowlist)."""
        from app.config import Config
        assert "hashlookup.circl.lu" in Config.ALLOWED_API_HOSTS, (
            "hashlookup.circl.lu missing from ALLOWED_API_HOSTS — "
            "HashlookupAdapter will always fail SSRF validation in production"
        )
