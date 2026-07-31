"""Integration tests for the settings page and API key management.

Tests cover:
- GET /settings renders settings page with expected content (5 provider sections)
- POST /settings saves API key via ConfigStore and redirects
- POST /settings with empty key shows error and rejects save
- POST /settings with unknown provider_id shows error and rejects save
- Stored key is masked (only last 4 chars visible) on GET /settings
- Multi-provider: different provider_id routes to correct ConfigStore method
"""
import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.pipeline.models import IOCType


# ---------------------------------------------------------------------------
# GET /settings — page rendering
# ---------------------------------------------------------------------------


def test_get_settings_page(client):
    """GET /settings returns 200 and contains VirusTotal section."""
    response = client.get("/settings")
    assert response.status_code == 200
    assert b"VirusTotal" in response.data


def test_get_settings_page_has_form(client):
    """GET /settings renders a form for API key input."""
    response = client.get("/settings")
    assert response.status_code == 200
    assert b"<form" in response.data
    assert b"api_key" in response.data


def test_get_settings_page_shows_info_text(client):
    """GET /settings shows storage location info and virustotal.com link."""
    response = client.get("/settings")
    assert response.status_code == 200
    assert b"~/.sentinelx/config.ini" in response.data
    assert b"virustotal.com" in response.data


def test_get_settings_page_shows_provider_health_dashboard(client):
    """GET /settings renders a secret-free local provider health summary."""
    response = client.get("/settings")
    data = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Provider Health" in data
    assert "Local readiness view" in data
    assert "VirusTotal" in data
    assert "Shodan InternetDB" in data
    assert "Not checked" in data
    assert "Never" in data
    assert "None" in data
    assert "Not required" in data


def test_get_settings_provider_health_uses_registry_without_secret_leak(client):
    """Provider health should show readiness without rendering API key values."""
    secret = "super-secret-provider-key"  # noqa: S105 - sentinel value for leak assertion.

    class StubRegistry:
        def all(self):
            return [
                SimpleNamespace(
                    name="Keyed Ready",
                    requires_api_key=True,
                    supported_types=frozenset({IOCType.IPV4, IOCType.DOMAIN}),
                    is_configured=lambda: True,
                    api_key=secret,
                ),
                SimpleNamespace(
                    name="Keyed Missing",
                    requires_api_key=True,
                    supported_types=frozenset({IOCType.URL}),
                    is_configured=lambda: False,
                ),
                SimpleNamespace(
                    name="Zero Auth",
                    requires_api_key=False,
                    supported_types=frozenset({IOCType.SHA256}),
                    is_configured=lambda: True,
                ),
            ]

    client.application.registry = StubRegistry()

    response = client.get("/settings")
    data = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Keyed Ready" in data
    assert "Configured" in data
    assert "Ready" in data
    assert "IPv4 · domain" in data
    assert "Keyed Missing" in data
    assert "Missing" in data
    assert "Needs API key" in data
    assert "Zero Auth" in data
    assert "Not required" in data
    assert "SHA256" in data
    assert secret not in data


def test_provider_health_rows_do_not_perform_lookup_or_network_calls():
    """Health rows report local readiness only; provider lookup must not run."""
    import app.routes.settings_view as settings_view

    provider = SimpleNamespace(
        name="No Network",
        requires_api_key=False,
        supported_types=frozenset({IOCType.IPV4}),
        is_configured=lambda: True,
        lookup=MagicMock(side_effect=AssertionError("settings health must not call lookup")),
    )
    registry = SimpleNamespace(all=lambda: [provider])

    rows = settings_view.provider_health_rows(registry)

    assert rows == [{
        "name": "No Network",
        "key_status": "Not required",
        "readiness": "Ready",
        "readiness_class": "ready",
        "supported_ioc_types": "IPv4",
        "reachability": "Not checked",
        "last_checked": "Never",
        "last_error": "None",
    }]
    provider.lookup.assert_not_called()


def test_provider_health_row_helper_owns_secret_free_shape():
    """Local provider health row shape should live in one helper."""
    import inspect

    import app.routes.settings_view as settings_view

    ready_provider = SimpleNamespace(
        name="Keyed Ready",
        requires_api_key=True,
        supported_types=frozenset({IOCType.IPV4, IOCType.DOMAIN}),
        is_configured=lambda: True,
        api_key="do-not-render",
    )
    missing_provider = SimpleNamespace(
        name="Keyed Missing",
        requires_api_key=True,
        supported_types=frozenset({IOCType.URL}),
        is_configured=lambda: False,
    )
    zero_auth_provider = SimpleNamespace(
        name="Zero Auth",
        requires_api_key=False,
        supported_types=frozenset({IOCType.SHA256}),
        is_configured=lambda: True,
    )

    assert settings_view._provider_health_row(ready_provider) == {
        "name": "Keyed Ready",
        "key_status": "Configured",
        "readiness": "Ready",
        "readiness_class": "ready",
        "supported_ioc_types": "IPv4 · domain",
        "reachability": "Not checked",
        "last_checked": "Never",
        "last_error": "None",
    }
    assert settings_view._provider_health_row(missing_provider)["key_status"] == "Missing"
    assert settings_view._provider_health_row(missing_provider)["readiness"] == "Needs API key"
    assert settings_view._provider_health_row(zero_auth_provider)["key_status"] == "Not required"
    assert settings_view.supported_types_text(frozenset()) == ""
    assert settings_view.supported_types_text(frozenset({IOCType.IPV4})) == "IPv4"
    assert settings_view.supported_types_text(frozenset({IOCType.DOMAIN, IOCType.IPV4})) == (
        "IPv4 · domain"
    )
    assert settings_view.supported_types_text(
        frozenset({IOCType.SHA256, IOCType.DOMAIN, IOCType.IPV4})
    ) == "IPv4 · domain · SHA256"
    assert settings_view.append_supported_type_text("", frozenset(), IOCType.IPV4) == ""
    assert settings_view.append_supported_type_text("", frozenset({IOCType.IPV4}), IOCType.IPV4) == (
        "IPv4"
    )
    assert settings_view.append_supported_type_text(
        "IPv4",
        frozenset({IOCType.DOMAIN}),
        IOCType.DOMAIN,
    ) == "IPv4 · domain"

    rows_source = inspect.getsource(settings_view.provider_health_rows)
    helper_source = inspect.getsource(settings_view._provider_health_row)
    supported_types_source = inspect.getsource(settings_view.supported_types_text)
    assert "append_provider_health_row(rows, provider)" in rows_source
    assert "rows.append(_provider_health_row(provider))" not in rows_source
    assert "rows.append(_provider_health_row(provider))" in inspect.getsource(
        settings_view.append_provider_health_row
    )
    assert "key_status" not in rows_source
    assert ".api_key" not in helper_source
    assert "lookup(" not in helper_source
    assert "labels: list" not in supported_types_source
    assert ".join(" not in supported_types_source
    assert "for ioc_type in" not in supported_types_source
    assert "append_supported_type_text" in supported_types_source


def test_settings_route_delegates_provider_rows_to_view_helpers():
    """GET route should delegate provider status and health row shaping."""
    import inspect

    import app.routes.browser_responses as browser_responses
    import app.routes.settings as settings_route
    import app.routes.settings_view as settings_view

    provider_info = (
        {"id": "virustotal", "name": "VirusTotal"},
        {"id": "urlhaus", "name": "URLhaus"},
    )
    rows = settings_view.provider_status_rows(
        provider_info,
        {"urlhaus": "urlhaus-key-123456"},
        "vt-key-123456",
    )

    assert rows[0]["configured"] is True
    assert rows[0]["masked_key"].endswith("3456")
    assert rows[1]["configured"] is True
    assert rows[1]["masked_key"].endswith("3456")

    route_source = inspect.getsource(settings_route.settings_get)
    assert "settings_page_route_response(" in route_source
    assert "settings_page_result(" not in route_source
    assert "apply_template_result(" not in route_source
    assert "provider_status_rows(" not in route_source
    assert "_provider_health_rows(" not in route_source
    assert "providers_with_status.append" not in route_source
    assert "for info in PROVIDER_INFO" not in route_source
    assert "settings_view.provider_key_save_route_response(" in inspect.getsource(
        settings_route.settings_post
    )
    assert "config_store.set_vt_api_key" not in inspect.getsource(settings_route.settings_post)
    assert "config_store.set_provider_key" not in inspect.getsource(settings_route.settings_post)


def test_settings_page_context_owns_get_template_shape():
    """Settings GET template shape should live outside the Flask route body."""
    import inspect

    import app.routes.browser_responses as browser_responses
    import app.routes.settings as settings_route
    import app.routes.settings_view as settings_view

    provider = SimpleNamespace(
        name="Ready Provider",
        requires_api_key=False,
        supported_types=frozenset({IOCType.IPV4}),
        is_configured=lambda: True,
    )
    config_store = MagicMock()
    config_store.all_provider_keys.return_value = {"urlhaus": "urlhaus-key-123456"}
    config_store.get_vt_api_key.return_value = "vt-key-123456"
    config_store.get_cache_ttl.return_value = 24
    cache_store = MagicMock()
    cache_store.stats.return_value = {"entries": 2}
    registry = SimpleNamespace(all=lambda: [provider])
    diagnostics = {"attempts": 1, "successes": 1}

    context = settings_view.settings_page_context(
        provider_info=(
            {"id": "virustotal", "name": "VirusTotal"},
            {"id": "urlhaus", "name": "URLhaus"},
        ),
        config_store=config_store,
        cache_store=cache_store,
        registry=registry,
        history_save_diagnostics=diagnostics,
    )
    route_context = settings_view.settings_route_context(
        cache_store=cache_store,
        registry=registry,
        provider_info=(
            {"id": "virustotal", "name": "VirusTotal"},
            {"id": "urlhaus", "name": "URLhaus"},
        ),
        config_store_factory=lambda: config_store,
        history_save_diagnostics=diagnostics,
    )
    page_result = settings_view.settings_page_result(
        cache_store=cache_store,
        registry=registry,
        provider_info=(
            {"id": "virustotal", "name": "VirusTotal"},
            {"id": "urlhaus", "name": "URLhaus"},
        ),
        config_store_factory=lambda: config_store,
        history_save_diagnostics=diagnostics,
    )
    route_response_calls: list[tuple[str | None, dict[str, object]]] = []

    def render_page(template_name: str | None, **context):
        route_response_calls.append((template_name, context))
        return ("rendered", template_name, context)

    route_response = settings_view.settings_page_route_response(
        cache_store=cache_store,
        registry=registry,
        provider_info=(
            {"id": "virustotal", "name": "VirusTotal"},
            {"id": "urlhaus", "name": "URLhaus"},
        ),
        config_store_factory=lambda: config_store,
        history_save_diagnostics=diagnostics,
        render_template=render_page,
    )
    route_source = inspect.getsource(settings_route.settings_get)
    route_helper_source = inspect.getsource(settings_view.settings_page_route_response)

    assert context["providers"][0]["configured"] is True
    assert context["providers"][1]["configured"] is True
    assert route_context["providers"][0]["configured"] is True
    assert route_context["cache_stats"] == {"entries": 2}
    assert route_context["history_save_diagnostics"] is diagnostics
    assert page_result.template_name == "settings.html"
    assert page_result.context["cache_stats"] == {"entries": 2}
    assert page_result.status == 200
    assert route_response[0] == ("rendered", "settings.html", page_result.context)
    assert route_response[1] == 200
    assert route_response_calls == [("settings.html", page_result.context)]
    assert context["provider_health_rows"][0]["name"] == "Ready Provider"
    assert context["cache_stats"] == {"entries": 2}
    assert context["cache_ttl"] == 24
    assert context["history_save_diagnostics"] is diagnostics
    assert config_store.all_provider_keys.call_count == 4
    assert config_store.get_vt_api_key.call_count == 4
    assert config_store.get_cache_ttl.call_count == 4
    assert cache_store.stats.call_count == 4
    assert "settings_page_route_response(" in route_source
    assert "settings_page_result(" not in route_source
    assert "apply_template_result(" not in route_source
    assert "cache_store=current_app.cache_store" in route_source
    assert "registry=current_app.registry" in route_source
    assert "apply_template_result(" in route_helper_source
    assert "settings_page_result(" in route_helper_source
    assert "render_template=render_template" in route_helper_source
    assert "settings_page_context(" not in route_source
    assert "ConfigStore()" not in route_source
    assert "app=current_app" not in route_source
    assert "cache_store.stats()" not in route_source
    assert "get_cache_ttl()" not in route_source
    assert "all_provider_keys()" not in route_source
    assert "\"providers\"" not in route_source
    assert "\"cache_stats\"" not in route_source


def test_save_provider_key_helper_preserves_vt_and_provider_paths() -> None:
    """Provider-key save routing should live in one settings helper."""
    import app.routes.settings_view as settings_view

    config_store = MagicMock()

    settings_view.save_provider_key(config_store, "virustotal", "vt-key")
    settings_view.save_provider_key(config_store, "urlhaus", "urlhaus-key")

    config_store.set_vt_api_key.assert_called_once_with("vt-key")
    config_store.set_provider_key.assert_called_once_with("urlhaus", "urlhaus-key")


def test_save_provider_key_and_registry_rebuild_lives_in_view_helper(monkeypatch) -> None:
    """Settings key saves should rebuild the registry outside the Flask route body."""
    import inspect

    import app.routes.settings as settings_route
    import app.routes.settings_view as settings_view

    calls: list[tuple[str, object]] = []
    config_store = MagicMock()
    rebuilt_registry = object()
    allowed_hosts = ("api.example.test",)

    def record_save(store, provider_id, api_key):
        calls.append(("save", (store, provider_id, api_key)))

    def record_build_registry(*, allowed_hosts, config_store):
        calls.append(("build", (allowed_hosts, config_store)))
        return rebuilt_registry

    monkeypatch.setattr(settings_view, "save_provider_key", record_save)
    monkeypatch.setattr(settings_view, "build_registry", record_build_registry)

    registry = settings_view.save_provider_key_and_rebuild_registry(
        config_store=config_store,
        provider_id="urlhaus",
        api_key="urlhaus-key",
        allowed_hosts=allowed_hosts,
    )
    route_source = inspect.getsource(settings_route.settings_post)

    assert registry is rebuilt_registry
    assert calls == [
        ("save", (config_store, "urlhaus", "urlhaus-key")),
        ("build", (allowed_hosts, config_store)),
    ]
    assert "settings_view.provider_key_save_route_response(" in route_source
    assert "settings_view.apply_settings_action_response(" not in route_source
    assert "current_app.registry = action.registry" not in route_source
    assert "action.message" not in route_source
    assert "action.category" not in route_source
    assert "save_provider_key_and_rebuild_registry(" not in route_source
    assert "ConfigStore()" not in route_source
    assert " build_registry(" not in route_source
    assert "ALLOWED_API_HOSTS" in route_source


def test_provider_key_save_action_from_form_owns_field_normalization(monkeypatch) -> None:
    """Provider-key save route helper should own submitted form field normalization."""
    import inspect

    import app.routes.settings as settings_route
    import app.routes.settings_view as settings_view

    calls: list[tuple[object, str]] = []
    saved_inputs: dict[str, object] = {}

    def form_value(form, field_name: str) -> str:
        calls.append((form, field_name))
        return {"provider_id": "urlhaus", "api_key": "saved-key"}[field_name]

    def save_action(**kwargs):
        saved_inputs.update(kwargs)
        return settings_view.SettingsActionResult("saved", "success", "registry")

    monkeypatch.setattr(settings_view, "stripped_form_value", form_value)
    monkeypatch.setattr(settings_view, "provider_key_save_action", save_action)

    form = {"provider_id": " urlhaus ", "api_key": " saved-key "}
    result = settings_view.provider_key_save_action_from_form(
        form,
        valid_provider_ids=frozenset(("urlhaus",)),
        config_store_factory=object,
        allowed_hosts=("api.example.test",),
    )
    route_source = inspect.getsource(settings_route.settings_post)
    helper_source = inspect.getsource(settings_view.provider_key_save_action_from_form)

    assert result == settings_view.SettingsActionResult("saved", "success", "registry")
    assert calls == [(form, "provider_id"), (form, "api_key")]
    assert saved_inputs == {
        "provider_id": "urlhaus",
        "api_key": "saved-key",
        "valid_provider_ids": frozenset(("urlhaus",)),
        "config_store_factory": object,
        "allowed_hosts": ("api.example.test",),
    }
    assert "settings_view.provider_key_save_route_response(" in route_source
    assert "stripped_form_value(" not in route_source
    assert "provider_id=" not in route_source
    assert "api_key=" not in route_source
    assert "stripped_form_value(form, \"provider_id\")" in helper_source
    assert "stripped_form_value(form, \"api_key\")" in helper_source


def test_provider_key_save_route_response_owns_action_application(monkeypatch) -> None:
    """Provider-key POST should share one helper for form action and response application."""
    import inspect

    import app.routes.settings as settings_route
    import app.routes.settings_view as settings_view

    form = {"provider_id": "urlhaus", "api_key": "saved-key"}
    action = settings_view.SettingsActionResult("saved", "success", "registry")
    calls: list[tuple[str, dict[str, object]]] = []

    def action_from_form(form_arg, **kwargs):
        calls.append(("action", {"form": form_arg, **kwargs}))
        return action

    def action_response(action_arg, **kwargs):
        calls.append(("response", {"action": action_arg, **kwargs}))
        return "redirected"

    monkeypatch.setattr(settings_view, "provider_key_save_action_from_form", action_from_form)
    monkeypatch.setattr(settings_view, "apply_settings_action_response", action_response)

    response = settings_view.provider_key_save_route_response(
        form,
        valid_provider_ids=frozenset(("urlhaus",)),
        config_store_factory=object,
        allowed_hosts=("api.example.test",),
        set_registry=list.append,
        flash_message=print,
        redirect_to=str,
        settings_url="/settings",
    )
    route_source = inspect.getsource(settings_route.settings_post)
    route_helper_source = inspect.getsource(settings_view.provider_key_save_route_response)

    assert response == "redirected"
    assert calls == [
        ("action", {
            "form": form,
            "valid_provider_ids": frozenset(("urlhaus",)),
            "config_store_factory": object,
            "allowed_hosts": ("api.example.test",),
        }),
        ("response", {
            "action": action,
            "set_registry": list.append,
            "flash_message": print,
            "redirect_to": str,
            "settings_url": "/settings",
        }),
    ]
    assert "settings_view.provider_key_save_route_response(" in route_source
    assert "provider_key_save_action_from_form(" not in route_source
    assert "apply_settings_action_response(" not in route_source
    assert "provider_key_save_action_from_form(" in route_helper_source
    assert "apply_settings_action_response(" in route_helper_source


def test_provider_key_save_action_owns_post_validation_and_registry_rebuild(monkeypatch) -> None:
    """Settings POST validation and save/rebuild sequencing should live in the view helper."""
    import inspect

    import app.routes.settings as settings_route
    import app.routes.settings_view as settings_view

    calls: list[tuple[str, object]] = []
    config_store = MagicMock()
    rebuilt_registry = object()

    def make_config_store():
        calls.append(("store", None))
        return config_store

    def record_rebuild(**kwargs):
        calls.append(("rebuild", kwargs))
        return rebuilt_registry

    monkeypatch.setattr(settings_view, "save_provider_key_and_rebuild_registry", record_rebuild)

    missing_key = settings_view.provider_key_save_action(
        provider_id="urlhaus",
        api_key="",
        valid_provider_ids=frozenset(("urlhaus",)),
        config_store_factory=make_config_store,
        allowed_hosts=("api.example.test",),
    )
    unknown_provider = settings_view.provider_key_save_action(
        provider_id="missing",
        api_key="key",
        valid_provider_ids=frozenset(("urlhaus",)),
        config_store_factory=make_config_store,
        allowed_hosts=("api.example.test",),
    )
    saved = settings_view.provider_key_save_action(
        provider_id="urlhaus",
        api_key="key",
        valid_provider_ids=frozenset(("urlhaus",)),
        config_store_factory=make_config_store,
        allowed_hosts=("api.example.test",),
    )
    route_source = inspect.getsource(settings_route.settings_post)
    helper_source = inspect.getsource(settings_view.provider_key_save_action)

    assert missing_key == settings_view.SettingsActionResult("API key cannot be empty.", "error")
    assert unknown_provider == settings_view.SettingsActionResult("Unknown provider.", "error")
    assert saved == settings_view.SettingsActionResult(
        "API key saved for urlhaus.",
        "success",
        rebuilt_registry,
    )
    assert calls == [
        ("store", None),
        (
            "rebuild",
            {
                "config_store": config_store,
                "provider_id": "urlhaus",
                "api_key": "key",
                "allowed_hosts": ("api.example.test",),
            },
        ),
    ]
    assert "settings_view.provider_key_save_route_response(" in route_source
    assert "if not api_key:" not in route_source
    assert "provider_id not in _VALID_PROVIDER_IDS" not in route_source
    assert "ConfigStore()" not in route_source
    assert "save_provider_key_and_rebuild_registry(" in helper_source


def test_apply_settings_action_owns_optional_registry_assignment() -> None:
    """Settings action app-state mutation should live outside the Flask route body."""
    import inspect

    import app.routes.settings as settings_route
    import app.routes.settings_view as settings_view

    rebuilt_registry = object()
    assigned: list[object] = []

    unchanged = settings_view.apply_settings_action(
        settings_view.SettingsActionResult("noop", "error"),
        set_registry=assigned.append,
    )
    changed = settings_view.apply_settings_action(
        settings_view.SettingsActionResult("saved", "success", rebuilt_registry),
        set_registry=assigned.append,
    )
    route_source = inspect.getsource(settings_route.settings_post)
    helper_source = inspect.getsource(settings_view.apply_settings_action)

    assert unchanged == settings_view.SettingsActionResult("noop", "error")
    assert changed == settings_view.SettingsActionResult("saved", "success", rebuilt_registry)
    assert assigned == [rebuilt_registry]
    assert "settings_view.provider_key_save_route_response(" in route_source
    assert "settings_view.apply_settings_action_response(" not in route_source
    assert "if action.registry is not None:" not in route_source
    assert "current_app.registry = action.registry" not in route_source
    assert "set_registry=_set_current_registry" in route_source
    assert "if action.registry is not None:" in helper_source
    assert "set_registry(action.registry)" in helper_source


def test_positive_cache_ttl_helper_owns_ttl_validation() -> None:
    """Cache TTL parsing should live outside the Flask route body."""
    import inspect

    import app.routes.settings as settings_route
    import app.routes.settings_view as settings_view

    route_source = inspect.getsource(settings_route.cache_ttl_set)

    assert settings_view.positive_cache_ttl_hours("1") == 1
    assert settings_view.positive_cache_ttl_hours("24") == 24
    assert settings_view.positive_cache_ttl_hours("0") is None
    assert settings_view.positive_cache_ttl_hours("-1") is None
    assert settings_view.positive_cache_ttl_hours("not-a-number") is None
    assert "settings_view.cache_ttl_update_route_response(" in route_source
    assert "positive_cache_ttl_hours(" not in route_source
    assert "int(" not in route_source
    assert "ValueError" not in route_source
    assert "set_cache_ttl(" not in route_source


def test_cache_ttl_update_action_owns_validation_and_save() -> None:
    """Cache TTL save behavior should live outside the Flask route body."""
    import inspect

    import app.routes.settings as settings_route
    import app.routes.settings_view as settings_view

    config_store = MagicMock()
    created: list[str] = []

    def make_config_store():
        created.append("store")
        return config_store

    invalid = settings_view.cache_ttl_update_action(
        raw_ttl="0",
        config_store_factory=make_config_store,
    )
    saved = settings_view.cache_ttl_update_action(
        raw_ttl="6",
        config_store_factory=make_config_store,
    )
    route_source = inspect.getsource(settings_route.cache_ttl_set)
    helper_source = inspect.getsource(settings_view.cache_ttl_update_action)

    assert invalid == settings_view.SettingsActionResult(
        "TTL must be a positive integer.",
        "error",
    )
    assert saved == settings_view.SettingsActionResult("Cache TTL set to 6 hours.", "success")
    assert created == ["store"]
    config_store.set_cache_ttl.assert_called_once_with(6)
    assert "settings_view.cache_ttl_update_route_response(" in route_source
    assert "ConfigStore()" not in route_source
    assert "set_cache_ttl(" not in route_source
    assert "positive_cache_ttl_hours(raw_ttl)" in helper_source
    assert "config_store.set_cache_ttl(ttl)" in helper_source


def test_cache_ttl_update_route_response_owns_action_application(monkeypatch) -> None:
    """Cache TTL POST should share one helper for form action and response application."""
    import inspect

    import app.routes.settings as settings_route
    import app.routes.settings_view as settings_view

    form = {"cache_ttl": "6"}
    action = settings_view.SettingsActionResult("saved", "success")
    calls: list[tuple[str, dict[str, object]]] = []

    def action_from_form(form_arg, **kwargs):
        calls.append(("action", {"form": form_arg, **kwargs}))
        return action

    def action_response(action_arg, **kwargs):
        calls.append(("response", {"action": action_arg, **kwargs}))
        return "redirected"

    monkeypatch.setattr(settings_view, "cache_ttl_update_action_from_form", action_from_form)
    monkeypatch.setattr(settings_view, "apply_settings_action_response", action_response)

    response = settings_view.cache_ttl_update_route_response(
        form,
        config_store_factory=object,
        set_registry=list.append,
        flash_message=print,
        redirect_to=str,
        settings_url="/settings",
    )
    route_source = inspect.getsource(settings_route.cache_ttl_set)
    route_helper_source = inspect.getsource(settings_view.cache_ttl_update_route_response)

    assert response == "redirected"
    assert calls == [
        ("action", {
            "form": form,
            "config_store_factory": object,
        }),
        ("response", {
            "action": action,
            "set_registry": list.append,
            "flash_message": print,
            "redirect_to": str,
            "settings_url": "/settings",
        }),
    ]
    assert "settings_view.cache_ttl_update_route_response(" in route_source
    assert "cache_ttl_update_action_from_form(" not in route_source
    assert "apply_settings_action_response(" not in route_source
    assert "cache_ttl_update_action_from_form(" in route_helper_source
    assert "apply_settings_action_response(" in route_helper_source


def test_cache_clear_action_owns_cache_clear_and_result() -> None:
    """Cache clear behavior should share the settings action helper pattern."""
    import inspect

    import app.routes.settings as settings_route
    import app.routes.settings_view as settings_view

    cache_store = MagicMock()

    result = settings_view.cache_clear_action(cache_store)
    route_source = inspect.getsource(settings_route.cache_clear)
    helper_source = inspect.getsource(settings_view.cache_clear_action)

    assert result == settings_view.SettingsActionResult("Cache cleared.", "success")
    cache_store.clear.assert_called_once_with()
    assert "settings_view.cache_clear_route_response(" in route_source
    assert "current_app.cache_store.clear()" not in route_source
    assert "CACHE_CLEARED_MESSAGE" not in route_source
    assert "cache_store.clear()" in helper_source


def test_cache_clear_route_response_owns_action_application(monkeypatch) -> None:
    """Cache clear POST should share one helper for action and response application."""
    import inspect

    import app.routes.settings as settings_route
    import app.routes.settings_view as settings_view

    cache_store = object()
    action = settings_view.SettingsActionResult("cleared", "success")
    calls: list[tuple[str, dict[str, object]]] = []

    def clear_action(cache_store_arg):
        calls.append(("action", {"cache_store": cache_store_arg}))
        return action

    def action_response(action_arg, **kwargs):
        calls.append(("response", {"action": action_arg, **kwargs}))
        return "redirected"

    monkeypatch.setattr(settings_view, "cache_clear_action", clear_action)
    monkeypatch.setattr(settings_view, "apply_settings_action_response", action_response)

    response = settings_view.cache_clear_route_response(
        cache_store,
        set_registry=list.append,
        flash_message=print,
        redirect_to=str,
        settings_url="/settings",
    )
    route_source = inspect.getsource(settings_route.cache_clear)
    route_helper_source = inspect.getsource(settings_view.cache_clear_route_response)

    assert response == "redirected"
    assert calls == [
        ("action", {"cache_store": cache_store}),
        ("response", {
            "action": action,
            "set_registry": list.append,
            "flash_message": print,
            "redirect_to": str,
            "settings_url": "/settings",
        }),
    ]
    assert "settings_view.cache_clear_route_response(" in route_source
    assert "cache_clear_action(" not in route_source
    assert "apply_settings_action_response(" not in route_source
    assert "cache_clear_action(" in route_helper_source
    assert "apply_settings_action_response(" in route_helper_source


def test_provider_status_rows_accumulates_without_constructor_copy():
    """Provider status rows should copy provider metadata without dict(info)."""
    import inspect

    import app.routes.settings_view as settings_view

    class NoDictCopyInfo(dict):
        def keys(self):
            raise AssertionError("provider status rows should iterate mapping directly")

        def items(self):
            raise AssertionError("provider status rows should not allocate an items view")

    provider_info = (
        NoDictCopyInfo({"id": "virustotal", "name": "VirusTotal"}),
        NoDictCopyInfo({"id": "urlhaus", "name": "URLhaus"}),
    )
    rows = settings_view.provider_status_rows(
        provider_info,
        {"urlhaus": "urlhaus-key-123456"},
        "vt-key-123456",
    )
    source = inspect.getsource(settings_view.provider_status_rows)

    assert rows[0]["name"] == "VirusTotal"
    assert rows[1]["name"] == "URLhaus"
    assert rows[0]["masked_key"].endswith("3456")
    assert rows[1]["masked_key"].endswith("3456")
    assert "dict(" not in source
    assert ".items()" not in source
    assert "append_provider_status_row(rows, info, provider_keys, vt_api_key)" in source
    assert "rows.append(_provider_status_row(info, provider_keys, vt_api_key))" not in source
    assert "rows.append(_provider_status_row(info, provider_keys, vt_api_key))" in inspect.getsource(
        settings_view.append_provider_status_row
    )
    status_row = settings_view._provider_status_row(
        NoDictCopyInfo({"id": "urlhaus", "name": "URLhaus"}),
        {"urlhaus": "urlhaus-key-123456"},
        None,
    )
    assert status_row["id"] == "urlhaus"
    assert status_row["name"] == "URLhaus"
    assert status_row["masked_key"].endswith("3456")
    assert status_row["configured"] is True


def test_get_settings_page_shows_history_save_diagnostics(client):
    """GET /settings renders bounded aggregate diagnostics for history saves."""
    diagnostics = {
        "attempts": 3,
        "successes": 2,
        "failures": 1,
        "skipped": 1,
        "last_outcome": "failed",
        "last_attempt_at": "2026-04-22T09:00:00Z",
        "last_success_at": "2026-04-22T08:59:00Z",
        "last_failure_at": "2026-04-22T09:00:00Z",
        "last_error_summary": "RuntimeError while saving analysis history",
        "input_text": "secret analyst note",
        "results": [{"ioc_value": "evil.com"}],
    }

    with patch("app.routes.settings.get_history_save_diagnostics", return_value=diagnostics):
        response = client.get("/settings")

    data = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "History Save Diagnostics" in data
    assert "3 attempted saves" in data
    assert "2 successful" in data
    assert "1 failed" in data
    assert "1 skipped" in data
    assert "RuntimeError while saving analysis history" in data
    assert "secret analyst note" not in data
    assert "evil.com" not in data


def test_get_settings_page_history_save_diagnostics_defaults(client):
    """GET /settings shows safe defaults when diagnostics have no timestamps yet."""
    diagnostics = {
        "attempts": 0,
        "successes": 0,
        "failures": 0,
        "skipped": 0,
        "last_outcome": "never",
        "last_attempt_at": None,
        "last_success_at": None,
        "last_failure_at": None,
        "last_error_summary": None,
    }

    with patch("app.routes.settings.get_history_save_diagnostics", return_value=diagnostics):
        response = client.get("/settings")

    data = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Last outcome:</strong> never" in data
    assert data.count("Never") >= 3
    assert "Last error summary:</strong> None" in data


def test_get_settings_page_no_key_configured(client):
    """GET /settings when no key is configured shows empty/masked field."""
    with patch("app.routes.settings.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        mock_instance.get_vt_api_key.return_value = None
        mock_instance.get_provider_key.return_value = None
        mock_instance.all_provider_keys.return_value = {}
        MockStore.return_value = mock_instance

        response = client.get("/settings")
        assert response.status_code == 200
        assert b"Settings" in response.data


def test_get_settings_page_shows_all_five_providers(client):
    """GET /settings renders a section for each of the 5 key-requiring providers."""
    response = client.get("/settings")
    assert response.status_code == 200
    for name in [b"VirusTotal", b"URLhaus", b"OTX AlienVault", b"GreyNoise", b"AbuseIPDB"]:
        assert name in response.data, f"Expected provider section for {name!r}"


def test_get_settings_page_shows_provider_id_fields(client):
    """GET /settings includes hidden provider_id fields for each provider."""
    response = client.get("/settings")
    assert response.status_code == 200
    for pid in [b"virustotal", b"urlhaus", b"otx", b"greynoise", b"abuseipdb"]:
        assert pid in response.data, f"Expected provider_id {pid!r} in form"


def test_get_settings_configured_badge(client):
    """GET /settings shows 'Configured' badge when VT key is set."""
    with patch("app.routes.settings.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        mock_instance.get_vt_api_key.return_value = "abcdef1234567890"
        mock_instance.get_provider_key.return_value = None
        mock_instance.all_provider_keys.return_value = {}
        MockStore.return_value = mock_instance

        response = client.get("/settings")
        assert response.status_code == 200
        assert b"Configured" in response.data


def test_get_settings_not_configured_badge(client):
    """GET /settings shows 'Not configured' badge when no key is set."""
    with patch("app.routes.settings.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        mock_instance.get_vt_api_key.return_value = None
        mock_instance.get_provider_key.return_value = None
        mock_instance.all_provider_keys.return_value = {}
        MockStore.return_value = mock_instance

        response = client.get("/settings")
        assert response.status_code == 200
        assert b"Not configured" in response.data


def test_get_settings_reads_provider_key_map_once(client):
    """GET /settings uses the provider-key map instead of per-provider reads."""
    with patch("app.routes.settings.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        mock_instance.get_vt_api_key.return_value = None
        mock_instance.all_provider_keys.return_value = {"urlhaus": "urlhaus-key-123456"}
        MockStore.return_value = mock_instance

        response = client.get("/settings")

        assert response.status_code == 200
        mock_instance.all_provider_keys.assert_called_once_with()
        mock_instance.get_provider_key.assert_not_called()
        assert b"Configured" in response.data


def test_virustotal_provider_id_is_static_route_constant() -> None:
    """Settings display and save paths should share one VirusTotal provider id."""
    import app.routes.settings as settings_route
    import app.routes.settings_view as settings_view

    assert settings_view.VIRUSTOTAL_PROVIDER_ID == "virustotal"
    assert settings_route.settings_get.__code__.co_consts.count("virustotal") == 0
    assert settings_route.settings_post.__code__.co_consts.count("virustotal") == 0


def test_valid_provider_ids_reuse_catalog_helper_without_route_list_builder() -> None:
    """Settings provider-id validation should reuse catalog metadata without route list building."""
    import app.routes.settings as settings_route
    from app.enrichment.provider_catalog import PROVIDER_INFO, valid_provider_ids

    provider_info_ids = tuple(str(provider["id"]) for provider in PROVIDER_INFO)
    with open("app/routes/settings.py", encoding="utf-8") as source_file:
        source = source_file.read()
    catalog_source = inspect.getsource(valid_provider_ids)

    assert settings_route._VALID_PROVIDER_IDS == valid_provider_ids()
    assert settings_route._VALID_PROVIDER_IDS == frozenset(provider_info_ids)
    assert "for provider in PROVIDER_INFO" not in catalog_source
    assert "provider_ids: set" not in catalog_source
    assert 'frozenset(("' not in catalog_source
    assert "frozenset((" in catalog_source
    assert "import PROVIDER_IDS" not in source
    assert "\nPROVIDER_IDS =" not in source
    assert "_valid_provider_ids" not in source
    assert "provider_ids: list" not in source


# ---------------------------------------------------------------------------
# POST /settings — saving an API key
# ---------------------------------------------------------------------------


def test_save_vt_api_key(client, tmp_path):
    """POST /settings with provider_id=virustotal saves via set_vt_api_key and redirects."""
    with patch("app.routes.settings.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        mock_instance.get_vt_api_key.return_value = "test123"
        mock_instance.get_provider_key.return_value = None
        mock_instance.all_provider_keys.return_value = {}
        MockStore.return_value = mock_instance

        response = client.post(
            "/settings",
            data={"api_key": "test123", "provider_id": "virustotal"},
        )

        # Should redirect to GET /settings
        assert response.status_code == 302
        assert "/settings" in response.headers["Location"]

        # ConfigStore.set_vt_api_key should have been called with the key
        mock_instance.set_vt_api_key.assert_called_once_with("test123")


def test_save_provider_key_for_urlhaus(client, tmp_path):
    """POST /settings with provider_id=urlhaus saves via set_provider_key and redirects."""
    with patch("app.routes.settings.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        mock_instance.get_vt_api_key.return_value = None
        mock_instance.get_provider_key.return_value = None
        mock_instance.all_provider_keys.return_value = {"urlhaus": "urlhaus-key-123"}
        MockStore.return_value = mock_instance

        response = client.post(
            "/settings",
            data={"api_key": "urlhaus-key-123", "provider_id": "urlhaus"},
        )

        assert response.status_code == 302
        assert "/settings" in response.headers["Location"]
        mock_instance.set_provider_key.assert_called_once_with("urlhaus", "urlhaus-key-123")


def test_save_api_key_follows_redirect(client):
    """POST /settings with valid key, following redirect, shows success message."""
    with patch("app.routes.settings.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        mock_instance.get_vt_api_key.return_value = "saved-key-abcd"
        mock_instance.get_provider_key.return_value = None
        mock_instance.all_provider_keys.return_value = {}
        MockStore.return_value = mock_instance

        response = client.post(
            "/settings",
            data={"api_key": "saved-key-abcd", "provider_id": "virustotal"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"saved" in response.data.lower() or b"success" in response.data.lower()


def test_save_empty_key_rejected(client):
    """POST /settings with empty api_key shows error and does not call set_vt_api_key."""
    with patch("app.routes.settings.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        MockStore.return_value = mock_instance

        response = client.post(
            "/settings",
            data={"api_key": "", "provider_id": "virustotal"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        # Error message must be shown
        assert b"empty" in response.data.lower() or b"cannot" in response.data.lower()
        # set_vt_api_key must NOT have been called
        mock_instance.set_vt_api_key.assert_not_called()


def test_save_whitespace_only_key_rejected(client):
    """POST /settings with whitespace-only api_key is treated as empty and rejected."""
    with patch("app.routes.settings.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        MockStore.return_value = mock_instance

        response = client.post(
            "/settings",
            data={"api_key": "   ", "provider_id": "virustotal"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        mock_instance.set_vt_api_key.assert_not_called()


def test_save_unknown_provider_id_rejected(client):
    """POST /settings with unknown provider_id shows error and does not save."""
    with patch("app.routes.settings.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        mock_instance.get_vt_api_key.return_value = None
        mock_instance.get_provider_key.return_value = None
        mock_instance.all_provider_keys.return_value = {}
        MockStore.return_value = mock_instance

        response = client.post(
            "/settings",
            data={"api_key": "some-key", "provider_id": "notaprovider"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"unknown" in response.data.lower()
        mock_instance.set_vt_api_key.assert_not_called()
        mock_instance.set_provider_key.assert_not_called()


def test_save_provider_validation_uses_precomputed_id_set(client, monkeypatch):
    """POST /settings should not rebuild provider id sets per request."""
    import app.routes.settings as settings_route

    assert "virustotal" in settings_route._VALID_PROVIDER_IDS
    assert "urlhaus" in settings_route._VALID_PROVIDER_IDS
    with open("app/routes/settings.py", encoding="utf-8") as source_file:
        source = source_file.read()

    class NonIterableProviderInfo:
        def __iter__(self):
            raise AssertionError("settings provider validation should reuse _VALID_PROVIDER_IDS")

    monkeypatch.setattr(settings_route, "PROVIDER_INFO", NonIterableProviderInfo())

    with patch("app.routes.settings.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        mock_instance.get_vt_api_key.return_value = None
        mock_instance.all_provider_keys.return_value = {}
        MockStore.return_value = mock_instance

        response = client.post(
            "/settings",
            data={"api_key": "some-key", "provider_id": "notaprovider"},
        )

        assert response.status_code == 302
        assert "/settings" in response.headers["Location"]
        mock_instance.set_vt_api_key.assert_not_called()
        mock_instance.set_provider_key.assert_not_called()
        assert "_valid_provider_ids" not in source
        assert "_VALID_PROVIDER_IDS = valid_provider_ids()" in source


def test_settings_post_and_cache_ttl_share_form_normalization(client, monkeypatch):
    """Settings save and cache TTL forms should use one stripped-value helper."""
    import app.routes.settings_view as settings_view

    calls: list[tuple[object, str]] = []

    def form_value(form, field_name: str) -> str:
        calls.append((form, field_name))
        values = {
            "provider_id": "virustotal",
            "api_key": "saved-key",
            "cache_ttl": "6",
        }
        return values[field_name]

    monkeypatch.setattr(settings_view, "stripped_form_value", form_value)

    with patch("app.routes.settings.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        MockStore.return_value = mock_instance

        save_response = client.post(
            "/settings",
            data={"provider_id": " virustotal ", "api_key": " saved-key "},
        )
        ttl_response = client.post(
            "/settings/cache/ttl",
            data={"cache_ttl": " 6 "},
        )

        assert save_response.status_code == 302
        assert ttl_response.status_code == 302
        mock_instance.set_vt_api_key.assert_called_once_with("saved-key")
        mock_instance.set_cache_ttl.assert_called_once_with(6)
        assert [field_name for _form, field_name in calls] == [
            "provider_id",
            "api_key",
            "cache_ttl",
        ]


def test_settings_form_normalization_lives_in_shared_route_helper(app):
    """Settings should delegate form-field stripping to the shared route helper."""
    import inspect

    import app.routes.form_values as form_values
    import app.routes.settings as settings_route
    import app.routes.settings_view as settings_view

    class NoStripValue(str):
        def strip(self, *_args, **_kwargs):
            raise AssertionError("settings form normalization should avoid direct strip allocation")

    form = {"api_key": NoStripValue("  saved-key  ")}
    route_source = inspect.getsource(settings_route.settings_post)
    ttl_route_source = inspect.getsource(settings_route.cache_ttl_set)
    provider_helper_source = inspect.getsource(settings_view.provider_key_save_action_from_form)
    ttl_helper_source = inspect.getsource(settings_view.cache_ttl_update_action_from_form)
    helper_source = inspect.getsource(form_values.stripped_form_value)

    assert form_values.stripped_form_value(form, "api_key") == "saved-key"
    assert form_values.stripped_form_value(form, "missing") == ""
    assert "stripped_form_value(" not in route_source
    assert "stripped_form_value(" not in ttl_route_source
    assert "stripped_form_value(form, \"provider_id\")" in provider_helper_source
    assert "stripped_form_value(form, \"api_key\")" in provider_helper_source
    assert "stripped_form_value(form, \"cache_ttl\")" in ttl_helper_source
    assert "request.form.get" not in route_source
    assert "stripped_text_or_none(value)" in helper_source
    assert "strip" not in form_values.stripped_form_value.__code__.co_names


def test_settings_action_response_application_lives_in_view_helper():
    """Settings routes should delegate action mutation, flash, and redirect plumbing."""
    import inspect

    import app.routes.browser_responses as browser_responses
    import app.routes.settings as settings_route
    import app.routes.settings_view as settings_view

    route_source = inspect.getsource(settings_route)
    post_source = inspect.getsource(settings_route.settings_post)
    clear_source = inspect.getsource(settings_route.cache_clear)
    ttl_source = inspect.getsource(settings_route.cache_ttl_set)
    response_source = inspect.getsource(settings_view.apply_settings_action_response)
    shared_source = inspect.getsource(browser_responses.apply_flash_redirect)

    assert settings_view.API_KEY_EMPTY_MESSAGE == "API key cannot be empty."
    assert settings_view.UNKNOWN_PROVIDER_MESSAGE == "Unknown provider."
    assert settings_view.CACHE_CLEARED_MESSAGE == "Cache cleared."
    assert settings_view.TTL_INVALID_MESSAGE == "TTL must be a positive integer."
    assert settings_view.api_key_saved_message("urlhaus") == "API key saved for urlhaus."
    assert settings_view.cache_ttl_saved_message(6) == "Cache TTL set to 6 hours."
    assert "settings_view.cache_clear_route_response(" in clear_source
    assert "settings_view.cache_ttl_update_route_response(" in ttl_source
    assert "settings_view.provider_key_save_route_response(" in post_source
    assert "settings_view.apply_settings_action_response(" not in post_source
    assert "settings_view.apply_settings_action_response(" not in clear_source
    assert "settings_view.apply_settings_action_response(" not in ttl_source
    assert "set_registry=_set_current_registry" in post_source
    assert "set_registry=_set_current_registry" in clear_source
    assert "set_registry=_set_current_registry" in ttl_source
    assert "_provider_key_save_action_from_form" not in route_source
    assert "_cache_clear_action" not in route_source
    assert "_cache_ttl_update_action_from_form" not in route_source
    assert "apply_settings_action(action, set_registry=set_registry)" in response_source
    assert "apply_flash_redirect(" in response_source
    assert "FlashRedirect(settings_url, applied.message, applied.category)" in response_source
    assert "flash_message(result.message, result.category)" in shared_source
    assert "redirect_to(resolve_url(result.url))" in shared_source
    assert "_settings_flash_redirect" not in route_source
    assert "flash(action.message" not in route_source
    assert "redirect(url_for(\"main.settings_get\"))" not in route_source
    assert "API key cannot be empty." not in route_source
    assert "Unknown provider." not in route_source
    assert "Cache cleared." not in route_source
    assert "TTL must be a positive integer." not in route_source
    assert "API key saved for {provider_id}" not in route_source
    assert "Cache TTL set to {ttl}" not in route_source


def test_apply_settings_action_response_preserves_flash_redirect_and_registry_assignment():
    """The settings response helper should apply mutations before flashing/redirecting."""
    from types import SimpleNamespace

    import app.routes.settings_view as settings_view

    registry = object()
    action = settings_view.SettingsActionResult("Saved.", "success", registry)
    assigned: list[object] = []
    calls: list[tuple[str, object]] = []

    def flash_message(message, category):
        calls.append(("flash", (message, category, assigned == [registry])))

    def redirect_to(url):
        calls.append(("redirect", url))
        return ("response", url)

    response = settings_view.apply_settings_action_response(
        action,
        set_registry=assigned.append,
        flash_message=flash_message,
        redirect_to=redirect_to,
        settings_url="/settings",
    )

    assert assigned == [registry]
    assert calls == [
        ("flash", ("Saved.", "success", True)),
        ("redirect", "/settings"),
    ]
    assert response == ("response", "/settings")


def test_stripped_form_value_uses_index_trim_without_strip(app):
    """Form normalization should avoid direct strip allocation."""
    import app.routes.form_values as form_values

    class NoStripValue(str):
        def strip(self, *_args, **_kwargs):
            raise AssertionError("settings form normalization should avoid direct strip allocation")

    form = {"api_key": NoStripValue("  saved-key  ")}

    assert form_values.stripped_form_value(form, "api_key") == "saved-key"
    assert form_values.stripped_form_value(form, "missing") == ""
    assert "strip" not in form_values.stripped_form_value.__code__.co_names


def test_save_missing_provider_id_rejected(client):
    """POST /settings with no provider_id shows error and does not save."""
    with patch("app.routes.settings.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        mock_instance.get_vt_api_key.return_value = None
        mock_instance.get_provider_key.return_value = None
        mock_instance.all_provider_keys.return_value = {}
        MockStore.return_value = mock_instance

        response = client.post(
            "/settings",
            data={"api_key": "some-key"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"unknown" in response.data.lower()
        mock_instance.set_vt_api_key.assert_not_called()


# ---------------------------------------------------------------------------
# Key masking behaviour
# ---------------------------------------------------------------------------


def test_settings_page_keeps_configured_secret_input_empty(client):
    """GET /settings reports configured state without putting a masked key in the input."""
    secret = "abcdef1234567890abcdef1234567890"  # noqa: S105 - leak sentinel.
    with patch("app.routes.settings.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        mock_instance.get_vt_api_key.return_value = secret
        mock_instance.get_provider_key.return_value = None
        mock_instance.all_provider_keys.return_value = {}
        MockStore.return_value = mock_instance

        response = client.get("/settings")
        assert response.status_code == 200
        data = response.get_data(as_text=True)

        assert "A key is configured. Enter a new key only to replace it." in data
        assert 'name="api_key"' in data
        assert 'value=""' in data
        assert secret not in data
        assert "****************************7890" not in data


def test_save_masked_api_key_rejected(client):
    """POST /settings must not persist a legacy masked display value."""
    with patch("app.routes.settings.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        MockStore.return_value = mock_instance

        response = client.post(
            "/settings",
            data={"api_key": "************7890", "provider_id": "virustotal"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"new API key" in response.data
        mock_instance.set_vt_api_key.assert_not_called()
        mock_instance.set_provider_key.assert_not_called()


def test_settings_page_masks_short_key(client):
    """GET /settings with a key of 4 chars or fewer shows no key (masks everything)."""
    with patch("app.routes.settings.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        mock_instance.get_vt_api_key.return_value = "abcd"
        mock_instance.get_provider_key.return_value = None
        mock_instance.all_provider_keys.return_value = {}
        MockStore.return_value = mock_instance

        response = client.get("/settings")
        assert response.status_code == 200
        # Short key should not be revealed at all
        data = response.data.decode("utf-8")
        assert "abcd" not in data


def test_mask_key_measures_configured_key_once():
    """Configured key masking should not repeat length work on the same key."""
    from app.routes.settings_view import _mask_key

    class MeasuredKey(str):
        len_calls = 0

        def __len__(self):
            type(self).len_calls += 1
            return super().__len__()

    masked = _mask_key(MeasuredKey("abcdef1234567890"))

    assert masked == "************7890"
    assert MeasuredKey.len_calls == 1


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------


def test_settings_link_in_nav(client):
    """GET / contains a link to /settings in the navigation."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"/settings" in response.data or b"Settings" in response.data
