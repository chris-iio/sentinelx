"""E2E tests for the SentinelX settings page.

Covers: page rendering, accordion, provider listing, API key forms,
status indicators, show/hide toggle (JS), flash messages, CSRF, navigation,
security headers.
"""

from playwright.sync_api import Page, expect

from tests.e2e.pages import IndexPage, SettingsPage

# All key-requiring providers displayed on the settings page.
EXPECTED_PROVIDERS = [
    "virustotal", "malwarebazaar", "threatfox", "urlhaus",
    "otx", "greynoise", "abuseipdb",
]


# -- Page Rendering --


def test_settings_page_loads(page: Page, live_server: str) -> None:
    """Settings page renders with a back link."""
    sp = SettingsPage(page, live_server)
    sp.goto()
    expect(sp.back_link).to_be_visible()


def test_settings_page_title_tag(page: Page, live_server: str) -> None:
    """Browser tab title is set for the settings page."""
    page.goto(live_server + "/settings")
    expect(page).to_have_title("SentinelX")


def test_settings_security_headers(page: Page, live_server: str) -> None:
    """Settings page response includes required security headers."""
    from tests.e2e.conftest import assert_security_headers

    response = page.goto(live_server + "/settings")
    assert response is not None
    assert_security_headers(response.headers)


# -- Accordion --


def test_accordion_all_collapsed_by_default(page: Page, live_server: str) -> None:
    """All accordion sections are collapsed on page load."""
    sp = SettingsPage(page, live_server)
    sp.goto()
    for pid in EXPECTED_PROVIDERS:
        sp.expect_provider_collapsed(pid)


def test_accordion_expands_on_click(page: Page, live_server: str) -> None:
    """Clicking an accordion header expands the section."""
    sp = SettingsPage(page, live_server)
    sp.goto()
    pid = "greynoise"
    sp.expand_provider(pid)
    sp.expect_provider_expanded(pid)


def test_accordion_one_at_a_time(page: Page, live_server: str) -> None:
    """Expanding one section collapses the previously open one."""
    sp = SettingsPage(page, live_server)
    sp.goto()
    sp.expand_provider("virustotal")
    sp.expect_provider_expanded("virustotal")

    sp.expand_provider("greynoise")
    sp.expect_provider_expanded("greynoise")
    sp.expect_provider_collapsed("virustotal")


# -- Provider Listing --


def test_settings_lists_all_providers(page: Page, live_server: str) -> None:
    """All key-requiring providers are listed as sections."""
    sp = SettingsPage(page, live_server)
    sp.goto()
    sp.expect_provider_count(len(EXPECTED_PROVIDERS))


def test_each_provider_has_title(page: Page, live_server: str) -> None:
    """Each provider section displays a title with the provider name."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    expected_names = {
        "virustotal": "VirusTotal",
        "malwarebazaar": "MalwareBazaar",
        "threatfox": "ThreatFox",
        "urlhaus": "URLhaus",
        "otx": "OTX AlienVault",
        "greynoise": "GreyNoise",
        "abuseipdb": "AbuseIPDB",
    }
    for pid, name in expected_names.items():
        expect(sp.provider_title(pid)).to_contain_text(name)


def test_each_provider_has_description(page: Page, live_server: str) -> None:
    """Each provider section shows a description when expanded."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    for pid in EXPECTED_PROVIDERS:
        sp.expand_provider(pid)
        expect(sp.provider_description(pid)).to_be_visible()


def test_each_provider_has_signup_link(page: Page, live_server: str) -> None:
    """Each provider section includes an external signup link."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    for pid in EXPECTED_PROVIDERS:
        sp.expand_provider(pid)
        link = sp.provider_signup_link(pid)
        expect(link).to_be_visible()
        href = link.get_attribute("href")
        assert href is not None
        assert href.startswith("https://"), f"Signup link for {pid} is not HTTPS: {href}"
        expect(link).to_have_attribute("target", "_blank")
        expect(link).to_have_attribute("rel", "noopener noreferrer")


def test_cache_section_visible(page: Page, live_server: str) -> None:
    """Cache section is visible on settings page."""
    sp = SettingsPage(page, live_server)
    sp.goto()
    cache_section = page.locator(".settings-cache-section")
    expect(cache_section).to_be_visible()


# -- Status Indicators --


def test_providers_show_not_configured_by_default(page: Page, live_server: str) -> None:
    """All providers show 'Not configured' status when no keys are stored."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    for pid in EXPECTED_PROVIDERS:
        sp.expect_status_not_configured(pid)


# -- Form Elements --


def test_each_provider_has_form_with_csrf(page: Page, live_server: str) -> None:
    """Each provider form includes a CSRF token hidden input."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    for pid in EXPECTED_PROVIDERS:
        sp.expand_provider(pid)
        csrf = sp.csrf_token(pid)
        expect(csrf).to_be_attached()
        token = csrf.get_attribute("value")
        assert token is not None
        assert len(token) > 10, f"CSRF token for {pid} looks too short"


def test_each_provider_has_hidden_provider_id(page: Page, live_server: str) -> None:
    """Each form includes a hidden provider_id input matching the provider."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    for pid in EXPECTED_PROVIDERS:
        hidden = sp.provider_section(pid).locator(f'input[name="provider_id"][value="{pid}"]')
        expect(hidden).to_be_attached()


def test_api_key_inputs_are_password_type(page: Page, live_server: str) -> None:
    """All API key inputs default to type=password for security."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    for pid in EXPECTED_PROVIDERS:
        sp.expect_key_input_masked(pid)


def test_api_key_inputs_have_placeholder(page: Page, live_server: str) -> None:
    """Each API key input has a helpful placeholder mentioning the provider."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    for pid in EXPECTED_PROVIDERS:
        sp.expand_provider(pid)
        placeholder = sp.api_key_input(pid).get_attribute("placeholder")
        assert placeholder is not None
        assert "api key" in placeholder.lower()


def test_each_provider_has_save_button(page: Page, live_server: str) -> None:
    """Each provider section has a Save API Key button."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    for pid in EXPECTED_PROVIDERS:
        sp.expand_provider(pid)
        expect(sp.save_button(pid)).to_be_visible()
        expect(sp.save_button(pid)).to_have_text("Save API Key")


# -- Show/Hide Toggle (JavaScript) --


def test_show_hide_toggle_reveals_key(page: Page, live_server: str) -> None:
    """Clicking Show changes input type to text and button label to Hide."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    pid = "virustotal"
    sp.expand_provider(pid)
    sp.expect_key_input_masked(pid)
    expect(sp.show_hide_button(pid)).to_have_text("Show")

    sp.toggle_key_visibility(pid)

    sp.expect_key_input_visible(pid)
    expect(sp.show_hide_button(pid)).to_have_text("Hide")


def test_show_hide_toggle_hides_key_again(page: Page, live_server: str) -> None:
    """Clicking Hide returns input to password type and button to Show."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    pid = "greynoise"
    sp.toggle_key_visibility(pid)
    sp.expect_key_input_visible(pid)

    sp.toggle_key_visibility(pid)
    sp.expect_key_input_masked(pid)
    expect(sp.show_hide_button(pid)).to_have_text("Show")


def test_show_hide_toggles_are_independent(page: Page, live_server: str) -> None:
    """Toggling one provider's visibility doesn't affect others."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    sp.expand_provider("virustotal")
    sp.toggle_key_visibility("virustotal")
    sp.expect_key_input_visible("virustotal")

    # Others remain masked (even though in different accordion sections)
    sp.expect_key_input_masked("urlhaus")
    sp.expect_key_input_masked("otx")
    sp.expect_key_input_masked("greynoise")
    sp.expect_key_input_masked("abuseipdb")


def test_show_hide_button_has_aria_label(page: Page, live_server: str) -> None:
    """Show/Hide button has an accessible aria-label."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    for pid in EXPECTED_PROVIDERS:
        sp.expand_provider(pid)
        btn = sp.show_hide_button(pid)
        label = btn.get_attribute("aria-label")
        assert label is not None, f"Show/Hide button for {pid} missing aria-label"
        assert "api key" in label.lower() or "show" in label.lower()


# -- Form Submission (with isolated config) --


def test_empty_key_shows_error_flash(page: Page, live_server: str) -> None:
    """Submitting an empty API key shows an error flash message."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    sp.expand_provider("virustotal")
    sp.api_key_input("virustotal").fill("")
    sp.save_button("virustotal").click()

    sp.expect_flash_error("API key cannot be empty")


def test_save_key_shows_success_flash(page: Page, live_server: str) -> None:
    """Submitting a valid API key shows a success flash and 'Configured' status."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    sp.save_api_key("virustotal", "test-key-for-e2e-1234567890abcdef")

    sp.expect_flash_success("API key saved for virustotal")
    sp.expect_status_configured("virustotal")


def test_saved_key_is_masked_on_reload(page: Page, live_server: str) -> None:
    """After saving a key, reloading shows a masked version."""
    sp = SettingsPage(page, live_server)

    sp.goto()
    sp.save_api_key("otx", "my-test-api-key-abcd1234")
    sp.expect_flash_success("API key saved for otx")

    sp.goto()
    sp.expand_provider("otx")

    input_val = sp.api_key_input("otx").input_value()
    assert input_val.endswith("1234"), f"Masked key should end with last 4 chars, got: {input_val}"
    assert "****" in input_val or "***" in input_val, f"Should contain asterisks, got: {input_val}"


def test_save_key_for_non_vt_provider(page: Page, live_server: str) -> None:
    """Saving a key for a non-VirusTotal provider works correctly."""
    sp = SettingsPage(page, live_server)
    sp.goto()

    sp.save_api_key("abuseipdb", "abuseipdb-test-key-xyz7890")

    sp.expect_flash_success("API key saved for abuseipdb")
    sp.expect_status_configured("abuseipdb")


# -- Navigation --


def test_settings_nav_from_index(page: Page, live_server: str) -> None:
    """Clicking the settings icon in the header navigates to settings page."""
    page.goto(live_server + "/")

    settings_link = page.locator("a[aria-label='Settings']")
    expect(settings_link).to_be_visible()
    settings_link.click()

    expect(page).to_have_url(live_server + "/settings")


def test_settings_nav_from_results(page: Page, live_server: str) -> None:
    """Settings icon is accessible from the results page too."""
    idx = IndexPage(page, live_server)
    idx.goto()
    idx.extract_iocs("192.168.1.1")

    settings_link = page.locator("a[aria-label='Settings']")
    expect(settings_link).to_be_visible()
    settings_link.click()

    expect(page).to_have_url(live_server + "/settings")
