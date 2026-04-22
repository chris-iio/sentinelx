---
id: S01
parent: M012
milestone: M012
provides:
  - A stable backend/frontend contract for explicit terminal enrichment states.
  - A verified baseline proving cursor polling, incremental rendering, and success-path completion still work.
  - Executable plan-compatible verification commands future slices can reuse.
requires:
  []
affects:
  - S02
  - S03
  - S04
key_files:
  - app/routes/_helpers.py
  - app/enrichment/orchestrator.py
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/types/api.ts
  - app/static/src/ts/modules/enrichment.test.ts
  - tests/test_routes.py
  - tests/test_api.py
  - tests/test_orchestrator.py
  - tests/test_routes_helpers.py
  - tests/test_api_enrichment.py
  - tests/test_analysis_page.py
  - .gsd/PROJECT.md
key_decisions:
  - Kept the enrichment status contract additive rather than replacing existing success/progress fields.
  - Parsed polling JSON before checking `resp.ok` so terminal 404 payloads become analyst-visible states.
  - Used compatibility wrapper tests to keep plan-named verification commands valid while leaving canonical coverage in the current test modules.
patterns_established:
  - Additive terminal metadata over stable success payloads is the preferred contract-hardening pattern for active polling APIs.
  - Treat meaningful non-2xx JSON as application state when the backend intentionally uses HTTP status to signal terminal job conditions.
  - Use thin compatibility wrappers when roadmap verification names drift from the canonical test layout.
observability_surfaces:
  - `status`, `terminal`, `terminal_reason`, and `error` are now explicit runtime signals on enrichment status responses.
  - The analyst UI now reflects terminal failure text directly in the warning banner and progress text, creating a visible debugging surface for live polling failures.
drill_down_paths:
  - .gsd/milestones/M012/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M012/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M012/slices/S01/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-22T04:07:42.947Z
blocker_discovered: false
---

# S01: S01

**Hardened the live enrichment status path so unknown, evicted, and failed jobs become explicit terminal states in both backend payloads and the analyst UI, while preserving cursor polling and the existing success-path rendering flow.**

## What Happened

S01 turned the enrichment status seam from an implicit retry-forever path into an explicit, testable contract. On the backend, the shared status helper and orchestrator now preserve the existing progress payload (`total`, `done`, `complete`, `results`, `next_since`) and add additive terminal metadata (`status`, `terminal`, `terminal_reason`, `error`) so callers can distinguish running, complete, unknown, evicted, and job-failed states without breaking success semantics. Helper-level and orchestrator-level tombstones preserve eviction visibility instead of collapsing evicted jobs into generic missing IDs.

On the frontend, the enrichment poller now parses JSON before branching on `resp.ok`, so 404 terminal payloads are interpreted instead of discarded. Terminal states stop polling, surface a clear analyst-visible banner/progress message, and leave the success path unchanged: incremental results still render, the progress bar completes, detail rows/link injection still work, and export still unlocks only on successful completion.

To make the slice verifiable in the current repository layout, I also added thin compatibility test wrappers for the plan-named files `tests/test_routes_helpers.py`, `tests/test_api_enrichment.py`, and `tests/test_analysis_page.py`. The canonical coverage remains in `tests/test_routes.py`, `tests/test_api.py`, and the frontend Vitest suite; the wrappers keep plan-driven verification commands executable without duplicating logic or moving the real test ownership back to stale filenames. This gives downstream slices a stable baseline for status-contract work, shared live/history result application, and verification-lane decisions.

## Verification

Fresh post-change verification passed on the real slice surface:

- `python3 -m pytest tests/test_routes_helpers.py tests/test_orchestrator.py -q` → 38 passed in 0.58s
- `python3 -m pytest tests/test_api_enrichment.py tests/test_analysis_page.py -q` → 12 passed in 0.56s
- `npx vitest run` → 68 passed across 3 files in 0.87s
- `make build` → success; Tailwind and esbuild completed and regenerated `app/static/dist/*`

This proves the slice goal end to end: backend status serialization exposes terminal outcomes, the UI surfaces terminal failures instead of silently polling forever, successful enrichment still renders normally, and the verification commands named in the slice plan now execute against the current repo layout.

## Requirements Advanced

- R008 — preserved analyst workflow continuity by keeping success-path rendering, detail links, export gating, and incremental live enrichment intact while adding terminal failure visibility.
- R009 — maintained current security boundaries; no CSP/CSRF/textContent-only regressions were introduced while changing the polling contract.
- R010 — preserved 750ms cursor polling and avoided retry-forever UI behavior, improving failure efficiency without changing the successful polling cadence.
- R019 — kept the `?since=` cursor contract as the canonical live polling mechanism while extending the payload with terminal metadata.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

None.

## Deviations

The slice plan referenced backend test files that no longer exist in this checkout (`tests/test_routes_helpers.py`, `tests/test_api_enrichment.py`, `tests/test_analysis_page.py`). Instead of moving canonical tests back to stale locations, I preserved the real coverage in `tests/test_routes.py` and `tests/test_api.py` and added thin compatibility wrappers so the planned verification commands now run successfully.

## Known Limitations

`make build` still emits a non-blocking Browserslist `caniuse-lite` outdated warning. It did not affect build success or slice verification, but it remains environment noise for future contributors.

## Follow-ups

S02 can now extract a shared live/history result-application path against a stable terminal-status contract. S03 can use the restored plan-compatible verification surface to separate fast proof lanes from slower evidence lanes without inheriting stale-file failures.

## Files Created/Modified

- `app/routes/_helpers.py` — Extended shared status serialization to emit additive terminal metadata and preserve cursor semantics for both HTML and API polling routes.
- `app/enrichment/orchestrator.py` — Recorded explicit failed/evicted terminal job states so helper code can surface bounded tombstones instead of silent disappearance.
- `app/static/src/ts/modules/enrichment.ts` — Updated the poller to parse JSON before `resp.ok`, stop on terminal states, and surface analyst-visible failure messages without changing success rendering.
- `app/static/src/ts/types/api.ts` — Modeled the optional terminal fields on the enrichment status payload.
- `app/static/src/ts/modules/enrichment.test.ts` — Added focused frontend coverage for terminal failure visibility and success-path continuity.
- `tests/test_routes.py` — Pinned HTML polling-route behavior for unknown, evicted, cursor, and serialization semantics.
- `tests/test_api.py` — Pinned API polling-route behavior for unknown jobs, known jobs, and cursor slicing.
- `tests/test_routes_helpers.py` — Added compatibility wrapper coverage for the plan-named helper-route verification file.
- `tests/test_api_enrichment.py` — Added compatibility wrapper coverage for the plan-named enrichment API verification file.
- `tests/test_analysis_page.py` — Added compatibility wrapper coverage for the plan-named analysis page verification file.
- `.gsd/PROJECT.md` — Refreshed current project state to reflect M012/S01 completion and the restored verification surface.
