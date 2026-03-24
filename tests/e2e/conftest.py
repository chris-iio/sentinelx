"""E2E test fixtures — live Flask server + Playwright browser.

Spins up SentinelX on an ephemeral port in a daemon thread so Playwright
can interact with the real application (CSRF enabled, security headers active).

The config_store module-level CONFIG_PATH is patched to a temp directory so
E2E tests that save API keys don't touch the real ~/.sentinelx/config.ini.
"""

import socket
import threading
import time

import pytest
from werkzeug.serving import make_server

import app.enrichment.config_store as _config_store_mod
from app import create_app


def assert_security_headers(headers: dict) -> None:
    """Assert response includes required security headers (shared across E2E tests)."""
    assert "content-security-policy" in headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "SAMEORIGIN"


def pytest_collection_modifyitems(items: list) -> None:
    """Auto-mark every test in tests/e2e/ with the 'e2e' marker."""
    for item in items:
        if "/e2e/" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)


def _find_free_port() -> int:
    """Bind to port 0 and let the OS assign an ephemeral port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_server(host: str, port: int, timeout: float = 5.0) -> None:
    """Block until the server accepts TCP connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"Server on {host}:{port} did not start within {timeout}s")


@pytest.fixture(scope="session")
def _isolate_config(tmp_path_factory):
    """Redirect ConfigStore to a temp directory so E2E tests never touch real config.

    Patches the module-level CONFIG_PATH before the Flask server starts.
    Since Flask runs in a daemon thread in the same process, all ConfigStore()
    instantiations inside request handlers will pick up the patched path.
    """
    original = _config_store_mod.CONFIG_PATH
    tmp_config = tmp_path_factory.mktemp("sentinelx") / "config.ini"
    _config_store_mod.CONFIG_PATH = tmp_config
    yield tmp_config
    _config_store_mod.CONFIG_PATH = original


@pytest.fixture(scope="session")
def live_server(_isolate_config):
    """Start SentinelX on an ephemeral port for the entire E2E session.

    Yields the base URL (e.g. ``http://127.0.0.1:54321``).
    The server shuts down automatically when the session ends.
    """
    port = _find_free_port()
    app = create_app({"TESTING": False, "WTF_CSRF_ENABLED": True, "RATELIMIT_ENABLED": False})
    server = make_server("127.0.0.1", port, app)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _wait_for_server("127.0.0.1", port)

    yield f"http://127.0.0.1:{port}"

    server.shutdown()


@pytest.fixture(scope="session")
def browser_context_args():
    """Default Playwright browser context settings for all E2E tests."""
    return {
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
    }


@pytest.fixture()
def index_url(live_server: str) -> str:
    """URL for the index page."""
    return live_server + "/"


@pytest.fixture()
def settings_url(live_server: str) -> str:
    """URL for the settings page."""
    return live_server + "/settings"


# ---------------------------------------------------------------------------
# Enrichment route-mocking helpers
# ---------------------------------------------------------------------------

#: Canned enrichment response for a single IP IOC (8.8.8.8 / ipv4).
#: Two provider results + complete: true so enrichment.ts fires the full pipeline
#: including handleProviderResult(), getOrCreateSummaryRow(), and markEnrichmentComplete().
MOCK_ENRICHMENT_RESPONSE_8888 = {
    "total": 2,
    "done": 2,
    "complete": True,
    "next_since": 2,
    "results": [
        {
            "type": "result",
            "ioc_value": "8.8.8.8",
            "ioc_type": "ipv4",
            "provider": "VirusTotal",
            "verdict": "clean",
            "detection_count": 0,
            "total_engines": 70,
            "scan_date": "2026-03-15T12:00:00Z",
            "raw_stats": {},
        },
        {
            "type": "result",
            "ioc_value": "8.8.8.8",
            "ioc_type": "ipv4",
            "provider": "AbuseIPDB",
            "verdict": "clean",
            "detection_count": 0,
            "total_engines": 1,
            "scan_date": "2026-03-15T12:00:00Z",
            "raw_stats": {"abuse_confidence_score": 0},
        },
    ],
}


def setup_enrichment_route_mock(page, response_body: dict | None = None) -> None:
    """Intercept ``**/enrichment/status/*`` and return canned enrichment JSON.

    Call this **before** navigating to the results page (or before submit) so that
    the Playwright route handler is registered before enrichment.ts fires its first
    ``fetch()`` poll.

    Args:
        page: The Playwright ``Page`` instance.
        response_body: Optional dict to return as JSON. Defaults to
            :data:`MOCK_ENRICHMENT_RESPONSE_8888` (one IP, two providers, complete).
    """
    import json

    body = response_body if response_body is not None else MOCK_ENRICHMENT_RESPONSE_8888

    page.route(
        "**/enrichment/status/**",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(body),
        ),
    )


@pytest.fixture()
def mocked_enrichment(page):
    """Fixture that pre-registers the enrichment route mock on *page*.

    Tests can use this fixture directly; the mock is active for the entire test.
    The route intercepts ``**/enrichment/status/**`` and returns a canned single-IP
    response with ``complete: true``.
    """
    setup_enrichment_route_mock(page)
    return page
