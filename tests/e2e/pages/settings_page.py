"""Page Object Model for the SentinelX settings page."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect


class SettingsPage:
    """Encapsulates selectors and actions for the multi-provider settings page."""

    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url

        # Top-level locators
        self.title = page.locator("h1.settings-title")
        self.flash_messages = page.locator("[role='alert']")

    def goto(self) -> None:
        """Navigate to the settings page."""
        self.page.goto(self.base_url + "/settings")

    # ---- Provider Sections ----

    @property
    def provider_sections(self) -> Locator:
        """All provider configuration sections."""
        return self.page.locator("section.settings-section")

    def provider_section(self, provider_id: str) -> Locator:
        """Return the section for a specific provider by its hidden input value."""
        return self.page.locator(
            f'section.settings-section:has(input[name="provider_id"][value="{provider_id}"])'
        )

    def provider_title(self, provider_id: str) -> Locator:
        """Return the title heading for a provider section."""
        return self.provider_section(provider_id).locator("h2.settings-section-title")

    def provider_status(self, provider_id: str) -> Locator:
        """Return the status badge (Configured / Not configured) for a provider."""
        return self.provider_section(provider_id).locator(".api-key-status")

    def provider_description(self, provider_id: str) -> Locator:
        """Return the description paragraph for a provider."""
        return self.provider_section(provider_id).locator("p.settings-info").first

    def provider_signup_link(self, provider_id: str) -> Locator:
        """Return the signup link element for a provider."""
        return self.provider_section(provider_id).locator("a[target='_blank']")

    # ---- Form Elements ----

    def api_key_input(self, provider_id: str) -> Locator:
        """Return the API key input field for a provider."""
        return self.page.locator(f"#api-key-{provider_id}")

    def save_button(self, provider_id: str) -> Locator:
        """Return the 'Save API Key' button for a provider."""
        return self.provider_section(provider_id).locator("button[type='submit']")

    def show_hide_button(self, provider_id: str) -> Locator:
        """Return the Show/Hide toggle button for a provider's API key field."""
        return self.provider_section(provider_id).locator("[data-role='toggle-key']")

    def csrf_token(self, provider_id: str) -> Locator:
        """Return the CSRF token hidden input for a provider's form."""
        return self.provider_section(provider_id).locator("input[name='csrf_token']")

    def form(self, provider_id: str) -> Locator:
        """Return the form element for a provider."""
        return self.provider_section(provider_id).locator("form")

    # ---- Actions ----

    def fill_api_key(self, provider_id: str, key: str) -> None:
        """Fill the API key input for a provider."""
        self.api_key_input(provider_id).fill(key)

    def save_api_key(self, provider_id: str, key: str) -> None:
        """Fill and submit the API key form for a provider."""
        self.fill_api_key(provider_id, key)
        self.save_button(provider_id).click()

    def toggle_key_visibility(self, provider_id: str) -> None:
        """Click the Show/Hide button to toggle API key visibility."""
        self.show_hide_button(provider_id).click()

    # ---- Assertions ----

    def expect_provider_count(self, count: int) -> None:
        """Assert the number of provider sections on the page."""
        expect(self.provider_sections).to_have_count(count)

    def expect_status_configured(self, provider_id: str) -> None:
        """Assert a provider shows 'Configured' status."""
        expect(self.provider_status(provider_id)).to_contain_text("Configured")
        expect(self.provider_status(provider_id)).to_have_class(
            "api-key-status api-key-status--configured"
        )

    def expect_status_not_configured(self, provider_id: str) -> None:
        """Assert a provider shows 'Not configured' status."""
        expect(self.provider_status(provider_id)).to_contain_text("Not configured")
        expect(self.provider_status(provider_id)).to_have_class(
            "api-key-status api-key-status--missing"
        )

    def expect_flash_success(self, text: str) -> None:
        """Assert a success flash message is visible with the given text."""
        alert = self.page.locator(".alert-success")
        expect(alert).to_be_visible()
        expect(alert).to_contain_text(text)

    def expect_flash_error(self, text: str) -> None:
        """Assert an error flash message is visible with the given text."""
        alert = self.page.locator(".alert-error")
        expect(alert).to_be_visible()
        expect(alert).to_contain_text(text)

    def expect_key_input_masked(self, provider_id: str) -> None:
        """Assert the API key input is type=password (masked)."""
        expect(self.api_key_input(provider_id)).to_have_attribute("type", "password")

    def expect_key_input_visible(self, provider_id: str) -> None:
        """Assert the API key input is type=text (visible)."""
        expect(self.api_key_input(provider_id)).to_have_attribute("type", "text")
