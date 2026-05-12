---
id: S03
parent: M018
milestone: M018
provides:
  - A supported GET `/diagnostics/export` route for S04's end-to-end download proof.
  - A nav-accessible analyst affordance for generating diagnostic bundles.
  - Route-level regression tests proving headers, ZIP content, redaction, bounded errors, and rate limiting.
requires:
  - slice: S02
    provides: Diagnostic source construction, bundle assembly, manifest, bounds, and redaction semantics consumed by the app route.
affects:
  - S04
key_files:
  - app/routes/diagnostics.py
  - app/routes/__init__.py
  - app/templates/base.html
  - tests/test_diagnostic_export_route.py
  - tests/test_diagnostic_export_bundle_integration.py
key_decisions:
  - Expose diagnostic export on the existing shared `main` blueprint rather than creating a separate API namespace.
  - Use `url_for('main.diagnostics_export')` from the nav affordance to keep UI wiring tied to the registered Flask endpoint.
  - Return a bounded plain-text 500 for assembly failures while preserving ERROR-level server logging for diagnosis.
  - Keep `/api/diagnostics/export` unsupported and covered by integration tests as a route-shape guardrail.
patterns_established:
  - Route-level tests exercise the public Flask test-client surface instead of duplicating assembler internals.
  - Download routes expose lightweight operational headers (`X-Diagnostic-Sources`) while detailed source outcomes live in the bundle manifest.
  - Failure responses for diagnostic tooling must be safe to show analysts and must not echo exception text or configured secrets.
observability_surfaces:
  - `X-Diagnostic-Sources` response header for quick source-count inspection.
  - `manifest.json` inside every successful ZIP for full per-source included/omitted/truncated/error inventory.
  - ERROR-level server log on assembly failures with a secret-free message and exception context.
drill_down_paths:
  - .gsd/milestones/M018/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M018/slices/S03/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-05-12T10:15:13.591Z
blocker_discovered: false
---

# S03: App route and analyst affordance

**Exposed the S02 diagnostic bundle assembler through a supported, rate-limited `/diagnostics/export` Flask route and nav download affordance with route-level tests for headers, ZIP content, redaction, bounded failures, and source-count observability.**

## What Happened

S03 connected the previously built diagnostic bundle assembler to the local SentinelX application surface. T01 added `app/routes/diagnostics.py` on the existing `main` blueprint, registered it through `app/routes/__init__.py`, and added a floating-settings nav link in `app/templates/base.html` using `url_for('main.diagnostics_export')`. The route instantiates `ConfigStore`, uses the runtime cache/history stores from `current_app`, builds default diagnostic sources, assembles a UTC-stamped ZIP bundle, and returns it as an attachment named `sentinelx-diagnostic-YYYY-MM-DD.zip` with `Content-Type: application/zip` and `X-Diagnostic-Sources` for quick curl inspection. It is rate-limited at `3 per minute` and converts assembly exceptions into a bounded plain-text 500 while logging an ERROR-level server-side diagnostic message.

T02 verified the route at the Flask test-client boundary. `tests/test_diagnostic_export_route.py` proves successful download headers, ZIP validity, `manifest.json` presence, source-count header parity with the manifest, configured-provider-secret absence from raw archive bytes, bounded text/plain failure responses that omit exception details/tracebacks/secrets, ERROR logging with exception context, nav link exposure, and rate limiting. `tests/test_diagnostic_export_bundle_integration.py` now keeps a positive registration assertion for `/diagnostics/export` while preserving the unsupported `/api/diagnostics/export` absence guard. No closer source edits were required; closeout only refreshed verification evidence and recorded reusable diagnostic-route patterns.

## Verification

Fresh closeout verification passed through `gsd_exec`.

### Observable Truths
| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `/diagnostics/export` is registered on the app | ✓ PASS | `python3 -c "from app import create_app; ... assert '/diagnostics/export' in rules"` exited 0 in gsd_exec `e8e6fd70-980f-4e8b-8684-ebfa3f44c523`. |
| 2 | Route module compiles and is imported | ✓ PASS | `python3 -m py_compile app/routes/diagnostics.py` plus `grep 'diagnostics' app/routes/__init__.py` exited 0. |
| 3 | Analyst nav affordance is wired to the supported route | ✓ PASS | `grep 'diagnostics_export' app/templates/base.html` found the nav link with `url_for('main.diagnostics_export')` and `aria-label="Download diagnostic export"`. |
| 4 | Route, assembler, source, integration, redaction, config, and settings coverage all passes together | ✓ PASS | `python3 -m pytest tests/test_diagnostic_export_route.py tests/test_diagnostic_export_bundle_integration.py tests/test_diagnostic_export_assembler.py tests/test_diagnostic_export_sources.py tests/test_config_store.py tests/test_diagnostic_redaction.py tests/test_emailrep_registry_settings.py tests/test_settings.py -q` exited 0 with `88 passed in 0.59s` in gsd_exec `2a7ffbc0-b1cd-4fae-914c-f1e35b99bac0`. |
| 5 | Route tests prove headers, archive content, redaction, bounded errors, source header, logging, nav, and rate limiting | ✓ PASS | Included in the 88-test closeout run; T02's prescribed diagnostic export subset previously reported 23 passing tests. |

### Artifacts
- `app/routes/diagnostics.py` — GET `/diagnostics/export` route implementation, ZIP response headers, source-count header, bounded failure response, and limiter decoration.
- `app/routes/__init__.py` — imports the diagnostics route module into the existing `main` blueprint registration flow.
- `app/templates/base.html` — nav-accessible diagnostic download link.
- `tests/test_diagnostic_export_route.py` — positive and failure-path Flask route tests.
- `tests/test_diagnostic_export_bundle_integration.py` — positive supported-route registration plus unsupported `/api` absence guard.

### Key Links
- `app/routes/diagnostics.py` → `app/diagnostics/sources.py` via `build_default_diagnostic_sources(...)`.
- `app/routes/diagnostics.py` → `app/diagnostics/assembler.py` via `assemble_diagnostic_bundle(...)`.
- `app/routes/diagnostics.py` → app runtime stores via `current_app.cache_store` and `current_app.history_store`.
- `app/templates/base.html` → route via `url_for('main.diagnostics_export')`.

### Operational Readiness
- Health signal: Successful route responses include `X-Diagnostic-Sources` and a manifest inventory inside the archive.
- Failure signal: Assembly failures log at ERROR level with exception context and return a bounded user-safe 500.
- Recovery procedure: Operators can check server logs after the bounded response; analysts can retry after the rate-limit window or after source/store issues are resolved.
- Monitoring gaps: No external telemetry or long-term log shipping is added by design; this remains local-first and is expected to be completed by S04's end-to-end proof and analyst documentation.

## Requirements Advanced

- R083 — S03 advanced the diagnostic export requirement by making the redacted diagnostic bundle downloadable from the local app and by proving route headers, manifest presence, configured-secret absence, bounded failure responses, and rate limiting with Flask route tests.

## Requirements Validated

None.

## New Requirements Surfaced

- None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

None.

## Deviations

None during closeout. T02 noted that the route test file already existed before its execution pass, so the executor inspected and verified it rather than rewriting it.

## Known Limitations

S03 proves the supported route and UI affordance at route/test-client level. Browser-level deterministic download inspection and analyst-facing sharing documentation are intentionally deferred to S04.

## Follow-ups

S04 should add the deterministic app-level proof that downloads and inspects the log bundle, then document safe sharing guidance, limits, and expected troubleshooting workflow.

## Files Created/Modified

- `app/routes/diagnostics.py` — Adds the rate-limited diagnostic export route, bundle assembly call, download headers, source-count header, and bounded error response.
- `app/routes/__init__.py` — Imports the diagnostics route module so the route registers on the existing main blueprint.
- `app/templates/base.html` — Adds the analyst-facing diagnostic export nav link.
- `tests/test_diagnostic_export_route.py` — Covers successful route downloads, ZIP manifest content, redaction, bounded failure behavior, logging, nav link, source-count header, and rate limiting.
- `tests/test_diagnostic_export_bundle_integration.py` — Replaces the old route-absence guard with positive supported-route registration while retaining unsupported API route absence.
