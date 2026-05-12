---
id: T01
parent: S03
milestone: M018
key_files:
  - app/routes/diagnostics.py
  - app/routes/__init__.py
  - app/templates/base.html
  - app/templates/macros/icons.html
  - tests/test_diagnostic_export_route.py
  - tests/test_diagnostic_export_bundle_integration.py
  - tests/test_diagnostic_export_primitives.py
key_decisions:
  - Use the existing shared `main` blueprint and endpoint name `diagnostics_export` so templates can call `url_for('main.diagnostics_export')`.
  - Expose only a non-secret fixed error message to analysts while preserving server-side stack context with `exc_info=True`.
  - Keep `/api/diagnostics/export` absent; this slice adds only the supported browser/download route.
duration: 
verification_result: passed
completed_at: 2026-05-12T09:53:01.818Z
blocker_discovered: false
---

# T01: Added a rate-limited `/diagnostics/export` Flask download route and nav link for analyst diagnostic bundles.

**Added a rate-limited `/diagnostics/export` Flask download route and nav link for analyst diagnostic bundles.**

## What Happened

Created `app/routes/diagnostics.py` on the shared `main` blueprint. The route instantiates `ConfigStore`, uses `current_app.cache_store` and `current_app.history_store`, builds default diagnostic sources with a shared UTC Zulu timestamp, assembles the diagnostic bundle, and returns ZIP bytes with `application/zip`, attachment filename, and `X-Diagnostic-Sources` headers. Assembly failures are logged at ERROR with `exc_info=True` using a fixed non-secret message and return the bounded plain-text 500 body. Registered the route module in `app/routes/__init__.py`, added a floating-settings nav link using `url_for('main.diagnostics_export')`, and added the missing `arrow-down-tray` icon branch so the visible affordance renders. Replaced prior route-absence tests with supported-route assertions and added route-level tests covering rendered nav link, ZIP headers, manifest source-count header, payload redaction, bounded error response/logging, and the 3-per-minute limiter.

## Verification

Verified the route is registered, the route module compiles, blueprint/template references exist, focused route tests pass, and the full diagnostic export test family remains green. Tests also exercise `GET /` for the nav affordance and `GET /diagnostics/export` for success, error, and rate-limit behavior.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/test_diagnostic_export_route.py tests/test_diagnostic_export_bundle_integration.py::test_diagnostic_export_route_is_registered_for_supported_app_slice tests/test_diagnostic_export_primitives.py::test_flask_exposes_supported_diagnostic_export_route
python3 -c "from app import create_app; app = create_app(); rules = [r.rule for r in app.url_map.iter_rules()]; assert '/diagnostics/export' in rules, f'route missing: {rules}'" && python3 -m py_compile app/routes/diagnostics.py && grep 'diagnostics' app/routes/__init__.py && grep 'diagnostics_export' app/templates/base.html` | 0 | ✅ pass | 796ms |
| 2 | `python3 -m pytest tests/test_diagnostic_export_route.py tests/test_diagnostic_export_sources.py tests/test_diagnostic_export_bundle_integration.py tests/test_diagnostic_export_primitives.py tests/test_diagnostic_export_contract.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_assembler.py` | 0 | ✅ pass | 522ms |

## Deviations

Added route-level tests and updated two prior route-absence guards as required by the slice contract; also added the missing `arrow-down-tray` icon branch so the planned nav affordance renders visibly instead of an empty SVG.

## Known Issues

None.

## Files Created/Modified

- `app/routes/diagnostics.py`
- `app/routes/__init__.py`
- `app/templates/base.html`
- `app/templates/macros/icons.html`
- `tests/test_diagnostic_export_route.py`
- `tests/test_diagnostic_export_bundle_integration.py`
- `tests/test_diagnostic_export_primitives.py`
