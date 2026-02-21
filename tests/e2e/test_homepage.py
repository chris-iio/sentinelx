"""E2E tests for the SentinelX homepage (index page).

Covers: page rendering, form elements, header/footer, title.
"""

from playwright.sync_api import Page, expect

from tests.e2e.pages import IndexPage


def test_page_title(page: Page, index_url: str) -> None:
    """Page title includes 'SentinelX'."""
    page.goto(index_url)
    expect(page).to_have_title("SentinelX — IOC Extractor")


def test_header_branding(page: Page, index_url: str) -> None:
    """Header shows logo and tagline."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    expect(idx.site_logo).to_have_text("SentinelX")
    expect(idx.site_tagline).to_have_text("Offline IOC Extractor")


def test_form_elements_present(page: Page, index_url: str) -> None:
    """All form elements render on page load."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    expect(idx.title).to_have_text("Extract IOCs")
    expect(idx.subtitle).to_contain_text("Paste a threat report")
    expect(idx.textarea).to_be_visible()
    expect(idx.submit_btn).to_be_visible()
    expect(idx.clear_btn).to_be_visible()
    expect(idx.mode_select).to_be_visible()


def test_textarea_placeholder(page: Page, index_url: str) -> None:
    """Textarea has helpful placeholder text with examples."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    placeholder = idx.textarea.get_attribute("placeholder")
    assert placeholder is not None
    assert "192[.]168[.]1[.]1" in placeholder
    assert "hxxp://" in placeholder
    assert "CVE-" in placeholder


def test_mode_select_options(page: Page, index_url: str) -> None:
    """Mode select offers offline and online options."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    options = idx.mode_select.locator("option")
    expect(options).to_have_count(2)
    expect(options.nth(0)).to_have_text("Offline (no network calls)")
    expect(options.nth(1)).to_have_text("Online (enrichment via APIs)")


def test_offline_mode_selected_by_default(page: Page, index_url: str) -> None:
    """Offline mode is selected by default."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    expect(idx.mode_select).to_have_value("offline")


def test_security_headers(page: Page, index_url: str) -> None:
    """Response includes required security headers."""
    response = page.goto(index_url)
    assert response is not None

    headers = response.headers
    assert "content-security-policy" in headers
    assert "'self'" in headers["content-security-policy"]
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "SAMEORIGIN"


def test_csrf_token_present(page: Page, index_url: str) -> None:
    """Form includes a hidden CSRF token field."""
    page.goto(index_url)
    csrf_input = page.locator("input[name='csrf_token']")
    expect(csrf_input).to_be_attached()

    token = csrf_input.get_attribute("value")
    assert token is not None
    assert len(token) > 10  # Non-trivial token
