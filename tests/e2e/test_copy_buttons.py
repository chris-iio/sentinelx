"""E2E tests for the copy-to-clipboard functionality.

Note: Clipboard API requires granting permissions in Playwright's browser context.
These tests verify the button behavior and feedback mechanism.
"""

from playwright.sync_api import BrowserContext, Page, expect

from tests.e2e.pages import IndexPage, ResultsPage


def test_copy_buttons_present_for_each_ioc(page: Page, index_url: str) -> None:
    """Every IOC row has a copy button."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs("10.0.0.1 and 172.16.0.1")

    results = ResultsPage(page)
    copy_btns = results.copy_buttons("ipv4")
    expect(copy_btns).to_have_count(2)


def test_copy_button_has_data_value(page: Page, index_url: str) -> None:
    """Copy buttons carry the IOC value in data-value attribute."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs("10.0.0.1")

    results = ResultsPage(page)
    btn = results.copy_buttons("ipv4").first
    data_value = btn.get_attribute("data-value")
    assert data_value == "10.0.0.1"


def test_copy_button_shows_feedback(
    browser: BrowserContext, live_server: str
) -> None:
    """Clicking copy shows 'Copied!' feedback text.

    We use a fresh context with clipboard permissions to test the full flow.
    """
    context = browser.new_context(
        permissions=["clipboard-read", "clipboard-write"],
        viewport={"width": 1280, "height": 720},
    )
    page = context.new_page()

    idx = IndexPage(page, live_server)
    idx.goto()
    idx.extract_iocs("10.0.0.1")

    results = ResultsPage(page)
    btn = results.copy_buttons("ipv4").first

    # Click copy
    btn.click()

    # Button text should change to "Copied!"
    expect(btn).to_have_text("Copied!")

    # After timeout (1.5s), reverts to "Copy"
    page.wait_for_timeout(2000)
    expect(btn).to_have_text("Copy")

    context.close()


def test_copy_button_has_aria_label(page: Page, index_url: str) -> None:
    """Copy buttons have accessible aria-label attributes."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs("10.0.0.1")

    results = ResultsPage(page)
    btn = results.copy_buttons("ipv4").first
    aria = btn.get_attribute("aria-label")
    assert aria is not None
    assert "10.0.0.1" in aria
