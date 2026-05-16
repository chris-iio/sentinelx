"""Integration tests for the settings page and API key management.

Tests cover:
- GET /settings renders settings page with expected content (5 provider sections)
- POST /settings saves API key via ConfigStore and redirects
- POST /settings with empty key shows error and rejects save
- POST /settings with unknown provider_id shows error and rejects save
- Stored key is masked (only last 4 chars visible) on GET /settings
- Multi-provider: different provider_id routes to correct ConfigStore method
"""
from unittest.mock import MagicMock, patch


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

    assert settings_route._VIRUSTOTAL_PROVIDER_ID == "virustotal"
    assert settings_route.settings_get.__code__.co_consts.count("virustotal") == 0
    assert settings_route.settings_post.__code__.co_consts.count("virustotal") == 0


def test_valid_provider_ids_reuse_setup_tuple_without_route_list_builder() -> None:
    """Settings provider-id validation should reuse setup metadata without route list building."""
    import app.routes.settings as settings_route
    from app.enrichment.setup import PROVIDER_IDS, PROVIDER_INFO

    provider_info_ids = tuple(str(provider["id"]) for provider in PROVIDER_INFO)
    source = open("app/routes/settings.py", encoding="utf-8").read()

    assert PROVIDER_IDS == provider_info_ids
    assert settings_route._VALID_PROVIDER_IDS == frozenset(PROVIDER_IDS)
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
    source = open("app/routes/settings.py", encoding="utf-8").read()

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
        assert "_VALID_PROVIDER_IDS = frozenset(PROVIDER_IDS)" in source


def test_settings_post_and_cache_ttl_share_form_normalization(client, monkeypatch):
    """Settings save and cache TTL forms should use one stripped-value helper."""
    import app.routes.settings as settings_route

    calls: list[str] = []

    def form_value(field_name: str) -> str:
        calls.append(field_name)
        values = {
            "provider_id": "virustotal",
            "api_key": "saved-key",
            "cache_ttl": "6",
        }
        return values[field_name]

    monkeypatch.setattr(settings_route, "_stripped_form_value", form_value)

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
        assert calls == ["provider_id", "api_key", "cache_ttl"]


def test_stripped_form_value_uses_index_trim_without_strip(app):
    """Form normalization should avoid direct strip allocation."""
    import app.routes.settings as settings_route

    class NoStripValue(str):
        def strip(self, *_args, **_kwargs):
            raise AssertionError("settings form normalization should avoid direct strip allocation")

    with app.test_request_context(
        "/settings",
        method="POST",
        data={"api_key": NoStripValue("  saved-key  ")},
    ):
        assert settings_route._stripped_form_value("api_key") == "saved-key"
        assert settings_route._stripped_form_value("missing") == ""

    assert "strip" not in settings_route._stripped_form_value.__code__.co_names


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


def test_settings_page_masks_key(client):
    """GET /settings when a key is configured shows only last 4 chars (masked)."""
    with patch("app.routes.settings.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        # 32-char key — last 4 should be visible, rest masked
        mock_instance.get_vt_api_key.return_value = "abcdef1234567890abcdef1234567890"
        mock_instance.get_provider_key.return_value = None
        mock_instance.all_provider_keys.return_value = {}
        MockStore.return_value = mock_instance

        response = client.get("/settings")
        assert response.status_code == 200
        data = response.data.decode("utf-8")

        # Last 4 chars should appear in page
        assert "7890" in data
        # The full key should NOT appear unmasked
        assert "abcdef1234567890abcdef1234" not in data


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
    from app.routes._helpers import _mask_key

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
