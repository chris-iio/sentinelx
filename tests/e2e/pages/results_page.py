"""Page Object Model for the SentinelX results page."""

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

    # ---- IOC Groups ----

    @property
    def ioc_groups(self) -> Locator:
        """All accordion IOC groups on the page."""
        return self.page.locator("details.ioc-group")

    def group_for_type(self, ioc_type: str) -> Locator:
        """Return the <details> accordion for a specific IOC type (lowercase)."""
        return self.page.locator(f"details.ioc-group--{ioc_type}")

    def type_label(self, ioc_type: str) -> Locator:
        """Return the type label element inside a group."""
        return self.group_for_type(ioc_type).locator(".ioc-type-label")

    def count_badge(self, ioc_type: str) -> Locator:
        """Return the count badge element inside a group."""
        return self.group_for_type(ioc_type).locator(".ioc-count-badge")

    def ioc_values(self, ioc_type: str) -> Locator:
        """Return all normalized value elements for a given IOC type."""
        return self.group_for_type(ioc_type).locator(".ioc-value")

    def ioc_originals(self, ioc_type: str) -> Locator:
        """Return all original value elements for a given IOC type."""
        return self.group_for_type(ioc_type).locator(".ioc-original")

    def copy_buttons(self, ioc_type: str) -> Locator:
        """Return all copy buttons for a given IOC type."""
        return self.group_for_type(ioc_type).locator(".copy-btn")

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

    def expect_group_visible(self, ioc_type: str) -> None:
        """Assert a specific IOC type group is visible."""
        expect(self.group_for_type(ioc_type)).to_be_visible()

    def expect_group_count(self, ioc_type: str, count: int) -> None:
        """Assert the count badge for a type shows the expected number."""
        expect(self.count_badge(ioc_type)).to_have_text(str(count))

    def go_back(self) -> None:
        """Click the 'Back to input' link."""
        self.back_link.click()
