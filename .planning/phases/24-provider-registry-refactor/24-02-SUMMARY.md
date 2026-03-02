---
phase: 24-provider-registry-refactor
plan: 02
subsystem: api
tags: [python, flask, registry, typescript, tdd, setup-factory]

# Dependency graph
requires:
  - 24-01 (Provider protocol, ProviderRegistry, ConfigStore multi-provider)
provides:
  - build_registry() factory at app/enrichment/setup.py — single provider registration point
  - Routes wired to registry — zero hardcoded adapter imports in routes.py
  - data-provider-counts DOM attribute on .page-results for dynamic TS provider counts
  - getProviderCounts() TypeScript function reading DOM attribute with hardcoded fallback
affects:
  - 24-03 (Settings page will display provider status from registry)
  - 25-shodan (new adapter added to setup.py only — zero other file changes)
  - 26-free-key-providers (same: setup.py is the only file to touch)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Setup factory pattern: build_registry() as the single provider registration point
    - DOM-injected configuration: Flask passes registry counts as JSON in data attribute
    - Graceful TypeScript fallback: getProviderCounts() falls back to hardcoded defaults on parse error

key-files:
  created:
    - app/enrichment/setup.py
    - tests/test_registry_setup.py
  modified:
    - app/routes.py
    - app/templates/results.html
    - app/static/src/ts/types/ioc.ts
    - app/static/src/ts/modules/enrichment.ts
    - app/static/dist/main.js
    - tests/test_routes.py

key-decisions:
  - "build_registry() takes allowed_hosts + config_store as args — no global state, fully testable"
  - "provider_counts serialized as JSON in Flask route, HTML-escaped by Jinja2 autoescaping for safe attribute value"
  - "getProviderCounts() falls back silently on JSON parse error — pending indicator degrades gracefully"
  - "IOC_PROVIDER_COUNTS made private (_defaultProviderCounts) — callers must use getProviderCounts() for runtime accuracy"
  - "IocType import removed from enrichment.ts — no longer needed after IOC_PROVIDER_COUNTS cast removal"

patterns-established:
  - "Single registration point: add new provider to setup.py only — routes, orchestrator, templates unchanged"
  - "Registry-driven online mode guard: registry.configured() replaces VT-key-only check"
  - "DOM-injected runtime config: Flask passes dynamic values via data-* attributes, TS reads them"

requirements-completed: [REG-03, REG-05]

# Metrics
duration: 5min
completed: 2026-03-02
---

# Phase 24 Plan 02: Provider Setup Module + Route Wiring Summary

**build_registry() factory wires ProviderRegistry into Flask routes — adding a provider now requires only one register() call in setup.py, with zero changes to routes, orchestrator, or templates**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-02T11:37:28Z
- **Completed:** 2026-03-02T11:42:23Z
- **Tasks:** 2
- **Files modified:** 8 (2 created, 6 modified)

## Accomplishments

- `app/enrichment/setup.py` created with `build_registry()` — the single place where all three providers are instantiated and registered into a `ProviderRegistry`
- `app/routes.py` fully refactored: no hardcoded adapter imports, online mode guard now checks `registry.configured()` (not VT key alone), `enrichable_count` computed from `registry.providers_for_type()` per IOC
- `results.html` gains `data-provider-counts` attribute in online mode — JSON string of `{ioc_type: count}` for all non-CVE types
- `ioc.ts` replaces exported `IOC_PROVIDER_COUNTS` constant with private `_defaultProviderCounts` and new exported `getProviderCounts()` that reads from the DOM with graceful fallback
- `enrichment.ts` updated: `getProviderCounts()` call in `updatePendingIndicator()`, `IocType` import removed (no longer needed)
- TypeScript bundle rebuilt — `make typecheck` and `make js` both pass
- 9 new tests in `tests/test_registry_setup.py`, 6 route tests updated to mock `build_registry` instead of individual adapters — all 276 non-E2E tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Setup Factory + Route Wiring + Test Updates** - `affa65c` (feat)
2. **Task 2: Dynamic Provider Counts (Template + TypeScript)** - `3a18781` (feat)

_Note: Task 1 followed TDD pattern (RED: test_registry_setup.py failing → GREEN: setup.py created)_

## Files Created/Modified

- `app/enrichment/setup.py` - build_registry() factory — VTAdapter, MBAdapter, TFAdapter registered
- `app/routes.py` - Removed 3 adapter imports, added build_registry import + IOCType; refactored analyze() online block
- `app/templates/results.html` - Added data-provider-counts="{{ provider_counts }}" to .page-results div
- `app/static/src/ts/types/ioc.ts` - IOC_PROVIDER_COUNTS → private _defaultProviderCounts + exported getProviderCounts()
- `app/static/src/ts/modules/enrichment.ts` - Import getProviderCounts, call in updatePendingIndicator()
- `app/static/dist/main.js` - Rebuilt TypeScript bundle
- `tests/test_registry_setup.py` - 9 tests for build_registry() (protocol conformance, key handling)
- `tests/test_routes.py` - 6 online-mode tests updated to mock app.routes.build_registry

## Decisions Made

- `build_registry()` receives `allowed_hosts` and `config_store` as parameters — avoids global state, keeps the factory pure and fully testable in isolation
- `provider_counts` passed as JSON string from Flask route (not as a template dict) — Jinja2 autoescaping handles HTML-encoding of quotes in the attribute value without requiring `| tojson` filter
- `getProviderCounts()` uses try/catch on `JSON.parse()` and returns `_defaultProviderCounts` on any error — the pending-indicator degrades gracefully rather than throwing
- `IOC_PROVIDER_COUNTS` made private rather than removed — the constant still has value as a well-typed fallback, removing the export breaks the public API surface cleanly

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

6 pre-existing E2E test failures (Playwright) — same failures as in Plan 01, unrelated to this plan. All 276 non-E2E tests pass.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 24 Plan 03 can add settings page provider-status display using `registry.all()` and `registry.configured()`
- Phase 25 (Shodan InternetDB) only needs: create `app/enrichment/adapters/shodan.py` + add one `registry.register()` call in `setup.py`
- Zero changes required in routes.py, orchestrator.py, templates, or TypeScript for any new provider

## Self-Check: PASSED

- app/enrichment/setup.py: FOUND
- tests/test_registry_setup.py: FOUND
- 24-02-SUMMARY.md: FOUND
- Commit affa65c: FOUND
- Commit 3a18781: FOUND

---
*Phase: 24-provider-registry-refactor*
*Completed: 2026-03-02*
