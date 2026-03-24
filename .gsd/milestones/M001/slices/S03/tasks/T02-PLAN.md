---
estimated_steps: 7
estimated_files: 3
---

# T02: Add category section headers and no-data collapse

**Slice:** S03 — Visual Redesign
**Milestone:** M001

## Description

Deliver VIS-03 (category section headers) and GRP-02 (no-data collapse). These changes add structure to the `.enrichment-details` container: provider rows are visually grouped under "Reputation" and "Infrastructure Context" headers, and no-data/error rows are hidden by default behind a clickable count summary.

Both features share a critical timing constraint: they must be injected AFTER enrichment completes (when `markEnrichmentComplete()` fires), not per-result. The `sortDetailRows()` function re-sorts `.provider-detail-row` elements on each result — injecting section headers during live enrichment would cause them to become mispositioned after sorts. Post-enrichment injection into the final sorted order avoids this entirely.

**Key interaction:** `sortDetailRows()` moves `.provider-detail-row` elements but ignores non-`.provider-detail-row` elements. Section headers (`.provider-section-header`) and the no-data summary row (`.no-data-summary-row`) are NOT `.provider-detail-row` — they stay in place once inserted. This is the correct behavior.

**CONTEXT_PROVIDERS set:** `["IP Context", "DNS Records", "Cert History", "ThreatMiner", "ASN Intel"]` — these are "Infrastructure Context". Everything else is "Reputation".

**Relevant skill:** `frontend-design` — load for CSS/DOM builder guidance.

## Steps

1. **CSS — Add new classes for section headers, no-data collapse.** In `app/static/src/input.css`, add after the micro-bar classes (added in T01):
   ```css
   /* VIS-03: Category section headers */
   .provider-section-header {
       font-size: 0.65rem;
       font-weight: 700;
       text-transform: uppercase;
       letter-spacing: 0.08em;
       color: var(--text-muted);
       padding: 0.4rem 0.5rem 0.15rem;
       margin-top: 0.25rem;
       border-top: 1px solid var(--border);
   }
   .provider-section-header:first-child {
       margin-top: 0;
       border-top: none;
   }
   
   /* GRP-02: No-data collapse */
   .provider-row--no-data {
       display: none;
   }
   .no-data-expanded .provider-row--no-data {
       display: flex;
   }
   .no-data-summary-row {
       display: flex;
       align-items: center;
       gap: 0.5rem;
       padding: 0.35rem 0.5rem;
       font-size: 0.75rem;
       color: var(--text-muted);
       cursor: pointer;
       border-top: 1px solid var(--border);
       transition: color var(--duration-fast) ease;
   }
   .no-data-summary-row:hover {
       color: var(--text-secondary);
   }
   ```

2. **TypeScript — Add `.provider-row--no-data` class in `createDetailRow()`.** In `app/static/src/ts/modules/row-factory.ts`, find `createDetailRow()` (around line 314). After the line `row.className = "provider-detail-row";` (line ~321), add logic to append `.provider-row--no-data` when verdict is `"no_data"` or `"error"`:
   ```typescript
   const isNoData = verdict === "no_data" || verdict === "error";
   row.className = "provider-detail-row" + (isNoData ? " provider-row--no-data" : "");
   ```
   This ensures no-data rows are hidden via CSS from the moment they are created. The existing `data-verdict` attribute is still set normally.

3. **TypeScript — Add `createSectionHeader()` helper.** In `row-factory.ts`, add and export:
   ```typescript
   export function createSectionHeader(label: string): HTMLElement {
     const header = document.createElement("div");
     header.className = "provider-section-header";
     header.setAttribute("data-section-label", label);
     header.textContent = label;
     return header;
   }
   ```

4. **TypeScript — Add `injectSectionHeadersAndNoDataSummary()`.** In `row-factory.ts`, add and export this function. It takes a `.enrichment-slot` element (not `.enrichment-details`) so it can find the details container itself.

   **Section header logic (VIS-03):** Scan all `.provider-detail-row` elements in DOM order. Track whether each is a context row (has `.provider-context-row` class). When the category changes from the previous row, insert a `.provider-section-header` before that row. Use `CONTEXT_PROVIDERS` set or `.provider-context-row` class to detect category.

   Important detail: after `sortDetailRows()`, context rows are pinned to the TOP of the container. So the DOM order will be: [context rows...] then [verdict rows...]. The function should produce:
   - "Infrastructure Context" header before the first context row (if any context rows exist)
   - "Reputation" header before the first non-context row (if any non-context rows exist)

   **No-data summary logic (GRP-02):** Count `.provider-row--no-data` elements. If count > 0, create a `.no-data-summary-row` div with text like "5 providers had no record". Insert it before the first `.provider-row--no-data` element. Wire a click handler that toggles `.no-data-expanded` on the `.enrichment-details` container and sets `aria-expanded` on the summary row.

   **Edge cases:**
   - Zero no-data rows → skip summary row creation entirely
   - Zero context rows → skip "Infrastructure Context" header
   - Zero verdict (non-context) rows → skip "Reputation" header
   - Empty details container → return early

5. **TypeScript — Wire into `markEnrichmentComplete()`.** In `app/static/src/ts/modules/enrichment.ts`, import `injectSectionHeadersAndNoDataSummary` from `row-factory.ts`. In the `markEnrichmentComplete()` function (around line 175), after the existing completion logic, add a call to inject headers and no-data summary for each enrichment slot:
   ```typescript
   document.querySelectorAll<HTMLElement>(".enrichment-slot").forEach(slot => {
     injectSectionHeadersAndNoDataSummary(slot);
   });
   ```
   Place this AFTER any existing sort/finalization logic in `markEnrichmentComplete()`.

6. **Verify CSS builds.** Run `make css` — confirm no errors.

7. **Verify TypeScript builds and E2E.** Run `make typecheck && make js-dev && pytest tests/ -m e2e --tb=short -q` — confirm zero TS errors and 89/91 E2E baseline.

## Must-Haves

- [ ] CSS: `.provider-section-header` styled as uppercase, muted, small label with border-top separator
- [ ] CSS: `.provider-row--no-data` has `display:none`; `.no-data-expanded .provider-row--no-data` has `display:flex`
- [ ] CSS: `.no-data-summary-row` styled as muted, clickable with hover state
- [ ] `createDetailRow()` adds `.provider-row--no-data` class for `no_data` and `error` verdicts
- [ ] `createSectionHeader(label)` exported from `row-factory.ts`
- [ ] `injectSectionHeadersAndNoDataSummary(slot)` exported from `row-factory.ts`
- [ ] Section headers placed BEFORE each category's first row in final sorted DOM order
- [ ] No-data summary row shows correct count and wires click → `.no-data-expanded` toggle
- [ ] `aria-expanded` attribute on `.no-data-summary-row` tracks toggle state
- [ ] `markEnrichmentComplete()` in `enrichment.ts` calls injection function for all slots
- [ ] Edge cases handled: zero no-data rows, zero context rows, zero verdict rows, empty container
- [ ] No E2E-locked class renamed or removed
- [ ] `make typecheck && make js-dev && make css` all pass
- [ ] 89/91 E2E baseline maintained

## Verification

- `make css` — CSS builds successfully
- `make typecheck` — zero TypeScript errors
- `make js-dev` — esbuild bundles successfully
- `pytest tests/ -m e2e --tb=short -q` — 89/91 baseline maintained
- `grep -n "provider-row--no-data\|provider-section-header\|no-data-summary-row\|injectSectionHeaders" app/static/src/ts/modules/row-factory.ts` — confirms all new functions exist
- `grep -n "injectSectionHeaders" app/static/src/ts/modules/enrichment.ts` — confirms call wired in `markEnrichmentComplete()`

## Observability Impact

- **New DOM elements:** `.provider-section-header` (inspect via `document.querySelectorAll('.provider-section-header')`) and `.no-data-summary-row` (inspect via `document.querySelectorAll('.no-data-summary-row')`) appear inside `.enrichment-details` after enrichment completes.
- **Collapse state:** `.no-data-summary-row[aria-expanded]` tracks whether hidden no-data rows are shown; the parent `.enrichment-details` gains/loses `.no-data-expanded` class on toggle.
- **Hidden rows:** `.provider-row--no-data` elements have `display:none` by default — count them via `document.querySelectorAll('.provider-row--no-data').length` to verify no-data detection is working.
- **Failure visibility:** If `injectSectionHeadersAndNoDataSummary()` throws, section headers and the collapse summary will be absent after enrichment completes — detectable by zero `.provider-section-header` elements when provider rows exist. TypeScript compilation errors surface via `make typecheck`; CSS build errors via `make css`.
- **Edge-case inspection:** Zero no-data rows → no `.no-data-summary-row` in DOM. Zero context rows → no "Infrastructure Context" header. Zero verdict rows → no "Reputation" header. All inspectable via DevTools element count queries.

## Inputs

- `app/static/src/input.css` — with T01 changes already applied (micro-bar classes present)
- `app/static/src/ts/modules/row-factory.ts` — with T01 changes already applied (micro-bar in updateSummaryRow); contains `createDetailRow()` (line ~314), `createContextRow()` (line ~281), `CONTEXT_PROVIDERS` set (line ~147)
- `app/static/src/ts/modules/enrichment.ts` — contains `markEnrichmentComplete()` (line ~175), `sortDetailRows()` (line ~42), `renderEnrichmentResult()` (line ~202)
- T01 task summary — confirms micro-bar is in place and typecheck passes

## Expected Output

- `app/static/src/input.css` — new CSS classes for section headers, no-data collapse, and summary row
- `app/static/src/ts/modules/row-factory.ts` — `createSectionHeader()`, `injectSectionHeadersAndNoDataSummary()` exported; `createDetailRow()` adds `.provider-row--no-data` class
- `app/static/src/ts/modules/enrichment.ts` — `markEnrichmentComplete()` calls injection function for all slots
