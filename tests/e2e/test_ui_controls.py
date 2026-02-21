"""E2E tests for SentinelX UI controls.

Covers: submit button enable/disable, clear button, mode toggle.
"""

from playwright.sync_api import Page, expect

from tests.e2e.pages import IndexPage


def test_submit_disabled_on_empty_textarea(page: Page, index_url: str) -> None:
    """Submit button is disabled when textarea is empty."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.expect_submit_disabled()


def test_submit_enabled_when_text_entered(page: Page, index_url: str) -> None:
    """Submit button enables when text is typed into textarea."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.expect_submit_disabled()
    idx.fill_text("192.168.1.1")
    idx.expect_submit_enabled()


def test_submit_disables_when_text_cleared_manually(page: Page, index_url: str) -> None:
    """Submit button disables when textarea is emptied by user."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.fill_text("some text")
    idx.expect_submit_enabled()

    idx.textarea.fill("")
    idx.expect_submit_disabled()


def test_clear_button_empties_textarea(page: Page, index_url: str) -> None:
    """Clear button empties the textarea."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.fill_text("192.168.1.1")
    expect(idx.textarea).not_to_be_empty()

    idx.clear()
    expect(idx.textarea).to_have_value("")


def test_clear_button_disables_submit(page: Page, index_url: str) -> None:
    """Clear button causes submit to become disabled."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.fill_text("some IOC text")
    idx.expect_submit_enabled()

    idx.clear()
    idx.expect_submit_disabled()


def test_clear_button_focuses_textarea(page: Page, index_url: str) -> None:
    """After clearing, textarea receives focus for quick re-entry."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.fill_text("test")
    idx.clear()

    # Verify textarea is focused
    focused_id = page.evaluate("document.activeElement.id")
    assert focused_id == "ioc-text"


def test_mode_toggle_to_online(page: Page, index_url: str) -> None:
    """User can switch to online mode."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.select_mode("online")
    expect(idx.mode_select).to_have_value("online")


def test_mode_toggle_back_to_offline(page: Page, index_url: str) -> None:
    """User can switch back to offline mode after selecting online."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.select_mode("online")
    expect(idx.mode_select).to_have_value("online")

    idx.select_mode("offline")
    expect(idx.mode_select).to_have_value("offline")
