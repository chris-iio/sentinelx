---
estimated_steps: 5
estimated_files: 3
---

# T02: Inject detail page link and apply expanded-panel CSS polish

**Slice:** S03 — Inline expand + progressive disclosure
**Milestone:** M002

## Description

R004 notes: "Detail page still exists for deep dives — linked from expanded view." This task injects a "View full detail →" link at the bottom of each `.enrichment-details` panel, constructed from `data-ioc-type` and `data-ioc-value` attributes on the ancestor `.ioc-card`. It also applies CSS polish to the expanded panel — subtle background tint, border accent, summary row hover state — so the expanded view reads as a polished production tool per R003 (quiet precision, no bright non-verdict colors).

**Relevant skills:** None required — this is DOM wiring + CSS.

## Steps

1. **Edit `app/static/src/ts/modules/enrichment.ts`** — Add a function `injectDetailLink(slot: HTMLElement)` (or add the logic inline to the enrichment completion flow). This function:
   - Finds the `.enrichment-details` container within the slot
   - Finds the ancestor `.ioc-card` via `slot.closest('.ioc-card')`
   - Reads `data-ioc-type` and `data-ioc-value` from the `.ioc-card`
   - Creates a footer `<div>` with class `detail-link-footer`
   - Creates an `<a>` element with class `detail-link`
   - Sets the anchor's `textContent` to `"View full detail →"` (use the actual → character or `\u2192`)
   - Sets `href` to `/detail/${iocType}/${encodeURIComponent(iocValue)}` via `setAttribute('href', ...)`
   - Appends anchor to footer div, footer div to the end of `.enrichment-details`
   - **SEC-08:** All construction via `createElement` + `textContent` + `setAttribute`. No `innerHTML`.
   - Call this function from the enrichment completion flow — the best place is in `handleProviderResult()` after the slot is populated, or in `markEnrichmentComplete()`. Check if a `.detail-link-footer` already exists before injecting (idempotency guard — `if (details.querySelector('.detail-link-footer')) return;`).

2. **Edit `app/static/src/input.css`** — Add styles for the detail link footer:
   ```
   .detail-link-footer {
       padding: 0.5rem;
       border-top: 1px solid var(--border);
       text-align: right;
   }
   .detail-link {
       color: var(--text-secondary);
       font-size: 0.8rem;
       text-decoration: none;
       transition: color var(--duration-fast) ease;
   }
   .detail-link:hover {
       color: var(--text-primary);
       text-decoration: underline;
   }
   ```

3. **Edit `app/static/src/input.css`** — Add expanded-panel visual polish:
   - `.enrichment-details.is-open` — add `background-color: var(--bg-secondary);` and `border-left: 2px solid var(--border);` (or `var(--bg-tertiary)` — use muted design tokens only). Add a small `padding-left: 0.5rem;` to give the left-border visual breathing room inside the panel.
   - `.ioc-summary-row:hover` — add `background-color: var(--bg-hover);` and `border-radius: var(--radius-sm);` for a subtle hover highlight indicating clickability.
   - Ensure no bright colors — all values must use `--text-*`, `--bg-*`, `--border` design tokens (R003 compliance).

4. **Build and verify** — Run `make typecheck`, `make css`, `make js-dev`. All must exit 0. Run `pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q` — 36 tests must pass.

5. **Post-verification checks:**
   - `grep -c 'innerHTML' app/static/src/ts/modules/enrichment.ts app/static/src/ts/modules/row-factory.ts` → both 0 (SEC-08)
   - `grep -n 'detail-link-footer' app/static/src/input.css` → styles present
   - `grep -n 'detail-link' app/static/src/ts/modules/enrichment.ts` → injection code present
   - `grep -n 'encodeURIComponent' app/static/src/ts/modules/enrichment.ts` → present (URL encoding)
   - Verify `git show HEAD --stat` includes all key files (D017)

## Must-Haves

- [ ] "View full detail →" link injected into `.enrichment-details` panel
- [ ] Link href uses `/detail/${type}/${encodeURIComponent(value)}` pattern
- [ ] Link only injected once per panel (idempotency guard)
- [ ] All DOM construction via createElement + textContent + setAttribute (SEC-08)
- [ ] Expanded panel has subtle background tint and border accent using design tokens only
- [ ] Summary row has hover state indicating clickability
- [ ] No bright non-verdict colors introduced (R003)
- [ ] All builds pass: `make typecheck`, `make css`, `make js-dev`
- [ ] 36 E2E tests pass with no regression

## Verification

- `make typecheck && make css && make js-dev` — all exit 0
- `pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q` — 36 passed
- `grep -c 'innerHTML' app/static/src/ts/modules/enrichment.ts app/static/src/ts/modules/row-factory.ts` → both 0
- `grep -n 'detail-link-footer' app/static/src/input.css` → styles present
- `grep -n 'encodeURIComponent' app/static/src/ts/modules/enrichment.ts` → present

## Inputs

- `app/static/src/ts/modules/enrichment.ts` — T01 has already rewired `wireExpandToggles()` to use `.ioc-summary-row`. The enrichment completion flow (`handleProviderResult` ~line 290-330, `markEnrichmentComplete` ~line 169) is where the detail link injection should hook in.
- `app/static/src/input.css` — T01 has already updated chevron styles and max-height. The new CSS goes after the existing `.enrichment-details` rules (~line 1356+).
- `app/templates/partials/_ioc_card.html` — Reference only (not edited). Line 46 shows the Flask `url_for` pattern: `url_for('main.ioc_detail', ioc_type=ioc.type.value, ioc_value=ioc.value)`. The JS equivalent is `/detail/${iocType}/${encodeURIComponent(iocValue)}`.
- The `.ioc-card` element has `data-ioc-type` and `data-ioc-value` attributes — these are the source for constructing the detail link href.

## Expected Output

- `app/static/src/ts/modules/enrichment.ts` — `injectDetailLink()` function added, called from enrichment completion flow, creates footer with anchor link using createElement
- `app/static/src/input.css` — `.detail-link-footer`, `.detail-link`, `.detail-link:hover` styles added; `.enrichment-details.is-open` background/border polish added; `.ioc-summary-row:hover` style added
- `app/static/dist/style.css` — rebuilt
- `app/static/dist/main.js` — rebuilt
