# S04 Research — Frontend polling/render shipped fixes and final rerun

## Summary

This is **targeted research**, not a broad architecture spike. The backend polling contract is already settled by S03; S04 should stay on the frontend seam plus the final audit rerun.

**Primary requirements for this slice**
- **R008** — preserve analyst-visible polling/export/filter/detail-link/copy/progress behavior.
- **R009** — preserve DOM-safety and the existing textContent/createElement rendering discipline.
- **R010** — reduce or at least not worsen polling/render churn.
- **R019** — keep live polling aligned with the shipped `since`/`next_since` contract.
- **R040** — finish with fresh proof, not inherited claims.

**Supported-but-already-settled guardrail**
- **R018** — do not disturb snapshot/cached-marker truth indirectly by reopening backend polling assumptions.

The best narrow shipped fix is still the one S01/S03 left queued: **cache stable IOC DOM handles inside the shared result-application coordinator** rather than widening the work into a new polling contract or a render rewrite.

## Relevant skill guidance

- **`verify-before-complete`** applies directly here: *fresh output or no claim*. Because this slice changes shared result application / analyst-visible DOM state, the final close must include fresh `make verify-fast` and `make verify-deep` evidence in the same execution window before anyone says the slice is done.

## Skill discovery

Installed skills already cover the important execution discipline here:
- `verify-before-complete` — final proof bar.
- `test` — focused test generation/runs if the executor wants help expanding coverage.
- `agent-browser` / `web-quality-audit` — optional if someone wants interactive browser confirmation, but the existing deterministic Playwright suite is already the main proof surface.

Directly relevant uninstalled skills discovered:
- **Playwright:** `currents-dev/playwright-best-practices-skill@playwright-best-practices` (`npx skills add currents-dev/playwright-best-practices-skill@playwright-best-practices`)
- **Flask:** `aj-geddes/useful-ai-prompts@flask-api-development` (`npx skills add aj-geddes/useful-ai-prompts@flask-api-development`)

These are optional. Nothing in the current slice looks blocked on installing them.

## Implementation landscape

### 1. `app/static/src/ts/modules/result-application.ts` is the primary shipping seam

This is the shared live/history application path and the safest place to retire render-path waste without reopening transport behavior.

Key hot spots already identified in code:
- `apply()` does `findCardForIoc(result.ioc_value)` at **line 136** and `card.querySelector('.enrichment-slot')` at **line 139** for every incoming result.
- `flushIoc()` repeats the same lookup pattern at **lines 110-120** before updating summary/copy/reputation state.
- `updatePendingIndicator()` calls `getProviderCounts()` at **line 80**, which reparses the DOM attribute every time.
- `flush()` still calls `updateDashboardCounts()` and `sortCardsBySeverity()` at **lines 202-203**.
- `finalize()` does whole-document scans at **lines 209-216**.

**What is safe to cache per IOC**
- `.ioc-card`
- `.enrichment-slot`
- `.copy-btn`
- `.ioc-context-line`
- section containers: `.enrichment-section--context`, `.enrichment-section--reputation`, `.enrichment-section--no-data`

**What should stay dynamic / not be pre-cached as fixed nodes**
- `.ioc-summary-row` (created lazily)
- `.detail-link-footer` / `.detail-link` (injected on finalize)
- provider detail rows
- `.no-data-summary-row`

That distinction matters: the stable handles are server-rendered before JS starts, while the dynamic nodes are created later by the shared pipeline.

### 2. `app/static/src/ts/modules/cards.ts` is the secondary seam, but there is no direct unit suite for it

Current cost centers:
- `findCardForIoc()` re-queries the document at **lines 33-35**.
- `updateCardVerdict()` re-finds the card at **line 47** and then its `.verdict-label` at **line 54**.
- `updateDashboardCounts()` scans every `.ioc-card` at **line 73**.
- `sortCardsBySeverity()` re-queries and re-appends the full grid at **lines 119-134**.

Important planner note: there is **no `cards.test.ts`**. Existing proof is indirect through:
- `result-application.test.ts`
- `enrichment.test.ts`
- `history.test.ts`
- browser E2E

So if the executor changes cards helpers significantly, either keep the change tiny or add direct coverage.

### 3. `app/static/src/ts/types/ioc.ts` has a cheap page-level cache candidate

`getProviderCounts()` at **lines 134-141**:
- queries `.page-results`
- reads `data-provider-counts`
- `JSON.parse()`s it

That data is immutable for the lifetime of a results page. A coordinator-local snapshot is safe and aligns with the main DOM-handle-caching change.

### 4. `enrichment.ts`, `history.ts`, and `main.ts` define the non-negotiable live/history boundary

- `main.ts` resolves the surface owner at **lines 24-59** and must keep dispatching exactly one runtime (`live`, `history`, or `static`).
- `enrichment.ts` creates one coordinator, polls every **750ms**, debounces flushes by **100ms**, and sets `data-results-runtime="live"` at **lines 194-292**.
- `history.ts` also creates one coordinator, replays stored results synchronously, never polls, and sets `data-results-runtime="history"` at **lines 74-87**.

**Do not reopen**
- polling cadence
- `since`/`next_since`
- terminal-failure handling
- owner resolution

The coordinator optimization should remain transparent to those callers.

### 5. Templates define the structural contract; JS should keep routing into it

- `app/templates/results.html` sets `data-results-owner`, `data-job-id`, `data-mode`, `data-provider-counts`, and optional `data-history-results` on `.page-results`.
- `app/templates/partials/_ioc_card.html` explicitly documents that `data-ioc-value`, `data-ioc-type`, and `data-verdict` are consumed by CSS, filter.ts, enrichment/cards logic, and E2E. Do not rename or relocate them.
- `app/templates/partials/_enrichment_slot.html` server-renders the section containers (`context`, `reputation`, `no-data`).

That means the safe optimization path is **cache stable existing nodes**, not replace them with string-template HTML or rebuild the slot structure.

### 6. Existing proof surface is already well aligned to this slice

Focused frontend unit tests:
- `app/static/src/ts/modules/result-application.test.ts`
- `app/static/src/ts/modules/enrichment.test.ts`
- `app/static/src/ts/modules/history.test.ts`
- `app/static/src/ts/modules/main.test.ts`
- `app/static/src/ts/modules/row-factory.test.ts`

I ran the current focused lanes to confirm the starting point:
- `npx vitest run app/static/src/ts/modules/enrichment.test.ts app/static/src/ts/modules/result-application.test.ts app/static/src/ts/modules/history.test.ts app/static/src/ts/modules/main.test.ts app/static/src/ts/modules/row-factory.test.ts` → **61 passed**
- `pytest tests/test_optimization_audit.py -q` → **6 passed**

Deep browser proof:
- `tests/e2e/conftest.py` arms the mocked-online route **before submit** and queues a deterministic fake job id. This is a known gotcha from memory (`MEM025`, `MEM069`): do not change the test flow to register the route after navigation.
- `tests/e2e/test_results_page.py` is the key live DOM seam: summary row creation, expand/collapse, section containers, detail link injection, loaded-slot marker, and results-owner attributes.

### 7. `tools/optimization_audit.py` is the audit source of truth; the markdown artifact is generated output

The current baseline still has one remaining `do next` row:
- `Cache IOC card/slot handles inside the shared result-application coordinator before chasing deeper render changes.`

That row lives in `BASELINE_FINDINGS` inside `tools/optimization_audit.py`, and its wording is pinned by `tests/test_optimization_audit.py`.

So S04 should:
1. update the runner constants / baseline wording,
2. update the runner test expectations,
3. regenerate `.gsd/milestones/M013/M013-AUDIT.md`.

**Do not hand-edit `.gsd/milestones/M013/M013-AUDIT.md`.** Prior slices treated it as generated output, and S04 should keep that pattern.

## Key implementation constraints / gotchas

- **Cached refs are safe across filtering and sorting.** `filter.ts` only toggles `card.style.display`; it does not replace nodes. `cards.ts` sorting re-appends the same `.ioc-card` nodes, so element identity is preserved.
- **History pages still carry `data-job-id="history"`.** Live-vs-history must continue to key off `data-results-owner` / owner resolution, not job-id presence alone.
- **R009 still rules out innerHTML shortcuts.** The current pipeline uses `createElement` + `textContent` comments/tests as a DOM-safety contract. A performance patch that switches to HTML string injection would be the wrong trade.
- **Do not widen this into a dashboard/sort redesign unless the narrow cache work is insufficient.** The audit row named card/slot caching first. Incremental dashboard counts or sort suppression could be follow-on work, but they are broader than the currently queued high-confidence fix.

## Recommendation

Keep S04 narrow and staged:

1. **Ship the coordinator-local cache first** in `result-application.ts`.
   - Cache stable nodes by IOC value.
   - Snapshot provider counts once per page/coordinator.
   - If helpful, track touched/loaded slots inside the coordinator instead of rescanning the whole document in `finalize()`.

2. **Only touch `cards.ts` surgically if the coordinator cache forces it.**
   - Prefer tiny helper additions (for example, updating an already-known card element) over a wider rewrite.
   - If cards helpers remain string-keyed, the main win still comes from removing repeated `findCardForIoc()` / slot lookups.

3. **After the frontend change is stable, update the audit runner and rerun the artifact.**
   - Reclassify the frontend finding from queued work to the truthful shipped/deferred state.
   - Keep any still-unshipped render work explicit instead of silently dropping it.

4. **Finish with the expensive proof last.**
   - This is the final slice and the final milestone rerun; proof should happen only after code + focused tests are stable.

## Natural task split for the planner

### Task 1 — Shared coordinator optimization
**Files likely touched**
- `app/static/src/ts/modules/result-application.ts`
- maybe `app/static/src/ts/modules/cards.ts`
- maybe `app/static/src/ts/types/ioc.ts`
- `app/static/src/ts/modules/result-application.test.ts`
- possibly `app/static/src/ts/modules/enrichment.test.ts`
- possibly `app/static/src/ts/modules/history.test.ts`

**Goal**
Retire repeated DOM lookups on the shared live/history path without changing user-visible behavior.

**Success bar**
- live polling still updates summary rows, copy buttons, detail links, pending text, and verdicts
- history replay still matches live output
- no change to owner resolution, polling cadence, or terminal-state semantics

### Task 2 — Audit runner / final artifact update
**Files likely touched**
- `tools/optimization_audit.py`
- `tests/test_optimization_audit.py`
- regenerated `.gsd/milestones/M013/M013-AUDIT.md`

**Goal**
Make the generated audit accurately reflect what S04 shipped and what remains deferred after the frontend fix.

**Success bar**
- runner baseline text matches the new slice reality
- test expectations match the new wording/buckets
- artifact is regenerated from the runner, not hand-edited

### Task 3 — Final rerun / milestone-close proof inputs
**Files likely touched**
- probably no source changes unless tests expose regressions
- regenerated `.gsd/milestones/M013/M013-AUDIT.md`

**Goal**
Produce the final trustworthy proof set for the last slice.

**Success bar**
- fresh `make verify-fast`
- fresh `make verify-deep`
- final audit artifact regenerated on the verified state

## Verification plan

### Fast development lanes
Use these while iterating:
- `npx vitest run app/static/src/ts/modules/enrichment.test.ts app/static/src/ts/modules/result-application.test.ts app/static/src/ts/modules/history.test.ts app/static/src/ts/modules/main.test.ts app/static/src/ts/modules/row-factory.test.ts`
- `pytest tests/test_optimization_audit.py -q`

If `cards.ts` changes materially, either broaden the Vitest selection or add a focused `cards` test file.

### Final required proof
Because this slice touches shared result application / results-page DOM state, the final proof must include:
- `make verify-fast`
- `make verify-deep`

### Final audit rerun recommendation
For the milestone-close artifact, prefer running the audit runner **last** with command captures so the markdown itself embeds the final proof state:

```bash
python3 tools/optimization_audit.py \
  --mode baseline \
  --output .gsd/milestones/M013/M013-AUDIT.md \
  --capture-command 'verify-fast::make verify-fast' \
  --capture-command 'verify-deep::make verify-deep'
```

That duplicates the expensive proof once, but it gives the cleanest end-state for the final slice: the generated audit itself contains the final rerun evidence instead of relying only on task prose.

## Planner-facing conclusion

This slice does **not** need new backend work. The narrow, high-confidence path is:
- optimize the shared frontend coordinator with stable DOM-handle caching,
- preserve the existing live/history boundary and DOM-safety rules,
- update the audit runner constants/tests,
- regenerate the audit artifact from code,
- finish with fresh fast+deep proof.

That is enough to close the remaining `frontend/render` item without reopening settled runtime/request/persistence seams.