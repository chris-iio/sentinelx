---
estimated_steps: 5
estimated_files: 4
skills_used:
  - test
  - review
---

# T03: Cache registry at startup with settings refresh hook and migrate route tests

**Slice:** S02 — Connection Pooling & Startup Optimization
**Milestone:** M002

## Description

Deliver R006 by caching the provider registry at app startup and eliminating per-request `build_registry()` calls. `create_app()` builds the registry once and stores it as `app.registry`. `analyze()` reads `current_app.registry` instead of calling `build_registry()`. `settings_post()` rebuilds and replaces the cached registry after saving a key so subsequent enrichments use the new key. Migrate 18 test mocks in `test_routes.py` from `patch("app.routes.build_registry")` to direct `app.registry` assignment.

**This is the highest-risk task** because it changes how routes access the registry, and 18 existing test mocks must be migrated atomically — tests break between the route change and the mock migration.

## Steps

1. **Update `app/__init__.py` (`create_app()`):**
   - After `config.validate()` and before blueprint registration, add:
     ```python
     from app.enrichment.config_store import ConfigStore
     from app.enrichment.setup import build_registry
     config_store = ConfigStore()
     app.registry = build_registry(
         allowed_hosts=app.config["ALLOWED_API_HOSTS"],
         config_store=config_store,
     )
     ```
   - The `app.registry` attribute is set on the Flask app object — accessible via `current_app.registry` in routes
   - **Important:** The registry must be built after `config.validate()` so ALLOWED_API_HOSTS is guaranteed to exist
   - **Important:** Place it before blueprint registration so routes can reference it at import time if needed

2. **Update `app/routes.py`:**
   - In `analyze()`: replace the 4 lines (`config_store = ConfigStore()`, `allowed_hosts = ...`, `registry = build_registry(...)`) with `registry = current_app.registry`
   - Keep `config_store = ConfigStore()` only for the `cache_ttl_hours` read — or move it after the registry read
   - In `settings_post()`: after saving the key (after both the VT and generic code paths), add registry rebuild:
     ```python
     from app.enrichment.setup import build_registry
     allowed_hosts = current_app.config.get("ALLOWED_API_HOSTS", [])
     current_app.registry = build_registry(
         allowed_hosts=allowed_hosts,
         config_store=config_store,
     )
     ```
   - The `build_registry` import at the top of routes.py can be removed from the `analyze()` code path (only needed in `settings_post()` now), but keeping it at module level is fine
   - **Do NOT change** the `PROVIDER_INFO` import — it's still used by `settings_get()`

3. **Migrate 18 test mocks in `tests/test_routes.py`:**
   - Every test that currently does `with patch("app.routes.build_registry") as mock_build_registry:` followed by `mock_build_registry.return_value = mock_registry` should change to:
     ```python
     app.registry = mock_registry
     ```
     where `app` is the test fixture (available via the `client` fixture's `.application` or via the `app` fixture directly)
   - Tests that assert `mock_build_registry.assert_called_once()` or inspect `mock_build_registry.call_args` should be replaced with assertions that verify `current_app.registry` is the expected registry
   - The test for `test_analyze_online_creates_all_three_adapters` asserts `allowed_hosts` was passed to `build_registry` — replace with: verify `app.registry` is the mock_registry (the detail of how it was built is now `create_app`'s responsibility, not `analyze()`'s)
   - **Pattern for each test:**
     - Old: `with patch("app.routes.build_registry") as mock_br: mock_br.return_value = mock_registry; ...`
     - New: `app.registry = mock_registry; ...` (inside the test, before making the POST request, using the `app` fixture)
   - Some tests will need the `app` fixture added to their signature if they only had `client` before. Access via `client.application` or add `app` fixture.

4. **Add registry caching tests to `tests/test_session_pooling.py`:**
   - `test_create_app_sets_registry_attribute`: call `create_app()`, verify `app.registry` exists and is a `ProviderRegistry` with 14 providers
   - `test_settings_post_rebuilds_registry`: create test app, set initial registry, POST to `/settings` with a new key, verify `app.registry` is a new (different-identity) ProviderRegistry
   - `test_analyze_uses_cached_registry`: create test app, set `app.registry` to a mock, POST to `/analyze` in online mode, verify mock registry methods were called (not `build_registry`)

5. **Run the full test suite** to confirm all 924+ tests pass.

## Must-Haves

- [ ] `create_app()` builds registry once and stores as `app.registry`
- [ ] `analyze()` reads `current_app.registry` — does NOT call `build_registry()`
- [ ] `settings_post()` rebuilds registry after saving key
- [ ] All 18 `build_registry` mocks in `test_routes.py` migrated to `app.registry` assignment
- [ ] New tests verify caching and refresh behavior
- [ ] 924+ tests pass

## Verification

- `python3 -m pytest tests/test_routes.py -v` — all 25 route tests pass
- `python3 -m pytest tests/test_session_pooling.py -v` — all session + caching tests pass
- `python3 -m pytest -x -q` — full suite 924+ tests pass
- `grep -c "build_registry" tests/test_routes.py` returns 0 (all mocks migrated)
- `grep -q "app.registry" app/__init__.py` — registry cached at startup
- `grep -q "current_app.registry" app/routes.py` — routes consume cached registry

## Inputs

- `app/__init__.py` — app factory to extend with registry caching
- `app/routes.py` — routes to rewire from `build_registry()` to `current_app.registry`
- `tests/test_routes.py` — 18 `build_registry` mocks to migrate
- `tests/test_session_pooling.py` — test file from T01/T02 to extend with caching tests
- `app/enrichment/setup.py` — `build_registry()` with Session support (from T01/T02)

## Expected Output

- `app/__init__.py` — `create_app()` builds and caches `app.registry`
- `app/routes.py` — `analyze()` reads `current_app.registry`; `settings_post()` rebuilds registry
- `tests/test_routes.py` — all `build_registry` mocks replaced with `app.registry` assignment
- `tests/test_session_pooling.py` — extended with registry caching and refresh tests

## Observability Impact

- **New inspection surface:** `app.registry` attribute on the Flask app object. Inspectable in `flask shell` via `app.registry.all()` (lists all 14 providers) and `app.registry.configured()` (lists key-configured providers).
- **Registry rebuild visibility:** After POST /settings, `id(app.registry)` changes — verifiable in tests or debugging to confirm the rebuild hook fired.
- **Failure state:** If the rebuild hook in `settings_post()` breaks, enrichments will use stale API keys. This surfaces as authentication failures on next enrichment run — visible in adapter-level `EnrichmentError` responses.
- **No new runtime logs or metrics:** Registry caching is transparent to callers. Connection reuse happens via `requests.Session` internals.
