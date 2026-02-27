"""Tests for the IOC classifier — type detection from normalized strings.

Covers all 8 IOC types with positive cases, negative cases, and precedence.
"""

from app.pipeline.classifier import classify
from app.pipeline.models import IOC, IOCType


class TestClassifyIPv4:
    """Tests for IPv4 classification."""

    def test_loopback_address(self):
        result = classify("127.0.0.1", "127.0.0.1")
        assert result is not None
        assert result.type == IOCType.IPV4
        assert result.value == "127.0.0.1"
        assert result.raw_match == "127.0.0.1"

    def test_private_rfc1918(self):
        result = classify("192.168.1.1", "192.168.1.1")
        assert result is not None
        assert result.type == IOCType.IPV4

    def test_private_10_block(self):
        result = classify("10.0.0.1", "10.0.0.1")
        assert result is not None
        assert result.type == IOCType.IPV4

    def test_public_dns(self):
        result = classify("8.8.8.8", "8.8.8.8")
        assert result is not None
        assert result.type == IOCType.IPV4

    def test_invalid_octet_too_large(self):
        """999.999.999.999 should not classify as IPv4"""
        result = classify("999.999.999.999", "999.999.999.999")
        assert result is None or result.type != IOCType.IPV4

    def test_incomplete_address(self):
        """192.168.1 (only 3 octets) should not classify as IPv4"""
        result = classify("192.168.1", "192.168.1")
        assert result is None or result.type != IOCType.IPV4


class TestClassifyIPv6:
    """Tests for IPv6 classification."""

    def test_full_ipv6(self):
        result = classify("2001:0db8:85a3::8a2e:0370:7334", "2001:0db8:85a3::8a2e:0370:7334")
        assert result is not None
        assert result.type == IOCType.IPV6

    def test_loopback_ipv6(self):
        result = classify("::1", "::1")
        assert result is not None
        assert result.type == IOCType.IPV6

    def test_link_local_ipv6(self):
        result = classify("fe80::1", "fe80::1")
        assert result is not None
        assert result.type == IOCType.IPV6

    def test_invalid_ipv6_partial(self):
        """Partial IPv6-like string should not classify"""
        result = classify("2001:db8", "2001:db8")
        # Not a valid complete IPv6 — should not classify as IPv6
        assert result is None or result.type != IOCType.IPV6


class TestClassifyDomain:
    """Tests for domain classification."""

    def test_simple_domain(self):
        result = classify("example.com", "example.com")
        assert result is not None
        assert result.type == IOCType.DOMAIN

    def test_subdomain(self):
        result = classify("sub.example.co.uk", "sub.example.co.uk")
        assert result is not None
        assert result.type == IOCType.DOMAIN

    def test_hyphenated_domain(self):
        result = classify("evil-domain.org", "evil-domain.org")
        assert result is not None
        assert result.type == IOCType.DOMAIN

    def test_localhost_rejected(self):
        """localhost has no dot so should not classify as domain"""
        result = classify("localhost", "localhost")
        assert result is None or result.type != IOCType.DOMAIN

    def test_bare_tld_rejected(self):
        """A bare TLD like 'com' should not classify as domain"""
        result = classify("com", "com")
        assert result is None or result.type != IOCType.DOMAIN


class TestClassifyURL:
    """Tests for URL classification."""

    def test_http_url(self):
        result = classify("http://example.com", "http://example.com")
        assert result is not None
        assert result.type == IOCType.URL

    def test_https_url(self):
        result = classify("https://example.com", "https://example.com")
        assert result is not None
        assert result.type == IOCType.URL

    def test_https_url_with_path_and_query(self):
        result = classify("https://example.com/path?q=1", "https://example.com/path?q=1")
        assert result is not None
        assert result.type == IOCType.URL

    def test_url_with_ip_and_port(self):
        result = classify("http://192.168.1.1:8080", "http://192.168.1.1:8080")
        assert result is not None
        assert result.type == IOCType.URL

    def test_url_with_ip_takes_url_precedence(self):
        """A URL containing an IP should classify as URL, not IPv4 (URL has higher precedence)"""
        result = classify("http://192.168.1.1", "http://192.168.1.1")
        assert result is not None
        assert result.type == IOCType.URL


class TestClassifyMD5:
    """Tests for MD5 hash classification (32 hex chars)."""

    def test_known_md5(self):
        """MD5 of empty string"""
        result = classify("d41d8cd98f00b204e9800998ecf8427e", "d41d8cd98f00b204e9800998ecf8427e")
        assert result is not None
        assert result.type == IOCType.MD5

    def test_md5_uppercase(self):
        result = classify("D41D8CD98F00B204E9800998ECF8427E", "D41D8CD98F00B204E9800998ECF8427E")
        assert result is not None
        assert result.type == IOCType.MD5

    def test_31_hex_not_md5(self):
        """31 hex chars should not classify as MD5"""
        result = classify("d41d8cd98f00b204e9800998ecf8427", "d41d8cd98f00b204e9800998ecf8427")
        assert result is None or result.type != IOCType.MD5

    def test_33_hex_not_md5(self):
        """33 hex chars should not classify as MD5"""
        result = classify("d41d8cd98f00b204e9800998ecf8427e1", "d41d8cd98f00b204e9800998ecf8427e1")
        assert result is None or result.type != IOCType.MD5


class TestClassifySHA1:
    """Tests for SHA1 hash classification (40 hex chars)."""

    def test_known_sha1(self):
        """SHA1 of empty string"""
        result = classify("da39a3ee5e6b4b0d3255bfef95601890afd80709", "da39a3ee5e6b4b0d3255bfef95601890afd80709")
        assert result is not None
        assert result.type == IOCType.SHA1

    def test_sha1_uppercase(self):
        result = classify("DA39A3EE5E6B4B0D3255BFEF95601890AFD80709", "DA39A3EE5E6B4B0D3255BFEF95601890AFD80709")
        assert result is not None
        assert result.type == IOCType.SHA1

    def test_39_hex_not_sha1(self):
        result = classify("da39a3ee5e6b4b0d3255bfef95601890afd8070", "da39a3ee5e6b4b0d3255bfef95601890afd8070")
        assert result is None or result.type != IOCType.SHA1


class TestClassifySHA256:
    """Tests for SHA256 hash classification (64 hex chars)."""

    def test_known_sha256(self):
        """SHA256 of empty string"""
        result = classify(
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )
        assert result is not None
        assert result.type == IOCType.SHA256

    def test_sha256_uppercase(self):
        result = classify(
            "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855",
            "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855",
        )
        assert result is not None
        assert result.type == IOCType.SHA256

    def test_sha256_takes_precedence_over_shorter_hashes(self):
        """64-char hex should always classify as SHA256, never as SHA1 or MD5"""
        value = "a" * 64
        result = classify(value, value)
        assert result is not None
        assert result.type == IOCType.SHA256

    def test_63_hex_not_sha256(self):
        value = "a" * 63
        result = classify(value, value)
        assert result is None or result.type != IOCType.SHA256


class TestClassifyCVE:
    """Tests for CVE classification."""

    def test_cve_2024(self):
        result = classify("CVE-2024-12345", "CVE-2024-12345")
        assert result is not None
        assert result.type == IOCType.CVE

    def test_cve_2025(self):
        result = classify("CVE-2025-49596", "CVE-2025-49596")
        assert result is not None
        assert result.type == IOCType.CVE

    def test_cve_lowercase(self):
        result = classify("cve-2024-12345", "cve-2024-12345")
        assert result is not None
        assert result.type == IOCType.CVE

    def test_cve_no_id_rejected(self):
        """CVE-2024 without the numeric ID part should not classify as CVE"""
        result = classify("CVE-2024", "CVE-2024")
        assert result is None or result.type != IOCType.CVE

    def test_cve_takes_highest_precedence(self):
        """CVE should be classified as CVE even if it could match other patterns"""
        result = classify("CVE-2024-12345", "CVE-2024-12345")
        assert result is not None
        assert result.type == IOCType.CVE


class TestClassifyPrecedence:
    """Tests for classification precedence ordering."""

    def test_sha256_before_sha1(self):
        """64-char hex string must not be classified as SHA1"""
        value = "b" * 64
        result = classify(value, value)
        assert result is not None
        assert result.type == IOCType.SHA256

    def test_sha256_before_md5(self):
        """64-char hex string must not be classified as MD5"""
        value = "c" * 64
        result = classify(value, value)
        assert result is not None
        assert result.type == IOCType.SHA256

    def test_sha1_before_md5(self):
        """40-char hex string must not be classified as MD5"""
        value = "d" * 40
        result = classify(value, value)
        assert result is not None
        assert result.type == IOCType.SHA1

    def test_url_before_ipv4(self):
        """http://IP should classify as URL not IPv4"""
        result = classify("http://10.0.0.1", "http://10.0.0.1")
        assert result is not None
        assert result.type == IOCType.URL

    def test_url_before_domain(self):
        """https://domain.com should classify as URL not DOMAIN"""
        result = classify("https://example.com", "https://example.com")
        assert result is not None
        assert result.type == IOCType.URL


class TestClassifyNone:
    """Tests for inputs that should not classify to any IOC type."""

    def test_empty_string(self):
        result = classify("", "")
        assert result is None

    def test_random_text(self):
        result = classify("hello world", "hello world")
        assert result is None

    def test_plain_number(self):
        result = classify("12345", "12345")
        assert result is None

    def test_returns_ioc_dataclass(self):
        """Successful classification returns an IOC instance"""
        result = classify("8.8.8.8", "8.8.8.8")
        assert isinstance(result, IOC)
