"""E2E tests for the SentinelX homepage (index page).

Covers: page rendering, command-card intake shell, form state, responsive
hierarchy, header/footer, security headers, and the offline fast path.
"""

from playwright.sync_api import Page, expect

from tests.e2e.pages import IndexPage, ResultsPage


SYNTHETIC_IOCS = """\
Alert source: 203.0.113.10
Callback domain: malware.example.com
"""


def test_page_title(page: Page, index_url: str) -> None:
    """Page title includes 'SentinelX'."""
    page.goto(index_url)
    expect(page).to_have_title("sentinelx")


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


def test_command_card_surface_visible(page: Page, index_url: str) -> None:
    """The index page renders the command-card intake workbench and stable controls."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.expect_integrated_workbench_ready()
    expect(idx.eyebrow).to_have_text("Offline-first IOC extraction")
    expect(idx.title).to_contain_text("Paste indicators")
    expect(idx.subtitle).to_contain_text("Offline mode")


def test_desktop_command_card_hierarchy(page: Page, index_url: str) -> None:
    """Desktop layout presents the command card as the dominant intake surface."""
    page.set_viewport_size({"width": 1280, "height": 720})
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.expect_command_surface_visible()
    idx.expect_desktop_command_card_dominates_recent_rail()
    idx.expect_no_horizontal_overflow()
    card_box = idx.command_card.bounding_box()
    textarea_box = idx.textarea.bounding_box()
    title_box = idx.title.bounding_box()
    assert card_box is not None
    assert textarea_box is not None
    assert title_box is not None

    assert card_box["width"] >= 760, f"Command card should dominate desktop width, got {card_box['width']}px"
    assert textarea_box["width"] < card_box["width"], "Textarea should sit inside the command card chrome"
    assert title_box["y"] < textarea_box["y"], "Command-card title should lead the intake form"


def test_mobile_command_card_stacks_without_overflow(page: Page, index_url: str) -> None:
    """Mobile layout keeps the command card visible and stacks controls under the textarea."""
    page.set_viewport_size({"width": 390, "height": 844})
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.expect_command_surface_visible()
    idx.expect_mobile_recent_rail_stacks_below_command_card(viewport_width=390)
    card_box = idx.command_card.bounding_box()
    textarea_box = idx.textarea.bounding_box()
    actions_box = page.locator(".form-actions").bounding_box()
    assert card_box is not None
    assert textarea_box is not None
    assert actions_box is not None

    assert 0 <= card_box["x"] <= 12
    assert card_box["width"] <= 390
    assert textarea_box["y"] < actions_box["y"], "Mobile controls should stack below the textarea"


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
    """All command-card form elements render on page load."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.expect_command_surface_visible()


def test_textarea_placeholder(page: Page, index_url: str) -> None:
    """Textarea starts with empty placeholder."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    placeholder = idx.textarea.get_attribute("placeholder")
    assert placeholder == ""


def test_mode_toggle_labels(page: Page, index_url: str) -> None:
    """Mode toggle shows Offline and Online labels."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    expect(idx.mode_offline_label).to_have_text("Offline")
    expect(idx.mode_online_label).to_have_text("Online")
    expect(idx.mode_title).to_have_text("Analysis mode")
    expect(idx.mode_help).to_contain_text("Offline mode is the safe default")
    expect(idx.mode_status).to_have_text(
        "Offline selected — local extraction only; no provider enrichment requests are sent."
    )


def test_offline_mode_by_default(page: Page, index_url: str) -> None:
    """Offline mode is active by default."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.expect_mode("offline")
    expect(idx.mode_toggle_btn).to_have_attribute("aria-pressed", "false")


def test_extract_disabled_until_text_entry(page: Page, index_url: str) -> None:
    """Extract starts disabled and enables after synthetic IOC text entry."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.expect_submit_disabled()
    idx.fill_text(SYNTHETIC_IOCS)
    idx.expect_submit_enabled()


def test_recent_analyses_empty_state_keeps_intake_ready(page: Page, index_url: str) -> None:
    """Empty live-server history shows a secondary state without blocking paste-and-extract."""
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.expect_command_surface_visible()
    idx.expect_recent_empty_without_rows()
    idx.expect_no_preview_surfaces()
    idx.fill_text(SYNTHETIC_IOCS)
    idx.expect_submit_enabled()


def test_seeded_recent_analysis_renders_resume_link(
    page: Page,
    index_url: str,
    seed_recent_analysis,
) -> None:
    """Seeded history renders a compact row linking to /history/<id>."""
    analysis_id = seed_recent_analysis(
        analysis_id="e2e-homepage-resume",
        input_text="Resume investigation for 203.0.113.10",
    )
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.expect_integrated_workbench_ready()
    expect(idx.recent_empty_state).to_have_count(0)
    expect(idx.recent_unavailable_state).to_have_count(0)
    expect(idx.recent_rows).to_have_count(1)
    row = idx.expect_recent_resume_link("Resume investigation", f"/history/{analysis_id}")

    row.click()
    expect(page).to_have_url(f"{index_url.rstrip('/')}/history/{analysis_id}")
    expect(page.locator(".page-results")).to_be_visible()


def test_seeded_recent_analysis_desktop_rail_is_secondary(
    page: Page,
    index_url: str,
    seed_recent_analysis,
) -> None:
    """A populated desktop rail stays secondary to the paste command card."""
    seed_recent_analysis(input_text="Desktop hierarchy check for 203.0.113.10")
    page.set_viewport_size({"width": 1280, "height": 720})
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.expect_integrated_workbench_ready()
    expect(idx.recent_rows).to_have_count(1)
    idx.expect_recent_resume_link("Desktop hierarchy check", "/history/e2e-recent-analysis")
    idx.expect_desktop_command_card_dominates_recent_rail()
    idx.expect_no_horizontal_overflow()


def test_seeded_recent_analysis_mobile_stacks_below_command_card(
    page: Page,
    index_url: str,
    seed_recent_analysis,
) -> None:
    """A populated mobile rail appears below the command card without horizontal overflow."""
    seed_recent_analysis(input_text="Mobile stacking check for 203.0.113.10")
    page.set_viewport_size({"width": 390, "height": 844})
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.expect_integrated_workbench_ready()
    expect(idx.recent_rows).to_have_count(1)
    idx.expect_recent_resume_link("Mobile stacking check", "/history/e2e-recent-analysis")
    idx.expect_mobile_recent_rail_stacks_below_command_card(viewport_width=390)


def test_recent_analyses_unavailable_state_keeps_form_visible(
    page: Page,
    index_url: str,
    e2e_history_store,
    monkeypatch,
) -> None:
    """History lookup failures render an unavailable state while keeping the form usable."""
    def fail_recent_lookup(*, limit: int = 4):
        raise RuntimeError("synthetic e2e history failure with 203.0.113.10")

    monkeypatch.setattr(e2e_history_store, "list_recent", fail_recent_lookup)
    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()

    idx.expect_integrated_workbench_ready()
    idx.expect_recent_unavailable_without_rows()
    idx.fill_text(SYNTHETIC_IOCS)
    idx.expect_submit_enabled()


def test_offline_command_card_submit_reaches_results(page: Page, index_url: str) -> None:
    """A real offline command-card submit navigates to results without provider dependency."""
    requested_urls: list[str] = []
    page.on("request", lambda request: requested_urls.append(request.url))

    idx = IndexPage(page, index_url.rstrip("/"))
    idx.goto()
    idx.expect_integrated_workbench_ready()
    idx.extract_iocs(SYNTHETIC_IOCS, mode="offline")

    results = ResultsPage(page)
    expect(page.locator(".page-results")).to_be_visible()
    results.expect_mode("offline")
    assert results.ioc_cards.count() >= 2
    assert not any("/enrichment/status/" in url for url in requested_urls), (
        "Offline extraction must not start enrichment polling"
    )


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
