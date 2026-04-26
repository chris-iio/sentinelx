"""Page Object Model for the SentinelX index (paste form) page."""

from playwright.sync_api import Page, expect


class IndexPage:
    """Encapsulates selectors and actions for the IOC paste form."""

    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url

        # Command-card shell locators
        self.page_index = page.locator(".page-index")
        self.workbench = page.locator(".intake-workbench")
        self.command_card = page.locator(".command-card")
        self.card_header = page.locator(".command-card-header")
        self.hero_brand = page.locator(".index-hero-brand")
        self.eyebrow = page.locator(".command-card-eyebrow")
        self.title = page.locator(".command-card-title")
        self.subtitle = page.locator(".command-card-help")
        self.form = page.locator("#analyze-form")

        # Stable form-control locators consumed by downstream tests
        self.textarea = page.locator("#ioc-text")
        self.submit_btn = page.locator("#submit-btn")
        self.clear_btn = page.locator("#clear-btn")
        self.mode_title = page.locator("#mode-title")
        self.mode_help = page.locator("#mode-help")
        self.mode_status = page.locator("#mode-status")
        self.mode_toggle_widget = page.locator("#mode-toggle-widget")
        self.mode_toggle_btn = page.locator("#mode-toggle-btn")
        self.mode_input = page.locator("#mode-input")
        self.mode_offline_label = self.mode_toggle_widget.locator(".mode-toggle-label--offline")
        self.mode_online_label = self.mode_toggle_widget.locator(".mode-toggle-label--online")
        self.paste_feedback = page.locator("#paste-feedback")
        self.error_alert = page.locator(".alert-error")
        self.site_settings_link = page.locator("nav.floating-settings a[aria-label='Settings']")

    def goto(self) -> None:
        """Navigate to the index page."""
        self.page.goto(self.base_url + "/")

    def fill_text(self, text: str) -> None:
        """Fill the IOC textarea with the given text."""
        self.textarea.fill(text)

    def toggle_mode(self) -> None:
        """Click the mode toggle button to switch between offline/online."""
        self.mode_toggle_btn.click()

    def get_mode(self) -> str:
        """Return the current mode value from the hidden input."""
        return self.mode_input.input_value()

    def expect_mode(self, mode: str) -> None:
        """Assert all synchronized mode surfaces have the expected state."""
        expect(self.mode_input).to_have_value(mode)
        expect(self.mode_toggle_widget).to_have_attribute("data-mode", mode)
        expect(self.mode_toggle_btn).to_have_attribute("aria-pressed", "true" if mode == "online" else "false")
        if mode == "online":
            expect(self.mode_status).to_have_text("Online selected — configured providers may enrich submitted indicators.")
        else:
            expect(self.mode_status).to_have_text(
                "Offline selected — local extraction only; no provider enrichment requests are sent."
            )

    def select_mode(self, mode: str) -> None:
        """Set mode to the given value by toggling if needed."""
        current = self.mode_input.input_value()
        if current != mode:
            self.toggle_mode()

    def submit(self) -> None:
        """Click the submit button."""
        self.submit_btn.click()

    def clear(self) -> None:
        """Click the clear button."""
        self.clear_btn.click()

    def extract_iocs(self, text: str, mode: str = "offline") -> None:
        """Fill text, select mode, and submit the form."""
        self.fill_text(text)
        self.select_mode(mode)
        self.submit()

    def expect_command_surface_visible(self) -> None:
        """Assert the command-card intake shell and stable controls are visible."""
        expect(self.page_index).to_be_visible()
        expect(self.workbench).to_be_visible()
        expect(self.command_card).to_be_visible()
        expect(self.card_header).to_be_visible()
        expect(self.title).to_be_visible()
        expect(self.subtitle).to_be_visible()
        expect(self.form).to_be_visible()
        expect(self.textarea).to_be_visible()
        expect(self.mode_title).to_be_visible()
        expect(self.mode_help).to_be_visible()
        expect(self.mode_status).to_be_visible()
        expect(self.mode_toggle_widget).to_be_visible()
        expect(self.clear_btn).to_be_visible()
        expect(self.submit_btn).to_be_visible()

    def expect_submit_disabled(self) -> None:
        """Assert the submit button is disabled."""
        expect(self.submit_btn).to_be_disabled()

    def expect_submit_enabled(self) -> None:
        """Assert the submit button is enabled."""
        expect(self.submit_btn).to_be_enabled()
