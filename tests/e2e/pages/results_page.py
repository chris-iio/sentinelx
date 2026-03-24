"""Page Object Model for the SentinelX results page (single-column layout with enrichment surface)."""

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
        self.no_results_box = page.locator(".empty-state")
        self.no_results_hint = page.locator(".empty-state-body")

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

    # ---- Filter Bar ----

    @property
    def filter_bar(self) -> Locator:
        """The sticky filter bar wrapper."""
        return self.page.locator(".filter-bar-wrapper")

    @property
    def filter_verdict_buttons(self) -> Locator:
        """All verdict filter buttons in the filter bar."""
        return self.page.locator(".filter-verdict-buttons .filter-btn")

    def filter_by_verdict(self, verdict: str) -> None:
        """Click the filter button for the given verdict (e.g., 'malicious', 'all')."""
        label = verdict.replace("_", " ").title()
        self.page.locator(".filter-btn").filter(has_text=label).click()

    @property
    def filter_type_pills(self) -> Locator:
        """All IOC type pills in the filter bar."""
        return self.page.locator(".filter-type-pills .filter-pill")

    def filter_by_type(self, ioc_type: str) -> None:
        """Click the type pill for the given IOC type (e.g., 'ipv4')."""
        self.page.locator(".filter-pill").filter(has_text=ioc_type.upper()).click()

    @property
    def search_input(self) -> Locator:
        """The text search input field."""
        return self.page.locator(".filter-search-input")

    def search(self, query: str) -> None:
        """Type a search query into the filter search input.

        Waits 150ms after filling to allow the debounced applyFilter()
        to fire (100ms debounce + margin).
        """
        self.search_input.fill(query)
        self.page.wait_for_timeout(150)

    @property
    def visible_cards(self) -> Locator:
        """IOC cards that are currently visible (not hidden by x-show)."""
        return self.page.locator(".ioc-card:visible")

    @property
    def hidden_cards(self) -> Locator:
        """IOC cards that are currently hidden by x-show."""
        return self.page.locator(".ioc-card:not(:visible)")

    @property
    def provider_coverage(self) -> Locator:
        """The provider coverage row below the verdict dashboard."""
        return self.page.locator(".provider-coverage-row")

    # ---- Enrichment Slots ----

    @property
    def enrichment_slots(self) -> Locator:
        """All enrichment slot containers (server-rendered, one per card)."""
        return self.page.locator(".enrichment-slot")

    @property
    def loaded_enrichment_slots(self) -> Locator:
        """Enrichment slots that have received data and been marked as loaded."""
        return self.page.locator(".enrichment-slot--loaded")

    @property
    def enrichment_details(self) -> Locator:
        """All enrichment detail panels (collapsed by default, toggled by summary row)."""
        return self.page.locator(".enrichment-details")

    # ---- Summary Rows ----

    @property
    def summary_rows(self) -> Locator:
        """All JS-created IOC summary rows (injected by row-factory.ts after enrichment)."""
        return self.page.locator(".ioc-summary-row")

    @property
    def expanded_summary_rows(self) -> Locator:
        """Summary rows currently in the expanded (is-open) state."""
        return self.page.locator(".ioc-summary-row.is-open")

    # ---- Enrichment Element Locators ----

    @property
    def chevron_wrappers(self) -> Locator:
        """All chevron icon wrappers inside summary rows."""
        return self.page.locator(".chevron-icon-wrapper")

    @property
    def micro_bars(self) -> Locator:
        """All verdict micro-bar elements (inline verdict visualisation)."""
        return self.page.locator(".verdict-micro-bar")

    @property
    def staleness_badges(self) -> Locator:
        """All staleness badge elements indicating data age."""
        return self.page.locator(".staleness-badge")

    @property
    def attribution_spans(self) -> Locator:
        """All provider attribution spans inside summary rows."""
        return self.page.locator(".ioc-summary-attribution")

    @property
    def detail_link_footers(self) -> Locator:
        """All detail link footer wrappers injected after enrichment completes."""
        return self.page.locator(".detail-link-footer")

    @property
    def detail_links(self) -> Locator:
        """All 'View full detail →' anchor links injected by enrichment.ts."""
        return self.page.locator(".detail-link")

    @property
    def context_lines(self) -> Locator:
        """All IOC context line elements (server-rendered in _ioc_card.html)."""
        return self.page.locator(".ioc-context-line")

    # ---- Section Containers ----

    @property
    def enrichment_sections(self) -> Locator:
        """All enrichment section containers inside detail panels."""
        return self.page.locator(".enrichment-section")

    @property
    def section_context(self) -> Locator:
        """Infrastructure context enrichment sections."""
        return self.page.locator(".enrichment-section--context")

    @property
    def section_reputation(self) -> Locator:
        """Reputation enrichment sections."""
        return self.page.locator(".enrichment-section--reputation")

    @property
    def section_no_data(self) -> Locator:
        """No-data placeholder sections (shown when a provider returned nothing)."""
        return self.page.locator(".enrichment-section--no-data")

    # ---- Card-Scoped Helpers ----

    def summary_row_for_card(self, ioc_value: str) -> Locator:
        """Return the summary row locator scoped to the card matching *ioc_value*."""
        return self.page.locator(f'.ioc-card[data-ioc-value="{ioc_value}"] .ioc-summary-row')

    def enrichment_details_for_card(self, ioc_value: str) -> Locator:
        """Return the enrichment details panel locator scoped to the card matching *ioc_value*."""
        return self.page.locator(f'.ioc-card[data-ioc-value="{ioc_value}"] .enrichment-details')

    # ---- Expand / Collapse Helpers ----

    def expand_row(self, ioc_value: str) -> None:
        """Click the summary row for *ioc_value* and assert it enters the expanded state.

        Both the ``.ioc-summary-row`` and its sibling ``.enrichment-details`` must
        acquire the ``is-open`` class before the assertion is satisfied.
        """
        summary_row = self.summary_row_for_card(ioc_value)
        details = self.enrichment_details_for_card(ioc_value)
        summary_row.click()
        expect(summary_row).to_have_class(r".*is-open.*")
        expect(details).to_have_class(r".*is-open.*")

    def collapse_row(self, ioc_value: str) -> None:
        """Click the summary row for *ioc_value* again and assert it returns to collapsed state.

        Both the ``.ioc-summary-row`` and its sibling ``.enrichment-details`` must
        lose the ``is-open`` class before the assertion is satisfied.
        """
        summary_row = self.summary_row_for_card(ioc_value)
        details = self.enrichment_details_for_card(ioc_value)
        summary_row.click()
        expect(summary_row).not_to_have_class(r".*is-open.*")
        expect(details).not_to_have_class(r".*is-open.*")

    def is_row_expanded(self, ioc_value: str) -> bool:
        """Return ``True`` if the summary row for *ioc_value* currently has the ``is-open`` class."""
        summary_row = self.summary_row_for_card(ioc_value)
        classes: str = summary_row.evaluate("el => el.className")
        return "is-open" in classes
