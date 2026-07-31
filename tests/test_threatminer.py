"""Tests for ThreatMinerAdapter — verdict logic, multi-call routing, and response parsing.

Contract tests (protocol, error handling, safety controls) are in test_adapter_contract.py.

All HTTP calls are mocked using unittest.mock.patch -- no real API calls.
"""
from __future__ import annotations

import inspect
from unittest.mock import MagicMock

import requests
import requests.exceptions

from app.enrichment.adapters.threatminer import (
    THREATMINER_BASE_DOMAIN,
    ThreatMinerAdapter,
    _domain_raw_stats,
    _extract_field_values,
    _extract_samples,
    _has_results,
    _no_data_result,
    _passive_dns_raw_stats,
    _samples_raw_stats,
    _threatminer_request_url,
    append_domain_passive_dns,
    append_domain_samples,
)
from tests.helpers import (
    make_mock_response,
    mock_adapter_session,
    make_domain_ioc,
    make_ipv4_ioc,
    make_ipv6_ioc,
    make_md5_ioc,
    make_sha1_ioc,
    make_sha256_ioc,
)
from app.enrichment.models import EnrichmentError, EnrichmentResult


ALLOWED_HOSTS = ["api.threatminer.org"]


# --- Sample API responses ---

IP_PASSIVE_DNS_RESPONSE = {
    "status_code": "200",
    "status_message": "Results found.",
    "results": [
        {"domain": "evil.com", "first_seen": "2022-01-01 00:00:00", "last_seen": "2023-01-01 00:00:00"},
        {"domain": "malware.net", "first_seen": "2021-06-01 00:00:00", "last_seen": "2022-06-01 00:00:00"},
        {"domain": "bad.org", "first_seen": "2023-01-01 00:00:00", "last_seen": "2024-01-01 00:00:00"},
    ],
}

DOMAIN_PASSIVE_DNS_RESPONSE = {
    "status_code": "200",
    "status_message": "Results found.",
    "results": [
        {"ip": "1.2.3.4", "first_seen": "2022-01-01 00:00:00", "last_seen": "2023-01-01 00:00:00"},
        {"ip": "5.6.7.8", "first_seen": "2021-06-01 00:00:00", "last_seen": "2022-06-01 00:00:00"},
    ],
}

DOMAIN_SAMPLES_RESPONSE = {
    "status_code": "200",
    "status_message": "Results found.",
    "results": [
        "dd0418c01b7196e967a63fedda70eaf6de4fffb5296a24b9ec13f7a09c2f7bc1",
        "abf736e1a8e0508b6dd840b012d4231cf13f8b48c2dcb3ed18ce92a59dba7109",
    ],
}

HASH_SAMPLES_RESPONSE = {
    "status_code": "200",
    "status_message": "Results found.",
    "results": [
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    ],
}

NO_DATA_RESPONSE = {
    "status_code": "404",
    "status_message": "Results not found.",
    "results": [],
}

EMPTY_RESULTS_RESPONSE = {
    "status_code": "200",
    "status_message": "Results found.",
    "results": [],
}


class _BoundedResults:
    def __init__(self, rows, *, max_reads: int):
        self._rows = rows
        self.max_reads = max_reads
        self.reads = 0

    def __iter__(self):
        for row in self._rows:
            self.reads += 1
            if self.reads > self.max_reads:
                raise AssertionError("ThreatMiner extraction should stop at the cap")
            yield row

    def __bool__(self) -> bool:
        return bool(self._rows)


class _ExplodingResults:
    def __iter__(self):
        raise AssertionError("zero-cap extraction should not read result rows")


# --- Helpers ---

def _make_adapter(allowed_hosts: list[str] | None = None) -> ThreatMinerAdapter:
    if allowed_hosts is None:
        allowed_hosts = ALLOWED_HOSTS
    return ThreatMinerAdapter(allowed_hosts=allowed_hosts)


def _mock_get_returning(response_body: dict) -> MagicMock:
    """Return a requests.get mock that returns the given response body via iter_content."""
    return make_mock_response(200, response_body)


# ===================================================================
# TestIPLookup
# ===================================================================

class TestIPLookup:

    def test_ip_lookup_returns_enrichment_result(self) -> None:
        """IPv4 lookup returns EnrichmentResult with correct response shape."""
        ioc = make_ipv4_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(IP_PASSIVE_DNS_RESPONSE))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult, got {type(result).__name__}: {result!r}"
        )
        assert result.detection_count == 0, "informational adapter — detection_count must be 0"
        assert result.total_engines == 0, "informational adapter — total_engines must be 0"
        assert result.scan_date is None, "informational adapter — scan_date must be None"

    def test_ip_lookup_returns_passive_dns_list(self) -> None:
        """IPv4 lookup returns passive_dns list in raw_stats."""
        ioc = make_ipv4_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(IP_PASSIVE_DNS_RESPONSE))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "passive_dns" in result.raw_stats
        assert isinstance(result.raw_stats["passive_dns"], list)

    def test_ip_lookup_passive_dns_contains_domains(self) -> None:
        """IPv4 passive_dns list contains the domain names from API response."""
        ioc = make_ipv4_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(IP_PASSIVE_DNS_RESPONSE))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        passive_dns = result.raw_stats["passive_dns"]
        assert "evil.com" in passive_dns
        assert "malware.net" in passive_dns
        assert "bad.org" in passive_dns

    def test_ip_lookup_uses_host_php_endpoint(self) -> None:
        """IP lookup must call host.php endpoint (not domain.php or sample.php)."""
        ioc = make_ipv4_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(IP_PASSIVE_DNS_RESPONSE))
        adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert "host.php" in called_url, f"Expected host.php in URL, got: {called_url}"

    def test_ip_lookup_uses_rt_2(self) -> None:
        """IP lookup must use rt=2 (passive DNS)."""
        ioc = make_ipv4_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(IP_PASSIVE_DNS_RESPONSE))
        adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert "rt=2" in called_url, f"Expected rt=2 in URL, got: {called_url}"

    def test_ip_lookup_passive_dns_capped_at_25(self) -> None:
        """passive_dns list is capped at 25 entries."""
        ioc = make_ipv4_ioc()
        # Create 30 domain results
        many_results = {
            "status_code": "200",
            "status_message": "Results found.",
            "results": [
                {"domain": f"sub{i}.example.com", "first_seen": "2022-01-01", "last_seen": "2023-01-01"}
                for i in range(30)
            ],
        }

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(many_results))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert len(result.raw_stats["passive_dns"]) <= 25, (
            f"Expected at most 25 passive_dns entries (cap), got {len(result.raw_stats['passive_dns'])}"
        )

    def test_ip_lookup_passive_dns_stops_at_cap(self) -> None:
        """IP passive DNS extraction should not read past the 25-row cap."""
        rows = _BoundedResults(
            [{"domain": f"sub{i}.example.com"} for i in range(30)],
            max_reads=25,
        )
        domains = _extract_field_values(rows, "domain", limit=25)

        assert rows.reads == 25
        assert len(domains) == 25
        assert domains[-1] == "sub24.example.com"

    def test_zero_cap_passive_dns_skips_result_iteration(self) -> None:
        """A zero passive-DNS cap should return empty without reading rows."""
        assert _extract_field_values(_ExplodingResults(), "domain", limit=0) == []

    def test_empty_single_pair_three_and_four_passive_dns_lists_skip_accumulator_loop(self) -> None:
        class NoIterList(list):
            def __iter__(self):
                raise AssertionError("short passive DNS extraction should not iterate")

        assert _extract_field_values([], "domain", limit=25) == []
        assert _extract_field_values([{"domain": "only.example"}], "domain", limit=25) == [
            "only.example"
        ]
        assert _extract_field_values([{"ip": "1.2.3.4"}], "domain", limit=25) == []
        assert _extract_field_values(
            NoIterList([{"domain": "first.example"}, {"domain": "second.example"}]),
            "domain",
            limit=25,
        ) == ["first.example", "second.example"]
        assert _extract_field_values(
            NoIterList([{"ip": "1.2.3.4"}, {"domain": "second.example"}]),
            "domain",
            limit=1,
        ) == ["second.example"]
        assert _extract_field_values(
            NoIterList([
                {"domain": "first.example"},
                {"domain": "second.example"},
                {"domain": "third.example"},
            ]),
            "domain",
            limit=25,
        ) == ["first.example", "second.example", "third.example"]
        assert _extract_field_values(
            NoIterList([
                {"ip": "1.2.3.4"},
                {"domain": "second.example"},
                {"domain": "third.example"},
            ]),
            "domain",
            limit=1,
        ) == ["second.example"]
        assert _extract_field_values(
            NoIterList([
                {"domain": "first.example"},
                {"domain": "second.example"},
                {"domain": "third.example"},
                {"domain": "fourth.example"},
            ]),
            "domain",
            limit=25,
        ) == ["first.example", "second.example", "third.example", "fourth.example"]
        assert "len" in _extract_field_values.__code__.co_names
        assert "result_count == 4" in inspect.getsource(_extract_field_values)
        assert "_append_field_value" in _extract_field_values.__code__.co_names

    def test_ip_lookup_verdict_is_no_data(self) -> None:
        """IP lookup verdict is always 'no_data' (informational context, not threat signal)."""
        ioc = make_ipv4_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(IP_PASSIVE_DNS_RESPONSE))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"

    def test_ipv6_lookup_uses_host_php(self) -> None:
        """IPv6 lookup also uses host.php (same endpoint as IPv4)."""
        ioc = make_ipv6_ioc("2001:db8::1")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(NO_DATA_RESPONSE))
        adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert "host.php" in called_url, f"Expected host.php for IPv6, got: {called_url}"


# ===================================================================
# TestDomainLookup
# ===================================================================

class TestDomainLookup:

    def test_domain_lookup_returns_enrichment_result(self) -> None:
        """Domain lookup returns EnrichmentResult (not EnrichmentError)."""
        ioc = make_domain_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, side_effect=[make_mock_response(200, DOMAIN_PASSIVE_DNS_RESPONSE), make_mock_response(200, DOMAIN_SAMPLES_RESPONSE)])
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult, got {type(result).__name__}: {result!r}"
        )

    def test_domain_lookup_makes_two_api_calls(self) -> None:
        """Domain lookup makes exactly 2 API calls (rt=2 passive DNS + rt=4 related samples)."""
        ioc = make_domain_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, side_effect=[make_mock_response(200, DOMAIN_PASSIVE_DNS_RESPONSE), make_mock_response(200, DOMAIN_SAMPLES_RESPONSE)])
        adapter.lookup(ioc)

        assert adapter._session.get.call_count == 2, (
            f"Domain lookup must make exactly 2 API calls (rt=2 + rt=4), got {adapter._session.get.call_count}"
        )

    def test_domain_lookup_first_call_uses_rt_2(self) -> None:
        """First API call for domain must use rt=2 (passive DNS)."""
        ioc = make_domain_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, side_effect=[make_mock_response(200, DOMAIN_PASSIVE_DNS_RESPONSE), make_mock_response(200, DOMAIN_SAMPLES_RESPONSE)])
        adapter.lookup(ioc)

        first_call = adapter._session.get.call_args_list[0]
        called_url = first_call.args[0]
        assert "rt=2" in called_url, f"First call must use rt=2, got: {called_url}"

    def test_domain_lookup_second_call_uses_rt_4(self) -> None:
        """Second API call for domain must use rt=4 (related samples)."""
        ioc = make_domain_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, side_effect=[make_mock_response(200, DOMAIN_PASSIVE_DNS_RESPONSE), make_mock_response(200, DOMAIN_SAMPLES_RESPONSE)])
        adapter.lookup(ioc)

        second_call = adapter._session.get.call_args_list[1]
        called_url = second_call.args[0]
        assert "rt=4" in called_url, f"Second call must use rt=4, got: {called_url}"

    def test_domain_lookup_uses_domain_php_endpoint(self) -> None:
        """Domain lookup must call domain.php endpoint."""
        ioc = make_domain_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, side_effect=[make_mock_response(200, DOMAIN_PASSIVE_DNS_RESPONSE), make_mock_response(200, DOMAIN_SAMPLES_RESPONSE)])
        adapter.lookup(ioc)

        for call_args in adapter._session.get.call_args_list:
            called_url = call_args.args[0]
            assert "domain.php" in called_url, f"Domain lookup must use domain.php, got: {called_url}"

    def test_domain_lookup_returns_merged_passive_dns_and_samples(self) -> None:
        """Domain lookup result contains both passive_dns and samples in raw_stats."""
        ioc = make_domain_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, side_effect=[make_mock_response(200, DOMAIN_PASSIVE_DNS_RESPONSE), make_mock_response(200, DOMAIN_SAMPLES_RESPONSE)])
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "passive_dns" in result.raw_stats, "raw_stats must contain 'passive_dns'"
        assert "samples" in result.raw_stats, "raw_stats must contain 'samples'"

    def test_domain_lookup_passive_dns_contains_ips(self) -> None:
        """Domain lookup passive_dns list contains IP addresses."""
        ioc = make_domain_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, side_effect=[make_mock_response(200, DOMAIN_PASSIVE_DNS_RESPONSE), make_mock_response(200, DOMAIN_SAMPLES_RESPONSE)])
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        passive_dns = result.raw_stats["passive_dns"]
        assert "1.2.3.4" in passive_dns
        assert "5.6.7.8" in passive_dns

    def test_domain_lookup_samples_contains_hashes(self) -> None:
        """Domain lookup samples list contains SHA-256 hashes."""
        ioc = make_domain_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, side_effect=[make_mock_response(200, DOMAIN_PASSIVE_DNS_RESPONSE), make_mock_response(200, DOMAIN_SAMPLES_RESPONSE)])
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        samples = result.raw_stats["samples"]
        assert "dd0418c01b7196e967a63fedda70eaf6de4fffb5296a24b9ec13f7a09c2f7bc1" in samples

    def test_domain_lookup_passive_dns_capped_at_25(self) -> None:
        """Domain passive_dns list is capped at 25 entries."""
        ioc = make_domain_ioc()
        many_ips = {
            "status_code": "200",
            "status_message": "Results found.",
            "results": [
                {"ip": f"10.0.{i}.1", "first_seen": "2022-01-01", "last_seen": "2023-01-01"}
                for i in range(30)
            ],
        }

        adapter = _make_adapter()
        mock_adapter_session(adapter, side_effect=[make_mock_response(200, many_ips), make_mock_response(200, DOMAIN_SAMPLES_RESPONSE)])
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert len(result.raw_stats["passive_dns"]) <= 25, (
            f"Expected at most 25 passive_dns entries, got {len(result.raw_stats['passive_dns'])}"
        )

    def test_domain_lookup_samples_capped_at_20(self) -> None:
        """Domain samples list is capped at 20 entries."""
        ioc = make_domain_ioc()
        many_samples = {
            "status_code": "200",
            "status_message": "Results found.",
            "results": [f"{'a' * 63}{i:01d}" for i in range(25)],
        }

        adapter = _make_adapter()
        mock_adapter_session(adapter, side_effect=[make_mock_response(200, DOMAIN_PASSIVE_DNS_RESPONSE), make_mock_response(200, many_samples)])
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert len(result.raw_stats["samples"]) <= 20, (
            f"Expected at most 20 samples entries, got {len(result.raw_stats['samples'])}"
        )

    def test_domain_lookup_samples_stop_at_cap(self) -> None:
        """Domain related-sample extraction should not read past the 20-row cap."""
        rows = _BoundedResults(
            [f"{'a' * 63}{i:01d}" for i in range(25)],
            max_reads=20,
        )
        samples = _extract_samples(rows, limit=20)

        assert rows.reads == 20
        assert len(samples) == 20
        assert samples[-1].endswith("9")

    def test_zero_cap_samples_skip_result_iteration(self) -> None:
        """A zero sample cap should return empty without reading rows."""
        assert _extract_samples(_ExplodingResults(), limit=0) == []

    def test_empty_single_pair_three_and_four_sample_lists_skip_accumulator_loop(self) -> None:
        class NoIterList(list):
            def __iter__(self):
                raise AssertionError("short sample extraction should not iterate")

        assert _extract_samples([], limit=20) == []
        assert _extract_samples(["hash-only"], limit=20) == ["hash-only"]
        assert _extract_samples([{"sha256": "hash-from-dict"}], limit=20) == ["hash-from-dict"]
        assert _extract_samples([{"count": 1}], limit=20) == []
        assert _extract_samples(
            NoIterList(["first-hash", {"sha256": "second-hash"}]),
            limit=20,
        ) == ["first-hash", "second-hash"]
        assert _extract_samples(
            NoIterList([{"sha256": "first-hash"}, "second-hash"]),
            limit=1,
        ) == ["first-hash"]
        assert _extract_samples(
            NoIterList(["first-hash", {"sha256": "second-hash"}, "third-hash"]),
            limit=20,
        ) == ["first-hash", "second-hash", "third-hash"]
        assert _extract_samples(
            NoIterList([{"count": 1}, {"sha256": "second-hash"}, "third-hash"]),
            limit=1,
        ) == ["second-hash"]
        assert _extract_samples(
            NoIterList(["first-hash", {"sha256": "second-hash"}, "third-hash", "fourth-hash"]),
            limit=20,
        ) == ["first-hash", "second-hash", "third-hash", "fourth-hash"]
        assert "len" in _extract_samples.__code__.co_names
        assert "result_count == 4" in inspect.getsource(_extract_samples)
        assert "_append_sample_value" in _extract_samples.__code__.co_names

    def test_dict_sample_rows_do_not_allocate_values_view(self) -> None:
        """Defensive dict sample extraction should scan keys directly."""
        from app.enrichment.adapters import threatminer

        class NoValuesDict(dict):
            def values(self):
                raise AssertionError("sample extraction should not allocate a values view")

        samples = _extract_samples(
            [
                NoValuesDict({"ignored": 1, "sample": "hash-from-dict"}),
            ],
            limit=20,
        )

        assert samples == ["hash-from-dict"]
        append_source = inspect.getsource(threatminer._append_sample_value)
        string_append_source = inspect.getsource(threatminer._append_sample_string)
        assert "_append_sample_string(samples, row)" in append_source
        assert "_append_sample_string(samples, v)" in append_source
        assert "samples.append(row)" not in append_source
        assert "samples.append(v)" not in append_source
        assert "samples.append(value)" in string_append_source

    def test_domain_lookup_verdict_is_no_data(self) -> None:
        """Domain lookup verdict is always 'no_data'."""
        ioc = make_domain_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, side_effect=[make_mock_response(200, DOMAIN_PASSIVE_DNS_RESPONSE), make_mock_response(200, DOMAIN_SAMPLES_RESPONSE)])
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"


# ===================================================================
# TestHashLookup
# ===================================================================

class TestHashLookup:

    def test_hash_lookup_returns_enrichment_result(self) -> None:
        """SHA256 lookup returns EnrichmentResult."""
        ioc = make_sha256_ioc("dd0418c01b7196e967a63fedda70eaf6de4fffb5296a24b9ec13f7a09c2f7bc1")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(HASH_SAMPLES_RESPONSE))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult, got {type(result).__name__}: {result!r}"
        )

    def test_hash_lookup_returns_samples_list(self) -> None:
        """SHA256 lookup returns samples list in raw_stats."""
        ioc = make_sha256_ioc("dd0418c01b7196e967a63fedda70eaf6de4fffb5296a24b9ec13f7a09c2f7bc1")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(HASH_SAMPLES_RESPONSE))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert "samples" in result.raw_stats
        assert isinstance(result.raw_stats["samples"], list)

    def test_hash_lookup_samples_contains_hashes(self) -> None:
        """SHA256 lookup samples list contains the related hashes from API response."""
        ioc = make_sha256_ioc("dd0418c01b7196e967a63fedda70eaf6de4fffb5296a24b9ec13f7a09c2f7bc1")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(HASH_SAMPLES_RESPONSE))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        samples = result.raw_stats["samples"]
        assert "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" in samples
        assert "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" in samples

    def test_hash_lookup_uses_sample_php_endpoint(self) -> None:
        """Hash lookup must call sample.php endpoint."""
        ioc = make_sha256_ioc("dd0418c01b7196e967a63fedda70eaf6de4fffb5296a24b9ec13f7a09c2f7bc1")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(HASH_SAMPLES_RESPONSE))
        adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert "sample.php" in called_url, f"Expected sample.php, got: {called_url}"

    def test_hash_lookup_uses_rt_4(self) -> None:
        """Hash lookup must use rt=4 (related samples)."""
        ioc = make_sha256_ioc("dd0418c01b7196e967a63fedda70eaf6de4fffb5296a24b9ec13f7a09c2f7bc1")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(HASH_SAMPLES_RESPONSE))
        adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert "rt=4" in called_url, f"Expected rt=4 in URL, got: {called_url}"

    def test_hash_lookup_samples_capped_at_20(self) -> None:
        """Hash samples list is capped at 20 entries."""
        ioc = make_sha256_ioc("dd0418c01b7196e967a63fedda70eaf6de4fffb5296a24b9ec13f7a09c2f7bc1")
        many_samples = {
            "status_code": "200",
            "status_message": "Results found.",
            "results": [f"{'a' * 63}{i:01d}" for i in range(25)],
        }

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(many_samples))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert len(result.raw_stats["samples"]) <= 20, (
            f"Expected at most 20 sample entries, got {len(result.raw_stats['samples'])}"
        )

    def test_hash_lookup_samples_stop_at_cap(self) -> None:
        """Hash sample extraction should not read past the 20-row cap."""
        rows = _BoundedResults(
            [f"{'a' * 63}{i:01d}" for i in range(25)],
            max_reads=20,
        )
        samples = _extract_samples(rows, limit=20)

        assert rows.reads == 20
        assert len(samples) == 20
        assert samples[-1].endswith("9")

    def test_md5_lookup_uses_sample_php(self) -> None:
        """MD5 hash lookup also uses sample.php."""
        ioc = make_md5_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(HASH_SAMPLES_RESPONSE))
        adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert "sample.php" in called_url

    def test_sha1_lookup_uses_sample_php(self) -> None:
        """SHA1 hash lookup also uses sample.php."""
        ioc = make_sha1_ioc("da39a3ee5e6b4b0d3255bfef95601890afd80709")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(HASH_SAMPLES_RESPONSE))
        adapter.lookup(ioc)

        called_url = adapter._session.get.call_args.args[0]
        assert "sample.php" in called_url

    def test_hash_lookup_verdict_is_no_data(self) -> None:
        """Hash lookup verdict is always 'no_data'."""
        ioc = make_sha256_ioc("dd0418c01b7196e967a63fedda70eaf6de4fffb5296a24b9ec13f7a09c2f7bc1")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(HASH_SAMPLES_RESPONSE))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"

    def test_hash_lookup_defensive_dict_handling(self) -> None:
        """Hash results that are dicts (unexpected) are handled defensively."""
        ioc = make_sha256_ioc("dd0418c01b7196e967a63fedda70eaf6de4fffb5296a24b9ec13f7a09c2f7bc1")
        dict_results = {
            "status_code": "200",
            "status_message": "Results found.",
            "results": [
                {"sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
                "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            ],
        }

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(dict_results))
        # Should not raise an exception
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        # At minimum the plain string result should be included
        assert "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" in result.raw_stats.get("samples", [])


# ===================================================================
# TestNoDataHandling
# ===================================================================

class TestNoDataHandling:

    def test_call_delegates_request_url_construction(self) -> None:
        """ThreatMiner safe_request dispatch should not own query-string construction."""
        from app.enrichment.adapters import threatminer

        call_source = inspect.getsource(threatminer.ThreatMinerAdapter._call)

        assert "_threatminer_request_url(base_url, ioc.value, rt)" in call_source
        assert "?q=" not in call_source
        assert "&rt=" not in call_source

    def test_request_url_helper_preserves_query_shape(self) -> None:
        """ThreatMiner request URL construction should live in one helper."""
        assert _threatminer_request_url(THREATMINER_BASE_DOMAIN, "example.com", "4") == (
            "https://api.threatminer.org/v2/domain.php?q=example.com&rt=4"
        )

    def test_lookup_paths_delegate_result_gates_and_raw_stats_helpers(self) -> None:
        """ThreatMiner lookup paths should not own repeated raw_stats mechanics."""
        from app.enrichment.adapters import threatminer

        ip_source = inspect.getsource(threatminer.ThreatMinerAdapter._lookup_ip)
        domain_source = inspect.getsource(threatminer.ThreatMinerAdapter._lookup_domain)
        hash_source = inspect.getsource(threatminer.ThreatMinerAdapter._lookup_hash)

        assert "not _has_results(body)" in ip_source
        assert "_passive_dns_raw_stats(body, field_name=\"domain\")" in ip_source
        assert "_domain_raw_stats(dns_body=dns_body, samples_body=samples_body)" in domain_source
        assert "raw_stats: dict = {}" not in domain_source
        assert "not _has_results(body)" in hash_source
        assert "_samples_raw_stats(body)" in hash_source
        assert '{"samples": samples}' not in hash_source

    def test_no_data_result_helper_preserves_informational_shape(self) -> None:
        """ThreatMiner no-data branches should share one result shape."""
        ioc = make_domain_ioc()
        raw_stats = {"samples": ["abc"]}

        result = _no_data_result(ioc, "ThreatMiner", raw_stats)

        assert result.ioc is ioc
        assert result.provider == "ThreatMiner"
        assert result.verdict == "no_data"
        assert result.detection_count == 0
        assert result.total_engines == 0
        assert result.scan_date is None
        assert result.raw_stats is raw_stats
        assert "no_data_result(ioc, provider_name, raw_stats)" in inspect.getsource(_no_data_result)

    def test_result_body_gate_preserves_404_and_empty_semantics(self) -> None:
        """ThreatMiner body gate should reject 404 and empty result bodies."""
        assert _has_results(NO_DATA_RESPONSE) is False
        assert _has_results(EMPTY_RESULTS_RESPONSE) is False
        assert _has_results(IP_PASSIVE_DNS_RESPONSE) is True

    def test_raw_stats_helpers_preserve_public_shapes(self) -> None:
        """ThreatMiner raw_stats helpers should preserve passive DNS and sample envelopes."""
        passive_stats = _passive_dns_raw_stats(IP_PASSIVE_DNS_RESPONSE, field_name="domain")
        sample_stats = _samples_raw_stats(HASH_SAMPLES_RESPONSE)
        merged_stats = _domain_raw_stats(
            dns_body=DOMAIN_PASSIVE_DNS_RESPONSE,
            samples_body=DOMAIN_SAMPLES_RESPONSE,
        )

        assert list(passive_stats) == ["passive_dns"]
        assert passive_stats["passive_dns"] == ["evil.com", "malware.net", "bad.org"]
        assert list(sample_stats) == ["samples"]
        assert sample_stats["samples"] == HASH_SAMPLES_RESPONSE["results"]
        assert list(merged_stats) == ["passive_dns", "samples"]
        assert merged_stats["passive_dns"] == ["1.2.3.4", "5.6.7.8"]
        assert merged_stats["samples"] == DOMAIN_SAMPLES_RESPONSE["results"]

    def test_domain_raw_stats_omits_empty_extracted_lists(self) -> None:
        """Domain raw_stats should only include ThreatMiner data that exists."""
        dns_without_ips = {
            "status_code": "200",
            "results": [{"domain": "example.com"}],
        }

        assert _domain_raw_stats(
            dns_body=dns_without_ips,
            samples_body=NO_DATA_RESPONSE,
        ) == {}

    def test_domain_raw_stats_delegates_optional_sections(self) -> None:
        """Domain raw_stats should delegate optional passive DNS and sample sections."""
        raw_stats: dict = {}

        append_domain_passive_dns(raw_stats, DOMAIN_PASSIVE_DNS_RESPONSE)
        append_domain_samples(raw_stats, DOMAIN_SAMPLES_RESPONSE)

        domain_source = inspect.getsource(_domain_raw_stats)
        passive_source = inspect.getsource(append_domain_passive_dns)
        samples_source = inspect.getsource(append_domain_samples)
        assert raw_stats == {
            "passive_dns": ["1.2.3.4", "5.6.7.8"],
            "samples": DOMAIN_SAMPLES_RESPONSE["results"],
        }
        assert "append_domain_passive_dns(raw_stats, dns_body)" in domain_source
        assert "append_domain_samples(raw_stats, samples_body)" in domain_source
        assert "_passive_dns_raw_stats(" not in domain_source
        assert "_samples_raw_stats(" not in domain_source
        assert "_passive_dns_raw_stats(dns_body, field_name=\"ip\")" in passive_source
        assert "_samples_raw_stats(samples_body)" in samples_source

    def test_ip_body_404_returns_no_data(self) -> None:
        """IP lookup with body status_code '404' returns EnrichmentResult(verdict='no_data')."""
        ioc = make_ipv4_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(NO_DATA_RESPONSE))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"status_code '404' in body must return EnrichmentResult (no_data), not EnrichmentError. Got: {result!r}"
        )
        assert result.verdict == "no_data"

    def test_ip_body_404_returns_empty_raw_stats(self) -> None:
        """IP lookup with body status_code '404' returns empty raw_stats."""
        ioc = make_ipv4_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(NO_DATA_RESPONSE))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats == {}

    def test_ip_empty_results_returns_no_data(self) -> None:
        """IP lookup with status_code '200' but empty results returns no_data."""
        ioc = make_ipv4_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(EMPTY_RESULTS_RESPONSE))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"

    def test_domain_both_404_returns_no_data(self) -> None:
        """Domain lookup with both calls returning status_code '404' returns no_data."""
        ioc = make_domain_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, side_effect=[make_mock_response(200, NO_DATA_RESPONSE), make_mock_response(200, NO_DATA_RESPONSE)])
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"
        assert result.raw_stats == {}

    def test_domain_first_404_second_has_data(self) -> None:
        """Domain with passive DNS '404' but samples data -> samples included, passive_dns absent or empty."""
        ioc = make_domain_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, side_effect=[make_mock_response(200, NO_DATA_RESPONSE), make_mock_response(200, DOMAIN_SAMPLES_RESPONSE)])
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        # samples should be populated from the second call
        assert result.raw_stats.get("samples"), "samples should be present when rt=4 has data"

    def test_domain_second_404_first_has_data(self) -> None:
        """Domain with passive DNS data but samples '404' -> passive_dns included, samples absent or empty."""
        ioc = make_domain_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, side_effect=[make_mock_response(200, DOMAIN_PASSIVE_DNS_RESPONSE), make_mock_response(200, NO_DATA_RESPONSE)])
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        # passive_dns should be populated from the first call
        assert result.raw_stats.get("passive_dns"), "passive_dns should be present when rt=2 has data"

    def test_hash_body_404_returns_no_data(self) -> None:
        """Hash lookup with body status_code '404' returns EnrichmentResult(verdict='no_data')."""
        ioc = make_sha256_ioc("dd0418c01b7196e967a63fedda70eaf6de4fffb5296a24b9ec13f7a09c2f7bc1")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(NO_DATA_RESPONSE))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"Body '404' must return EnrichmentResult, got {type(result).__name__}: {result!r}"
        )
        assert result.verdict == "no_data"

    def test_hash_body_404_returns_empty_raw_stats(self) -> None:
        """Hash lookup with body status_code '404' returns empty raw_stats."""
        ioc = make_sha256_ioc("dd0418c01b7196e967a63fedda70eaf6de4fffb5296a24b9ec13f7a09c2f7bc1")

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=_mock_get_returning(NO_DATA_RESPONSE))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats == {}


# ===================================================================
# TestHTTPErrors
# ===================================================================

class TestHTTPErrors:

    def test_http_429_ip_returns_enrichment_error(self) -> None:
        """HTTP 429 for IP lookup -> EnrichmentError('HTTP 429')."""
        ioc = make_ipv4_ioc()
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        http_err = requests.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status = MagicMock(side_effect=http_err)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError), (
            f"HTTP 429 must return EnrichmentError, got {type(result).__name__}: {result!r}"
        )
        assert result.provider == "ThreatMiner"
        assert "429" in result.error

    def test_http_403_ip_returns_enrichment_error(self) -> None:
        """HTTP 403 for IP lookup -> EnrichmentError('HTTP 403')."""
        ioc = make_ipv4_ioc()
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        http_err = requests.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status = MagicMock(side_effect=http_err)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert "403" in result.error

    def test_unexpected_exception_ip_returns_enrichment_error(self) -> None:
        """Unexpected exception for IP lookup -> EnrichmentError('Unexpected error')."""
        ioc = make_ipv4_ioc()

        adapter = _make_adapter()
        mock_adapter_session(adapter, side_effect=RuntimeError("boom"))
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert "Unexpected" in result.error or "unexpected" in result.error.lower()

    def test_http_429_domain_first_call_skips_second(self) -> None:
        """HTTP 429 on domain's first API call (rt=2) -> return error, do NOT make second call."""
        ioc = make_domain_ioc()
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        http_err = requests.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status = MagicMock(side_effect=http_err)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError), (
            f"HTTP 429 on first domain call must return EnrichmentError, got {type(result).__name__}"
        )
        assert "429" in result.error
        assert adapter._session.get.call_count == 1, (
            f"After 429 on first domain call, must NOT make second call. Got {adapter._session.get.call_count} calls."
        )
