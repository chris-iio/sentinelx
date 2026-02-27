"""Tests for the IOC extractor — raw text -> candidate extraction.

Uses both iocextract and iocsearcher under the hood.
Tests cover all required IOC types and edge cases.
"""

from app.pipeline.extractor import extract_iocs


class TestExtractIPv4:
    """Tests for IPv4 address extraction."""

    def test_single_ipv4(self):
        text = "Check IP 192.168.1.1 for suspicious activity"
        results = extract_iocs(text)
        values = [r["raw"] for r in results]
        assert any("192.168.1.1" in v for v in values)

    def test_multiple_ipv4(self):
        text = "Blocked 10.0.0.1 and 172.16.0.50 in firewall"
        results = extract_iocs(text)
        raws = [r["raw"] for r in results]
        assert any("10.0.0.1" in v for v in raws)
        assert any("172.16.0.50" in v for v in raws)

    def test_defanged_ipv4(self):
        text = "Source IP: 192[.]168[.]1[.]1"
        results = extract_iocs(text)
        # iocextract refangs, so the raw should be refanged
        raws = [r["raw"] for r in results]
        assert any("192.168.1.1" in v for v in raws)


class TestExtractURLs:
    """Tests for URL extraction."""

    def test_defanged_hxxp_url(self):
        text = "Visit hxxp://evil[.]com/malware for payload"
        results = extract_iocs(text)
        raws = [r["raw"] for r in results]
        assert any("evil.com" in v or "evil[.]com" in v for v in raws)

    def test_plain_http_url(self):
        text = "Download from http://malicious.example.com/payload.exe"
        results = extract_iocs(text)
        raws = [r["raw"] for r in results]
        assert any("malicious.example.com" in v for v in raws)

    def test_https_url(self):
        text = "C2 beacon to https://command.evil.org/beacon"
        results = extract_iocs(text)
        raws = [r["raw"] for r in results]
        assert any("command.evil.org" in v for v in raws)


class TestExtractHashes:
    """Tests for hash extraction (MD5, SHA1, SHA256)."""

    SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    SHA1 = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
    MD5 = "d41d8cd98f00b204e9800998ecf8427e"

    def test_sha256_hash(self):
        text = f"Hash: {self.SHA256}"
        results = extract_iocs(text)
        raws = [r["raw"] for r in results]
        assert any(self.SHA256.lower() in v.lower() for v in raws)

    def test_sha1_hash(self):
        text = f"SHA1: {self.SHA1}"
        results = extract_iocs(text)
        raws = [r["raw"] for r in results]
        assert any(self.SHA1.lower() in v.lower() for v in raws)

    def test_md5_hash(self):
        text = f"MD5: {self.MD5}"
        results = extract_iocs(text)
        raws = [r["raw"] for r in results]
        assert any(self.MD5.lower() in v.lower() for v in raws)


class TestExtractCVE:
    """Tests for CVE extraction via iocsearcher."""

    def test_cve_extraction(self):
        text = "Vulnerability CVE-2025-49596 is critical"
        results = extract_iocs(text)
        raws = [r["raw"] for r in results]
        assert any("CVE-2025-49596" in v for v in raws)

    def test_cve_2024(self):
        text = "Patch CVE-2024-12345 immediately"
        results = extract_iocs(text)
        raws = [r["raw"] for r in results]
        assert any("CVE-2024-12345" in v for v in raws)


class TestExtractMixedInput:
    """Tests for realistic mixed input (SIEM alerts, threat reports)."""

    def test_mixed_siem_alert(self):
        """Realistic SIEM alert with IP, URL, and hash."""
        text = (
            "ALERT: Connection from 10.1.2.3 to hxxp://evil[.]example[.]com/c2 "
            "downloading payload e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        results = extract_iocs(text)
        raws = [r["raw"] for r in results]
        # Should find IP
        assert any("10.1.2.3" in v for v in raws)
        # Should find URL
        assert any("evil" in v and ("example" in v or "com" in v) for v in raws)
        # Should find SHA256
        assert any("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" in v.lower() for v in raws)

    def test_threat_report_snippet(self):
        """Realistic threat report with multiple IOC types."""
        text = (
            "The actor uses IP 198.51.100.42 as a C2 server. "
            "The dropper contacts https://drop.malware.net/stage2. "
            "Known file hash: d41d8cd98f00b204e9800998ecf8427e. "
            "Exploits CVE-2024-12345 for privilege escalation."
        )
        results = extract_iocs(text)
        raws = [r["raw"] for r in results]
        assert any("198.51.100.42" in v for v in raws)
        assert any("malware.net" in v or "drop.malware.net" in v for v in raws)
        assert any("d41d8cd98f00b204e9800998ecf8427e" in v.lower() for v in raws)
        assert any("CVE-2024-12345" in v for v in raws)


class TestExtractEdgeCases:
    """Edge cases: empty input, no IOCs, type hints."""

    def test_empty_string(self):
        results = extract_iocs("")
        assert results == []

    def test_no_iocs_text(self):
        results = extract_iocs("Hello world, no indicators here")
        assert results == []

    def test_returns_list_of_dicts(self):
        """Each result must be a dict with 'raw' and 'type_hint' keys."""
        text = "IP 192.168.1.1 found"
        results = extract_iocs(text)
        assert isinstance(results, list)
        for r in results:
            assert isinstance(r, dict)
            assert "raw" in r
            assert "type_hint" in r


class TestDeduplicationInExtract:
    """Test that extract_iocs deduplicates repeated raw values."""

    def test_duplicate_ip_not_returned_twice(self):
        """Same IP appearing twice in text should produce one candidate."""
        text = "IP 192.168.1.1 and also 192.168.1.1 again"
        results = extract_iocs(text)
        raws = [r["raw"] for r in results if "192.168.1.1" in r["raw"]]
        assert len(raws) == 1
