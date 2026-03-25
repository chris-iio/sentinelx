---
id: S01
parent: M006
milestone: M006
provides:
  - HistoryStore class (app/enrichment/history_store.py) with save_analysis(), list_recent(), load_analysis()
  - /history/<analysis_id> Flask route serving stored analysis results
  - Recent analyses list HTML structure in index.html (verdict badges, IOC counts, timestamps)
  - data-history-results attribute pattern on .page-results for JS replay
  - history.ts JS module replaying stored results through the rendering pipeline
requires:
  []
affects:
  - S04
key_files:
  - app/enrichment/history_store.py
  - tests/test_history_store.py
  - app/routes.py
  - app/templates/results.html
  - app/templates/index.html
  - app/static/src/input.css
  - tests/test_history_routes.py
  - app/static/src/ts/modules/history.ts
  - app/static/src/ts/main.ts
  - app/static/src/ts/modules/enrichment.ts
key_decisions:
  - Used UUID4 hex as history row id (not autoincrement) — avoids leaking analysis count
  - top_verdict computed at save time and stored in the row — avoids re-parsing results_json on every list_recent()
  - Extended save_analysis() with optional analysis_id to reuse enrichment job_id as history id
  - History save failures silently caught — enrichment results must always be available regardless of persistence issues
  - Exported wireExpandToggles from enrichment.ts for reuse by history.ts rather than duplicating event delegation
  - History replay filters context providers out of verdict computation to match live enrichment behavior
patterns_established:
  - HistoryStore follows CacheStore SQLite WAL-mode pattern — same connection management, threading.Lock on writes, db_path constructor override for test isolation
  - Background thread wrapper pattern: _run_enrichment_and_save() wraps enrichment + persistence — failures in secondary concerns (save) don't affect primary flow (enrichment)
  - JS replay pattern: history.ts replays stored results through the same rendering building blocks as live enrichment — single rendering pipeline, two entry points (polling vs batch)
  - Graceful degradation for home page queries: HistoryStore errors caught in index() route — page renders normally without recent analyses section
observability_surfaces:
  - SQLite WAL-mode DB at ~/.sentinelx/history.db — row count and created_at timestamps provide analysis history audit trail
  - HistoryStore.list_recent() returns lightweight summaries for home page inspection
  - /history/<id> route returns 404 for missing IDs — observable via HTTP status codes
drill_down_paths:
  - .gsd/milestones/M006/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M006/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M006/slices/S01/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-25T11:22:35.326Z
blocker_discovered: false
---

# S01: Analysis History & Persistence

**Every online analysis is now persisted to SQLite, displayed in a recent analyses list on the home page, and fully reloadable via /history/<id> with JS replay through the existing rendering pipeline.**

## What Happened

This slice added end-to-end analysis history persistence across three tasks:

**T01 — HistoryStore class.** Created `app/enrichment/history_store.py` following the CacheStore SQLite WAL-mode pattern. The class provides `save_analysis()` (serializes IOCs/results to JSON, computes top_verdict at save time, stores with UUID4 hex id), `list_recent(limit=20)` (returns lightweight summaries ordered by created_at DESC, input_text truncated to 120 chars), and `load_analysis(id)` (returns full row with deserialized JSON, or None). 20 unit tests cover roundtrip, ordering, limits, verdict computation, concurrent writes, and IOC serialization fidelity.

**T02 — Flask route integration.** Wired HistoryStore into three touch points: (1) `_run_enrichment_and_save()` wrapper in the analyze route's Thread target saves results after enrichment completes — failures are silently caught so enrichment always works. (2) `GET /history/<analysis_id>` loads stored data, reconstructs IOC objects, groups by type, and renders results.html with `history_results` JSON for JS replay and `job_id='history'`. (3) `index()` queries `list_recent(limit=10)` and passes `recent_analyses` to the template — errors are caught gracefully. Templates updated: `results.html` adds `data-history-results` attribute, `index.html` adds conditional recent analyses list with verdict badges. 13 route integration tests added. Extended `save_analysis()` to accept optional `analysis_id` parameter so the enrichment job_id is reused as the history row id.

**T03 — JS history replay.** Created `app/static/src/ts/modules/history.ts` that detects `data-history-results` on `.page-results`, parses the JSON, and replays all results through the existing rendering building blocks (findCardForIoc, createContextRow, createDetailRow, updateSummaryRow, updateCardVerdict, updateDashboardCounts, sortCardsBySeverity, etc.). After replay: marks enrichment complete, wires expand/collapse toggles (via newly-exported `wireExpandToggles()` from enrichment.ts), and wires the export dropdown with its own allResults array. No debouncing needed — all results are synchronous. Imported and initialized from main.ts after initEnrichment().

## Verification

All five slice-level verification checks pass:
1. `python3 -m pytest tests/test_history_store.py -v` — 20/20 passed (0.82s)
2. `python3 -m pytest tests/test_history_routes.py -v` — 13/13 passed (0.47s)
3. `python3 -m pytest --tb=short -q` — 977 passed (47.83s), zero failures, zero regressions
4. `make js` — TypeScript builds successfully, 29.9kb bundle
5. `make css` — CSS builds successfully

Key files confirmed present: history_store.py with 3 public methods, routes.py with /history/<id> route + save wrapper, results.html with data-history-results attribute, index.html with recent analyses list, history.ts with full replay logic.

## Requirements Advanced

None.

## Requirements Validated

- R030 — HistoryStore persists every online analysis to SQLite. load_analysis reconstructs full results via /history/<id>. 20 unit + 13 route tests verify roundtrip persistence.
- R031 — Home page shows recent analyses with timestamp, IOC count, verdict badge. Click navigates to /history/<id> for full reload. Verified by test_index_shows_recent_analyses, test_index_shows_verdict_badge.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

Minor deviations from plan, all backward-compatible:
- Extended save_analysis() with optional analysis_id parameter to reuse the enrichment job_id (plan assumed new UUID always)
- Added _serialize_ioc() helper in routes.py (not in plan but needed for IOC dataclass → dict conversion)
- Duplicated injectDetailLink() and initExportButton() in history.ts instead of exporting from enrichment.ts (simpler than refactoring closure-bound functions; each is ~20 lines)

## Known Limitations

- History save failures in the background thread are silently ignored — enrichment results remain available but analysis won't appear in recent list if save fails
- No UI for deleting individual history entries or clearing all history
- No pagination on the recent analyses list (hard-coded limit=10)

## Follow-ups

- S04 will restyle the recent analyses list and home page to match the quiet precision design language
- Future: add history deletion/management UI
- Future: add pagination or infinite scroll for history list beyond 10 entries

## Files Created/Modified

- `app/enrichment/history_store.py` — New HistoryStore class with SQLite WAL-mode persistence — save_analysis(), list_recent(), load_analysis(), _compute_top_verdict()
- `tests/test_history_store.py` — 20 unit tests covering roundtrip, ordering, limits, verdict computation, concurrent writes, IOC serialization
- `app/routes.py` — Added _serialize_ioc(), _run_enrichment_and_save() wrapper, /history/<analysis_id> route, list_recent() call in index()
- `app/templates/results.html` — Added data-history-results attribute on .page-results when history_results is provided
- `app/templates/index.html` — Added conditional recent analyses list with verdict badges, IOC count, timestamps
- `app/static/src/input.css` — Added .recent-analyses, .recent-analyses-title, .recent-analyses-list CSS classes
- `tests/test_history_routes.py` — 13 integration tests covering save wrapper, history detail 200/404, index with/without history, error handling
- `app/static/src/ts/modules/history.ts` — New JS module — detects data-history-results, replays results through existing rendering pipeline
- `app/static/src/ts/main.ts` — Added import and initHistory() call after initEnrichment()
- `app/static/src/ts/modules/enrichment.ts` — Exported wireExpandToggles() for reuse by history.ts
