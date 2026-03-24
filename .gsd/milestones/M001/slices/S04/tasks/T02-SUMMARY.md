---
id: T02
parent: S04
milestone: M001
provides:
  - Dead code removal of createSectionHeader() confirming complete JS→template migration
  - E2E baseline validation (89 pass, 2 pre-existing fail) with no regressions
key_files:
  - app/static/src/ts/modules/row-factory.ts
  - app/static/dist/main.js
key_decisions:
  - Removed createSectionHeader() entirely — zero call sites remain after T01's template migration
patterns_established:
  - Dead code detection via `make typecheck` — removed exports trigger build errors if still referenced
observability_surfaces:
  - "grep -rn createSectionHeader app/static/src/ts/" returns zero results, confirming migration complete
duration: 2 sessions (recovery)
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: Run E2E suite and clean up dead code

**Removed dead createSectionHeader() from row-factory.ts; E2E suite confirms 89/2 baseline with no regressions from template restructuring**

## What Happened

Ran the full E2E suite to validate T01's template+JS changes introduced no regressions. Result: 89 passed, 2 failed (pre-existing title-case issues) — matches baseline exactly.

Confirmed `createSectionHeader()` had zero call sites after T01's migration to server-rendered section headers. Removed the function and its export from `row-factory.ts`. Ran `make typecheck && make js-dev && make css` — all pass. Bundle size dropped from 184.7kb → 183.8kb.

Verified SEC-08 gate: zero `innerHTML`/`insertAdjacentHTML` usage in TypeScript source (only a comment reference in `graph.ts`).

## Verification

- `python3 -m pytest tests/ -m e2e --tb=short -q` → **89 passed, 2 failed** (pre-existing title-case: `test_page_title`, `test_settings_page_title_tag`)
- `grep -rn "createSectionHeader" app/static/src/ts/` → zero results ✓
- `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` → only comment in graph.ts ✓
- `make typecheck` → zero errors ✓
- `make js-dev` → bundle 183.8kb ✓
- `make css` → Tailwind rebuild succeeds ✓
- Slice-level checks:
  - Template has 3 `.enrichment-section` divs (context, reputation, no-data) ✓
  - JS routes to `.enrichment-section--context` and `.enrichment-section--reputation` ✓
  - `injectSectionHeadersAndNoDataSummary()` does not call `createSectionHeader()` ✓
  - CSS `.enrichment-section:not(:has(.provider-detail-row))` hides empty sections ✓
  - `.provider-row--no-data` visibility rules present in CSS ✓

## Diagnostics

- `grep -rn "createSectionHeader" app/static/src/ts/` — should return zero results (migration complete)
- If a future module re-imports the removed function, `make typecheck` will fail with an import error
- E2E baseline: 89 pass / 2 fail (title-case). Deviation from this indicates regression.

## Deviations

None

## Known Issues

- 2 pre-existing E2E failures: `test_page_title[chromium]` and `test_settings_page_title_tag[chromium]` — title case mismatch ("sentinelx" vs "SentinelX"). Not introduced by this slice.

## Files Created/Modified

- `app/static/src/ts/modules/row-factory.ts` — removed dead `createSectionHeader()` function and export
- `app/static/dist/main.js` — rebuilt bundle reflecting dead code removal (183.8kb)
- `app/static/dist/style.css` — rebuilt CSS (no changes, verified clean)
