"""E2E tests for the SentinelX homepage (index page).

Covers: page rendering, form elements, header/footer, title.
"""

from playwright.sync_api import Page, expect

from tests.e2e.pages import IndexPage


def test_page_title(page: Page, index_url: str) -> None:
    """Page title includes 'SentinelX'."""
    page.goto(index_url)
    expect(page).to_have_title("SentinelX")


def test_header_branding(page: Page, index_url: str) -> None:
    """Page shows hero brand and floating settings icon — no tagline."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    expect(idx.hero_brand).to_be_visible()
    expect(idx.site_settings_link).to_be_visible()
    expect(page.locator(".site-tagline")).to_have_count(0)


def test_header_no_tagline(page: Page, index_url: str) -> None:
    """Header contains no tagline or descriptive text — only logo, brand, settings icon."""
    page.goto(index_url)
    # .site-tagline element must not exist
    expect(page.locator(".site-tagline")).to_have_count(0)
    # Settings link must be icon-only (aria-label present, no visible text label)
    settings_link = page.locator("nav a[aria-label='Settings']")
    expect(settings_link).to_be_visible()


def test_textarea_default_rows(page: Page, index_url: str) -> None:
    """Textarea defaults to approximately 5 visible rows on first load."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    # rows attribute should be 5
    rows_attr = idx.textarea.get_attribute("rows")
    assert rows_attr == "5", f"Expected rows=5, got rows={rows_attr}"


def test_textarea_auto_grow(page: Page, index_url: str) -> None:
    """Textarea grows taller as content is typed, up to max height."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    # Record initial height
    initial_box = idx.textarea.bounding_box()
    assert initial_box is not None
    initial_height = initial_box["height"]

    # Type enough content to cause multiple lines
    many_lines = "\n".join([f"192.168.1.{i}" for i in range(20)])
    idx.textarea.fill(many_lines)
    # Trigger input event so auto-grow JS fires
    idx.textarea.dispatch_event("input")

    grown_box = idx.textarea.bounding_box()
    assert grown_box is not None
    grown_height = grown_box["height"]

    assert grown_height > initial_height, (
        f"Textarea did not grow: initial={initial_height}px, after fill={grown_height}px"
    )


def test_form_elements_present(page: Page, index_url: str) -> None:
    """All form elements render on page load."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    expect(idx.hero_brand).to_be_visible()
    expect(idx.textarea).to_be_visible()
    expect(idx.submit_btn).to_be_visible()
    expect(idx.clear_btn).to_be_visible()
    expect(idx.mode_toggle_widget).to_be_visible()


def test_textarea_placeholder(page: Page, index_url: str) -> None:
    """Textarea starts with empty placeholder in freetext mode."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    placeholder = idx.textarea.get_attribute("placeholder")
    assert placeholder == ""


def test_mode_toggle_labels(page: Page, index_url: str) -> None:
    """Mode toggle shows Offline and Online labels."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    offline_label = idx.mode_toggle_widget.locator(".mode-toggle-label--offline")
    online_label = idx.mode_toggle_widget.locator(".mode-toggle-label--online")
    expect(offline_label).to_have_text("Offline")
    expect(online_label).to_have_text("Online")


def test_offline_mode_by_default(page: Page, index_url: str) -> None:
    """Offline mode is active by default."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.expect_mode("offline")
    expect(idx.mode_toggle_btn).to_have_attribute("aria-pressed", "false")


def test_security_headers(page: Page, index_url: str) -> None:
    """Response includes required security headers."""
    from tests.e2e.conftest import assert_security_headers

    response = page.goto(index_url)
    assert response is not None

    assert_security_headers(response.headers)
    assert "'self'" in response.headers["content-security-policy"]


def test_csrf_token_present(page: Page, index_url: str) -> None:
    """Form includes a hidden CSRF token field."""
    page.goto(index_url)
    csrf_input = page.locator("input[name='csrf_token']")
    expect(csrf_input).to_be_attached()

    token = csrf_input.get_attribute("value")
    assert token is not None
    assert len(token) > 10  # Non-trivial token
