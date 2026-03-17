---
estimated_steps: 5
estimated_files: 4
---

# T01: Add template sections and wire JS routing to section containers

**Slice:** S04 — Template Restructuring
**Milestone:** M001

## Description

Deliver the core GRP-01 structural change: three explicit `.enrichment-section` containers in the `_enrichment_slot.html` Jinja template, with JS routing updated to place each provider row into the correct section at render time. This is an atomic change — template, JS routing, sort simplification, post-enrichment cleanup, and CSS must all land together.

S03 currently injects section headers via JavaScript post-enrichment (`injectSectionHeadersAndNoDataSummary()` in row-factory.ts). This task promotes the section structure into the server-rendered HTML template and simplifies the JS to match.

**Relevant installed skills:** `lint` (for formatting checks after edits).

## Steps

1. **Modify `_enrichment_slot.html`** — Inside the existing `.enrichment-details` div, add three child divs:
   ```html
   <div class="enrichment-section enrichment-section--context">
       <div class="provider-section-header">Infrastructure Context</div>
   </div>
   <div class="enrichment-section enrichment-section--reputation">
       <div class="provider-section-header">Reputation</div>
   </div>
   <div class="enrichment-section enrichment-section--no-data">
       <div class="provider-section-header">No Data</div>
   </div>
   ```
   Keep the `.enrichment-details` outer div unchanged — it must remain the immediate next sibling of `.chevron-toggle` (chevron adjacency constraint). Do NOT add any new Jinja template variables.

2. **Update `renderEnrichmentResult()` in `enrichment.ts`** — Two routing changes:
   - **Context path** (the `CONTEXT_PROVIDERS.has(result.provider)` branch, around line 233): Change `slot.querySelector(".enrichment-details")` to `slot.querySelector(".enrichment-section--context")`. The `insertBefore(..., firstChild)` call stays as-is (context rows still prepend within their section).
   - **Verdict path** (around line 307): Instead of appending to `.enrichment-details`, route based on verdict:
     - If verdict is `"no_data"` or `"error"`: append to `slot.querySelector(".enrichment-section--no-data")`
     - Otherwise (malicious, suspicious, clean, undetected): append to `slot.querySelector(".enrichment-section--reputation")`
   - The `sortDetailRows()` call must pass the reputation section container, not `.enrichment-details`.

3. **Simplify `sortDetailRows()` in `enrichment.ts`** — Remove the context-row-pinning block (lines ~64-69 that query `[data-verdict="context"]` and `insertBefore` to first child). Context rows now live in their own section, so pinning is unnecessary. The sort function itself still works — it sorts `.provider-detail-row` children within whatever container it receives (which will now be `.enrichment-section--reputation`).

4. **Simplify `injectSectionHeadersAndNoDataSummary()` in `row-factory.ts`** — Major changes:
   - **Remove ALL section header injection logic** — delete the VIS-03 block that finds `firstContextRow`/`firstVerdictRow` and calls `createSectionHeader()`. Headers are now in the template.
   - **Retarget no-data logic** — Change queries to look inside `.enrichment-section--no-data` instead of `.enrichment-details`:
     - `const noDataSection = slot.querySelector<HTMLElement>(".enrichment-section--no-data");`
     - Query `.provider-row--no-data` within `noDataSection`
     - Insert summary row into `noDataSection` (before first no-data row)
     - Toggle `.no-data-expanded` class on `noDataSection` (not on `.enrichment-details`)
   - Keep `createSectionHeader()` function definition for now (T02 will assess if it can be removed).

5. **Add CSS in `input.css`** — Add rules for the new section structure:
   - **Empty section hiding:** `.enrichment-section:not(:has(.provider-detail-row)) { display: none; }` — hides sections with no provider rows (the static header alone won't prevent hiding since it's not a `.provider-detail-row`).
   - **No-data visibility override:** `.enrichment-section--no-data .provider-row--no-data { display: flex; }` — Override the existing `.provider-row--no-data { display: none; }` rule so no-data rows ARE visible inside their designated section. They should be visible by default within the no-data section, but still hidden until the summary row toggles expansion.
     
     Actually, re-examine the CSS flow: Currently `.provider-row--no-data { display: none; }` hides all no-data rows everywhere, and `.no-data-expanded .provider-row--no-data { display: flex; }` shows them when the container has `.no-data-expanded`. With section-based routing, no-data rows are INSIDE `.enrichment-section--no-data`. The hide-by-default + expand-to-show pattern should still work — but the `.no-data-expanded` class now goes on `.enrichment-section--no-data` (not `.enrichment-details`). Update the CSS selector accordingly:
     - Change `.no-data-expanded .provider-row--no-data { display: flex; }` to `.enrichment-section--no-data.no-data-expanded .provider-row--no-data { display: flex; }`
     - The existing `.provider-row--no-data { display: none; }` stays.
   - **Max-height increase:** Change `.enrichment-details.is-open { max-height: 600px; }` to `max-height: 750px;` — S03 forward intel flagged that additional section wrapper chrome (~60px for 3 headers) could cause clipping.
   - **Section container styling:** `.enrichment-section` needs no special styling — it's a transparent structural wrapper.

6. **Build** — Run `make typecheck && make js-dev && make css` to verify everything compiles.

## Must-Haves

- [ ] `_enrichment_slot.html` has three `.enrichment-section` children inside `.enrichment-details`, each with a `.provider-section-header`
- [ ] `renderEnrichmentResult()` routes context rows to `.enrichment-section--context`
- [ ] `renderEnrichmentResult()` routes no-data/error rows to `.enrichment-section--no-data`
- [ ] `renderEnrichmentResult()` routes reputation rows to `.enrichment-section--reputation`
- [ ] `sortDetailRows()` has no context-pinning block
- [ ] `injectSectionHeadersAndNoDataSummary()` does not call `createSectionHeader()`
- [ ] No-data collapse toggle scoped to `.enrichment-section--no-data` container
- [ ] CSS hides empty sections via `:has()` selector
- [ ] `.enrichment-details.is-open` max-height increased to 750px
- [ ] Zero `innerHTML` usage (SEC-08)
- [ ] `.enrichment-details` remains immediate next sibling of `.chevron-toggle`
- [ ] `make typecheck && make js-dev && make css` all succeed

## Verification

- `make typecheck` — zero TypeScript errors
- `make js-dev` — esbuild bundle succeeds
- `make css` — Tailwind rebuild succeeds
- Template inspection: `grep -c "enrichment-section" app/templates/partials/_enrichment_slot.html` = 6 (3 opening class refs + 3 div elements with modifier classes)
- `grep "createSectionHeader" app/static/src/ts/modules/row-factory.ts` — function exists but NOT called from `injectSectionHeadersAndNoDataSummary`
- `grep "insertBefore(cr, detailsContainer.firstChild)" app/static/src/ts/modules/enrichment.ts` — zero results (context pinning removed)
- `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` — zero results

## Inputs

- `app/templates/partials/_enrichment_slot.html` — current 21 LOC template with single `.enrichment-details` div
- `app/static/src/ts/modules/enrichment.ts` — current routing puts all rows into `.enrichment-details`; `sortDetailRows` has context-pinning
- `app/static/src/ts/modules/row-factory.ts` — `injectSectionHeadersAndNoDataSummary()` creates section headers via JS and handles no-data collapse
- `app/static/src/input.css` — existing `.provider-section-header`, `.provider-row--no-data`, `.no-data-expanded`, `.enrichment-details` rules
- S03 forward intel: max-height 600px may clip with added chrome; `.provider-row--no-data` class must remain on no-data rows

## Expected Output

- `app/templates/partials/_enrichment_slot.html` — three `.enrichment-section` divs with static headers inside `.enrichment-details`
- `app/static/src/ts/modules/enrichment.ts` — routing targets section-specific containers; `sortDetailRows` simplified (no context pinning)
- `app/static/src/ts/modules/row-factory.ts` — `injectSectionHeadersAndNoDataSummary()` simplified to no-data summary only, scoped to `.enrichment-section--no-data`
- `app/static/src/input.css` — empty-section hiding rule, updated no-data-expanded selector, max-height 750px
- `app/static/dist/main.js` — rebuilt bundle
- `app/static/dist/style.css` — rebuilt CSS
