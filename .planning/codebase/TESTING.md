# Testing Patterns

**Analysis Date:** 2026-04-06

## Test Framework

**Runner:**
- `pytest` (configured in `pyproject.toml` with `testpaths = ["tests"]`)
- Test discovery: Files matching `test_*.py` and `*_test.py` in `tests/` directory
- Run all tests: `pytest` (or `make test` if Makefile configured)
- Run specific file: `pytest tests/test_orchestrator.py`
- Run non-E2E tests: `pytest -m 'not e2e'` (excludes browser tests)
- Run E2E only: `pytest -m 'e2e'`

**Assertion Library:**
- `pytest` assertions (`assert` statements)
- TypeScript: `jest`/`expect` compatible (uses `describe()` and `it()` in `.test.ts` files)

**Test Markers:**
- `@pytest.mark.e2e` automatically applied to all tests in `tests/e2e/` (via `pytest_collection_modifyitems` hook in `conftest.py` line 32)

## Test File Organization

**Location:**
- Python: `tests/` mirror of app structure (test files co-located by feature, not type)
  - `tests/test_api.py` tests `app/routes/api.py`
  - `tests/test_orchestrator.py` tests `app/enrichment/orchestrator.py`
  - `tests/test_adapter_contract.py` tests all adapter protocol compliance
  - `tests/e2e/` for browser-based end-to-end tests
- TypeScript: `.test.ts` suffix in same directory as source (e.g., `verdict-compute.test.ts` next to `verdict-compute.ts`)

**Naming:**
- Unit/integration: `test_{module}.py` (e.g., `test_extractor.py`, `test_settings.py`)
- E2E test files: `test_{feature}.py` (e.g., `test_results_page.py`, `test_extraction.py`)
- Page object models: `tests/e2e/pages/{page_name}.py` (e.g., `results_page.py`, `index_page.py`)

## Test Structure

**Suite Organization (Python):**
Tests are organized in classes by feature or responsibility:

```python
"""Module docstring explaining what is tested."""

from unittest.mock import MagicMock, patch
import pytest

class TestApiAnalyzeValidation:
    """Input validation for POST /api/analyze."""

    def test_no_json_body(self, client):
        resp = client.post("/api/analyze", data="not json")
        assert resp.status_code == 400

    def test_empty_text(self, client):
        resp = client.post("/api/analyze", json={"text": ""})
        assert resp.status_code == 400
```

**Patterns:**
- **Setup:** Fixtures provide pre-configured dependencies (e.g., `client` fixture creates Flask test client with CSRF disabled)
- **Arrange-Act-Assert:** Most tests follow AAA pattern — setup state, call function, assert results
- **Helper functions:** Private functions in same file (prefixed with `_`) or shared helpers in `tests/helpers.py`
- **Teardown:** Not explicitly needed in most tests; Flask test_client context handles cleanup (fixture uses `with app.test_client() as c: yield c`)

## Test Types

**Unit Tests:**
- Scope: Single function or pure logic (e.g., `TestClassifyIPv4` tests IOC classification)
- Example: `tests/test_classifier.py` tests every IOC type classification with positive/negative cases
- Files: `tests/test_*.py` (e.g., `test_extractor.py`, `test_orchestrator.py`)
- Pattern: Direct function calls, no HTTP or threading needed
- Mock usage: `MagicMock()` for dependencies that are not the focus (e.g., mock adapter in orchestrator tests)

**Integration Tests:**
- Scope: Multi-layer interactions (Flask routes + mock providers, orchestrator + cache, etc.)
- Example: `tests/test_api.py::TestApiAnalyzeOffline` tests extraction + JSON serialization via Flask
- Files: Same `test_*.py` files (no separation by type)
- Pattern: Real Flask client making actual requests, mocked external calls
- Mock usage: Mock HTTP adapters via `unittest.mock.patch()`, keep database/cache real or mocked consistently

**E2E Tests:**
- Scope: Critical user flows in a real browser (Playwright)
- Example: `tests/e2e/test_results_page.py` tests filter bar, search, verdict display in Firefox/Chrome/Safari
- Files: `tests/e2e/test_*.py` with corresponding page objects in `tests/e2e/pages/`
- Framework: **Playwright** (sync API via `pytest-playwright` plugin)
- Pattern: 
  1. Start live Flask server (fixture `live_server` in `conftest.py`)
  2. Navigate page, interact with UI
  3. Assert DOM state and visual behavior
- Marker: All E2E tests automatically get `@pytest.mark.e2e` (skip with `-m 'not e2e'`)

## Test Structure Details

**Fixtures (Python):**
Located in `tests/conftest.py`:

```python
@pytest.fixture()
def app():
    """Create Flask test application with security scaffold active."""
    test_app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SERVER_NAME": "localhost",
    })
    yield test_app

@pytest.fixture()
def client(app):
    """Create Flask test client."""
    return app.test_client()
```

Most tests use `client` fixture for HTTP testing; some tests inject `app` directly for attribute setup (e.g., mocking `app.history_store`).

**E2E Fixtures (Python):**
Located in `tests/e2e/conftest.py`:

```python
@pytest.fixture(scope="session")
def live_server(_isolate_config):
    """Start SentinelX on an ephemeral port for the entire E2E session."""
    port = _find_free_port()
    app = create_app({"TESTING": False, "WTF_CSRF_ENABLED": True, ...})
    server = make_server("127.0.0.1", port, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _wait_for_server("127.0.0.1", port)
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
```

**Page Objects (Python):**
Located in `tests/e2e/pages/`, inherit Playwright Page:

```python
class ResultsPage:
    def __init__(self, page: Page):
        self.page = page
    
    @property
    def filter_bar(self):
        return self.page.locator("[data-testid='filter-bar']")
    
    @property
    def filter_verdict_buttons(self):
        return self.page.locator("[data-testid='verdict-btn']")
```

Encapsulates DOM selectors, reduces brittle hard-coded CSS in test code.

## Mocking

**Framework (Python):**
- `unittest.mock.MagicMock` — primary mocking tool
- `unittest.mock.patch` — decorator or context manager for function/method replacement
- All HTTP calls mocked via `mock_adapter_session()` helper in `tests/helpers.py`

**Patterns:**
```python
# Mock a method return value
mock_adapter.lookup.return_value = _make_result(ioc_ipv4_a)

# Mock with side effect (function to call instead)
mock_adapter.lookup.side_effect = lambda ioc: _make_result(ioc)

# Patch a module function
with patch("app.routes._helpers._enrichment_pool") as mock_pool:
    resp = client.post("/api/analyze", json={"text": "8.8.8.8", "mode": "online"})

# Mock HTTP session
def mock_adapter_session(adapter, *, method="get", response=None):
    adapter._session = MagicMock()
    target = getattr(adapter._session, method)
    target.return_value = response
    return adapter
```

**What to Mock:**
- External HTTP calls (adapters, APIs)
- File I/O (config store, history store)
- Threading primitives (semaphores, locks) — only if testing synchronization logic
- Flask dependencies attached to `app` (e.g., `app.registry`, `app.cache_store`)

**What NOT to Mock:**
- Core business logic (IOC extraction, classification, verdict computation)
- Database operations (use in-memory or test fixtures instead)
- Flask request/response objects (use test client instead)

## Test Data & Factories

**Fixtures and Factories:**
Located in `tests/helpers.py`:

```python
def make_mock_response(status_code: int, body: dict | None = None) -> MagicMock:
    """Build a mock requests.Response with status code and optional JSON body."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if body is not None:
        raw_bytes = json.dumps(body).encode()
        mock_resp.iter_content = MagicMock(return_value=iter([raw_bytes]))
    return mock_resp

def make_ioc(ioc_type: IOCType, value: str) -> IOC:
    """Build an IOC with raw_match equal to value."""
    return IOC(type=ioc_type, value=value, raw_match=value)

def make_ipv4_ioc(value: str = "1.2.3.4") -> IOC:
    return make_ioc(IOCType.IPV4, value)
```

**Location:** `tests/helpers.py` — shared across all adapter tests (10+ test files)

**TypeScript Test Data:**
In-line helper function in `.test.ts` file:

```typescript
function entry(overrides: Partial<VerdictEntry> & Pick<VerdictEntry, "provider" | "verdict">): VerdictEntry {
  return {
    summaryText: "",
    detectionCount: 0,
    totalEngines: 0,
    statText: "",
    ...overrides,
  };
}
```

## Coverage

**Requirements:**
- Minimum 80% line coverage (project standard from user rules)
- View coverage: `pytest --cov=app tests/` (if pytest-cov installed)

**Coverage by Area:**
- Python: ~757 unit/integration tests covering pipeline, enrichment, routes, adapters
- TypeScript: Verdict computation tested (`verdict-compute.test.ts`), DOM interactions tested via E2E
- E2E: 91 tests covering critical user flows (search, filter, settings, copy)

## Common Testing Patterns

**Parallel Execution Testing (with Barrier):**
Tests verify concurrent behavior without race conditions:

```python
def test_enrich_all_parallel_execution(self, mock_adapter):
    """5 IOCs dispatched in parallel — barrier proves all 5 threads run concurrently."""
    iocs = [_make_ioc(IOCType.IPV4, f"10.0.0.{i}") for i in range(5)]
    barrier = threading.Barrier(5, timeout=2)

    def barrier_lookup(ioc):
        barrier.wait()  # blocks until all 5 threads arrive
        return _make_result(ioc)

    mock_adapter.lookup.side_effect = barrier_lookup
    orchestrator = _make_orchestrator(mock_adapter, max_workers=5)
    with patch("app.enrichment.orchestrator.time.sleep"):
        orchestrator.enrich_all("job-parallel", iocs)

    status = orchestrator.get_status("job-parallel")
    assert len(status["results"]) == 5
```

**Async Testing (Playwright E2E):**
E2E tests use async patterns with timeout handling:

```python
def test_filter_bar_renders(page: Page, index_url: str) -> None:
    """Filter bar is visible and contains all required elements."""
    results = _navigate_to_results(page, index_url)
    
    expect(results.filter_bar).to_be_visible()
    expect(results.filter_verdict_buttons).to_have_count(6)
    expect(results.filter_type_pills).to_have_count(4)
```

**Error Testing:**
Test both error conditions and error handling:

```python
class TestApiAnalyzeValidation:
    def test_no_json_body(self, client):
        resp = client.post("/api/analyze", data="not json", content_type="text/plain")
        assert resp.status_code == 400
        assert "must be JSON" in resp.get_json()["error"]

    def test_invalid_mode(self, client):
        resp = client.post("/api/analyze", json={"text": "8.8.8.8", "mode": "turbo"})
        assert resp.status_code == 400
        assert "Invalid mode" in resp.get_json()["error"]
```

**Verdict Computation Testing (TypeScript):**
Pure function tests with clear input/output:

```typescript
describe("computeWorstVerdict", () => {
  it("returns 'no_data' for an empty array", () => {
    expect(computeWorstVerdict([])).toBe("no_data");
  });

  it("returns 'malicious' when it is the worst verdict present", () => {
    const entries: VerdictEntry[] = [
      entry({ provider: "VT", verdict: "malicious" }),
      entry({ provider: "TF", verdict: "clean" }),
    ];
    expect(computeWorstVerdict(entries)).toBe("malicious");
  });
});
```

## Test Execution

**Run Commands:**
```bash
pytest                              # Run all unit/integration + E2E tests
pytest -m 'not e2e'               # Run only unit/integration (skip E2E)
pytest tests/test_api.py           # Run specific test file
pytest tests/test_api.py::TestApiAnalyzeValidation::test_no_json_body  # Single test
pytest -v                          # Verbose output with test names
pytest --tb=short                  # Shorter traceback format
pytest -x                          # Stop on first failure
```

**Parallel E2E Testing:**
E2E tests can run in parallel with `pytest-xdist` (if installed):
```bash
pytest -m 'e2e' -n auto  # Run on all CPU cores
```

## Test Isolation

**Session Fixtures:**
- `live_server` — Flask server started once per test session (scope="session")
- `_isolate_config` — Config path patched to temp directory (prevents test pollution)

**Function Fixtures:**
- `client`, `app` — Fresh Flask app/client per test (scope="function", default)
- `mocked_enrichment` — Route mock on page per test (scope="function")

**Cleanup:**
- Context managers handle cleanup: Flask test client exits context, patches are reverted
- E2E: Page fixtures are automatically fresh from Playwright's browser context management

---

*Testing analysis: 2026-04-06*
