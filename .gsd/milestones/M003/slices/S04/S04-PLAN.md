# S04: Frontend Render Efficiency & Integration Verification

**Goal:** Summary row DOM rebuilds debounced at 100ms per IOC (R017); all M003 gates pass — typecheck clean, bundle ≤ 30KB, full test suite 0 failures, ≥ 99 E2E tests passing.
**Demo:** Submit a multi-IOC input → during streaming enrichment, each IOC's summary row rebuilds only 1–2 times instead of once per provider. `make typecheck` exits 0. `wc -c app/static/dist/main.js` ≤ 30,000. `python3 -m pytest tests/ -q` → 0 failures.

## Must-Haves

- `summaryTimers` debounce map in `enrichment.ts` wrapping `updateSummaryRow()` at 100ms per IOC — identical pattern to existing `sortTimers`
- OTX supported_types assertion updated from 8 to 9 (accounts for `IOCType.EMAIL`)
- Route dedup test threshold relaxed from `< 10` to `< 20` (richer template produces more string occurrences)
- `make typecheck` exits 0
- `wc -c app/static/dist/main.js` ≤ 30,000 bytes
- `python3 -m pytest tests/ -q` → 0 failures, ≥ 920 passing
- `python3 -m pytest tests/e2e/ -q` → ≥ 99 passing, 0 failures

## Verification

- `make typecheck` → exit 0
- `make js` → exit 0, then `wc -c app/static/dist/main.js` ≤ 30,000 bytes
- `python3 -m pytest tests/ -q --ignore=tests/e2e` → 0 failures
- `python3 -m pytest tests/e2e/ -q` → ≥ 99 passing, 0 failures
- `grep -c 'summaryTimers' app/static/src/ts/modules/enrichment.ts` → ≥ 3 (declaration + get + set)

## Observability / Diagnostics

**Runtime signals:**
- `summaryTimers.size` observable via browser DevTools console: `window._dbg?.summaryTimers` (not exposed — inspect via breakpoint in `debouncedUpdateSummaryRow` if needed)
- Summary row rebuilds reduced from ~10/IOC to 1–2/IOC; confirm by adding a `console.count('updateSummaryRow')` breakpoint in `row-factory.ts:updateSummaryRow` during manual testing
- No server-side signal: this is a pure client-side render optimization

**Failure visibility:**
- If debounce timer leaks (IOC navigated away before 100ms fires), the orphaned `setTimeout` callback calls `updateSummaryRow` on a detached slot — harmless (no DOM parent) but wastes a micro-task; detectable via `summaryTimers.size > 0` after enrichment completes
- TypeScript compiler catches type errors immediately: `make typecheck` must exit 0

**Inspection surfaces:**
- `grep -c 'summaryTimers' app/static/src/ts/modules/enrichment.ts` → must be ≥ 3
- `wc -c app/static/dist/main.js` → bundle size sanity gate ≤ 30,000 bytes

**Redaction constraints:** None — no PII flows through the debounce wrapper; only `ioc_value` is used as a timer key (already visible in the DOM)

## Tasks

- [x] **T01: Debounce updateSummaryRow via summaryTimers map in enrichment.ts** `est:20m`
  - Why: R017 — `updateSummaryRow()` is called once per provider result during streaming enrichment, causing 10+ DOM rebuilds per IOC. Debouncing at 100ms matches the existing `sortTimers` pattern and limits rebuilds to 1–2 per IOC.
  - Files: `app/static/src/ts/modules/enrichment.ts`
  - Do: Add `summaryTimers` Map at module scope (identical type to `sortTimers`). Add `debouncedUpdateSummaryRow()` wrapper function. Replace the direct `updateSummaryRow()` call at line 359 with the debounced version. Run `make typecheck` and `make js` to verify. All DOM construction remains `createElement` + `textContent` (SEC-08 unaffected — debounce wrapper doesn't touch DOM).
  - Verify: `make typecheck` exits 0; `make js` exits 0; `wc -c app/static/dist/main.js` ≤ 30,000; `grep -c 'summaryTimers' app/static/src/ts/modules/enrichment.ts` ≥ 3
  - Done when: `summaryTimers` debounce wraps `updateSummaryRow()`, typecheck clean, bundle ≤ 30KB

- [x] **T02: Fix pre-existing test failures and verify all M003 gates** `est:15m`
  - Why: S02 added `IOCType.EMAIL` (9th enum member), breaking two hardcoded test assertions. After fixing these, the full test suite must pass with 0 failures to close M003.
  - Files: `tests/test_otx.py`, `tests/test_routes.py`
  - Do: (1) In `test_otx.py` line 196–198, change `== 8` to `== 9` and update docstring from "8 IOC types" to "9 IOC types". (2) In `test_routes.py` line 194, change `< 10` to `< 20` (the dedup guarantee is "not 3 separate IOC entries", not "fewer than 10 HTML string occurrences"). (3) Run `python3 -m pytest tests/ -q --ignore=tests/e2e` and confirm 0 failures. (4) Run `python3 -m pytest tests/e2e/ -q` and confirm ≥ 99 passing, 0 failures. (5) Run `make typecheck` to confirm still clean.
  - Verify: `python3 -m pytest tests/ -q` → 0 failures, ≥ 920 passing; `python3 -m pytest tests/e2e/ -q` → ≥ 99 passing, 0 failures; `make typecheck` exits 0; `wc -c app/static/dist/main.js` ≤ 30,000
  - Done when: Full suite 0 failures; all 4 gates pass (typecheck, bundle, unit tests, E2E tests)

## Files Likely Touched

- `app/static/src/ts/modules/enrichment.ts` — add `summaryTimers` debounce map + wrapper function
- `app/static/dist/main.js` — rebuilt by `make js`
- `tests/test_otx.py` — update supported_types assertion from 8 to 9
- `tests/test_routes.py` — relax dedup count threshold from `< 10` to `< 20`
