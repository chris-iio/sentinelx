---
phase: 19-build-pipeline-infrastructure
plan: 02
subsystem: infra
tags: [esbuild, typescript, flask, base.html, csp, iife, build-pipeline]

# Dependency graph
requires:
  - phase: 19-01
    provides: esbuild binary, JS build targets (make js/build), dist/main.js placeholder IIFE bundle
provides:
  - base.html dual-script-tag pattern (dist/main.js placeholder + main.js functionality)
  - Flask serving dist/main.js via url_for static route
  - Verified CSP compatibility of esbuild IIFE output
  - Clean build pipeline: make build produces both CSS and JS artifacts
affects:
  - 20-type-definitions (can now rely on build pipeline being fully wired to template)
  - 21-module-conversion (will compile TypeScript modules into dist/main.js)
  - 22-module-conversion (final phase that removes main.js script tag and deletes original)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Dual-script-tag pattern: dist/main.js (pipeline placeholder) + main.js (real code) until Phase 22
    - CSP-safe IIFE bundle delivery via Flask url_for static file routing

key-files:
  created: []
  modified:
    - app/templates/base.html

key-decisions:
  - "Option A (dual script tags): dist/main.js empty placeholder + main.js real functionality — avoids JS breakage during migration"
  - "dist/main.js already committed from Plan 01 — no separate commit needed in Plan 02"
  - "main.js tag retained until Phase 22 when TypeScript conversion is complete"

patterns-established:
  - "Dual-script-tag migration pattern: add compiled bundle script tag alongside original during incremental migration"

requirements-completed: [BUILD-02, BUILD-06]

# Metrics
duration: 1min
completed: 2026-02-28
---

# Phase 19 Plan 02: Build Pipeline Infrastructure Summary

**Flask base.html wired to serve esbuild IIFE bundle via dual-script-tag pattern, CSP regression verified clean, make build pipeline end-to-end confirmed**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-28T14:20:03Z
- **Completed:** 2026-02-28T14:21:21Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- base.html now serves dist/main.js (empty IIFE placeholder) alongside main.js (real functionality) via dual defer script tags
- CSP test `test_csp_header_exact_match` passes — esbuild IIFE output does not use eval/Function constructor, no CSP regression
- `make build` produces both `dist/style.css` and `dist/main.js` from a clean state; clean rebuild verified by deleting and regenerating
- All 224 unit/integration tests pass without regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Update base.html script tag and verify CSP compliance** - `2e258c8` (feat)
2. **Task 2: Commit dist/main.js bundle and verify full build pipeline** - no additional commit needed (dist/main.js was already committed in 19-01 Task 3 as `4d4ed74`; no files changed)

**Plan metadata:** (docs commit — created after this summary)

## Files Created/Modified

- `app/templates/base.html` — Added dist/main.js script tag before main.js; both use `defer`; dual-tag approach preserves all existing JS functionality while proving build pipeline is wired to the template

## Decisions Made

- **Option A (dual script tags)** chosen over Option B (no template change yet): Adding `dist/main.js` as a no-op empty IIFE alongside `main.js` proves the build pipeline is integrated with the template while preserving all functionality until Phase 22 TypeScript conversion completes.
- **No new commit for Task 2**: `dist/main.js` was already committed in Plan 01 (commit `4d4ed74`). Running `make build` confirms it regenerates cleanly — no additional git operation needed.

## Deviations from Plan

None — plan executed exactly as written. Option A (dual script tags) was specified in the plan and implemented as described.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Build pipeline is fully integrated: Flask serves `dist/main.js` from the template, esbuild produces it via `make build`
- CSP compatibility confirmed — no security regression from the build output
- Phase 20 (type definitions) can proceed with confidence that the pipeline is wired end-to-end
- Phase 22 will remove the `main.js` script tag and delete the original `app/static/main.js` once TypeScript conversion is complete
- No blockers

---
*Phase: 19-build-pipeline-infrastructure*
*Completed: 2026-02-28*
