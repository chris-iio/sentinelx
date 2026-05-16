"""Integration tests for Flask routes.

Tests cover:
- Functional behavior of GET / and POST /analyze
- Security properties: 413, 400 (bad host), CSRF, CSP headers, debug=False
- Offline mode: no outbound HTTP calls during extraction (UI-02)
- Online mode: API key check, background enrichment launch, job_id in response
- Polling endpoint: JSON structure, 404 for unknown jobs, result serialization
- Edge cases: empty input, no IOCs, duplicate IOC deduplication
"""
import json
import inspect
from types import MappingProxyType
from unittest.mock import MagicMock, patch

from app.pipeline.models import IOCType
from tests.helpers import make_domain_ioc, make_ipv4_ioc


# ---------------------------------------------------------------------------
# Functional tests
# ---------------------------------------------------------------------------


def test_index_returns_200(client):
    """GET / returns 200 OK."""
    response = client.get("/")
    assert response.status_code == 200


def test_analyze_with_valid_input(client):
    """POST /analyze with mixed IOC text returns 200 with results."""
    text = (
        "Source IP 192[.]168[.]1[.]1 contacted hxxps://evil[.]example[.]com/beacon. "
        "Hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    response = client.post("/analyze", data={"text": text, "mode": "offline"})
    assert response.status_code == 200


def test_analyze_empty_input(client):
    """POST /analyze with empty text shows an error message."""
    response = client.post("/analyze", data={"text": "", "mode": "offline"})
    assert response.status_code == 200
    assert b"No input provided" in response.data


def test_analyze_whitespace_only_input(client):
    """POST /analyze with whitespace-only text treats it as empty."""
    response = client.post("/analyze", data={"text": "   \n\t  ", "mode": "offline"})
    assert response.status_code == 200
    assert b"No input provided" in response.data


def test_analyze_uses_shared_text_presence_check(client, monkeypatch):
    """Browser analyze should share the direct non-whitespace scanner."""
    from app.routes import analysis as analysis_routes

    calls: list[str] = []

    def record_presence(value: str) -> bool:
        calls.append(value)
        return True

    monkeypatch.setattr(analysis_routes, "has_non_whitespace", record_presence)
    monkeypatch.setattr(analysis_routes, "run_pipeline", lambda _text: [])

    response = client.post("/analyze", data={"text": "no indicators here", "mode": "offline"})

    assert response.status_code == 200
    assert calls == ["no indicators here"]


def test_analyze_extracts_ipv4(client):
    """POST with text containing a defanged IPv4 returns the refanged IP in response."""
    response = client.post(
        "/analyze", data={"text": "Alert from 10[.]0[.]0[.]1", "mode": "offline"}
    )
    assert response.status_code == 200
    # The refanged IP should appear in the rendered HTML
    assert b"10.0.0.1" in response.data


def test_analyze_groups_by_type(client):
    """POST with mixed IOC types — response HTML contains grouping indicators."""
    text = (
        "IP: 192[.]168[.]1[.]1 "
        "URL: hxxps://evil[.]example[.]com/path "
        "CVE-2025-49596"
    )
    response = client.post("/analyze", data={"text": text, "mode": "offline"})
    assert response.status_code == 200
    # Results page should contain group/accordion structure
    data = response.data
    assert b"grouped" in data or b"details" in data or b"summary" in data or b"ipv4" in data.lower()


def test_analyze_groups_template_iocs_with_shared_group_helper(client, monkeypatch):
    """Browser analyze should use the shared IOC grouping helper for template rendering."""
    from app.routes import analysis as analysis_routes

    iocs = [
        make_ipv4_ioc("8.8.8.8"),
        make_ipv4_ioc("1.1.1.1"),
        make_domain_ioc("example.com"),
    ]
    monkeypatch.setattr(analysis_routes, "run_pipeline", lambda _text: iocs)

    grouped = analysis_routes._group_iocs_for_template(iocs)
    response = client.post("/analyze", data={"text": "8.8.8.8 example.com", "mode": "offline"})

    assert grouped[IOCType.IPV4] == iocs[:2]
    assert grouped[IOCType.DOMAIN] == [iocs[2]]
    assert response.status_code == 200
    assert b"8.8.8.8" in response.data


def test_analyze_template_grouping_reuses_shared_group_helper(client, monkeypatch):
    """Browser analyze should delegate to the optimized pipeline grouping helper."""
    from app.routes import analysis as analysis_routes
    from app.routes import _helpers as route_helpers

    iocs = [
        make_ipv4_ioc("8.8.8.8"),
        make_ipv4_ioc("1.1.1.1"),
        make_domain_ioc("example.com"),
    ]
    calls: list[list] = []

    def group_once(seen_iocs):
        calls.append(seen_iocs)
        return {IOCType.IPV4: seen_iocs[:2], IOCType.DOMAIN: [seen_iocs[2]]}

    monkeypatch.setattr(route_helpers, "group_by_type", group_once)

    grouped = analysis_routes._group_iocs_for_template(iocs)

    assert grouped[IOCType.IPV4] == iocs[:2]
    assert grouped[IOCType.DOMAIN] == [iocs[2]]
    assert calls == [iocs]
    assert "group_by_type" in analysis_routes._group_iocs_for_template.__code__.co_names
    assert "group_by_type" in route_helpers._group_iocs_for_template.__code__.co_names
    assert "setdefault" not in analysis_routes._group_iocs_for_template.__code__.co_names


def test_analyze_template_grouping_preserves_pipeline_short_paths() -> None:
    """Route-level grouping should preserve pipeline empty/single/pair fast paths."""
    from app.routes import analysis as analysis_routes

    ioc_a = make_ipv4_ioc("8.8.8.8")
    ioc_b = make_domain_ioc("example.com")

    class NoIterIocs(list):
        def __iter__(self):
            raise AssertionError("route grouping should preserve shared short paths")

        def __getitem__(self, index):
            if isinstance(index, slice):
                raise AssertionError("route grouping should not slice short IOC lists")
            return super().__getitem__(index)

    assert analysis_routes._group_iocs_for_template(NoIterIocs()) == {}
    assert analysis_routes._group_iocs_for_template(NoIterIocs([ioc_a])) == {
        IOCType.IPV4: [ioc_a],
    }
    assert analysis_routes._group_iocs_for_template(NoIterIocs([ioc_a, ioc_b])) == {
        IOCType.IPV4: [ioc_a],
        IOCType.DOMAIN: [ioc_b],
    }


# ---------------------------------------------------------------------------
# Security tests
# ---------------------------------------------------------------------------


def test_max_content_length_is_5mb():
    """WEB-06: MAX_CONTENT_LENGTH must be 5 MB for SSH auth.log uploads."""
    from app.config import Config

    assert Config.MAX_CONTENT_LENGTH == 5 * 1024 * 1024


def test_oversize_post_returns_413(client):
    """POST a 600 KB payload returns 413 (SEC-12 / MAX_CONTENT_LENGTH)."""
    large_payload = "A" * (600 * 1024)
    response = client.post(
        "/analyze",
        data={"text": large_payload, "mode": "offline"},
        content_length=600 * 1024 + 100,
    )
    assert response.status_code == 413


def test_invalid_host_returns_400(client, app):
    """GET with an untrusted Host header returns 400 (SEC-11)."""
    # Bypass SERVER_NAME for this specific test by using a raw request
    with app.test_client() as raw_client:
        response = raw_client.get("/", headers={"Host": "evil.com"})
        assert response.status_code == 400


def test_debug_mode_is_false(app):
    """Flask app.debug is False (SEC-15)."""
    assert app.debug is False


def test_testing_app_uses_isolated_sqlite_paths(app):
    """Testing app factories should avoid the user home SQLite store."""
    test_data_dir = app.config.get("TEST_DATA_DIR")

    assert test_data_dir
    assert str(app.cache_store._db_path).startswith(test_data_dir)
    assert str(app.history_store._db_path).startswith(test_data_dir)


def test_security_headers_present(client):
    """CSP, X-Content-Type-Options, and X-Frame-Options are all present (SEC-09)."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Content-Security-Policy" in response.headers
    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "X-Frame-Options" in response.headers


def test_offline_mode_makes_no_http_calls(client):
    """POST in offline mode makes zero outbound HTTP calls (UI-02).

    Mocks common HTTP clients to ensure none are invoked during extraction.
    """
    with (
        patch("urllib.request.urlopen") as mock_urlopen,
        patch("http.client.HTTPConnection") as mock_http,
        patch("http.client.HTTPSConnection") as mock_https,
    ):
        text = (
            "Source IP 192[.]168[.]1[.]100 contacted "
            "hxxps://evil-c2[.]example[.]com/beacon\n"
            "Hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n"
            "CVE-2025-49596"
        )
        response = client.post("/analyze", data={"text": text, "mode": "offline"})
        assert response.status_code == 200

        mock_urlopen.assert_not_called()
        mock_http.assert_not_called()
        mock_https.assert_not_called()


def test_csrf_token_required(app):
    """POST /analyze without CSRF token returns 400 when CSRF is enabled (SEC-10).

    Uses a fresh app with CSRF enabled (not the test fixture which disables it).
    """
    # Create a separate app with CSRF enabled
    from app import create_app

    prod_like_app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": True,
            "SERVER_NAME": "localhost",
            "SECRET_KEY": "test-csrf-key",
        }
    )
    with prod_like_app.test_client() as csrf_client:
        response = csrf_client.post(
            "/analyze",
            data={"text": "192[.]168[.]1[.]1", "mode": "offline"},
        )
        # Without a valid CSRF token, Flask-WTF returns 400
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


def test_analyze_no_iocs_found(client):
    """POST with text containing no IOCs shows a friendly 'no results' message."""
    response = client.post(
        "/analyze",
        data={"text": "Hello world, no indicators here", "mode": "offline"},
    )
    assert response.status_code == 200
    data = response.data
    assert b"No IOCs detected" in data or b"no_results" in data or b"No IOCs" in data


def test_analyze_online_no_iocs_skips_enrichment_setup(client, monkeypatch):
    """Online mode with no extracted IOCs renders no-results without provider setup."""
    from app.routes import analysis as analysis_routes
    from app.routes import _helpers as route_helpers

    mock_registry = MagicMock()
    mock_registry.configured.side_effect = AssertionError(
        "zero-IOC online analysis should not check provider configuration"
    )
    client.application.registry = mock_registry

    def fail_group_iocs(_iocs):
        raise AssertionError("zero-IOC browser analysis should not group template IOCs")

    monkeypatch.setattr(route_helpers, "_group_iocs_for_template", fail_group_iocs)

    with patch("app.routes._helpers._enrichment_pool") as mock_pool:
        response = client.post(
            "/analyze",
            data={"text": "Hello world, no indicators here", "mode": "online"},
        )

    assert response.status_code == 200
    assert b"No IOCs detected" in response.data or b"No IOCs found" in response.data
    assert b"data-job-id" not in response.data
    mock_pool.submit.assert_not_called()
    assert "no_results else _group_iocs_for_template" in inspect.getsource(route_helpers._ioc_template_context)
    assert "_ioc_template_context" in inspect.getsource(analysis_routes.analyze)


def test_analyze_deduplicates(client):
    """POST with duplicate IOC values returns deduplicated results (no doubles)."""
    text = (
        "192[.]168[.]1[.]1 contacted 192[.]168[.]1[.]1 again and again: "
        "192.168.1.1"
    )
    response = client.post("/analyze", data={"text": text, "mode": "offline"})
    assert response.status_code == 200
    # The IP should appear in results but be deduplicated
    data = response.data.decode("utf-8")
    # Count occurrences of the canonical IP in value context
    count = data.count("192.168.1.1")
    # Should appear at least once (it was found) but not 3 times as separate entries
    assert count >= 1
    assert count < 20  # Sanity: not repeated many times as separate rows (richer M002/M003 template produces ~12 occurrences)


# ---------------------------------------------------------------------------
# Online mode tests
# ---------------------------------------------------------------------------


def test_analyze_online_without_api_key_redirects_to_settings(client):
    """POST /analyze online mode with no configured providers redirects to /settings."""
    mock_registry = MagicMock()
    mock_registry.configured.return_value = []
    client.application.registry = mock_registry

    response = client.post(
        "/analyze",
        data={"text": "192[.]168[.]1[.]1", "mode": "online"},
    )
    assert response.status_code == 302
    assert "/settings" in response.headers["Location"]


def test_analyze_online_without_api_key_redirects_follows(client):
    """POST /analyze online mode with no configured providers, following redirect, shows flash message."""
    mock_registry = MagicMock()
    mock_registry.configured.return_value = []
    client.application.registry = mock_registry

    response = client.post(
        "/analyze",
        data={"text": "192[.]168[.]1[.]1", "mode": "online"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"provider" in response.data.lower() or b"configure" in response.data.lower()


def test_analyze_online_without_api_key_skips_template_grouping(client, monkeypatch):
    """Missing-provider online rejection should redirect before template IOC grouping."""
    from app.routes import analysis as analysis_routes

    mock_registry = MagicMock()
    mock_registry.configured.return_value = []
    client.application.registry = mock_registry

    monkeypatch.setattr(
        analysis_routes,
        "_group_iocs_for_template",
        lambda _iocs: (_ for _ in ()).throw(
            AssertionError("missing-provider redirect should not group template IOCs")
        ),
    )

    response = client.post(
        "/analyze",
        data={"text": "192[.]168[.]1[.]1", "mode": "online"},
    )

    assert response.status_code == 302
    assert "/settings" in response.headers["Location"]


def test_analyze_online_with_api_key_returns_job_id(client):
    """POST /analyze online mode with configured registry returns results page with job_id."""
    with (
        patch("app.routes._helpers.EnrichmentOrchestrator") as MockOrchestrator,
        patch("app.routes._helpers._enrichment_pool") as mock_pool,
    ):
        mock_registry = MagicMock()
        mock_registry.configured.return_value = [MagicMock()]
        mock_registry.all.return_value = [MagicMock()]
        mock_registry.providers_for_type.return_value = [MagicMock()]
        mock_registry.provider_count_for_type.return_value = 2
        client.application.registry = mock_registry

        mock_orchestrator = MagicMock()
        MockOrchestrator.return_value = mock_orchestrator

        response = client.post(
            "/analyze",
            data={"text": "192[.]168[.]1[.]1", "mode": "online"},
        )

        assert response.status_code == 200
        # Pool submit must be called for background enrichment
        mock_pool.submit.assert_called_once()


def test_provider_counts_metadata_uses_direct_count_path():
    """Provider-count page metadata should not allocate provider lists or comprehension frames."""
    from app.routes.analysis import _PROVIDER_COUNT_IOC_TYPES, _provider_counts_json

    mock_registry = MagicMock()
    mock_registry.provider_count_for_type.side_effect = (
        lambda ioc_type: 3 if ioc_type == IOCType.SHA256 else 1
    )
    mock_registry.providers_for_type.side_effect = AssertionError(
        "provider-count metadata should use provider_count_for_type"
    )

    provider_counts = json.loads(_provider_counts_json(mock_registry))

    assert provider_counts["sha256"] == 3
    assert provider_counts["ipv4"] == 1
    assert "cve" not in provider_counts
    assert IOCType.CVE not in _PROVIDER_COUNT_IOC_TYPES
    assert tuple(_PROVIDER_COUNT_IOC_TYPES) is _PROVIDER_COUNT_IOC_TYPES
    assert "_PROVIDER_COUNT_IOC_TYPES" in _provider_counts_json.__code__.co_names
    assert "encode_json_object" in _provider_counts_json.__code__.co_names
    assert mock_registry.providers_for_type.call_count == 0
    assert all(
        getattr(const, "co_name", None) != "<dictcomp>"
        for const in _provider_counts_json.__code__.co_consts
    )


def test_provider_coverage_reuses_configured_provider_list():
    """Provider coverage should reuse configured providers and count registered providers directly."""
    from app.routes.analysis import _provider_coverage

    configured_providers = [MagicMock()]
    mock_registry = MagicMock()
    mock_registry.registered_count.return_value = 2
    mock_registry.all.side_effect = AssertionError(
        "provider coverage should not allocate all registered providers"
    )
    mock_registry.configured.side_effect = AssertionError(
        "provider coverage should reuse the caller's configured-provider list"
    )

    coverage = _provider_coverage(mock_registry, configured_providers)

    assert coverage == {"registered": 2, "configured": 1, "needs_key": 1}
    mock_registry.registered_count.assert_called_once()
    assert mock_registry.all.call_count == 0
    assert mock_registry.configured.call_count == 0


def test_online_fanout_diagnostics_uses_direct_count_path():
    """Admission diagnostics should count fanout without allocating provider lists."""
    from app.routes._helpers import _online_fanout_diagnostics
    from app.pipeline.models import IOC

    mock_registry = MagicMock()
    mock_registry.provider_count_for_type.return_value = 2
    mock_registry.providers_for_type.side_effect = AssertionError(
        "fanout diagnostics should use provider_count_for_type"
    )
    iocs = [
        IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4"),
        IOC(type=IOCType.IPV4, value="5.6.7.8", raw_match="5.6.7.8"),
    ]

    diagnostics = _online_fanout_diagnostics(
        iocs,
        mock_registry,
        max_iocs=10,
        max_dispatches=10,
    )

    assert diagnostics["dispatch_count"] == 4
    assert diagnostics["provider_counts_by_type"] == {"ipv4": 2}
    assert mock_registry.provider_count_for_type.call_count == 1
    assert mock_registry.providers_for_type.call_count == 0


def test_enrichable_count_caches_provider_counts_by_ioc_type():
    """Progress totals should not recount providers for repeated IOC types."""
    from app.routes.analysis import _enrichable_count

    mock_registry = MagicMock()
    mock_registry.provider_count_for_type.side_effect = (
        lambda ioc_type: 2 if ioc_type == IOCType.IPV4 else 3
    )
    mock_registry.providers_for_type.side_effect = AssertionError(
        "enrichable progress count should use provider_count_for_type"
    )
    iocs = [
        make_ipv4_ioc("1.2.3.4"),
        make_ipv4_ioc("5.6.7.8"),
        make_domain_ioc("example.com"),
    ]

    count = _enrichable_count(iocs, mock_registry)

    assert count == 7
    assert mock_registry.provider_count_for_type.call_count == 2
    assert mock_registry.provider_count_for_type.call_args_list[0].args == (IOCType.IPV4,)
    assert mock_registry.provider_count_for_type.call_args_list[1].args == (IOCType.DOMAIN,)
    assert mock_registry.providers_for_type.call_count == 0


def test_analyze_online_reuses_fanout_dispatch_count_for_progress_total(client, monkeypatch):
    """Online browser progress should reuse admission fanout instead of recounting providers."""
    from app.pipeline.models import IOC
    from app.routes import analysis as analysis_routes

    iocs = [
        IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8"),
        IOC(type=IOCType.IPV4, value="1.1.1.1", raw_match="1.1.1.1"),
    ]
    monkeypatch.setattr(analysis_routes, "run_pipeline", lambda _text: iocs)
    monkeypatch.setattr(
        analysis_routes,
        "_provider_counts_json",
        lambda _registry: "{}",
    )
    mock_registry = MagicMock()
    mock_registry.configured.return_value = [MagicMock()]
    mock_registry.all.return_value = [MagicMock()]
    mock_registry.provider_count_for_type.return_value = 2
    client.application.registry = mock_registry

    with (
        patch("app.routes._helpers.EnrichmentOrchestrator") as MockOrchestrator,
        patch("app.routes._helpers._enrichment_pool"),
    ):
        MockOrchestrator.return_value = MagicMock()
        response = client.post(
            "/analyze",
            data={"text": "8.8.8.8 1.1.1.1", "mode": "online"},
        )

    assert response.status_code == 200
    assert b"0/4" in response.data or b"Enriching 0/4" in response.data
    assert mock_registry.provider_count_for_type.call_count == 1


class _BoundedKeyDict(dict):
    def __init__(self, pairs, *, max_reads: int):
        super().__init__()
        self._pairs = pairs
        self.max_reads = max_reads
        self.reads = 0
        self._values = dict(pairs)

    def __iter__(self):
        for key, _value in self._pairs:
            self.reads += 1
            if self.reads > self.max_reads:
                raise AssertionError("diagnostic coercion should stop at the export cap")
            yield key

    def __getitem__(self, key):
        return self._values[key]

    def items(self):
        raise AssertionError("diagnostic coercion should avoid items-view allocation")


class _NoSliceList(list):
    def __getitem__(self, index):
        if isinstance(index, slice):
            raise AssertionError("diagnostic list coercion should use bounded iteration")
        return super().__getitem__(index)


def test_orchestration_diagnostics_export_coercion_uses_bounded_iteration():
    """Diagnostic export coercion should not materialize entries beyond its caps."""
    from app.routes._helpers import _coerce_orchestration_diagnostics_for_export

    child = _BoundedKeyDict(
        [(f"child-{index}", index) for index in range(45)],
        max_reads=40,
    )
    raw = _BoundedKeyDict(
        [("nested", child), *[(f"key-{index}", index) for index in range(44)]],
        max_reads=40,
    )

    diagnostics = _coerce_orchestration_diagnostics_for_export(raw)

    assert raw.reads == 40
    assert child.reads == 40
    assert "key-38" in diagnostics
    assert "key-39" not in diagnostics
    assert diagnostics["nested"]["child-39"] == 39
    assert "child-40" not in diagnostics["nested"]


def test_orchestration_diagnostics_export_coercion_does_not_slice_lists():
    """Diagnostic export list caps should not allocate a sliced copy."""
    from app.routes._helpers import _coerce_orchestration_diagnostics_for_export

    raw = {"events": _NoSliceList(f"event-{index}" for index in range(30))}

    diagnostics = _coerce_orchestration_diagnostics_for_export(raw)

    assert diagnostics["events"][0] == "event-0"
    assert diagnostics["events"][-1] == "event-24"
    assert len(diagnostics["events"]) == 25


def test_orchestration_diagnostics_export_coercion_accumulates_lists_directly():
    """Diagnostic export list coercion should not allocate a list-comprehension frame."""
    from app.routes._helpers import _coerce_orchestration_diagnostics_for_export

    nested_code_names = {
        const.co_name
        for const in _coerce_orchestration_diagnostics_for_export.__code__.co_consts
        if hasattr(const, "co_name")
    }

    assert "<listcomp>" not in nested_code_names
    assert _coerce_orchestration_diagnostics_for_export({"events": ["ok", object()]}) == {
        "events": ["ok"]
    }


def test_orchestration_status_string_coercion_avoids_strip_allocation():
    """Diagnostic status strings should trim through the shared bounded index helper."""
    from app.routes import _helpers

    source = inspect.getsource(_helpers._coerce_orchestration_status_for_diagnostics)
    assert '("total", "done")' not in source
    assert '("complete", "terminal")' not in source
    assert '("status", "terminal_reason", "error")' not in source

    class MeasuredStripText(str):
        strip_calls = 0

        def strip(self, *_args, **_kwargs):
            raise AssertionError("diagnostic status coercion should not allocate through strip()")

    status = _helpers._coerce_orchestration_status_for_diagnostics({
        "total": 1,
        "done": 1,
        "complete": True,
        "terminal": False,
        "status": MeasuredStripText(" running "),
        "terminal_reason": MeasuredStripText("   "),
        "error": MeasuredStripText(" failed "),
    })

    assert status["status"] == "running"
    assert "terminal_reason" not in status
    assert status["error"] == "failed"
    assert MeasuredStripText.strip_calls == 0


def test_analyze_online_creates_all_three_adapters(client):
    """Online mode uses current_app.registry and passes registry.configured() to the orchestrator."""
    with (
        patch("app.routes._helpers.EnrichmentOrchestrator") as MockOrchestrator,
        patch("app.routes._helpers._enrichment_pool"),
    ):
        mock_provider_vt = MagicMock(name="VTProvider")
        mock_provider_mb = MagicMock(name="MBProvider")
        mock_provider_tf = MagicMock(name="TFProvider")
        all_providers = [mock_provider_vt, mock_provider_mb, mock_provider_tf]

        mock_registry = MagicMock()
        mock_registry.configured.return_value = all_providers
        mock_registry.all.return_value = all_providers
        mock_registry.providers_for_type.return_value = [MagicMock()]
        mock_registry.provider_count_for_type.return_value = 2
        client.application.registry = mock_registry

        MockOrchestrator.return_value = MagicMock()

        client.post("/analyze", data={"text": "192[.]168[.]1[.]1", "mode": "online"})

        # Orchestrator receives registry.configured() — only configured provider mocks
        orch_call_kwargs = MockOrchestrator.call_args[1]
        adapters_passed = orch_call_kwargs["adapters"]
        assert mock_provider_vt in adapters_passed
        assert mock_provider_mb in adapters_passed
        assert mock_provider_tf in adapters_passed
        assert mock_registry.configured.call_count == 1


def test_enrichable_count_multi_provider(client):
    """SHA256 hash IOC yields enrichable_count=3 (VT + MB + TF all support hashes)."""

    with (
        patch("app.routes._helpers.EnrichmentOrchestrator") as MockOrchestrator,
        patch("app.routes._helpers._enrichment_pool"),
    ):
        mock_registry = MagicMock()
        mock_registry.configured.return_value = [MagicMock(), MagicMock(), MagicMock()]
        mock_registry.all.return_value = [MagicMock(), MagicMock(), MagicMock()]
        # SHA256 type — 3 providers support it
        mock_registry.providers_for_type.return_value = [MagicMock(), MagicMock(), MagicMock()]
        mock_registry.provider_count_for_type.return_value = 3
        client.application.registry = mock_registry

        MockOrchestrator.return_value = MagicMock()

        # SHA256 hash — all three adapters support it
        sha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        response = client.post("/analyze", data={"text": sha256, "mode": "online"})
        assert response.status_code == 200
        # enrichable_count=3 appears in the progress text
        assert b"0/3" in response.data or b"Enriching 0/3" in response.data


def test_enrichable_count_domain_two_providers(client):
    """Domain IOC yields enrichable_count=2 (VT + TF support domains, MB does not)."""
    with (
        patch("app.routes._helpers.EnrichmentOrchestrator") as MockOrchestrator,
        patch("app.routes._helpers._enrichment_pool"),
    ):
        mock_registry = MagicMock()
        mock_registry.configured.return_value = [MagicMock(), MagicMock()]
        mock_registry.all.return_value = [MagicMock(), MagicMock(), MagicMock()]
        # Domain/URL types — 2 providers (VT + TF, not MB)
        mock_registry.providers_for_type.return_value = [MagicMock(), MagicMock()]
        mock_registry.provider_count_for_type.return_value = 2
        client.application.registry = mock_registry

        MockOrchestrator.return_value = MagicMock()

        # Domain — VT and TF support it, MB does not
        response = client.post("/analyze", data={"text": "hxxps://evil[.]example[.]com", "mode": "online"})
        assert response.status_code == 200
        # The domain evil.example.com may be extracted as both domain and URL — each gets 2 providers
        # enrichable_count=2 or 4 depending on how many IOCs are extracted
        assert b"Enriching 0/2" in response.data or b"0/2" in response.data or b"0/4" in response.data


def test_analyze_offline_unchanged(client):
    """POST /analyze offline mode behaves identically to Phase 1 (no job_id, no enrichment)."""
    with patch("app.routes._helpers._enrichment_pool") as mock_pool:
        response = client.post(
            "/analyze",
            data={"text": "10[.]0[.]0[.]1", "mode": "offline"},
        )
        assert response.status_code == 200
        assert b"10.0.0.1" in response.data
        # Pool should NOT have been called for offline mode
        mock_pool.submit.assert_not_called()


def test_analyze_online_rejects_ioc_limit_before_launch(client):
    """HTML online mode shows a friendly limit diagnostic without background work."""
    mock_provider = MagicMock()
    mock_registry = MagicMock()
    mock_registry.configured.return_value = [mock_provider]
    mock_registry.all.return_value = [mock_provider]
    mock_registry.providers_for_type.return_value = [mock_provider]
    mock_registry.provider_count_for_type.return_value = 1
    client.application.registry = mock_registry
    client.application.config["ONLINE_MAX_IOCS"] = 1
    client.application.config["ONLINE_MAX_DISPATCHES"] = 200

    with patch("app.routes._helpers._enrichment_pool") as mock_pool:
        response = client.post(
            "/analyze",
            data={"text": "192.168.1.1 10.0.0.1", "mode": "online"},
        )

    assert response.status_code == 200
    assert b"Online enrichment was not started" in response.data
    assert b"Current limits" in response.data
    assert b"data-job-id" not in response.data
    mock_pool.submit.assert_not_called()


def test_analyze_online_uses_shared_limit_config_helper(client):
    """HTML online admission should read limits through the shared helper."""
    mock_provider = MagicMock()
    mock_registry = MagicMock()
    mock_registry.configured.return_value = [mock_provider]
    mock_registry.all.return_value = [mock_provider]
    mock_registry.providers_for_type.return_value = [mock_provider]
    mock_registry.provider_count_for_type.return_value = 1
    client.application.registry = mock_registry
    client.application.config["ONLINE_MAX_IOCS"] = 50
    client.application.config["ONLINE_MAX_DISPATCHES"] = 200

    with (
        patch("app.routes.analysis._online_limits_from_config", return_value=(1, 200)) as limits,
        patch("app.routes._helpers._enrichment_pool") as mock_pool,
    ):
        response = client.post(
            "/analyze",
            data={"text": "192.168.1.1 10.0.0.1", "mode": "online"},
        )

    assert response.status_code == 200
    assert b"Online enrichment was not started" in response.data
    limits.assert_called_once_with()
    mock_pool.submit.assert_not_called()


def test_analyze_online_rejects_dispatch_limit_before_launch(client):
    """HTML online mode rejects excessive provider fanout before background work."""
    providers = [MagicMock(), MagicMock()]
    mock_registry = MagicMock()
    mock_registry.configured.return_value = providers
    mock_registry.all.return_value = providers
    mock_registry.providers_for_type.return_value = providers
    mock_registry.provider_count_for_type.return_value = 2
    client.application.registry = mock_registry
    client.application.config["ONLINE_MAX_IOCS"] = 50
    client.application.config["ONLINE_MAX_DISPATCHES"] = 1

    with patch("app.routes._helpers._enrichment_pool") as mock_pool:
        response = client.post(
            "/analyze",
            data={"text": "192.168.1.1", "mode": "online"},
        )

    assert response.status_code == 200
    assert b"Online enrichment was not started" in response.data
    assert b"provider lookup" in response.data
    assert b"data-job-id" not in response.data
    mock_pool.submit.assert_not_called()


# ---------------------------------------------------------------------------
# Polling endpoint tests
# ---------------------------------------------------------------------------


def _build_incremental_snapshot_orchestrator(
    results,
    *,
    total=None,
    done=None,
    complete=True,
    status=None,
    terminal=False,
    terminal_reason=None,
    error=None,
    cached_markers=None,
):
    """Return a mock orchestrator exposing only the incremental polling API."""
    full_results = list(results)
    marker_map = dict(cached_markers or {})
    mock_orch = MagicMock(spec_set=["get_incremental_status", "get_status"])

    def _get_incremental_status(_job_id, since=0):
        tail_results = list(full_results[since:])
        tail_markers = {}
        for result in tail_results:
            ioc = getattr(result, "ioc", None)
            provider = getattr(result, "provider", None)
            ioc_value = getattr(ioc, "value", None)
            if not ioc_value or not provider:
                continue
            cache_key = f"{ioc_value}|{provider}"
            cached_at = marker_map.get(cache_key)
            if cached_at:
                tail_markers[cache_key] = cached_at
        return {
            "total": len(full_results) if total is None else total,
            "done": len(full_results) if done is None else done,
            "complete": complete,
            "results": tail_results,
            "next_since": since if terminal else len(full_results),
            "status": status or ("failed" if terminal else "complete" if complete else "running"),
            "terminal": terminal,
            "terminal_reason": terminal_reason,
            "error": error,
            "cached_markers": tail_markers,
        }

    mock_orch.get_incremental_status.side_effect = _get_incremental_status
    mock_orch.get_status.side_effect = AssertionError(
        "_get_enrichment_status should use get_incremental_status() for polling"
    )
    return mock_orch


def test_enrichment_status_unknown_job(client):
    """GET /enrichment/status/nonexistent returns explicit terminal JSON."""
    response = client.get("/enrichment/status/nonexistentjob123?since=7")
    assert response.status_code == 404
    data = response.get_json()
    assert data is not None
    assert data["error"] == "Enrichment job was not found."
    assert data["status"] == "failed"
    assert data["terminal"] is True
    assert data["terminal_reason"] == "unknown"
    assert data["complete"] is True
    assert data["next_since"] == 7


def test_enrichment_status_returns_json(client):
    """GET /enrichment/status/{job_id} returns correct JSON structure."""
    import app.routes._helpers as routes_module

    mock_orchestrator = _build_incremental_snapshot_orchestrator(
        [],
        total=3,
        done=2,
        complete=False,
        status="running",
    )

    job_id = "testjob123abc"
    # Inject directly into module-level registry
    routes_module._orchestrators[job_id] = mock_orchestrator

    try:
        response = client.get(f"/enrichment/status/{job_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 3
        assert data["done"] == 2
        assert data["complete"] is False
        assert data["status"] == "running"
        assert data["terminal"] is False
        assert data["terminal_reason"] is None
        assert "results" in data
        mock_orchestrator.get_incremental_status.assert_called_once_with(job_id, since=0)
        mock_orchestrator.get_status.assert_not_called()
    finally:
        routes_module._orchestrators.pop(job_id, None)


def test_enrichment_result_serialization(client):
    """GET /enrichment/status/{job_id} serializes EnrichmentResult with provider, verdict, scan_date (ENRC-05)."""
    import app.routes._helpers as routes_module
    from app.enrichment.models import EnrichmentResult
    from app.pipeline.models import IOC, IOCType

    sample_ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
    sample_result = EnrichmentResult(
        ioc=sample_ioc,
        provider="VirusTotal",
        verdict="malicious",
        detection_count=5,
        total_engines=72,
        scan_date="2026-02-21T00:00:00+00:00",
        raw_stats={"malicious": 5, "clean": 67},
    )

    mock_orchestrator = _build_incremental_snapshot_orchestrator([sample_result])

    job_id = "serialjob456def"
    routes_module._orchestrators[job_id] = mock_orchestrator

    try:
        response = client.get(f"/enrichment/status/{job_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["results"]) == 1

        r = data["results"][0]
        assert r["type"] == "result"
        assert r["provider"] == "VirusTotal"         # ENRC-05: provider name
        assert r["verdict"] == "malicious"            # ENRC-05: raw verdict
        assert r["scan_date"] == "2026-02-21T00:00:00+00:00"  # ENRC-05: timestamp
        assert r["ioc_value"] == "1.2.3.4"
        assert r["ioc_type"] == "ipv4"
        assert r["detection_count"] == 5
        assert r["total_engines"] == 72
        assert data["status"] == "complete"
        assert data["terminal"] is False
        assert data["terminal_reason"] is None
    finally:
        routes_module._orchestrators.pop(job_id, None)


def test_enrichment_error_serialization(client):
    """GET /enrichment/status/{job_id} serializes EnrichmentError with provider and error fields."""
    import app.routes._helpers as routes_module
    from app.enrichment.models import EnrichmentError
    from app.pipeline.models import IOC, IOCType

    sample_ioc = IOC(type=IOCType.DOMAIN, value="evil.com", raw_match="evil.com")
    sample_error = EnrichmentError(
        ioc=sample_ioc,
        provider="VirusTotal",
        error="Timeout",
    )

    mock_orchestrator = _build_incremental_snapshot_orchestrator([sample_error])

    job_id = "errorjob789ghi"
    routes_module._orchestrators[job_id] = mock_orchestrator

    try:
        response = client.get(f"/enrichment/status/{job_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["results"]) == 1

        r = data["results"][0]
        assert r["type"] == "error"
        assert r["provider"] == "VirusTotal"
        assert r["error"] == "Timeout"
        assert r["ioc_value"] == "evil.com"
        assert r["ioc_type"] == "domain"
        assert data["status"] == "complete"
        assert data["terminal"] is False
        assert data["terminal_reason"] is None
    finally:
        routes_module._orchestrators.pop(job_id, None)


def test_enrichment_status_serializes_cached_at_only_for_cached_rows(client):
    """Cached markers come from the incremental tail and only annotate cached rows."""
    import app.routes._helpers as routes_module
    from app.enrichment.models import EnrichmentResult

    first_result = EnrichmentResult(
        ioc=make_ipv4_ioc("1.1.1.1"),
        provider="FreshProvider",
        verdict="clean",
        detection_count=0,
        total_engines=10,
        scan_date=None,
        raw_stats={},
    )
    cached_ioc = make_ipv4_ioc("2.2.2.2")
    cached_result = EnrichmentResult(
        ioc=cached_ioc,
        provider="CachedProvider",
        verdict="clean",
        detection_count=0,
        total_engines=5,
        scan_date=None,
        raw_stats={},
    )

    cache_key = f"{cached_ioc.value}|{cached_result.provider}"
    mock_orchestrator = _build_incremental_snapshot_orchestrator(
        [first_result, cached_result],
        cached_markers={cache_key: "2026-04-25T00:00:00Z"},
    )

    job_id = "cachedrowsjob123"
    routes_module._orchestrators[job_id] = mock_orchestrator

    try:
        response = client.get(f"/enrichment/status/{job_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["results"]) == 2
        assert "cached_at" not in data["results"][0]
        assert data["results"][1]["cached_at"] == "2026-04-25T00:00:00Z"
        mock_orchestrator.get_incremental_status.assert_called_once_with(job_id, since=0)
        mock_orchestrator.get_status.assert_not_called()
    finally:
        routes_module._orchestrators.pop(job_id, None)


def test_enrichment_status_reads_cached_markers_once_per_payload(client):
    """Polling serialization should reuse the cached marker map for the whole tail."""
    import app.routes._helpers as routes_module
    from app.enrichment.models import EnrichmentResult

    class CountingStatus(dict):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.cached_marker_gets = 0

        def get(self, key, default=None):
            if key == "cached_markers":
                self.cached_marker_gets += 1
            return super().get(key, default)

    results = [
        EnrichmentResult(
            ioc=make_ipv4_ioc(f"192.0.2.{index}"),
            provider="CachedProvider",
            verdict="clean",
            detection_count=0,
            total_engines=5,
            scan_date=None,
            raw_stats={},
        )
        for index in range(1, 4)
    ]
    status = CountingStatus(
        {
            "total": 3,
            "done": 3,
            "complete": True,
            "results": results,
            "next_since": 3,
            "status": "complete",
            "terminal": False,
            "terminal_reason": None,
            "error": None,
            "cached_markers": {
                f"{result.ioc.value}|{result.provider}": "2026-04-25T00:00:00Z"
                for result in results
            },
        }
    )
    mock_orchestrator = MagicMock(spec_set=["get_incremental_status", "get_status"])
    mock_orchestrator.get_incremental_status.return_value = status
    mock_orchestrator.get_status.side_effect = AssertionError(
        "_get_enrichment_status should not fall back to get_status()"
    )

    job_id = "cachedmarkersonce123"
    routes_module._orchestrators[job_id] = mock_orchestrator

    try:
        response = client.get(f"/enrichment/status/{job_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["results"]) == 3
        assert status.cached_marker_gets == 1
        nested_code_names = {
            const.co_name
            for const in routes_module._get_enrichment_status.__code__.co_consts
            if hasattr(const, "co_name")
        }
        assert "<listcomp>" not in nested_code_names
    finally:
        routes_module._orchestrators.pop(job_id, None)


def test_serialize_result_skips_empty_cached_marker_map():
    """Empty cached-marker maps should not build per-result cache lookup keys."""
    from app.enrichment.models import EnrichmentResult
    from app.routes._helpers import _serialize_result

    class EmptyMarkerMap(dict):
        def get(self, key, default=None):
            raise AssertionError("empty cached markers should not be queried per result")

    result = EnrichmentResult(
        ioc=make_ipv4_ioc("192.0.2.10"),
        provider="CachedProvider",
        verdict="clean",
        detection_count=0,
        total_engines=5,
        scan_date=None,
        raw_stats={},
    )

    serialized = _serialize_result(result, EmptyMarkerMap())

    assert serialized["ioc_value"] == "192.0.2.10"
    assert "cached_at" not in serialized


def test_serialize_results_shared_direct_accumulation(monkeypatch):
    """Batch result serialization should use the shared per-result serializer path."""
    import app.routes._helpers as routes_module

    calls = []
    cached_markers = {"192.0.2.10|CachedProvider": "2026-04-25T00:00:00Z"}

    def serialize_result(result, markers=None):
        calls.append((result, markers))
        return {"value": result}

    monkeypatch.setattr(routes_module, "_serialize_result", serialize_result)

    class NoIterResults(list):
        def __iter__(self):
            raise AssertionError("short result serialization should not iterate")

    assert routes_module._serialize_results([], cached_markers) == []
    assert routes_module._serialize_results(NoIterResults(["only"]), cached_markers) == [{"value": "only"}]
    serialized = routes_module._serialize_results(NoIterResults(["first", "second"]), cached_markers)
    triple_serialized = routes_module._serialize_results(
        NoIterResults(["first", "second", "third"]),
        cached_markers,
    )
    nested_code_names = {
        const.co_name
        for const in routes_module._serialize_results.__code__.co_consts
        if hasattr(const, "co_name")
    }

    assert serialized == [{"value": "first"}, {"value": "second"}]
    assert triple_serialized == [{"value": "first"}, {"value": "second"}, {"value": "third"}]
    assert calls == [
        ("only", cached_markers),
        ("first", cached_markers),
        ("second", cached_markers),
        ("first", cached_markers),
        ("second", cached_markers),
        ("third", cached_markers),
    ]
    assert "<listcomp>" not in nested_code_names
    assert "len" in routes_module._serialize_results.__code__.co_names


def test_enrichment_status_job_failed_payload_stays_truthful(client):
    """Orchestrator terminal failures stay terminal without being collapsed into 404 tombstones."""
    import app.routes._helpers as routes_module

    mock_orchestrator = MagicMock(spec_set=["get_incremental_status", "get_status"])
    mock_orchestrator.get_incremental_status.return_value = {
        "total": 2,
        "done": 1,
        "complete": True,
        "results": [],
        "next_since": 5,
        "status": "failed",
        "terminal": True,
        "terminal_reason": "job_failed",
        "error": "VirusTotal lookup crashed",
        "cached_markers": {},
    }
    mock_orchestrator.get_status.side_effect = AssertionError(
        "_get_enrichment_status should not fall back to get_status()"
    )

    job_id = "jobfailed123"
    routes_module._orchestrators[job_id] = mock_orchestrator

    try:
        response = client.get(f"/enrichment/status/{job_id}?since=5")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "failed"
        assert data["terminal"] is True
        assert data["terminal_reason"] == "job_failed"
        assert data["error"] == "VirusTotal lookup crashed"
        assert data["next_since"] == 5
        mock_orchestrator.get_incremental_status.assert_called_once_with(job_id, since=5)
        mock_orchestrator.get_status.assert_not_called()
    finally:
        routes_module._orchestrators.pop(job_id, None)


def test_status_payload_uses_explicit_next_since_without_measuring_results() -> None:
    """Status payloads should not measure retained results when next_since is explicit."""
    from app.routes._helpers import _build_status_payload

    class NoLenResults:
        def __len__(self):
            raise AssertionError("explicit next_since should skip result-length fallback")

    payload = _build_status_payload(
        {
            "total": 10,
            "done": 2,
            "complete": False,
            "results": NoLenResults(),
            "next_since": 7,
        },
        [],
    )

    assert payload["next_since"] == 7
    assert payload["status"] == "running"


def test_enrichment_status_evicted_job_returns_terminal_payload(client):
    """Registry-level eviction returns an explicit terminal eviction payload."""
    import app.routes._helpers as routes_module

    job_id = "evictedjob123"
    routes_module._terminal_jobs[job_id] = routes_module._terminal_status(
        job_id,
        reason="evicted",
        error="Enrichment job status was evicted from memory.",
        since=4,
    )

    try:
        response = client.get(f"/enrichment/status/{job_id}?since=4")
        assert response.status_code == 404
        data = response.get_json()
        assert data["status"] == "failed"
        assert data["terminal"] is True
        assert data["terminal_reason"] == "evicted"
        assert data["error"] == "Enrichment job status was evicted from memory."
        assert data["complete"] is True
        assert data["next_since"] == 4
    finally:
        routes_module._terminal_jobs.pop(job_id, None)


def test_enrichment_status_not_found_reasons_use_static_membership_set(client):
    """404 terminal reason checks should reuse a static membership table."""
    import app.routes._helpers as routes_module

    source = inspect.getsource(routes_module._get_enrichment_status)
    assert '{"unknown", "evicted"}' not in source
    assert "_STATUS_NOT_FOUND_REASONS" in source
    assert routes_module._STATUS_NOT_FOUND_REASONS == frozenset(("unknown", "evicted"))

    mock_orchestrator = _build_incremental_snapshot_orchestrator(
        [],
        total=1,
        done=0,
        complete=True,
        terminal=True,
        terminal_reason="job_failed",
        error="Provider lookup crashed.",
    )
    job_id = "failedterminal123"
    routes_module._orchestrators[job_id] = mock_orchestrator

    try:
        response = client.get(f"/enrichment/status/{job_id}?since=1")
        assert response.status_code == 200
        data = response.get_json()
        assert data["terminal"] is True
        assert data["terminal_reason"] == "job_failed"
    finally:
        routes_module._orchestrators.pop(job_id, None)


def test_orchestration_diagnostics_evicted_job_copies_terminal_snapshot_directly():
    """Diagnostic tombstone snapshots should avoid constructor-copying terminal jobs."""
    import app.routes._helpers as routes_module

    job_id = "diagsevicted123"
    routes_module._terminal_jobs[job_id] = routes_module._terminal_status(
        job_id,
        reason="evicted",
        error="Enrichment job status was evicted from memory.",
        since=2,
    )

    try:
        snapshot = routes_module.get_orchestration_diagnostics_snapshot(job_id)
        source = inspect.getsource(routes_module.get_orchestration_diagnostics_snapshot)

        assert "dict(_terminal_jobs.get" not in source
        assert snapshot == {
            "job_id": job_id,
            "found": False,
            "reason": "evicted",
            "terminal": True,
        }
    finally:
        routes_module._terminal_jobs.pop(job_id, None)


def test_orchestration_diagnostics_job_id_normalization_avoids_strip_allocation():
    """Diagnostic job-id normalization should trim through the shared index helper."""
    import app.routes._helpers as routes_module

    class NoStripJobId(str):
        def strip(self, *_args, **_kwargs):
            raise AssertionError("diagnostic job-id normalization should avoid direct strip allocation")

    class JobIdWrapper:
        def __str__(self) -> str:
            return NoStripJobId(" diagstripjob123 ")

    job_id = "diagstripjob123"
    routes_module._terminal_jobs[job_id] = routes_module._terminal_status(
        job_id,
        reason="evicted",
        error="Enrichment job status was evicted from memory.",
        since=0,
    )

    try:
        snapshot = routes_module.get_orchestration_diagnostics_snapshot(JobIdWrapper())

        assert snapshot["job_id"] == job_id
        assert snapshot["found"] is False
        assert snapshot["reason"] == "evicted"
        assert "strip" not in routes_module.get_orchestration_diagnostics_snapshot.__code__.co_names
    finally:
        routes_module._terminal_jobs.pop(job_id, None)


def test_route_snapshot_helpers_share_mapping_copy_contract():
    """Route diagnostic snapshots should share one constructor-free copy helper."""
    import app.routes._helpers as routes_module

    class NoIterEmptyDict(dict):
        def __iter__(self):
            raise AssertionError("empty mapping copy should not iterate")

    class SingleReadDict(dict):
        reads = 0

        def __iter__(self):
            for key in super().__iter__():
                type(self).reads += 1
                if type(self).reads > 1:
                    raise AssertionError("single mapping copy should stop after one key")
                yield key

    class PairReadDict(dict):
        reads = 0

        def __iter__(self):
            for key in super().__iter__():
                type(self).reads += 1
                if type(self).reads > 2:
                    raise AssertionError("pair mapping copy should stop after two keys")
                yield key

    source = inspect.getsource(routes_module)
    single = SingleReadDict({"count": 1})
    pair = PairReadDict({"terminal": True, "terminal_reason": "evicted"})

    assert routes_module._copy_mapping({"count": 1}) == {"count": 1}
    assert routes_module._copy_mapping(None) == {}
    assert routes_module._copy_mapping(NoIterEmptyDict()) == {}
    assert isinstance(routes_module._HISTORY_SAVE_DIAGNOSTICS_DEFAULTS, MappingProxyType)
    assert routes_module._copy_mapping(routes_module._HISTORY_SAVE_DIAGNOSTICS_DEFAULTS)["last_outcome"] == "never"
    assert routes_module._copy_mapping(single) == {"count": 1}
    assert routes_module._copy_mapping(pair) == {"terminal": True, "terminal_reason": "evicted"}
    assert SingleReadDict.reads == 1
    assert PairReadDict.reads == 2
    assert "_copy_mapping" in routes_module._history_save_diagnostics_defaults.__code__.co_names
    assert "_copy_mapping" in routes_module._copy_history_save_diagnostics.__code__.co_names
    assert "_copy_mapping" in routes_module._copy_terminal_job_snapshot.__code__.co_names
    assert "len" in routes_module._copy_mapping.__code__.co_names
    assert "dict(_terminal_jobs.get" not in source


def test_history_save_diagnostic_updates_share_identity_preserving_replace_helper():
    """History-save diagnostic writers should reuse one clear/update path."""
    import app.routes._helpers as routes_module

    routes_module._reset_history_save_diagnostics()
    diagnostics_id = id(routes_module._history_save_diagnostics)

    routes_module._record_history_save_attempt()
    snapshot = routes_module.get_history_save_diagnostics()

    assert id(routes_module._history_save_diagnostics) == diagnostics_id
    assert snapshot["attempts"] == 1
    assert "_replace_history_save_diagnostics" in routes_module._record_history_save_attempt.__code__.co_names
    assert "_replace_history_save_diagnostics" in routes_module._record_history_save_outcome.__code__.co_names
    assert "_replace_history_save_diagnostics" in routes_module._reset_history_save_diagnostics.__code__.co_names

    routes_module._reset_history_save_diagnostics()


# ---------------------------------------------------------------------------
# ?since= cursor tests
# ---------------------------------------------------------------------------

def _make_three_result_orchestrator():
    """Return a mock orchestrator with 3 completed results for cursor tests."""
    from app.enrichment.models import EnrichmentResult
    from app.pipeline.models import IOC, IOCType

    ioc = IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")
    results = [
        EnrichmentResult(ioc=ioc, provider="VirusTotal", verdict="clean",
                         detection_count=0, total_engines=70,
                         scan_date=None, raw_stats={}),
        EnrichmentResult(ioc=ioc, provider="AbuseIPDB", verdict="clean",
                         detection_count=0, total_engines=1,
                         scan_date=None, raw_stats={}),
        EnrichmentResult(ioc=ioc, provider="Shodan", verdict="no_data",
                         detection_count=0, total_engines=0,
                         scan_date=None, raw_stats={}),
    ]
    return _build_incremental_snapshot_orchestrator(results)


def test_enrichment_status_since_returns_slice(client):
    """?since=2 returns only the 1 result at index 2 and next_since == 3."""
    import app.routes._helpers as routes_module

    mock_orch = _make_three_result_orchestrator()
    job_id = "cursor_slice_job"
    routes_module._orchestrators[job_id] = mock_orch
    try:
        response = client.get(f"/enrichment/status/{job_id}?since=2")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["results"]) == 1
        assert data["next_since"] == 3
    finally:
        routes_module._orchestrators.pop(job_id, None)


def test_enrichment_status_since_zero_returns_all(client):
    """?since=0 returns all 3 results and next_since == 3."""
    import app.routes._helpers as routes_module

    mock_orch = _make_three_result_orchestrator()
    job_id = "cursor_zero_job"
    routes_module._orchestrators[job_id] = mock_orch
    try:
        response = client.get(f"/enrichment/status/{job_id}?since=0")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["results"]) == 3
        assert data["next_since"] == 3
    finally:
        routes_module._orchestrators.pop(job_id, None)


def test_enrichment_status_no_since_returns_all(client):
    """No since param returns all 3 results (backward compat) and next_since == 3."""
    import app.routes._helpers as routes_module

    mock_orch = _make_three_result_orchestrator()
    job_id = "cursor_nosince_job"
    routes_module._orchestrators[job_id] = mock_orch
    try:
        response = client.get(f"/enrichment/status/{job_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["results"]) == 3
        assert data["next_since"] == 3
    finally:
        routes_module._orchestrators.pop(job_id, None)


def test_enrichment_status_negative_since_preserves_tail_behavior(client):
    """Negative since values preserve the existing Python-slice tail behavior."""
    import app.routes._helpers as routes_module

    mock_orch = _make_three_result_orchestrator()
    job_id = "cursor_negative_job"
    routes_module._orchestrators[job_id] = mock_orch
    try:
        response = client.get(f"/enrichment/status/{job_id}?since=-1")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["results"]) == 1
        assert data["results"][0]["provider"] == "Shodan"
        assert data["next_since"] == 3
        mock_orch.get_incremental_status.assert_called_once_with(job_id, since=-1)
        mock_orch.get_status.assert_not_called()
    finally:
        routes_module._orchestrators.pop(job_id, None)


def test_enrichment_status_since_equal_to_length_returns_empty_delta(client):
    """?since=3 with 3 results returns no new rows and preserves next_since."""
    import app.routes._helpers as routes_module

    mock_orch = _make_three_result_orchestrator()
    job_id = "cursor_exact_length_job"
    routes_module._orchestrators[job_id] = mock_orch
    try:
        response = client.get(f"/enrichment/status/{job_id}?since=3")
        assert response.status_code == 200
        data = response.get_json()
        assert data["results"] == []
        assert data["next_since"] == 3
    finally:
        routes_module._orchestrators.pop(job_id, None)


def test_enrichment_status_since_beyond_length(client):
    """?since=99 with 3 results returns 0 results and next_since == 3."""
    import app.routes._helpers as routes_module

    mock_orch = _make_three_result_orchestrator()
    job_id = "cursor_beyond_job"
    routes_module._orchestrators[job_id] = mock_orch
    try:
        response = client.get(f"/enrichment/status/{job_id}?since=99")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["results"]) == 0
        assert data["next_since"] == 3
    finally:
        routes_module._orchestrators.pop(job_id, None)
