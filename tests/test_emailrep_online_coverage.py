"""Route-level coverage for EmailRep settings and Online email provider counts."""

from __future__ import annotations

import json
import re
from html import unescape
from unittest.mock import Mock

from app.enrichment.config_store import ConfigStore
from app.enrichment.setup import build_registry
from app.pipeline.models import IOC, IOCType


EMAILREP_TEST_KEY = "emailrep-route-test-key-1234567890"
EMAIL_IOC = IOC(
    type=IOCType.EMAIL,
    value="analyst@example.com",
    raw_match="analyst@example.com",
)


def _provider_counts_from_html(html: str) -> dict[str, int]:
    """Extract the JSON provider-count map from the results root attribute."""
    match = re.search(r'data-provider-counts="([^"]+)"', html)
    assert match is not None, "results page did not expose data-provider-counts"
    return json.loads(unescape(match.group(1)))


def _post_online_email(client, registry):
    """Submit a representative email IOC with background enrichment patched out."""
    client.application.registry = registry

    setup_orchestrator = Mock(return_value=("emailrep-test-job", object(), registry))
    with client.application.app_context():
        # Patch the symbols imported by app.routes.analysis to keep this route test
        # focused on rendering/counting without launching background enrichment.
        import app.routes.analysis as analysis_routes

        original_setup = analysis_routes._setup_orchestrator
        original_pipeline = analysis_routes.run_pipeline
        analysis_routes._setup_orchestrator = setup_orchestrator
        analysis_routes.run_pipeline = Mock(return_value=[EMAIL_IOC])
        try:
            response = client.post(
                "/analyze",
                data={"text": "Investigate analyst@example.com", "mode": "online"},
            )
        finally:
            analysis_routes._setup_orchestrator = original_setup
            analysis_routes.run_pipeline = original_pipeline

    assert response.status_code == 200
    setup_orchestrator.assert_called_once()
    return response


def test_settings_get_lists_emailrep_metadata(client, tmp_path, monkeypatch):
    """GET /settings includes the EmailRep metadata and missing-key status."""
    store = ConfigStore(config_path=tmp_path / "config.ini")
    monkeypatch.setattr("app.routes.settings.ConfigStore", lambda: store)

    response = client.get("/settings")

    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert 'data-provider="emailrep"' in html
    assert "EmailRep" in html
    assert "Email only, reputation and account-risk signals" in html
    assert "https://emailrep.io/key" in html
    assert "Not configured" in html


def test_settings_post_saves_emailrep_key_without_echoing_raw_secret(
    client, tmp_path, monkeypatch
):
    """POST /settings persists EmailRep through provider-key storage and rebuilds registry."""
    store = ConfigStore(config_path=tmp_path / "config.ini")
    monkeypatch.setattr("app.routes.settings.ConfigStore", lambda: store)

    response = client.post(
        "/settings",
        data={"provider_id": "emailrep", "api_key": EMAILREP_TEST_KEY},
        follow_redirects=True,
    )

    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert store.get_provider_key("emailrep") == EMAILREP_TEST_KEY
    assert EMAILREP_TEST_KEY not in html
    assert "API key saved for emailrep" in html
    assert "Configured" in html
    assert client.application.registry.provider_count_for_type(IOCType.EMAIL) == 1


def test_settings_post_rejects_empty_emailrep_key_without_configuring(
    client, tmp_path, monkeypatch
):
    """Empty EmailRep keys preserve validation and do not configure EmailRep."""
    store = ConfigStore(config_path=tmp_path / "config.ini")
    monkeypatch.setattr("app.routes.settings.ConfigStore", lambda: store)

    response = client.post(
        "/settings",
        data={"provider_id": "emailrep", "api_key": ""},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"API key cannot be empty" in response.data
    assert store.get_provider_key("emailrep") is None


def test_settings_post_rejects_unknown_provider_without_storing_key(
    client, tmp_path, monkeypatch
):
    """Unknown provider ids flash/redirect and do not write arbitrary provider keys."""
    store = ConfigStore(config_path=tmp_path / "config.ini")
    monkeypatch.setattr("app.routes.settings.ConfigStore", lambda: store)

    response = client.post(
        "/settings",
        data={"provider_id": "not-real", "api_key": "arbitrary-secret"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Unknown provider" in response.data
    assert store.all_provider_keys() == {}


def test_online_email_with_emailrep_key_reports_one_email_provider(client, tmp_path):
    """A configured EmailRep key contributes exactly one email provider in Online mode."""
    store = ConfigStore(config_path=tmp_path / "config.ini")
    store.set_provider_key("emailrep", EMAILREP_TEST_KEY)
    registry = build_registry(allowed_hosts=["emailrep.io"], config_store=store)

    response = _post_online_email(client, registry)

    html = response.data.decode("utf-8")
    provider_counts = _provider_counts_from_html(html)
    assert provider_counts["email"] == 1
    assert "0/1 providers complete" in html
    assert EMAILREP_TEST_KEY not in html


def test_online_email_without_emailrep_key_reports_zero_email_providers(client, tmp_path):
    """Missing EmailRep key keeps email coverage at zero while Online mode still renders."""
    store = ConfigStore(config_path=tmp_path / "config.ini")
    store.set_provider_key("abuseipdb", "configured-non-email-key")
    registry = build_registry(allowed_hosts=["api.abuseipdb.com"], config_store=store)

    response = _post_online_email(client, registry)

    html = response.data.decode("utf-8")
    provider_counts = _provider_counts_from_html(html)
    assert provider_counts["email"] == 0
    assert "0/0 providers complete" in html
    assert "EmailRep" not in html
