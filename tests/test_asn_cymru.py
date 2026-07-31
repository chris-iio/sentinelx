"""Tests for Cymru ASN lookup adapter.

Tests IPv4/IPv6 query construction, TXT response parsing, NXDOMAIN/NoAnswer/timeout
handling, protocol conformance, and the critical design invariants:
  - DNS uses port 53, NOT HTTP -- no http_safety imports, no requests import
  - NXDOMAIN is no_data (private/RFC-1918 IPs), NOT EnrichmentError
  - NoAnswer/NoNameservers/Timeout are no_data, NOT EnrichmentError
  - Unexpected exceptions return EnrichmentError
  - verdict is always "no_data" -- ASN context is informational, not a threat signal
  - resolver.lifetime=5.0 (not the HTTP TIMEOUT tuple from http_safety)
  - Resolver created with configure=True

All DNS calls are mocked using unittest.mock.patch -- no real DNS queries.
"""
from __future__ import annotations

import dis
import inspect
from unittest.mock import MagicMock, patch

import dns.exception
import dns.resolver
import pytest

from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

IPV4_IOC = IOC(type=IOCType.IPV4, value="216.90.108.31", raw_match="216.90.108.31")
IPV6_IOC = IOC(type=IOCType.IPV6, value="2001:4860:4860::8888", raw_match="2001:4860:4860::8888")
DOMAIN_IOC = IOC(type=IOCType.DOMAIN, value="example.com", raw_match="example.com")
PRIVATE_IPV4_IOC = IOC(type=IOCType.IPV4, value="192.168.1.1", raw_match="192.168.1.1")
INVALID_IP_IOC = IOC(type=IOCType.IPV4, value="not-an-ip", raw_match="not-an-ip")

# Sample TXT response: "ASN | prefix | country | rir | allocated"
SAMPLE_TXT = "23028 | 216.90.108.0/24 | US | arin | 1998-09-25"


def _make_adapter():
    """Construct a CymruASNAdapter. DNS uses port 53 directly, not HTTP allowlists."""
    from app.enrichment.adapters.asn_cymru import CymruASNAdapter

    return CymruASNAdapter()


def _make_txt_answer(txt_string: str) -> MagicMock:
    """Return a mock DNS answer list whose first element has .strings containing TXT bytes.

    The adapter decodes the first answer record's TXT chunks as UTF-8.
    """
    answer_record = MagicMock()
    answer_record.strings = [txt_string.encode("utf-8")]
    mock_answers = [answer_record]
    return mock_answers


# ---------------------------------------------------------------------------
# Unsupported IOC type — DNS-specific behavior
# ---------------------------------------------------------------------------


class TestUnsupportedType:

    def test_domain_ioc_does_not_call_dns(self) -> None:
        """DOMAIN IOC -> no DNS resolution attempted."""
        with patch("dns.resolver.Resolver") as mock_cls:
            _make_adapter().lookup(DOMAIN_IOC)
        mock_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Query construction tests
# ---------------------------------------------------------------------------


class TestQueryConstruction:

    def test_ipv4_query_constructs_reversed_origin_asn_cymru_com(self) -> None:
        """IPv4 lookup constructs correct query '31.108.90.216.origin.asn.cymru.com' for 216.90.108.31."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            _make_adapter().lookup(IPV4_IOC)

        call_args = mock_resolver.resolve.call_args
        query_name = call_args.args[0] if call_args.args else call_args[0][0]
        assert query_name == "31.108.90.216.origin.asn.cymru.com", (
            f"Expected '31.108.90.216.origin.asn.cymru.com', got: {query_name!r}"
        )

    def test_ipv4_query_uses_txt_rdtype(self) -> None:
        """IPv4 lookup resolves TXT record type."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            _make_adapter().lookup(IPV4_IOC)

        call_args = mock_resolver.resolve.call_args
        rdtype = call_args.args[1] if len(call_args.args) > 1 else call_args[0][1]
        assert rdtype == "TXT"

    def test_ipv6_query_uses_origin6_asn_cymru_com_zone(self) -> None:
        """IPv6 lookup constructs query with origin6.asn.cymru.com zone."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            _make_adapter().lookup(IPV6_IOC)

        call_args = mock_resolver.resolve.call_args
        query_name = call_args.args[0] if call_args.args else call_args[0][0]
        assert "origin6.asn.cymru.com" in query_name, (
            f"IPv6 query must use origin6.asn.cymru.com zone, got: {query_name!r}"
        )

    def test_ipv6_query_does_not_use_ipv4_zone(self) -> None:
        """IPv6 lookup must NOT use origin.asn.cymru.com (IPv4 zone)."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            _make_adapter().lookup(IPV6_IOC)

        call_args = mock_resolver.resolve.call_args
        query_name = call_args.args[0] if call_args.args else call_args[0][0]
        # Should not end with .origin.asn.cymru.com (IPv4 suffix)
        assert not query_name.endswith(".origin.asn.cymru.com"), (
            f"IPv6 query must use origin6 zone, not origin: {query_name!r}"
        )

    def test_lookup_delegates_dns_query_name_helper(self) -> None:
        """lookup should not own IPv4/IPv6 Cymru zone replacement or resolver setup."""
        from app.enrichment.adapters.asn_cymru import CymruASNAdapter

        source = inspect.getsource(CymruASNAdapter.lookup)

        assert "_cymru_query_name(ip)" in source
        assert "_configured_resolver()" in source
        assert ".replace(" not in source
        assert "dns.resolver.Resolver" not in source
        assert ".lifetime" not in source
        assert "origin.asn.cymru.com" not in source
        assert "origin6.asn.cymru.com" not in source

    def test_configured_resolver_helper_preserves_lifetime_policy(self) -> None:
        """Cymru resolver construction and timeout policy should live in one helper."""
        from app.enrichment.adapters import asn_cymru

        resolver = MagicMock()
        with patch("dns.resolver.Resolver", return_value=resolver) as resolver_factory:
            assert asn_cymru._configured_resolver() is resolver

        resolver_factory.assert_called_once_with(configure=True)
        assert resolver.lifetime == asn_cymru._RESOLVER_LIFETIME

    def test_query_name_helper_preserves_ipv4_and_ipv6_zones(self) -> None:
        """Cymru DNS query-name construction should live in one helper."""
        import ipaddress

        from app.enrichment.adapters.asn_cymru import _cymru_query_name

        assert _cymru_query_name(ipaddress.ip_address("216.90.108.31")) == (
            "31.108.90.216.origin.asn.cymru.com"
        )
        assert _cymru_query_name(ipaddress.ip_address("2001:4860:4860::8888")).endswith(
            ".origin6.asn.cymru.com"
        )


# ---------------------------------------------------------------------------
# Successful lookup tests
# ---------------------------------------------------------------------------


class TestSuccessfulLookup:

    def test_successful_lookup_returns_enrichment_result(self) -> None:
        """Successful TXT lookup returns EnrichmentResult with correct response shape."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult, got {type(result).__name__}: {result!r}"
        )
        assert result.provider == "ASN Intel", "ASN adapter — provider must be 'ASN Intel'"
        assert result.detection_count == 0, "informational adapter — detection_count must be 0"
        assert result.total_engines == 0, "informational adapter — total_engines must be 0"
        assert result.scan_date is None, "informational adapter — scan_date must be None"

    def test_successful_lookup_verdict_is_no_data(self) -> None:
        """ASN adapter always returns verdict='no_data' — ASN context is informational."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data", (
            f"ASN context is informational, verdict must be 'no_data', got: {result.verdict!r}"
        )

    def test_no_data_result_helper_preserves_informational_shape(self) -> None:
        """Cymru empty misses and parsed context should share one no_data result shape."""
        import inspect

        from app.enrichment.adapters.asn_cymru import _no_data_result

        raw_stats = {"asn": "23028"}

        result = _no_data_result(IPV4_IOC, "ASN Intel", raw_stats)

        assert result.ioc is IPV4_IOC
        assert result.provider == "ASN Intel"
        assert result.verdict == "no_data"
        assert result.detection_count == 0
        assert result.total_engines == 0
        assert result.scan_date is None
        assert result.raw_stats is raw_stats
        assert "no_data_result(ioc, provider_name, raw_stats)" in inspect.getsource(_no_data_result)

    @pytest.mark.parametrize("field,expected", [
        ("asn", "23028"),
        ("prefix", "216.90.108.0/24"),
        ("rir", "arin"),
        ("allocated", "1998-09-25"),
    ])
    def test_raw_stats_field_values(self, field: str, expected: str) -> None:
        """raw_stats fields must match the parsed TXT response values."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats[field] == expected, (
            f"Expected {field}={expected!r}, got: {result.raw_stats.get(field)!r}"
        )

    def test_txt_answer_uses_first_record_without_materializing_all_answers(self) -> None:
        """TXT extraction should read only the first answer record."""
        answer_record = MagicMock()
        answer_record.strings = [SAMPLE_TXT.encode("utf-8")]

        def answers():
            yield answer_record
            raise AssertionError("ASN lookup should not materialize every TXT answer")

        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = answers()

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["asn"] == "23028"

    def test_short_chunk_txt_answers_skip_join_iteration(self) -> None:
        """Common one-, two-, three-, and four-chunk Cymru TXT answers should decode without joining."""
        from app.enrichment.adapters.asn_cymru import _decode_txt_strings
        from app.enrichment.adapters.dns_txt import decode_txt_chunks

        class ShortChunkStrings:
            def __init__(self, chunks: tuple[bytes, ...]) -> None:
                self.chunks = chunks

            def __len__(self) -> int:
                return len(self.chunks)

            def __getitem__(self, index: int) -> bytes:
                if index >= len(self.chunks):
                    raise IndexError(index)
                return self.chunks[index]

            def __iter__(self):
                raise AssertionError("short Cymru TXT chunks should not be joined through iteration")

        assert _decode_txt_strings(ShortChunkStrings(())) == ""
        assert _decode_txt_strings(ShortChunkStrings((SAMPLE_TXT.encode("utf-8"),))) == SAMPLE_TXT
        assert _decode_txt_strings(ShortChunkStrings((b"23028 | ", b"216.90.108.0/24"))) == (
            "23028 | 216.90.108.0/24"
        )
        assert _decode_txt_strings(ShortChunkStrings((b"23028 | ", b"216.90.", b"108.0/24"))) == (
            "23028 | 216.90.108.0/24"
        )
        assert _decode_txt_strings(ShortChunkStrings((b"23028", b" | ", b"216.90.", b"108.0/24"))) == (
            "23028 | 216.90.108.0/24"
        )
        assert "decode_txt_chunks" in _decode_txt_strings.__code__.co_names
        assert "string_count == 4" in inspect.getsource(decode_txt_chunks)

    def test_multi_chunk_txt_answer_still_concatenates_segments(self) -> None:
        """Segmented Cymru TXT answers keep DNS TXT concatenation semantics."""
        from app.enrichment.adapters.asn_cymru import _decode_txt_strings

        assert _decode_txt_strings([b"23028 | ", b"216.90.108.0/24"]) == (
            "23028 | 216.90.108.0/24"
        )

    def test_txt_parse_does_not_allocate_split_parts(self) -> None:
        """TXT parsing should extract fields directly instead of split-list allocation."""
        from app.enrichment.adapters.asn_cymru import _parse_response

        class NoSplitText(str):
            def split(self, *_args, **_kwargs):
                raise AssertionError("ASN TXT parsing should not split into a parts list")

        result = _parse_response(IPV4_IOC, NoSplitText(SAMPLE_TXT), "ASN Intel")

        assert result.raw_stats["asn"] == "23028"
        assert result.raw_stats["prefix"] == "216.90.108.0/24"
        assert result.raw_stats["rir"] == "arin"
        assert result.raw_stats["allocated"] == "1998-09-25"

    def test_parse_response_delegates_raw_stats_helper(self) -> None:
        """Cymru parser should not own ASN raw_stats mechanics."""
        from app.enrichment.adapters.asn_cymru import _parse_response

        source = inspect.getsource(_parse_response)

        assert "_asn_raw_stats(txt)" in source
        assert "_parse_txt_fields(txt)" not in source
        assert '"asn"' not in source
        assert '"allocated"' not in source

    def test_raw_stats_helper_preserves_key_order_and_values(self) -> None:
        """Cymru raw_stats helper should preserve public metadata shape."""
        from app.enrichment.adapters.asn_cymru import _asn_raw_stats

        raw_stats = _asn_raw_stats(SAMPLE_TXT)

        assert list(raw_stats) == ["asn", "prefix", "rir", "allocated"]
        assert raw_stats == {
            "asn": "23028",
            "prefix": "216.90.108.0/24",
            "rir": "arin",
            "allocated": "1998-09-25",
        }

    def test_txt_field_parser_does_not_build_intermediate_field_list(self) -> None:
        """Field extraction should return direct tuple values without list accumulation."""
        from app.enrichment.adapters.asn_cymru import _parse_txt_fields

        opnames = {instruction.opname for instruction in dis.get_instructions(_parse_txt_fields)}

        assert "BUILD_LIST" not in opnames
        assert _parse_txt_fields(SAMPLE_TXT) == (
            "23028",
            "216.90.108.0/24",
            "US",
            "arin",
            "1998-09-25",
        )
        assert _parse_txt_fields("23028 | 216.90.108.0/24") == (
            "23028",
            "216.90.108.0/24",
            "",
            "",
            "",
        )

    def test_txt_field_parser_trims_ranges_before_slicing(self) -> None:
        """TXT field extraction should avoid slice-then-strip field allocations."""
        from app.enrichment.adapters.asn_cymru import (
            _next_txt_field,
            _parse_txt_fields,
            _strip_txt_field,
        )

        assert "strip" not in _next_txt_field.__code__.co_names
        assert "strip" not in _parse_txt_fields.__code__.co_names
        assert _strip_txt_field("  arin  ", 0, 8) == "arin"
        assert _parse_txt_fields(" 23028 | 216.90.108.0/24 | US | arin | 1998-09-25 ") == (
            "23028",
            "216.90.108.0/24",
            "US",
            "arin",
            "1998-09-25",
        )


# ---------------------------------------------------------------------------
# NXDOMAIN handling
# ---------------------------------------------------------------------------


class TestNXDOMAIN:

    def test_nxdomain_returns_no_data_result(self) -> None:
        """NXDOMAIN must return EnrichmentResult(verdict='no_data') with correct response shape.

        Private/RFC-1918 IPs return NXDOMAIN — this is expected 'no BGP entry', not an error.
        """
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = dns.resolver.NXDOMAIN()

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(PRIVATE_IPV4_IOC)

        assert isinstance(result, EnrichmentResult), (
            f"NXDOMAIN must return EnrichmentResult not EnrichmentError, got {type(result).__name__}"
        )
        assert result.verdict == "no_data"
        assert result.detection_count == 0, "NXDOMAIN — detection_count must be 0"
        assert result.scan_date is None, "NXDOMAIN — scan_date must be None"

    def test_nxdomain_returns_empty_raw_stats(self) -> None:
        """NXDOMAIN -> raw_stats={} (no BGP entry for private IP)."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = dns.resolver.NXDOMAIN()

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(PRIVATE_IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats == {}, (
            f"NXDOMAIN must return empty raw_stats, got: {result.raw_stats!r}"
        )


# ---------------------------------------------------------------------------
# DNS error handling (NoAnswer, NoNameservers, Timeout)
# ---------------------------------------------------------------------------


class TestDNSErrors:

    @pytest.mark.parametrize("exception", [
        dns.resolver.NoAnswer(),
        dns.resolver.NoNameservers(),
        dns.exception.Timeout(),
    ], ids=["NoAnswer", "NoNameservers", "Timeout"])
    def test_dns_error_returns_no_data_with_empty_raw_stats(self, exception) -> None:
        """DNS errors (NoAnswer/NoNameservers/Timeout) -> EnrichmentResult(verdict='no_data', raw_stats={})."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = exception

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult), (
            f"{type(exception).__name__} must return EnrichmentResult, got {type(result).__name__}"
        )
        assert result.verdict == "no_data"
        assert result.raw_stats == {}


# ---------------------------------------------------------------------------
# Unexpected exception handling
# ---------------------------------------------------------------------------


class TestUnexpectedError:

    def test_generic_exception_returns_enrichment_error(self) -> None:
        """Generic/unexpected Exception must return EnrichmentError with correct provider."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = RuntimeError("unexpected failure")

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentError), (
            f"Unexpected exception must return EnrichmentError, got {type(result).__name__}"
        )
        assert result.provider == "ASN Intel"



# ---------------------------------------------------------------------------
# Invalid IP string handling
# ---------------------------------------------------------------------------


class TestInvalidIP:

    def test_invalid_ip_returns_enrichment_error(self) -> None:
        """Invalid IP string -> EnrichmentError with correct provider, no DNS attempted."""
        with patch("dns.resolver.Resolver") as mock_cls:
            result = _make_adapter().lookup(INVALID_IP_IOC)

        assert isinstance(result, EnrichmentError), (
            f"Invalid IP must return EnrichmentError, got {type(result).__name__}"
        )
        assert result.provider == "ASN Intel"
        mock_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Resolver configuration tests
# ---------------------------------------------------------------------------


class TestResolverConfig:

    def test_resolver_lifetime_set_to_5_seconds(self) -> None:
        """resolver.lifetime must be set to 5.0 (not the HTTP TIMEOUT tuple)."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            _make_adapter().lookup(IPV4_IOC)

        assert mock_resolver.lifetime == 5.0, (
            f"resolver.lifetime must be 5.0, got: {mock_resolver.lifetime!r}"
        )

    def test_resolver_created_with_configure_true(self) -> None:
        """Resolver must be created with configure=True to use system resolv.conf."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        with patch("dns.resolver.Resolver", return_value=mock_resolver) as mock_cls:
            _make_adapter().lookup(IPV4_IOC)

        call_kwargs = mock_cls.call_args
        if call_kwargs is not None and call_kwargs.kwargs:
            configure_val = call_kwargs.kwargs.get("configure", True)
            assert configure_val is True, (
                f"Resolver(configure=...) must be True, got: {configure_val!r}"
            )

    def test_fresh_resolver_per_lookup(self) -> None:
        """A fresh Resolver instance must be created for each lookup() call (thread safety)."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        adapter = _make_adapter()
        with patch("dns.resolver.Resolver", return_value=mock_resolver) as mock_cls:
            adapter.lookup(IPV4_IOC)
            adapter.lookup(IPV4_IOC)

        assert mock_cls.call_count == 2, (
            f"A fresh Resolver must be created per lookup, got {mock_cls.call_count} calls"
        )


# ---------------------------------------------------------------------------
# No HTTP safety imports
# ---------------------------------------------------------------------------


class TestNoHTTPSafety:

    def test_asn_adapter_does_not_import_http_safety(self) -> None:
        """CymruASNAdapter must NOT import http_safety.py (DNS is port 53, not HTTP).

        This test inspects the adapter module's globals to confirm no http_safety
        symbols are present (validate_endpoint, TIMEOUT, read_limited).
        """
        import app.enrichment.adapters.asn_cymru as asn_module

        http_safety_symbols = {"validate_endpoint", "read_limited", "TIMEOUT", "http_safety"}
        module_attrs = set(dir(asn_module))
        imported_safety = http_safety_symbols.intersection(module_attrs)
        assert not imported_safety, (
            f"CymruASNAdapter must NOT import http_safety symbols (DNS is port 53): {imported_safety}"
        )

    def test_asn_adapter_does_not_use_requests(self) -> None:
        """CymruASNAdapter must NOT import requests (DNS is not HTTP).

        DNS resolution uses dns.resolver directly — no HTTP calls.
        """
        import app.enrichment.adapters.asn_cymru as asn_module

        assert "requests" not in dir(asn_module), (
            "CymruASNAdapter must not import 'requests' — DNS uses port 53 directly"
        )
