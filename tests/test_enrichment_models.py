"""Tests for enrichment result models.

Verifies that EnrichmentResult and EnrichmentError are frozen dataclasses
that correctly store IOC references and all result fields.
"""
import pytest

from app.pipeline.models import IOC, IOCType
from app.enrichment.models import (
    EnrichmentError,
    EnrichmentResult,
    error_result,
    no_data_result,
    provider_result,
)


@pytest.fixture
def sample_ioc() -> IOC:
    return IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")


class TestEnrichmentResult:
    def test_stores_ioc_reference(self, sample_ioc: IOC) -> None:
        result = EnrichmentResult(
            ioc=sample_ioc,
            provider="VirusTotal",
            verdict="malicious",
            detection_count=5,
            total_engines=73,
            scan_date="2024-01-15T00:00:00+00:00",
            raw_stats={"malicious": 5, "clean": 68},
        )
        assert result.ioc is sample_ioc

    def test_stores_all_fields(self, sample_ioc: IOC) -> None:
        result = EnrichmentResult(
            ioc=sample_ioc,
            provider="VirusTotal",
            verdict="malicious",
            detection_count=5,
            total_engines=73,
            scan_date="2024-01-15T00:00:00+00:00",
            raw_stats={"malicious": 5},
        )
        assert result.provider == "VirusTotal"
        assert result.verdict == "malicious"
        assert result.detection_count == 5
        assert result.total_engines == 73
        assert result.scan_date == "2024-01-15T00:00:00+00:00"
        assert result.raw_stats == {"malicious": 5}

    def test_is_frozen(self, sample_ioc: IOC) -> None:
        result = EnrichmentResult(
            ioc=sample_ioc,
            provider="VirusTotal",
            verdict="clean",
            detection_count=0,
            total_engines=73,
            scan_date=None,
            raw_stats={},
        )
        with pytest.raises((AttributeError, TypeError)):
            result.verdict = "malicious"  # type: ignore[misc]

    def test_uses_slots_to_avoid_instance_dict(self, sample_ioc: IOC) -> None:
        result = EnrichmentResult(
            ioc=sample_ioc,
            provider="VirusTotal",
            verdict="clean",
            detection_count=0,
            total_engines=73,
            scan_date=None,
            raw_stats={},
        )
        assert not hasattr(result, "__dict__")

    def test_scan_date_can_be_none(self, sample_ioc: IOC) -> None:
        result = EnrichmentResult(
            ioc=sample_ioc,
            provider="VirusTotal",
            verdict="no_data",
            detection_count=0,
            total_engines=0,
            scan_date=None,
            raw_stats={},
        )
        assert result.scan_date is None

    def test_no_data_verdict(self, sample_ioc: IOC) -> None:
        result = EnrichmentResult(
            ioc=sample_ioc,
            provider="VirusTotal",
            verdict="no_data",
            detection_count=0,
            total_engines=0,
            scan_date=None,
            raw_stats={},
        )
        assert result.verdict == "no_data"

    def test_provider_result_preserves_provider_envelope(self, sample_ioc: IOC) -> None:
        raw_stats = {"malicious": 5}

        result = provider_result(
            ioc=sample_ioc,
            provider="VirusTotal",
            verdict="malicious",
            detection_count=5,
            total_engines=73,
            scan_date="2024-01-15T00:00:00+00:00",
            raw_stats=raw_stats,
        )

        assert result.ioc is sample_ioc
        assert result.provider == "VirusTotal"
        assert result.verdict == "malicious"
        assert result.detection_count == 5
        assert result.total_engines == 73
        assert result.scan_date == "2024-01-15T00:00:00+00:00"
        assert result.raw_stats is raw_stats

    def test_provider_result_uses_fresh_empty_stats_default(self, sample_ioc: IOC) -> None:
        first = provider_result(
            ioc=sample_ioc,
            provider="VirusTotal",
            verdict="clean",
            detection_count=0,
            total_engines=73,
        )
        second = provider_result(
            ioc=sample_ioc,
            provider="VirusTotal",
            verdict="clean",
            detection_count=0,
            total_engines=73,
        )

        assert first.raw_stats == {}
        assert second.raw_stats == {}
        assert first.raw_stats is not second.raw_stats

    def test_no_data_result_uses_shared_provider_result(self, sample_ioc: IOC) -> None:
        result = no_data_result(sample_ioc, "VirusTotal")

        assert result.verdict == "no_data"
        assert result.detection_count == 0
        assert result.total_engines == 0
        assert "provider_result" in no_data_result.__code__.co_names


class TestEnrichmentError:
    def test_stores_ioc_reference(self, sample_ioc: IOC) -> None:
        err = EnrichmentError(
            ioc=sample_ioc,
            provider="VirusTotal",
            error="Timeout",
        )
        assert err.ioc is sample_ioc

    def test_stores_all_fields(self, sample_ioc: IOC) -> None:
        err = EnrichmentError(
            ioc=sample_ioc,
            provider="VirusTotal",
            error="Rate limit exceeded (429)",
        )
        assert err.provider == "VirusTotal"
        assert err.error == "Rate limit exceeded (429)"

    def test_is_frozen(self, sample_ioc: IOC) -> None:
        err = EnrichmentError(
            ioc=sample_ioc,
            provider="VirusTotal",
            error="Timeout",
        )
        with pytest.raises((AttributeError, TypeError)):
            err.error = "changed"  # type: ignore[misc]

    def test_uses_slots_to_avoid_instance_dict(self, sample_ioc: IOC) -> None:
        err = EnrichmentError(
            ioc=sample_ioc,
            provider="VirusTotal",
            error="Timeout",
        )
        assert not hasattr(err, "__dict__")

    def test_unsupported_type_error(self) -> None:
        cve_ioc = IOC(type=IOCType.CVE, value="CVE-2024-1234", raw_match="CVE-2024-1234")
        err = EnrichmentError(
            ioc=cve_ioc,
            provider="VirusTotal",
            error="Unsupported type",
        )
        assert err.ioc.type == IOCType.CVE
        assert "Unsupported" in err.error

    def test_error_result_preserves_error_envelope(self, sample_ioc: IOC) -> None:
        err = error_result(sample_ioc, "VirusTotal", "HTTP 429")

        assert err.ioc is sample_ioc
        assert err.provider == "VirusTotal"
        assert err.error == "HTTP 429"
