---
id: S02
parent: M012
milestone: M012
provides:
  - A single shared result-application seam future slices can change once instead of patching both live polling and history replay independently.
  - An explicit results-page ownership contract that prevents history/live double initialization and gives downstream work a stable dispatch boundary.
  - Parity and non-polling tests that make future regressions in result rendering, export gating, detail-link injection, and copy-button summaries fail quickly.
requires:
  - slice: S01
    provides: Terminal-state and cursor-polling contract continuity that S02 preserved while moving rendering into the shared coordinator and exclusive owner dispatcher.
affects:
  - S04
key_files:
  - app/static/src/ts/modules/result-application.ts
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/modules/history.ts
  - app/static/src/ts/main.ts
  - app/static/src/ts/modules/shared-rendering.ts
  - app/templates/results.html
  - app/routes/history.py
  - app/static/src/ts/modules/result-application.test.ts
  - app/static/src/ts/modules/history.test.ts
  - app/static/src/ts/modules/enrichment.test.ts
  - tests/test_history_routes.py
key_decisions:
  - Introduced `result-application.ts` as the only shared stateful result-application owner and kept transport/timing ownership in `enrichment.ts` and `history.ts`.
  - Made `.page-results[data-results-owner]` the authoritative runtime ownership contract and treated malformed explicit live markers as non-live/static rather than falling back to polling.
  - Made expand/export listener wiring idempotent at the page root so duplicate initializer calls cannot double-bind behavior.
  - Proved parity with the same mixed IOC fixture rendered through both live and history paths and pinned the history-detail HTML contract in route tests.
patterns_established:
  - Use a shared apply/flush/finalize coordinator for stateful DOM replay while leaving mode-specific polling/replay cadence in the owning runtime.
  - Use explicit page-level ownership markers to prevent accidental multi-initializer behavior on shared UI surfaces.
  - Guard refactor seams with parity tests that compare full visible DOM state, not presence-only assertions.
  - Pin frontend dispatcher assumptions in server-rendered route/template tests so ownership drift fails before analyst-visible regressions ship.
observability_surfaces:
  - `.page-results[data-results-owner]` and resolved runtime markers now act as the primary health/inspection surface for which runtime owns a results page.
  - Focused Vitest fetch spies fail if history replay ever calls `/enrichment/status/history` or surfaces live-only terminal warnings.
  - `tests/test_history_routes.py` now pins the HTML ownership contract (`data-results-owner`, `data-job-id`, mode/progress/export attributes) that the frontend dispatcher depends on.
drill_down_paths:
  - .gsd/milestones/M012/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M012/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M012/slices/S02/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-22T06:26:08.275Z
blocker_discovered: false
---

# S02: S02 — Shared result-application path for live and history views

**Unified live polling and history replay behind one shared result-application coordinator, made results-surface ownership exclusive, and proved parity/non-polling with focused frontend and route tests.**

## What Happened

S02 closed the frontend seam where live polling and history replay had been drifting apart. The slice extracted the shared stateful DOM/result coordination into `app/static/src/ts/modules/result-application.ts`, giving both modes one apply/flush/finalize path for card updates, summary rows, verdict aggregation, detail-link injection, progress completion, export readiness, and copy-button `data-enrichment` text. Live-only behavior stayed local to `enrichment.ts` — 750 ms cursor polling, `?since=` continuity, terminal-state handling from S01, warning banners, and debounced flush timing. History-only behavior stayed local to `history.ts` — parsing stored `data-history-results`, synchronous replay, and completion without network polling.

The slice also removed the integration ambiguity that let history detail pages satisfy the live guard. `results.html` now carries an additive `.page-results[data-results-owner]` contract, `app/routes/history.py` sets history pages to `history`, and `main.ts` dispatches to exactly one runtime owner per page. Both runtime modules defensively verify ownership and wire expand/export behavior idempotently at the page root, so duplicate initializer calls no longer accumulate listeners by accident. The net result is that analysts see the same enrichment cards, detail rows, verdict summaries, detail links, export availability, and copy-button summaries whether results arrive live or are replayed from stored history, while history pages never leak `/enrichment/status/history` polling or false terminal banners.

Operationally, the slice's health signal is explicit owner/runtime state on `.page-results` and parity-backed DOM behavior in tests; the primary failure signal is any accidental history polling, duplicate expand/export behavior, or live/history UI divergence. Recovery is simple because the runtime boundary is now explicit: fix or revert the owner contract or shared coordinator without needing to untangle two duplicated render paths. The remaining gap is production telemetry — today this seam is guarded by focused Vitest/pytest coverage and DOM markers rather than runtime instrumentation, which is acceptable for this refactor slice but worth remembering if future work wants field diagnostics.

## Verification

Fresh slice verification passed after the final code state:

- `npx vitest run app/static/src/ts/modules/result-application.test.ts app/static/src/ts/modules/history.test.ts app/static/src/ts/modules/enrichment.test.ts` → 3 test files passed, 10 tests passed in 672 ms.
- `python3 -m pytest tests/test_history_routes.py -q` → 14 passed in 0.67 s.
- `npx tsc --noEmit && echo TSC_OK` → `TSC_OK`.
- `make build >/tmp/m012_s02_build.log && tail -n 5 /tmp/m012_s02_build.log && echo BUILD_OK` → bundled `app/static/dist/main.js` at 29.5kb and printed `BUILD_OK`.

These checks prove the shared coordinator behavior, live/history parity, no accidental `/enrichment/status/history` polling, preserved `next_since` cursor continuity, stable route/template ownership contract, successful typecheck, and successful production bundle rebuild.

## Requirements Advanced

- R008 — Preserved analyst-visible continuity for enrichment cards, detail links, export gating, progress, and copy-button summaries by routing both live and history through one shared application path with parity tests.
- R009 — Maintained the existing safe DOM construction boundary during the refactor; shared application logic continued using existing createElement/textContent-based helpers rather than introducing unsafe HTML rendering.
- R010 — Kept live-only debounce and 750 ms cursor polling behavior local to `enrichment.ts` while extracting shared rendering, preventing the refactor from regressing polling efficiency or sort/update cadence.
- R019 — Preserved the `?since=` live polling contract while the UI path was unified; live continuity tests now prove `next_since` progression still works after the refactor.
- R040 — Added explicit parity/non-polling proof at the refactor seam so cleanup is backed by targeted tests rather than structural assumptions.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

None.

## Deviations

None.

## Known Limitations

There is no new production telemetry for owner-selection mistakes or duplicate listener attachment; this seam is guarded by explicit DOM owner markers plus focused Vitest/pytest parity coverage rather than runtime metrics.

## Follow-ups

S04 can now evaluate persistence/helper-layer next work against a stabilized results-surface seam instead of duplicated live/history paths. If future work needs field diagnostics, add lightweight runtime instrumentation around owner selection and duplicate-listener prevention rather than reopening the shared rendering boundary.

## Files Created/Modified

- `app/static/src/ts/modules/result-application.ts` — New shared stateful coordinator that applies enrichment items, tracks per-IOC state, flushes summary/verdict updates, and finalizes detail-link/copy-button state for both live and history flows.
- `app/static/src/ts/modules/enrichment.ts` — Refactored live polling to use the shared coordinator while retaining cursor polling, terminal handling, debounce timing, and live-only ownership checks.
- `app/static/src/ts/modules/history.ts` — Refactored history replay to use the shared coordinator, enforce exclusive ownership, and complete synchronously without live polling.
- `app/static/src/ts/main.ts` — Dispatches results pages to exactly one owner based on `.page-results[data-results-owner]` instead of starting both runtimes.
- `app/static/src/ts/modules/shared-rendering.ts` — Hardened shared event/export wiring to be idempotent at the page root.
- `app/templates/results.html` — Added the additive results-owner contract consumed by the frontend dispatcher.
- `app/routes/history.py` — Marks history detail pages as `results_owner="history"` while preserving the existing online-mode DOM shape for UI parity.
- `app/static/src/ts/modules/result-application.test.ts` — Pins shared coordinator behavior for mixed result fixtures, ordering, no-data grouping, detail-link injection, and copy-button enrichment updates.
- `app/static/src/ts/modules/history.test.ts` — Adds history replay parity, non-polling, malformed-history, and empty-history coverage.
- `app/static/src/ts/modules/enrichment.test.ts` — Extends live coverage to prove `next_since` continuity and final DOM parity with the shared coordinator path.
- `tests/test_history_routes.py` — Pins the server-rendered history-detail ownership contract and replay page markup the frontend relies on.
