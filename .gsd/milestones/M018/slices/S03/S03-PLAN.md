# S03: App route and analyst affordance

**Goal:** Expose the S02 diagnostic bundle assembler through a supported GET /diagnostics/export Flask route with correct download headers, bounded error handling, and rate limiting; add a nav-accessible analyst download affordance in the UI; prove all route behaviors with route-level tests that replace S02's route-absence guard.
**Demo:** After this, analysts can download a diagnostic export from the app and route tests prove headers, redaction, and error responses.

## Must-Haves

- GET /diagnostics/export returns 200 with Content-Type: application/zip and Content-Disposition: attachment; the response archive contains manifest.json; configured provider secrets are absent from returned bytes; a simulated assembly failure returns a bounded plain-text 500 with no stack trace or secret values; route tests pass alongside the existing 20-test assembler/source/integration suite and 51-test redaction/config/settings suite.

## Proof Level

- This slice proves: contract — route tests assert response headers, archive content, redaction, and bounded error behavior using the Flask test client with injected stores

## Integration Closure

Route registers on the existing main blueprint; imports build_default_diagnostic_sources and assemble_diagnostic_bundle from app/diagnostics; reads current_app.config_store/cache_store/history_store; rate-limited via the shared limiter; nav link in base.html uses url_for('main.diagnostics_export'); S02 route-absence assertions in test_diagnostic_export_bundle_integration.py are replaced by positive route tests in the new test file.

## Verification

- Route logs assembly errors at ERROR level with exc info (no secrets in log message); X-Diagnostic-Sources response header carries the source count from the manifest summary for easy curl inspection; manifest.json inside the archive provides full per-source outcome inventory.

## Tasks

- [x] **T01: Add diagnostic export route and nav affordance** `est:45m`
  Create app/routes/diagnostics.py with a GET /diagnostics/export route on the main blueprint. The route must: (1) instantiate ConfigStore(), read current_app.cache_store and current_app.history_store, call build_default_diagnostic_sources() with those runtime objects; (2) call assemble_diagnostic_bundle(sources, generated_at=..., config_store=config_store) with a UTC ISO timestamp; (3) return ZIP bytes with Content-Type: application/zip, Content-Disposition: attachment; filename="sentinelx-diagnostic-YYYY-MM-DD.zip", and X-Diagnostic-Sources: <count> headers; (4) on any exception from assemble_diagnostic_bundle, log at ERROR level (message only, no exc repr that could contain secrets) and return a plain-text 500 reading 'Diagnostic export failed. Check server logs.' with no stack trace or internal detail; (5) apply @limiter.limit('3 per minute'). Register the new module in app/routes/__init__.py via 'from . import diagnostics'. Add a nav download link to app/templates/base.html in the floating-settings nav, pointing to url_for('main.diagnostics_export') with aria-label='Download diagnostic export'.
  - Files: `app/routes/diagnostics.py`, `app/routes/__init__.py`, `app/templates/base.html`
  - Verify: python3 -c "from app import create_app; app = create_app(); rules = [r.rule for r in app.url_map.iter_rules()]; assert '/diagnostics/export' in rules, f'route missing: {rules}'" && python3 -m py_compile app/routes/diagnostics.py && grep 'diagnostics' app/routes/__init__.py && grep 'diagnostics_export' app/templates/base.html

- [ ] **T02: Route tests: headers, archive content, redaction, and bounded errors** `est:50m`
  Create tests/test_diagnostic_export_route.py with Flask test-client route tests. Use create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False}) and inject a fake ConfigStore (or use the real one with no secrets configured). Tests must cover: (1) GET /diagnostics/export returns 200 with Content-Type application/zip and Content-Disposition header containing 'attachment' and a .zip filename; (2) the response body is a valid ZIP archive containing manifest.json; (3) no configured provider secret values appear in the raw archive bytes (use a patched ConfigStore that returns a known test-only secret and assert it is absent); (4) patching assemble_diagnostic_bundle to raise RuntimeError causes the route to return 500 with Content-Type text/plain and body containing 'Diagnostic export failed' but not the exception message or any stack trace text; (5) X-Diagnostic-Sources header is present and numeric. Also update tests/test_diagnostic_export_bundle_integration.py to remove or replace the route-absence assertions (the negative guard is now superseded by the positive route tests); the rest of the integration suite must still pass. Run: python3 -m pytest tests/test_diagnostic_export_route.py tests/test_diagnostic_export_bundle_integration.py tests/test_diagnostic_export_assembler.py tests/test_diagnostic_export_sources.py -q
  - Files: `tests/test_diagnostic_export_route.py`, `tests/test_diagnostic_export_bundle_integration.py`
  - Verify: python3 -m pytest tests/test_diagnostic_export_route.py tests/test_diagnostic_export_bundle_integration.py tests/test_diagnostic_export_assembler.py tests/test_diagnostic_export_sources.py -q 2>&1 | tail -5

## Files Likely Touched

- app/routes/diagnostics.py
- app/routes/__init__.py
- app/templates/base.html
- tests/test_diagnostic_export_route.py
- tests/test_diagnostic_export_bundle_integration.py
