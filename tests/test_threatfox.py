"""Tests for ThreatFox (abuse.ch) API adapter.

Tests IOC type coverage, confidence-based verdict mapping, error handling,
and all HTTP safety controls (SEC-04, SEC-05, SEC-06, SEC-07/SEC-16).

All HTTP calls are mocked using unittest.mock.patch — no real API calls.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import requests

from app.pipeline.models import IOC, IOCType
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.adapters.threatfox import TFAdapter
from app.enrichment.http_safety import MAX_RESPONSE_BYTES


ALLOWED_HOSTS = ["threatfox-api.abuse.ch"]

# -- Fixtures / helpers -------------------------------------------------------

def _make_adapter(allowed_hosts: list[str] | None = None) -> TFAdapter:
    return TFAdapter(allowed_hosts=allowed_hosts if allowed_hosts is not None else ALLOWED_HOSTS)


def _make_mock_response(status_code: int, body: dict | None = None) -> MagicMock:
    """Build a mock requests.Response for POST."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if body is not None:
        raw_bytes = json.dumps(body).encode()
        mock_resp.iter_content = MagicMock(return_value=iter([raw_bytes]))
    if status_code >= 400:
        http_err = requests.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status = MagicMock(side_effect=http_err)
    else:
        mock_resp.raise_for_status = MagicMock()
    return mock_resp


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
        sha256 = "a" * 64
        ioc = IOC(type=IOCType.SHA256, value=sha256, raw_match=sha256)
        body = _tf_hit_response(confidence_level=90, ioc_type="sha256_hash")
        mock_resp = _make_mock_response(200, body)

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.post.return_value = mock_resp

            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.provider == "ThreatFox"
        assert result.verdict == "malicious"
        assert "threat_type" in result.raw_stats
        assert "malware_printable" in result.raw_stats
        assert "confidence_level" in result.raw_stats
        assert "ioc_type_desc" in result.raw_stats

    def test_lookup_domain_found_low_confidence(self) -> None:
        """search_ioc for domain with confidence=50 -> verdict=suspicious."""
        ioc = IOC(type=IOCType.DOMAIN, value="evil.example.com", raw_match="evil.example.com")
        body = _tf_hit_response(confidence_level=50, ioc_type="domain")
        mock_resp = _make_mock_response(200, body)

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.post.return_value = mock_resp

            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "suspicious"

    def test_lookup_ip_found(self) -> None:
        """search_ioc for IPv4 with confidence=80 -> verdict=malicious."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        body = _tf_hit_response(confidence_level=80, ioc_type="ip:port")
        mock_resp = _make_mock_response(200, body)

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.post.return_value = mock_resp

            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"
        assert result.provider == "ThreatFox"

    def test_lookup_url_found(self) -> None:
        """search_ioc for URL -> EnrichmentResult with correct fields."""
        url_val = "http://evil.example.com/malware"
        ioc = IOC(type=IOCType.URL, value=url_val, raw_match=url_val)
        body = _tf_hit_response(confidence_level=85, ioc_type="url")
        mock_resp = _make_mock_response(200, body)

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.post.return_value = mock_resp

            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"

    def test_lookup_md5_found(self) -> None:
        """search_hash for MD5 -> EnrichmentResult."""
        md5 = "d" * 32
        ioc = IOC(type=IOCType.MD5, value=md5, raw_match=md5)
        body = _tf_hit_response(confidence_level=75, ioc_type="md5_hash")
        mock_resp = _make_mock_response(200, body)

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.post.return_value = mock_resp

            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"


# -- Task 1 Tests: Edge cases --------------------------------------------------

class TestEdgeCases:
    def test_lookup_not_found(self) -> None:
        """query_status=no_result -> verdict=no_data, detection_count=0."""
        ioc = IOC(type=IOCType.SHA256, value="b" * 64, raw_match="b" * 64)
        mock_resp = _make_mock_response(200, _tf_no_result_response())

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.post.return_value = mock_resp

            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"
        assert result.detection_count == 0

    def test_lookup_unsupported_type_cve(self) -> None:
        """CVE IOC type -> EnrichmentError with 'Unsupported type'."""
        ioc = IOC(type=IOCType.CVE, value="CVE-2024-1234", raw_match="CVE-2024-1234")
        result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert "Unsupported" in result.error or "unsupported" in result.error.lower()

    def test_lookup_timeout(self) -> None:
        """requests.Timeout -> EnrichmentError with 'Timeout'."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.post.side_effect = requests.exceptions.Timeout("Connection timed out")

            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert "Timeout" in result.error or "timeout" in result.error.lower()

    def test_lookup_http_error(self) -> None:
        """HTTP error from server -> EnrichmentError."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_response(500)

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.post.return_value = mock_resp
            # Make raise_for_status raise on call
            mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
                response=mock_resp
            )

            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)

    def test_ssrf_validation(self) -> None:
        """allowed_hosts missing threatfox-api.abuse.ch -> EnrichmentError with SSRF message."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        adapter = TFAdapter(allowed_hosts=[])

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.post.side_effect = AssertionError("Should not reach network")

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
        ioc = IOC(type=IOCType.SHA256, value="c" * 64, raw_match="c" * 64)
        body = _tf_hit_response(confidence_level=75)
        mock_resp = _make_mock_response(200, body)

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.post.return_value = mock_resp

            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious", (
            f"Expected 'malicious' for confidence=75, got {result.verdict!r}"
        )

    def test_confidence_threshold_boundary_74(self) -> None:
        """confidence_level=74 -> verdict=suspicious (<75 threshold)."""
        ioc = IOC(type=IOCType.SHA256, value="c" * 64, raw_match="c" * 64)
        body = _tf_hit_response(confidence_level=74)
        mock_resp = _make_mock_response(200, body)

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.post.return_value = mock_resp

            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "suspicious", (
            f"Expected 'suspicious' for confidence=74, got {result.verdict!r}"
        )


# -- Task 1 Tests: HTTP safety controls ----------------------------------------

class TestHTTPSafetyControls:
    def test_response_size_limit(self) -> None:
        """SEC-05: Response exceeding 1 MB -> EnrichmentError."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        oversized_chunk = b"x" * (MAX_RESPONSE_BYTES + 1)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.iter_content = MagicMock(return_value=iter([oversized_chunk]))

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.post.return_value = mock_resp

            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError), (
            f"Expected EnrichmentError for oversized response, got {type(result).__name__}"
        )


# -- Task 1 Tests: Multiple results — use highest confidence -------------------

class TestMultipleResults:
    def test_multiple_results_uses_highest_confidence(self) -> None:
        """ThreatFox may return multiple IOC records; adapter should use the highest-confidence one."""
        ioc = IOC(type=IOCType.SHA256, value="a" * 64, raw_match="a" * 64)

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

        mock_resp = _make_mock_response(200, body)

        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.post.return_value = mock_resp

            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        # Must use the record with confidence=90 -> malicious
        assert result.verdict == "malicious", (
            f"Expected 'malicious' (from confidence=90 record), got {result.verdict!r}"
        )
        # Malware family must be from the highest-confidence record
        assert result.raw_stats.get("malware_printable") == "Emotet", (
            f"Expected 'Emotet' (highest confidence record), got {result.raw_stats.get('malware_printable')!r}"
        )
