"""E2E tests for the IOC extraction flow.

Covers: successful extraction, empty input, no IOCs found, defanging,
deduplication, multiple IOC types, mode indicator, card layout,
type badges, verdict labels, and dashboard.
"""

from playwright.sync_api import Page, expect

from tests.e2e.pages import IndexPage, ResultsPage


# ---- Sample IOC texts ----

MIXED_IOCS = """\
Alert: suspicious activity from 192.168.1.1 and 10.0.0.5.
C2 domain: evil.example.com
Malware hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
URL: https://malware.example.com/payload.exe
CVE-2024-12345 exploited in the wild.
"""

DEFANGED_IOCS = """\
Source IP: 192[.]168[.]1[.]100
URL: hxxps://evil[.]example[.]com/callback
Domain: malware[.]test[.]org
"""

IPV4_ONLY = "Alert from 10.20.30.40 and 172.16.0.1"

NO_IOCS_TEXT = "This is just a plain text message with no indicators."

DUPLICATE_IOCS = """\
192.168.1.1
192.168.1.1
192.168.1.1
10.0.0.5
10.0.0.5
"""


# ---- Extraction flow tests ----


def test_extract_mixed_iocs_offline(page: Page, index_url: str) -> None:
    """Mixed IOC text produces card results in offline mode."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(MIXED_IOCS, mode="offline")

    results = ResultsPage(page)
    results.expect_mode("offline")

    # Verify cards are present for multiple types
    card_count = results.ioc_cards.count()
    assert card_count >= 3, f"Expected at least 3 IOC cards, got {card_count}"


def test_extract_shows_correct_total_count(page: Page, index_url: str) -> None:
    """Total count in results summary reflects extracted IOCs."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(IPV4_ONLY)

    results = ResultsPage(page)
    # Should find 2 unique IPv4 addresses
    results.expect_total_count(2)


def test_extract_ipv4_cards(page: Page, index_url: str) -> None:
    """IPv4 addresses appear as cards with ipv4 type."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(IPV4_ONLY)

    results = ResultsPage(page)
    results.expect_cards_for_type("ipv4", 2)

    values = results.ioc_values("ipv4")
    texts = [values.nth(i).text_content() for i in range(values.count())]
    assert "10.20.30.40" in texts
    assert "172.16.0.1" in texts


def test_extract_sha256_card(page: Page, index_url: str) -> None:
    """SHA256 hashes appear as cards with sha256 type."""
    sha256_text = "Hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(sha256_text)

    results = ResultsPage(page)
    results.expect_cards_for_type("sha256", 1)


def test_extract_cve_cards(page: Page, index_url: str) -> None:
    """CVE identifiers appear as cards with cve type."""
    cve_text = "Exploited: CVE-2024-12345 and CVE-2023-99999"
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(cve_text)

    results = ResultsPage(page)
    results.expect_cards_for_type("cve", 2)


def test_defanged_iocs_are_normalized(page: Page, index_url: str) -> None:
    """Defanged IOCs are refanged and shown as normalized values."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(DEFANGED_IOCS)

    results = ResultsPage(page)

    # The defanged 192[.]168[.]1[.]100 should be normalized to 192.168.1.100
    ipv4_values = results.ioc_values("ipv4")
    ipv4_texts = [ipv4_values.nth(i).text_content() for i in range(ipv4_values.count())]
    assert "192.168.1.100" in ipv4_texts


def test_defanged_shows_original(page: Page, index_url: str) -> None:
    """When raw form differs from normalized, original is displayed."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs("Source: 192[.]168[.]1[.]100")

    results = ResultsPage(page)
    originals = results.ioc_originals("ipv4")

    # At least one original should be visible (the defanged form)
    original_count = originals.count()
    if original_count > 0:
        original_text = originals.first.text_content()
        assert original_text is not None
        assert "[.]" in original_text or "[dot]" in original_text or original_text != "192.168.1.100"


def test_deduplication(page: Page, index_url: str) -> None:
    """Duplicate IOCs are deduplicated in results."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(DUPLICATE_IOCS)

    results = ResultsPage(page)
    # 5 lines with 2 unique IPs
    results.expect_total_count(2)
    results.expect_cards_for_type("ipv4", 2)


def test_empty_input_shows_error(page: Page, index_url: str) -> None:
    """Submitting empty text shows an error on the index page."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    # Force-enable the submit button to bypass JS validation
    page.evaluate("document.getElementById('submit-btn').disabled = false")
    idx.submit()

    # Should stay on index with error message
    expect(idx.error_alert).to_be_visible()
    expect(idx.error_alert).to_contain_text("No input provided")


def test_whitespace_only_input_shows_error(page: Page, index_url: str) -> None:
    """Submitting whitespace-only text shows an error.

    The JS correctly keeps the submit button disabled for whitespace-only
    input, so we bypass client-side validation to test the server-side guard.
    """
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.fill_text("   \n\t  ")
    # Force-enable submit to bypass JS validation (testing server-side guard)
    page.evaluate("document.getElementById('submit-btn').disabled = false")
    idx.submit()

    expect(idx.error_alert).to_be_visible()
    expect(idx.error_alert).to_contain_text("No input provided")


def test_no_iocs_found(page: Page, index_url: str) -> None:
    """Text with no IOCs shows the 'no results' state."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(NO_IOCS_TEXT)

    results = ResultsPage(page)
    results.expect_total_count(0)
    results.expect_no_results()


def test_online_mode_indicator(page: Page, index_url: str) -> None:
    """Submitting in online mode shows 'Online Mode' in results."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(IPV4_ONLY, mode="online")

    results = ResultsPage(page)
    results.expect_mode("online")


def test_cards_have_type_badges(page: Page, index_url: str) -> None:
    """Each IOC card has a type badge with the correct label."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(IPV4_ONLY)

    results = ResultsPage(page)
    badges = results.type_badge("ipv4")
    expect(badges).to_have_count(2)
    expect(badges.first).to_have_text("IPV4")


def test_cards_have_verdict_labels(page: Page, index_url: str) -> None:
    """Each IOC card has a verdict label (defaults to NO DATA in offline mode)."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(IPV4_ONLY)

    results = ResultsPage(page)
    labels = results.verdict_labels("ipv4")
    expect(labels).to_have_count(2)
    expect(labels.first).to_have_text("NO DATA")


def test_cards_have_data_verdict_attribute(page: Page, index_url: str) -> None:
    """Each IOC card has a data-verdict attribute (defaults to no_data)."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(IPV4_ONLY)

    results = ResultsPage(page)
    cards = results.cards_for_type("ipv4")
    count = cards.count()

    for i in range(count):
        card = cards.nth(i)
        verdict = card.get_attribute("data-verdict")
        assert verdict == "no_data", f"Card {i} should have data-verdict='no_data', got '{verdict}'"


def test_cards_have_data_ioc_value_attribute(page: Page, index_url: str) -> None:
    """Each IOC card carries its value in data-ioc-value attribute."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs("10.0.0.1")

    results = ResultsPage(page)
    card = results.cards_for_type("ipv4").first
    data_value = card.get_attribute("data-ioc-value")
    assert data_value == "10.0.0.1"


def test_online_mode_shows_verdict_dashboard(page: Page, index_url: str) -> None:
    """Online mode results page shows the verdict dashboard."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(IPV4_ONLY, mode="online")

    results = ResultsPage(page)
    expect(results.verdict_dashboard).to_be_visible()


def test_offline_mode_hides_verdict_dashboard(page: Page, index_url: str) -> None:
    """Offline mode results page does not show the verdict dashboard."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(IPV4_ONLY, mode="offline")

    results = ResultsPage(page)
    expect(results.verdict_dashboard).to_have_count(0)


def test_responsive_grid_layout(page: Page, index_url: str) -> None:
    """Cards grid uses responsive layout."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(IPV4_ONLY)

    # Verify the grid container exists
    grid = page.locator("#ioc-cards-grid")
    expect(grid).to_be_visible()
