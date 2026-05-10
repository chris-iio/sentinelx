"""E2E test fixtures — live Flask server + Playwright browser.

Spins up SentinelX on an ephemeral port in a daemon thread so Playwright
can interact with the real application (CSRF enabled, security headers active).

The config_store module-level CONFIG_PATH is patched to a temp directory so
E2E tests that save API keys don't touch the real ~/.sentinelx/config.ini.
"""

import itertools
import socket
import threading
import time
from collections.abc import Callable

import pytest

# Guard: skip all e2e tests if Playwright is not fully installed
pytest.importorskip("playwright.sync_api", reason="Playwright not installed")

from werkzeug.serving import make_server

import app.enrichment.config_store as _config_store_mod
import app.enrichment.history_store as _history_store_mod
import app.routes.analysis as _analysis_routes
from app import create_app
from app.enrichment.history_store import HistoryStore

_MOCKED_ONLINE_JOB_PREFIX = "e2e-mocked-online-"
_mocked_online_job_ids: list[str] = []
_mocked_online_job_counter = itertools.count(1)
_mocked_online_job_lock = threading.Lock()
_e2e_history_store: HistoryStore | None = None


def _clear_mocked_online_jobs() -> None:
    """Drop any queued deterministic E2E job ids between tests."""
    with _mocked_online_job_lock:
        _mocked_online_job_ids.clear()


def _arm_mocked_online_job() -> str:
    """Queue the next deterministic job id consumed by the E2E-only seam."""
    with _mocked_online_job_lock:
        job_id = f"{_MOCKED_ONLINE_JOB_PREFIX}{next(_mocked_online_job_counter):04d}"
        _mocked_online_job_ids.append(job_id)
        return job_id


def _consume_mocked_online_job() -> str | None:
    """Return the next deterministic E2E job id, if one has been armed."""
    with _mocked_online_job_lock:
        if not _mocked_online_job_ids:
            return None
        return _mocked_online_job_ids.pop(0)


def _require_e2e_history_store() -> HistoryStore:
    """Return the live-server temp HistoryStore or fail loudly if unavailable."""
    if _e2e_history_store is None:
        raise RuntimeError("E2E history store is not initialized; request live_server first")
    return _e2e_history_store


def _clear_e2e_history_store() -> None:
    """Remove all deterministic E2E history rows without touching user history."""
    store = _require_e2e_history_store()
    with store._lock:  # noqa: SLF001 - test fixture intentionally resets temp DB state.
        store._conn.execute("DELETE FROM analysis_history")  # noqa: SLF001
        store._conn.commit()  # noqa: SLF001


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
def _isolate_history(tmp_path_factory):
    """Redirect HistoryStore to a temp DB so E2E tests never read real history."""
    original = _history_store_mod.DEFAULT_DB_PATH
    tmp_history = tmp_path_factory.mktemp("sentinelx-history") / "history.db"
    _history_store_mod.DEFAULT_DB_PATH = tmp_history
    yield tmp_history
    _history_store_mod.DEFAULT_DB_PATH = original


@pytest.fixture(autouse=True)
def _reset_mocked_online_jobs():
    """Keep deterministic mocked-online submissions isolated to each test."""
    _clear_mocked_online_jobs()
    yield
    _clear_mocked_online_jobs()


@pytest.fixture(autouse=True)
def _reset_e2e_history(live_server):
    """Keep live-server history deterministic and empty unless a test seeds it."""
    _clear_e2e_history_store()
    yield
    _clear_e2e_history_store()


@pytest.fixture(scope="session")
def live_server(_isolate_config, _isolate_history):
    """Start SentinelX on an ephemeral port for the entire E2E session.

    Yields the base URL (e.g. ``http://127.0.0.1:54321``).
    The server shuts down automatically when the session ends.
    """
    global _e2e_history_store
    real_setup_orchestrator = _analysis_routes._setup_orchestrator

    def _e2e_setup_orchestrator(iocs, text, mode, history_store):
        fake_job_id = _consume_mocked_online_job()
        if fake_job_id is not None:
            return fake_job_id, object(), app.registry
        return real_setup_orchestrator(iocs, text, mode, history_store)

    _analysis_routes._setup_orchestrator = _e2e_setup_orchestrator

    port = _find_free_port()
    app = create_app({"TESTING": False, "WTF_CSRF_ENABLED": True, "RATELIMIT_ENABLED": False})
    _e2e_history_store = app.history_store
    server = make_server("127.0.0.1", port, app)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _wait_for_server("127.0.0.1", port)

    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        _analysis_routes._setup_orchestrator = real_setup_orchestrator
        _e2e_history_store = None


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


@pytest.fixture()
def seed_recent_analysis(live_server: str) -> Callable[..., str]:
    """Seed one deterministic recent analysis in the live server's temp history DB."""
    store = _require_e2e_history_store()

    def _seed(
        *,
        analysis_id: str = "e2e-recent-analysis",
        input_text: str = "Alert source: 203.0.113.10",
        mode: str = "online",
        verdict: str = "clean",
    ) -> str:
        iocs = [
            {"type": "ipv4", "value": "203.0.113.10", "raw_match": "203.0.113.10"},
        ]
        results = [
            {
                "type": "result",
                "ioc_value": "203.0.113.10",
                "ioc_type": "ipv4",
                "provider": "E2E Provider",
                "verdict": verdict,
                "detection_count": 0,
                "total_engines": 1,
                "scan_date": "2026-04-26T08:30:00Z",
                "raw_stats": {},
            },
        ]
        return store.save_analysis(
            input_text=input_text,
            mode=mode,
            iocs=iocs,
            results=results,
            analysis_id=analysis_id,
        )

    return _seed


@pytest.fixture()
def e2e_history_store(live_server: str) -> HistoryStore:
    """Expose the live server's temp HistoryStore for fault-injection tests."""
    return _require_e2e_history_store()


# ---------------------------------------------------------------------------
# Enrichment route-mocking helpers
# ---------------------------------------------------------------------------

EMAILREP_E2E_EMAIL = "analyst@example.com"

#: Canned enrichment response for a single Email IOC (analyst@example.com / email).
#: One EmailRep provider result + complete: true so browser tests can exercise
#: the real online form/results/polling path without a live EmailRep key.
#: Includes safe-rendering sentinels: a script-like scalar/list value on allowed
#: fields and an unsupported nested object under an unknown key.
MOCK_ENRICHMENT_RESPONSE_EMAILREP = {
    "total": 1,
    "done": 1,
    "complete": True,
    "next_since": 1,
    "results": [
        {
            "type": "result",
            "ioc_value": EMAILREP_E2E_EMAIL,
            "ioc_type": "email",
            "provider": "EmailRep",
            "verdict": "suspicious",
            "detection_count": 2,
            "total_engines": 1,
            "scan_date": "2026-04-26T09:15:00Z",
            "raw_stats": {
                "reputation": "medium <script>alert('emailrep')</script>",
                "references": 7,
                "risk_flags": [
                    "suspicious",
                    "credentials_leak",
                    "<script>alert('risk')</script>",
                ],
                "domain_reputation": "low",
                "profiles": ["github", "gravatar"],
                "first_seen": "2024-01-15",
                "last_seen": "2026-04-25",
                "deliverable": True,
                "valid_mx": True,
                "spoofable": False,
                "spf_strict": True,
                "dmarc_enforced": False,
                "unsupported_nested_object": {
                    "should_not_render": "<img src=x onerror=alert('nested')>",
                },
            },
        },
    ],
}


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


def setup_enrichment_route_mock(page, response_body: dict | None = None) -> str:
    """Intercept ``**/enrichment/status/*`` and arm a deterministic fake job id.

    Call this **before** navigating to the results page (or before submit) so that
    the Playwright route handler is registered before enrichment.ts fires its first
    ``fetch()`` poll.

    The helper also queues a deterministic ``data-job-id`` for the live Flask app's
    online results page so mocked browser tests do not submit real background
    enrichment work while still exercising the real form POST, CSRF, security
    headers, and HTML contract.

    Args:
        page: The Playwright ``Page`` instance.
        response_body: Optional dict to return as JSON. Defaults to
            :data:`MOCK_ENRICHMENT_RESPONSE_8888` (one IP, two providers, complete).

    Returns:
        The deterministic fake job id rendered into ``.page-results[data-job-id]``.
    """
    import json

    body = response_body if response_body is not None else MOCK_ENRICHMENT_RESPONSE_8888
    fake_job_id = _arm_mocked_online_job()

    page.route(
        "**/enrichment/status/**",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(body),
        ),
    )

    return fake_job_id


def setup_emailrep_enrichment_route_mock(page, email: str = EMAILREP_E2E_EMAIL) -> str:
    """Intercept enrichment status polling with a single EmailRep email result.

    Mirrors :func:`setup_enrichment_route_mock`: call before online submit so the
    route is registered before the first polling request, and returns the fake job
    id rendered into ``.page-results[data-job-id]``. The response body is copied so
    callers can change the submitted email without mutating the canned fixture.
    """
    import copy

    body = copy.deepcopy(MOCK_ENRICHMENT_RESPONSE_EMAILREP)
    body["results"][0]["ioc_value"] = email
    return setup_enrichment_route_mock(page, body)


@pytest.fixture()
def mocked_enrichment(page):
    """Fixture that pre-registers the enrichment route mock on *page*.

    Tests can use this fixture directly; the mock is active for the entire test.
    The route intercepts ``**/enrichment/status/**`` and returns a canned single-IP
    response with ``complete: true``.
    """
    setup_enrichment_route_mock(page)
    return page
