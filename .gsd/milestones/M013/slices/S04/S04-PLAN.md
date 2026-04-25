# S04: Frontend polling/render shipped fixes and final rerun

**Goal:** Ship the narrow frontend/render optimization that the M013 audit already justified by caching stable result-application DOM handles inside the shared live/history coordinator, then refresh the generated audit and finish with a truthful final rerun that proves analyst-visible polling/render behavior stayed intact.
**Demo:** After this: An analyst sees unchanged live/history enrichment UX with any proven polling/render improvement shipped, and the repo contains the final rerun of the ranked audit showing what shipped now versus what remains deferred.

## Must-Haves

- ## Demo
- An analyst can complete a live enrichment run or open a history result and see the same summary rows, context/reputation sections, copy buttons, detail links, filters, export surface, progress states, and live/history ownership markers while the shared coordinator stops re-discovering stable DOM handles on every result.
- ## Must-Haves
- Cache stable IOC-scoped DOM handles (`.ioc-card`, `.enrichment-slot`, `.copy-btn`, `.ioc-context-line`, and the server-rendered section containers) inside the shared result-application coordinator instead of repeating whole-document lookups for each incoming result.
- Snapshot `data-provider-counts` once per page/coordinator so pending-indicator math does not re-read and re-parse the same immutable page attribute on every result.
- Preserve live/history owner resolution, polling cadence, `since`/`next_since` semantics, DOM-safety rules (`createElement` + `textContent`), expand/collapse behavior, and finalize/link injection semantics; do not reopen backend request/status or transport contracts settled by S03.
- Update `tools/optimization_audit.py`, `tests/test_optimization_audit.py`, and the generated `.gsd/milestones/M013/M013-AUDIT.md` artifact so the frontend/render finding truthfully records the shipped coordinator-local fix and keeps any broader render follow-up explicit rather than implied.
- Final proof must include the focused frontend/audit suites plus a captured audit rerun that executes fresh `make verify-fast` and `make verify-deep` on the same final repository state, satisfying R040.
- ## Threat Surface
- **Abuse**: live polling payloads and history-replayed provider strings still reach the DOM; the optimization must not introduce `innerHTML`, selector shortcuts that bypass stable ownership checks, or render paths that skip the existing safe text-only row builders.
- **Data exposure**: do not widen history payloads, provider raw data, or page-level metadata beyond the existing summary/detail contract.
- **Input trust**: `data-history-results`, live polling JSON, `data-provider-counts`, and server-rendered IOC metadata remain untrusted inputs until normalized by the existing rendering helpers.
- ## Requirement Impact
- **Requirements touched**: R008, R009, R010, R019, and R040 directly; R018 remains a supporting continuity guardrail because S04 must not accidentally invalidate cached-marker or snapshot assumptions by reopening polling semantics.
- **Re-verify**: live polling parity, history replay parity, loaded-slot/finalize behavior, copy/detail-link/export/filter/progress continuity, and audit wording plus captured proof.
- **Decisions revisited**: D058 and D059 remain binding — keep S04 narrow to the frontend coordinator seam and finish with fresh proof instead of reopening settled backend or persistence decisions.
- ## Verification
- `npx vitest run app/static/src/ts/modules/result-application.test.ts app/static/src/ts/modules/enrichment.test.ts app/static/src/ts/modules/history.test.ts app/static/src/ts/modules/main.test.ts app/static/src/ts/modules/row-factory.test.ts`
- `pytest tests/test_optimization_audit.py -q`
- `pytest tests/e2e/test_results_page.py -q`
- `python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md --capture-command 'verify-fast::make verify-fast' --capture-command 'verify-deep::make verify-deep'`

## Proof Level

- This slice proves: final-assembly + operational proof for the frontend live/history boundary — the shipped coordinator optimization must preserve analyst-visible results-page behavior and leave the milestone with a regenerated audit whose embedded captures were taken on the same final state.

## Integration Closure

- Upstream surfaces consumed: `app/static/src/ts/modules/result-application.ts`, `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/modules/history.ts`, `app/static/src/ts/modules/main.ts`, `app/static/src/ts/modules/cards.ts`, `app/static/src/ts/types/ioc.ts`, `app/templates/results.html`, `app/templates/partials/_ioc_card.html`, `app/templates/partials/_enrichment_slot.html`, `tools/optimization_audit.py`, and the focused Vitest/Pytest/Playwright verification files.
- New wiring introduced in this slice: one coordinator-local cache of stable IOC DOM handles/provider counts shared by both live polling and history replay, plus the final audit rerun with captured fast/deep verification embedded into `.gsd/milestones/M013/M013-AUDIT.md`.
- What remains before the milestone is truly usable end-to-end: nothing in M013 once this slice ships and the final rerun stays green.

## Verification

- Runtime signals: `.page-results[data-results-owner][data-results-runtime]`, `.enrichment-slot--loaded`, `.ioc-summary-row`, pending-indicator text, and the frontend/render row plus capture table in `.gsd/milestones/M013/M013-AUDIT.md` remain the high-signal inspection points.
- Inspection surfaces: focused Vitest suites for live/history parity, `tests/e2e/test_results_page.py` for mocked-online DOM continuity, and the captured `verify-fast` / `verify-deep` entries in the generated audit artifact.
- Failure visibility: regressions should surface as missing summary/detail-link/copy/progress DOM state, stale pending counts, owner/runtime attribute drift, or audit wording/capture mismatches.
- Redaction constraints: keep DOM rendering text-only and avoid widening stored/raw provider payloads, secrets, or hidden metadata in the browser-visible contract.

## Tasks

- [x] **T01: Cache stable IOC DOM handles inside the shared result-application coordinator** `est:0.75d`
  Design and implement the narrow frontend hot-path fix that S01/S03 left queued: cache the stable per-IOC DOM handles once inside `createResultApplicationCoordinator()` and reuse them for both live polling and history replay instead of repeating `findCardForIoc()` / `.querySelector()` / provider-count parsing on every incoming result. Keep the work coordinator-local so S04 does not reopen polling cadence, owner resolution, or backend status semantics.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| Server-rendered card/slot structure in `app/templates/results.html` + partials | Fail soft by skipping the IOC when a card/slot is genuinely absent; never throw and break the whole polling/history pass | N/A | Treat missing optional handles as absent and preserve the current graceful no-op behavior |
| Shared `cards.ts` helpers and verdict/dashboard/sort semantics | Keep verdict text/count/sort outcomes identical; if a new helper is needed, make it additive and keep selector contracts unchanged | Debounced sorting must still settle within the existing 100ms flush behavior | Do not let cache state drift from the actual DOM node identity after filtering/sorting re-append operations |
| Page-level provider-count metadata from `data-provider-counts` | Fall back to the existing default counts when the attribute is absent or invalid | N/A | Parse once and preserve the current fallback behavior for malformed JSON |

## Load Profile

- **Shared resources**: the `.ioc-card` grid, per-card `.enrichment-slot` subtree, copy buttons, pending-indicator text, and the shared debounce/sort path.
- **Per-operation cost**: target one IOC-map lookup plus local node reuse per result, instead of repeated whole-document selectors and repeated provider-count JSON parsing.
- **10x breakpoint**: repeated `querySelector` work across every result and every flush; the task fails if the coordinator still re-discovers stable card/slot handles or reparses page metadata on the hot path.

## Negative Tests

- **Malformed inputs**: missing card for an IOC, missing slot, missing provider-count attribute, and malformed provider-count JSON.
- **Error paths**: context-only results, provider error rows, and repeated results for the same IOC that must still converge on the correct worst verdict/copy text.
- **Boundary conditions**: one IOC with multiple providers, multiple IOC cards, history replay using the same coordinator path, and finalize after no-data/mixed-detail rows.

## Steps

1. Add a coordinator-local cache keyed by IOC value that captures the stable DOM nodes and provider-count snapshot once, while keeping dynamic nodes like summary rows and detail links created lazily through the existing row builders.
2. Route `apply()`, `flushIoc()`, and `finalize()` through those cached handles so live polling and history replay share the cheaper path without changing sorting/filtering/detail-link/copy/progress behavior.
3. Extend the focused Vitest coverage to prove live/history parity, provider-count fallback behavior, and finalize/link/copy continuity on the cached path.

## Must-Haves

- [ ] Stable IOC DOM handles are discovered once and reused across `apply()`, `flush()`, and `finalize()`.
- [ ] Provider-count parsing happens once per coordinator/page and preserves the current fallback semantics.
- [ ] Live polling and history replay still produce the same loaded-slot, summary-row, context/detail, copy-button, and detail-link outcomes.
- [ ] The task does not change owner resolution, polling cadence, route payload shape, or DOM-safety discipline.
  - Files: `app/static/src/ts/modules/result-application.ts`, `app/static/src/ts/modules/cards.ts`, `app/static/src/ts/types/ioc.ts`, `app/static/src/ts/modules/result-application.test.ts`, `app/static/src/ts/modules/enrichment.test.ts`, `app/static/src/ts/modules/history.test.ts`, `app/static/src/ts/modules/main.test.ts`, `app/static/src/ts/modules/row-factory.test.ts`
  - Verify: npx vitest run app/static/src/ts/modules/result-application.test.ts app/static/src/ts/modules/enrichment.test.ts app/static/src/ts/modules/history.test.ts app/static/src/ts/modules/main.test.ts app/static/src/ts/modules/row-factory.test.ts

- [ ] **T02: Refresh the audit runner and pinned wording for the shipped frontend/render fix** `est:0.5d`
  Update the generated-audit source of truth so M013 stops describing frontend coordinator caching as queued work and instead truthfully records what S04 ships now versus what still remains deferred. Keep the artifact generated from `tools/optimization_audit.py`; do not hand-edit `.gsd/milestones/M013/M013-AUDIT.md`.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `tools/optimization_audit.py` baseline constants and rendered prose | Fail loudly in tests if the wording still claims the frontend fix is unshipped or silently drops the seam | Keep the runner deterministic and local; do not add long-running external captures here | Render explicit failure/capture summaries rather than ambiguous or placeholder wording |
| `tests/test_optimization_audit.py` pinned expectations | Update assertions in lockstep with the new truthful bucket/wording so later slices cannot drift the audit contract silently | N/A | Treat stale assertions as a blocker, not as a reason to weaken coverage |
| Generated audit artifact `.gsd/milestones/M013/M013-AUDIT.md` | Regenerate from the runner on the same code state instead of hand-editing markdown | Bound generation to the existing deterministic workflow | If the regenerated artifact disagrees with the tests or runner constants, stop and fix the source of truth |

## Load Profile

- **Shared resources**: the audit runner constants, generated markdown artifact, and focused audit tests.
- **Per-operation cost**: one local markdown regeneration plus focused pytest coverage.
- **10x breakpoint**: wording drift between runner, tests, and generated artifact that makes the final milestone rerun untrustworthy.

## Negative Tests

- **Malformed inputs**: missing or stale frontend/render row text, placeholder bucket content, or capture rows that omit the frontend seam entirely.
- **Error paths**: a regenerated artifact that still claims coordinator caching is `do next`, or tests that no longer reflect the shipped/deferred split.
- **Boundary conditions**: the request/status and persistence rows keep their current shipped/leave-alone stance while only the frontend/render wording changes to match S04 reality.

## Steps

1. Update the frontend/render finding, seam note, and any baseline-stance prose in `tools/optimization_audit.py` so the audit describes the coordinator-local cache as shipped and leaves any broader render work explicitly deferred.
2. Update `tests/test_optimization_audit.py` to pin the new wording and guard against regression back to the pre-S04 `do next` language.
3. Regenerate `.gsd/milestones/M013/M013-AUDIT.md` from the runner and confirm the artifact matches the new truthful wording before starting the expensive final proof.

## Must-Haves

- [ ] The frontend/render row no longer describes stable-handle caching as queued work.
- [ ] Any remaining render follow-up stays explicit in the ranked audit instead of disappearing.
- [ ] Runner, tests, and generated artifact all agree on the shipped frontend/render stance.
- [ ] The audit remains generated output sourced from `tools/optimization_audit.py`.
  - Files: `tools/optimization_audit.py`, `tests/test_optimization_audit.py`, `.gsd/milestones/M013/M013-AUDIT.md`
  - Verify: pytest tests/test_optimization_audit.py -q && python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md

- [ ] **T03: Run the final milestone-close rerun and fix any proof regressions on the verified state** `est:0.5d`
  Finish M013 with fresh evidence, not inherited claims. Run the focused browser lane plus the final audit command that captures `make verify-fast` and `make verify-deep`, and only make the smallest regression fixes needed to keep the audited final state green. This task is allowed to touch source or tests only when the rerun exposes a real regression from T01/T02.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `tests/e2e/test_results_page.py` mocked-online results-page proof | Treat any DOM/state regression as a slice blocker because it threatens analyst-visible continuity | Use the existing deterministic mocked-online flow; do not swap in live-provider dependencies | If the browser output no longer matches the contract, fix code/tests or audit wording before claiming completion |
| `make verify-fast` / `make verify-deep` capture commands | Do not mark the slice complete until both commands pass on the same final state captured into the audit artifact | Keep captures on the audit runner's deterministic command surface rather than ad hoc shell notes | Failed captures must remain visible in the artifact/command output, not be hidden by a partial rerun |
| Final generated audit artifact | Regenerate it last so the capture table reflects the verified final repository state | Bound generation to the existing runner timeout/command-capture behavior | Stop if the artifact and the actual verification state disagree |

## Load Profile

- **Shared resources**: the repo-wide fast/deep verification lanes, the deterministic mocked-online browser harness, and the generated audit artifact.
- **Per-operation cost**: one focused browser pytest run plus one final baseline audit generation that shells out to `make verify-fast` and `make verify-deep`.
- **10x breakpoint**: letting final proof depend on stale earlier output, or chasing broad refactors instead of the smallest fix needed to restore the verified final state.

## Negative Tests

- **Malformed inputs**: missing detail links, missing loaded-slot markers, wrong owner/runtime attributes, or stale capture rows in the final audit.
- **Error paths**: Vitest/E2E/build/typecheck failures surfaced through the captured verify lanes.
- **Boundary conditions**: live and history paths still share the coordinator, the final audit captures both verification lanes, and the generated artifact reflects the exact final state used for slice closure.

## Steps

1. Run `pytest tests/e2e/test_results_page.py -q` after the focused code/test changes settle so the analyst-visible live seam is checked before the expensive full rerun.
2. Run the final audit command with `verify-fast` and `verify-deep` capture commands so `.gsd/milestones/M013/M013-AUDIT.md` becomes the durable record of the last verified state.
3. If the rerun exposes regressions, make the smallest source/test/audit fix needed and rerun until the generated artifact, focused E2E lane, and captured fast/deep proof all agree.

## Must-Haves

- [ ] Fresh mocked-online results-page proof passes on the post-S04 code state.
- [ ] The final audit artifact embeds fresh `verify-fast` and `verify-deep` captures from the same repository state.
- [ ] Any regression fixes stay narrowly scoped to restoring the promised live/history/frontend continuity.
- [ ] The slice finishes with durable evidence that satisfies R040 instead of relying on earlier slice output.
  - Files: `tests/e2e/test_results_page.py`, `tools/optimization_audit.py`, `.gsd/milestones/M013/M013-AUDIT.md`, `app/static/src/ts/modules/result-application.ts`, `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/modules/history.ts`
  - Verify: pytest tests/e2e/test_results_page.py -q && python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md --capture-command 'verify-fast::make verify-fast' --capture-command 'verify-deep::make verify-deep'

## Files Likely Touched

- app/static/src/ts/modules/result-application.ts
- app/static/src/ts/modules/cards.ts
- app/static/src/ts/types/ioc.ts
- app/static/src/ts/modules/result-application.test.ts
- app/static/src/ts/modules/enrichment.test.ts
- app/static/src/ts/modules/history.test.ts
- app/static/src/ts/modules/main.test.ts
- app/static/src/ts/modules/row-factory.test.ts
- tools/optimization_audit.py
- tests/test_optimization_audit.py
- .gsd/milestones/M013/M013-AUDIT.md
- tests/e2e/test_results_page.py
- app/static/src/ts/modules/enrichment.ts
- app/static/src/ts/modules/history.ts
