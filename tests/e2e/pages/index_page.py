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
        self.mode_select = page.locator("#mode-select")
        self.error_alert = page.locator(".alert-error")
        self.site_logo = page.locator(".site-logo")
        self.site_tagline = page.locator(".site-tagline")

    def goto(self) -> None:
        """Navigate to the index page."""
        self.page.goto(self.base_url + "/")

    def fill_text(self, text: str) -> None:
        """Fill the IOC textarea with the given text."""
        self.textarea.fill(text)

    def select_mode(self, mode: str) -> None:
        """Select analysis mode: 'offline' or 'online'."""
        self.mode_select.select_option(mode)

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
