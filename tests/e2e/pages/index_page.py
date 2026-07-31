"""Page Object Model for the SentinelX index (paste form) page."""

from playwright.sync_api import Locator, Page, expect


class IndexPage:
    """Encapsulates selectors and actions for the IOC paste form."""

    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url

        # Command-card shell locators
        self.page_index = page.locator(".page-index")
        self.workbench = page.locator(".intake-workbench")
        self.command_card = page.locator(".command-card")
        self.card_header = page.locator(".command-card-header")
        self.hero_brand = page.locator(".site-nav-brand")
        self.eyebrow = self.card_header.locator(".command-card-eyebrow")
        self.title = page.locator(".command-card-title")
        self.subtitle = page.locator(".command-card-help")
        self.form = page.locator("#analyze-form")

        # Stable form-control locators consumed by downstream tests
        self.textarea = page.locator("#ioc-text")
        self.submit_btn = page.locator("#submit-btn")
        self.clear_btn = page.locator("#clear-btn")
        self.mode_title = page.locator("#mode-title")
        self.mode_help = page.locator("#mode-help")
        self.mode_status = page.locator("#mode-status")
        self.mode_toggle_widget = page.locator("#mode-toggle-widget")
        self.mode_toggle_btn = page.locator("#mode-toggle-btn")
        self.mode_input = page.locator("#mode-input")
        self.mode_offline_label = self.mode_toggle_widget.locator(".mode-toggle-label--offline")
        self.mode_online_label = self.mode_toggle_widget.locator(".mode-toggle-label--online")
        self.paste_feedback = page.locator("#paste-feedback")
        self.error_alert = page.locator(".alert-error")
        self.site_settings_link = page.locator("nav.floating-settings a[aria-label='Settings']")

        # Recent analyses rail locators
        self.recent_rail = page.locator(".recent-analyses-rail")
        self.recent_rows = page.locator(".recent-analysis-row")
        self.recent_empty_state = page.locator(".recent-analyses-empty")
        self.recent_unavailable_state = page.locator(".recent-analyses-unavailable")
        self.recent_title = page.locator("#recent-analyses-title")

    def goto(self) -> None:
        """Navigate to the index page."""
        self.page.goto(self.base_url + "/")

    def fill_text(self, text: str) -> None:
        """Fill the IOC textarea with the given text."""
        self.textarea.fill(text)

    def toggle_mode(self) -> None:
        """Click the mode toggle button to switch between offline/online."""
        self.mode_toggle_btn.click()

    def get_mode(self) -> str:
        """Return the current mode value from the hidden input."""
        return self.mode_input.input_value()

    def expect_mode(self, mode: str) -> None:
        """Assert all synchronized mode surfaces have the expected state."""
        expect(self.mode_input).to_have_value(mode)
        expect(self.mode_toggle_widget).to_have_attribute("data-mode", mode)
        expect(self.mode_toggle_btn).to_have_attribute("aria-pressed", "true" if mode == "online" else "false")
        if mode == "online":
            expect(self.mode_status).to_have_text("Online selected — configured providers may enrich submitted indicators.")
        else:
            expect(self.mode_status).to_have_text(
                "Offline selected — local extraction only; no provider enrichment requests are sent."
            )

    def select_mode(self, mode: str) -> None:
        """Set mode to the given value by toggling if needed."""
        current = self.mode_input.input_value()
        if current != mode:
            self.toggle_mode()

    def submit(self) -> None:
        """Click the submit button."""
        self.submit_btn.click()

    def clear(self) -> None:
        """Click the clear button."""
        self.clear_btn.click()

    def extract_iocs(self, text: str, mode: str = "offline") -> None:
        """Fill text, select mode, and submit the form."""
        self.fill_text(text)
        self.select_mode(mode)
        self.submit()

    def expect_command_surface_visible(self) -> None:
        """Assert the command-card intake shell and stable controls are visible."""
        expect(self.page_index).to_be_visible()
        expect(self.workbench).to_be_visible()
        expect(self.command_card).to_be_visible()
        expect(self.card_header).to_be_visible()
        expect(self.title).to_be_visible()
        expect(self.subtitle).to_be_visible()
        expect(self.form).to_be_visible()
        expect(self.textarea).to_be_visible()
        expect(self.mode_title).to_be_visible()
        expect(self.mode_help).to_be_visible()
        expect(self.mode_status).to_be_visible()
        expect(self.mode_toggle_widget).to_be_visible()
        expect(self.clear_btn).to_be_visible()
        expect(self.submit_btn).to_be_visible()

    def expect_no_preview_surfaces(self) -> None:
        """Assert pre-submit preview/results surfaces are absent from the intake workbench."""
        expect(self.page.locator(".ioc-preview")).to_have_count(0)
        expect(self.page.locator(".preview-rail")).to_have_count(0)
        expect(self.page.locator(".page-results")).to_have_count(0)

    def expect_integrated_workbench_ready(self, mode: str = "offline") -> None:
        """Assert the assembled intake workbench is visible, synchronized, and diagnostic-ready."""
        self.expect_command_surface_visible()
        self.expect_mode(mode)
        self.expect_recent_rail_visible()
        self.expect_no_preview_surfaces()

    def expect_no_horizontal_overflow(self, *, tolerance_px: int = 1) -> None:
        """Assert the document does not create horizontal scroll at the current viewport."""
        viewport = self.page.evaluate(
            """() => {
                const scrolling = document.scrollingElement || document.documentElement;
                return {
                    clientWidth: document.documentElement.clientWidth,
                    scrollWidth: scrolling.scrollWidth,
                    bodyScrollWidth: document.body.scrollWidth,
                };
            }"""
        )
        max_scroll_width = max(viewport["scrollWidth"], viewport["bodyScrollWidth"])
        assert max_scroll_width <= viewport["clientWidth"] + tolerance_px, (
            "Workbench should not create horizontal overflow: "
            f"clientWidth={viewport['clientWidth']}px scrollWidth={viewport['scrollWidth']}px "
            f"bodyScrollWidth={viewport['bodyScrollWidth']}px"
        )

    def expect_submit_disabled(self) -> None:
        """Assert the submit button is disabled."""
        expect(self.submit_btn).to_be_disabled()

    def expect_submit_enabled(self) -> None:
        """Assert the submit button is enabled."""
        expect(self.submit_btn).to_be_enabled()

    def recent_row(self, text: str) -> Locator:
        """Return a recent-analysis row containing *text*."""
        return self.recent_rows.filter(has_text=text)

    def expect_recent_resume_link(self, text: str, href: str) -> Locator:
        """Assert a recent-analysis row exists for *text* and links to *href*."""
        row = self.recent_row(text)
        expect(row).to_be_visible()
        expect(row).to_have_attribute("href", href)
        return row

    def expect_recent_rail_visible(self) -> None:
        """Assert the recent analyses rail shell is visible."""
        expect(self.recent_rail).to_be_visible()
        expect(self.recent_title).to_have_text("Recent Analyses")

    def expect_recent_empty_without_rows(self) -> None:
        """Assert empty recent-history state does not render row links."""
        self.expect_recent_rail_visible()
        expect(self.recent_empty_state).to_be_visible()
        expect(self.recent_rows).to_have_count(0)

    def expect_recent_unavailable_without_rows(self) -> None:
        """Assert unavailable recent-history state does not render row links."""
        self.expect_recent_rail_visible()
        expect(self.recent_unavailable_state).to_be_visible()
        expect(self.recent_rows).to_have_count(0)

    def expect_desktop_command_card_dominates_recent_rail(self) -> None:
        """Assert desktop workbench keeps the paste command card visually primary."""
        self.expect_command_surface_visible()
        self.expect_recent_rail_visible()
        command_box = self.command_card.bounding_box()
        rail_box = self.recent_rail.bounding_box()
        assert command_box is not None
        assert rail_box is not None

        assert command_box["x"] < rail_box["x"], "Recent rail should sit after the command card on desktop"
        assert command_box["width"] >= rail_box["width"] * 2.2, (
            f"Command card should remain dominant, got command={command_box['width']}px "
            f"rail={rail_box['width']}px"
        )
        assert abs(command_box["y"] - rail_box["y"]) <= 24, "Desktop rail should align with the command card top"

    def expect_mobile_recent_rail_stacks_below_command_card(self, viewport_width: int) -> None:
        """Assert mobile layout places recent history below the paste command card without overflow."""
        self.expect_command_surface_visible()
        self.expect_recent_rail_visible()
        command_box = self.command_card.bounding_box()
        rail_box = self.recent_rail.bounding_box()
        assert command_box is not None
        assert rail_box is not None

        assert rail_box["y"] >= command_box["y"] + command_box["height"] - 1, (
            "Recent rail should stack below the command card on mobile"
        )
        assert 0 <= rail_box["x"] <= 12
        assert rail_box["width"] <= viewport_width
        self.expect_no_horizontal_overflow()
