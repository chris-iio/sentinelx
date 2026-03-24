# S04: Frontend Render Efficiency & Integration Verification — UAT

**Milestone:** M003
**Written:** 2026-03-21

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S04 is a pure efficiency fix (debounce) plus test/gate verification. The debounce is not user-visible (it reduces DOM rebuilds behind the scenes); its presence is confirmed by grep count. All other verification is command-driven (typecheck, bundle size, test suite). No new UI surface was added. Human visual inspection is not required.

## Preconditions

- Working directory: `/home/chris/.gsd/projects/bb1bd2fe6965/worktrees/M003`
- Python virtualenv active with pytest and Playwright installed
- Node/esbuild available for `make typecheck` and `make js`
- Server does NOT need to be running for unit tests; E2E tests start their own server

## Smoke Test

```bash
grep -c 'summaryTimers' app/static/src/ts/modules/enrichment.ts
# Expected output: 4
```
If this returns 4, the debounce wiring is in place and S04's primary deliverable exists.

## Test Cases

### 1. summaryTimers debounce wiring present

1. Run: `grep -c 'summaryTimers' app/static/src/ts/modules/enrichment.ts`
2. **Expected:** Output is `4` (declaration at module scope + `.get` in timer-clear + `.set` storing new timer + `.delete` inside callback = 4 occurrences)

### 2. Debounce wrapper function exists and wraps updateSummaryRow

1. Run: `grep -n 'debouncedUpdateSummaryRow\|summaryTimers' app/static/src/ts/modules/enrichment.ts`
2. **Expected:** Output shows:
   - One `const summaryTimers: Map<string, ReturnType<typeof setTimeout>> = new Map();` line
   - One `function debouncedUpdateSummaryRow(` declaration
   - `.get`, `.set`, `.delete` calls inside that function body
   - One `debouncedUpdateSummaryRow(` call replacing the former direct `updateSummaryRow(` call in `renderEnrichmentResult()`

### 3. TypeScript typecheck clean

1. Run: `make typecheck`
2. **Expected:** Exit code 0. No output beyond `tsc --noEmit`.

### 4. Bundle size gate

1. Run: `make js && wc -c app/static/dist/main.js`
2. **Expected:** Exit code 0; byte count printed is ≤ 30,000. (Baseline: 26,783 bytes)

### 5. Unit and integration tests — zero failures

1. Run: `python3 -m pytest tests/ -q --ignore=tests/e2e`
2. **Expected:** All tests pass, 0 failures. Count ≥ 828.

### 6. OTX supported_types test reflects intentional EMAIL exclusion

1. Run: `python3 -m pytest tests/test_otx.py -k "supported_types" -v`
2. **Expected:** Test passes. The assertion checks `len(...) == 8` (not 9) — EMAIL is intentionally excluded from OTX's frozenset.

### 7. Routes dedup test uses relaxed threshold

1. Run: `python3 -m pytest tests/test_routes.py::test_analyze_deduplicates -v`
2. **Expected:** Test passes. The `count < 20` threshold is satisfied by the M002/M003 template markup.

### 8. Full E2E suite — zero failures, ≥ 99 passing

1. Run: `python3 -m pytest tests/e2e/ -q`
2. **Expected:** All tests pass, 0 failures. Count ≥ 99 (baseline: 105).

### 9. E2E coverage includes M003 deliverables

1. Run: `python3 -m pytest tests/e2e/ -v 2>&1 | grep -E "email|detail|orchestrat|semaphore|backoff" -i`
2. **Expected:** Multiple test names matching — confirms S01 (orchestrator), S02 (email), and S03 (detail page) are all covered in the E2E suite.

## Edge Cases

### Timer leak: summaryTimers.size after enrichment completes

This is not user-visible, but verifiable via browser DevTools if needed:

1. Open the app in a browser (server running)
2. Submit a multi-IOC input (e.g., `1.1.1.1 8.8.8.8`)
3. Wait for enrichment to fully complete (progress bar fills, "View full detail →" links appear)
4. Open DevTools console and add a breakpoint inside `debouncedUpdateSummaryRow` in enrichment.ts
5. **Expected:** After all providers complete, `summaryTimers.size` returns to 0. Any transient non-zero value is harmless (orphaned setTimeout fires against a detached slot and silently no-ops).

### OTX explicit frozenset exclusion documented

1. Run: `grep -A5 'test_all_eight_ioc_types_supported' tests/test_otx.py`
2. **Expected:** Docstring mentions that EMAIL is intentionally excluded from OTX's supported types (OTX has no email lookup endpoint).

### HTML dedup comment documents intent

1. Run: `grep -A3 'count < 20' tests/test_routes.py`
2. **Expected:** Comment explains that the threshold tests for "no duplicate IOC rows," not "few HTML string occurrences" — and notes that richer template markup legitimately produces ~12 occurrences.

## Failure Signals

- `grep -c 'summaryTimers' enrichment.ts` returns < 4 → debounce wiring partially missing; inspect with `grep -n` to find which usage site was lost
- `make typecheck` exits non-zero → TypeScript error introduced; output will show file:line
- `wc -c app/static/dist/main.js` > 30,000 → bundle size regression; compare with 26,783 baseline to estimate what was added
- `python3 -m pytest tests/ -q` shows failures → run with `-v` and filter by FAILED to see which tests; most likely culprits are test_otx.py (new IOCType without OTX update) or test_routes.py (template change crossing the < 20 threshold)
- E2E failures → run `python3 -m pytest tests/e2e/ -v` to see which tests fail; the server must be startable (check `python3 -m flask run` for import errors first)

## Not Proven By This UAT

- **Actual reduction in DOM rebuilds during live enrichment** — the debounce is structurally correct but the 1–2 rebuilds vs. 10+ can only be confirmed by adding `console.count('updateSummaryRow')` to `row-factory.ts:updateSummaryRow` and running a live enrichment with a real multi-provider IOC. This is a manual runtime-only verification.
- **VT 429 backoff behavior at runtime** — S01 unit tests prove the logic; actual VT rate-limit behavior in production cannot be reproduced in automated tests without real VT API traffic.
- **Email extraction from fully-defanged `user[@]evil[.]com`** — known limitation from S02: iocsearcher doesn't handle this form. Not a regression, but not fixed either.

## Notes for Tester

- The 105 E2E test count exceeds the ≥ 99 gate. The gate was set conservatively when the suite had 91 tests; it was never updated. The true baseline is now 105.
- `make typecheck` invokes `tsc --noEmit` — if the TypeScript server is slow to warm up, allow 3-5 seconds for the first run.
- The T02 task summary incorrectly states that OTXAdapter uses `frozenset(IOCType)`. It does not — it uses an explicit frozenset. The KNOWLEDGE.md entry "OTXAdapter.supported_types uses an explicit frozenset, not frozenset(IOCType)" is the authoritative source.
