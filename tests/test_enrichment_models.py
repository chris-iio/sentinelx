"""Tests for enrichment result models.

Verifies that EnrichmentResult and EnrichmentError are frozen dataclasses
that correctly store IOC references and all result fields.
"""
import pytest

from app.pipeline.models import IOC, IOCType
from app.enrichment.models import EnrichmentError, EnrichmentResult


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

    def test_unsupported_type_error(self) -> None:
        cve_ioc = IOC(type=IOCType.CVE, value="CVE-2024-1234", raw_match="CVE-2024-1234")
        err = EnrichmentError(
            ioc=cve_ioc,
            provider="VirusTotal",
            error="Unsupported type",
        )
        assert err.ioc.type == IOCType.CVE
        assert "Unsupported" in err.error
