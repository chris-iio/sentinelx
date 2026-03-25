"""E2E tests for the results page filter bar interactions.

Covers all 4 FILTER requirements:
  FILTER-01 — verdict filter buttons
  FILTER-02 — IOC type pills
  FILTER-03 — text search input
  FILTER-04 — sticky positioning

Uses offline mode so no API key is required.  All cards default to
data-verdict="no_data" in offline mode — this is expected and the tests
account for it.

Dashboard badge click-to-filter (verdict toggle shortcut) requires online
mode and a VT API key, so those tests are skipped by default.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.e2e.pages import IndexPage, ResultsPage


# ---------------------------------------------------------------------------
# Sample text: 2 IPs + 2 domains + 1 MD5 = 5 IOCs, 3 types
# ---------------------------------------------------------------------------

MULTI_TYPE_IOCS = "8.8.8.8 1.1.1.1 evil.com test.org abc123def456abc123def456abc123de"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _navigate_to_results(page: Page, index_url: str, text: str = MULTI_TYPE_IOCS) -> ResultsPage:
    """Navigate to index, submit text in offline mode, return ResultsPage."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(text, mode="offline")
    return ResultsPage(page)


# ---------------------------------------------------------------------------
# FILTER-01 / FILTER-02 / FILTER-03 — filter bar renders correctly
# ---------------------------------------------------------------------------


def test_filter_bar_renders(page: Page, index_url: str) -> None:
    """Filter bar is visible and contains all required elements (FILTER-01, FILTER-02, FILTER-03)."""
    results = _navigate_to_results(page, index_url)

    # Filter bar wrapper is present
    expect(results.filter_bar).to_be_visible()

    # 6 verdict buttons: All | Malicious | Suspicious | Clean | Known Good | No Data
    expect(results.filter_verdict_buttons).to_have_count(6)

    # "All Types" pill plus one pill per type present (ipv4, domain, md5)
    expect(results.filter_type_pills).to_have_count(4)  # All Types + 3 types

    # Search input is visible
    expect(results.search_input).to_be_visible()


def test_filter_bar_type_pills_match_result_types(page: Page, index_url: str) -> None:
    """Type pills are rendered only for IOC types present in results (FILTER-02)."""
    results = _navigate_to_results(page, index_url)

    pills = results.filter_type_pills
    count = pills.count()
    labels = [pills.nth(i).text_content() or "" for i in range(count)]

    # Should contain exactly: All Types, IPV4, DOMAIN, MD5
    assert "All Types" in labels, f"Expected 'All Types' pill, got: {labels}"
    assert "IPV4" in labels, f"Expected 'IPV4' pill, got: {labels}"
    assert "DOMAIN" in labels, f"Expected 'DOMAIN' pill, got: {labels}"
    assert "MD5" in labels, f"Expected 'MD5' pill, got: {labels}"

    # No unexpected pills (e.g. SHA256, URL, CVE) — only those 4
    assert len(labels) == 4, f"Expected 4 pills, got {len(labels)}: {labels}"


# ---------------------------------------------------------------------------
# FILTER-01 — verdict filtering
# ---------------------------------------------------------------------------


def test_verdict_filter_no_data_shows_all_cards(page: Page, index_url: str) -> None:
    """Clicking 'No Data' shows all cards because all are no_data in offline mode (FILTER-01)."""
    results = _navigate_to_results(page, index_url)

    # All 5 cards should be visible initially
    expect(results.visible_cards).to_have_count(5)

    # Click 'No Data' — all should remain visible
    results.filter_by_verdict("no_data")
    expect(results.visible_cards).to_have_count(5)


def test_verdict_filter_malicious_hides_all_cards(page: Page, index_url: str) -> None:
    """Clicking 'Malicious' hides all cards when none are malicious (FILTER-01)."""
    results = _navigate_to_results(page, index_url)

    # In offline mode, no cards are malicious
    results.filter_by_verdict("malicious")
    expect(results.visible_cards).to_have_count(0)
    expect(results.hidden_cards).to_have_count(5)


def test_verdict_filter_all_resets_visibility(page: Page, index_url: str) -> None:
    """Clicking 'All' after another filter restores all cards (FILTER-01)."""
    results = _navigate_to_results(page, index_url)

    # First hide everything with 'Malicious'
    results.filter_by_verdict("malicious")
    expect(results.visible_cards).to_have_count(0)

    # Then click 'All' — all 5 cards should reappear
    results.filter_by_verdict("all")
    expect(results.visible_cards).to_have_count(5)


# ---------------------------------------------------------------------------
# FILTER-02 — IOC type pill filtering
# ---------------------------------------------------------------------------


def test_type_filter_ipv4_shows_only_ipv4(page: Page, index_url: str) -> None:
    """Clicking 'IPV4' type pill shows only ipv4 cards (FILTER-02)."""
    results = _navigate_to_results(page, index_url)

    results.filter_by_type("ipv4")
    expect(results.visible_cards).to_have_count(2)  # 8.8.8.8 and 1.1.1.1


def test_type_filter_domain_shows_only_domains(page: Page, index_url: str) -> None:
    """Clicking 'DOMAIN' type pill shows only domain cards (FILTER-02)."""
    results = _navigate_to_results(page, index_url)

    results.filter_by_type("domain")
    expect(results.visible_cards).to_have_count(2)  # evil.com and test.org


def test_type_filter_all_types_resets_visibility(page: Page, index_url: str) -> None:
    """Clicking 'All Types' after a type filter restores all cards (FILTER-02)."""
    results = _navigate_to_results(page, index_url)

    # First filter to IPV4
    results.filter_by_type("ipv4")
    expect(results.visible_cards).to_have_count(2)

    # Then reset to 'All Types'
    results.filter_by_type("all")
    expect(results.visible_cards).to_have_count(5)


# ---------------------------------------------------------------------------
# FILTER-03 — text search
# ---------------------------------------------------------------------------


def test_search_filters_by_value_substring(page: Page, index_url: str) -> None:
    """Typing in search box filters cards by IOC value substring (FILTER-03)."""
    results = _navigate_to_results(page, index_url)

    # Search for "8.8" — should match only 8.8.8.8
    results.search("8.8")
    expect(results.visible_cards).to_have_count(1)

    visible = results.visible_cards.first
    assert visible.get_attribute("data-ioc-value") == "8.8.8.8"


def test_search_filters_by_domain_substring(page: Page, index_url: str) -> None:
    """Searching 'evil' shows only evil.com card (FILTER-03)."""
    results = _navigate_to_results(page, index_url)

    results.search("evil")
    expect(results.visible_cards).to_have_count(1)

    visible = results.visible_cards.first
    assert visible.get_attribute("data-ioc-value") == "evil.com"


def test_search_clear_restores_all_cards(page: Page, index_url: str) -> None:
    """Clearing the search field restores all cards (FILTER-03)."""
    results = _navigate_to_results(page, index_url)

    results.search("evil")
    expect(results.visible_cards).to_have_count(1)

    # Clear the search
    results.search("")
    expect(results.visible_cards).to_have_count(5)


def test_search_is_case_insensitive(page: Page, index_url: str) -> None:
    """Text search is case-insensitive (FILTER-03)."""
    results = _navigate_to_results(page, index_url)

    # Search uppercase for a lowercase domain
    results.search("EVIL")
    expect(results.visible_cards).to_have_count(1)

    visible = results.visible_cards.first
    assert visible.get_attribute("data-ioc-value") == "evil.com"


# ---------------------------------------------------------------------------
# Combined filters (FILTER-01 + FILTER-02 + FILTER-03)
# ---------------------------------------------------------------------------


def test_combined_type_and_search_filters(page: Page, index_url: str) -> None:
    """Type pill and search input combine with AND logic (FILTER-01 + FILTER-02 + FILTER-03)."""
    results = _navigate_to_results(page, index_url)

    # Type "1.1" in search — matches 1.1.1.1 only (8.8.8.8 contains no "1.1" substring match)
    results.search("1.1")
    expect(results.visible_cards).to_have_count(1)

    # Additionally filter to IPV4 — should still be 1 (same card)
    results.filter_by_type("ipv4")
    expect(results.visible_cards).to_have_count(1)

    # Now search for "8.8" — only 8.8.8.8 matches (still filtered to IPV4)
    results.search("8.8")
    expect(results.visible_cards).to_have_count(1)
    assert results.visible_cards.first.get_attribute("data-ioc-value") == "8.8.8.8"


def test_combined_verdict_and_type_filters(page: Page, index_url: str) -> None:
    """Verdict filter and type pill combine with AND logic (FILTER-01 + FILTER-02)."""
    results = _navigate_to_results(page, index_url)

    # 'No Data' verdict (all cards) + 'DOMAIN' type = 2 cards
    results.filter_by_verdict("no_data")
    results.filter_by_type("domain")
    expect(results.visible_cards).to_have_count(2)

    # 'Malicious' verdict (no cards) + 'DOMAIN' type = 0 cards
    results.filter_by_verdict("malicious")
    expect(results.visible_cards).to_have_count(0)


# ---------------------------------------------------------------------------
# FILTER-04 — sticky positioning
# ---------------------------------------------------------------------------


def test_filter_bar_has_sticky_position(page: Page, index_url: str) -> None:
    """Filter bar wrapper has CSS position: sticky (FILTER-04)."""
    # Navigate freshly to ensure we are on the results page
    results = _navigate_to_results(page, index_url)

    # Verify filter bar is present before checking its style
    expect(results.filter_bar).to_be_visible()

    # Use JS evaluate to read the computed style of the filter bar wrapper
    position = page.evaluate(
        "() => window.getComputedStyle(document.querySelector('.filter-bar-wrapper')).position"
    )
    assert position == "sticky", (
        f"Expected filter bar to have position:sticky, got: '{position}'"
    )


# ---------------------------------------------------------------------------
# Phase 4 — Results UX structural tests
# ---------------------------------------------------------------------------


def test_offline_mode_has_no_provider_coverage(page: Page, index_url: str) -> None:
    """Provider coverage row is not present in offline mode."""
    results = _navigate_to_results(page, index_url)
    expect(results.provider_coverage).to_have_count(0)


def test_offline_mode_cards_have_no_enrichment_slot(page: Page, index_url: str) -> None:
    """In offline mode, IOC cards do not contain enrichment slots."""
    results = _navigate_to_results(page, index_url)
    slots = results.page.locator(".enrichment-slot")
    expect(slots).to_have_count(0)


# ---------------------------------------------------------------------------
# Enrichment surface tests — online mode with mocked API responses
# ---------------------------------------------------------------------------
# These tests intercept /enrichment/status/* via page.route() so no real API
# key is required.  The canned response triggers the full enrichment.ts pipeline:
#   - handleProviderResult() → getOrCreateSummaryRow() (row-factory.ts)
#   - markEnrichmentComplete() → injectDetailLink()
#
# All enrichment tests submit a single IOC ("8.8.8.8") so the mock response
# (which references "8.8.8.8") aligns with what the server processes.
# ---------------------------------------------------------------------------

# Single IOC used in all enrichment surface tests
SINGLE_IP_IOC = "8.8.8.8"


def _navigate_online_with_mock(page: Page, index_url: str, text: str = SINGLE_IP_IOC) -> ResultsPage:
    """Navigate in online mode with enrichment polling intercepted by a route mock.

    Sets up the route mock BEFORE navigation so the handler is active when
    enrichment.ts fires its first fetch().  Waits for ``.ioc-summary-row`` to
    appear (confirms enrichment.ts processed the mocked response) before
    returning the ResultsPage.

    Args:
        page: Playwright Page instance.
        index_url: URL of the SentinelX index page.
        text: IOC text to submit (default: single IP matching the mock response).

    Returns:
        :class:`ResultsPage` after enrichment rows are visible.
    """
    from tests.e2e.conftest import setup_enrichment_route_mock

    # Register route mock BEFORE navigation
    setup_enrichment_route_mock(page)

    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(text, mode="online")

    # Wait for enrichment.ts to fire and row-factory.ts to inject the summary row
    page.wait_for_selector(".ioc-summary-row", timeout=10_000)

    return ResultsPage(page)


def test_online_mode_has_enrichment_slots(page: Page, index_url: str) -> None:
    """In online mode, each IOC card has an enrichment slot (server-rendered)."""
    results = _navigate_online_with_mock(page, index_url)

    card_count = results.ioc_cards.count()
    slot_count = results.enrichment_slots.count()
    assert slot_count == card_count, (
        f"Expected {card_count} enrichment slots (one per card), got {slot_count}"
    )


def test_enrichment_summary_row_created_after_polling(page: Page, index_url: str) -> None:
    """Mocked enrichment polling causes .ioc-summary-row to appear inside an .ioc-card."""
    results = _navigate_online_with_mock(page, index_url)

    # At least one summary row must exist
    expect(results.summary_rows).not_to_have_count(0)

    # The first summary row must be a descendant of an .ioc-card
    first_row = results.summary_rows.first
    card_ancestor = page.locator(".ioc-card").filter(has=first_row)
    assert card_ancestor.count() >= 1, ".ioc-summary-row is not inside an .ioc-card"


def test_enrichment_summary_row_has_verdict_micro_bar(page: Page, index_url: str) -> None:
    """Each summary row contains a .verdict-micro-bar element after mocked enrichment."""
    results = _navigate_online_with_mock(page, index_url)

    # Wait for micro-bar (it may render slightly after the summary row)
    page.wait_for_selector(".verdict-micro-bar", timeout=5_000)

    expect(results.micro_bars).not_to_have_count(0)


def test_expand_collapse_toggle(page: Page, index_url: str) -> None:
    """Clicking .ioc-summary-row toggles .is-open on both the row and .enrichment-details."""
    results = _navigate_online_with_mock(page, index_url)

    # --- Expand ---
    results.summary_rows.first.click()

    expect(page.locator(".ioc-summary-row.is-open")).to_have_count(1)
    expect(page.locator(".enrichment-details.is-open")).to_have_count(1)

    # --- Collapse ---
    results.summary_rows.first.click()

    expect(page.locator(".ioc-summary-row.is-open")).to_have_count(0)
    expect(page.locator(".enrichment-details.is-open")).to_have_count(0)


def test_enrichment_details_has_section_containers(page: Page, index_url: str) -> None:
    """Expanded .enrichment-details contains the expected section modifier classes."""
    results = _navigate_online_with_mock(page, index_url)

    # Expand the first summary row
    results.summary_rows.first.click()

    # Wait for details panel to open
    page.wait_for_selector(".enrichment-details.is-open", timeout=5_000)

    # At least one of the three section types must exist inside the open panel
    open_panel = page.locator(".enrichment-details.is-open")
    section_count = open_panel.locator(".enrichment-section").count()
    assert section_count >= 1, (
        f"Expected at least 1 .enrichment-section inside open panel, got {section_count}"
    )


def test_detail_link_injected_after_enrichment_complete(page: Page, index_url: str) -> None:
    """With complete:true in mock, .detail-link-footer and .detail-link are injected."""
    results = _navigate_online_with_mock(page, index_url)

    # markEnrichmentComplete() fires when complete:true — waits for footer injection
    page.wait_for_selector(".detail-link-footer", timeout=10_000)

    expect(results.detail_link_footers).not_to_have_count(0)
    expect(results.detail_links).not_to_have_count(0)

    # Detail link href must contain /ioc/ path (matches Flask route)
    first_link_href = results.detail_links.first.get_attribute("href") or ""
    assert "/ioc/" in first_link_href, (
        f"Expected detail link href to contain '/ioc/', got: '{first_link_href}'"
    )


def test_enrichment_slot_loaded_class_added(page: Page, index_url: str) -> None:
    """After mocked enrichment, at least one .enrichment-slot--loaded class is added."""
    results = _navigate_online_with_mock(page, index_url)

    # Wait until at least one slot gets the --loaded modifier
    page.wait_for_selector(".enrichment-slot--loaded", timeout=10_000)

    expect(results.loaded_enrichment_slots).not_to_have_count(0)


def test_offline_mode_no_summary_rows(page: Page, index_url: str) -> None:
    """In offline mode, no .ioc-summary-row elements are created (no enrichment polling)."""
    results = _navigate_to_results(page, index_url)

    expect(results.summary_rows).to_have_count(0)


# ---------------------------------------------------------------------------
# Email IOC rendering (R016)
# ---------------------------------------------------------------------------
# These tests verify that email addresses in analyst input are extracted and
# displayed as IOC cards with a distinct EMAIL type badge and filter pill.
# Fully-defanged form (user[@]evil[.]com) is a known limitation — only
# undefanged emails are reliably extracted by iocsearcher.
# ---------------------------------------------------------------------------

EMAIL_IOC_TEXT = "Contact attacker@evil.com or admin@phish.org about the incident."


def test_email_ioc_card_renders(page: Page, index_url: str) -> None:
    """Email addresses in input are extracted and rendered as IOC cards (R016)."""
    results = _navigate_to_results(page, index_url, text=EMAIL_IOC_TEXT)

    email_cards = results.cards_for_type("email")
    assert email_cards.count() >= 1, (
        "Expected at least 1 .ioc-card[data-ioc-type='email'], got 0"
    )


def test_email_filter_pill_exists(page: Page, index_url: str) -> None:
    """EMAIL filter pill is present in the filter bar when email IOCs are in results (R016)."""
    _navigate_to_results(page, index_url, text=EMAIL_IOC_TEXT)

    pill = page.locator(".filter-pill--email")
    expect(pill).to_be_visible()
    expect(pill).to_contain_text("EMAIL")


def test_email_filter_pill_shows_only_email_cards(page: Page, index_url: str) -> None:
    """Clicking EMAIL pill hides all non-email cards (R016)."""
    results = _navigate_to_results(page, index_url, text=EMAIL_IOC_TEXT)

    results.filter_by_type("email")

    visible = results.visible_cards
    count = visible.count()
    assert count >= 1, "Expected at least 1 visible card after EMAIL filter"
    for i in range(count):
        card_type = visible.nth(i).get_attribute("data-ioc-type")
        assert card_type == "email", (
            f"Expected all visible cards to be email type, got: {card_type!r}"
        )


def test_email_filter_pill_active_state(page: Page, index_url: str) -> None:
    """EMAIL filter pill shows active state when clicked (R016)."""
    _navigate_to_results(page, index_url, text=EMAIL_IOC_TEXT)

    results_page = page.locator(".filter-type-pills")
    results_page.locator(".filter-pill--email").click()

    active_pill = page.locator(".filter-pill--email.filter-pill--active")
    expect(active_pill).to_be_visible()


def test_all_types_pill_resets_after_email_filter(page: Page, index_url: str) -> None:
    """Clicking 'All Types' after EMAIL filter restores the full card count (R016)."""
    results = _navigate_to_results(page, index_url, text=EMAIL_IOC_TEXT)

    total_before = results.visible_cards.count()
    results.filter_by_type("email")
    email_count = results.visible_cards.count()
    assert email_count < total_before, (
        "Expected fewer cards after EMAIL filter than before"
    )

    results.filter_by_type("all")
    expect(results.visible_cards).to_have_count(total_before)


def test_email_cards_have_neutral_type_badge(page: Page, index_url: str) -> None:
    """Email IOC cards contain a .ioc-type-badge--email badge element (R016)."""
    _navigate_to_results(page, index_url, text=EMAIL_IOC_TEXT)

    badge = page.locator(".ioc-type-badge--email")
    expect(badge.first).to_be_visible()
    badge_text = badge.first.text_content() or ""
    assert "EMAIL" in badge_text.upper(), (
        f"Expected badge text to contain 'EMAIL', got: {badge_text!r}"
    )

