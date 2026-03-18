---
estimated_steps: 6
estimated_files: 4
---

# T01: Wire summary-row expand toggle and fix max-height clipping

**Slice:** S03 — Inline expand + progressive disclosure
**Milestone:** M002

## Description

The expand/collapse mechanism exists but uses a tiny `.chevron-toggle` button as the click target. R004 requires "clicking an IOC row expands full provider details inline." This task restructures the interaction: the `.ioc-summary-row` becomes the click target, the chevron icon moves inside the summary row, keyboard Enter/Space support is added, and the `max-height: 750px` clipping cap is increased to handle IOCs with many providers.

The standalone `<button class="chevron-toggle">` is removed from the Jinja template. The chevron SVG is injected into the summary row by `row-factory.ts` (which already creates the summary row during enrichment). `enrichment.ts` `wireExpandToggles()` is rewired to bind on `.ioc-summary-row` elements. CSS is updated for the new selector paths.

**Relevant skills:** None required — this is DOM wiring + CSS.

## Steps

1. **Edit `app/templates/partials/_enrichment_slot.html`** — Remove the entire `<button class="chevron-toggle">...</button>` block (lines with the chevron SVG). Keep the comment `{# Chevron toggle — ...#}` but update it to say chevron is now injected into summary row by JS. Keep everything else: shimmer wrapper, enrichment-details container, section containers.

2. **Edit `app/static/src/ts/modules/row-factory.ts` — `getOrCreateSummaryRow()`** — The function currently does `slot.insertBefore(row, chevron)` where `chevron = slot.querySelector(".chevron-toggle")`. Since the chevron button no longer exists in the template, change the insertion logic: insert the summary row before `.enrichment-details` instead (use `slot.querySelector('.enrichment-details')` as the reference node; fallback to `slot.appendChild(row)` if not found). Then, at the end of `getOrCreateSummaryRow()`, create the chevron icon element and append it to the summary row:
   - Create a `<span>` with class `chevron-icon-wrapper`
   - Inside it, create an SVG element using `document.createElementNS('http://www.w3.org/2000/svg', 'svg')` with the same attributes as the removed template SVG: `class="chevron-icon"`, width=12, height=12, viewBox="0 0 12 12", fill="none"
   - Create the `<path>` element with `d="M4.5 2.5L8.5 6L4.5 9.5"`, stroke="currentColor", stroke-width="1.5", stroke-linecap="round", stroke-linejoin="round"
   - Append path to SVG, SVG to wrapper span, wrapper span to summary row
   - Set `role="button"`, `tabindex="0"`, `aria-expanded="false"` on the summary row element
   - **SEC-08 constraint:** ALL DOM construction via `createElement` / `createElementNS` + `setAttribute`. No `innerHTML`.

3. **Edit `app/static/src/ts/modules/enrichment.ts` — `wireExpandToggles()`** — Rewrite the function body:
   - Query `.ioc-summary-row` elements instead of `.chevron-toggle`
   - For each summary row, find the `.enrichment-details` sibling: use `summaryRow.nextElementSibling` and verify it has class `enrichment-details`. If not found, walk up to `.enrichment-slot` and query `.enrichment-details` within it.
   - On click: toggle `.is-open` on both the summary row AND the `.enrichment-details` container. Update `aria-expanded` on the summary row.
   - Add keyboard handler: on `keydown`, if `event.key === 'Enter' || event.key === ' '`, prevent default and trigger the same toggle logic.
   - Multiple rows remain independently expandable — no accordion logic.

4. **Edit `app/static/src/input.css`** — CSS changes:
   - Add to `.ioc-summary-row`: `cursor: pointer;` and add a `user-select: none;` to prevent text selection on click
   - Rename `.chevron-toggle.is-open .chevron-icon { transform: rotate(90deg); }` → `.ioc-summary-row.is-open .chevron-icon { transform: rotate(90deg); }`
   - The `.chevron-toggle` rule block (background:none, border:none, color, cursor, padding, transition, display:flex, align-items) — repurpose the relevant styles into a `.chevron-icon-wrapper` rule or inline them on `.ioc-summary-row`. The key styles to preserve: chevron color `var(--text-secondary)`, and the `.chevron-icon` transition rule.
   - The CSS guard `.enrichment-slot:not(.enrichment-slot--loaded) .chevron-toggle { display: none; }` — this guard is now implicit (summary row doesn't exist before `--loaded`), but add `.enrichment-slot:not(.enrichment-slot--loaded) .ioc-summary-row { display: none; }` as a safety fallback in case of race conditions.
   - Change `.enrichment-details.is-open { max-height: 750px; }` → `max-height: 2000px;`
   - Keep the old `.chevron-toggle` CSS rules in place but commented out or removed — they're dead code now.

5. **Build and verify** — Run `make typecheck`, `make css`, `make js-dev`. All must exit 0. Run `pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q` — 36 tests must pass.

6. **Post-verification checks:**
   - `grep -c 'chevron-toggle' app/templates/partials/_enrichment_slot.html` → 0 (button removed)
   - `grep -n 'max-height: 750px' app/static/src/input.css` → no matches
   - `grep -c 'innerHTML' app/static/src/ts/modules/enrichment.ts app/static/src/ts/modules/row-factory.ts` → 0
   - Verify `git show HEAD --stat` includes all key files (D017 — don't repeat S02's commit mistake)

## Must-Haves

- [ ] Standalone `.chevron-toggle` button removed from `_enrichment_slot.html`
- [ ] Chevron SVG injected into `.ioc-summary-row` by `row-factory.ts` using createElement/createElementNS (no innerHTML)
- [ ] `.ioc-summary-row` is the click target for expand/collapse in `enrichment.ts`
- [ ] Keyboard Enter/Space on summary row toggles expand
- [ ] `aria-expanded` attribute correctly reflects expand state
- [ ] `max-height` on `.enrichment-details.is-open` increased from 750px to 2000px
- [ ] CSS chevron rotation rule targets `.ioc-summary-row.is-open .chevron-icon`
- [ ] All builds pass: `make typecheck`, `make css`, `make js-dev`
- [ ] 36 E2E tests pass with no regression

## Verification

- `make typecheck && make css && make js-dev` — all exit 0
- `pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q` — 36 passed
- `grep -c 'chevron-toggle' app/templates/partials/_enrichment_slot.html` → 0
- `grep -n 'max-height: 750px' app/static/src/input.css` → no output
- `grep -c 'innerHTML' app/static/src/ts/modules/enrichment.ts app/static/src/ts/modules/row-factory.ts` → both 0

## Inputs

- `app/templates/partials/_enrichment_slot.html` — current template with standalone `<button class="chevron-toggle">` that must be removed
- `app/static/src/ts/modules/row-factory.ts` — `getOrCreateSummaryRow()` at ~line 231 creates summary row and inserts before `.chevron-toggle`; `updateSummaryRow()` at ~line 254 populates it
- `app/static/src/ts/modules/enrichment.ts` — `wireExpandToggles()` at ~line 341 currently wires `.chevron-toggle` click handlers; called from `init()` at ~line 421
- `app/static/src/input.css` — `.chevron-toggle` styles at ~line 1326, `.enrichment-details` expand at ~line 1356, `.ioc-summary-row` at ~line 1210
- S02 Forward Intelligence: `.enrichment-slot--loaded` class is the authoritative signal; `opacity: 0.85` base rule is intentional — don't remove it

## Expected Output

- `app/templates/partials/_enrichment_slot.html` — standalone chevron button removed, template simplified
- `app/static/src/ts/modules/row-factory.ts` — `getOrCreateSummaryRow()` injects chevron SVG into summary row, sets role/tabindex/aria-expanded
- `app/static/src/ts/modules/enrichment.ts` — `wireExpandToggles()` binds on `.ioc-summary-row` with click + keyboard handlers
- `app/static/src/input.css` — chevron rotation on `.ioc-summary-row.is-open`, max-height 2000px, summary row cursor:pointer, dead `.chevron-toggle` rules cleaned up
- `app/static/dist/style.css` — rebuilt
- `app/static/dist/main.js` — rebuilt
