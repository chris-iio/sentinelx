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
from collections import OrderedDict
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from unittest.mock import MagicMock, call, patch

from app.pipeline.models import IOCType
from tests.helpers import make_domain_ioc, make_ipv4_ioc


# ---------------------------------------------------------------------------
# Functional tests
# ---------------------------------------------------------------------------


def test_route_helper_modules_use_relative_sibling_imports():
    """Route helper modules should not import siblings through the package facade."""
    package_imports: list[str] = []

    for path in sorted(Path("app/routes").glob("*.py")):
        if path.name in {"__init__.py", "api.py"}:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("from app.routes") or line.startswith("import app.routes"):
                package_imports.append(f"{path}:{line}")

    assert package_imports == []


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


def test_analyze_rejects_invalid_mode_before_extraction(client, monkeypatch):
    """Browser analyze should share the API mode allowlist."""
    from app.routes import analysis as analysis_routes
    from app.routes import analysis_modes

    monkeypatch.setattr(
        analysis_routes,
        "run_pipeline",
        lambda _text: (_ for _ in ()).throw(
            AssertionError("invalid mode should not reach extraction")
        ),
    )

    response = client.post("/analyze", data={"text": "8.8.8.8", "mode": "turbo"})

    assert response.status_code == 400
    assert b"Invalid mode selected" in response.data
    assert analysis_modes.VALID_ANALYSIS_MODES == frozenset(("offline", "online"))
    assert analysis_modes.DEFAULT_ANALYSIS_MODE == analysis_modes.ANALYSIS_MODE_OFFLINE
    assert analysis_modes.valid_analysis_modes_label() == "'offline' or 'online'"
    assert not hasattr(analysis_routes, "VALID_ANALYSIS_MODES")


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


def test_browser_analyze_uses_shared_intake_workflow() -> None:
    """Browser analyze should not duplicate validation and extraction control flow."""
    from app.routes import analysis as analysis_routes
    from app.routes import analysis_results
    from app.routes.analysis_workflow import (
        ANALYSIS_ERROR_EMPTY_TEXT,
        ANALYSIS_ERROR_INVALID_MODE,
        analysis_request_values,
    )

    source = inspect.getsource(analysis_routes.analyze)
    helper_source = inspect.getsource(analysis_results.browser_analyze_result)
    online_source = inspect.getsource(analysis_results.start_online_analysis)
    values = analysis_request_values({"text": " 8.8.8.8 ", "mode": "online"})

    assert values.text == " 8.8.8.8 "
    assert values.mode == "online"
    assert "browser_analyze_route_response(" in source
    assert "browser_analyze_result(" not in source
    assert "request.form" in source
    assert "registry=current_app.registry" in source
    assert "cache_store=current_app.cache_store" in source
    assert "online_limits=online._online_limits_from_config(current_app.config)" in source
    assert "build_analysis_intake" not in source
    assert "analysis_request_values(request.form)" not in source
    assert "start_online_analysis" not in source
    assert "build_analysis_intake" in helper_source
    assert "analysis_request_values(values)" in helper_source
    assert '"empty_text"' not in helper_source
    assert '"invalid_mode"' not in helper_source
    assert "ANALYSIS_ERROR_EMPTY_TEXT" in helper_source
    assert "ANALYSIS_ERROR_INVALID_MODE" in helper_source
    assert ANALYSIS_ERROR_EMPTY_TEXT == "empty_text"
    assert ANALYSIS_ERROR_INVALID_MODE == "invalid_mode"
    assert "start_online" in helper_source
    assert "registry=registry" in helper_source
    assert "cache_store=cache_store" in helper_source
    assert "online_limits=online_limits" in helper_source
    assert "_online_admission(" in online_source
    assert "registry=registry" in online_source
    assert "cache=cache_store" in online_source
    assert "online_limits=online_limits" in online_source
    assert "request.form.get" not in source
    assert "run_pipeline(text)" not in source
    assert "_online_admission" not in source


def test_start_online_analysis_uses_explicit_runtime_dependencies_for_current_setup() -> None:
    """Online start should pass explicit registry/cache dependencies when supported."""
    from app.pipeline.models import IOC, IOCType
    from app.routes.analysis_workflow import start_online_analysis

    ioc = IOC(value="8.8.8.8", type=IOCType.IPV4, raw_match="8.8.8.8")
    registry = MagicMock()
    registry.configured.return_value = [object()]
    registry.provider_count_for_type.return_value = 1
    cache_store = object()
    history_store = object()
    calls: list[dict[str, object]] = []

    def setup_orchestrator(
        iocs,
        text,
        mode,
        history,
        configured_providers=None,
        *,
        registry=None,
        cache=None,
    ):
        calls.append(
            {
                "iocs": iocs,
                "text": text,
                "mode": mode,
                "history": history,
                "configured_providers": configured_providers,
                "registry": registry,
                "cache": cache,
            }
        )
        return "job-123", object(), registry

    start = start_online_analysis(
        iocs=[ioc],
        text="8.8.8.8",
        mode="online",
        history_store=history_store,
        registry=registry,
        cache_store=cache_store,
        online_limits=(50, 200),
        setup_orchestrator=setup_orchestrator,
    )

    assert start.job_id == "job-123"
    assert calls[0]["registry"] is registry
    assert calls[0]["cache"] is cache_store
    assert calls[0]["history"] is history_store


def test_start_online_analysis_avoids_runtime_signature_branching() -> None:
    """Online start should call the current setup seam directly."""
    from app.pipeline.models import IOC, IOCType
    from app.routes import analysis_workflow
    from app.routes.analysis_workflow import start_online_analysis

    ioc = IOC(value="8.8.8.8", type=IOCType.IPV4, raw_match="8.8.8.8")
    registry = MagicMock()
    registry.configured.return_value = [object()]
    registry.provider_count_for_type.return_value = 1
    history_store = object()
    calls: list[dict[str, object]] = []

    def setup_orchestrator(
        iocs,
        text,
        mode,
        history,
        configured_providers=None,
        *,
        registry=None,
        cache=None,
    ):
        calls.append(
            {
                "iocs": iocs,
                "text": text,
                "mode": mode,
                "history": history,
                "configured_providers": configured_providers,
                "registry": registry,
                "cache": cache,
            }
        )
        return "job-direct", object(), registry

    cache_store = object()
    start = start_online_analysis(
        iocs=[ioc],
        text="8.8.8.8",
        mode="online",
        history_store=history_store,
        registry=registry,
        cache_store=cache_store,
        online_limits=(50, 200),
        setup_orchestrator=setup_orchestrator,
    )
    source = inspect.getsource(analysis_workflow.start_online_analysis)

    assert start.job_id == "job-direct"
    assert calls[0]["history"] is history_store
    assert calls[0]["registry"] is registry
    assert calls[0]["cache"] is cache_store
    assert "inspect.signature" not in source
    assert "_accepts_runtime_dependencies" not in source


def test_browser_analyze_route_delegates_render_result_helper(client, monkeypatch) -> None:
    """Browser analyze route should leave decisions and response application to helpers."""
    from app.routes import analysis as analysis_routes

    calls: list[dict[str, object]] = []

    def route_response(values, **kwargs):
        calls.append({"values": values, **kwargs})
        return kwargs["render_template"](
            "index.html",
            recent_analyses=[],
            recent_analyses_unavailable=False,
        ), 203

    monkeypatch.setattr(analysis_routes, "browser_analyze_route_response", route_response)

    response = client.post("/analyze", data={"text": "8.8.8.8", "mode": "offline"})
    route_source = inspect.getsource(analysis_routes.analyze)

    assert response.status_code == 203
    assert calls[0]["values"]["text"] == "8.8.8.8"
    assert calls[0]["has_content"] is analysis_routes.has_non_whitespace
    assert calls[0]["extract_iocs"] is analysis_routes.run_pipeline
    assert calls[0]["history_store"] is client.application.history_store
    assert calls[0]["registry"] is client.application.registry
    assert calls[0]["cache_store"] is client.application.cache_store
    assert calls[0]["app_logger"] is client.application.logger
    assert calls[0]["setup_orchestrator"] is analysis_routes._setup_orchestrator
    assert callable(calls[0]["recent_context"])
    assert "if intake.error" not in route_source
    assert "if intake.mode" not in route_source
    assert "start_online_analysis(" not in route_source
    assert "_log_online_limit_rejection(" not in route_source
    assert "browser_analyze_route_response(" in route_source
    assert "browser_analyze_result(" not in route_source
    assert "apply_browser_analyze_result(" not in route_source
    assert "if result.flash_message" not in route_source
    assert "if result.redirect_endpoint" not in route_source
    assert "return render_template(result.template_name" not in route_source


def test_apply_browser_analyze_result_owns_flask_response_application() -> None:
    """Browser analyze result flash, redirect, and render application should be shared."""
    from app.routes import analysis as analysis_routes
    from app.routes import browser_responses
    from app.routes import analysis_results

    calls: list[tuple[str, object]] = []

    def flash_message(message: str, category: str) -> None:
        calls.append(("flash", (message, category)))

    def endpoint_url(endpoint: str) -> str:
        calls.append(("url_for", endpoint))
        return f"/endpoint/{endpoint}"

    def redirect_to(url: str) -> tuple[str, str]:
        calls.append(("redirect", url))
        return ("redirect", url)

    def render_template(template_name: str | None, **context):
        calls.append(("render", (template_name, context)))
        return ("rendered", template_name, context)

    redirect_result = analysis_results.apply_browser_analyze_result(
        analysis_results.BrowserAnalyzeResult(
            flash_message="Configure providers",
            flash_category="warning",
            redirect_endpoint="main.settings_get",
        ),
        flash_message=flash_message,
        redirect_to=redirect_to,
        endpoint_url=endpoint_url,
        render_template=render_template,
    )
    rendered_result = analysis_results.apply_browser_analyze_result(
        analysis_results.BrowserAnalyzeResult(
            template_name="results.html",
            context={"mode": "offline"},
            status=207,
        ),
        flash_message=flash_message,
        redirect_to=redirect_to,
        endpoint_url=endpoint_url,
        render_template=render_template,
    )
    route_source = inspect.getsource(analysis_routes.analyze)
    helper_source = inspect.getsource(analysis_results.apply_browser_analyze_result)
    route_helper_source = inspect.getsource(analysis_results.browser_analyze_route_response)
    shared_source = inspect.getsource(browser_responses.apply_flash_redirect)

    assert redirect_result == ("redirect", "/endpoint/main.settings_get")
    assert rendered_result == (("rendered", "results.html", {"mode": "offline"}), 207)
    assert calls == [
        ("flash", ("Configure providers", "warning")),
        ("url_for", "main.settings_get"),
        ("redirect", "/endpoint/main.settings_get"),
        ("render", ("results.html", {"mode": "offline"})),
    ]
    assert "browser_analyze_route_response(" in route_source
    assert "apply_browser_analyze_result(" not in route_source
    assert "if result.flash_message" not in route_source
    assert "if result.redirect_endpoint" not in route_source
    assert "render_template(result.template_name" not in route_source
    assert "if result.redirect_endpoint" in helper_source
    assert "apply_flash_redirect(" in helper_source
    assert "apply_template_result(" in helper_source
    assert "browser_analyze_result(" in route_helper_source
    assert "apply_browser_analyze_result(" in route_helper_source
    assert "flash_message=flash_message" in route_helper_source
    assert "render_template=render_template" in route_helper_source
    assert "lambda status: None" not in helper_source
    assert "render_template(result.template_name" not in helper_source
    assert "if result.message" in shared_source


def test_apply_flash_redirect_owns_browser_flash_redirect_response_application() -> None:
    """Shared browser flash/redirect helper should preserve call order."""
    from app.routes import browser_responses

    calls: list[tuple[str, object]] = []

    def flash_message(message: str, category: str) -> None:
        calls.append(("flash", (message, category)))

    def redirect_to(url: str) -> tuple[str, str]:
        calls.append(("redirect", url))
        return ("redirect", url)

    flashed = browser_responses.apply_flash_redirect(
        browser_responses.FlashRedirect("/settings", "Saved.", "success"),
        flash_message=flash_message,
        redirect_to=redirect_to,
    )
    silent = browser_responses.apply_flash_redirect(
        browser_responses.FlashRedirect("/results"),
        flash_message=flash_message,
        redirect_to=redirect_to,
    )

    assert flashed == ("redirect", "/settings")
    assert silent == ("redirect", "/results")
    assert calls == [
        ("flash", ("Saved.", "success")),
        ("redirect", "/settings"),
        ("redirect", "/results"),
    ]


def test_recent_analyses_context_lives_in_result_helper() -> None:
    """Index recent-history fail-open context should live outside the route module."""
    from app.routes import analysis as analysis_routes
    from app.routes import analysis_results

    store = MagicMock()
    logger = MagicMock()
    recent = [{"id": "analysis-1"}]
    store.list_recent.return_value = recent

    context = analysis_results.recent_analyses_context(store, logger, limit=3)
    result = analysis_results.index_page_result(store, logger, limit=3)
    route_response_calls: list[tuple[str | None, dict[str, object]]] = []

    def render_page(template_name: str | None, **context):
        route_response_calls.append((template_name, context))
        return ("rendered", template_name, context)

    route_response = analysis_results.index_page_route_response(
        store,
        logger,
        render_template=render_page,
        limit=3,
    )
    route_source = inspect.getsource(analysis_routes)
    helper_source = inspect.getsource(analysis_results.recent_analyses_context)
    result_source = inspect.getsource(analysis_results.index_page_result)
    route_helper_source = inspect.getsource(analysis_results.index_page_route_response)

    assert context == {
        "recent_analyses": recent,
        "recent_analyses_unavailable": False,
    }
    assert result.template_name == "index.html"
    assert result.context == context
    assert result.status == 200
    assert route_response == (("rendered", "index.html", context), 200)
    assert route_response_calls == [("index.html", context)]
    assert store.list_recent.call_args_list == [call(limit=3), call(limit=3), call(limit=3)]
    logger.warning.assert_not_called()
    assert "_recent_analyses_context" not in route_source
    assert "list_recent(" not in route_source
    assert "logger.warning(" not in route_source
    assert "try:" not in route_source
    assert "index_page_route_response(" in route_source
    assert "index_page_result(" not in inspect.getsource(analysis_routes.index)
    assert "apply_template_result(" not in route_source
    assert "render_template(" not in inspect.getsource(analysis_routes.index)
    assert "list_recent(limit=limit)" in helper_source
    assert "TemplateResult(" in result_source
    assert "\"index.html\"" in result_source
    assert "apply_template_result(" in route_helper_source
    assert "index_page_result(" in route_helper_source
    assert "render_template=render_template" in route_helper_source

    store.list_recent.side_effect = RuntimeError("raw IOC 203.0.113.10 secret-token")
    failed_context = analysis_results.recent_analyses_context(store, logger, limit=2)

    assert failed_context == {
        "recent_analyses": [],
        "recent_analyses_unavailable": True,
    }
    logger.warning.assert_called_once_with(
        "Recent history lookup failed for index page: %s",
        "RuntimeError",
    )


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
    from app.routes import ioc_payloads

    iocs = [
        make_ipv4_ioc("8.8.8.8"),
        make_ipv4_ioc("1.1.1.1"),
        make_domain_ioc("example.com"),
    ]
    monkeypatch.setattr(analysis_routes, "run_pipeline", lambda _text: iocs)

    grouped = ioc_payloads._group_iocs_for_template(iocs)
    response = client.post("/analyze", data={"text": "8.8.8.8 example.com", "mode": "offline"})

    assert grouped[IOCType.IPV4] == iocs[:2]
    assert grouped[IOCType.DOMAIN] == [iocs[2]]
    assert response.status_code == 200
    assert b"8.8.8.8" in response.data


def test_analyze_template_grouping_reuses_shared_group_helper(client, monkeypatch):
    """Browser analyze should delegate to the optimized pipeline grouping helper."""
    from app.routes import ioc_payloads

    iocs = [
        make_ipv4_ioc("8.8.8.8"),
        make_ipv4_ioc("1.1.1.1"),
        make_domain_ioc("example.com"),
    ]
    calls: list[list] = []

    def group_once(seen_iocs):
        calls.append(seen_iocs)
        return {IOCType.IPV4: seen_iocs[:2], IOCType.DOMAIN: [seen_iocs[2]]}

    monkeypatch.setattr(ioc_payloads, "group_by_type", group_once)

    grouped = ioc_payloads._group_iocs_for_template(iocs)

    assert grouped[IOCType.IPV4] == iocs[:2]
    assert grouped[IOCType.DOMAIN] == [iocs[2]]
    assert calls == [iocs]
    assert "group_by_type" in ioc_payloads._group_iocs_for_template.__code__.co_names
    assert "setdefault" not in ioc_payloads._group_iocs_for_template.__code__.co_names


def test_analyze_template_grouping_preserves_pipeline_short_paths() -> None:
    """Route-level grouping should preserve pipeline empty/single/pair fast paths."""
    from app.routes import ioc_payloads

    ioc_a = make_ipv4_ioc("8.8.8.8")
    ioc_b = make_domain_ioc("example.com")

    class NoIterIocs(list):
        def __iter__(self):
            raise AssertionError("route grouping should preserve shared short paths")

        def __getitem__(self, index):
            if isinstance(index, slice):
                raise AssertionError("route grouping should not slice short IOC lists")
            return super().__getitem__(index)

    assert ioc_payloads._group_iocs_for_template(NoIterIocs()) == {}
    assert ioc_payloads._group_iocs_for_template(NoIterIocs([ioc_a])) == {
        IOCType.IPV4: [ioc_a],
    }
    assert ioc_payloads._group_iocs_for_template(NoIterIocs([ioc_a, ioc_b])) == {
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


def test_sensitive_routes_reject_non_loopback_remote_addr(app):
    """Local-admin routes are guarded even when Host validation passes."""
    import app as app_module

    boundary_source = inspect.getsource(app_module._is_local_admin_path)
    assert "for prefix in _LOCAL_ADMIN_PATH_PREFIXES" not in boundary_source
    assert "_path_matches_prefix(path, " in boundary_source
    assert app_module._is_local_admin_path("/settings")
    assert app_module._is_local_admin_path("/settings/providers")
    assert app_module._is_local_admin_path("/diagnostics/export")
    assert app_module._is_local_admin_path("/api/status/missing-job")
    assert not app_module._is_local_admin_path("/api/analyze")

    with app.test_client() as raw_client:
        for path in (
            "/settings",
            "/history",
            "/diagnostics/export",
            "/enrichment/status/missing-job",
            "/api/status/missing-job",
        ):
            response = raw_client.get(path, environ_base={"REMOTE_ADDR": "203.0.113.10"})
            assert response.status_code == 403


def test_public_routes_still_allow_non_loopback_remote_addr(app):
    """The local-admin boundary must not block the intake page itself."""
    with app.test_client() as raw_client:
        response = raw_client.get("/", environ_base={"REMOTE_ADDR": "203.0.113.10"})
        assert response.status_code == 200


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
    from app.routes import analysis_results
    from app.routes import ioc_payloads

    mock_registry = MagicMock()
    mock_registry.configured.side_effect = AssertionError(
        "zero-IOC online analysis should not check provider configuration"
    )
    client.application.registry = mock_registry

    def fail_group_iocs(_iocs):
        raise AssertionError("zero-IOC browser analysis should not group template IOCs")

    monkeypatch.setattr(ioc_payloads, "_group_iocs_for_template", fail_group_iocs)

    with patch("app.routes.enrichment_jobs._enrichment_pool") as mock_pool:
        response = client.post(
            "/analyze",
            data={"text": "Hello world, no indicators here", "mode": "online"},
        )

    assert response.status_code == 200
    assert b"No IOCs detected" in response.data or b"No IOCs found" in response.data
    assert b"data-job-id" not in response.data
    mock_pool.submit.assert_not_called()
    helper_source = inspect.getsource(analysis_results.browser_analyze_result)
    assert "no_results else _group_iocs_for_template" in inspect.getsource(
        ioc_payloads._ioc_template_context
    )
    assert "_ioc_template_context" not in inspect.getsource(analysis_routes.analyze)
    assert "browser_analyze_result" not in inspect.getsource(analysis_routes.analyze)
    assert "_ioc_template_context" in helper_source


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


def test_analyze_public_template_preserves_grouped_ioc_cards(client, monkeypatch):
    """Rendered analysis results should expose grouped IOC cards without leaking raw HTML."""
    from app.pipeline.models import IOC
    from app.routes import analysis as analysis_routes

    iocs = [
        IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8[.]8[.]8[.]8"),
        IOC(type=IOCType.DOMAIN, value="evil.example", raw_match="<script>alert(1)</script>"),
        IOC(type=IOCType.IPV4, value="1.1.1.1", raw_match="1[.]1[.]1[.]1"),
    ]
    monkeypatch.setattr(analysis_routes, "run_pipeline", lambda _text: iocs)

    response = client.post("/analyze", data={"text": "synthetic grouped indicators", "mode": "offline"})
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Found 3 unique IOCs" in html
    assert "8.8.8.8" in html
    assert "1.1.1.1" in html
    assert "evil.example" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)</script>" not in html


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
    from app.routes import ioc_payloads

    mock_registry = MagicMock()
    mock_registry.configured.return_value = []
    client.application.registry = mock_registry

    monkeypatch.setattr(
        ioc_payloads,
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
        patch("app.routes.enrichment_jobs.EnrichmentOrchestrator") as MockOrchestrator,
        patch("app.routes.enrichment_jobs._enrichment_pool") as mock_pool,
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
    from app.routes import provider_metadata

    mock_registry = MagicMock()
    mock_registry.provider_count_for_type.side_effect = (
        lambda ioc_type: 3 if ioc_type == IOCType.SHA256 else 1
    )
    mock_registry.providers_for_type.side_effect = AssertionError(
        "provider-count metadata should use provider_count_for_type"
    )

    provider_counts = json.loads(provider_metadata.provider_counts_json(mock_registry))

    assert provider_counts["sha256"] == 3
    assert provider_counts["ipv4"] == 1
    assert "cve" not in provider_counts
    assert IOCType.CVE not in provider_metadata.PROVIDER_COUNT_IOC_TYPES
    assert tuple(provider_metadata.PROVIDER_COUNT_IOC_TYPES) is provider_metadata.PROVIDER_COUNT_IOC_TYPES
    assert "encode_json_object" in provider_metadata.provider_counts_json.__code__.co_names
    source = inspect.getsource(provider_metadata.provider_counts_json)
    assert "for ioc_type in PROVIDER_COUNT_IOC_TYPES" not in source
    assert '"ipv4": registry.provider_count_for_type(IOCType.IPV4)' in source
    assert '"email": registry.provider_count_for_type(IOCType.EMAIL)' in source
    assert mock_registry.providers_for_type.call_count == 0
    assert mock_registry.provider_count_for_type.call_count == len(provider_metadata.PROVIDER_COUNT_IOC_TYPES)
    assert all(
        getattr(const, "co_name", None) != "<dictcomp>"
        for const in provider_metadata.provider_counts_json.__code__.co_consts
    )


def test_provider_coverage_reuses_configured_provider_list():
    """Provider coverage should reuse configured providers and count registered providers directly."""
    from app.routes import provider_metadata

    configured_providers = [MagicMock()]
    mock_registry = MagicMock()
    mock_registry.registered_count.return_value = 2
    mock_registry.all.side_effect = AssertionError(
        "provider coverage should not allocate all registered providers"
    )
    mock_registry.configured.side_effect = AssertionError(
        "provider coverage should reuse the caller's configured-provider list"
    )

    coverage = provider_metadata.provider_coverage(mock_registry, configured_providers)

    assert coverage == {"registered": 2, "configured": 1, "needs_key": 1}
    mock_registry.registered_count.assert_called_once()
    assert mock_registry.all.call_count == 0
    assert mock_registry.configured.call_count == 0


def test_online_fanout_diagnostics_uses_direct_count_path():
    """Admission diagnostics should count fanout without allocating provider lists."""
    from app.routes.online import _online_fanout_diagnostics
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


def test_online_admission_centralizes_provider_and_limit_decision(app, monkeypatch):
    """Online routes should share provider configuration and limit admission."""
    from app.pipeline.models import IOC
    from app.routes import online

    providers = [MagicMock()]
    mock_registry = MagicMock()
    mock_registry.configured.return_value = providers
    mock_registry.provider_count_for_type.return_value = 2
    iocs = [
        IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4"),
        IOC(type=IOCType.IPV4, value="5.6.7.8", raw_match="5.6.7.8"),
    ]
    monkeypatch.setattr(online, "_online_limits_from_config", lambda _config=None: (10, 3))

    with app.app_context():
        admission = online._online_admission(iocs, registry=mock_registry)
    source = inspect.getsource(online._online_admission)

    assert admission.registry is mock_registry
    assert admission.configured_providers is providers
    assert admission.has_configured_providers is True
    assert admission.rejected_by_limit is True
    assert admission.fanout_diagnostics["dispatch_count"] == 4
    assert "current_app.registry" not in source
    assert "registry.configured()" in source
    assert "online_limits" in source
    mock_registry.configured.assert_called_once_with()
    assert mock_registry.provider_count_for_type.call_count == 1


def test_online_limits_config_resolution_is_named_boundary() -> None:
    """Online limit parsing should not own the Flask-global fallback expression."""
    from app.routes import online

    explicit_config = {
        "ONLINE_MAX_IOCS": "7",
        "ONLINE_MAX_DISPATCHES": "11",
    }
    limits_source = inspect.getsource(online._online_limits_from_config)
    resolver_source = inspect.getsource(online._resolve_online_limit_config)

    assert online._online_limits_from_config(explicit_config) == (7, 11)
    assert "_resolve_online_limit_config(config)" in limits_source
    assert "current_app.config if config is None else config" not in limits_source
    assert "current_app.config if config is None else config" in resolver_source


def test_online_admission_short_circuits_when_no_providers(app, monkeypatch):
    """Missing-provider Online requests should not compute fan-out diagnostics."""
    from app.pipeline.models import IOC
    from app.routes import online

    mock_registry = MagicMock()
    mock_registry.configured.return_value = []
    mock_registry.provider_count_for_type.side_effect = AssertionError(
        "missing provider admission should not inspect fan-out"
    )
    monkeypatch.setattr(
        online,
        "_online_limits_from_config",
        lambda _config=None: (_ for _ in ()).throw(
            AssertionError("missing provider admission should not read limits")
        ),
    )

    with app.app_context():
        admission = online._online_admission(
            [IOC(type=IOCType.IPV4, value="1.2.3.4", raw_match="1.2.3.4")],
            registry=mock_registry,
        )

    assert admission.has_configured_providers is False
    assert admission.rejected_by_limit is False
    assert admission.fanout_diagnostics is None


def test_online_limit_rejection_logging_is_shared() -> None:
    """HTML and API routes should share Online limit warning formatting."""
    from app.routes import analysis as analysis_routes
    from app.routes import analysis_results
    from app.routes import api as api_routes
    from app.routes import api_analysis
    from app.routes import online

    diagnostics = {
        "ioc_count": 2,
        "dispatch_count": 5,
        "max_iocs": 1,
        "max_dispatches": 4,
    }
    app_logger = MagicMock()

    online._log_online_limit_rejection(
        diagnostics,
        app_logger=app_logger,
        surface="api",
    )
    online._log_online_limit_rejection(
        diagnostics,
        app_logger=app_logger,
        surface="html",
    )
    api_source = inspect.getsource(api_routes.api_analyze)
    api_helper_source = inspect.getsource(api_analysis.api_analyze_result)
    analysis_source = inspect.getsource(analysis_routes.analyze)
    analysis_helper_source = inspect.getsource(analysis_results.browser_analyze_result)
    helper_source = inspect.getsource(online._log_online_limit_rejection)

    assert app_logger.warning.call_args_list[0].args == (
        "%s enrichment rejected by admission guard: iocs=%s dispatches=%s limits=%s/%s",
        "API online",
        2,
        5,
        1,
        4,
    )
    assert app_logger.warning.call_args_list[1].args == (
        "%s enrichment rejected by admission guard: iocs=%s dispatches=%s limits=%s/%s",
        "Online",
        2,
        5,
        1,
        4,
    )
    assert "_log_online_limit_rejection(" not in api_source
    assert "_log_online_limit_rejection(" in api_helper_source
    assert "_log_online_limit_rejection(" not in analysis_source
    assert "_log_online_limit_rejection(" in analysis_helper_source
    assert "fanout_diagnostics[\"ioc_count\"]" not in api_source
    assert "fanout_diagnostics[\"ioc_count\"]" not in api_helper_source
    assert "fanout_diagnostics[\"ioc_count\"]" not in analysis_source
    assert "fanout_diagnostics[\"ioc_count\"]" not in analysis_helper_source
    assert "dispatch_count" in helper_source
    assert "max_dispatches" in helper_source


def test_enrichable_count_caches_provider_counts_by_ioc_type():
    """Progress totals should not recount providers for repeated IOC types."""
    from app.routes import provider_metadata

    class NoIterIocs(list):
        def __iter__(self):
            raise AssertionError("short enrichable counts should not iterate")

        def __getitem__(self, index):
            if isinstance(index, slice):
                raise AssertionError("short enrichable counts should not slice")
            return super().__getitem__(index)

    mock_registry = MagicMock()
    mock_registry.provider_count_for_type.side_effect = (
        lambda ioc_type: 2 if ioc_type == IOCType.IPV4 else 3
    )
    mock_registry.providers_for_type.side_effect = AssertionError(
        "enrichable progress count should use provider_count_for_type"
    )
    iocs = NoIterIocs([
        make_ipv4_ioc("1.2.3.4"),
        make_ipv4_ioc("5.6.7.8"),
        make_domain_ioc("example.com"),
        make_ipv4_ioc("9.9.9.9"),
    ])

    count = provider_metadata.enrichable_count(iocs, mock_registry)

    assert count == 9
    assert mock_registry.provider_count_for_type.call_count == 2
    assert mock_registry.provider_count_for_type.call_args_list[0].args == (IOCType.IPV4,)
    assert mock_registry.provider_count_for_type.call_args_list[1].args == (IOCType.DOMAIN,)
    assert mock_registry.providers_for_type.call_count == 0
    assert "len" in provider_metadata.enrichable_count.__code__.co_names
    assert "ioc_count == 4" in inspect.getsource(provider_metadata.enrichable_count)
    assert "_provider_count_for_type_cached" in provider_metadata.enrichable_count.__code__.co_names


def test_enrichable_count_long_path_delegates_cache_miss_assignment():
    """Long enrichable counts should share one provider-count cache miss helper."""
    from app.routes import provider_metadata

    mock_registry = MagicMock()
    mock_registry.provider_count_for_type.side_effect = (
        lambda ioc_type: 2 if ioc_type == IOCType.IPV4 else 3
    )
    iocs = [
        make_ipv4_ioc("1.2.3.4"),
        make_ipv4_ioc("5.6.7.8"),
        make_domain_ioc("example.com"),
        make_ipv4_ioc("9.9.9.9"),
        make_domain_ioc("example.net"),
    ]

    count = provider_metadata.enrichable_count(iocs, mock_registry)

    assert count == 12
    assert mock_registry.provider_count_for_type.call_count == 2
    assert "counts_by_type[ioc_type] =" in inspect.getsource(
        provider_metadata._provider_count_for_type_cached
    )
    assert "counts_by_type[ioc_type] =" not in inspect.getsource(
        provider_metadata.enrichable_count
    )


def test_analysis_route_delegates_provider_metadata_helpers():
    """Provider metadata helper aliases should stay out of the Flask route module."""
    from app.routes import analysis as analysis_routes

    source = inspect.getsource(analysis_routes)

    assert "_provider_counts_json" not in source
    assert "_provider_coverage" not in source
    assert "_enrichable_count" not in source
    assert "_group_iocs_for_template" not in source
    assert "_ioc_template_context" not in source
    assert "_online_result_template_extras" not in source
    assert "def _provider_counts_json" not in source
    assert "def _provider_coverage" not in source
    assert "def _enrichable_count" not in source


def test_online_result_template_extras_own_browser_shape():
    """Browser Online result context should live outside the Flask route body."""
    from app.routes import analysis as analysis_routes
    from app.routes import analysis_results
    from app.routes.analysis_results import online_result_template_extras
    from app.routes.analysis_workflow import OnlineStartDecision
    from app.routes.online import OnlineAdmission

    configured_providers = [MagicMock()]
    mock_registry = MagicMock()
    mock_registry.provider_count_for_type.return_value = 2
    mock_registry.registered_count.return_value = 3
    mock_registry.configured.side_effect = AssertionError(
        "template extras should reuse the admission configured-provider list"
    )
    mock_registry.all.side_effect = AssertionError(
        "template extras should not allocate all registered providers"
    )
    accepted_diagnostics = {
        "allowed": True,
        "dispatch_count": 4,
        "ioc_count": 2,
        "max_iocs": 50,
        "max_dispatches": 200,
    }
    rejected_diagnostics = {
        "allowed": False,
        "dispatch_count": 300,
        "ioc_count": 75,
        "max_iocs": 50,
        "max_dispatches": 200,
    }

    accepted = online_result_template_extras(
        OnlineStartDecision(
            admission=OnlineAdmission(
                registry=mock_registry,
                configured_providers=configured_providers,
                fanout_diagnostics=accepted_diagnostics,
            ),
            job_id="job123",
        )
    )
    rejected = online_result_template_extras(
        OnlineStartDecision(
            admission=OnlineAdmission(
                registry=mock_registry,
                configured_providers=configured_providers,
                fanout_diagnostics=rejected_diagnostics,
            ),
            job_id=None,
        )
    )
    route_source = inspect.getsource(analysis_routes.analyze)
    helper_source = inspect.getsource(analysis_results.browser_analyze_result)

    assert accepted["job_id"] == "job123"
    assert accepted["enrichable_count"] == 4
    assert accepted["provider_coverage"] == {"registered": 3, "configured": 1, "needs_key": 2}
    assert "provider_counts" in accepted
    assert "online_limit_diagnostics" not in accepted
    assert rejected["online_limit_diagnostics"] is rejected_diagnostics
    assert "job_id" not in rejected
    assert "online_result_template_extras(start)" not in route_source
    assert "online_result_template_extras(start)" in helper_source
    assert "\"online_limit_diagnostics\"" not in route_source
    assert "\"provider_counts\"" not in route_source
    assert "\"provider_coverage\"" not in route_source
    assert "\"enrichable_count\"" not in route_source
    mock_registry.configured.assert_not_called()
    mock_registry.all.assert_not_called()


def test_analyze_online_reuses_fanout_dispatch_count_for_progress_total(client, monkeypatch):
    """Online browser progress should reuse admission fanout instead of recounting providers."""
    from app.pipeline.models import IOC
    from app.routes import analysis as analysis_routes
    from app.routes import analysis_results

    iocs = [
        IOC(type=IOCType.IPV4, value="8.8.8.8", raw_match="8.8.8.8"),
        IOC(type=IOCType.IPV4, value="1.1.1.1", raw_match="1.1.1.1"),
    ]
    monkeypatch.setattr(analysis_routes, "run_pipeline", lambda _text: iocs)
    monkeypatch.setattr(
        analysis_results,
        "provider_counts_json",
        lambda _registry: "{}",
    )
    mock_registry = MagicMock()
    mock_registry.configured.return_value = [MagicMock()]
    mock_registry.all.return_value = [MagicMock()]
    mock_registry.provider_count_for_type.return_value = 2
    client.application.registry = mock_registry

    with (
        patch("app.routes.enrichment_jobs.EnrichmentOrchestrator") as MockOrchestrator,
        patch("app.routes.enrichment_jobs._enrichment_pool"),
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
    from app.routes.enrichment_diagnostics import _coerce_orchestration_diagnostics_for_export

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
    from app.routes.enrichment_diagnostics import _coerce_orchestration_diagnostics_for_export

    raw = {"events": _NoSliceList(f"event-{index}" for index in range(30))}

    diagnostics = _coerce_orchestration_diagnostics_for_export(raw)

    assert diagnostics["events"][0] == "event-0"
    assert diagnostics["events"][-1] == "event-24"
    assert len(diagnostics["events"]) == 25


def test_orchestration_diagnostics_export_coercion_accumulates_lists_directly():
    """Diagnostic export list coercion should not allocate a list-comprehension frame."""
    from app.routes.enrichment_diagnostics import (
        _coerce_export_list,
        _coerce_orchestration_diagnostics_for_export,
        _set_export_child_scalar,
        _set_export_value,
    )

    nested_code_names = {
        const.co_name
        for const in _coerce_orchestration_diagnostics_for_export.__code__.co_consts
        if hasattr(const, "co_name")
    }

    assert "<listcomp>" not in nested_code_names
    assert _coerce_orchestration_diagnostics_for_export({"events": ["ok", object()]}) == {
        "events": ["ok"]
    }
    assert "_set_export_value" in _coerce_orchestration_diagnostics_for_export.__code__.co_names
    assert "_coerce_export_list" not in _coerce_orchestration_diagnostics_for_export.__code__.co_names
    assert "_set_export_child_scalar" not in _coerce_orchestration_diagnostics_for_export.__code__.co_names
    export_source = inspect.getsource(_coerce_orchestration_diagnostics_for_export)
    value_source = inspect.getsource(_set_export_value)
    child_source = inspect.getsource(_set_export_child_scalar)
    assert "_set_export_child_scalar(children, child_key, value[child_key])" not in export_source
    assert "_set_export_child_scalar(children, child_key, value[child_key])" in value_source
    assert "_is_export_scalar(value)" in value_source
    assert "safe[key_text] = _export_scalar(value)" in value_source
    assert "value[:240] if isinstance(value, str) else value" not in value_source
    assert "_coerce_export_list(value)" in value_source
    assert "children[str(child_key)[:80]] = _export_scalar(child_value)" not in export_source
    assert "children[str(child_key)[:80]] = _export_scalar(child_value)" in child_source
    assert "<listcomp>" not in {
        const.co_name
        for const in _coerce_export_list.__code__.co_consts
        if hasattr(const, "co_name")
    }


def test_orchestration_diagnostics_export_coercion_skips_iteration_for_short_lists():
    from app.routes.enrichment_diagnostics import _coerce_export_list

    class NoIterList(list):
        def __iter__(self):
            raise AssertionError("short diagnostic export lists should not iterate")

        def __getitem__(self, index):
            if isinstance(index, slice):
                raise AssertionError("short diagnostic export lists should not slice")
            return super().__getitem__(index)

    assert _coerce_export_list(NoIterList([])) == []
    assert _coerce_export_list(NoIterList(["one"])) == ["one"]
    assert _coerce_export_list(NoIterList(["one", object()])) == ["one"]
    assert _coerce_export_list(NoIterList(["one", 2, None])) == ["one", 2, None]
    assert _coerce_export_list(NoIterList(["one", 2, None, object()])) == ["one", 2, None]
    assert "len" in _coerce_export_list.__code__.co_names
    assert "item_count == 4" in inspect.getsource(_coerce_export_list)
    assert "_append_export_scalar" in _coerce_export_list.__code__.co_names


def test_orchestration_status_string_coercion_avoids_strip_allocation():
    """Diagnostic status strings should trim through the shared bounded index helper."""
    from app.routes import enrichment_diagnostics

    source = inspect.getsource(
        enrichment_diagnostics._coerce_orchestration_status_for_diagnostics
    )
    assert '("total", "done")' not in source
    assert '("complete", "terminal")' not in source
    assert '("status", "terminal_reason", "error")' not in source
    assert "for field in _ORCHESTRATION_STATUS_COUNT_FIELDS" not in source
    assert "for field in _ORCHESTRATION_STATUS_BOOL_FIELDS" not in source
    assert "for field in _ORCHESTRATION_STATUS_TEXT_FIELDS" not in source
    assert '_coerce_status_count_field(status, data, "total")' in source
    assert '_coerce_status_bool_field(status, data, "terminal")' in source
    assert '_coerce_status_text_field(status, data, "error")' in source

    class MeasuredStripText(str):
        strip_calls = 0

        def strip(self, *_args, **_kwargs):
            raise AssertionError("diagnostic status coercion should not allocate through strip()")

    status = enrichment_diagnostics._coerce_orchestration_status_for_diagnostics({
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
        patch("app.routes.enrichment_jobs.EnrichmentOrchestrator") as MockOrchestrator,
        patch("app.routes.enrichment_jobs._enrichment_pool"),
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
        patch("app.routes.enrichment_jobs.EnrichmentOrchestrator") as MockOrchestrator,
        patch("app.routes.enrichment_jobs._enrichment_pool"),
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
        patch("app.routes.enrichment_jobs.EnrichmentOrchestrator") as MockOrchestrator,
        patch("app.routes.enrichment_jobs._enrichment_pool"),
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
    with patch("app.routes.enrichment_jobs._enrichment_pool") as mock_pool:
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

    with patch("app.routes.enrichment_jobs._enrichment_pool") as mock_pool:
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
        patch("app.routes.online._online_limits_from_config", return_value=(1, 200)) as limits,
        patch("app.routes.enrichment_jobs._enrichment_pool") as mock_pool,
    ):
        response = client.post(
            "/analyze",
            data={"text": "192.168.1.1 10.0.0.1", "mode": "online"},
        )

    assert response.status_code == 200
    assert b"Online enrichment was not started" in response.data
    limits.assert_called_once_with(client.application.config)
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

    with patch("app.routes.enrichment_jobs._enrichment_pool") as mock_pool:
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
    assert data["complete"] is False
    assert data["next_since"] == 7


def test_enrichment_status_returns_json(client):
    """GET /enrichment/status/{job_id} returns correct JSON structure."""
    import app.routes.enrichment_jobs as routes_module

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
    import app.routes.enrichment_jobs as routes_module
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
    import app.routes.enrichment_jobs as routes_module
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
    import app.routes.enrichment_jobs as routes_module
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
    import app.routes.enrichment_jobs as routes_module
    import app.routes.enrichment_status as status_module
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
        helper_source = inspect.getsource(status_module.serialized_status_results)
        nested_code_names = {
            const.co_name
            for const in routes_module._get_enrichment_status.__code__.co_consts
            if hasattr(const, "co_name")
        }
        assert "<listcomp>" not in nested_code_names
        assert 'status.get("cached_markers")' in helper_source
        assert "serialize_results(" in helper_source
    finally:
        routes_module._orchestrators.pop(job_id, None)


def test_serialize_result_skips_empty_cached_marker_map():
    """Empty cached-marker maps should not build per-result cache lookup keys."""
    from app.enrichment.models import EnrichmentResult
    from app.routes.enrichment_status import serialize_result

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

    serialized = serialize_result(result, EmptyMarkerMap())

    assert serialized["ioc_value"] == "192.0.2.10"
    assert "cached_at" not in serialized


def test_serialize_result_reuses_cache_marker_key_helper():
    """Route serialization should share the enrichment cache marker key format."""
    import app.enrichment.cache_payloads as cache_payloads
    import app.routes.enrichment_status as status_module
    from app.enrichment.models import EnrichmentResult

    result = EnrichmentResult(
        ioc=make_ipv4_ioc("192.0.2.11"),
        provider="CachedProvider",
        verdict="clean",
        detection_count=0,
        total_engines=5,
        scan_date=None,
        raw_stats={},
    )
    markers = {
        cache_payloads.cache_marker_key(result.ioc, result.provider): (
            "2026-04-25T00:00:00Z"
        )
    }
    source = inspect.getsource(status_module.serialize_result)

    serialized = status_module.serialize_result(result, markers)

    assert serialized["cached_at"] == "2026-04-25T00:00:00Z"
    assert status_module.cache_marker_key is cache_payloads.cache_marker_key
    assert "cache_marker_key(result.ioc, result.provider)" in source
    assert 'result.ioc.value + "|"' not in source


def test_serialize_results_shared_direct_accumulation(monkeypatch):
    """Batch result serialization should use the shared per-result serializer path."""
    import app.routes.enrichment_status as status_module

    calls = []
    cached_markers = {"192.0.2.10|CachedProvider": "2026-04-25T00:00:00Z"}

    def serialize_result(result, markers=None):
        calls.append((result, markers))
        return {"value": result}

    class NoIterResults(list):
        def __iter__(self):
            raise AssertionError("short result serialization should not iterate")

    assert status_module.serialize_results([], cached_markers, serializer=serialize_result) == []
    assert status_module.serialize_results(
        NoIterResults(["only"]),
        cached_markers,
        serializer=serialize_result,
    ) == [{"value": "only"}]
    serialized = status_module.serialize_results(
        NoIterResults(["first", "second"]),
        cached_markers,
        serializer=serialize_result,
    )
    triple_serialized = status_module.serialize_results(
        NoIterResults(["first", "second", "third"]),
        cached_markers,
        serializer=serialize_result,
    )
    four_serialized = status_module.serialize_results(
        NoIterResults(["first", "second", "third", "fourth"]),
        cached_markers,
        serializer=serialize_result,
    )
    nested_code_names = {
        const.co_name
        for const in status_module.serialize_results.__code__.co_consts
        if hasattr(const, "co_name")
    }

    assert serialized == [{"value": "first"}, {"value": "second"}]
    assert triple_serialized == [{"value": "first"}, {"value": "second"}, {"value": "third"}]
    assert four_serialized == [
        {"value": "first"},
        {"value": "second"},
        {"value": "third"},
        {"value": "fourth"},
    ]
    assert calls == [
        ("only", cached_markers),
        ("first", cached_markers),
        ("second", cached_markers),
        ("first", cached_markers),
        ("second", cached_markers),
        ("third", cached_markers),
        ("first", cached_markers),
        ("second", cached_markers),
        ("third", cached_markers),
        ("fourth", cached_markers),
    ]
    assert "<listcomp>" not in nested_code_names
    assert "len" in status_module.serialize_results.__code__.co_names
    assert "result_count == 4" in inspect.getsource(status_module.serialize_results)


def test_append_serialized_result_owns_long_path_mutation():
    """Long result serialization should share one append helper."""
    import app.routes.enrichment_status as status_module

    serialized: list[dict] = []
    markers = {"k": "cached"}

    def serialize_result(result, cached_markers=None):
        return {"value": result, "markers": cached_markers}

    status_module.append_serialized_result(
        serialized,
        "first",
        markers,
        serializer=serialize_result,
    )

    assert serialized == [{"value": "first", "markers": markers}]


def test_serialize_results_delegates_long_path_append() -> None:
    import app.routes.enrichment_status as status_module

    source = inspect.getsource(status_module.serialize_results)

    assert "append_serialized_result(serialized, result, cached_markers, serializer=serializer)" in source
    assert "serialized.append(serializer(result, cached_markers))" not in source


def test_enrichment_jobs_delegates_status_payload_helpers() -> None:
    """Route module should delegate pure polling payload shape to enrichment_status."""
    import app.routes.enrichment_jobs as routes_module
    import app.routes.enrichment_status as status_module

    source = inspect.getsource(routes_module)
    route_source = inspect.getsource(routes_module._get_enrichment_status)
    helper_source = inspect.getsource(status_module.enrichment_status_response)
    live_helper_source = inspect.getsource(status_module.live_status_response)

    assert not hasattr(routes_module, "_serialize_result")
    assert not hasattr(routes_module, "_build_status_payload")
    assert not hasattr(routes_module, "_terminal_status")
    assert not hasattr(routes_module, "enrichment_status_response")
    assert not hasattr(routes_module, "_STATUS_NOT_FOUND_REASONS")
    assert not hasattr(status_module.EnrichmentStatusResponse({"ok": True}, 200), "status_code")
    assert "def _serialize_result(" not in source
    assert "def _build_status_payload(" not in source
    assert "def _terminal_status(" not in source
    assert "enrichment_status.enrichment_status_response(" in route_source
    assert "apply_json_result(" in route_source
    assert "jsonify(result.payload)" not in route_source
    assert "_status_payloads" not in source
    assert "get_incremental_status(" not in route_source
    assert "_terminal_status(" not in route_source
    assert "_build_status_payload(" not in route_source
    assert "_serialize_results(" not in route_source
    assert "if orchestrator is None:" not in route_source
    assert "if status is None:" not in route_source
    assert "get_incremental_status(" in helper_source
    assert "terminal_status(" in helper_source
    assert "live_status_response(status)" in helper_source
    assert "build_status_payload(" in live_helper_source


def test_enrichment_status_route_delegates_response_decision(client, monkeypatch) -> None:
    """Flask status route should only collect request/registry inputs and apply JSON."""
    import app.routes.enrichment_jobs as routes_module
    import app.routes.enrichment_job_registry as registry_module
    import app.routes.enrichment_status as status_module

    orchestrator = object()
    terminal = {"terminal": True}
    job_id = "delegatedstatus123"
    calls = []

    def response_result(seen_job_id, *, orchestrator, terminal, since):
        calls.append((seen_job_id, orchestrator, terminal, since))
        return status_module.EnrichmentStatusResponse({"ok": True, "since": since}, 202)

    monkeypatch.setattr(status_module, "enrichment_status_response", response_result)
    routes_module._orchestrators[job_id] = orchestrator
    routes_module._terminal_jobs[job_id] = terminal

    try:
        response = client.get(f"/enrichment/status/{job_id}?since=6")
    finally:
        routes_module._orchestrators.pop(job_id, None)
        routes_module._terminal_jobs.pop(job_id, None)

    assert response.status_code == 202
    assert response.get_json() == {"ok": True, "since": 6}
    assert calls == [(job_id, orchestrator, terminal, 6)]
    assert "registered_job_state(" in inspect.getsource(routes_module._get_enrichment_status)
    assert "_orchestrators.get(" not in inspect.getsource(routes_module._get_enrichment_status)
    assert "_terminal_jobs.get(" not in inspect.getsource(routes_module._get_enrichment_status)
    assert "orchestrators.get(job_id)" in inspect.getsource(registry_module.registered_job_state)
    assert "terminal_jobs.get(job_id)" in inspect.getsource(registry_module.registered_job_state)


def test_registered_job_state_reads_live_and_terminal_under_lock() -> None:
    """Route-level job state reads should share one locked registry helper."""
    import app.routes.enrichment_job_registry as registry_module

    class RecordingLock:
        def __init__(self):
            self.calls: list[str] = []

        def __enter__(self):
            self.calls.append("enter")
            return self

        def __exit__(self, exc_type, exc, tb):
            self.calls.append("exit")
            return False

    lock = RecordingLock()
    orchestrators = OrderedDict([("job-1", "orchestrator")])
    terminal_jobs = OrderedDict([("job-1", {"terminal": True})])

    state = registry_module.registered_job_state(
        lock=lock,
        orchestrators=orchestrators,
        terminal_jobs=terminal_jobs,
        job_id="job-1",
    )
    missing = registry_module.registered_job_state(
        lock=lock,
        orchestrators=orchestrators,
        terminal_jobs=terminal_jobs,
        job_id="missing",
    )

    assert state == registry_module.RegisteredJobState(
        orchestrator="orchestrator",
        terminal={"terminal": True},
    )
    assert missing == registry_module.RegisteredJobState(orchestrator=None, terminal=None)
    assert lock.calls == ["enter", "exit", "enter", "exit"]


def test_enrichment_jobs_delegates_status_query_cursor() -> None:
    """Route module should delegate polling cursor query extraction."""
    import app.routes.enrichment_jobs as routes_module
    import app.routes.query_values as query_values

    class QueryArgs:
        def __init__(self, raw_value):
            self.raw_value = raw_value
            self.calls: list[tuple[str, int, object]] = []

        def get(self, key, default=None, type=None):  # noqa: A002 - mirrors Flask args API.
            self.calls.append((key, default, type))
            if self.raw_value is None:
                return default
            return type(self.raw_value) if type is not None else self.raw_value

    args = QueryArgs("-3")
    source = inspect.getsource(routes_module._get_enrichment_status)

    assert query_values.status_cursor_from_query(args) == 0
    assert args.calls == [("since", 0, int)]
    assert "status_cursor_from_query(request.args)" in source
    assert "request.args.get" not in source


def test_enrichment_jobs_public_exports_exclude_route_private_state() -> None:
    """Route-private job state helpers should not be advertised as public exports."""
    import app.routes.enrichment_jobs as routes_module

    assert routes_module.__all__ == ("get_orchestration_diagnostics_snapshot",)
    assert "_setup_orchestrator" not in routes_module.__all__
    assert "_orchestrators" not in routes_module.__all__
    assert "_terminal_jobs" not in routes_module.__all__
    assert "_enrichment_pool" not in routes_module.__all__


def test_setup_orchestrator_delegates_live_job_registration(monkeypatch) -> None:
    """Live job registration and eviction pruning should live outside setup wiring."""
    import app.routes.enrichment_jobs as routes_module
    import app.routes.enrichment_job_registry as registry_module

    original_orchestrators = routes_module._orchestrators
    original_terminal_jobs = routes_module._terminal_jobs
    live_jobs = OrderedDict()
    terminal_jobs = OrderedDict()
    monkeypatch.setattr(routes_module, "_orchestrators", live_jobs)
    monkeypatch.setattr(routes_module, "_terminal_jobs", terminal_jobs)
    monkeypatch.setattr(routes_module, "_MAX_ORCHESTRATORS", 2)

    try:
        routes_module._register_orchestrator("job-1", "orchestrator-1")
        routes_module._register_orchestrator("job-2", "orchestrator-2")
        routes_module._register_orchestrator("job-3", "orchestrator-3")
    finally:
        monkeypatch.setattr(routes_module, "_orchestrators", original_orchestrators)
        monkeypatch.setattr(routes_module, "_terminal_jobs", original_terminal_jobs)

    setup_source = inspect.getsource(routes_module._setup_orchestrator)
    helper_source = inspect.getsource(routes_module._register_orchestrator)
    registry_source = inspect.getsource(registry_module.register_orchestrator_state)

    assert list(live_jobs) == ["job-2", "job-3"]
    assert list(terminal_jobs) == ["job-1"]
    assert terminal_jobs["job-1"]["terminal_reason"] == "evicted"
    assert terminal_jobs["job-1"]["status"] == "failed"
    assert "_register_orchestrator(job_id, orchestrator)" in setup_source
    assert "_orchestrators[job_id]" not in setup_source
    assert "popitem(last=False)" not in setup_source
    assert "register_orchestrator_state(" in helper_source
    assert "_orchestrators[job_id]" not in helper_source
    assert "popitem(last=False)" not in helper_source
    assert "evicted_terminal_status" in helper_source
    assert "reason=\"evicted\"" not in helper_source
    assert "Enrichment job status was evicted from memory." not in helper_source
    assert "orchestrators[job_id]" in registry_source
    assert "popitem(last=False)" in registry_source


def test_route_job_registry_owns_live_orchestrator_retention() -> None:
    """Pure registry helper should own duplicate cleanup and retention pruning."""
    from collections import OrderedDict

    import app.routes.enrichment_job_registry as registry_module

    live_jobs = OrderedDict([("job-0", "orchestrator-0")])
    terminal_jobs = OrderedDict(
        [
            ("job-0", {"terminal_reason": "stale"}),
            ("old-terminal", {"terminal_reason": "old"}),
        ]
    )

    def evicted_status(job_id: str) -> dict[str, object]:
        return {"job_id": job_id, "terminal_reason": "evicted"}

    registry_module.register_orchestrator_state(
        orchestrators=live_jobs,
        terminal_jobs=terminal_jobs,
        job_id="job-1",
        orchestrator="orchestrator-1",
        max_jobs=1,
        evicted_status=evicted_status,
    )

    assert list(live_jobs.items()) == [("job-1", "orchestrator-1")]
    assert list(terminal_jobs.items()) == [
        ("job-0", {"job_id": "job-0", "terminal_reason": "evicted"})
    ]


def test_enrichment_status_owns_evicted_terminal_tombstone_shape() -> None:
    """Evicted tombstone reason and message should live with status payload shape."""
    import inspect

    import app.routes.enrichment_jobs as routes_module
    import app.routes.enrichment_status as status_module

    helper_source = inspect.getsource(routes_module._register_orchestrator)
    status_source = inspect.getsource(status_module.evicted_terminal_status)

    assert status_module.evicted_terminal_status("job-1") == {
        "job_id": "job-1",
        "total": 0,
        "done": 0,
        "complete": False,
        "results": [],
        "next_since": 0,
        "status": "failed",
        "terminal": True,
        "terminal_reason": "evicted",
        "error": status_module.EVICTED_JOB_ERROR,
    }
    assert "evicted_terminal_status" in helper_source
    assert "reason=\"evicted\"" not in helper_source
    assert "EVICTED_JOB_ERROR" not in helper_source
    assert "terminal_status(" in status_source
    assert "reason=\"evicted\"" in status_source
    assert "EVICTED_JOB_ERROR" in status_source


def test_enrichment_status_owns_unknown_terminal_tombstone_shape() -> None:
    """Unknown-job tombstone reason and message should have one status owner."""
    import inspect

    import app.routes.enrichment_status as status_module

    response_source = inspect.getsource(status_module.enrichment_status_response)
    status_source = inspect.getsource(status_module.unknown_terminal_status)

    assert status_module.unknown_terminal_status("missing-job", since=9) == {
        "job_id": "missing-job",
        "total": 0,
        "done": 0,
        "complete": False,
        "results": [],
        "next_since": 9,
        "status": "failed",
        "terminal": True,
        "terminal_reason": "unknown",
        "error": status_module.UNKNOWN_JOB_ERROR,
    }
    assert response_source.count("unknown_terminal_status(") == 1
    assert "terminal_status_response(" in response_source
    assert "reason=\"unknown\"" not in response_source
    assert "Enrichment job was not found." not in response_source
    assert "terminal_status(" in status_source
    assert "reason=\"unknown\"" in status_source
    assert "UNKNOWN_JOB_ERROR" in status_source


def test_enrichment_status_terminal_response_owns_cursor_alignment() -> None:
    """Terminal/unknown response cursor alignment should live outside the resolver branch."""
    import inspect

    import app.routes.enrichment_status as status_module

    terminal = status_module.evicted_terminal_status("evicted-job")
    response = status_module.terminal_status_response(
        "evicted-job",
        terminal,
        since=8,
    )
    unknown_response = status_module.terminal_status_response(
        "missing-job",
        None,
        since=5,
    )
    resolver_source = inspect.getsource(status_module.enrichment_status_response)
    helper_source = inspect.getsource(status_module.terminal_status_response)

    assert response.status == 404
    assert response.payload is terminal
    assert response.payload["terminal_reason"] == "evicted"
    assert response.payload["next_since"] == 8
    assert unknown_response.status == 404
    assert unknown_response.payload["terminal_reason"] == "unknown"
    assert unknown_response.payload["next_since"] == 5
    assert "terminal_status_response(" in resolver_source
    assert "payload[\"next_since\"] = since" not in resolver_source
    assert "payload[\"next_since\"] = since" in helper_source


def test_enrichment_status_live_response_owns_result_serialization() -> None:
    """Live response serialization should live outside the resolver branch."""
    import inspect

    from app.enrichment.models import EnrichmentError
    import app.routes.enrichment_status as status_module

    result = EnrichmentError(
        ioc=make_ipv4_ioc("192.0.2.44"),
        provider="ErrorProvider",
        error="lookup failed",
    )

    class CountingStatus(dict):
        def __init__(self):
            super().__init__(
                {
                    "total": 1,
                    "done": 1,
                    "complete": True,
                    "results": [result],
                    "next_since": 1,
                    "status": "complete",
                    "terminal": False,
                    "terminal_reason": None,
                    "error": None,
                    "cached_markers": {"marker": "cached"},
                }
            )
            self.cached_marker_gets = 0

        def get(self, key, default=None):
            if key == "cached_markers":
                self.cached_marker_gets += 1
            return super().get(key, default)

    calls: list[tuple[object, object]] = []

    def serialize_result(result, markers=None):
        calls.append((result, markers))
        return {"value": result}

    status = CountingStatus()
    response = status_module.live_status_response(
        status,
    )
    serialized = status_module.serialize_results(
        status["results"],
        status["cached_markers"],
        serializer=serialize_result,
    )
    resolver_source = inspect.getsource(status_module.enrichment_status_response)
    helper_source = inspect.getsource(status_module.live_status_response)
    serializer_source = inspect.getsource(status_module.serialized_status_results)

    assert response.status == 200
    assert response.payload["results"] == [
        {
            "type": "error",
            "ioc_value": "192.0.2.44",
            "ioc_type": "ipv4",
            "provider": "ErrorProvider",
            "error": "lookup failed",
        }
    ]
    assert status.cached_marker_gets == 1
    assert serialized == [{"value": result}]
    assert calls == [(result, {"marker": "cached"})]
    assert "live_status_response(status)" in resolver_source
    assert "serialize_results(" not in resolver_source
    assert "build_status_payload(" not in resolver_source
    assert "status_code_for_payload(" not in resolver_source
    assert "serialized_status_results(status)" in helper_source
    assert "serialize_results(" not in helper_source
    assert "serialize_results(" in serializer_source
    assert "build_status_payload(" in helper_source
    assert "status_code_for_payload(" in helper_source


def test_setup_orchestrator_delegates_orchestrator_construction(monkeypatch) -> None:
    """Orchestrator construction should live outside setup registration/submission wiring."""
    import app.routes.enrichment_jobs as routes_module

    configured_providers = [MagicMock(name="configured-provider")]
    fallback_providers = [MagicMock(name="fallback-provider")]
    mock_registry = MagicMock()
    mock_registry.configured.return_value = fallback_providers
    mock_cache = object()
    built: list[dict[str, object]] = []

    class MockConfigStore:
        def get_cache_ttl(self):
            return 7

    def build_orchestrator(**kwargs):
        built.append(kwargs)
        return {"orchestrator": kwargs}

    monkeypatch.setattr(routes_module, "EnrichmentOrchestrator", build_orchestrator)

    explicit = routes_module._build_enrichment_orchestrator(
        registry=mock_registry,
        cache=mock_cache,
        configured_providers=configured_providers,
        config_store_factory=MockConfigStore,
    )
    fallback = routes_module._build_enrichment_orchestrator(
        registry=mock_registry,
        cache=mock_cache,
        config_store_factory=MockConfigStore,
    )
    setup_source = inspect.getsource(routes_module._setup_orchestrator)
    helper_source = inspect.getsource(routes_module._build_enrichment_orchestrator)

    assert explicit == {"orchestrator": built[0]}
    assert fallback == {"orchestrator": built[1]}
    assert built == [
        {
            "adapters": configured_providers,
            "cache": mock_cache,
            "cache_ttl_seconds": 7 * 3600,
        },
        {
            "adapters": fallback_providers,
            "cache": mock_cache,
            "cache_ttl_seconds": 7 * 3600,
        },
    ]
    mock_registry.configured.assert_called_once_with()
    assert "_build_enrichment_orchestrator(" in setup_source
    assert "ConfigStore()" not in setup_source
    assert "registry.configured()" not in setup_source
    assert "cache_ttl_seconds" not in setup_source
    assert "config_store_factory()" in helper_source
    assert "cache_ttl_seconds" in helper_source


def test_setup_orchestrator_accepts_explicit_runtime_dependencies(monkeypatch) -> None:
    """Online setup should not require current_app for registry/cache already known upstream."""
    import app.routes.enrichment_jobs as routes_module

    configured_providers = [MagicMock(name="configured-provider")]
    mock_registry = MagicMock()
    mock_cache = object()
    mock_orchestrator = MagicMock(name="orchestrator")
    submitted: list[dict[str, object]] = []
    registered: list[tuple[str, object]] = []

    def build_orchestrator(**kwargs):
        assert kwargs == {
            "registry": mock_registry,
            "cache": mock_cache,
            "configured_providers": configured_providers,
            "config_store_factory": object,
        }
        return mock_orchestrator

    def register(job_id, orchestrator):
        registered.append((job_id, orchestrator))

    def submit(**kwargs):
        submitted.append(kwargs)

    monkeypatch.setattr(routes_module, "_build_enrichment_orchestrator", build_orchestrator)
    monkeypatch.setattr(routes_module, "_register_orchestrator", register)
    monkeypatch.setattr(routes_module, "_submit_enrichment_job", submit)
    monkeypatch.setattr(routes_module.uuid, "uuid4", lambda: SimpleNamespace(hex="job-explicit"))

    job_id, orchestrator, registry = routes_module._setup_orchestrator(
        [MagicMock(name="ioc")],
        "8.8.8.8",
        "online",
        "history-store",
        configured_providers,
        registry=mock_registry,
        cache=mock_cache,
        config_store_factory=object,
    )
    setup_source = inspect.getsource(routes_module._setup_orchestrator)
    resolver_source = inspect.getsource(routes_module._resolve_orchestrator_runtime_dependencies)

    assert (job_id, orchestrator, registry) == ("job-explicit", mock_orchestrator, mock_registry)
    assert registered == [("job-explicit", mock_orchestrator)]
    assert submitted[0]["orchestrator"] is mock_orchestrator
    assert submitted[0]["history_store"] == "history-store"
    assert "_resolve_orchestrator_runtime_dependencies(" in setup_source
    assert "current_app.registry if registry is None else registry" not in setup_source
    assert "current_app.cache_store if cache is None else cache" not in setup_source
    assert "current_app.registry if registry is None else registry" in resolver_source
    assert "current_app.cache_store if cache is None else cache" in resolver_source
    assert "config_store_factory=config_store_factory" in setup_source


def test_setup_orchestrator_delegates_background_submission(monkeypatch) -> None:
    """Executor submission should live outside setup construction/registration wiring."""
    import app.routes.enrichment_jobs as routes_module

    mock_pool = MagicMock()
    mock_orchestrator = MagicMock(name="orchestrator")
    mock_history_store = object()
    iocs = [MagicMock(name="ioc")]
    monkeypatch.setattr(routes_module, "_enrichment_pool", mock_pool)

    routes_module._submit_enrichment_job(
        orchestrator=mock_orchestrator,
        job_id="job-1",
        iocs=iocs,
        text="8.8.8.8",
        mode="online",
        history_store=mock_history_store,
    )
    setup_source = inspect.getsource(routes_module._setup_orchestrator)
    helper_source = inspect.getsource(routes_module._submit_enrichment_job)

    mock_pool.submit.assert_called_once_with(
        routes_module._run_enrichment_and_save,
        mock_orchestrator,
        "job-1",
        iocs,
        "8.8.8.8",
        "online",
        mock_history_store,
    )
    assert "_submit_enrichment_job(" in setup_source
    assert "_enrichment_pool.submit(" not in setup_source
    assert "_run_enrichment_and_save," not in setup_source
    assert "pool.submit(" in helper_source
    assert "_run_enrichment_and_save," in helper_source


def test_enrichment_status_job_failed_payload_stays_truthful(client):
    """Orchestrator terminal failures stay terminal without being collapsed into 404 tombstones."""
    import app.routes.enrichment_jobs as routes_module

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
    import inspect

    import app.routes.enrichment_status as status_module

    class NoLenResults:
        def __len__(self):
            raise AssertionError("explicit next_since should skip result-length fallback")

    payload = status_module.build_status_payload(
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
    payload_source = inspect.getsource(status_module.build_status_payload)
    cursor_source = inspect.getsource(status_module.status_next_since)
    text_source = inspect.getsource(status_module.status_text)
    assert "status_next_since(status)" in payload_source
    assert "status_text(status)" in payload_source
    assert "len(status.get(\"results\", []))" not in payload_source
    assert "len(status.get(\"results\", []))" in cursor_source
    assert "\"complete\" if status[\"complete\"] else \"running\"" not in payload_source
    assert "\"complete\" if status[\"complete\"] else \"running\"" in text_source


def test_status_payload_fallback_helpers_own_cursor_and_status_text() -> None:
    import app.routes.enrichment_status as status_module

    complete_status = {
        "total": 2,
        "done": 2,
        "complete": True,
        "results": [object(), object()],
    }
    running_status = {
        "total": 2,
        "done": 1,
        "complete": False,
        "results": [object()],
    }

    assert status_module.status_next_since(complete_status) == 2
    assert status_module.status_next_since({"next_since": 8, "results": NoLenList()}) == 8
    assert status_module.status_text(complete_status) == "complete"
    assert status_module.status_text(running_status) == "running"
    assert status_module.status_text({"status": "failed", "complete": False}) == "failed"


class NoLenList(list):
    def __len__(self):
        raise AssertionError("explicit status cursor should not measure results")


def test_enrichment_status_evicted_job_returns_terminal_payload(client):
    """Registry-level eviction returns an explicit terminal eviction payload."""
    import app.routes.enrichment_jobs as routes_module
    import app.routes.enrichment_status as status_module

    job_id = "evictedjob123"
    routes_module._terminal_jobs[job_id] = status_module.terminal_status(
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
        assert data["complete"] is False
        assert data["next_since"] == 4
    finally:
        routes_module._terminal_jobs.pop(job_id, None)


def test_enrichment_status_not_found_reasons_use_static_membership_set(client):
    """404 terminal reason checks should reuse a static membership table."""
    import app.routes.enrichment_jobs as routes_module
    import app.routes.enrichment_status as status_module

    route_source = inspect.getsource(routes_module._get_enrichment_status)
    helper_source = inspect.getsource(status_module.status_code_for_payload)
    response_source = inspect.getsource(status_module.enrichment_status_response)
    live_helper_source = inspect.getsource(status_module.live_status_response)
    assert '{"unknown", "evicted"}' not in route_source
    assert '{"unknown", "evicted"}' not in helper_source
    assert "_STATUS_NOT_FOUND_REASONS" not in route_source
    assert "STATUS_NOT_FOUND_REASONS" in helper_source
    assert "live_status_response(status)" in response_source
    assert "status_code_for_payload(" in live_helper_source
    assert status_module.STATUS_NOT_FOUND_REASONS == frozenset(("unknown", "evicted"))

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
    import app.routes.enrichment_jobs as routes_module
    import app.routes.enrichment_status as status_module

    job_id = "diagsevicted123"
    routes_module._terminal_jobs[job_id] = status_module.terminal_status(
        job_id,
        reason="evicted",
        error="Enrichment job status was evicted from memory.",
        since=2,
    )

    try:
        snapshot = routes_module.get_orchestration_diagnostics_snapshot(job_id)
        source = inspect.getsource(routes_module.get_orchestration_diagnostics_snapshot)

        assert "dict(_terminal_jobs.get" not in source
        assert "registered_job_state(" in source
        assert "_orchestrators.get(" not in source
        assert "_terminal_jobs.get(" not in source
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
    import app.routes.enrichment_jobs as routes_module
    import app.routes.enrichment_status as status_module

    class NoStripJobId(str):
        def strip(self, *_args, **_kwargs):
            raise AssertionError("diagnostic job-id normalization should avoid direct strip allocation")

    class JobIdWrapper:
        def __str__(self) -> str:
            return NoStripJobId(" diagstripjob123 ")

    job_id = "diagstripjob123"
    routes_module._terminal_jobs[job_id] = status_module.terminal_status(
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
    import app.enrichment.history_diagnostics as history_diagnostics
    import app.routes.enrichment_diagnostics as diagnostics_module
    import app.routes.enrichment_jobs as routes_module

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

    class TripleReadDict(dict):
        reads = 0

        def __iter__(self):
            for key in super().__iter__():
                type(self).reads += 1
                if type(self).reads > 3:
                    raise AssertionError("triple mapping copy should stop after three keys")
                yield key

    class FourReadDict(dict):
        reads = 0

        def __iter__(self):
            for key in super().__iter__():
                type(self).reads += 1
                if type(self).reads > 4:
                    raise AssertionError("four mapping copy should stop after four keys")
                yield key

    source = inspect.getsource(routes_module)
    single = SingleReadDict({"count": 1})
    pair = PairReadDict({"terminal": True, "terminal_reason": "evicted"})
    triple = TripleReadDict({"total": 3, "done": 2, "status": "running"})
    four = FourReadDict({"total": 4, "done": 2, "status": "running", "terminal": False})

    assert history_diagnostics.copy_mapping({"count": 1}) == {"count": 1}
    assert history_diagnostics.copy_mapping(None) == {}
    assert history_diagnostics.copy_mapping(NoIterEmptyDict()) == {}
    assert isinstance(history_diagnostics._HISTORY_SAVE_DIAGNOSTICS_DEFAULTS, MappingProxyType)
    assert history_diagnostics.copy_mapping(
        history_diagnostics._HISTORY_SAVE_DIAGNOSTICS_DEFAULTS
    )["last_outcome"] == "never"
    assert history_diagnostics.copy_mapping(single) == {"count": 1}
    assert history_diagnostics.copy_mapping(pair) == {
        "terminal": True,
        "terminal_reason": "evicted",
    }
    assert history_diagnostics.copy_mapping(triple) == {
        "total": 3,
        "done": 2,
        "status": "running",
    }
    assert history_diagnostics.copy_mapping(four) == {
        "total": 4,
        "done": 2,
        "status": "running",
        "terminal": False,
    }
    assert SingleReadDict.reads == 1
    assert PairReadDict.reads == 2
    assert TripleReadDict.reads == 3
    assert FourReadDict.reads == 4
    assert "copy_mapping" in history_diagnostics.history_save_diagnostics_defaults.__code__.co_names
    assert "copy_mapping" in history_diagnostics.get_history_save_diagnostics.__code__.co_names
    assert "copy_mapping" in diagnostics_module.build_orchestration_diagnostics_snapshot.__code__.co_names
    assert "append_mapping_value" in history_diagnostics.copy_mapping.__code__.co_names
    assert "snapshot[key] = source[key]" not in inspect.getsource(history_diagnostics.copy_mapping)
    assert "snapshot[key] = source[key]" in inspect.getsource(
        history_diagnostics.append_mapping_value
    )
    assert not hasattr(diagnostics_module, "_history_save_diagnostics")
    assert not hasattr(diagnostics_module, "get_history_save_diagnostics")
    assert not hasattr(diagnostics_module, "_copy_mapping")
    assert not hasattr(diagnostics_module, "_copy_history_save_diagnostics")
    assert not hasattr(diagnostics_module, "_copy_terminal_job_snapshot")
    assert "len" in history_diagnostics.copy_mapping.__code__.co_names
    assert "source_count == 4" in inspect.getsource(history_diagnostics.copy_mapping)
    assert not hasattr(routes_module, "_copy_mapping")
    assert not hasattr(routes_module, "_copy_terminal_job_snapshot")
    assert "dict(_terminal_jobs.get" not in source


def test_history_save_diagnostic_updates_share_identity_preserving_replace_helper():
    """History-save diagnostic writers should reuse one clear/update path."""
    import app.enrichment.history_diagnostics as diagnostics_module

    diagnostics_module.reset_history_save_diagnostics()
    diagnostics_id = id(diagnostics_module._history_save_diagnostics)

    diagnostics_module.record_history_save_attempt()
    snapshot = diagnostics_module.get_history_save_diagnostics()

    assert id(diagnostics_module._history_save_diagnostics) == diagnostics_id
    assert snapshot["attempts"] == 1
    assert (
        "_replace_history_save_diagnostics"
        not in diagnostics_module.record_history_save_attempt.__code__.co_names
    )
    assert (
        "replace_history_save_diagnostics"
        in diagnostics_module.record_history_save_attempt.__code__.co_names
    )
    assert (
        "replace_history_save_diagnostics"
        in diagnostics_module.record_history_save_outcome.__code__.co_names
    )
    assert "replace_history_save_diagnostics" in diagnostics_module.reset_history_save_diagnostics.__code__.co_names

    diagnostics_module.reset_history_save_diagnostics()


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
    import app.routes.enrichment_jobs as routes_module

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
    import app.routes.enrichment_jobs as routes_module

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
    import app.routes.enrichment_jobs as routes_module

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


def test_enrichment_status_negative_since_clamps_to_zero(client):
    """Negative since values are clamped before reaching the orchestrator."""
    import app.routes.enrichment_jobs as routes_module

    mock_orch = _make_three_result_orchestrator()
    job_id = "cursor_negative_job"
    routes_module._orchestrators[job_id] = mock_orch
    try:
        response = client.get(f"/enrichment/status/{job_id}?since=-1")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["results"]) == 3
        assert data["results"][0]["provider"] == "VirusTotal"
        assert data["next_since"] == 3
        mock_orch.get_incremental_status.assert_called_once_with(job_id, since=0)
        mock_orch.get_status.assert_not_called()
    finally:
        routes_module._orchestrators.pop(job_id, None)


def test_enrichment_status_since_equal_to_length_returns_empty_delta(client):
    """?since=3 with 3 results returns no new rows and preserves next_since."""
    import app.routes.enrichment_jobs as routes_module

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
    import app.routes.enrichment_jobs as routes_module

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
