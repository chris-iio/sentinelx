"""Tests for EmailRep email reputation adapter.

Contract tests (shared protocol, safety controls, and registry coverage) are
added separately in test_adapter_contract.py. This file pins EmailRep-specific
API shape, auth headers, verdict mapping, and flattened raw_stats.

All HTTP calls are mocked; no real EmailRep API calls are made.
"""
from __future__ import annotations

from app.enrichment.adapters.emailrep import EmailRepAdapter
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType
from tests.helpers import make_domain_ioc, make_mock_response, mock_adapter_session


ALLOWED_HOSTS = ["emailrep.io"]
TEST_API_KEY = "test-emailrep-key-123"


def make_email_ioc(value: str = "attacker@evil.com") -> IOC:
    """Build an email IOC for EmailRep adapter tests."""
    return IOC(type=IOCType.EMAIL, value=value, raw_match=value)


def _make_adapter(
    api_key: str = TEST_API_KEY,
    allowed_hosts: list[str] | None = None,
) -> EmailRepAdapter:
    if allowed_hosts is None:
        allowed_hosts = ALLOWED_HOSTS
    return EmailRepAdapter(api_key=api_key, allowed_hosts=allowed_hosts)


EMAILREP_MALICIOUS_RESPONSE = {
    "email": "attacker@evil.com",
    "reputation": "low",
    "suspicious": True,
    "references": 4,
    "details": {
        "blacklisted": True,
        "malicious_activity": True,
        "malicious_activity_recent": True,
        "credentials_leaked": True,
        "credentials_leaked_recent": True,
        "data_breach": True,
        "first_seen": "01/02/2024",
        "last_seen": "04/05/2024",
        "domain_exists": True,
        "domain_reputation": "low",
        "new_domain": True,
        "suspicious_tld": False,
        "spam": True,
        "free_provider": False,
        "disposable": False,
        "deliverable": True,
        "accept_all": False,
        "valid_mx": True,
        "spoofable": True,
        "spf_strict": False,
        "dmarc_enforced": False,
        "profiles": [],
    },
}

EMAILREP_SUSPICIOUS_RESPONSE = {
    "email": "temp@throwaway.example",
    "reputation": "low",
    "suspicious": True,
    "references": 1,
    "details": {
        "blacklisted": False,
        "malicious_activity": False,
        "malicious_activity_recent": False,
        "credentials_leaked": False,
        "credentials_leaked_recent": False,
        "data_breach": False,
        "first_seen": "never",
        "last_seen": "never",
        "domain_exists": True,
        "domain_reputation": "low",
        "new_domain": True,
        "suspicious_tld": True,
        "spam": False,
        "free_provider": False,
        "disposable": True,
        "deliverable": False,
        "accept_all": False,
        "valid_mx": False,
        "spoofable": True,
        "spf_strict": False,
        "dmarc_enforced": False,
        "profiles": [],
    },
}

EMAILREP_CLEAN_RESPONSE = {
    "email": "bill@microsoft.com",
    "reputation": "high",
    "suspicious": False,
    "references": 79,
    "details": {
        "blacklisted": False,
        "malicious_activity": False,
        "malicious_activity_recent": False,
        "credentials_leaked": False,
        "credentials_leaked_recent": False,
        "data_breach": False,
        "first_seen": "07/01/2008",
        "last_seen": "05/24/2019",
        "domain_exists": True,
        "domain_reputation": "high",
        "new_domain": False,
        "suspicious_tld": False,
        "spam": False,
        "free_provider": False,
        "disposable": False,
        "deliverable": True,
        "accept_all": True,
        "valid_mx": True,
        "spoofable": False,
        "spf_strict": True,
        "dmarc_enforced": True,
        "profiles": ["linkedin", "twitter"],
    },
}

EMAILREP_NO_DATA_RESPONSE = {
    "email": "unknown@example.net",
    "reputation": "none",
    "suspicious": False,
    "references": 0,
    "details": {
        "first_seen": "never",
        "last_seen": "never",
        "domain_exists": True,
        "domain_reputation": "n/a",
        "profiles": [],
    },
}


class TestEmailRepLookup:
    """Tests for EmailRepAdapter.lookup() verdict logic."""

    def test_high_confidence_abuse_flags_return_malicious(self) -> None:
        """blacklisted/malicious/recent credential flags -> malicious verdict."""
        ioc = make_email_ioc("attacker@evil.com")
        mock_resp = make_mock_response(200, EMAILREP_MALICIOUS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.provider == "EmailRep"
        assert result.verdict == "malicious"
        assert result.detection_count > 0
        assert result.total_engines == 1
        assert result.scan_date == "04/05/2024"
        assert result.raw_stats["reputation"] == "low"
        assert result.raw_stats["suspicious"] is True
        assert result.raw_stats["references"] == 4
        assert result.raw_stats["domain_reputation"] == "low"
        assert result.raw_stats["profiles"] == []
        assert result.raw_stats["risk_flags"] == [
            "blacklisted",
            "malicious_activity",
            "malicious_activity_recent",
            "credentials_leaked",
            "credentials_leaked_recent",
            "data_breach",
            "new_domain",
            "spam",
            "spoofable",
        ]

    def test_risky_but_not_confirmed_abuse_flags_return_suspicious(self) -> None:
        """Low reputation and disposable/deliverability flags -> suspicious, not malicious."""
        ioc = make_email_ioc("temp@throwaway.example")
        mock_resp = make_mock_response(200, EMAILREP_SUSPICIOUS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.provider == "EmailRep"
        assert result.verdict == "suspicious"
        assert result.detection_count > 0
        assert result.raw_stats["risk_flags"] == [
            "new_domain",
            "suspicious_tld",
            "disposable",
            "deliverable_false",
            "valid_mx_false",
            "spoofable",
        ]

    def test_high_reputation_without_risk_flags_returns_clean(self) -> None:
        """High reputation with no risk flags -> clean verdict."""
        ioc = make_email_ioc("bill@microsoft.com")
        mock_resp = make_mock_response(200, EMAILREP_CLEAN_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.provider == "EmailRep"
        assert result.verdict == "clean"
        assert result.detection_count == 0
        assert result.total_engines == 1
        assert result.raw_stats["risk_flags"] == []
        assert result.raw_stats["profiles"] == ["linkedin", "twitter"]
        assert result.raw_stats["domain_reputation"] == "high"

    def test_no_reputation_response_returns_no_data(self) -> None:
        """reputation='none' with no risk flags -> no_data, not clean."""
        ioc = make_email_ioc("unknown@example.net")
        mock_resp = make_mock_response(200, EMAILREP_NO_DATA_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.provider == "EmailRep"
        assert result.verdict == "no_data"
        assert result.detection_count == 0
        assert result.total_engines == 1
        assert result.raw_stats["reputation"] == "none"
        assert result.raw_stats["risk_flags"] == []

    def test_thin_response_returns_no_data_without_raising(self) -> None:
        """Malformed/thin JSON should degrade to no_data instead of raising."""
        ioc = make_email_ioc("thin@example.net")
        mock_resp = make_mock_response(200, {"email": "thin@example.net"})

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.provider == "EmailRep"
        assert result.verdict == "no_data"
        assert result.raw_stats["reputation"] == "none"
        assert result.raw_stats["suspicious"] is False
        assert result.raw_stats["references"] == 0
        assert result.raw_stats["risk_flags"] == []
        assert result.raw_stats["profiles"] == []

    def test_unsupported_ioc_type_returns_error_without_network_call(self) -> None:
        """Non-email IOCs are rejected by the adapter type guard."""
        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, EMAILREP_CLEAN_RESPONSE))

        result = adapter.lookup(make_domain_ioc("evil.com"))

        assert isinstance(result, EnrichmentError)
        assert result.provider == "EmailRep"
        assert result.error == "Unsupported type"
        adapter._session.get.assert_not_called()

    def test_http_401_returns_enrichment_error(self) -> None:
        """Invalid EmailRep keys surface as HTTP 401 EnrichmentError via safe_request."""
        ioc = make_email_ioc("attacker@evil.com")
        adapter = _make_adapter(api_key="bad-key")
        mock_adapter_session(adapter, response=make_mock_response(401, {"error": "invalid key"}))

        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert result.provider == "EmailRep"
        assert result.error == "HTTP 401"


class TestEmailRepRequestContract:
    """Tests for EmailRep request shape and adapter configuration."""

    def test_is_key_gated(self) -> None:
        """EmailRep is configured only when an API key is present."""
        assert _make_adapter(api_key="configured-key").is_configured() is True
        assert _make_adapter(api_key="").is_configured() is False

    def test_supported_types_email_only(self) -> None:
        """EmailRep supports email IOCs only."""
        adapter = _make_adapter()
        assert adapter.supported_types == frozenset({IOCType.EMAIL})

    def test_auth_headers_use_documented_key_header_and_user_agent(self) -> None:
        """EmailRep docs require Key auth header and a non-empty User-Agent."""
        adapter = _make_adapter(api_key="my-emailrep-key")
        headers = dict(adapter._session.headers)

        assert headers["Key"] == "my-emailrep-key"
        assert headers["User-Agent"] == "SentinelX"
        assert "Authorization" not in headers

    def test_lookup_url_encodes_email_value(self) -> None:
        """EmailRep query URL is https://emailrep.io/{url-encoded-email}."""
        ioc = make_email_ioc("user+tag@example.com")
        adapter = _make_adapter()
        mock_adapter_session(adapter, response=make_mock_response(200, EMAILREP_CLEAN_RESPONSE))

        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        adapter._session.get.assert_called_once()
        requested_url = adapter._session.get.call_args.args[0]
        assert requested_url == "https://emailrep.io/user%2Btag%40example.com"
