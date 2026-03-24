# S04 — Research

**Date:** 2026-03-20
**Depth:** Light research — straightforward pattern application using an existing debounce pattern already in the codebase, plus fixing two known pre-existing test failures.

## Summary

S04 has three concrete deliverables: (1) debounce `updateSummaryRow()` at 100ms per IOC (R017), (2) fix two pre-existing test failures introduced by S01–S03 changes, and (3) verify all gates pass (make typecheck clean, bundle ≤ 30KB, ≥ 99 E2E tests, 0 failures).

The debounce work is minimal — `enrichment.ts` already contains the exact pattern in `sortDetailRows()` (a `Map<string, ReturnType<typeof setTimeout>>` keyed by IOC value with 100ms `setTimeout` + `clearTimeout`). The same pattern wraps the `updateSummaryRow()` call site at line 359 of `enrichment.ts`.

The two pre-existing test failures are trivial collateral from S02 adding `IOCType.EMAIL`:
- `test_otx.py::test_all_eight_ioc_types_supported` — OTX's `supported_types = frozenset(IOCType)` now has 9 members, not 8. Fix: update assertion to 9.
- `test_routes.py::test_analyze_deduplicates` — the dedup test counts string occurrences of `"192.168.1.1"` in rendered HTML and asserts `< 10`. The richer template (new sections, data attributes) now produces 12 occurrences. Fix: relax threshold or switch to a structural assertion.

## Recommendation

Three tight tasks in sequence:

1. **T01: Debounce `updateSummaryRow()`** — Add a `summaryTimers` map to `enrichment.ts` using the identical `sortTimers` pattern, wrap the `updateSummaryRow()` call at line 359 in a debounced closure. Pure TS change, no template or CSS changes. Run `make typecheck` + `make js` to verify.

2. **T02: Fix pre-existing test failures** — Two one-line fixes in test assertions. No production code changes.

3. **T03: Final gate verification** — Run full test suite, confirm all gates pass. No code changes expected.

## Implementation Landscape

### Key Files

- `app/static/src/ts/modules/enrichment.ts` — Lines 32–65: existing `sortTimers` debounce pattern to replicate. Line 359: `updateSummaryRow()` call site to wrap. This is the only production file that changes.
- `tests/test_otx.py` — Line 197: `assert len(OTXAdapter.supported_types) == 8` → change to `== 9`. OTX uses `frozenset(IOCType)` which now includes EMAIL.
- `tests/test_routes.py` — Line 194: `assert count < 10` → relax to `< 15` or switch to counting `.ioc-card` elements via BeautifulSoup/regex.
- `app/static/dist/main.js` — Rebuilt by `make js`. Currently 26,648 bytes (under 30KB gate).

### Build Order

1. **T01 first** — the debounce is the only production code change in S04. It must pass `make typecheck` and `make js` before any test verification is meaningful.
2. **T02 second** — fix the two test assertions so the full suite can go green.
3. **T03 last** — run `python3 -m pytest tests/ -q`, `make typecheck`, `wc -c app/static/dist/main.js`, `python3 -m pytest tests/e2e/ -q` and confirm all gates.

### Verification Approach

| Gate | Command | Expected |
|------|---------|----------|
| TypeScript typecheck | `make typecheck` | exit 0 |
| Bundle size | `wc -c app/static/dist/main.js` | ≤ 30,000 bytes |
| Unit + integration tests | `python3 -m pytest tests/ -q --ignore=tests/e2e` | 0 failures |
| E2E tests | `python3 -m pytest tests/e2e/ -q` | ≥ 99 passing, 0 failures |
| Full suite | `python3 -m pytest tests/ -q` | 0 failures, ≥ 920 passing |

### Debounce Pattern (exact model to copy)

The `sortTimers` pattern in `enrichment.ts` lines 32–65:

```ts
const sortTimers: Map<string, ReturnType<typeof setTimeout>> = new Map();

function sortDetailRows(container: HTMLElement, iocValue: string): void {
  const existing = sortTimers.get(iocValue);
  if (existing !== undefined) clearTimeout(existing);
  const timer = setTimeout(() => {
    sortTimers.delete(iocValue);
    // ... actual work ...
  }, 100);
  sortTimers.set(iocValue, timer);
}
```

For `updateSummaryRow`, add a parallel `summaryTimers` map and wrap the call at line 359:

```ts
const summaryTimers: Map<string, ReturnType<typeof setTimeout>> = new Map();

// In renderEnrichmentResult(), replace:
//   updateSummaryRow(slot, result.ioc_value, iocVerdicts);
// with:
function debouncedUpdateSummaryRow(
  slot: HTMLElement, iocValue: string,
  iocVerdicts: Record<string, VerdictEntry[]>
): void {
  const existing = summaryTimers.get(iocValue);
  if (existing !== undefined) clearTimeout(existing);
  const timer = setTimeout(() => {
    summaryTimers.delete(iocValue);
    updateSummaryRow(slot, iocValue, iocVerdicts);
  }, 100);
  summaryTimers.set(iocValue, timer);
}
```

### Pre-existing Failures Detail

**`test_otx.py` line 197:** `OTXAdapter.supported_types = frozenset(IOCType)` — this is a wildcard that includes all enum members. S02 added `IOCType.EMAIL`, making the frozenset 9 members. The test hardcodes `== 8`. Fix: change to `== 9` and update the test docstring/message.

**`test_routes.py` line 194:** The test submits `"192[.]168[.]1[.]1 contacted 192[.]168[.]1[.]1 again and again: 192.168.1.1"` and counts string occurrences of `"192.168.1.1"` in the response HTML. With the richer M002/M003 template (data attributes, additional sections), the canonical IP now appears 12 times. The assertion `count < 10` was always fragile. Fix: relax to `< 20` (the actual dedup guarantee is "not 3 separate IOC entries", not "fewer than 10 string occurrences in the HTML").

## Constraints

- All DOM construction must remain `createElement` + `textContent` (SEC-08) — the debounce wrapper doesn't change DOM construction, it only delays calling `updateSummaryRow()`.
- Bundle must stay ≤ 30KB. Current: 26,648 bytes. Adding ~10 lines of debounce code will not breach this.
- `make typecheck` must exit 0 — adding a `Map<string, ReturnType<typeof setTimeout>>` and a wrapper function introduces no type issues (identical to existing `sortTimers` pattern).
