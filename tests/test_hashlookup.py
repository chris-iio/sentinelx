"""Tests for CIRCL Hashlookup NSRL adapter — verdict logic and response parsing.

Contract tests (protocol, error handling, safety controls) are in test_adapter_contract.py.

All HTTP calls are mocked using unittest.mock.patch -- no real API calls.
"""
from __future__ import annotations

from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.adapters.hashlookup import HashlookupAdapter
from tests.helpers import (
    make_mock_response,
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

