"""E2E proof for mocked Online EmailRep enrichment rendering.

Exercises the real settings form, CSRF-protected Online analyze form, mocked
status polling, shared result application, and EmailRep provider-context DOM
safety without making any live EmailRep requests.
"""

from __future__ import annotations

import configparser
import json

import app.enrichment.config_store as _config_store_mod
from playwright.sync_api import Page, expect

from tests.e2e.conftest import EMAILREP_E2E_EMAIL, setup_emailrep_enrichment_route_mock
from tests.e2e.pages import IndexPage, ResultsPage, SettingsPage


FAKE_EMAILREP_KEY = "emailrep-e2e-fake-key-1234567890"


def _remove_emailrep_key_from_isolated_config() -> None:
    """Undo the settings save so session-scoped E2E config stays test-isolated."""
    cfg = configparser.ConfigParser()
    cfg.read(_config_store_mod.CONFIG_PATH)
    if cfg.has_section("providers") and cfg.remove_option("providers", "emailrep"):
        with _config_store_mod.CONFIG_PATH.open("w") as fh:
            cfg.write(fh)


def test_online_email_ioc_renders_mocked_emailrep_context(page: Page, live_server: str) -> None:
    """Online email submission renders EmailRep verdict/context safely via route mock."""
    try:
        settings = SettingsPage(page, live_server)
        settings.goto()
        settings.save_api_key("emailrep", FAKE_EMAILREP_KEY)
        settings.expect_flash_success("API key saved for emailrep")
        settings.expect_status_configured("emailrep")

        settings.goto()
        settings.expect_status_configured("emailrep")
        assert FAKE_EMAILREP_KEY not in (page.locator("body").text_content() or "")

        fake_job_id = setup_emailrep_enrichment_route_mock(page, email=EMAILREP_E2E_EMAIL)

        index = IndexPage(page, live_server)
        index.goto()
        index.extract_iocs(EMAILREP_E2E_EMAIL, mode="online")

        results_root = page.locator(".page-results")
        expect(results_root).to_be_visible()
        expect(results_root).to_have_attribute("data-results-owner", "live")
        expect(results_root).to_have_attribute("data-job-id", fake_job_id)

        provider_counts_raw = results_root.get_attribute("data-provider-counts")
        assert provider_counts_raw is not None, "results page did not expose provider-count JSON"
        provider_counts = json.loads(provider_counts_raw)
        assert provider_counts.get("email") == 1

        results = ResultsPage(page)
        email_card = page.locator(
            f'.ioc-card[data-ioc-type="email"][data-ioc-value="{EMAILREP_E2E_EMAIL}"]'
        )
        expect(email_card).to_be_visible()

        summary_row = results.summary_row_for_card(EMAILREP_E2E_EMAIL)
        expect(summary_row).to_be_visible()
        expect(summary_row).to_contain_text("SUSPICIOUS")
        expect(summary_row).to_contain_text("EmailRep: Suspicious")
        expect(email_card.locator(".verdict-label")).to_contain_text("SUSPICIOUS")
        expect(email_card).to_have_attribute("data-verdict", "suspicious")

        summary_row.click()
        expect(summary_row).to_have_attribute("aria-expanded", "true")
        expect(results.enrichment_details_for_card(EMAILREP_E2E_EMAIL)).to_have_class(
            "enrichment-details is-open"
        )

        reputation_rows = email_card.locator(".enrichment-section--reputation .provider-detail-row")
        expect(reputation_rows).to_have_count(1)
        emailrep_row = reputation_rows.first
        expect(emailrep_row.locator(".provider-detail-name")).to_have_text("EmailRep")
        expect(emailrep_row).to_have_attribute("data-verdict", "suspicious")
        expect(email_card.locator(".enrichment-section--context .provider-detail-row")).to_have_count(0)
        expect(email_card.locator(".enrichment-section--no-data .provider-detail-row")).to_have_count(0)

        context_fields = emailrep_row.locator(".provider-context-field")
        rendered_fields = [
            context_fields.nth(i).text_content() or "" for i in range(context_fields.count())
        ]
        assert "Reputation: medium <script>alert('emailrep')</script>" in rendered_fields
        assert "Refs: 7" in rendered_fields
        assert "Risks: suspiciouscredentials_leak<script>alert('risk')</script>" in rendered_fields
        assert "Domain: low" in rendered_fields
        assert "Profiles: githubgravatar" in rendered_fields
        assert "Deliverable: true" in rendered_fields
        assert "MX: true" in rendered_fields
        assert "Spoofable: false" in rendered_fields
        assert "SPF: true" in rendered_fields
        assert "DMARC: false" in rendered_fields

        rendered_text = email_card.text_content() or ""
        assert "<script>alert('emailrep')</script>" in rendered_text
        assert "<script>alert('risk')</script>" in rendered_text
        expect(email_card.locator("script")).to_have_count(0)
        expect(emailrep_row.locator("script")).to_have_count(0)
        assert "unsupported_nested_object" not in rendered_text
        assert "should_not_render" not in rendered_text
        assert "<img src=x onerror=alert('nested')>" not in rendered_text
        assert "[object Object]" not in rendered_text
        assert '{"' not in rendered_text
        assert FAKE_EMAILREP_KEY not in rendered_text
    finally:
        _remove_emailrep_key_from_isolated_config()
