"""End-to-end pipeline integration tests.

Tests the full pipeline: extract -> normalize -> classify -> deduplicate.
Verifies that run_pipeline() returns correctly typed, deduplicated IOC objects.
"""
import pytest

from app.pipeline.extractor import run_pipeline
from app.pipeline.models import IOC, IOCType


class TestRunPipelineDeduplication:
    """Test that run_pipeline deduplicates identical normalized IOCs."""

    def test_duplicate_url_collapsed(self):
        """Same URL appearing twice in text -> one IOC result."""
        text = "Alert: hxxp://evil[.]com and hxxp://evil[.]com again"
        results = run_pipeline(text)
        url_results = [r for r in results if r.type == IOCType.URL]
        # Deduplicated: only 1 URL even though it appears twice
        assert len(url_results) == 1

    def test_mixed_defanged_with_duplicates(self):
        """Defanged URL + IP, URL appears twice -> 2 unique IOCs."""
        text = "Alert: hxxp://evil[.]com and hxxp://evil[.]com again, IP 192[.]168[.]1[.]1"
        results = run_pipeline(text)
        types_found = {r.type for r in results}
        assert IOCType.IPV4 in types_found
        # URL should appear once (deduped)
        url_results = [r for r in results if r.type == IOCType.URL]
        assert len(url_results) == 1

    def test_duplicate_hash_collapsed(self):
        """Same hash appearing twice -> one IOC result."""
        h = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        text = f"Hash {h} and also {h}"
        results = run_pipeline(text)
        hash_results = [r for r in results if r.type == IOCType.SHA256]
        assert len(hash_results) == 1


class TestRunPipelineTypes:
    """Test that run_pipeline correctly classifies IOC types."""

    def test_ipv4_classified(self):
        text = "Suspicious IP 10.0.0.1 observed in traffic"
        results = run_pipeline(text)
        types_found = {r.type for r in results}
        assert IOCType.IPV4 in types_found

    def test_url_classified(self):
        text = "Beacon to http://c2.malware.org/beacon detected"
        results = run_pipeline(text)
        types_found = {r.type for r in results}
        assert IOCType.URL in types_found

    def test_sha256_classified(self):
        h = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        text = f"File hash: {h}"
        results = run_pipeline(text)
        types_found = {r.type for r in results}
        assert IOCType.SHA256 in types_found

    def test_cve_classified(self):
        text = "Exploits CVE-2025-49596 in the wild"
        results = run_pipeline(text)
        types_found = {r.type for r in results}
        assert IOCType.CVE in types_found


class TestRunPipelineReturnType:
    """Test that run_pipeline returns correctly typed IOC objects."""

    def test_returns_list(self):
        results = run_pipeline("IP 192.168.1.1")
        assert isinstance(results, list)

    def test_returns_ioc_objects(self):
        results = run_pipeline("IP 192.168.1.1")
        for r in results:
            assert isinstance(r, IOC)

    def test_ioc_has_value(self):
        results = run_pipeline("IP 192.168.1.1")
        ipv4_results = [r for r in results if r.type == IOCType.IPV4]
        assert len(ipv4_results) >= 1
        assert ipv4_results[0].value == "192.168.1.1"

    def test_ioc_has_raw_match(self):
        """IOC.raw_match preserves the original string."""
        results = run_pipeline("IP 192.168.1.1")
        ipv4_results = [r for r in results if r.type == IOCType.IPV4]
        assert len(ipv4_results) >= 1
        assert ipv4_results[0].raw_match  # non-empty


class TestRunPipelineEdgeCases:
    """Edge cases for run_pipeline."""

    def test_empty_text(self):
        results = run_pipeline("")
        assert results == []

    def test_no_iocs_text(self):
        results = run_pipeline("Hello world, nothing suspicious here")
        assert results == []

    def test_realistic_threat_report(self):
        """Realistic threat report with IPv4, URL, hash, CVE."""
        text = (
            "The threat actor uses 198.51.100.42 as C2. "
            "Payload downloads from https://drop.evil.net/stage2. "
            "Sample hash: d41d8cd98f00b204e9800998ecf8427e. "
            "Exploits CVE-2024-12345."
        )
        results = run_pipeline(text)
        types_found = {r.type for r in results}
        # At minimum: IP, URL, MD5, CVE
        assert IOCType.IPV4 in types_found
        assert IOCType.URL in types_found
        assert IOCType.MD5 in types_found
        assert IOCType.CVE in types_found
