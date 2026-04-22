# S04: Persistence and helper-layer next-work decision — UAT

**Milestone:** M012
**Written:** 2026-04-22T10:44:56.057Z

# UAT — S04 Persistence/helper diagnostics and keep-change decision

## Preconditions
- Worktree is at the completed `M012/S04` state.
- Python and Node dependencies are installed.
- Run from `/home/chris/projects/sentinelx`.
- No other local process is already bound to `127.0.0.1:5000`.

## Test Case 1 — `/settings` exposes safe aggregate history-save diagnostics
1. Start the app with `python3 run.py`.
2. Open `http://127.0.0.1:5000/settings` in a browser, or fetch it with `curl -fsS http://127.0.0.1:5000/settings`.
3. Expected outcome:
   - The page contains a **History Save Diagnostics** section.
   - On a fresh process, the section shows `0 attempted saves`, `0 successful`, `0 failed`, `0 skipped`.
   - The detail rows show `Last outcome: never`, `Last save attempt: Never`, `Last save success: Never`, `Last save failure: Never`, and `Last error summary: None`.
4. Edge check: the page must not render raw IOC values, input text, or result JSON anywhere in the diagnostics section.

## Test Case 2 — Helper save success/failure/skip paths update diagnostics without breaking enrichment continuity
1. Run `python3 -m pytest tests/test_history_routes.py tests/test_settings.py -q`.
2. Expected outcome:
   - The command exits 0.
   - The wrapper tests prove three helper outcomes:
     - successful history save increments attempts/successes,
     - failed save increments failures and records a coarse error summary,
     - `get_status() is None` skips saving and records `last_outcome == skipped`.
   - Settings-route tests prove the rendered page shows aggregate values only and safely falls back to defaults when timestamps are missing.
3. Edge check: the malformed-diagnostics test must pass, proving bad helper state is coerced back to safe defaults instead of breaking `/settings`.

## Test Case 3 — Cache/history persistence contracts stay untouched while diagnostics are added
1. Run `python3 -m pytest tests/test_cache_store.py tests/test_history_store.py tests/test_history_routes.py tests/test_settings.py -q`.
2. Expected outcome:
   - The command exits 0.
   - CacheStore and HistoryStore tests still pass, confirming the WAL-backed persistence layer remains healthy.
   - History route tests still pass, confirming `/history/<analysis_id>` replay remains intact after the helper diagnostics addition.
3. Edge check: no test should require changes to `_get_enrichment_status()` cursor semantics or to `HistoryStore.save_analysis()` payload shape.

## Test Case 4 — The broader fast proof lane still passes after S04
1. Run `make verify-fast`.
2. Expected outcome:
   - The command exits 0.
   - Non-E2E pytest passes.
   - Vitest passes frontend unit coverage.
   - TypeScript exits cleanly.
   - Tailwind and esbuild complete the production asset build.
3. Edge check: S04 should not force browser/E2E proof for this helper/settings-only seam; the fast lane remains sufficient for routine follow-up work here.

## Test Case 5 — The ranked assessment gives an explicit keep/change answer
1. Open `.gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md`.
2. Confirm it contains the sections `## Do now`, `## Do next`, `## Later`, and `## Leave alone`.
3. Expected outcome:
   - The assessment explicitly names `app/cache/store.py`, `app/enrichment/history_store.py`, `app/routes/_helpers.py`, and the `/settings` diagnostics surface.
   - The conclusion preserves WAL-mode stores, full-results history replay, and `_get_enrichment_status()` cursor semantics unless future measurement proves otherwise.
4. Edge check: if the assessment recommends a rewrite without new measurement, the slice fails UAT because it would contradict the evidence gathered in M012.

## Pass/Fail Rule
- Pass if all five test cases succeed.
- Fail if `/settings` leaks raw analysis content, helper diagnostics can break the page, or the written assessment recommends storage/helper churn without proof.
