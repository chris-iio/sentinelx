---
id: S04
parent: M012
milestone: M012
provides:
  - An additive `/settings` inspection seam that shows aggregate background history-save health without reading logs or opening analyst result pages.
  - A durable ranked keep/change assessment for persistence/helper work that milestone validation and future planners can cite directly.
  - Fresh proof that helper diagnostics can be added without changing WAL-backed storage, full-results history replay, or `_get_enrichment_status()` cursor semantics.
requires:
  []
affects:
  []
key_files:
  - app/routes/_helpers.py
  - app/routes/settings.py
  - app/templates/settings.html
  - .gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md
  - .gsd/DECISIONS.md
  - tests/test_history_routes.py
  - tests/test_settings.py
key_decisions:
  - Kept history-save observability as a bounded helper-local aggregate snapshot surfaced on `/settings` instead of changing `HistoryStore.save_analysis()` payloads, WAL-backed storage, or `_get_enrichment_status()` cursor semantics.
  - Sanitized helper diagnostics on read so malformed internal state falls back to safe defaults rather than breaking the settings inspection page.
  - Confirmed the M012 keep/change conclusion: preserve `app/cache/store.py`, `app/enrichment/history_store.py`, full-results history replay, and cursor polling semantics until future measurement proves a real persistence/helper problem.
patterns_established:
  - Expose helper-owned persistence health through an aggregate inspection surface first; do not disturb analyst-facing replay or polling contracts merely to add diagnostics.
  - Coerce malformed diagnostic state back to safe defaults on read so `/settings` stays inspectable even if in-memory helper bookkeeping is damaged.
  - Make persistence refactors measurement-gated: keep WAL-backed SQLite stores and full-results history replay unless diagnostics or realistic load measurements show real pain.
observability_surfaces:
  - `/settings` now exposes History Save Diagnostics with attempts/successes/failures/skips, last-outcome timestamps, and a coarse last error summary.
  - Focused pytest coverage in `tests/test_history_routes.py` and `tests/test_settings.py` now proves helper success/failure/skip bookkeeping plus safe rendering/default behavior.
  - The ranked assessment artifact `.gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md` is the explicit decision-grade handoff for future persistence/helper follow-up.
drill_down_paths:
  - .gsd/milestones/M012/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M012/slices/S04/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-22T10:44:56.057Z
blocker_discovered: false
---

# S04: Persistence and helper-layer next-work decision

**Added bounded history-save diagnostics to `/settings` and closed M012 persistence/helper work with an evidence-backed keep decision that leaves WAL-backed stores, full-results history replay, and cursor polling semantics unchanged.**

## What Happened

S04 closed the last open seam in M012 by proving that SentinelX does not currently need a persistence rewrite and by shipping the lowest-regret observability improvement at the helper boundary. In `app/routes/_helpers.py`, the helper-owned background history-save path now records a constant-size aggregate snapshot of attempts, successes, failures, skips, last-outcome timestamps, and a coarse error summary. `app/routes/settings.py` and `app/templates/settings.html` expose that snapshot on the existing `/settings` inspection surface using only aggregate values, so operators can see whether background history persistence is healthy without reading logs, opening analyst result pages, or touching live polling/history replay contracts.

Just as importantly, the slice intentionally did **not** churn the core continuity seams. `HistoryStore.save_analysis()` remains the source of truth for full serialized results persistence, so `/history/<analysis_id>` still replays the original analyst-visible output without re-enrichment. `_get_enrichment_status()` and its `?since=` cursor contract in `app/routes/_helpers.py` were left untouched because earlier slices already proved that path and this slice produced no evidence that cursor slicing is the bottleneck. The WAL-mode persistent-connection design in `app/cache/store.py` and `app/enrichment/history_store.py` also remains in place.

T02 then turned the code-level evidence into a durable ranked assessment in `.gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md` and a matching decision log entry in `.gsd/DECISIONS.md`. The result is an explicit milestone-closeout stance future planners can trust: **do now** keep and use the new helper diagnostics surface; **do next** measure the helper/runtime seam only if diagnostics or live behavior suggest real pain; **later** consider deeper store/helper redesign only with concrete concurrent-load or file-growth evidence; **leave alone** the WAL-backed stores, full-results history replay, and `_get_enrichment_status()` cursor semantics until measurement proves otherwise.

## Verification

Fresh slice verification was run after reviewing the assembled work:

- `python3 -m pytest tests/test_history_routes.py tests/test_settings.py -q` ✅ passed — `35 passed in 0.62s`
- `python3 -m pytest tests/test_cache_store.py tests/test_history_store.py tests/test_history_routes.py tests/test_settings.py -q` ✅ passed — `73 passed in 1.40s`
- `make verify-fast` ✅ passed in 27.0s
  - `python3 -m pytest -q -m 'not e2e'` → `955 passed, 113 deselected in 3.21s`
  - `npx vitest run` → `6 passed files, 78 passed tests`
  - `npx tsc --noEmit` → exit 0
  - `make build` → Tailwind + esbuild production bundle completed successfully
- Live observability surface check: `curl -fsS http://127.0.0.1:5000/settings | rg -n 'History Save Diagnostics|0 attempted saves|Last outcome:</strong> never|Last error summary:</strong> None'` ✅ passed and returned the rendered diagnostics heading plus safe default values.
- Assessment artifact check: `test -s .gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md && rg -n '^## (Do now|Do next|Later|Leave alone)' .gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md` ✅ passed.
- Decision log check: `rg -n 'WAL|helper|persistence|history replay' .gsd/DECISIONS.md` ✅ passed and showed the new S04 keep/change conclusion.

This verification proves the shipped diagnostics surface works, helper success/failure/skip behavior is covered, the assessment artifact exists with the required ranking, and the broader fast lane still holds after the slice changes.

## Requirements Advanced

- R022 — S04's assessment and fresh store/history verification explicitly preserved the WAL-mode persistent-connection design in `app/cache/store.py` and `app/enrichment/history_store.py` rather than rewriting it without proof.
- R008 — S04 preserved `HistoryStore.save_analysis()` as the full-results persistence source of truth so `/history/<analysis_id>` replay remains faithful to the original analyst-visible output.
- R019 — S04 intentionally left `_get_enrichment_status()` and its `?since=` cursor contract untouched while adding only helper-local diagnostics.

## Requirements Validated

- R040 — Fresh `make verify-fast` passed with `955 passed, 113 deselected`, 78 frontend unit tests, clean TypeScript, and a successful production build after the S04 changes.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

None.

## Deviations

None.

## Known Limitations

The `/settings` diagnostics surface is intentionally aggregate-only and process-local: it does not persist a long-term timeline across restarts, and it is not a substitute for future concurrent-load measurement. If operators start seeing repeated failures or skips, a later milestone should measure `_run_enrichment_and_save()` and the helper/runtime seam before proposing structural rewrites.

## Follow-ups

Use the new `/settings` diagnostics surface as the first signal for any persistence/helper follow-up. Only schedule deeper store or helper refactors if those counters start showing repeated failures/skips or if future concurrent-load/file-growth measurements reveal real contention, write amplification, or request-path waste.

## Files Created/Modified

- `app/routes/_helpers.py` — Added bounded helper-local history-save diagnostics bookkeeping, safe snapshot coercion, and test reset support without changing the live polling contract.
- `app/routes/settings.py` — Wired the helper diagnostics snapshot into the existing settings inspection route.
- `app/templates/settings.html` — Rendered aggregate History Save Diagnostics values on `/settings` using counts, timestamps, and an error-summary string only.
- `tests/test_history_routes.py` — Added helper success/failure/skip and malformed-state coverage for the history-save diagnostics seam.
- `tests/test_settings.py` — Added settings-page rendering coverage for aggregate diagnostics values, safe defaults, and no-leak behavior.
- `.gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md` — Recorded the ranked do-now/do-next/later/leave-alone persistence/helper assessment.
- `.gsd/DECISIONS.md` — Appended the S04 execution-level keep/change conclusion preserving the WAL-backed stores and history replay path.
