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
    """User can switch to online mode via toggle."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.toggle_mode()
    idx.expect_mode("online")
    expect(idx.mode_toggle_btn).to_have_attribute("aria-pressed", "true")


def test_mode_toggle_back_to_offline(page: Page, index_url: str) -> None:
    """User can switch back to offline mode after toggling to online."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.toggle_mode()
    idx.expect_mode("online")

    idx.toggle_mode()
    idx.expect_mode("offline")
    expect(idx.mode_toggle_btn).to_have_attribute("aria-pressed", "false")


def test_submit_label_changes_on_mode_toggle(page: Page, index_url: str) -> None:
    """Submit button label changes between 'Extract IOCs' and 'Extract & Enrich' on toggle."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    expect(idx.submit_btn).to_have_text("Extract IOCs")

    idx.toggle_mode()
    expect(idx.submit_btn).to_have_text("Extract & Enrich")

    idx.toggle_mode()
    expect(idx.submit_btn).to_have_text("Extract IOCs")


def test_paste_shows_character_count_feedback(page: Page, index_url: str) -> None:
    """Pasting text shows 'N characters pasted' feedback near textarea."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    # Simulate paste by setting textarea value then dispatching paste event
    test_text = "192.168.1.1\n10.0.0.1\nhxxps://evil[.]com"
    idx.textarea.focus()
    # Use evaluate to simulate paste event with clipboard data
    page.evaluate("""(text) => {
        const textarea = document.getElementById('ioc-text');
        textarea.value = text;
        textarea.dispatchEvent(new Event('paste', { bubbles: true }));
    }""", test_text)

    # Wait for the feedback to appear (setTimeout 0 + render)
    expect(idx.paste_feedback).to_be_visible(timeout=2000)
    expect(idx.paste_feedback).to_contain_text("characters pasted")
