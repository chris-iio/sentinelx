"""E2E tests for URL IOC extraction, card rendering, filtering, enrichment, and detail links.

Covers the full URL IOC flow:
  - URL extraction from free-form text
  - Card rendering with correct type badge
  - Filter pill visibility and filtering
  - Enrichment surface with mocked URLhaus/VT response
  - Detail link href correctness (/ioc/url/...)

Uses offline mode for rendering/filter tests, online mode with mocked enrichment
for enrichment surface and detail link tests.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.e2e.pages import IndexPage, ResultsPage

# ---------------------------------------------------------------------------
# Sample text containing a URL IOC alongside other IOC types
# ---------------------------------------------------------------------------

URL_IOC_TEXT = "Visit https://evil.example.com/payload.exe for the malware sample."
URL_IOC_VALUE = "https://evil.example.com/payload.exe"

# Mixed text: URL + IP + domain — ensures URL pill appears among other types
MIXED_WITH_URL = "Check https://evil.example.com/payload.exe and 8.8.8.8 plus evil.com"

# Canned enrichment response for a URL IOC — mimics URLhaus + VT providers
MOCK_ENRICHMENT_RESPONSE_URL = {
    "total": 2,
    "done": 2,
    "complete": True,
    "next_since": 2,
    "results": [
        {
            "type": "result",
            "ioc_value": "https://evil.example.com/payload.exe",
            "ioc_type": "url",
            "provider": "URLhaus",
            "verdict": "malicious",
            "detection_count": 1,
            "total_engines": 1,
            "scan_date": "2026-03-15T12:00:00Z",
            "raw_stats": {"threat": "malware_download"},
        },
        {
            "type": "result",
            "ioc_value": "https://evil.example.com/payload.exe",
            "ioc_type": "url",
            "provider": "VirusTotal",
            "verdict": "malicious",
            "detection_count": 15,
            "total_engines": 70,
            "scan_date": "2026-03-15T12:00:00Z",
            "raw_stats": {},
        },
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _navigate_to_results(page: Page, index_url: str, text: str = URL_IOC_TEXT) -> ResultsPage:
    """Navigate to index, submit text in offline mode, return ResultsPage."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(text, mode="offline")
    return ResultsPage(page)


def _navigate_online_with_url_mock(page: Page, index_url: str, text: str = URL_IOC_TEXT) -> ResultsPage:
    """Navigate in online mode with enrichment polling intercepted by a URL-specific route mock.

    Sets up the route mock BEFORE navigation so the handler is active when
    enrichment.ts fires its first fetch().  Waits for ``.ioc-summary-row`` to
    appear (confirms enrichment.ts processed the mocked response) before
    returning the ResultsPage.
    """
    from tests.e2e.conftest import setup_enrichment_route_mock

    # Register route mock BEFORE navigation — URL-specific canned response
    setup_enrichment_route_mock(page, response_body=MOCK_ENRICHMENT_RESPONSE_URL)

    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(text, mode="online")

    # Wait for enrichment.ts to fire and row-factory.ts to inject the summary row
    page.wait_for_selector(".ioc-summary-row", timeout=10_000)

    return ResultsPage(page)


# ---------------------------------------------------------------------------
# URL IOC card rendering tests
# ---------------------------------------------------------------------------


def test_url_ioc_card_renders(page: Page, index_url: str) -> None:
    """URL in input text is extracted and rendered as an IOC card with data-ioc-type='url'."""
    results = _navigate_to_results(page, index_url, text=URL_IOC_TEXT)

    url_cards = results.cards_for_type("url")
    assert url_cards.count() >= 1, (
        "Expected at least 1 .ioc-card[data-ioc-type='url'], got 0"
    )


def test_url_type_badge_text(page: Page, index_url: str) -> None:
    """URL IOC cards contain a .ioc-type-badge with 'URL' text."""
    _navigate_to_results(page, index_url, text=URL_IOC_TEXT)

    badge = page.locator(".ioc-type-badge--url")
    expect(badge.first).to_be_visible()
    badge_text = badge.first.text_content() or ""
    assert "URL" in badge_text.upper(), (
        f"Expected badge text to contain 'URL', got: {badge_text!r}"
    )


# ---------------------------------------------------------------------------
# URL filter pill tests
# ---------------------------------------------------------------------------


def test_url_filter_pill_exists(page: Page, index_url: str) -> None:
    """URL filter pill is present in the filter bar when URL IOCs are in results."""
    _navigate_to_results(page, index_url, text=URL_IOC_TEXT)

    pill = page.locator(".filter-pill--url")
    expect(pill).to_be_visible()
    expect(pill).to_contain_text("URL")


def test_url_filter_pill_shows_only_url_cards(page: Page, index_url: str) -> None:
    """Clicking URL pill hides all non-URL cards."""
    results = _navigate_to_results(page, index_url, text=MIXED_WITH_URL)

    results.filter_by_type("url")

    visible = results.visible_cards
    count = visible.count()
    assert count >= 1, "Expected at least 1 visible card after URL filter"
    for i in range(count):
        card_type = visible.nth(i).get_attribute("data-ioc-type")
        assert card_type == "url", (
            f"Expected all visible cards to be url type, got: {card_type!r}"
        )


def test_url_filter_pill_active_state(page: Page, index_url: str) -> None:
    """URL filter pill shows active state when clicked."""
    _navigate_to_results(page, index_url, text=URL_IOC_TEXT)

    page.locator(".filter-type-pills .filter-pill--url").click()

    active_pill = page.locator(".filter-pill--url.filter-pill--active")
    expect(active_pill).to_be_visible()


def test_all_types_pill_resets_after_url_filter(page: Page, index_url: str) -> None:
    """Clicking 'All Types' after URL filter restores the full card count."""
    results = _navigate_to_results(page, index_url, text=MIXED_WITH_URL)

    total_before = results.visible_cards.count()
    results.filter_by_type("url")
    url_count = results.visible_cards.count()
    assert url_count < total_before, (
        "Expected fewer cards after URL filter than before"
    )

    results.filter_by_type("all")
    expect(results.visible_cards).to_have_count(total_before)


# ---------------------------------------------------------------------------
# URL enrichment surface tests — online mode with mocked URLhaus/VT response
# ---------------------------------------------------------------------------


def test_url_enrichment_summary_row_created(page: Page, index_url: str) -> None:
    """Mocked enrichment polling causes .ioc-summary-row to appear for URL IOC."""
    results = _navigate_online_with_url_mock(page, index_url)

    expect(results.summary_rows).not_to_have_count(0)

    # The summary row must be inside a url-type card
    url_card = page.locator('.ioc-card[data-ioc-type="url"]')
    row_inside_url_card = url_card.locator(".ioc-summary-row")
    assert row_inside_url_card.count() >= 1, (
        ".ioc-summary-row not found inside a url IOC card"
    )


def test_url_detail_link_href_correct(page: Page, index_url: str) -> None:
    """Detail link for URL IOC points to /ioc/url/<url_value> after enrichment completes."""
    _navigate_online_with_url_mock(page, index_url)

    # Wait for enrichment complete → detail link injection
    page.wait_for_selector(".detail-link-footer", timeout=10_000)

    detail_link = page.locator(".detail-link").first
    expect(detail_link).to_be_visible()

    href = detail_link.get_attribute("href") or ""
    assert "/ioc/url/" in href, (
        f"Expected detail link href to contain '/ioc/url/', got: '{href}'"
    )
    # Verify the URL IOC value is encoded in the href
    assert "evil.example.com" in href, (
        f"Expected detail link href to contain 'evil.example.com', got: '{href}'"
    )
