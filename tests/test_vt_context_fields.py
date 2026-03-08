"""Tests for VirusTotal contextual fields (top_detections, reputation).

Verifies that _parse_response extracts top 5 malicious detection names
and reputation score into raw_stats.
"""
from __future__ import annotations

from app.enrichment.adapters.virustotal import _parse_response
from app.pipeline.models import IOC, IOCType


def _make_ioc() -> IOC:
    return IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")


class TestTopDetections:
    def test_extracts_top_malicious_detections(self) -> None:
        """top_detections contains only engines with 'malicious' category."""
        body = {
            "data": {
                "attributes": {
                    "last_analysis_stats": {"malicious": 3, "harmless": 60},
                    "last_analysis_date": 1700000000,
                    "last_analysis_results": {
                        "EngineA": {"category": "malicious", "result": "Trojan.Gen"},
                        "EngineB": {"category": "malicious", "result": "Win32.Malware"},
                        "EngineC": {"category": "malicious", "result": "Backdoor.Agent"},
                        "EngineD": {"category": "harmless", "result": None},
                        "EngineE": {"category": "undetected", "result": None},
                    },
                    "reputation": 42,
                }
            }
        }
        result = _parse_response(_make_ioc(), body)
        detections = result.raw_stats["top_detections"]
        assert len(detections) == 3
        assert "Trojan.Gen" in detections
        assert "Win32.Malware" in detections
        assert "Backdoor.Agent" in detections

    def test_limits_to_5_detections(self) -> None:
        """Only top 5 malicious detection names are kept."""
        results = {}
        for i in range(10):
            results[f"Engine{i}"] = {"category": "malicious", "result": f"Malware{i}"}
        body = {
            "data": {
                "attributes": {
                    "last_analysis_stats": {"malicious": 10},
                    "last_analysis_date": 1700000000,
                    "last_analysis_results": results,
                    "reputation": 0,
                }
            }
        }
        result = _parse_response(_make_ioc(), body)
        assert len(result.raw_stats["top_detections"]) == 5

    def test_empty_when_no_analysis_results(self) -> None:
        """top_detections is empty list when last_analysis_results is absent."""
        body = {
            "data": {
                "attributes": {
                    "last_analysis_stats": {"malicious": 0, "harmless": 70},
                    "last_analysis_date": 1700000000,
                }
            }
        }
        result = _parse_response(_make_ioc(), body)
        assert result.raw_stats["top_detections"] == []

    def test_skips_none_results(self) -> None:
        """Detection names that are None are excluded."""
        body = {
            "data": {
                "attributes": {
                    "last_analysis_stats": {"malicious": 2},
                    "last_analysis_date": 1700000000,
                    "last_analysis_results": {
                        "EngineA": {"category": "malicious", "result": "Trojan.Gen"},
                        "EngineB": {"category": "malicious", "result": None},
                    },
                    "reputation": 10,
                }
            }
        }
        result = _parse_response(_make_ioc(), body)
        assert result.raw_stats["top_detections"] == ["Trojan.Gen"]

    def test_deduplicates_detection_names(self) -> None:
        """Duplicate detection names are collapsed."""
        body = {
            "data": {
                "attributes": {
                    "last_analysis_stats": {"malicious": 3},
                    "last_analysis_date": 1700000000,
                    "last_analysis_results": {
                        "EngineA": {"category": "malicious", "result": "Trojan.Gen"},
                        "EngineB": {"category": "malicious", "result": "Trojan.Gen"},
                        "EngineC": {"category": "malicious", "result": "Win32.Malware"},
                    },
                    "reputation": 0,
                }
            }
        }
        result = _parse_response(_make_ioc(), body)
        detections = result.raw_stats["top_detections"]
        assert len(detections) == 2
        assert "Trojan.Gen" in detections
        assert "Win32.Malware" in detections


class TestReputation:
    def test_extracts_reputation(self) -> None:
        """reputation field is added to raw_stats."""
        body = {
            "data": {
                "attributes": {
                    "last_analysis_stats": {"malicious": 0, "harmless": 60},
                    "last_analysis_date": 1700000000,
                    "reputation": -15,
                }
            }
        }
        result = _parse_response(_make_ioc(), body)
        assert result.raw_stats["reputation"] == -15

    def test_reputation_defaults_to_zero(self) -> None:
        """reputation defaults to 0 when absent."""
        body = {
            "data": {
                "attributes": {
                    "last_analysis_stats": {"malicious": 0, "harmless": 60},
                    "last_analysis_date": 1700000000,
                }
            }
        }
        result = _parse_response(_make_ioc(), body)
        assert result.raw_stats["reputation"] == 0
