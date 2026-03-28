"""Tests for ThreatFox (abuse.ch) API adapter.

Tests IOC type coverage, confidence-based verdict mapping, error handling,
and all HTTP safety controls (SEC-04, SEC-05, SEC-06, SEC-07/SEC-16).

All HTTP calls are mocked using unittest.mock.patch — no real API calls.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import requests

from app.pipeline.models import IOCType
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.adapters.threatfox import TFAdapter
from app.enrichment.http_safety import MAX_RESPONSE_BYTES
from tests.helpers import (
    make_mock_response,
    make_cve_ioc,
    make_domain_ioc,
    make_ipv4_ioc,
    make_md5_ioc,
    make_sha256_ioc,
    make_url_ioc,
    mock_adapter_session,
)


ALLOWED_HOSTS = ["threatfox-api.abuse.ch"]

# -- Fixtures / helpers -------------------------------------------------------

def _make_adapter(allowed_hosts: list[str] | None = None) -> TFAdapter:
    return TFAdapter(api_key="test-key", allowed_hosts=allowed_hosts if allowed_hosts is not None else ALLOWED_HOSTS)




def _tf_hit_response(confidence_level: int, ioc_type: str = "sha256_hash") -> dict:
    """Return a ThreatFox API response with one hit at the given confidence."""
    return {
        "query_status": "ok",
        "data": [
            {
                "id": "12345",
                "ioc": "deadbeef" * 8,
                "threat_type": "botnet_cc",
                "threat_type_desc": "Botnet C2",
                "ioc_type": ioc_type,
                "ioc_type_desc": "SHA256 hash of a malware sample",
                "malware": "elf.mirai",
                "malware_printable": "Mirai",
                "malware_alias": None,
                "malware_malpedia": None,
                "confidence_level": confidence_level,
                "first_seen": "2024-01-15 12:00:00 UTC",
                "last_seen": None,
                "reporter": "abuse_ch",
                "reference": None,
                "tags": None,
            }
        ],
    }


def _tf_no_result_response() -> dict:
    return {"query_status": "no_result", "data": "No results found."}


# -- Task 1 Tests: IOC type coverage ------------------------------------------

class TestLookupTypeCoverage:
    def test_lookup_sha256_found_high_confidence(self) -> None:
        """search_hash for SHA256 with confidence=90 -> verdict=malicious."""
        ioc = make_sha256_ioc("a" * 64)
        body = _tf_hit_response(confidence_level=90, ioc_type="sha256_hash")
        mock_resp = make_mock_response(200, body)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)

        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.provider == "ThreatFox"
        assert result.verdict == "malicious"
        assert "threat_type" in result.raw_stats
        assert "malware_printable" in result.raw_stats
        assert "confidence_level" in result.raw_stats
        assert "ioc_type_desc" in result.raw_stats

    def test_lookup_domain_found_low_confidence(self) -> None:
        """search_ioc for domain with confidence=50 -> verdict=suspicious."""
        ioc = make_domain_ioc("evil.example.com")
        body = _tf_hit_response(confidence_level=50, ioc_type="domain")
        mock_resp = make_mock_response(200, body)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)

        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "suspicious"

    def test_lookup_ip_found(self) -> None:
        """search_ioc for IPv4 with confidence=80 -> verdict=malicious."""
        ioc = make_ipv4_ioc()
        body = _tf_hit_response(confidence_level=80, ioc_type="ip:port")
        mock_resp = make_mock_response(200, body)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)

        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"
        assert result.provider == "ThreatFox"

    def test_lookup_url_found(self) -> None:
        """search_ioc for URL -> EnrichmentResult with correct fields."""
        ioc = make_url_ioc("http://evil.example.com/malware")
        body = _tf_hit_response(confidence_level=85, ioc_type="url")
        mock_resp = make_mock_response(200, body)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)

        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"

    def test_lookup_md5_found(self) -> None:
        """search_hash for MD5 -> EnrichmentResult."""
        ioc = make_md5_ioc("d" * 32)
        body = _tf_hit_response(confidence_level=75, ioc_type="md5_hash")
        mock_resp = make_mock_response(200, body)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)

        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"


# -- Task 1 Tests: Edge cases --------------------------------------------------

class TestEdgeCases:
    def test_lookup_not_found(self) -> None:
        """query_status=no_result -> verdict=no_data, detection_count=0."""
        ioc = make_sha256_ioc("b" * 64)
        mock_resp = make_mock_response(200, _tf_no_result_response())

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)

        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"
        assert result.detection_count == 0

    def test_lookup_unsupported_type_cve(self) -> None:
        """CVE IOC type -> EnrichmentError with 'Unsupported type'."""
        ioc = make_cve_ioc("CVE-2024-1234")
        result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert "Unsupported" in result.error or "unsupported" in result.error.lower()

    def test_lookup_timeout(self) -> None:
        """requests.Timeout -> EnrichmentError with 'Timeout'."""
        ioc = make_ipv4_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", side_effect=requests.exceptions.Timeout("Connection timed out"))

        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert "Timeout" in result.error or "timed out" in result.error.lower()

    def test_lookup_http_error(self) -> None:
        """HTTP error from server -> EnrichmentError."""
        ioc = make_ipv4_ioc()
        mock_resp = make_mock_response(500)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)
        # Make raise_for_status raise on call
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_resp
        )

        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)

    def test_ssrf_validation(self) -> None:
        """allowed_hosts missing threatfox-api.abuse.ch -> EnrichmentError with SSRF message."""
        ioc = make_ipv4_ioc()
        adapter = TFAdapter(api_key="test-key", allowed_hosts=[])

        mock_adapter_session(adapter, method="post", side_effect=AssertionError("Should not reach network"))

        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        # Error message must mention SSRF or allowlist
        assert (
            "SSRF" in result.error
            or "allowed" in result.error.lower()
            or "allowlist" in result.error.lower()
        )

    def test_supported_types(self) -> None:
        """TFAdapter.supported_types includes all 7 enrichable IOC types (not CVE)."""
        supported = TFAdapter.supported_types
        expected = {
            IOCType.MD5, IOCType.SHA1, IOCType.SHA256,
            IOCType.DOMAIN, IOCType.IPV4, IOCType.IPV6, IOCType.URL,
        }
        assert expected == supported
        assert IOCType.CVE not in supported


# -- Task 1 Tests: Confidence threshold boundary tests -------------------------

class TestConfidenceThreshold:
    def test_confidence_threshold_boundary_75(self) -> None:
        """confidence_level=75 exactly -> verdict=malicious (>=75 threshold)."""
        ioc = make_sha256_ioc("c" * 64)
        body = _tf_hit_response(confidence_level=75)
        mock_resp = make_mock_response(200, body)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)

        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious", (
            f"Expected 'malicious' for confidence=75, got {result.verdict!r}"
        )

    def test_confidence_threshold_boundary_74(self) -> None:
        """confidence_level=74 -> verdict=suspicious (<75 threshold)."""
        ioc = make_sha256_ioc("c" * 64)
        body = _tf_hit_response(confidence_level=74)
        mock_resp = make_mock_response(200, body)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)

        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "suspicious", (
            f"Expected 'suspicious' for confidence=74, got {result.verdict!r}"
        )


# -- Task 1 Tests: HTTP safety controls ----------------------------------------

class TestHTTPSafetyControls:
    def test_response_size_limit(self) -> None:
        """SEC-05: Response exceeding 1 MB -> EnrichmentError."""
        ioc = make_ipv4_ioc()
        oversized_chunk = b"x" * (MAX_RESPONSE_BYTES + 1)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.iter_content = MagicMock(return_value=iter([oversized_chunk]))

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)

        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError), (
            f"Expected EnrichmentError for oversized response, got {type(result).__name__}"
        )


# -- Task 1 Tests: Multiple results — use highest confidence -------------------

class TestMultipleResults:
    def test_multiple_results_uses_highest_confidence(self) -> None:
        """ThreatFox may return multiple IOC records; adapter should use the highest-confidence one."""
        ioc = make_sha256_ioc("a" * 64)

        body = {
            "query_status": "ok",
            "data": [
                {
                    "id": "1",
                    "ioc": "a" * 64,
                    "threat_type": "botnet_cc",
                    "threat_type_desc": "Botnet C2",
                    "ioc_type": "sha256_hash",
                    "ioc_type_desc": "SHA256 hash",
                    "malware": "elf.generic",
                    "malware_printable": "Generic",
                    "malware_alias": None,
                    "malware_malpedia": None,
                    "confidence_level": 40,  # low confidence
                    "first_seen": "2024-01-01 00:00:00 UTC",
                    "last_seen": None,
                    "reporter": "reporter_a",
                    "reference": None,
                    "tags": None,
                },
                {
                    "id": "2",
                    "ioc": "a" * 64,
                    "threat_type": "payload_delivery",
                    "threat_type_desc": "Payload delivery",
                    "ioc_type": "sha256_hash",
                    "ioc_type_desc": "SHA256 hash",
                    "malware": "win.emotet",
                    "malware_printable": "Emotet",
                    "malware_alias": None,
                    "malware_malpedia": None,
                    "confidence_level": 90,  # high confidence — must win
                    "first_seen": "2024-06-15 08:00:00 UTC",
                    "last_seen": None,
                    "reporter": "reporter_b",
                    "reference": None,
                    "tags": None,
                },
            ],
        }

        mock_resp = make_mock_response(200, body)

        adapter = _make_adapter()
        mock_adapter_session(adapter, method="post", response=mock_resp)

        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        # Must use the record with confidence=90 -> malicious
        assert result.verdict == "malicious", (
            f"Expected 'malicious' (from confidence=90 record), got {result.verdict!r}"
        )
        # Malware family must be from the highest-confidence record
        assert result.raw_stats.get("malware_printable") == "Emotet", (
            f"Expected 'Emotet' (highest confidence record), got {result.raw_stats.get('malware_printable')!r}"
        )
