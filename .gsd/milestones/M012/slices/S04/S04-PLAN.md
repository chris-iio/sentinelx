# S04: Persistence and helper-layer next-work decision

**Goal:** Close M012 with a proof-backed keep/change decision for persistence and helper-layer next work, limiting any code in this slice to additive diagnostics that make the current seam easier to inspect without rewriting the WAL-backed stores or disturbing live/history continuity.
**Demo:** The milestone closes with a ranked, evidence-backed decision on whether cache/history/helper-path changes are warranted now, later, or should be left alone, with any shipped quick win proven against the real stack boundary it touches.

## Must-Haves

- Keep `app/cache/store.py` WAL-mode persistent-connection behavior and `app/enrichment/history_store.py` full-fidelity save/load semantics unchanged unless fresh evidence proves they are the bottleneck.
- Add one additive helper-layer diagnostics surface that makes history-save outcomes inspectable without changing `_get_enrichment_status()` cursor semantics, `/history/<analysis_id>` replay, or the shared live/history results UI path.
- Preserve `HistoryStore.save_analysis()` as the source of truth for full results persistence and avoid frontend/status-path churn that would regress R008, R019, or the already-proved S01/S02 contracts.
- Produce a ranked S04 assessment with explicit **Do now / Do next / Later / Leave alone** recommendations backed by fresh tests and the new diagnostics surface.
- Re-run focused helper/settings/history tests and `make verify-fast` so R022 and R040 stay justified by evidence instead of structural assumptions.

## Proof Level

- This slice proves: operational

## Integration Closure

Consume the existing helper background-save path and the existing settings inspection route, wiring only an additive diagnostics seam between them. Nothing new should be introduced into live polling, history replay, or the SQLite connection model; after this slice, the milestone only needs summary/validation work to close end-to-end.

## Verification

- The slice should leave one additive inspection surface for helper-layer persistence health, so a future agent can see aggregate history-save outcomes without opening analyst results pages or inferring state from logs alone.

## Tasks

- [x] **T01: Expose helper-layer history-save diagnostics through the settings inspection surface** `est:0.75d`
  ---
estimated_steps: 4
estimated_files: 5
skills_used:
  - observability
  - test
  - verify-before-complete
---

Add additive diagnostics around the helper-owned history save path and surface them on the existing `/settings` inspection page so future agents can see whether background persistence is healthy without touching live polling, history replay, or the WAL-mode store implementation. Keep the change aggregate-only: no raw input text, IOC values, or full results should be exposed.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `app/routes/_helpers.py` background save wrapper | Keep enrichment completion intact and treat diagnostics as best-effort; never let diagnostic bookkeeping block or fail the save path | Do not add waits or retries in the request path; diagnostics must stay O(1) around the existing background job | Ignore malformed internal state and fall back to zero/default diagnostics rather than crashing `/settings` |
| `app/routes/settings.py` + `app/templates/settings.html` inspection surface | Render safe defaults if diagnostics are absent so the settings page still loads | N/A | Only show aggregate counts, timestamps, and error-summary strings; never render raw results or input text |
| Existing history/store contracts (`HistoryStore.save_analysis()`, `/history/<id>`, `_get_enrichment_status()`) | Leave them unchanged; if a diagnostic change requires contract churn, stop and keep diagnostics out of those paths | N/A | N/A |

## Load Profile

- **Shared resources**: helper module state, `/settings` page render, and the existing background history-save path.
- **Per-operation cost**: constant-time counter/timestamp updates on save attempt/success/failure plus one extra template render on `/settings`.
- **10x breakpoint**: unbounded diagnostic state or request-path coupling; the task fails if diagnostics grow per job without a bound or if `/settings` depends on raw analysis payloads.

## Negative Tests

- **Malformed inputs**: no diagnostics present yet, partially populated diagnostic state, or missing timestamps should still render the settings page safely.
- **Error paths**: `HistoryStore.save_analysis()` raises, returns after `get_status()` is `None`, or succeeds after background enrichment, and diagnostics must record the right aggregate outcome without changing enrichment behavior.
- **Boundary conditions**: first successful save, repeated failures, and skipped save paths all leave `/history/<analysis_id>` replay and `_get_enrichment_status()` cursor semantics untouched.

## Steps

1. Add a bounded helper-level diagnostics summary for history-save attempts/successes/failures/last outcome in `app/routes/_helpers.py`, keeping it additive and free of raw analysis content.
2. Surface the aggregate diagnostics on the existing settings inspection surface via `app/routes/settings.py` and `app/templates/settings.html` instead of touching live polling or history detail routes.
3. Extend `tests/test_history_routes.py` and `tests/test_settings.py` to prove success, failure, and skipped-save cases update the diagnostics correctly and render safe aggregate values.
4. Run focused pytest plus the fast verification lane so the helper/settings change is backed by fresh proof and broader regressions are caught immediately.

## Must-Haves

- [ ] The helper background save path exposes additive aggregate diagnostics without changing `HistoryStore.save_analysis()` payloads or the WAL-mode stores.
- [ ] `/settings` renders the diagnostics using counts, timestamps, and error summaries only; no raw IOC input, results JSON, or secrets leak into the page.
- [ ] `_get_enrichment_status()` and the `?since=` cursor contract remain untouched.
- [ ] `/history/<analysis_id>` replay and existing settings page provider/cache behavior still pass fresh tests.

## Verification

- `python3 -m pytest tests/test_history_routes.py tests/test_settings.py -q`
- `make verify-fast`

## Observability Impact

- Signals added/changed: helper-level history-save attempt/success/failure counts plus last outcome metadata.
- How a future agent inspects this: open `/settings` or run the focused pytest modules to confirm the additive diagnostics surface.
- Failure state exposed: history persistence failures stop being log-only and become visible as aggregate last-outcome diagnostics.

## Inputs

- `app/routes/_helpers.py` — existing background enrichment + history-save wrapper that currently logs failures without an inspection surface.
- `app/routes/settings.py` — existing settings inspection route that already surfaces cache stats.
- `app/templates/settings.html` — current settings template where additive diagnostics can be rendered without touching analyst results pages.
- `tests/test_history_routes.py` — existing wrapper tests for success/failure/skip history-save behavior.
- `tests/test_settings.py` — existing settings route coverage that should pin the new inspection surface.

## Expected Output

- `app/routes/_helpers.py` — additive helper diagnostics for history-save outcomes.
- `app/routes/settings.py` — settings route wiring for the new diagnostics surface.
- `app/templates/settings.html` — aggregate helper diagnostics rendered safely for inspection.
- `tests/test_history_routes.py` — proof that success/failure/skip paths update diagnostics without breaking persistence flow.
- `tests/test_settings.py` — proof that the settings page renders the diagnostics safely.
  - Files: `app/routes/_helpers.py`, `app/routes/settings.py`, `app/templates/settings.html`, `tests/test_history_routes.py`, `tests/test_settings.py`
  - Verify: python3 -m pytest tests/test_history_routes.py tests/test_settings.py -q && make verify-fast

- [x] **T02: Write the ranked persistence/helper keep-change assessment for M012** `est:0.5d`
  ---
estimated_steps: 4
estimated_files: 2
skills_used:
  - write-docs
  - verify-before-complete
---

Turn the S04 evidence into a durable assessment and decision record. Use the research findings, the new helper/settings diagnostics surface, and fresh verification output to rank what SentinelX should do now, do next, later, and leave alone. Keep the conclusion explicit: preserve the WAL-backed stores and full-fidelity history replay unless new measurement disproves the current evidence.

## Steps

1. Re-read `S04-RESEARCH.md`, the M012 context/roadmap, and the final T01 outputs so the assessment cites real code seams instead of generic optimization advice.
2. Write `.gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md` with explicit **Do now**, **Do next**, **Later**, and **Leave alone** sections, plus a short requirement-impact note covering R022, R040, R008, and R019.
3. Append the planning/execution conclusion to `.gsd/DECISIONS.md`, capturing that S04 keeps the WAL stores as-is and treats helper-layer diagnostics/measurement as the only justified near-term follow-through.
4. Verify the assessment file exists, is non-empty, and contains the ranked sections so milestone closeout has a durable handoff artifact.

## Must-Haves

- [ ] The assessment names specific files/seams (`app/cache/store.py`, `app/enrichment/history_store.py`, `app/routes/_helpers.py`, and the new diagnostics surface) rather than generic “persistence” prose.
- [ ] The ranking clearly distinguishes **Do now**, **Do next**, **Later**, and **Leave alone** with proof-backed rationale.
- [ ] The written decision explicitly preserves WAL-mode cache/history behavior and the full-results history replay path unless future measurement says otherwise.
- [ ] The assessment calls out that `_get_enrichment_status()` `?since=` behavior and `HistoryStore.save_analysis()` continuity were intentionally left alone in this slice.

## Verification

- `test -s .gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md && rg -n "^## (Do now|Do next|Later|Leave alone)" .gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md`
- `rg -n "WAL|helper|persistence|history replay" .gsd/DECISIONS.md`

## Inputs

- `.gsd/milestones/M012/slices/S04/S04-RESEARCH.md` — evidence summary and recommendation baseline for the slice.
- `.gsd/milestones/M012/M012-CONTEXT.md` — milestone-level framing for optimization proof and ranked next work.
- `.gsd/milestones/M012/M012-ROADMAP.md` — roadmap promise this slice must close truthfully.
- `app/routes/_helpers.py` — final helper seam shape after T01.
- `app/routes/settings.py` — final inspection surface used as the slice’s shipped quick win.
- `.gsd/DECISIONS.md` — existing decision log that needs the S04 keep/change conclusion appended.

## Expected Output

- `.gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md` — ranked persistence/helper next-work decision with proof-backed recommendations.
- `.gsd/DECISIONS.md` — appended S04 decision capturing the keep/change stance.
  - Files: `.gsd/milestones/M012/slices/S04/S04-RESEARCH.md`, `.gsd/milestones/M012/M012-CONTEXT.md`, `.gsd/milestones/M012/M012-ROADMAP.md`, `.gsd/DECISIONS.md`, `app/routes/_helpers.py`, `app/routes/settings.py`
  - Verify: test -s .gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md && rg -n "^## (Do now|Do next|Later|Leave alone)" .gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md && rg -n "WAL|helper|persistence|history replay" .gsd/DECISIONS.md

## Files Likely Touched

- app/routes/_helpers.py
- app/routes/settings.py
- app/templates/settings.html
- tests/test_history_routes.py
- tests/test_settings.py
- .gsd/milestones/M012/slices/S04/S04-RESEARCH.md
- .gsd/milestones/M012/M012-CONTEXT.md
- .gsd/milestones/M012/M012-ROADMAP.md
- .gsd/DECISIONS.md
