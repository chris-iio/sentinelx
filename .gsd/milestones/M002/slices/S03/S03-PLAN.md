# S03: Inline expand + progressive disclosure

**Goal:** Clicking an IOC summary row expands full provider details inline with smooth animation, a "View full detail →" link, and polished visual treatment. The expand mechanism is the natural progressive disclosure surface — important data visible at a glance (S02), full breakdown on demand.
**Demo:** After enrichment completes, click any IOC's summary row → provider details expand below with smooth animation. Chevron rotates. Click again → collapses. "View full detail →" link at bottom of expanded panel navigates to the correct detail page. Multiple rows expand independently. Keyboard Enter/Space on focused summary row toggles expand.

## Must-Haves

- Summary row (`.ioc-summary-row`) is the click target for expand/collapse — not a separate chevron button
- Chevron icon moves into the summary row as a visual rotation indicator
- Keyboard accessible: Tab to summary row, Enter/Space toggles expand
- `aria-expanded` correctly reflects state on the summary row
- Multiple rows expand independently (no accordion collapse-others)
- Expand not accessible before enrichment loads (`.enrichment-slot--loaded` gating is implicit — no summary row exists until enrichment writes one)
- "View full detail →" link in expanded panel, constructed from `data-ioc-type` and `data-ioc-value` via `encodeURIComponent()` (SEC-08: no innerHTML)
- `max-height` increased to prevent clipping with many providers
- Expanded panel has subtle visual separation (background tint, border accent)
- All DOM construction uses `createElement` + `textContent` / `setAttribute` — no `innerHTML` (SEC-08)
- No bright non-verdict colors introduced (R003)
- Existing selector names preserved: `.ioc-card`, `.enrichment-slot`, `.enrichment-details` (D015)

## Proof Level

- This slice proves: integration — the expand/collapse wiring connects the enrichment pipeline (S02) to the user interaction model
- Real runtime required: yes — expand/collapse is a DOM interaction that requires browser context
- Human/UAT required: yes — animation smoothness, visual polish quality, and interaction feel require human judgment

## Verification

- `make typecheck` — zero errors, no new `any` types
- `make css` — exit 0
- `make js-dev` — exit 0
- `pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q` — 36 tests pass (no regression)
- `grep -c 'innerHTML' app/static/src/ts/modules/enrichment.ts app/static/src/ts/modules/row-factory.ts` — 0 occurrences (SEC-08)
- `grep -n 'chevron-toggle' app/templates/partials/_enrichment_slot.html` — no matches (standalone button removed)
- `grep -n 'ioc-summary-row' app/static/src/ts/modules/enrichment.ts` — matches present (new wiring target)
- `grep -n 'max-height: 750px' app/static/src/input.css` — no matches (clipping fix applied)
- Manual verification (human UAT, documented for S04):
  - Click summary row → details expand with smooth animation
  - Click again → details collapse
  - Chevron rotates 90° on expand, back on collapse
  - Multiple rows independently expandable
  - "View full detail →" link visible, navigates to `/detail/<type>/<value>`
  - Tab + Enter/Space toggles expand
  - Pre-enrichment: no summary row visible, no expand possible

## Observability / Diagnostics

- Runtime signals: `.is-open` class on `.ioc-summary-row` and `.enrichment-details` indicates expand state; `aria-expanded` attribute on summary row reflects the same
- Inspection surfaces: `document.querySelectorAll('.ioc-summary-row.is-open').length` in devtools shows count of currently expanded rows; `document.querySelectorAll('.detail-link').length` shows count of detail links injected
- Failure visibility: If expand doesn't work, check (1) `.enrichment-slot--loaded` present (enrichment pipeline OK), (2) `.ioc-summary-row` exists (row-factory created it), (3) click handler bound (enrichment.ts `wireExpandToggles` ran)

## Integration Closure

- Upstream surfaces consumed: `.enrichment-slot--loaded` class from enrichment.ts (S02 signal), `.ioc-summary-row` from row-factory.ts (S02 DOM), `.enrichment-details` container from `_enrichment_slot.html` (S01 template), `data-ioc-type` / `data-ioc-value` from `.ioc-card` (S01 DOM contract)
- New wiring introduced in this slice: summary-row click → expand/collapse toggle, detail link injection into expanded panel
- What remains before the milestone is truly usable end-to-end: export integration, filter wiring, progress bar, security verification (S04), E2E test update (S05)

## Tasks

- [x] **T01: Wire summary-row expand toggle and fix max-height clipping** `est:45m`
  - Why: R004 requires "clicking an IOC row expands full provider details inline." Currently only a tiny chevron button toggles. This task restructures the interaction model so the summary row is the click target, moves the chevron icon into the summary row, adds keyboard support, and fixes the max-height clipping issue.
  - Files: `app/templates/partials/_enrichment_slot.html`, `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/modules/row-factory.ts`, `app/static/src/input.css`
  - Do: (1) Remove the standalone `<button class="chevron-toggle">` from `_enrichment_slot.html`. (2) In `row-factory.ts` `getOrCreateSummaryRow()`, append a chevron SVG icon element to the summary row — use `createElement`+`setAttribute`, no innerHTML. Add `role="button"`, `tabindex="0"`, `aria-expanded="false"` to the summary row element. Remove the `insertBefore(row, chevron)` logic since the chevron button no longer exists in the template. (3) In `enrichment.ts` `wireExpandToggles()`, rewire to query `.ioc-summary-row` elements instead of `.chevron-toggle`. Toggle `.is-open` on both the summary row and its sibling `.enrichment-details`. Handle keyboard Enter/Space. Update `aria-expanded`. (4) In `input.css`, change `.enrichment-details.is-open { max-height: 750px }` to `max-height: 2000px`. Update `.chevron-toggle.is-open .chevron-icon` to `.ioc-summary-row.is-open .chevron-icon`. Add `cursor: pointer` to `.ioc-summary-row`. Update the CSS guard from `.enrichment-slot:not(.enrichment-slot--loaded) .chevron-toggle` to use the summary row if needed (implicit guard: summary row doesn't exist before `--loaded`). SEC-08: all DOM construction via createElement+textContent+setAttribute.
  - Verify: `make typecheck && make css && make js-dev` all exit 0. `pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q` — 36 pass. `grep -c 'chevron-toggle' app/templates/partials/_enrichment_slot.html` returns 0. `grep -n 'max-height: 750px' app/static/src/input.css` returns no matches.
  - Done when: Summary row is the expand/collapse click target with keyboard support, chevron is inside the summary row, max-height increased, all builds and tests pass.

- [x] **T02: Inject detail page link and apply expanded-panel CSS polish** `est:30m`
  - Why: R004 says "detail page still exists for deep dives — linked from expanded view." R003 requires no bright non-verdict colors. This task adds the "View full detail →" link inside the expanded panel and applies visual polish (background tint, border accent, hover states) to make the expanded panel feel like a production tool.
  - Files: `app/static/src/ts/modules/enrichment.ts`, `app/static/src/input.css`
  - Do: (1) In `enrichment.ts`, after enrichment results are rendered into `.enrichment-details` (in the `handleProviderResult` flow or `markEnrichmentComplete`), inject a footer element at the bottom of `.enrichment-details` with class `detail-link-footer`. Create an anchor element with class `detail-link`, text "View full detail →", and href `/detail/${iocType}/${encodeURIComponent(iocValue)}` — read `data-ioc-type` and `data-ioc-value` from the ancestor `.ioc-card` via `closest('.ioc-card')`. SEC-08: use createElement+textContent+setAttribute only. (2) In `input.css`, add styles for `.detail-link-footer` (padding, border-top, text-align) and `.detail-link` (color: var(--text-secondary), hover to var(--text-primary), font-size: 0.8rem, no underline by default, underline on hover). (3) Add expanded-panel visual polish: `.enrichment-details.is-open` gets a subtle `background-color: var(--bg-secondary)` and `border-left: 2px solid var(--border)` or similar muted accent. (4) Add `.ioc-summary-row:hover` style (subtle background highlight). (5) Verify no innerHTML usage, no bright non-verdict colors.
  - Verify: `make typecheck && make css && make js-dev` all exit 0. `pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q` — 36 pass. `grep -c 'innerHTML' app/static/src/ts/modules/enrichment.ts app/static/src/ts/modules/row-factory.ts` returns 0. `grep -n 'detail-link' app/static/src/ts/modules/enrichment.ts` shows link injection code present. `grep -n 'detail-link-footer' app/static/src/input.css` shows styles present.
  - Done when: "View full detail →" link renders inside expanded panel with correct href pattern, expanded panel has polished visual treatment, all builds and tests pass, SEC-08 and R003 verified.

## Files Likely Touched

- `app/templates/partials/_enrichment_slot.html`
- `app/static/src/ts/modules/enrichment.ts`
- `app/static/src/ts/modules/row-factory.ts`
- `app/static/src/input.css`
- `app/static/dist/style.css` (rebuilt)
- `app/static/dist/main.js` (rebuilt)
