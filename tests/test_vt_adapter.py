"""Tests for VirusTotal API v3 adapter — verdict logic, endpoint mapping, and parsing.

Contract tests (protocol, error handling, safety controls) are in test_adapter_contract.py.

All HTTP calls are mocked using unittest.mock.patch — no real API calls.
"""
from __future__ import annotations

import base64
import builtins
import inspect
from types import MappingProxyType


from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.enrichment.adapters.virustotal import (
    VTAdapter,
    _parse_response,
    _trim_base64_padding,
    _virustotal_result,
)
from tests.helpers import (
    make_mock_response,
    make_domain_ioc,
    make_ipv4_ioc,
    make_md5_ioc,
    make_sha1_ioc,
    make_sha256_ioc,
    make_url_ioc,
    mock_adapter_session,
)


ALLOWED_HOSTS = ["www.virustotal.com"]
FAKE_API_KEY = "test-api-key-abc123"

VT_IP_RESPONSE = {
    "data": {
        "type": "ip_address",
        "id": "1.2.3.4",
        "attributes": {
            "last_analysis_stats": {
                "malicious": 5,
                "suspicious": 0,
                "harmless": 60,
                "undetected": 8,
                "timeout": 0,
            },
            "last_analysis_date": 1700000000,
        },
    }
}

VT_CLEAN_RESPONSE = {
    "data": {
        "type": "domain",
        "id": "example.com",
        "attributes": {
            "last_analysis_stats": {
                "malicious": 0,
                "suspicious": 0,
                "harmless": 70,
                "undetected": 3,
                "timeout": 0,
            },
            "last_analysis_date": 1700000000,
        },
    }
}

VT_HASH_RESPONSE = {
    "data": {
        "type": "file",
        "id": "abc123",
        "attributes": {
            "last_analysis_stats": {
                "malicious": 10,
                "suspicious": 2,
                "harmless": 55,
                "undetected": 3,
                "timeout": 0,
            },
            "last_analysis_date": 1700000000,
        },
    }
}




def _make_adapter() -> VTAdapter:
    return VTAdapter(api_key=FAKE_API_KEY, allowed_hosts=ALLOWED_HOSTS)


def test_supported_types_derive_from_endpoint_map() -> None:
    """Supported VT types should stay locked to the endpoint map keys."""
    from app.enrichment.adapters.virustotal import ENDPOINT_MAP

    assert isinstance(ENDPOINT_MAP, MappingProxyType)
    assert VTAdapter.supported_types == frozenset(ENDPOINT_MAP)


class TestLookupSuccess:
    def test_lookup_ipv4_success(self) -> None:
        ioc = make_ipv4_ioc("1.2.3.4")
        mock_resp = make_mock_response(200, VT_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)

        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "malicious"
        assert result.detection_count == 5
        assert result.provider == "VirusTotal"
        assert result.scan_date is not None
        # scan_date must be ISO8601
        assert "T" in result.scan_date

    def test_lookup_ipv4_uses_correct_endpoint(self) -> None:
        ioc = make_ipv4_ioc("1.2.3.4")
        mock_resp = make_mock_response(200, VT_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)

        adapter.lookup(ioc)

        call_url = adapter._session.get.call_args[0][0]
        assert "/ip_addresses/1.2.3.4" in call_url

    def test_lookup_domain_success(self) -> None:
        ioc = make_domain_ioc("example.com")
        mock_resp = make_mock_response(200, VT_CLEAN_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)

        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.verdict == "clean"
        call_url = adapter._session.get.call_args[0][0]
        assert "/domains/example.com" in call_url

    def test_lookup_url_uses_base64_id(self) -> None:
        url_value = "https://evil.com/malware"
        expected_id = base64.urlsafe_b64encode(url_value.encode()).decode().strip("=")
        ioc = make_url_ioc(url_value)
        mock_resp = make_mock_response(200, VT_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)

        adapter.lookup(ioc)

        call_url = adapter._session.get.call_args[0][0]
        # Must use base64 ID — never the raw URL
        assert f"/urls/{expected_id}" in call_url
        assert "evil.com" not in call_url

    def test_url_id_padding_trim_uses_suffix_scan_without_strip(self) -> None:
        class NoStripBase64(str):
            def strip(self, *_args, **_kwargs):
                raise AssertionError("VT URL id padding trim should not use generic strip")

        assert _trim_base64_padding(NoStripBase64("YWJjZA==")) == "YWJjZA"
        assert _trim_base64_padding(NoStripBase64("YWJjZA")) == "YWJjZA"
        assert "strip" not in _trim_base64_padding.__code__.co_names

    def test_lookup_hash_sha256(self) -> None:
        sha256 = "a" * 64
        ioc = make_sha256_ioc(sha256)
        mock_resp = make_mock_response(200, VT_HASH_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)

        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        call_url = adapter._session.get.call_args[0][0]
        assert f"/files/{sha256}" in call_url

    def test_lookup_md5_uses_files_endpoint(self) -> None:
        md5 = "d" * 32
        ioc = make_md5_ioc(md5)
        mock_resp = make_mock_response(200, VT_HASH_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)

        adapter.lookup(ioc)

        call_url = adapter._session.get.call_args[0][0]
        assert f"/files/{md5}" in call_url

    def test_lookup_sha1_uses_files_endpoint(self) -> None:
        sha1 = "e" * 40
        ioc = make_sha1_ioc(sha1)
        mock_resp = make_mock_response(200, VT_HASH_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)

        adapter.lookup(ioc)

        call_url = adapter._session.get.call_args[0][0]
        assert f"/files/{sha1}" in call_url

    def test_total_engine_count_does_not_use_sum_helper(self, monkeypatch) -> None:
        """VT stats parsing should compute engine totals in the stats scan."""
        class NoItemsDict(dict):
            def items(self):
                raise AssertionError("VT stats parsing should scan stat keys directly")

        ioc = make_ipv4_ioc("1.2.3.4")
        body = {
            "data": {
                "type": "ip_address",
                "id": "1.2.3.4",
                "attributes": {
                    "last_analysis_stats": NoItemsDict(
                        {
                            "malicious": 5,
                            "suspicious": 0,
                            "harmless": 60,
                            "undetected": 8,
                            "timeout": 0,
                        }
                    ),
                    "last_analysis_date": 1700000000,
                },
            }
        }

        def fail_sum(*_args, **_kwargs):
            raise AssertionError("VT stats parsing should not rescan via sum")

        monkeypatch.setattr(builtins, "sum", fail_sum)

        result = _parse_response(ioc, body)

        assert isinstance(result, EnrichmentResult)
        assert result.detection_count == 5
        assert result.total_engines == 73

    def test_engine_status_exclusions_use_static_frozenset(self) -> None:
        """VT stats parsing should not rebuild excluded engine-status sets."""
        from app.enrichment.adapters import virustotal

        source = inspect.getsource(virustotal._parse_response)

        assert '{"timeout", "type-unsupported"}' not in source
        assert isinstance(virustotal._EXCLUDED_ENGINE_STATUSES, frozenset)
        assert virustotal._EXCLUDED_ENGINE_STATUSES == frozenset(
            ("timeout", "type-unsupported")
        )

    def test_top_detections_do_not_allocate_values_view(self) -> None:
        """VT top detections should scan analysis result keys directly."""

        class NoValuesDict(dict):
            def values(self):
                raise AssertionError("VT top detection parsing should not allocate a values view")

        ioc = make_ipv4_ioc("1.2.3.4")
        body = {
            "data": {
                "attributes": {
                    "last_analysis_stats": {"malicious": 1},
                    "last_analysis_results": NoValuesDict({
                        "EngineA": {"category": "malicious", "result": "Trojan.A"},
                        "EngineB": {"category": "malicious", "result": "Trojan.A"},
                        "EngineC": {"category": "malicious", "result": "Dropper.C"},
                    }),
                },
            },
        }
        mock_resp = make_mock_response(200, body)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)
        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentResult)
        assert result.raw_stats["top_detections"] == ["Trojan.A", "Dropper.C"]

    def test_missing_analysis_maps_avoid_eager_default_dicts(self) -> None:
        """Missing VT analysis maps should not allocate through dict.get defaults."""
        class NoDefaultAttrs(dict):
            def get(self, key, default=None):
                if key in {"last_analysis_stats", "last_analysis_results"} and default is not None:
                    raise AssertionError("VT analysis maps should avoid eager default dict allocation")
                return super().get(key, default)

        body = {
            "data": {
                "attributes": NoDefaultAttrs({
                    "last_analysis_date": 1700000000,
                }),
            },
        }

        result = _parse_response(make_ipv4_ioc("1.2.3.4"), body)

        assert result.verdict == "no_data"
        assert result.detection_count == 0
        assert result.total_engines == 0
        assert result.raw_stats["top_detections"] == []
        assert result.raw_stats["reputation"] == 0

    def test_result_helper_preserves_provider_envelope(self) -> None:
        """Parsed VT results should keep the provider envelope centralized."""
        ioc = make_ipv4_ioc("1.2.3.4")
        raw_stats = {"malicious": 5, "top_detections": ["Example"]}

        result = _virustotal_result(
            ioc=ioc,
            verdict="malicious",
            detection_count=5,
            total_engines=73,
            scan_date="2023-11-14T22:13:20+00:00",
            raw_stats=raw_stats,
        )

        assert result.ioc is ioc
        assert result.provider == "VirusTotal"
        assert result.verdict == "malicious"
        assert result.detection_count == 5
        assert result.total_engines == 73
        assert result.scan_date == "2023-11-14T22:13:20+00:00"
        assert result.raw_stats is raw_stats


class TestLookupErrors:
    def test_lookup_404_returns_no_data(self) -> None:
        ioc = make_ipv4_ioc("10.0.0.1")
        mock_resp = make_mock_response(404)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)

        result = adapter.lookup(ioc)

        # 404 = VT has no record — must be EnrichmentResult, NOT EnrichmentError
        assert isinstance(result, EnrichmentResult), (
            f"Expected EnrichmentResult for 404, got {type(result).__name__}: "
            f"{result!r}"
        )
        assert result.verdict == "no_data"
        assert result.detection_count == 0
        assert result.total_engines == 0
        assert result.scan_date is None
        assert result.raw_stats == {}
        assert 'no_data_result(ioc, "VirusTotal")' in inspect.getsource(VTAdapter.lookup)

    def test_lookup_429_returns_rate_limit_error(self) -> None:
        ioc = make_ipv4_ioc()
        mock_resp = make_mock_response(429)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)

        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert "Rate limit" in result.error or "429" in result.error

    def test_lookup_401_returns_auth_error(self) -> None:
        ioc = make_ipv4_ioc()
        mock_resp = make_mock_response(401)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)

        result = adapter.lookup(ioc)

        assert isinstance(result, EnrichmentError)
        assert "Authentication" in result.error or "auth" in result.error.lower() or "401" in result.error
class TestHTTPSafetyControls:
    """Verify SEC-04 through SEC-07 HTTP safety controls."""

    def test_no_redirects_enforced(self) -> None:
        """SEC-06: allow_redirects=False must be passed."""
        ioc = make_ipv4_ioc()
        mock_resp = make_mock_response(200, VT_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)

        adapter.lookup(ioc)

        kwargs = adapter._session.get.call_args[1]
        assert kwargs.get("allow_redirects") is False, (
            f"Expected allow_redirects=False (SEC-06), got {kwargs.get('allow_redirects')!r}"
        )

    def test_timeout_params_enforced(self) -> None:
        """SEC-04: timeout=(5, 30) must be passed."""
        ioc = make_ipv4_ioc()
        mock_resp = make_mock_response(200, VT_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)

        adapter.lookup(ioc)

        kwargs = adapter._session.get.call_args[1]
        assert kwargs.get("timeout") == (5, 30), (
            f"Expected timeout=(5, 30) (SEC-04), got {kwargs.get('timeout')!r}"
        )

    def test_stream_enabled(self) -> None:
        """SEC-05 setup: stream=True must be passed."""
        ioc = make_ipv4_ioc()
        mock_resp = make_mock_response(200, VT_IP_RESPONSE)

        adapter = _make_adapter()
        mock_adapter_session(adapter, response=mock_resp)

        adapter.lookup(ioc)

        kwargs = adapter._session.get.call_args[1]
        assert kwargs.get("stream") is True, (
            f"Expected stream=True (SEC-05), got {kwargs.get('stream')!r}"
        )
