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

from unittest.mock import MagicMock, patch

import dns.exception
import dns.resolver

from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.provider import Provider
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


def _make_adapter(allowed_hosts: list[str] | None = None):
    """Construct a CymruASNAdapter. allowed_hosts is accepted but unused (DNS is port 53)."""
    from app.enrichment.adapters.asn_cymru import CymruASNAdapter

    return CymruASNAdapter(allowed_hosts=allowed_hosts or [])


def _make_txt_answer(txt_string: str) -> MagicMock:
    """Return a mock DNS answer list whose first element has .strings containing TXT bytes.

    The adapter calls: b"".join(list(answers)[0].strings).decode("utf-8", errors="replace")
    """
    answer_record = MagicMock()
    answer_record.strings = [txt_string.encode("utf-8")]
    mock_answers = [answer_record]
    return mock_answers


# ---------------------------------------------------------------------------
# Class metadata tests
# ---------------------------------------------------------------------------


class TestClassMetadata:

    def test_name_is_asn_intel(self) -> None:
        """CymruASNAdapter.name must be 'ASN Intel'."""
        from app.enrichment.adapters.asn_cymru import CymruASNAdapter
        assert CymruASNAdapter.name == "ASN Intel"

    def test_supported_types_is_frozenset(self) -> None:
        """supported_types must be a frozenset."""
        from app.enrichment.adapters.asn_cymru import CymruASNAdapter
        assert isinstance(CymruASNAdapter.supported_types, frozenset)

    def test_supported_types_contains_ipv4(self) -> None:
        """IOCType.IPV4 must be in CymruASNAdapter.supported_types."""
        from app.enrichment.adapters.asn_cymru import CymruASNAdapter
        assert IOCType.IPV4 in CymruASNAdapter.supported_types

    def test_supported_types_contains_ipv6(self) -> None:
        """IOCType.IPV6 must be in CymruASNAdapter.supported_types."""
        from app.enrichment.adapters.asn_cymru import CymruASNAdapter
        assert IOCType.IPV6 in CymruASNAdapter.supported_types

    def test_supported_types_is_ipv4_and_ipv6_only(self) -> None:
        """supported_types must be exactly {IPV4, IPV6}."""
        from app.enrichment.adapters.asn_cymru import CymruASNAdapter
        assert CymruASNAdapter.supported_types == frozenset({IOCType.IPV4, IOCType.IPV6})

    def test_requires_api_key_false(self) -> None:
        """CymruASNAdapter.requires_api_key must be False."""
        from app.enrichment.adapters.asn_cymru import CymruASNAdapter
        assert CymruASNAdapter.requires_api_key is False

    def test_is_configured_returns_true(self) -> None:
        """is_configured() must always return True — no API key needed."""
        adapter = _make_adapter()
        assert adapter.is_configured() is True

    def test_is_configured_returns_true_with_empty_hosts(self) -> None:
        """is_configured() returns True even when allowed_hosts is empty."""
        adapter = _make_adapter(allowed_hosts=[])
        assert adapter.is_configured() is True

    def test_is_configured_returns_true_with_populated_hosts(self) -> None:
        """is_configured() returns True regardless of allowed_hosts content."""
        adapter = _make_adapter(allowed_hosts=["www.virustotal.com"])
        assert adapter.is_configured() is True


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestProtocolConformance:

    def test_cymru_adapter_satisfies_provider_protocol(self) -> None:
        """CymruASNAdapter instance must satisfy the Provider @runtime_checkable protocol."""
        adapter = _make_adapter()
        assert isinstance(adapter, Provider), (
            "CymruASNAdapter must satisfy Provider protocol via @runtime_checkable"
        )


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


# ---------------------------------------------------------------------------
# Successful lookup tests
# ---------------------------------------------------------------------------


class TestSuccessfulLookup:

    def test_successful_lookup_returns_enrichment_result(self) -> None:
        """Successful TXT lookup returns EnrichmentResult, not EnrichmentError."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult, got {type(result).__name__}: {result!r}"
        )

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

    def test_successful_lookup_provider_name(self) -> None:
        """Result provider must be 'ASN Intel'."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.provider == "ASN Intel"

    def test_detection_count_always_zero(self) -> None:
        """detection_count must always be 0 — ASN is informational."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.detection_count == 0

    def test_total_engines_always_zero(self) -> None:
        """total_engines must always be 0 — ASN is informational."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.total_engines == 0

    def test_scan_date_always_none(self) -> None:
        """scan_date must always be None — ASN has no scan date concept."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.scan_date is None

    def test_raw_stats_has_asn_key(self) -> None:
        """raw_stats must contain 'asn' key from parsed TXT response."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert "asn" in result.raw_stats, "raw_stats must contain 'asn' key"

    def test_raw_stats_has_prefix_key(self) -> None:
        """raw_stats must contain 'prefix' key from parsed TXT response."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert "prefix" in result.raw_stats, "raw_stats must contain 'prefix' key"

    def test_raw_stats_has_rir_key(self) -> None:
        """raw_stats must contain 'rir' key from parsed TXT response."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert "rir" in result.raw_stats, "raw_stats must contain 'rir' key"

    def test_raw_stats_has_allocated_key(self) -> None:
        """raw_stats must contain 'allocated' key from parsed TXT response."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert "allocated" in result.raw_stats, "raw_stats must contain 'allocated' key"

    def test_raw_stats_asn_value(self) -> None:
        """raw_stats['asn'] must be '23028' from sample TXT response."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["asn"] == "23028", (
            f"Expected asn='23028', got: {result.raw_stats.get('asn')!r}"
        )

    def test_raw_stats_prefix_value(self) -> None:
        """raw_stats['prefix'] must be '216.90.108.0/24' from sample TXT response."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["prefix"] == "216.90.108.0/24", (
            f"Expected prefix='216.90.108.0/24', got: {result.raw_stats.get('prefix')!r}"
        )

    def test_raw_stats_rir_value(self) -> None:
        """raw_stats['rir'] must be 'arin' from sample TXT response."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["rir"] == "arin", (
            f"Expected rir='arin', got: {result.raw_stats.get('rir')!r}"
        )

    def test_raw_stats_allocated_value(self) -> None:
        """raw_stats['allocated'] must be '1998-09-25' from sample TXT response."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = _make_txt_answer(SAMPLE_TXT)

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["allocated"] == "1998-09-25", (
            f"Expected allocated='1998-09-25', got: {result.raw_stats.get('allocated')!r}"
        )


# ---------------------------------------------------------------------------
# NXDOMAIN handling
# ---------------------------------------------------------------------------


class TestNXDOMAIN:

    def test_nxdomain_returns_enrichment_result(self) -> None:
        """NXDOMAIN must return EnrichmentResult(verdict='no_data'), NOT EnrichmentError.

        Private/RFC-1918 IPs return NXDOMAIN — this is expected 'no BGP entry', not an error.
        """
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = dns.resolver.NXDOMAIN()

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(PRIVATE_IPV4_IOC)

        assert isinstance(result, EnrichmentResult), (
            f"NXDOMAIN must return EnrichmentResult not EnrichmentError, got {type(result).__name__}"
        )

    def test_nxdomain_verdict_is_no_data(self) -> None:
        """NXDOMAIN -> verdict='no_data' (private IP has no BGP route, not an error)."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = dns.resolver.NXDOMAIN()

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(PRIVATE_IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"

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

    def test_nxdomain_is_not_enrichment_error(self) -> None:
        """NXDOMAIN must NOT return EnrichmentError."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = dns.resolver.NXDOMAIN()

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(PRIVATE_IPV4_IOC)

        assert not isinstance(result, EnrichmentError), (
            "NXDOMAIN is 'no BGP entry' (private IP), NOT a lookup failure — return EnrichmentResult"
        )

    def test_nxdomain_detection_count_zero(self) -> None:
        """NXDOMAIN -> detection_count=0."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = dns.resolver.NXDOMAIN()

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(PRIVATE_IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.detection_count == 0

    def test_nxdomain_scan_date_none(self) -> None:
        """NXDOMAIN -> scan_date=None."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = dns.resolver.NXDOMAIN()

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(PRIVATE_IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.scan_date is None


# ---------------------------------------------------------------------------
# DNS error handling (NoAnswer, NoNameservers, Timeout)
# ---------------------------------------------------------------------------


class TestDNSErrors:

    def test_no_answer_returns_enrichment_result(self) -> None:
        """NoAnswer must return EnrichmentResult(verdict='no_data'), NOT EnrichmentError."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = dns.resolver.NoAnswer()

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult), (
            f"NoAnswer must return EnrichmentResult, got {type(result).__name__}"
        )

    def test_no_answer_verdict_is_no_data(self) -> None:
        """NoAnswer -> verdict='no_data'."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = dns.resolver.NoAnswer()

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"

    def test_no_nameservers_returns_enrichment_result(self) -> None:
        """NoNameservers must return EnrichmentResult(verdict='no_data'), NOT EnrichmentError."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = dns.resolver.NoNameservers()

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult), (
            f"NoNameservers must return EnrichmentResult, got {type(result).__name__}"
        )

    def test_no_nameservers_verdict_is_no_data(self) -> None:
        """NoNameservers -> verdict='no_data'."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = dns.resolver.NoNameservers()

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"

    def test_timeout_returns_enrichment_result(self) -> None:
        """dns.exception.Timeout must return EnrichmentResult(verdict='no_data'), NOT EnrichmentError."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = dns.exception.Timeout()

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult), (
            f"Timeout must return EnrichmentResult, got {type(result).__name__}"
        )

    def test_timeout_verdict_is_no_data(self) -> None:
        """Timeout -> verdict='no_data'."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = dns.exception.Timeout()

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"

    def test_no_answer_returns_empty_raw_stats(self) -> None:
        """NoAnswer -> raw_stats={}."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = dns.resolver.NoAnswer()

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats == {}

    def test_timeout_returns_empty_raw_stats(self) -> None:
        """Timeout -> raw_stats={}."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = dns.exception.Timeout()

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats == {}

    def test_no_nameservers_returns_empty_raw_stats(self) -> None:
        """NoNameservers -> raw_stats={}."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = dns.resolver.NoNameservers()

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats == {}


# ---------------------------------------------------------------------------
# Unexpected exception handling
# ---------------------------------------------------------------------------


class TestUnexpectedError:

    def test_generic_exception_returns_enrichment_error(self) -> None:
        """Generic/unexpected Exception must return EnrichmentError, NOT EnrichmentResult."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = RuntimeError("unexpected failure")

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentError), (
            f"Unexpected exception must return EnrichmentError, got {type(result).__name__}"
        )

    def test_generic_exception_provider_name_correct(self) -> None:
        """EnrichmentError from unexpected exception must have provider='ASN Intel'."""
        mock_resolver = MagicMock()
        mock_resolver.resolve.side_effect = RuntimeError("unexpected failure")

        with patch("dns.resolver.Resolver", return_value=mock_resolver):
            result = _make_adapter().lookup(IPV4_IOC)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "ASN Intel"


# ---------------------------------------------------------------------------
# Unsupported IOC type
# ---------------------------------------------------------------------------


class TestUnsupportedType:

    def test_domain_ioc_returns_enrichment_error(self) -> None:
        """DOMAIN IOC -> EnrichmentError (CymruASNAdapter only supports IPV4/IPV6)."""
        result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentError), (
            f"DOMAIN IOC must return EnrichmentError, got {type(result).__name__}"
        )

    def test_domain_ioc_error_provider_name(self) -> None:
        """EnrichmentError from unsupported type must have provider='ASN Intel'."""
        result = _make_adapter().lookup(DOMAIN_IOC)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "ASN Intel"

    def test_domain_ioc_does_not_call_dns(self) -> None:
        """DOMAIN IOC -> no DNS resolution attempted."""
        with patch("dns.resolver.Resolver") as mock_cls:
            _make_adapter().lookup(DOMAIN_IOC)
        mock_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Invalid IP string handling
# ---------------------------------------------------------------------------


class TestInvalidIP:

    def test_invalid_ip_returns_enrichment_error(self) -> None:
        """Invalid IP string -> EnrichmentError (ipaddress.ip_address() raises ValueError)."""
        result = _make_adapter().lookup(INVALID_IP_IOC)

        assert isinstance(result, EnrichmentError), (
            f"Invalid IP must return EnrichmentError, got {type(result).__name__}"
        )

    def test_invalid_ip_provider_name(self) -> None:
        """EnrichmentError from invalid IP must have provider='ASN Intel'."""
        result = _make_adapter().lookup(INVALID_IP_IOC)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "ASN Intel"

    def test_invalid_ip_does_not_call_dns(self) -> None:
        """Invalid IP -> no DNS resolution attempted."""
        with patch("dns.resolver.Resolver") as mock_cls:
            _make_adapter().lookup(INVALID_IP_IOC)
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
