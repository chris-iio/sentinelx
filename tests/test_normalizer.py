"""Tests for the IOC normalizer — defanging → canonical form.

Covers 30+ defanging variants documented in the plan spec.
"""

from app.pipeline.normalizer import normalize


class TestSchemeNormalization:
    """Tests for hxxp/hxxps scheme defanging."""

    def test_hxxp_lowercase(self):
        assert normalize("hxxp://example.com") == "http://example.com"

    def test_hxxps_lowercase(self):
        assert normalize("hxxps://example.com") == "https://example.com"

    def test_hxxp_mixed_case_X(self):
        assert normalize("hXXp://example.com") == "http://example.com"

    def test_hxxps_mixed_case_X(self):
        assert normalize("hXXps://example.com") == "https://example.com"

    def test_hxxp_uppercase(self):
        assert normalize("HXXP://example.com") == "http://example.com"

    def test_hxxps_uppercase(self):
        assert normalize("HXXPS://example.com") == "https://example.com"

    def test_hxxp_bracket_colon_slash_slash(self):
        """hxxp[://] variant"""
        assert normalize("hxxp[://]example.com") == "http://example.com"

    def test_hxxps_bracket_colon_slash_slash(self):
        """hxxps[://] variant"""
        assert normalize("hxxps[://]example.com") == "https://example.com"

    def test_hxxp_bracket_colon_then_slashes(self):
        """hxxp[:]//example.com variant"""
        assert normalize("hxxp[:]//example.com") == "http://example.com"

    def test_hxxps_bracket_colon_then_slashes(self):
        """hxxps[:]//example.com variant"""
        assert normalize("hxxps[:]//example.com") == "https://example.com"


class TestDotNormalization:
    """Tests for defanged dot patterns."""

    def test_bracket_dot(self):
        assert normalize("example[.]com") == "example.com"

    def test_paren_dot(self):
        assert normalize("example(.)com") == "example.com"

    def test_brace_dot(self):
        assert normalize("example{.}com") == "example.com"

    def test_bracket_dot_word(self):
        assert normalize("example[dot]com") == "example.com"

    def test_paren_dot_word(self):
        assert normalize("example(dot)com") == "example.com"

    def test_brace_dot_word(self):
        assert normalize("example{dot}com") == "example.com"

    def test_underscore_dot_underscore(self):
        """example_dot_com variant"""
        assert normalize("example_dot_com") == "example.com"

    def test_bracket_dot_in_ip(self):
        assert normalize("192[.]168[.]1[.]1") == "192.168.1.1"

    def test_paren_dot_in_ip(self):
        assert normalize("192(.)168(.)1(.)1") == "192.168.1.1"


class TestAtNormalization:
    """Tests for defanged @ (at) in email-like strings."""

    def test_bracket_at(self):
        assert normalize("user[@]example.com") == "user@example.com"

    def test_bracket_at_word(self):
        assert normalize("user[at]example.com") == "user@example.com"

    def test_paren_at(self):
        assert normalize("user(@)example.com") == "user@example.com"


class TestCombinedPatterns:
    """Tests for multiple patterns applied together."""

    def test_hxxps_with_bracket_dot(self):
        assert normalize("hxxps://example[.]com/path") == "https://example.com/path"

    def test_hxxp_with_ip_and_port(self):
        assert normalize("hxxp://192[.]168[.]1[.]1:8080/test") == "http://192.168.1.1:8080/test"

    def test_multiple_dot_patterns(self):
        assert normalize("hxxps://evil[.]example[dot]com") == "https://evil.example.com"

    def test_hxxp_bracket_url_with_bracket_dot(self):
        assert normalize("hxxps[://]evil[.]example.com") == "https://evil.example.com"

    def test_dot_variants_mixed(self):
        """Multiple different dot variants in same string"""
        assert normalize("192[.]168(.)1{.}1") == "192.168.1.1"


class TestEdgeCases:
    """Tests for edge cases and already-clean input."""

    def test_empty_string(self):
        assert normalize("") == ""

    def test_already_clean_ip(self):
        assert normalize("192.168.1.1") == "192.168.1.1"

    def test_already_clean_url(self):
        assert normalize("https://example.com") == "https://example.com"

    def test_already_clean_http_url(self):
        assert normalize("http://example.com") == "http://example.com"

    def test_already_clean_domain(self):
        assert normalize("example.com") == "example.com"

    def test_case_insensitive_scheme_lowercase(self):
        """Scheme is lowercased; rest preserved as-is"""
        assert normalize("HXXP://EXAMPLE[.]COM") == "http://EXAMPLE.COM"

    def test_plain_text_unchanged(self):
        """Text with no defanging patterns passes through unchanged"""
        result = normalize("hello world")
        assert result == "hello world"

    def test_bracket_colon_slash_variant(self):
        """http[:/]example.com variant"""
        assert normalize("http[:/]example.com") == "http://example.com"
