# M010: Cleanup & History Page

**Gathered:** 2026-04-04
**Status:** Ready for planning

## Project Description

SentinelX is a universal threat intelligence hub for SOC analysts. It extracts, normalizes, classifies, and enriches IOCs from pasted text against 15 providers in parallel. After 9 milestones of feature development and refactoring, the codebase is mature (1060 tests, 12K app LOC) but has accumulated some duplication in the routes layer and a UI element (Recent Analyses) that belongs in its own page.

## Why This Milestone

The codebase has specific known duplication that should be eliminated before building new features:
- Orchestrator setup logic is copy-pasted between `analysis.py` and `api.py` (~20 identical lines)
- `enrichment_status()` in `enrichment.py` and `api_status()` in `api.py` are functionally identical
- Stale imports and exports (`json` in api.py, `ResultDisplay` in shared-rendering.ts)
- The Recent Analyses section clutters the home page — analysts need it accessible but not blocking the primary paste form

## User-Visible Outcome

### When this milestone is complete, the user can:

- Visit the home page and see only the paste form — clean, focused input
- Navigate to `/history` to see all recent analyses with links to detail pages
- Use the same enrichment and analysis flow with zero behavior changes

### Entry point / environment

- Entry point: browser at `http://localhost:5000`
- Environment: local dev
- Live dependencies involved: none (SQLite local storage)

## Completion Class

- Contract complete means: all tests pass, dead code removed, duplication measured at zero for identified patterns
- Integration complete means: home page renders without recent analyses, /history page lists and links to detail pages
- Operational complete means: none (no service lifecycle changes)

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Home page renders the paste form only — no Recent Analyses section
- `/history` lists recent analyses and each entry links to the correct `/history/<id>` detail page
- All 1060 tests pass (or adjusted count if tests were added/removed with the refactoring)
- `grep` confirms zero duplication of orchestrator setup between analysis.py and api.py

## Risks and Unknowns

- Route test mocking — Tests that patch specific function locations in route modules may need updating when code moves to `_helpers.py`. This was a known pattern from M007/M008.
- enrichment.ts polling URL — The frontend polls `/enrichment/status/<job_id>`. If the HTML blueprint status endpoint is removed (consolidated into the API one), the URL must either stay the same or the frontend must be updated.

## Existing Codebase / Prior Art

- `app/routes/_helpers.py` — already hosts shared state (_orchestrators, _enrichment_pool, _serialize_result, _serialize_ioc, _run_enrichment_and_save). Natural home for the extracted orchestrator setup helper.
- `app/routes/analysis.py` — HTML analyze endpoint with orchestrator setup (lines 56-84)
- `app/routes/api.py` — JSON analyze endpoint with identical orchestrator setup (lines 88-118); also has identical status polling logic
- `app/routes/enrichment.py` — HTML status polling endpoint (identical body to api_status)
- `app/routes/history.py` — existing `/history/<analysis_id>` detail route; new `/history` list route adds here
- `app/enrichment/history_store.py` — `list_recent()` already exists, currently called by index route
- `app/templates/index.html` — Recent Analyses section (lines 61-82) to be removed
- `app/static/src/ts/modules/ui.ts` — `initRecentAnalysesToggle()` JS handler to be moved
- `app/static/src/input.css` — Recent Analyses CSS (lines 1981-2129) to be relocated

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R050 — Orchestrator setup extraction (M010/S01)
- R051 — Status endpoint consolidation (M010/S01)
- R052 — Dead import/export removal (M010/S01)
- R053 — Recent Analyses removed from home page (M010/S02)
- R054 — Dedicated /history page (M010/S02)
- R055 — All tests pass, zero behavior changes (M010/all)

## Scope

### In Scope

- Extract shared orchestrator setup helper into _helpers.py
- Consolidate duplicate status polling endpoints
- Remove unused imports and dead exports
- Move Recent Analyses from index.html to new /history page
- Create /history list route and template
- Add /history link to nav
- Update E2E tests as needed

### Out of Scope / Non-Goals

- New features or UI changes beyond the history page
- Adapter refactoring (done in M009)
- Test framework changes
- Performance optimization

## Technical Constraints

- Frontend polls `/enrichment/status/<job_id>` — this URL must continue to work (KNOWLEDGE.md: Playwright route mocking registers before navigation)
- `url_for('main.xxx')` references in templates depend on the shared `main` Blueprint (KNOWLEDGE.md: shared Blueprint preserves template url_for)
- Tests mock `app.routes._enrichment_pool`, `client.application.registry`, etc. — patch targets must match after code moves (KNOWLEDGE.md: routes refactoring test mocking)

## Integration Points

- `HistoryStore.list_recent()` — already exists, reused by new /history route
- `base.html` nav — add /history link alongside settings icon
- `ui.ts` — `initRecentAnalysesToggle()` removed from home page, toggle logic moves to new history page if needed

## Open Questions

- None — scope is well-defined from investigation
