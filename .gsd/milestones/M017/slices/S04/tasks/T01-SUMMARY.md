---
id: T01
parent: S04
milestone: M017
key_files:
  - app/static/src/ts/modules/result-application.ts
  - app/static/src/ts/modules/result-application.test.ts
  - package.json
key_decisions:
  - Use DOM verdict snapshots inside the existing shared flush path to decide whether global dashboard recount and card reorder work is necessary, avoiding production-only diagnostics or timing assertions.
  - Keep churn observability in tests via card/dashboard/order DOM state and helper spies where useful, while preserving textContent-based safe rendering assertions.
duration: 
verification_result: passed
completed_at: 2026-05-13T17:43:32.080Z
blocker_discovered: false
---

# T01: Added focused result-application regression coverage and gated global dashboard recount/reorder work to severity-changing flushes.

**Added focused result-application regression coverage and gated global dashboard recount/reorder work to severity-changing flushes.**

## What Happened

Extended `app/static/src/ts/modules/result-application.test.ts` around the real `createResultApplicationCoordinator()` path. The new coverage exercises provider-only deltas after an initial severity flush, severity-changing deltas across multiple cards, history-style finalize replay preserving copy/detail-link affordances, and malicious-looking provider text rendered as inert text. Updated `result-application.ts` so `flush()` snapshots card verdict state before and after dirty IOC flushes and only runs `updateDashboardCounts()` / `sortCardsBySeverity()` when card verdict state changes. Added a `test` npm script so the task's required `npm test -- --run` verification command executes Vitest directly.

## Verification

Ran `npm test -- --run`; all frontend Vitest suites passed: 7 test files and 97 tests. This includes the focused `result-application.test.ts` suite with 12 tests covering unchanged-severity provider deltas, severity/order-changing deltas, history replay/finalize affordances, and text-safe provider rendering.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `npm test -- --run` | 0 | ✅ pass — 7 test files and 97 tests passed | 1306ms |

## Deviations

Added a minimal `package.json` `test` script because the required verification command initially failed with `Missing script: "test"`. The script delegates to existing Vitest dev dependency.

## Known Issues

None.

## Files Created/Modified

- `app/static/src/ts/modules/result-application.ts`
- `app/static/src/ts/modules/result-application.test.ts`
- `package.json`
