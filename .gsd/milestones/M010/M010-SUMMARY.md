---
id: M010
title: "Cleanup & History Page"
status: complete
completed_at: 2026-04-04T05:33:22.086Z
key_decisions:
  - D048: Recent Analyses relocated to dedicated /history route (supersedes D044 which kept it on home page) — still valid, provides clean separation of concerns
  - _setup_orchestrator() returns (job_id, orchestrator, registry) tuple so callers can use registry for template_extras without a second lookup
key_files:
  - app/routes/_helpers.py
  - app/routes/analysis.py
  - app/routes/api.py
  - app/routes/enrichment.py
  - app/routes/history.py
  - app/templates/history.html
  - app/templates/index.html
  - app/templates/base.html
  - app/templates/macros/icons.html
  - app/static/src/ts/modules/shared-rendering.ts
  - app/static/src/ts/modules/ui.ts
  - tests/test_routes.py
  - tests/test_api.py
  - tests/test_history_routes.py
lessons_learned:
  - Route helper extraction pattern is mechanical and safe: extract shared logic into _helpers.py, retarget test patch paths, verify with grep. The pattern established in M007/M008 (KNOWLEDGE.md entry) continues to hold.
  - When relocating a UI block to a new page, reusing existing CSS classes avoids duplicating styling — history.html reuses .recent-analyses-list and .recent-analysis-row verbatim.
  - Test count changes should be tracked explicitly — S02 added 1 test (1060→1061) which is a signal of proper coverage, not a regression.
---

# M010: Cleanup & History Page

**Eliminated route layer duplication via shared helpers, removed dead imports/exports, and relocated Recent Analyses from the home page to a dedicated /history page — 15 files changed, net reduction in route module complexity, 1061 tests passing.**

## What Happened

M010 was a focused cleanup milestone with two slices targeting known technical debt and a UI improvement.

S01 (Route Duplication & Dead Code Cleanup) extracted `_setup_orchestrator()` and `_get_enrichment_status()` into `app/routes/_helpers.py`, eliminating ~40 duplicated lines across `analysis.py`, `api.py`, and `enrichment.py`. The orchestrator setup block (~20 lines of uuid/cache/config/constructor/registry/pool-submit) was identical in both analysis routes; the status endpoint body was identical in enrichment.py and api.py. Both are now one-liner delegations. Dead imports (uuid, json, ConfigStore, EnrichmentOrchestrator) were removed from the cleaned modules. The unused `export` keyword was removed from `ResultDisplay` in shared-rendering.ts. 13 test patch targets were retargeted from the old module paths to `app.routes._helpers.*`.

S02 (Recent Analyses → Dedicated /history Page) moved the collapsible Recent Analyses block from `index.html` to a new `/history` route served by `history_list()` in `history.py`. A new `history.html` template reuses existing CSS classes for visual consistency. A clock Heroicon was added to the nav bar. On the removal side: the Jinja block was deleted from index.html, `index()` was simplified to a bare `render_template("index.html")`, and `initRecentAnalysesToggle()` was removed from ui.ts. One new error-propagation test was added, bringing the total from 1060 to 1061.

Cross-slice integration was clean — S01 provided the consolidated route helpers, S02 built on top by further simplifying analysis.py and adding the history list route.

## Success Criteria Results

- **analysis.py and api.py share a single orchestrator setup helper**: ✅ PASS — `_setup_orchestrator()` exists in `_helpers.py`; `grep -c 'EnrichmentOrchestrator(' analysis.py api.py` returns 0 for both files.
- **Status endpoints consolidated**: ✅ PASS — `_get_enrichment_status()` in `_helpers.py`; both `enrichment.py` and `api.py` delegate as one-liners.
- **Dead imports/exports removed**: ✅ PASS — No uuid/json/ConfigStore imports in cleaned modules; `export interface ResultDisplay` removed from shared-rendering.ts (grep returns 0).
- **All tests pass**: ✅ PASS — 1061 passed, 0 failures (pytest --tb=short -q, 51.6s). Count increased from 1060 baseline due to new error-propagation test in S02.
- **make typecheck passes**: ✅ PASS — tsc --noEmit exits 0.
- **make js passes**: ✅ PASS — esbuild produces 28.7kb bundle.
- **Home page shows only the paste form**: ✅ PASS — GET / returns 200 with no 'Recent Analyses' text; no `list_recent` call in analysis.py; no `initRecentAnalysesToggle` in ui.ts.
- **/history page lists analyses**: ✅ PASS — `history_list()` route exists in history.py; GET /history returns 200.
- **Enrichment polling continues to function**: ✅ PASS — Status endpoints delegate to shared helper; 1061 tests cover polling behavior.

## Definition of Done Results

- **All slices complete**: ✅ Both S01 and S02 are `[x]` in the roadmap.
- **All slice summaries exist**: ✅ S01-SUMMARY.md and S02-SUMMARY.md both present with verification_result: passed.
- **Cross-slice integration**: ✅ S01→S02 dependency clean. S02's simplification of analysis.py is compatible with S01's helper extraction. 1061 tests pass together.
- **Code changes verified**: ✅ 15 non-.gsd files changed (237 insertions, 187 deletions) confirmed via git diff --stat.

## Requirement Outcomes

- **R050** (Orchestrator setup extracted): active → validated. `_setup_orchestrator()` in _helpers.py; zero inline constructors in analysis.py/api.py.
- **R051** (Status endpoints consolidated): active → validated. `_get_enrichment_status()` in _helpers.py; one-liner delegations in enrichment.py/api.py.
- **R052** (Dead imports/exports removed): active → validated. No uuid/json/ConfigStore in cleaned modules; ResultDisplay export keyword removed.
- **R053** (Home page shows only paste form): active → validated. No 'Recent Analyses' in index.html; no list_recent call in analysis.py; no toggle JS.
- **R054** (Dedicated /history page): active → validated. history_list() route in history.py; history.html template; clock nav icon; links to detail pages.
- **R055** (All tests pass, zero behavior changes): active → validated. 1061 passed, up from 1060 baseline (one test added, none removed).

## Deviations

S02/T01 completed most of the T02-planned test rewrites ahead of schedule, leaving T02 with only the error-propagation test to add. No material impact on deliverables.

## Follow-ups

None — the codebase is clean and ready for the next feature milestone.
