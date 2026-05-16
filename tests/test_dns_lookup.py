"""Tests for DNS record lookup adapter.

Tests A/MX/NS/TXT record resolution, NXDOMAIN/NoAnswer/timeout handling, protocol
conformance, and the critical design invariants:
  - DNS uses port 53, NOT HTTP -- no http_safety imports
  - NXDOMAIN and NoAnswer are no_data, NOT EnrichmentError
  - Partial failures (one record type fails) populate lookup_errors, other types still work
  - verdict is always "no_data" -- DNS records are informational, not threat signals
  - resolver.lifetime=5.0 (not the HTTP TIMEOUT tuple from http_safety)

All DNS calls are mocked using unittest.mock.patch -- no real DNS queries.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import dns.exception
import dns.resolver

from app.enrichment.models import EnrichmentResult
from app.pipeline.models import IOC, IOCType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DOMAIN_IOC = IOC(type=IOCType.DOMAIN, value="example.com", raw_match="example.com")
IPV4_IOC = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")


def _make_adapter(allowed_hosts: list[str] | None = None):
    """Construct a DnsAdapter.  allowed_hosts is accepted but unused (DNS is port 53)."""
    from app.enrichment.adapters.dns_lookup import DnsAdapter

    return DnsAdapter(allowed_hosts=allowed_hosts or [])


def _make_a_rdata(ip: str) -> MagicMock:
    """Mock A record rdata: has .to_text() -> ip string."""
    r = MagicMock()
    r.to_text.return_value = ip
    return r


def _make_mx_rdata(preference: int, exchange: str) -> MagicMock:
    """Mock MX record rdata: .preference (int) and .exchange.to_text() (str)."""
    r = MagicMock()
    r.preference = preference
    r.exchange.to_text.return_value = exchange
    return r


def _make_ns_rdata(nameserver: str) -> MagicMock:
    """Mock NS record rdata: .to_text() -> nameserver string."""
    r = MagicMock()
    r.to_text.return_value = nameserver
    return r


def _make_txt_rdata(*strings: bytes) -> MagicMock:
    """Mock TXT record rdata: .strings is a list of bytes."""
    r = MagicMock()
    r.strings = list(strings)
    return r


def _full_mock_resolver(
    *,
    a_records: list | None = None,
    mx_records: list | None = None,
    ns_records: list | None = None,
    txt_records: list | None = None,
) -> MagicMock:
    """Build a mock dns.resolver.Resolver that returns the given records for each rdtype.

    Pass None (default) to get empty lists. The mock's .resolve() method routes
    by rdtype string.
    """
    resolver = MagicMock()
    resolver.lifetime = None  # will be set by adapter

    a_records = a_records or []
    mx_records = mx_records or []
    ns_records = ns_records or []
    txt_records = txt_records or []

    def resolve_side_effect(domain, rdtype):
        mapping = {
            "A": a_records,
            "MX": mx_records,
            "NS": ns_records,
            "TXT": txt_records,
        }
        return mapping[rdtype]

    resolver.resolve.side_effect = resolve_side_effect
    return resolver


# ---------------------------------------------------------------------------
# Unsupported IOC type — DNS-specific behavior
# ---------------------------------------------------------------------------


class TestUnsupportedType:

    def test_ipv4_does_not_call_dns(self) -> None:
        """IPV4 IOC -> no DNS resolution attempted."""
        with patch("dns.resolver.Resolver") as mock_cls:
            _make_adapter().lookup(IPV4_IOC)
        mock_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Successful lookups
# ---------------------------------------------------------------------------


class TestSuccessfulLookup:

    def test_successful_lookup_returns_enrichment_result(self) -> None:
        """Successful DNS lookup returns EnrichmentResult with correct response shape."""
        mock_resolver = _full_mock_resolver(
            a_records=[_make_a_rdata("93.184.216.34")],
        )
        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult, got {type(result).__name__}: {result!r}"
        )
        assert result.provider == "DNS Records", "DNS adapter — provider must be 'DNS Records'"
        assert result.detection_count == 0, "informational adapter — detection_count must be 0"
        assert result.total_engines == 0, "informational adapter — total_engines must be 0"
        assert result.scan_date is None, "informational adapter — scan_date must be None"

    def test_successful_lookup_verdict_is_no_data(self) -> None:
        """DNS adapter always returns verdict='no_data' — records are informational."""
        mock_resolver = _full_mock_resolver(
            a_records=[_make_a_rdata("93.184.216.34")],
        )
        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data", (
            f"DNS records are informational, verdict must be 'no_data', got: {result.verdict!r}"
        )

    def test_result_helper_preserves_provider_envelope(self) -> None:
        """DNS result construction should keep the informational envelope centralized."""
        import inspect

        from app.enrichment.adapters.dns_lookup import _dns_result

        raw_stats = {
            "a": ["93.184.216.34"],
            "mx": [],
            "ns": [],
            "txt": [],
            "lookup_errors": [],
        }

        result = _dns_result(
            ioc=DOMAIN_IOC,
            provider="DNS Records",
            raw_stats=raw_stats,
        )

        assert result.ioc is DOMAIN_IOC
        assert result.provider == "DNS Records"
        assert result.verdict == "no_data"
        assert result.detection_count == 0
        assert result.total_engines == 0
        assert result.scan_date is None
        assert result.raw_stats is raw_stats
        assert "no_data_result(ioc, provider, raw_stats)" in inspect.getsource(_dns_result)

    def test_lookup_uses_record_table_extractors(self, monkeypatch) -> None:
        """Record-type dispatch should use table extractors instead of an rdtype branch chain."""
        import app.enrichment.adapters.dns_lookup as dns_module

        mock_resolver = MagicMock()
        answers = [object()]
        mock_resolver.resolve.return_value = answers
        extractor_calls: list[object] = []

        def custom_extractor(received_answers):
            extractor_calls.append(received_answers)
            return ["custom-value"]

        monkeypatch.setattr(
            dns_module,
            "_RECORD_TYPES",
            (("CUSTOM", "custom", custom_extractor),),
        )

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        mock_resolver.resolve.assert_called_once_with("example.com", "CUSTOM")
        assert extractor_calls == [answers]
        assert result.raw_stats["custom"] == ["custom-value"]


# ---------------------------------------------------------------------------
# A record extraction
# ---------------------------------------------------------------------------


class TestARecords:

    def test_a_records_returned_as_list_of_strings(self) -> None:
        """A records returned as list of IP strings in raw_stats['a']."""
        mock_resolver = _full_mock_resolver(
            a_records=[_make_a_rdata("93.184.216.34"), _make_a_rdata("93.184.216.35")],
        )
        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert "a" in result.raw_stats
        assert result.raw_stats["a"] == ["93.184.216.34", "93.184.216.35"]

    def test_single_a_record(self) -> None:
        """Single A record -> list with one IP string."""
        mock_resolver = _full_mock_resolver(
            a_records=[_make_a_rdata("1.2.3.4")],
        )
        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["a"] == ["1.2.3.4"]

    def test_a_uses_to_text_not_str(self) -> None:
        """A record extraction uses rdata.to_text(), not str(rdata)."""
        mock_rdata = _make_a_rdata("5.6.7.8")
        mock_resolver = _full_mock_resolver(a_records=[mock_rdata])
        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            _make_adapter().lookup(DOMAIN_IOC)

        mock_rdata.to_text.assert_called()


# ---------------------------------------------------------------------------
# MX record extraction
# ---------------------------------------------------------------------------


class TestMXRecords:

    def test_mx_records_returned_as_preference_exchange_format(self) -> None:
        """MX records returned as 'preference exchange' format strings."""
        mock_resolver = _full_mock_resolver(
            mx_records=[
                _make_mx_rdata(10, "mail.example.com."),
                _make_mx_rdata(20, "mail2.example.com."),
            ],
        )
        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert "mx" in result.raw_stats
        assert "10 mail.example.com." in result.raw_stats["mx"]
        assert "20 mail2.example.com." in result.raw_stats["mx"]

    def test_mx_format_is_pref_space_exchange(self) -> None:
        """MX string format is '{preference} {exchange.to_text()}'."""
        mock_resolver = _full_mock_resolver(
            mx_records=[_make_mx_rdata(10, "mail.example.com.")],
        )
        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        # Exact format: "10 mail.example.com."
        assert result.raw_stats["mx"] == ["10 mail.example.com."]

    def test_mx_uses_exchange_to_text(self) -> None:
        """MX extraction calls exchange.to_text() for the hostname."""
        mock_rdata = _make_mx_rdata(10, "mail.example.com.")
        mock_resolver = _full_mock_resolver(mx_records=[mock_rdata])
        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            _make_adapter().lookup(DOMAIN_IOC)

        mock_rdata.exchange.to_text.assert_called()


# ---------------------------------------------------------------------------
# NS record extraction
# ---------------------------------------------------------------------------


class TestNSRecords:

    def test_ns_records_returned_as_list(self) -> None:
        """NS records returned as list of nameserver strings in raw_stats['ns']."""
        mock_resolver = _full_mock_resolver(
            ns_records=[
                _make_ns_rdata("ns1.example.com."),
                _make_ns_rdata("ns2.example.com."),
            ],
        )
        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert "ns" in result.raw_stats
        assert "ns1.example.com." in result.raw_stats["ns"]
        assert "ns2.example.com." in result.raw_stats["ns"]

    def test_ns_uses_to_text(self) -> None:
        """NS extraction calls rdata.to_text()."""
        mock_rdata = _make_ns_rdata("ns1.example.com.")
        mock_resolver = _full_mock_resolver(ns_records=[mock_rdata])
        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            _make_adapter().lookup(DOMAIN_IOC)

        mock_rdata.to_text.assert_called()


# ---------------------------------------------------------------------------
# TXT record extraction
# ---------------------------------------------------------------------------


class TestTXTRecords:

    def test_txt_records_joined_and_decoded(self) -> None:
        """TXT records use b''.join(rdata.strings).decode('utf-8', errors='replace')."""
        mock_resolver = _full_mock_resolver(
            txt_records=[
                _make_txt_rdata(b"v=spf1 include:_spf.example.com ~all"),
            ],
        )
        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert "txt" in result.raw_stats
        assert result.raw_stats["txt"] == ["v=spf1 include:_spf.example.com ~all"]

    def test_txt_multi_string_concatenated(self) -> None:
        """TXT rdata with multiple string segments are joined (no spaces between segments)."""
        mock_resolver = _full_mock_resolver(
            txt_records=[
                _make_txt_rdata(b"part1", b"part2"),
            ],
        )
        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["txt"] == ["part1part2"]

    def test_txt_multiple_records(self) -> None:
        """Multiple TXT records -> multiple entries in raw_stats['txt']."""
        mock_resolver = _full_mock_resolver(
            txt_records=[
                _make_txt_rdata(b"v=spf1 ~all"),
                _make_txt_rdata(b"google-site-verification=abc123"),
            ],
        )
        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert len(result.raw_stats["txt"]) == 2
        assert "v=spf1 ~all" in result.raw_stats["txt"]
        assert "google-site-verification=abc123" in result.raw_stats["txt"]

    def test_txt_does_not_use_rdata_to_text(self) -> None:
        """TXT extraction must NOT call rdata.to_text() (that would add DNS quoting).

        Correct method is b''.join(rdata.strings).decode().
        """
        mock_rdata = _make_txt_rdata(b"v=spf1 ~all")
        mock_resolver = _full_mock_resolver(txt_records=[mock_rdata])
        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            _make_adapter().lookup(DOMAIN_IOC)

        # to_text should not be called on TXT rdata
        mock_rdata.to_text.assert_not_called()

    def test_short_chunk_txt_records_skip_join_iteration(self) -> None:
        """One- and two-chunk TXT records should decode directly instead of joining."""
        from app.enrichment.adapters.dns_lookup import _extract_txt_records

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
                raise AssertionError("short TXT chunks should not be joined through iteration")

        record = MagicMock()
        record.strings = ShortChunkStrings((b"v=spf1 ~all",))
        pair_record = MagicMock()
        pair_record.strings = ShortChunkStrings((b"google-site-", b"verification=abc"))

        assert _extract_txt_records([record]) == ["v=spf1 ~all"]
        assert _extract_txt_records([pair_record]) == ["google-site-verification=abc"]


# ---------------------------------------------------------------------------
# Extractor implementation shape
# ---------------------------------------------------------------------------


class TestRecordExtractorImplementation:

    def test_record_extractors_do_not_allocate_list_comprehension_frames(self) -> None:
        """Record extractors should use direct loops, not per-call list comprehensions."""
        from app.enrichment.adapters.dns_lookup import (
            _extract_mx_records,
            _extract_text_records,
            _extract_txt_records,
        )

        for extractor in (_extract_text_records, _extract_mx_records, _extract_txt_records):
            nested_code_names = {
                const.co_name
                for const in extractor.__code__.co_consts
                if hasattr(const, "co_name")
            }
            assert "<listcomp>" not in nested_code_names

    def test_record_extractors_skip_iteration_for_empty_single_pair_or_three_answers(self) -> None:
        from app.enrichment.adapters.dns_lookup import (
            _extract_mx_records,
            _extract_text_records,
            _extract_txt_records,
        )

        class ShortAnswers:
            def __init__(self, *records) -> None:
                self.records = records

            def __len__(self) -> int:
                return len(self.records)

            def __getitem__(self, index: int):
                if index >= len(self.records):
                    raise IndexError(index)
                return self.records[index]

            def __iter__(self):
                raise AssertionError("short-answer extraction should not iterate")

        class EmptyAnswers:
            def __len__(self) -> int:
                return 0

            def __getitem__(self, index: int):
                raise IndexError(index)

            def __iter__(self):
                raise AssertionError("empty-answer extraction should not iterate")

        text_record = _make_a_rdata("93.184.216.34")
        second_text_record = _make_a_rdata("93.184.216.35")
        third_text_record = _make_a_rdata("93.184.216.36")
        mx_record = _make_mx_rdata(10, "mail.example.com.")
        second_mx_record = _make_mx_rdata(20, "backup.example.com.")
        third_mx_record = _make_mx_rdata(30, "fallback.example.com.")
        txt_record = _make_txt_rdata(b"v=spf1 ~all")
        second_txt_record = _make_txt_rdata(b"google-site-verification=abc")
        third_txt_record = _make_txt_rdata(b"apple-domain-verification=xyz")

        assert _extract_text_records(EmptyAnswers()) == []
        assert _extract_mx_records(EmptyAnswers()) == []
        assert _extract_txt_records(EmptyAnswers()) == []
        assert _extract_text_records(ShortAnswers(text_record)) == ["93.184.216.34"]
        assert _extract_mx_records(ShortAnswers(mx_record)) == ["10 mail.example.com."]
        assert _extract_txt_records(ShortAnswers(txt_record)) == ["v=spf1 ~all"]
        assert _extract_text_records(ShortAnswers(text_record, second_text_record)) == [
            "93.184.216.34",
            "93.184.216.35",
        ]
        assert _extract_mx_records(ShortAnswers(mx_record, second_mx_record)) == [
            "10 mail.example.com.",
            "20 backup.example.com.",
        ]
        assert _extract_txt_records(ShortAnswers(txt_record, second_txt_record)) == [
            "v=spf1 ~all",
            "google-site-verification=abc",
        ]
        assert _extract_text_records(ShortAnswers(text_record, second_text_record, third_text_record)) == [
            "93.184.216.34",
            "93.184.216.35",
            "93.184.216.36",
        ]
        assert _extract_mx_records(ShortAnswers(mx_record, second_mx_record, third_mx_record)) == [
            "10 mail.example.com.",
            "20 backup.example.com.",
            "30 fallback.example.com.",
        ]
        assert _extract_txt_records(ShortAnswers(txt_record, second_txt_record, third_txt_record)) == [
            "v=spf1 ~all",
            "google-site-verification=abc",
            "apple-domain-verification=xyz",
        ]
        assert "len" in _extract_text_records.__code__.co_names
        assert "len" in _extract_mx_records.__code__.co_names
        assert "len" in _extract_txt_records.__code__.co_names


# ---------------------------------------------------------------------------
# raw_stats structure
# ---------------------------------------------------------------------------


class TestRawStatsStructure:

    def test_raw_stats_has_all_keys(self) -> None:
        """raw_stats must contain 'a', 'mx', 'ns', 'txt', 'lookup_errors'."""
        mock_resolver = _full_mock_resolver()
        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        for key in ("a", "mx", "ns", "txt", "lookup_errors"):
            assert key in result.raw_stats, f"raw_stats missing key: {key!r}"

    def test_raw_stats_all_empty_when_no_records(self) -> None:
        """raw_stats lists are empty when all record types return no results."""
        mock_resolver = _full_mock_resolver()  # all empty
        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["a"] == []
        assert result.raw_stats["mx"] == []
        assert result.raw_stats["ns"] == []
        assert result.raw_stats["txt"] == []
        assert result.raw_stats["lookup_errors"] == []


# ---------------------------------------------------------------------------
# NXDOMAIN handling
# ---------------------------------------------------------------------------


class TestNXDOMAIN:

    def test_nxdomain_returns_no_data_result(self) -> None:
        """NXDOMAIN must return EnrichmentResult(verdict='no_data') with empty record lists."""
        resolver = MagicMock()
        resolver.resolve.side_effect = dns.resolver.NXDOMAIN()
        with patch("dns.resolver.Resolver", return_value=resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult), (
            f"NXDOMAIN must return EnrichmentResult not EnrichmentError, got {type(result).__name__}"
        )
        assert result.verdict == "no_data"
        assert result.raw_stats["a"] == []
        assert result.raw_stats["mx"] == []
        assert result.raw_stats["ns"] == []
        assert result.raw_stats["txt"] == []
        assert result.raw_stats["lookup_errors"] == [], (
            "NXDOMAIN is a normal outcome, not an error to track in lookup_errors"
        )


# ---------------------------------------------------------------------------
# NoAnswer handling
# ---------------------------------------------------------------------------


class TestNoAnswer:

    def test_no_answer_for_mx_returns_empty_mx_list(self) -> None:
        """NoAnswer for MX record type -> raw_stats['mx'] is empty list."""
        def resolve_side_effect(domain, rdtype):
            if rdtype == "MX":
                raise dns.resolver.NoAnswer()
            return []

        resolver = MagicMock()
        resolver.resolve.side_effect = resolve_side_effect
        with patch("dns.resolver.Resolver", return_value=resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["mx"] == []

    def test_no_answer_for_txt_returns_empty_txt_list(self) -> None:
        """NoAnswer for TXT record type -> raw_stats['txt'] is empty list."""
        def resolve_side_effect(domain, rdtype):
            if rdtype == "TXT":
                raise dns.resolver.NoAnswer()
            return []

        resolver = MagicMock()
        resolver.resolve.side_effect = resolve_side_effect
        with patch("dns.resolver.Resolver", return_value=resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["txt"] == []

    def test_no_answer_not_in_lookup_errors(self) -> None:
        """NoAnswer is expected — must NOT be added to lookup_errors."""
        resolver = MagicMock()
        resolver.resolve.side_effect = dns.resolver.NoAnswer()
        with patch("dns.resolver.Resolver", return_value=resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["lookup_errors"] == [], (
            "NoAnswer is a normal outcome, not an error"
        )


# ---------------------------------------------------------------------------
# Partial failure: other record types still populated
# ---------------------------------------------------------------------------


class TestPartialFailure:

    def test_mx_timeout_does_not_prevent_a_records(self) -> None:
        """MX timeout -> A records still populated (each type resolved independently)."""
        def resolve_side_effect(domain, rdtype):
            if rdtype == "MX":
                raise dns.exception.Timeout()
            if rdtype == "A":
                return [_make_a_rdata("1.2.3.4")]
            return []

        resolver = MagicMock()
        resolver.resolve.side_effect = resolve_side_effect
        with patch("dns.resolver.Resolver", return_value=resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["a"] == ["1.2.3.4"]
        assert result.raw_stats["mx"] == []

    def test_partial_failure_populates_lookup_errors(self) -> None:
        """MX timeout -> 'MX: timeout' (or similar) in lookup_errors list."""
        def resolve_side_effect(domain, rdtype):
            if rdtype == "MX":
                raise dns.exception.Timeout()
            return []

        resolver = MagicMock()
        resolver.resolve.side_effect = resolve_side_effect
        with patch("dns.resolver.Resolver", return_value=resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        errors = result.raw_stats["lookup_errors"]
        assert len(errors) == 1
        assert "MX" in errors[0] or "mx" in errors[0].lower()
        assert "timeout" in errors[0].lower()

    def test_all_four_types_resolved_independently(self) -> None:
        """All four rdtypes are resolved via separate resolver.resolve() calls."""
        mock_resolver = _full_mock_resolver(
            a_records=[_make_a_rdata("1.2.3.4")],
            mx_records=[_make_mx_rdata(10, "mail.example.com.")],
            ns_records=[_make_ns_rdata("ns1.example.com.")],
            txt_records=[_make_txt_rdata(b"v=spf1 ~all")],
        )
        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        # All four rdtypes must be queried
        called_rdtypes = {c.args[1] for c in mock_resolver.resolve.call_args_list}
        assert called_rdtypes == {"A", "MX", "NS", "TXT"}, (
            f"Expected A/MX/NS/TXT calls, got: {called_rdtypes}"
        )


# ---------------------------------------------------------------------------
# Timeout handling
# ---------------------------------------------------------------------------


class TestTimeout:

    def test_timeout_populates_lookup_errors(self) -> None:
        """Timeout for a record type -> '{rdtype}: timeout' in lookup_errors."""
        resolver = MagicMock()
        resolver.resolve.side_effect = dns.exception.Timeout()
        with patch("dns.resolver.Resolver", return_value=resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        errors = result.raw_stats["lookup_errors"]
        assert len(errors) == 4  # one per rdtype
        assert all("timeout" in e.lower() for e in errors)

    def test_timeout_returns_enrichment_result(self) -> None:
        """Timeout -> EnrichmentResult (partial failure), not EnrichmentError."""
        resolver = MagicMock()
        resolver.resolve.side_effect = dns.exception.Timeout()
        with patch("dns.resolver.Resolver", return_value=resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)


# ---------------------------------------------------------------------------
# NoNameservers handling
# ---------------------------------------------------------------------------


class TestNoNameservers:

    def test_no_nameservers_populates_lookup_errors(self) -> None:
        """NoNameservers -> '{rdtype}: no nameservers' (or similar) in lookup_errors."""
        resolver = MagicMock()
        resolver.resolve.side_effect = dns.resolver.NoNameservers()
        with patch("dns.resolver.Resolver", return_value=resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)
        errors = result.raw_stats["lookup_errors"]
        assert len(errors) == 4
        assert all("nameserver" in e.lower() or "no nameservers" in e.lower() for e in errors)

    def test_no_nameservers_returns_enrichment_result(self) -> None:
        """NoNameservers -> EnrichmentResult with lookup_errors, not EnrichmentError."""
        resolver = MagicMock()
        resolver.resolve.side_effect = dns.resolver.NoNameservers()
        with patch("dns.resolver.Resolver", return_value=resolver):
            result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentResult)


# ---------------------------------------------------------------------------
# Resolver lifetime configuration
# ---------------------------------------------------------------------------


class TestResolverLifetime:

    def test_resolver_lifetime_set_to_5_seconds(self) -> None:
        """resolver.lifetime must be set to 5.0 (not the HTTP TIMEOUT tuple)."""
        mock_resolver = _full_mock_resolver()
        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            _make_adapter().lookup(DOMAIN_IOC)

        # Confirm lifetime was set to 5.0
        assert mock_resolver.lifetime == 5.0, (
            f"resolver.lifetime must be 5.0, got: {mock_resolver.lifetime!r}"
        )

    def test_resolver_created_with_configure_true(self) -> None:
        """Resolver must be created with configure=True to use system resolv.conf."""
        mock_resolver = _full_mock_resolver()
        with patch("dns.resolver.Resolver", return_value=mock_resolver) as mock_cls:
            _make_adapter().lookup(DOMAIN_IOC)

        # configure=True is the default that reads resolv.conf
        call_kwargs = mock_cls.call_args
        # Either called with configure=True or no args (default is True)
        if call_kwargs is not None and call_kwargs.kwargs:
            configure_val = call_kwargs.kwargs.get("configure", True)
            assert configure_val is True, (
                f"Resolver(configure=...) must be True, got: {configure_val!r}"
            )


# ---------------------------------------------------------------------------
# No HTTP safety imports
# ---------------------------------------------------------------------------


class TestNoHTTPSafety:

    def test_dns_adapter_does_not_import_http_safety(self) -> None:
        """DnsAdapter must NOT import http_safety.py (DNS is port 53, not HTTP).

        This test inspects the adapter module's globals to confirm no http_safety
        symbols are present (validate_endpoint, TIMEOUT, read_limited).
        """
        import app.enrichment.adapters.dns_lookup as dns_module

        http_safety_symbols = {"validate_endpoint", "read_limited", "TIMEOUT", "http_safety"}
        module_attrs = set(dir(dns_module))
        imported_safety = http_safety_symbols.intersection(module_attrs)
        assert not imported_safety, (
            f"DnsAdapter must NOT import http_safety symbols (DNS is port 53): {imported_safety}"
        )

    def test_dns_adapter_does_not_use_requests(self) -> None:
        """DnsAdapter must NOT import requests (DNS is not HTTP).

        DNS resolution uses dns.resolver directly — no HTTP calls.
        """
        import app.enrichment.adapters.dns_lookup as dns_module

        # Check module globals — 'requests' should not be imported
        assert "requests" not in dir(dns_module), (
            "DnsAdapter must not import 'requests' — DNS uses port 53 directly"
        )
