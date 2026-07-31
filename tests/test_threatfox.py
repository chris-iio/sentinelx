"""Tests for ThreatFox (abuse.ch) API adapter — verdict logic and response parsing.

Contract tests (protocol, error handling, safety controls) are in test_adapter_contract.py.

All HTTP calls are mocked using unittest.mock.patch — no real API calls.
"""
from __future__ import annotations

from collections.abc import Iterator
import inspect

import requests

from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOCType
from app.enrichment.adapters.threatfox import (
    TFAdapter,
    _HASH_TYPES,
    _higher_confidence_record,
    _parse_response,
    _select_best_record,
    _threatfox_raw_stats,
    _threatfox_result,
    _threatfox_verdict,
)
from tests.helpers import (
    make_mock_response,
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
    def test_hash_type_membership_uses_static_frozenset(self) -> None:
        """ThreatFox hash routing should reuse a static membership table."""
        assert isinstance(_HASH_TYPES, frozenset)
        assert _HASH_TYPES == frozenset((IOCType.MD5, IOCType.SHA1, IOCType.SHA256))

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
        assert result.total_engines == 0
        assert result.scan_date is None
        assert result.raw_stats == {}

    def test_ok_with_empty_data_returns_no_data_before_record_selection(self, monkeypatch) -> None:
        """ThreatFox ok responses without records should not build an empty suspicious hit."""
        import app.enrichment.adapters.threatfox as threatfox

        def fail_select(_data):
            raise AssertionError("empty ThreatFox data should return before selecting a record")

        monkeypatch.setattr(threatfox, "_select_best_record", fail_select)

        result = threatfox._parse_response(
            make_sha256_ioc("b" * 64),
            {"query_status": "ok", "data": []},
        )

        assert result.verdict == "no_data"
        assert result.detection_count == 0
        assert result.total_engines == 0
        assert result.raw_stats == {}

    def test_missing_data_avoids_eager_default_list(self) -> None:
        """Missing data should not allocate through dict.get's default argument."""
        ioc = make_sha256_ioc("b" * 64)

        class NoDefaultBody(dict):
            def get(self, key, default=None):
                if key == "data" and default is not None:
                    raise AssertionError("ThreatFox data parsing should avoid eager default list allocation")
                return super().get(key, default)

        result = _parse_response(ioc, NoDefaultBody({"query_status": "ok"}))

        assert result.verdict == "no_data"
        assert result.detection_count == 0
        assert result.total_engines == 0
        assert result.raw_stats == {}

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

    def test_result_helper_preserves_provider_envelope(self) -> None:
        """ThreatFox result construction should keep the provider envelope centralized."""
        ioc = make_sha256_ioc("b" * 64)
        raw_stats = {"confidence_level": 90, "malware_printable": "Mirai"}

        result = _threatfox_result(
            ioc=ioc,
            verdict="malicious",
            detection_count=1,
            total_engines=1,
            scan_date="2024-01-15 12:00:00 UTC",
            raw_stats=raw_stats,
        )

        assert result.ioc is ioc
        assert result.provider == "ThreatFox"
        assert result.verdict == "malicious"
        assert result.detection_count == 1
        assert result.total_engines == 1
        assert result.scan_date == "2024-01-15 12:00:00 UTC"
        assert result.raw_stats is raw_stats

    def test_parse_response_delegates_verdict_and_raw_stats_helpers(self) -> None:
        """ThreatFox parser should not own confidence verdicting or raw_stats literals."""
        source = inspect.getsource(_parse_response)

        assert 'abusech_data_records(body, no_data_status="no_result")' in source
        assert "_threatfox_verdict(confidence_level)" in source
        assert "_threatfox_raw_stats(best, confidence_level)" in source
        assert 'body.get("data")' not in source
        assert 'body.get("query_status"' not in source
        assert "CONFIDENCE_THRESHOLD else" not in source
        assert '"threat_type": best.get("threat_type")' not in source

    def test_raw_stats_helper_preserves_key_order_and_values(self) -> None:
        """Selected-record metadata should keep the public raw_stats shape stable."""
        record = _tf_hit_response(confidence_level=90)["data"][0]

        raw_stats = _threatfox_raw_stats(record, 90)

        assert list(raw_stats) == [
            "threat_type",
            "malware_printable",
            "confidence_level",
            "ioc_type_desc",
        ]
        assert raw_stats["threat_type"] == record["threat_type"]
        assert raw_stats["malware_printable"] == record["malware_printable"]
        assert raw_stats["confidence_level"] == 90
        assert raw_stats["ioc_type_desc"] == record["ioc_type_desc"]


# -- Task 1 Tests: Confidence threshold boundary tests -------------------------

class TestConfidenceThreshold:
    def test_verdict_helper_preserves_confidence_threshold(self) -> None:
        """Threshold semantics should live in the verdict helper."""
        assert _threatfox_verdict(75) == "malicious"
        assert _threatfox_verdict(74) == "suspicious"

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

    def test_best_record_selection_short_circuits_on_perfect_confidence(self) -> None:
        """A perfect confidence record is the best possible record, so selection should stop."""

        class ExplodingTail(list):
            def __iter__(self) -> Iterator[dict]:
                yield {
                    "confidence_level": 20,
                    "malware_printable": "Low",
                }
                yield {
                    "confidence_level": 100,
                    "malware_printable": "Perfect",
                }
                raise AssertionError("best-record selection should stop at perfect confidence")

        best = _select_best_record(ExplodingTail())

        assert best["confidence_level"] == 100
        assert best["malware_printable"] == "Perfect"

    def test_best_record_selection_skips_iteration_for_zero_to_four_records(self) -> None:
        """Short ThreatFox result sets should use direct indexed comparisons."""

        class NoIterRecords(list):
            def __iter__(self) -> Iterator[dict]:
                raise AssertionError("short ThreatFox record selection should not iterate")

        low = {"confidence_level": 20, "malware_printable": "Low"}
        high = {"confidence_level": 90, "malware_printable": "High"}
        mid = {"confidence_level": 50, "malware_printable": "Mid"}
        fourth = {"confidence_level": 75, "malware_printable": "Fourth"}

        assert _select_best_record([]) == {}
        assert _select_best_record(NoIterRecords([high])) is high
        assert _select_best_record(NoIterRecords([high, low])) is high
        assert _select_best_record(NoIterRecords([low, high])) is high
        assert _select_best_record(NoIterRecords([mid, low, high])) is high
        assert _select_best_record(NoIterRecords([mid, low, fourth, high])) is high

    def test_best_record_selection_delegates_pair_comparison_before_loop(self) -> None:
        """ThreatFox short-path comparison should stay isolated from the fallback loop."""
        source = inspect.getsource(_select_best_record)
        direct_path, fallback = source.split("best: dict = {}", 1)

        assert "_higher_confidence_record(first, second)" in direct_path
        assert "_higher_confidence_record(_higher_confidence_record(first, second), third)" in direct_path
        assert "for record in data" not in direct_path
        assert "for record in data" in fallback
        assert _higher_confidence_record({"confidence_level": 75}, {"confidence_level": 74}) == {
            "confidence_level": 75
        }
