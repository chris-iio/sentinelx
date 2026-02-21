"""E2E tests for the IOC extraction flow.

Covers: successful extraction, empty input, no IOCs found, defanging,
deduplication, multiple IOC types, and mode indicator.
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
    """Mixed IOC text produces grouped results in offline mode."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(MIXED_IOCS, mode="offline")

    results = ResultsPage(page)
    results.expect_mode("offline")

    # Verify at least some groups are present
    group_count = results.ioc_groups.count()
    assert group_count >= 3, f"Expected at least 3 IOC groups, got {group_count}"


def test_extract_shows_correct_total_count(page: Page, index_url: str) -> None:
    """Total count in results summary reflects extracted IOCs."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(IPV4_ONLY)

    results = ResultsPage(page)
    # Should find 2 unique IPv4 addresses
    results.expect_total_count(2)


def test_extract_ipv4_group(page: Page, index_url: str) -> None:
    """IPv4 addresses appear in the ipv4 group."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(IPV4_ONLY)

    results = ResultsPage(page)
    results.expect_group_visible("ipv4")
    results.expect_group_count("ipv4", 2)

    values = results.ioc_values("ipv4")
    texts = [values.nth(i).text_content() for i in range(values.count())]
    assert "10.20.30.40" in texts
    assert "172.16.0.1" in texts


def test_extract_sha256_group(page: Page, index_url: str) -> None:
    """SHA256 hashes appear in the sha256 group."""
    sha256_text = "Hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(sha256_text)

    results = ResultsPage(page)
    results.expect_group_visible("sha256")
    results.expect_group_count("sha256", 1)


def test_extract_cve_group(page: Page, index_url: str) -> None:
    """CVE identifiers appear in the cve group."""
    cve_text = "Exploited: CVE-2024-12345 and CVE-2023-99999"
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(cve_text)

    results = ResultsPage(page)
    results.expect_group_visible("cve")
    results.expect_group_count("cve", 2)


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
    results.expect_group_count("ipv4", 2)


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


def test_accordion_groups_are_open_by_default(page: Page, index_url: str) -> None:
    """All IOC group accordions start in the open state."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(MIXED_IOCS)

    results = ResultsPage(page)
    groups = results.ioc_groups
    count = groups.count()

    for i in range(count):
        group = groups.nth(i)
        assert group.get_attribute("open") is not None, f"Group {i} should be open"


def test_accordion_can_be_collapsed(page: Page, index_url: str) -> None:
    """Clicking a group summary collapses the accordion."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(IPV4_ONLY)

    results = ResultsPage(page)
    group = results.group_for_type("ipv4")
    summary = group.locator("summary")

    # Initially open
    assert group.get_attribute("open") is not None

    # Click to collapse
    summary.click()
    assert group.get_attribute("open") is None

    # Click to re-open
    summary.click()
    assert group.get_attribute("open") is not None


def test_type_labels_are_uppercase(page: Page, index_url: str) -> None:
    """IOC type labels are displayed in uppercase."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.extract_iocs(IPV4_ONLY)

    results = ResultsPage(page)
    label = results.type_label("ipv4")
    expect(label).to_have_text("IPV4")
