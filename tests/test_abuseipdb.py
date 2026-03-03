"""Tests for AbuseIPDB API adapter.

Tests IP lookups, verdict logic (malicious/suspicious/clean/no_data), error handling,
and all HTTP safety controls (timeout, size cap, no redirects, SSRF allowlist).

Verdict thresholds (abuseConfidenceScore):
  - score >= 75                         -> "malicious"
  - 25 <= score < 75                    -> "suspicious"
  - score < 25 AND totalReports > 0     -> "clean"
  - totalReports == 0                   -> "no_data"

Auth header: capital 'Key' with 'Accept: application/json' (required to avoid HTML response).

AbuseIPDB does NOT use 404 for unknown IPs — always 200 with score=0.
detection_count = totalReports, total_engines = numDistinctUsers.

HTTP 429 rate limit -> specific EnrichmentError("Rate limit exceeded (429)").

All HTTP calls are mocked using unittest.mock.patch -- no real API calls.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import requests
import requests.exceptions

from app.pipeline.models import IOC, IOCType
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.adapters.abuseipdb import AbuseIPDBAdapter
from app.enrichment.http_safety import MAX_RESPONSE_BYTES
from app.enrichment.provider import Provider


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


def _make_mock_get_response(status_code: int, body: dict | None = None) -> MagicMock:
    """Build a mock requests.Response for GET requests."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if body is not None:
        raw_bytes = json.dumps(body).encode()
        mock_resp.iter_content = MagicMock(return_value=iter([raw_bytes]))
    if status_code >= 400:
        http_err = requests.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status = MagicMock(side_effect=http_err)
    else:
        mock_resp.raise_for_status = MagicMock()
    return mock_resp


def _make_adapter(
    api_key: str = TEST_API_KEY,
    allowed_hosts: list[str] | None = None,
) -> AbuseIPDBAdapter:
    if allowed_hosts is None:
        allowed_hosts = ALLOWED_HOSTS
    return AbuseIPDBAdapter(api_key=api_key, allowed_hosts=allowed_hosts)


class TestAbuseIPDBProtocol:
    """Tests that AbuseIPDBAdapter satisfies the Provider protocol contract."""

    def test_name(self) -> None:
        """AbuseIPDBAdapter.name must equal 'AbuseIPDB'."""
        assert AbuseIPDBAdapter.name == "AbuseIPDB"

    def test_requires_api_key_true(self) -> None:
        """AbuseIPDBAdapter.requires_api_key must be True (free-key provider)."""
        assert AbuseIPDBAdapter.requires_api_key is True

    def test_supported_types_contains_ipv4(self) -> None:
        """IOCType.IPV4 must be in AbuseIPDBAdapter.supported_types."""
        assert IOCType.IPV4 in AbuseIPDBAdapter.supported_types

    def test_supported_types_contains_ipv6(self) -> None:
        """IOCType.IPV6 must be in AbuseIPDBAdapter.supported_types."""
        assert IOCType.IPV6 in AbuseIPDBAdapter.supported_types

    def test_supported_types_excludes_domain(self) -> None:
        """IOCType.DOMAIN must NOT be in AbuseIPDBAdapter.supported_types."""
        assert IOCType.DOMAIN not in AbuseIPDBAdapter.supported_types

    def test_supported_types_excludes_md5(self) -> None:
        """IOCType.MD5 must NOT be in AbuseIPDBAdapter.supported_types."""
        assert IOCType.MD5 not in AbuseIPDBAdapter.supported_types

    def test_supported_types_excludes_url(self) -> None:
        """IOCType.URL must NOT be in AbuseIPDBAdapter.supported_types."""
        assert IOCType.URL not in AbuseIPDBAdapter.supported_types

    def test_is_configured_true_with_key(self) -> None:
        """is_configured() must return True when api_key is non-empty."""
        adapter = _make_adapter(api_key="somekey")
        assert adapter.is_configured() is True

    def test_is_configured_false_with_empty_key(self) -> None:
        """is_configured() must return False when api_key is empty string."""
        adapter = _make_adapter(api_key="")
        assert adapter.is_configured() is False

    def test_isinstance_provider(self) -> None:
        """AbuseIPDBAdapter instance must satisfy the Provider protocol (isinstance check)."""
        adapter = _make_adapter()
        assert isinstance(adapter, Provider), (
            "AbuseIPDBAdapter must satisfy the Provider protocol via @runtime_checkable"
        )


class TestAbuseIPDBLookup:
    """Tests for AbuseIPDBAdapter.lookup() verdict logic."""

    def test_high_score_returns_malicious(self) -> None:
        """abuseConfidenceScore >= 75 -> verdict 'malicious'."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_get_response(200, ABUSEIPDB_MALICIOUS_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult, got {type(result).__name__}: {result!r}"
        )
        assert result.provider == "AbuseIPDB"
        assert result.verdict == "malicious"

    def test_medium_score_returns_suspicious(self) -> None:
        """25 <= abuseConfidenceScore < 75 -> verdict 'suspicious'."""
        ioc = IOC(type=IOCType.IPV4, value="5.6.7.8", raw_match="5.6.7.8")
        mock_resp = _make_mock_get_response(200, ABUSEIPDB_SUSPICIOUS_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.provider == "AbuseIPDB"
        assert result.verdict == "suspicious"

    def test_low_score_with_reports_returns_clean(self) -> None:
        """score < 25 AND totalReports > 0 -> verdict 'clean'."""
        ioc = IOC(type=IOCType.IPV4, value="9.10.11.12", raw_match="9.10.11.12")
        mock_resp = _make_mock_get_response(200, ABUSEIPDB_CLEAN_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.provider == "AbuseIPDB"
        assert result.verdict == "clean"

    def test_zero_reports_returns_no_data(self) -> None:
        """totalReports == 0 -> verdict 'no_data' (not in database)."""
        ioc = IOC(type=IOCType.IPV4, value="192.0.2.1", raw_match="192.0.2.1")
        mock_resp = _make_mock_get_response(200, ABUSEIPDB_NO_DATA_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.provider == "AbuseIPDB"
        assert result.verdict == "no_data"

    def test_detection_count_equals_total_reports(self) -> None:
        """detection_count must equal totalReports from response."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_get_response(200, ABUSEIPDB_MALICIOUS_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        expected_reports = ABUSEIPDB_MALICIOUS_RESPONSE["data"]["totalReports"]
        assert result.detection_count == expected_reports

    def test_total_engines_equals_num_distinct_users(self) -> None:
        """total_engines must equal numDistinctUsers from response."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_get_response(200, ABUSEIPDB_MALICIOUS_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        expected_users = ABUSEIPDB_MALICIOUS_RESPONSE["data"]["numDistinctUsers"]
        assert result.total_engines == expected_users

    def test_scan_date_is_last_reported_at(self) -> None:
        """scan_date must equal data.lastReportedAt from response."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_get_response(200, ABUSEIPDB_MALICIOUS_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        expected_date = ABUSEIPDB_MALICIOUS_RESPONSE["data"]["lastReportedAt"]
        assert result.scan_date == expected_date

    def test_raw_stats_content(self) -> None:
        """200 response -> raw_stats contains expected keys."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_get_response(200, ABUSEIPDB_MALICIOUS_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        for key in ("abuseConfidenceScore", "totalReports", "numDistinctUsers",
                    "countryCode", "isp", "usageType", "lastReportedAt", "isWhitelisted"):
            assert key in result.raw_stats, f"raw_stats missing key: {key!r}"

    def test_raw_stats_values_match_response(self) -> None:
        """raw_stats values must match response data fields."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_get_response(200, ABUSEIPDB_SUSPICIOUS_RESPONSE)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        data = ABUSEIPDB_SUSPICIOUS_RESPONSE["data"]
        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["abuseConfidenceScore"] == data["abuseConfidenceScore"]
        assert result.raw_stats["totalReports"] == data["totalReports"]
        assert result.raw_stats["countryCode"] == data["countryCode"]
        assert result.raw_stats["isp"] == data["isp"]

    def test_ipv6_lookup_works(self) -> None:
        """IPv6 IOC with high confidence score -> verdict 'malicious'."""
        ipv6 = "2001:db8::bad"
        ioc = IOC(type=IOCType.IPV6, value=ipv6, raw_match=ipv6)
        response_body = _make_response_body(
            abuse_confidence_score=80,
            total_reports=25,
            ip_address=ipv6,
        )
        mock_resp = _make_mock_get_response(200, response_body)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"

    def test_score_boundary_75_is_malicious(self) -> None:
        """Boundary: score == 75 -> verdict 'malicious' (threshold is >=75)."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        response_body = _make_response_body(
            abuse_confidence_score=75,
            total_reports=5,
        )
        mock_resp = _make_mock_get_response(200, response_body)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"

    def test_score_boundary_25_is_suspicious(self) -> None:
        """Boundary: score == 25 -> verdict 'suspicious' (threshold is >=25 and <75)."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        response_body = _make_response_body(
            abuse_confidence_score=25,
            total_reports=5,
        )
        mock_resp = _make_mock_get_response(200, response_body)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "suspicious"

    def test_auth_header_uses_capital_key(self) -> None:
        """CRITICAL: AbuseIPDB auth header must be capital 'Key' (not lowercase 'key')."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_get_response(200, ABUSEIPDB_NO_DATA_RESPONSE)

        with patch("requests.get", return_value=mock_resp) as mock_get:
            _make_adapter(api_key="myapikey").lookup(ioc)

        call_kwargs = mock_get.call_args.kwargs
        headers = call_kwargs.get("headers", {})
        assert "Key" in headers, (
            f"AbuseIPDB auth header must use capital 'Key', got headers: {headers}"
        )
        assert headers["Key"] == "myapikey"
        assert "key" not in headers, "Header must be capital 'Key', not lowercase 'key'"

    def test_accept_header_present(self) -> None:
        """'Accept: application/json' header must be included to avoid HTML response."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_get_response(200, ABUSEIPDB_NO_DATA_RESPONSE)

        with patch("requests.get", return_value=mock_resp) as mock_get:
            _make_adapter().lookup(ioc)

        call_kwargs = mock_get.call_args.kwargs
        headers = call_kwargs.get("headers", {})
        assert headers.get("Accept") == "application/json", (
            "AbuseIPDB requires 'Accept: application/json' or it may return HTML"
        )

    def test_no_redirect_flag(self) -> None:
        """SEC-06: allow_redirects must be False for all requests."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_get_response(200, ABUSEIPDB_NO_DATA_RESPONSE)

        with patch("requests.get", return_value=mock_resp) as mock_get:
            _make_adapter().lookup(ioc)

        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs.get("allow_redirects") is False, (
            "SEC-06: allow_redirects must be False"
        )


class TestAbuseIPDBErrors:
    """Tests for error handling in AbuseIPDBAdapter.lookup()."""

    def test_unsupported_type_domain(self) -> None:
        """DOMAIN IOC -> EnrichmentError, provider='AbuseIPDB', error contains 'Unsupported'."""
        ioc = IOC(type=IOCType.DOMAIN, value="evil.com", raw_match="evil.com")

        result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "AbuseIPDB"
        assert "unsupported" in result.error.lower() or "Unsupported" in result.error

    def test_unsupported_type_url(self) -> None:
        """URL IOC -> EnrichmentError (URLs not supported by AbuseIPDB IP endpoint)."""
        ioc = IOC(type=IOCType.URL, value="http://evil.com/path", raw_match="http://evil.com/path")

        result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "AbuseIPDB"

    def test_timeout(self) -> None:
        """Network timeout -> EnrichmentError with 'Timeout' in error."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")

        with patch("requests.get", side_effect=requests.exceptions.Timeout("timed out")):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "AbuseIPDB"
        assert "timeout" in result.error.lower() or "Timeout" in result.error

    def test_http_500(self) -> None:
        """HTTP 500 -> EnrichmentError with 'HTTP 500' in error."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_get_response(500)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "AbuseIPDB"
        assert "HTTP 500" in result.error

    def test_rate_limit_429_returns_specific_message(self) -> None:
        """HTTP 429 -> EnrichmentError with 'Rate limit exceeded (429)' message."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        mock_resp = _make_mock_get_response(429)

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "AbuseIPDB"
        assert "429" in result.error
        assert "rate limit" in result.error.lower() or "Rate limit" in result.error

    def test_ssrf_validation_blocks_disallowed_host(self) -> None:
        """Adapter with allowed_hosts=[] -> EnrichmentError before network call."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
        adapter = AbuseIPDBAdapter(api_key=TEST_API_KEY, allowed_hosts=[])

        with patch("requests.get") as mock_get:
            mock_get.side_effect = AssertionError("Should not reach network")
            result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError), (
            "Expected EnrichmentError when host not in allowed_hosts (SSRF check)"
        )
        assert (
            "SSRF" in result.error
            or "allowed" in result.error.lower()
            or "allowlist" in result.error.lower()
        )

    def test_response_size_limit(self) -> None:
        """SEC-05: Responses exceeding 1 MB must be rejected with EnrichmentError."""
        ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")

        oversized_chunk = b"x" * (MAX_RESPONSE_BYTES + 1)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.iter_content = MagicMock(return_value=iter([oversized_chunk]))

        with patch("requests.get", return_value=mock_resp):
            result = _make_adapter().lookup(ioc)

        assert isinstance(result, EnrichmentError), (
            f"Expected EnrichmentError for oversized response, got {type(result).__name__}"
        )


class TestAllowedHosts:
    """Integration test: SSRF allowlist must include AbuseIPDB hostname."""

    def test_config_allows_abuseipdb(self) -> None:
        """'api.abuseipdb.com' must be in Config.ALLOWED_API_HOSTS (SSRF allowlist)."""
        from app.config import Config
        assert "api.abuseipdb.com" in Config.ALLOWED_API_HOSTS, (
            "api.abuseipdb.com missing from ALLOWED_API_HOSTS — "
            "AbuseIPDBAdapter will always fail SSRF validation in production"
        )
