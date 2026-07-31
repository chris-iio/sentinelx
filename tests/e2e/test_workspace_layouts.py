"""Desktop and mobile layout checks for the Flask Audit and CTF workspaces."""

import pytest
from playwright.sync_api import ConsoleMessage, Error, Page, expect

from tests.e2e.conftest import assert_security_headers


@pytest.mark.parametrize("path, heading", (("/audit", "Security engagements"), ("/ctf", "CTF Events")))
@pytest.mark.parametrize("viewport", ((1280, 720), (390, 844)))
def test_workspace_has_no_overflow_or_console_errors(
    page: Page,
    live_server: str,
    path: str,
    heading: str,
    viewport: tuple[int, int],
) -> None:
    """Each Flask workspace stays inside its viewport and satisfies CSP."""
    console_errors: list[str] = []
    page_errors: list[str] = []

    def record_console(message: ConsoleMessage) -> None:
        if message.type == "error":
            console_errors.append(message.text)

    def record_page_error(error: Error) -> None:
        page_errors.append(str(error))

    page.on("console", record_console)
    page.on("pageerror", record_page_error)
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})

    response = page.goto(live_server + path, wait_until="networkidle")

    assert response is not None
    assert response.ok
    assert_security_headers(response.headers)
    expect(page.get_by_role("heading", name=heading, exact=True)).to_be_visible()
    expect(page.get_by_role("link", name="Analyze workspace", exact=True)).to_be_visible()
    expect(page.get_by_role("link", name="Audit workspace", exact=True)).to_be_visible()
    expect(page.get_by_role("link", name="CTF workspace", exact=True)).to_be_visible()

    overflow = page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    assert overflow <= 0, f"{path} overflows {viewport[0]} px viewport by {overflow} px"
    assert console_errors == []
    assert page_errors == []
