"""Tests for OTX AlienVault adapter — verdict logic, type routing, and response parsing.

Contract tests (protocol, error handling, safety controls) are in test_adapter_contract.py.

All HTTP calls are mocked using unittest.mock.patch -- no real API calls.
"""
from __future__ import annotations

import inspect
from types import MappingProxyType

from app.enrichment.models import EnrichmentResult
from app.enrichment.adapters.otx import (
    OTXAdapter,
    _otx_raw_stats,
    _otx_signals,
    _otx_verdict,
    _parse_response,
)
from tests.helpers import (
    make_mock_response,
    mock_adapter_session,
    make_cve_ioc,
    make_domain_ioc,
    make_ipv4_ioc,
    make_ipv6_ioc,
    make_md5_ioc,
    make_sha1_ioc,
    make_sha256_ioc,
    make_url_ioc,
)


ALLOWED_HOSTS = ["otx.alienvault.com"]

OTX_MALICIOUS_RESPONSE = {
    "indicator": "8.8.8.8",
    "type": "IPv4",
    "type_title": "IPv4",
    "reputation": 0,
    "pulse_info": {
        "count": 7,
        "pulses": [],
        "references": [],
        "related": {},
    },
}

OTX_SUSPICIOUS_RESPONSE = {
    "indicator": "1.2.3.4",
    "type": "IPv4",
    "type_title": "IPv4",
    "reputation": 0,
    "pulse_info": {
        "count": 3,
        "pulses": [],
        "references": [],
        "related": {},
    },
}

OTX_NO_DATA_RESPONSE = {
    "indicator": "192.0.2.1",
    "type": "IPv4",
    "type_title": "IPv4",
    "reputation": 0,
    "pulse_info": {
        "count": 0,
        "pulses": [],
        "references": [],
        "related": {},
    },
}

OTX_DOMAIN_RESPONSE = {
    "indicator": "evil.com",
    "type": "domain",
    "type_title": "Domain",
    "reputation": 0,
    "pulse_info": {
        "count": 5,
        "pulses": [],
    },
}

OTX_URL_RESPONSE = {
    "indicator": "http://evil.com/payload.exe",
    "type": "URL",
    "type_title": "URL",
    "reputation": 0,
    "pulse_info": {
        "count": 2,
        "pulses": [],
    },
}

OTX_FILE_RESPONSE = {
    "indicator": "a" * 32,
    "type": "FileHash-MD5",
    "type_title": "FileHash-MD5",
    "reputation": 0,
    "pulse_info": {
        "count": 6,
        "pulses": [],
    },
}

OTX_CVE_RESPONSE = {
    "indicator": "CVE-2021-44228",
    "type": "CVE",
    "type_title": "CVE",
    "reputation": 0,
    "pulse_info": {
        "count": 10,
        "pulses": [],
    },
}

OTX_404_RESPONSE = {"detail": "Not found"}




def _make_adapter(api_key: str = "test-api-key", allowed_hosts: list[str] | None = None) -> OTXAdapter:
    if allowed_hosts is None:
        allowed_hosts = ALLOWED_HOSTS
    return OTXAdapter(api_key=api_key, allowed_hosts=allowed_hosts)


class TestOTXLookup:

    def test_result_helper_preserves_provider_envelope(self) -> None:
        """OTX response branches should share one provider envelope."""
        from app.enrichment.adapters.otx import _otx_result

        ioc = make_ipv4_ioc("8.8.8.8")
        result = _otx_result(
            ioc=ioc,
            provider_name="OTX AlienVault",
            verdict="malicious",
            detection_count=7,
            total_engines=1,
            raw_stats={"pulse_count": 7},
        )

        assert result.ioc is ioc
        assert result.provider == "OTX AlienVault"
        assert result.verdict == "malicious"
        assert result.detection_count == 7
        assert result.total_engines == 1
        assert result.scan_date is None
        assert result.raw_stats == {"pulse_count": 7}

    def test_ipv4_high_pulse_count_returns_malicious(self) -> None:
        """IPv4 with pulse_info.count >= 5 -> verdict=malicious."""
        ioc = make_ipv4_ioc("8.8.8.8")
        mock_resp = make_mock_response(200, OTX_MALICIOUS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult, got {type(result).__name__}: {result!r}"
        )
        assert result.provider == "OTX AlienVault"
        assert result.verdict == "malicious"
        assert result.detection_count == 7

    def test_ipv4_low_pulse_count_returns_suspicious(self) -> None:
        """IPv4 with pulse_info.count 1-4 -> verdict=suspicious."""
        ioc = make_ipv4_ioc("1.2.3.4")
        mock_resp = make_mock_response(200, OTX_SUSPICIOUS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "suspicious"
        assert result.detection_count == 3

    def test_ipv4_zero_pulse_count_returns_no_data(self) -> None:
        """IPv4 with pulse_info.count == 0 -> verdict=no_data."""
        ioc = make_ipv4_ioc("192.0.2.1")
        mock_resp = make_mock_response(200, OTX_NO_DATA_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "no_data"
        assert result.detection_count == 0

    def test_missing_pulse_info_reuses_static_empty_mapping(self) -> None:
        """Missing pulse info should not allocate a per-call default dict."""
        ioc = make_ipv4_ioc("192.0.2.1")

        class NoDefaultBody(dict):
            def get(self, key, default=None):
                if key == "pulse_info" and default is not None:
                    raise AssertionError("missing OTX pulse info should use the shared empty mapping")
                return super().get(key, default)

        result = _parse_response(ioc, NoDefaultBody(), "OTX AlienVault")

        assert result.verdict == "no_data"
        assert result.detection_count == 0
        assert result.raw_stats["pulse_count"] == 0

    def test_parse_response_delegates_verdict_and_raw_stats_helpers(self) -> None:
        """Parser should not own OTX threshold or raw_stats mechanics."""
        source = inspect.getsource(_parse_response)

        assert "_otx_signals(body)" in source
        assert "_otx_verdict(signals.pulse_count)" in source
        assert "_otx_raw_stats(" in source
        assert 'body.get("pulse_info"' not in source
        assert "_MALICIOUS_THRESHOLD" not in source
        assert "_SUSPICIOUS_MIN" not in source
        assert '"pulse_count"' not in source

    def test_signal_helper_preserves_defaults_and_pulse_mapping(self) -> None:
        """OTX response field extraction should live in one signal helper."""
        class NoDefaultBody(dict):
            def get(self, key, default=None):
                expected_defaults = {
                    "pulse_info": None,
                    "reputation": 0,
                    "type_title": "",
                }
                if default != expected_defaults[key]:
                    raise AssertionError("OTX signal defaults should stay provider-specific")
                return super().get(key, default)

        signals = _otx_signals(
            NoDefaultBody({
                "pulse_info": {"count": 4},
                "reputation": None,
                "type_title": None,
            })
        )

        assert signals.pulse_count == 4
        assert signals.reputation == 0
        assert signals.type_title == ""

    def test_verdict_helper_preserves_thresholds(self) -> None:
        """OTX thresholds should remain malicious/suspicious/no-data by pulse count."""
        assert _otx_verdict(5) == "malicious"
        assert _otx_verdict(4) == "suspicious"
        assert _otx_verdict(1) == "suspicious"
        assert _otx_verdict(0) == "no_data"

    def test_raw_stats_helper_preserves_key_order_and_values(self) -> None:
        """Raw stats helper should preserve OTX metadata shape."""
        raw_stats = _otx_raw_stats(
            pulse_count=7,
            reputation=0,
            type_title="IPv4",
        )

        assert list(raw_stats) == ["pulse_count", "reputation", "type_title"]
        assert raw_stats == {
            "pulse_count": 7,
            "reputation": 0,
            "type_title": "IPv4",
        }

    def test_domain_lookup_returns_result(self) -> None:
        """DOMAIN IOC -> GET /api/v1/indicators/domain/{value}/general."""
        ioc = make_domain_ioc("evil.com")
        mock_resp = make_mock_response(200, OTX_DOMAIN_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        call_url = adapter._session.get.call_args[0][0]
        assert "/indicators/domain/" in call_url

    def test_url_lookup_returns_result(self) -> None:
        """URL IOC -> GET /api/v1/indicators/url/{value}/general."""
        ioc = make_url_ioc("http://evil.com/payload.exe")
        mock_resp = make_mock_response(200, OTX_URL_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        call_url = adapter._session.get.call_args[0][0]
        assert "/indicators/url/" in call_url

    def test_md5_hash_maps_to_file_endpoint(self) -> None:
        """MD5 IOC -> GET /api/v1/indicators/file/{value}/general (NOT /md5/)."""
        md5 = "a" * 32
        ioc = make_md5_ioc(md5)
        mock_resp = make_mock_response(200, OTX_FILE_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        call_url = adapter._session.get.call_args[0][0]
        assert "/indicators/file/" in call_url, (
            f"MD5 must map to /indicators/file/ path, got: {call_url}"
        )

    def test_sha1_hash_maps_to_file_endpoint(self) -> None:
        """SHA1 IOC -> GET /api/v1/indicators/file/{value}/general (NOT /sha1/)."""
        sha1 = "a" * 40
        ioc = make_sha1_ioc(sha1)
        mock_resp = make_mock_response(200, OTX_FILE_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        call_url = adapter._session.get.call_args[0][0]
        assert "/indicators/file/" in call_url, (
            f"SHA1 must map to /indicators/file/ path, got: {call_url}"
        )

    def test_sha256_hash_maps_to_file_endpoint(self) -> None:
        """SHA256 IOC -> GET /api/v1/indicators/file/{value}/general (NOT /sha256/)."""
        sha256 = "b" * 64
        ioc = make_sha256_ioc(sha256)
        mock_resp = make_mock_response(200, OTX_FILE_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        call_url = adapter._session.get.call_args[0][0]
        assert "/indicators/file/" in call_url, (
            f"SHA256 must map to /indicators/file/ path, got: {call_url}"
        )

    def test_cve_lookup_returns_malicious(self) -> None:
        """CVE IOC with high pulse count -> GET /api/v1/indicators/cve/{value}/general, verdict=malicious."""
        ioc = make_cve_ioc("CVE-2021-44228")
        mock_resp = make_mock_response(200, OTX_CVE_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"
        call_url = adapter._session.get.call_args[0][0]
        assert "/indicators/cve/" in call_url, (
            f"CVE must map to /indicators/cve/ path, got: {call_url}"
        )

    def test_404_returns_no_data_result_not_error(self) -> None:
        """404 response -> EnrichmentResult(verdict='no_data'), NOT EnrichmentError."""
        ioc = make_ipv4_ioc("192.0.2.1")
        mock_resp = make_mock_response(404, OTX_404_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult), (
            f"404 must return EnrichmentResult (not EnrichmentError), got {type(result).__name__}: {result!r}"
        )
        assert result.verdict == "no_data"
        assert result.detection_count == 0
        assert result.total_engines == 0
        assert result.scan_date is None
        assert result.raw_stats == {}
        assert OTXAdapter._no_data_on_404 is True
        assert "_make_pre_raise_hook" not in inspect.getsource(OTXAdapter)

    def test_raw_stats_contains_expected_keys(self) -> None:
        """200 response -> raw_stats dict contains keys: pulse_count, reputation, type_title."""
        ioc = make_ipv4_ioc("8.8.8.8")
        mock_resp = make_mock_response(200, OTX_MALICIOUS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        for key in ("pulse_count", "reputation", "type_title"):
            assert key in result.raw_stats, f"raw_stats missing key: {key!r}"

    def test_get_uses_otx_api_key_header(self) -> None:
        """GET request must include X-OTX-API-KEY header with the API key."""
        # Headers are set on the persistent session in __init__
        adapter = _make_adapter(api_key="my-otx-key")
        headers = dict(adapter._session.headers)
        assert "X-OTX-API-KEY" in headers, "OTX GET must include X-OTX-API-KEY header"
        assert headers["X-OTX-API-KEY"] == "my-otx-key"

    def test_ipv6_maps_to_ipv6_endpoint(self) -> None:
        """IPv6 IOC -> GET /api/v1/indicators/IPv6/{value}/general."""
        ipv6 = "2001:db8::1"
        ioc = make_ipv6_ioc(ipv6)
        mock_resp = make_mock_response(200, OTX_MALICIOUS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        call_url = adapter._session.get.call_args[0][0]
        assert "/indicators/IPv6/" in call_url

    def test_pulse_count_boundary_exactly_5_is_malicious(self) -> None:
        """Exactly 5 pulses -> malicious (boundary condition)."""
        ioc = make_ipv4_ioc("10.0.0.1")
        body = {**OTX_NO_DATA_RESPONSE, "pulse_info": {"count": 5}}
        mock_resp = make_mock_response(200, body)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"

    def test_pulse_count_boundary_exactly_4_is_suspicious(self) -> None:
        """Exactly 4 pulses -> suspicious (boundary condition, just below malicious threshold)."""
        ioc = make_ipv4_ioc("10.0.0.1")
        body = {**OTX_NO_DATA_RESPONSE, "pulse_info": {"count": 4}}
        mock_resp = make_mock_response(200, body)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "suspicious"

    def test_pulse_count_boundary_exactly_1_is_suspicious(self) -> None:
        """Exactly 1 pulse -> suspicious (just above no_data threshold)."""
        ioc = make_ipv4_ioc("10.0.0.1")
        body = {**OTX_NO_DATA_RESPONSE, "pulse_info": {"count": 1}}
        mock_resp = make_mock_response(200, body)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "suspicious"


class TestOTXTypeMapping:

    def test_supported_types_derive_from_otx_route_map(self) -> None:
        """Supported OTX types should stay locked to the URL route map keys."""
        from app.enrichment.adapters.otx import _OTX_TYPE_MAP

        assert isinstance(_OTX_TYPE_MAP, MappingProxyType)
        assert OTXAdapter.supported_types == frozenset(_OTX_TYPE_MAP)

    def test_ipv4_maps_to_ipv4_string(self) -> None:
        """IOCType.IPV4 -> 'IPv4' in URL path."""
        ioc = make_ipv4_ioc("8.8.8.8")
        mock_resp = make_mock_response(200, OTX_MALICIOUS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        adapter.lookup(ioc)

        call_url = adapter._session.get.call_args[0][0]
        assert "/indicators/IPv4/8.8.8.8/general" in call_url

    def test_ipv6_maps_to_ipv6_string(self) -> None:
        """IOCType.IPV6 -> 'IPv6' in URL path."""
        ipv6 = "2001:db8::1"
        ioc = make_ipv6_ioc(ipv6)
        mock_resp = make_mock_response(200, OTX_MALICIOUS_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        adapter.lookup(ioc)

        call_url = adapter._session.get.call_args[0][0]
        assert "/indicators/IPv6/" in call_url

    def test_domain_maps_to_domain_string(self) -> None:
        """IOCType.DOMAIN -> 'domain' in URL path."""
        ioc = make_domain_ioc("evil.com")
        mock_resp = make_mock_response(200, OTX_DOMAIN_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        adapter.lookup(ioc)

        call_url = adapter._session.get.call_args[0][0]
        assert "/indicators/domain/evil.com/general" in call_url

    def test_url_maps_to_url_string(self) -> None:
        """IOCType.URL -> 'url' in URL path."""
        ioc = make_url_ioc("http://evil.com/payload.exe")
        mock_resp = make_mock_response(200, OTX_URL_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        adapter.lookup(ioc)

        call_url = adapter._session.get.call_args[0][0]
        assert "/indicators/url/" in call_url

    def test_md5_maps_to_file_not_md5(self) -> None:
        """IOCType.MD5 -> 'file' in URL path (NOT 'md5')."""
        md5 = "a" * 32
        ioc = make_md5_ioc(md5)
        mock_resp = make_mock_response(200, OTX_FILE_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        adapter.lookup(ioc)

        call_url = adapter._session.get.call_args[0][0]
        assert "/indicators/file/" in call_url
        assert "/indicators/md5/" not in call_url

    def test_sha1_maps_to_file_not_sha1(self) -> None:
        """IOCType.SHA1 -> 'file' in URL path (NOT 'sha1')."""
        sha1 = "a" * 40
        ioc = make_sha1_ioc(sha1)
        mock_resp = make_mock_response(200, OTX_FILE_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        adapter.lookup(ioc)

        call_url = adapter._session.get.call_args[0][0]
        assert "/indicators/file/" in call_url
        assert "/indicators/sha1/" not in call_url

    def test_sha256_maps_to_file_not_sha256(self) -> None:
        """IOCType.SHA256 -> 'file' in URL path (NOT 'sha256')."""
        sha256 = "b" * 64
        ioc = make_sha256_ioc(sha256)
        mock_resp = make_mock_response(200, OTX_FILE_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        adapter.lookup(ioc)

        call_url = adapter._session.get.call_args[0][0]
        assert "/indicators/file/" in call_url
        assert "/indicators/sha256/" not in call_url

    def test_cve_maps_to_cve_string(self) -> None:
        """IOCType.CVE -> 'cve' in URL path."""
        ioc = make_cve_ioc("CVE-2021-44228")
        mock_resp = make_mock_response(200, OTX_CVE_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        adapter.lookup(ioc)

        call_url = adapter._session.get.call_args[0][0]
        assert "/indicators/cve/CVE-2021-44228/general" in call_url
