"""E2E test fixtures — live Flask server + Playwright browser.

Spins up SentinelX on an ephemeral port in a daemon thread so Playwright
can interact with the real application (CSRF enabled, security headers active).
"""

import socket
import threading
import time

import pytest
from werkzeug.serving import make_server

from app import create_app


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
def live_server():
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
def analyze_url(live_server: str) -> str:
    """URL for the analyze endpoint."""
    return live_server + "/analyze"
