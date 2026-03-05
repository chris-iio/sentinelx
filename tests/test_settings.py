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


def test_get_settings_page_no_key_configured(client):
    """GET /settings when no key is configured shows empty/masked field."""
    with patch("app.routes.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        mock_instance.get_vt_api_key.return_value = None
        mock_instance.get_provider_key.return_value = None
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
    with patch("app.routes.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        mock_instance.get_vt_api_key.return_value = "abcdef1234567890"
        mock_instance.get_provider_key.return_value = None
        MockStore.return_value = mock_instance

        response = client.get("/settings")
        assert response.status_code == 200
        assert b"Configured" in response.data


def test_get_settings_not_configured_badge(client):
    """GET /settings shows 'Not configured' badge when no key is set."""
    with patch("app.routes.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        mock_instance.get_vt_api_key.return_value = None
        mock_instance.get_provider_key.return_value = None
        MockStore.return_value = mock_instance

        response = client.get("/settings")
        assert response.status_code == 200
        assert b"Not configured" in response.data


# ---------------------------------------------------------------------------
# POST /settings — saving an API key
# ---------------------------------------------------------------------------


def test_save_vt_api_key(client, tmp_path):
    """POST /settings with provider_id=virustotal saves via set_vt_api_key and redirects."""
    with patch("app.routes.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        mock_instance.get_vt_api_key.return_value = "test123"
        mock_instance.get_provider_key.return_value = None
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
    with patch("app.routes.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        mock_instance.get_vt_api_key.return_value = None
        mock_instance.get_provider_key.return_value = None
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
    with patch("app.routes.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        mock_instance.get_vt_api_key.return_value = "saved-key-abcd"
        mock_instance.get_provider_key.return_value = None
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
    with patch("app.routes.ConfigStore") as MockStore:
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
    with patch("app.routes.ConfigStore") as MockStore:
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
    with patch("app.routes.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        mock_instance.get_vt_api_key.return_value = None
        mock_instance.get_provider_key.return_value = None
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


def test_save_missing_provider_id_rejected(client):
    """POST /settings with no provider_id shows error and does not save."""
    with patch("app.routes.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        mock_instance.get_vt_api_key.return_value = None
        mock_instance.get_provider_key.return_value = None
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
    with patch("app.routes.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        # 32-char key — last 4 should be visible, rest masked
        mock_instance.get_vt_api_key.return_value = "abcdef1234567890abcdef1234567890"
        mock_instance.get_provider_key.return_value = None
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
    with patch("app.routes.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        mock_instance.get_vt_api_key.return_value = "abcd"
        mock_instance.get_provider_key.return_value = None
        MockStore.return_value = mock_instance

        response = client.get("/settings")
        assert response.status_code == 200
        # Short key should not be revealed at all
        data = response.data.decode("utf-8")
        assert "abcd" not in data


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------


def test_settings_link_in_nav(client):
    """GET / contains a link to /settings in the navigation."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"/settings" in response.data or b"Settings" in response.data


# ---------------------------------------------------------------------------
# Backward compatibility — old test names preserved
# ---------------------------------------------------------------------------


def test_save_api_key(client, tmp_path):
    """POST /settings with api_key and provider_id=virustotal saves and redirects."""
    with patch("app.routes.ConfigStore") as MockStore:
        mock_instance = MagicMock()
        mock_instance.get_vt_api_key.return_value = "test123"
        mock_instance.get_provider_key.return_value = None
        MockStore.return_value = mock_instance

        response = client.post(
            "/settings",
            data={"api_key": "test123", "provider_id": "virustotal"},
        )

        assert response.status_code == 302
        assert "/settings" in response.headers["Location"]
        mock_instance.set_vt_api_key.assert_called_once_with("test123")
