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

import pytest
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

    # 5 verdict buttons: All | Malicious | Suspicious | Clean | No Data
    expect(results.filter_verdict_buttons).to_have_count(5)

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
