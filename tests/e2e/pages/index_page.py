"""Page Object Model for the SentinelX index (paste form) page."""

from playwright.sync_api import Page, expect


class IndexPage:
    """Encapsulates selectors and actions for the IOC paste form."""

    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url

        # Locators
        self.title = page.locator("h1.input-title")
        self.subtitle = page.locator("p.input-subtitle")
        self.textarea = page.locator("#ioc-text")
        self.submit_btn = page.locator("#submit-btn")
        self.clear_btn = page.locator("#clear-btn")
        self.mode_toggle_widget = page.locator("#mode-toggle-widget")
        self.mode_toggle_btn = page.locator("#mode-toggle-btn")
        self.mode_input = page.locator("#mode-input")
        self.paste_feedback = page.locator("#paste-feedback")
        self.error_alert = page.locator(".alert-error")
        self.site_logo = page.locator(".site-logo")
        self.site_tagline = page.locator(".site-tagline")

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
        """Assert the hidden mode input has the expected value."""
        expect(self.mode_input).to_have_value(mode)

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

    def expect_submit_disabled(self) -> None:
        """Assert the submit button is disabled."""
        expect(self.submit_btn).to_be_disabled()

    def expect_submit_enabled(self) -> None:
        """Assert the submit button is enabled."""
        expect(self.submit_btn).to_be_enabled()
