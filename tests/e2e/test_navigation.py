"""E2E tests for page navigation.

Covers: back link, form re-submission, results-to-index round-trip.
"""

from playwright.sync_api import Page, expect

from tests.e2e.pages import IndexPage, ResultsPage


def test_back_link_returns_to_index(page: Page, index_url: str) -> None:
    """Back link on results page navigates to the index."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs("10.0.0.1")

    results = ResultsPage(page)
    expect(results.back_link).to_be_visible()
    expect(results.back_link).to_contain_text("Back to input")

    results.go_back()

    # Should be back on the index page
    expect(page).to_have_url(index_url.rstrip("/") + "/")
    expect(idx.title).to_have_text("Extract IOCs")


def test_round_trip_extract_back_extract(page: Page, index_url: str) -> None:
    """User can extract, go back, and extract again."""
    base = index_url.rstrip("/")
    idx = IndexPage(page, base)

    # First extraction
    idx.goto()
    idx.extract_iocs("10.0.0.1")
    results = ResultsPage(page)
    results.expect_total_count(1)

    # Go back
    results.go_back()

    # Second extraction with different IOCs
    idx.fill_text("192.168.1.1 and 172.16.0.1")
    idx.submit()

    results2 = ResultsPage(page)
    results2.expect_total_count(2)


def test_results_page_has_back_link_on_no_results(page: Page, index_url: str) -> None:
    """Back link is available even when no IOCs are found."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs("just plain text, no IOCs here")

    results = ResultsPage(page)
    results.expect_no_results()
    expect(results.back_link).to_be_visible()

    results.go_back()
    expect(idx.title).to_have_text("Extract IOCs")
