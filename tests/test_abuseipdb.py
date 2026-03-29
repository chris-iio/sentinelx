"""Tests for AbuseIPDB API adapter — verdict logic and response parsing.

Contract tests (protocol, error handling, safety controls) are in test_adapter_contract.py.

Verdict thresholds (abuseConfidenceScore):
  - score >= 75                         -> "malicious"
  - 25 <= score < 75                    -> "suspicious"
  - score < 25 AND totalReports > 0     -> "clean"
  - totalReports == 0                   -> "no_data"

All HTTP calls are mocked using unittest.mock.patch -- no real API calls.
"""
from __future__ import annotations

from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.adapters.abuseipdb import AbuseIPDBAdapter
from tests.helpers import (
    make_mock_response,
    mock_adapter_session,
    make_ipv4_ioc,
    make_ipv6_ioc,
)


ALLOWED_HOSTS = ["api.abuseipdb.com"]
TEST_API_KEY = "test-abuseipdb-key-456"

# Sample AbuseIPDB API response bodies (wrapped in data envelope)

def _make_response_body(
    abuse_confidence_score: int,
    total_reports: int,
    num_distinct_users: int = 5,
    country_code: str = "US",
    isp: str = "Test ISP",
    usage_type: str = "Data Center/Web Hosting/Transit",
    last_reported_at: str | None = "2024-01-15T10:00:00+00:00",
    is_whitelisted: bool = False,
    ip_address: str = "1.2.3.4",
) -> dict:
    return {
        "data": {
            "ipAddress": ip_address,
            "isPublic": True,
            "ipVersion": 4,
            "isWhitelisted": is_whitelisted,
            "abuseConfidenceScore": abuse_confidence_score,
            "countryCode": country_code,
            "usageType": usage_type,
            "isp": isp,
            "domain": "example.com",
            "hostnames": [],
            "isTor": False,
            "totalReports": total_reports,
            "numDistinctUsers": num_distinct_users,
            "lastReportedAt": last_reported_at,
        }
    }


ABUSEIPDB_MALICIOUS_RESPONSE = _make_response_body(
    abuse_confidence_score=90,
    total_reports=50,
    num_distinct_users=15,
    country_code="CN",
    isp="Shady ISP",
    last_reported_at="2024-01-15T09:00:00+00:00",
)

ABUSEIPDB_SUSPICIOUS_RESPONSE = _make_response_body(
    abuse_confidence_score=50,
    total_reports=10,
    num_distinct_users=3,
    country_code="RU",
    isp="VPN Provider",
    last_reported_at="2024-01-14T08:00:00+00:00",
)

ABUSEIPDB_CLEAN_RESPONSE = _make_response_body(
    abuse_confidence_score=10,
    total_reports=3,
    num_distinct_users=2,
    country_code="US",
    isp="Comcast",
    last_reported_at="2024-01-10T07:00:00+00:00",
)

ABUSEIPDB_NO_DATA_RESPONSE = _make_response_body(
    abuse_confidence_score=0,
    total_reports=0,
    num_distinct_users=0,
    last_reported_at=None,
)




def _make_adapter(
    api_key: str = TEST_API_KEY,
    allowed_hosts: list[str] | None = None,
) -> AbuseIPDBAdapter:
    if allowed_hosts is None:
        allowed_hosts = ALLOWED_HOSTS
    return AbuseIPDBAdapter(api_key=api_key, allowed_hosts=allowed_hosts)


class TestAbuseIPDBLookup:
    """Tests for AbuseIPDBAdapter.lookup() verdict logic."""

    def test_high_score_returns_malicious(self) -> None:
        """abuseConfidenceScore >= 75 -> verdict 'malicious'."""
        ioc = make_ipv4_ioc("1.2.3.4")
        mock_resp = make_mock_response(200, ABUSEIPDB_MALICIOUS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult, got {type(result).__name__}: {result!r}"
        )
        assert result.provider == "AbuseIPDB"
        assert result.verdict == "malicious"

    def test_medium_score_returns_suspicious(self) -> None:
        """25 <= abuseConfidenceScore < 75 -> verdict 'suspicious'."""
        ioc = make_ipv4_ioc("5.6.7.8")
        mock_resp = make_mock_response(200, ABUSEIPDB_SUSPICIOUS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.provider == "AbuseIPDB"
        assert result.verdict == "suspicious"

    def test_low_score_with_reports_returns_clean(self) -> None:
        """score < 25 AND totalReports > 0 -> verdict 'clean'."""
        ioc = make_ipv4_ioc("9.10.11.12")
        mock_resp = make_mock_response(200, ABUSEIPDB_CLEAN_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.provider == "AbuseIPDB"
        assert result.verdict == "clean"

    def test_zero_reports_returns_no_data(self) -> None:
        """totalReports == 0 -> verdict 'no_data' (not in database)."""
        ioc = make_ipv4_ioc("192.0.2.1")
        mock_resp = make_mock_response(200, ABUSEIPDB_NO_DATA_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.provider == "AbuseIPDB"
        assert result.verdict == "no_data"

    def test_detection_count_equals_total_reports(self) -> None:
        """detection_count must equal totalReports from response."""
        ioc = make_ipv4_ioc("1.2.3.4")
        mock_resp = make_mock_response(200, ABUSEIPDB_MALICIOUS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        expected_reports = ABUSEIPDB_MALICIOUS_RESPONSE["data"]["totalReports"]
        assert result.detection_count == expected_reports

    def test_total_engines_equals_num_distinct_users(self) -> None:
        """total_engines must equal numDistinctUsers from response."""
        ioc = make_ipv4_ioc("1.2.3.4")
        mock_resp = make_mock_response(200, ABUSEIPDB_MALICIOUS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        expected_users = ABUSEIPDB_MALICIOUS_RESPONSE["data"]["numDistinctUsers"]
        assert result.total_engines == expected_users

    def test_scan_date_is_last_reported_at(self) -> None:
        """scan_date must equal data.lastReportedAt from response."""
        ioc = make_ipv4_ioc("1.2.3.4")
        mock_resp = make_mock_response(200, ABUSEIPDB_MALICIOUS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        expected_date = ABUSEIPDB_MALICIOUS_RESPONSE["data"]["lastReportedAt"]
        assert result.scan_date == expected_date

    def test_raw_stats_content(self) -> None:
        """200 response -> raw_stats contains expected keys."""
        ioc = make_ipv4_ioc("1.2.3.4")
        mock_resp = make_mock_response(200, ABUSEIPDB_MALICIOUS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        for key in ("abuseConfidenceScore", "totalReports", "numDistinctUsers",
                    "countryCode", "isp", "usageType", "lastReportedAt", "isWhitelisted"):
            assert key in result.raw_stats, f"raw_stats missing key: {key!r}"

    def test_raw_stats_values_match_response(self) -> None:
        """raw_stats values must match response data fields."""
        ioc = make_ipv4_ioc("1.2.3.4")
        mock_resp = make_mock_response(200, ABUSEIPDB_SUSPICIOUS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        data = ABUSEIPDB_SUSPICIOUS_RESPONSE["data"]
        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["abuseConfidenceScore"] == data["abuseConfidenceScore"]
        assert result.raw_stats["totalReports"] == data["totalReports"]
        assert result.raw_stats["countryCode"] == data["countryCode"]
        assert result.raw_stats["isp"] == data["isp"]

    def test_ipv6_lookup_works(self) -> None:
        """IPv6 IOC with high confidence score -> verdict 'malicious'."""
        ipv6 = "2001:db8::bad"
        ioc = make_ipv6_ioc(ipv6)
        response_body = _make_response_body(
            abuse_confidence_score=80,
            total_reports=25,
            ip_address=ipv6,
        )
        mock_resp = make_mock_response(200, response_body)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"

    def test_score_boundary_75_is_malicious(self) -> None:
        """Boundary: score == 75 -> verdict 'malicious' (threshold is >=75)."""
        ioc = make_ipv4_ioc("1.2.3.4")
        response_body = _make_response_body(
            abuse_confidence_score=75,
            total_reports=5,
        )
        mock_resp = make_mock_response(200, response_body)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"

    def test_score_boundary_25_is_suspicious(self) -> None:
        """Boundary: score == 25 -> verdict 'suspicious' (threshold is >=25 and <75)."""
        ioc = make_ipv4_ioc("1.2.3.4")
        response_body = _make_response_body(
            abuse_confidence_score=25,
            total_reports=5,
        )
        mock_resp = make_mock_response(200, response_body)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "suspicious"

    def test_auth_header_uses_capital_key(self) -> None:
        """CRITICAL: AbuseIPDB auth header must be capital 'Key' (not lowercase 'key')."""
        adapter = _make_adapter(api_key="myapikey")
        # Headers are set on the persistent session in __init__
        headers = dict(adapter._session.headers)
        assert "Key" in headers, (
            f"AbuseIPDB auth header must use capital 'Key', got headers: {headers}"
        )
        assert headers["Key"] == "myapikey"
        assert "key" not in headers, "Header must be capital 'Key', not lowercase 'key'"

    def test_accept_header_present(self) -> None:
        """'Accept: application/json' header must be included to avoid HTML response."""
        adapter = _make_adapter()
        # Accept header is set on the persistent session in __init__
        headers = dict(adapter._session.headers)
        assert headers.get("Accept") == "application/json", (
            "AbuseIPDB requires 'Accept: application/json' or it may return HTML"
        )

    def test_no_redirect_flag(self) -> None:
        """SEC-06: allow_redirects must be False for all requests."""
        ioc = make_ipv4_ioc("1.2.3.4")
        mock_resp = make_mock_response(200, ABUSEIPDB_NO_DATA_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        adapter.lookup(ioc)

        call_kwargs = adapter._session.get.call_args.kwargs
        assert call_kwargs.get("allow_redirects") is False, (
            "SEC-06: allow_redirects must be False"
        )


class TestAbuseIPDBErrors:
    """Tests for adapter-specific error handling in AbuseIPDBAdapter.lookup()."""

    def test_rate_limit_429_returns_specific_message(self) -> None:
        """HTTP 429 -> EnrichmentError with 'Rate limit exceeded (429)' message."""
        ioc = make_ipv4_ioc("1.2.3.4")
        mock_resp = make_mock_response(429)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "AbuseIPDB"
        assert "429" in result.error
        assert "rate limit" in result.error.lower() or "Rate limit" in result.error

