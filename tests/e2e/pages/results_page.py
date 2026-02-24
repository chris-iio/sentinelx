"""Page Object Model for the SentinelX results page (card layout)."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect


class ResultsPage:
    """Encapsulates selectors and actions for the results page."""

    def __init__(self, page: Page) -> None:
        self.page = page

        # Top-level locators
        self.mode_indicator = page.locator(".mode-indicator")
        self.ioc_count = page.locator(".results-summary .ioc-count")
        self.back_link = page.locator("a.back-link")
        self.no_results_box = page.locator(".no-results")
        self.no_results_hint = page.locator(".no-results-hint")

    # ---- IOC Cards ----

    @property
    def ioc_cards(self) -> Locator:
        """All IOC cards on the page."""
        return self.page.locator(".ioc-card")

    def cards_for_type(self, ioc_type: str) -> Locator:
        """Return cards for a specific IOC type (lowercase)."""
        return self.page.locator(f'.ioc-card[data-ioc-type="{ioc_type}"]')

    def type_badge(self, ioc_type: str) -> Locator:
        """Return type badge elements for a specific IOC type."""
        return self.cards_for_type(ioc_type).locator(".ioc-type-badge")

    def ioc_values(self, ioc_type: str) -> Locator:
        """Return all normalized value elements for a given IOC type."""
        return self.cards_for_type(ioc_type).locator(".ioc-value")

    def ioc_originals(self, ioc_type: str) -> Locator:
        """Return all original value elements for a given IOC type."""
        return self.cards_for_type(ioc_type).locator(".ioc-original")

    def copy_buttons(self, ioc_type: str) -> Locator:
        """Return all copy buttons for a given IOC type."""
        return self.cards_for_type(ioc_type).locator(".copy-btn")

    def verdict_labels(self, ioc_type: str) -> Locator:
        """Return all verdict label elements for a given IOC type."""
        return self.cards_for_type(ioc_type).locator(".verdict-label")

    # ---- Verdict Dashboard ----

    @property
    def verdict_dashboard(self) -> Locator:
        """The verdict dashboard element."""
        return self.page.locator("#verdict-dashboard")

    def verdict_count(self, verdict: str) -> Locator:
        """Return the count element for a specific verdict in the dashboard."""
        return self.page.locator(f'[data-verdict-count="{verdict}"]')

    # ---- Assertions ----

    def expect_mode(self, mode: str) -> None:
        """Assert the mode indicator shows the expected mode text."""
        if mode == "offline":
            expect(self.mode_indicator).to_contain_text("Offline Mode")
        else:
            expect(self.mode_indicator).to_contain_text("Online Mode")

    def expect_total_count(self, count: int) -> None:
        """Assert the total IOC count shown in the summary."""
        if count == 0:
            expect(self.ioc_count).to_contain_text("No IOCs found")
        else:
            expect(self.ioc_count).to_contain_text(f"Found {count} unique IOC")

    def expect_no_results(self) -> None:
        """Assert the 'no results' state is displayed."""
        expect(self.no_results_box).to_be_visible()
        expect(self.no_results_hint).to_contain_text("Supported types")

    def expect_cards_for_type(self, ioc_type: str, count: int) -> None:
        """Assert the number of cards for a specific IOC type."""
        expect(self.cards_for_type(ioc_type)).to_have_count(count)

    def go_back(self) -> None:
        """Click the 'Back to input' link."""
        self.back_link.click()
