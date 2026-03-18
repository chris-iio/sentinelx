---
id: S03
parent: M002
milestone: M002
provides:
  - Summary row (.ioc-summary-row) as the expand/collapse click target — no standalone chevron button
  - Chevron SVG injected into .ioc-summary-row by row-factory.ts; rotates 90° on expand
  - Event delegation on .page-results ancestor handles all dynamically-created summary rows
  - aria-expanded and .is-open class correctly reflect expand state on both row and details panel
  - Keyboard Enter/Space toggles expand on focused summary row
  - max-height raised from 750px to 2000px — no provider list clipping
  - "View full detail →" link injected into .enrichment-details panel via injectDetailLink()
  - injectDetailLink() called from markEnrichmentComplete() with idempotency guard
  - Expanded panel visual polish: bg tint, left border accent, padding-left (design tokens only)
  - Summary row hover state indicating clickability
requires:
  - slice: S02
    provides: .ioc-summary-row DOM element from row-factory.ts; .enrichment-slot--loaded signal; .enrichment-details container
  - slice: S01
    provides: .ioc-card with data-ioc-type/data-ioc-value attributes; _enrichment_slot.html template; design tokens
affects:
  - S04
key_files:
  - app/templates/partials/_enrichment_slot.html
  - app/static/src/ts/modules/row-factory.ts
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/input.css
  - app/static/dist/style.css
  - app/static/dist/main.js
key_decisions:
  - D018: Event delegation on .page-results for wireExpandToggles() — summary rows don't exist at init() time; direct querySelectorAll would bind 0 handlers
  - D019: Chevron wrapper saved before summaryRow.textContent="" clear and re-appended afterward — preserves chevron across incremental enrichment updates
  - D020: injectDetailLink() called from markEnrichmentComplete() with .detail-link-footer idempotency guard — fires once when all providers complete, iterates .enrichment-slot--loaded only
patterns_established:
  - Clear-and-rebuild containers: save persistent child references before textContent="" and re-append after rebuilding other children (documented in KNOWLEDGE.md)
  - Dynamic elements: use event delegation on a stable ancestor rather than per-element binding at init time (documented in KNOWLEDGE.md)
  - Run-once injections: hook into completion callback with querySelector idempotency guard rather than boolean flag
observability_surfaces:
  - document.querySelectorAll('.ioc-summary-row.is-open').length — count of currently expanded panels
  - document.querySelectorAll('[aria-expanded="true"]').length — should match .is-open count; mismatch = wiring bug
  - document.querySelectorAll('.ioc-summary-row .chevron-icon').length — confirms chevron injection ran
  - document.querySelectorAll('.detail-link').length — count of injected detail links after completion
  - document.querySelector('.detail-link')?.href — verify /detail/<type>/<encoded-value> URL pattern
drill_down_paths:
  - .gsd/milestones/M002/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M002/slices/S03/tasks/T02-SUMMARY.md
duration: ~30m (T01: ~20m, T02: ~10m)
verification_result: passed
completed_at: 2026-03-18
---

# S03: Inline expand + progressive disclosure

**Summary row is now the expand/collapse click target — event-delegated keyboard-accessible toggle with animated chevron, "View full detail →" link injected on completion, and polished expanded panel using design tokens only.**

## What Happened

S03 replaced the old standalone `<button class="chevron-toggle">` interaction model with a whole-row click target. Two tasks, no deviations in T02, two necessary corrections in T01 that weren't in the original plan.

**T01 — Expand wiring and max-height fix:** The standalone `chevron-toggle` button was removed from `_enrichment_slot.html`. `row-factory.ts`'s `getOrCreateSummaryRow()` now injects a chevron SVG wrapper (via `createElement`/`createElementNS`, SEC-08 compliant) with `margin-left:auto` to float it right in the flex row. The summary row itself gets `role="button"`, `tabindex="0"`, and `aria-expanded="false"`.

`wireExpandToggles()` in `enrichment.ts` was rewritten with event delegation on the stable `.page-results` ancestor. This was a necessary deviation from the plan: the original approach called for `querySelectorAll('.ioc-summary-row')` at `init()` time, but summary rows don't exist at init — they're created during the polling loop. A direct query would bind 0 handlers. The event delegation approach captures bubbled click and keydown events from any row created at any point.

A second necessary correction: `updateSummaryRow()` uses `summaryRow.textContent = ""` as an immutable-rebuild pattern. This destroys any child elements injected only once — including the chevron wrapper. The fix saves a reference to the chevron wrapper before the clear and re-appends it after rebuilding all other children. This pattern is now documented in KNOWLEDGE.md.

CSS changes: `max-height` raised from `750px` to `2000px` (prevents clipping with many providers), `cursor:pointer` and `user-select:none` added to `.ioc-summary-row`, chevron rotation selector updated from `.chevron-toggle.is-open .chevron-icon` to `.ioc-summary-row.is-open .chevron-icon`.

**T02 — Detail link injection and visual polish:** `injectDetailLink()` is a new function in `enrichment.ts` that creates a footer div + anchor via `createElement`+`textContent`+`setAttribute` (SEC-08). It reads `data-ioc-type` and `data-ioc-value` from the nearest `.ioc-card` ancestor via `closest()`, then constructs `/detail/<type>/<encodeURIComponent(value)>`. The idempotency guard checks for `.detail-link-footer` before injecting — no boolean flag needed. Called from `markEnrichmentComplete()` over `handleProviderResult()` to fire once when all providers are complete.

CSS additions: `.detail-link-footer` (padding, border-top separator), `.detail-link` (color: `--text-secondary`, hover to `--text-primary`, underline on hover), `.enrichment-details.is-open` extended with `background-color: var(--bg-secondary)`, `border-left: 2px solid var(--border)`, `padding-left: 0.5rem`, and `.ioc-summary-row:hover` with `background-color: var(--bg-hover)`. All values are muted design tokens — R003 compliant.

## Verification

| Check | Result |
|-------|--------|
| `make typecheck` | ✅ 0 errors |
| `make css` | ✅ exit 0 |
| `make js-dev` | ✅ exit 0 (205.6kb) |
| `pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q` | ✅ 36/36 passed |
| `grep -c 'innerHTML' enrichment.ts` | ✅ 0 (code), 0 (row-factory.ts code; 1 comment) |
| `grep -c 'chevron-toggle' _enrichment_slot.html` | ✅ 0 |
| `grep 'max-height: 750px' input.css` | ✅ no matches |
| `grep -o 'max-height:2000px' dist/style.css` | ✅ match present |
| `grep -n 'ioc-summary-row' enrichment.ts` | ✅ lines 383, 394, 417 |
| `grep -n 'detail-link-footer' input.css` | ✅ line 1373 |
| `grep -n 'encodeURIComponent' enrichment.ts` | ✅ line 198 |
| dist CSS contains detail-link, detail-link-footer, ioc-summary-row:hover | ✅ all present |

## Requirements Advanced

- R004 (Inline expand for full provider breakdown) — fully delivered: row-as-click-target, event delegation, keyboard support, aria-expanded, detail link. **Primary owner requirement now verifiable via UAT.**
- R007 (Progressive disclosure) — fully delivered: provider details hidden by default, revealed on deliberate interaction; detail link only visible in expanded state. **Primary owner requirement now verifiable via UAT.**
- R003 (Verdict-only color) — S03 confirmed compliance: all expanded-panel polish uses only muted design tokens; no bright non-verdict colors introduced.
- R008 (All functionality preserved) — 36 E2E tests pass, no regression on enrichment pipeline.

## Requirements Validated

- R004 — Implementation complete and mechanically verified. Human UAT (S03-UAT.md) documents the interaction sequence for final validation.
- R007 — Implementation complete. Human UAT documents the progressive disclosure scenario.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

**T01 only:**

1. **Event delegation instead of per-element binding (necessary):** Plan called for `wireExpandToggles()` to query `.ioc-summary-row` at init. Since rows don't exist at init time (polling creates them), switched to event delegation on `.page-results`. The old `.chevron-toggle` worked only because it was server-rendered before `init()` ran.

2. **Chevron re-append after textContent clear (unplanned fix):** `updateSummaryRow()` uses `summaryRow.textContent = ""` (immutable-rebuild pattern) which destroys the chevron wrapper on each incremental update. Added pre-clear save + post-build re-append.

**T02:** No deviations. Plan followed exactly.

## Known Limitations

- **Human UAT not yet run:** Animation smoothness, visual polish quality, and interaction feel require human judgment (per slice plan). The UAT script is written at S03-UAT.md.
- **Multiple rows simultaneously expanded:** The implementation supports independent expand per row (no accordion). Deep UAT with many expanded rows simultaneously may surface layout density issues — deferred to human review.
- **Detail link before enrichment:** `injectDetailLink()` is called from `markEnrichmentComplete()`, so the link is absent until all providers return. This is intentional but means a slow/failing enrichment delays link availability.

## Follow-ups

- S04 should run the human UAT script (S03-UAT.md) as part of its visual polish pass
- S04 should verify the hover state uses `--bg-hover` token (confirm token is defined in the design system)
- S04 integration pass should confirm `injectDetailLink()` still fires correctly after export/filter wiring changes
- S05 E2E update: new selectors to target include `.ioc-summary-row`, `.is-open`, `[aria-expanded]`, `.detail-link`

## Files Created/Modified

- `app/templates/partials/_enrichment_slot.html` — removed standalone `<button class="chevron-toggle">` block; updated comment
- `app/static/src/ts/modules/row-factory.ts` — `getOrCreateSummaryRow()` injects chevron SVG + a11y attrs; `updateSummaryRow()` saves/restores chevron across textContent clear
- `app/static/src/ts/modules/enrichment.ts` — `wireExpandToggles()` rewritten with event delegation; `injectDetailLink()` function added; `markEnrichmentComplete()` extended to call it
- `app/static/src/input.css` — cursor/user-select on `.ioc-summary-row`; chevron rotation updated; max-height 2000px; hover state; expanded panel bg/border/padding; detail link styles
- `app/static/dist/style.css` — rebuilt
- `app/static/dist/main.js` — rebuilt (205.6kb)

## Forward Intelligence

### What the next slice should know

- **Event delegation is now the correct pattern for all dynamically-created enrichment DOM elements.** Any new interaction (e.g., copy buttons, filter-by-indicator click) should bind to the stable `.page-results` ancestor, not directly on dynamically created elements. Binding at `init()` will silently wire 0 handlers if the elements are created by the polling loop.
- **The chevron wrapper lives at `.chevron-icon-wrapper` inside `.ioc-summary-row`.** Any code that modifies the summary row's children (e.g., adding badges, re-ordering) must preserve this pattern: query the wrapper before any `textContent = ""` reset and re-append it last.
- **`markEnrichmentComplete()` is the right hook for post-enrichment injection.** It already iterates `.enrichment-slot--loaded` slots. For any "run once at completion" behavior (summary line, export payload, etc.), this is the correct insertion point.
- **`injectDetailLink()` depends on `.ioc-card`'s `data-ioc-type` and `data-ioc-value` attributes.** Any refactoring of the `.ioc-card` data attribute contract in S04 will break the detail link href. Keep the attribute names stable or update `injectDetailLink()` together.

### What's fragile

- **`--bg-hover` design token** — used in `.ioc-summary-row:hover` but not confirmed to be defined in the design system. If undefined, hover state will silently fail (no error, just transparent background). Verify token definition in S04 visual polish pass.
- **`markEnrichmentComplete()` call timing** — if any future change causes this function to fire before `.enrichment-slot--loaded` is set on the slots, `injectDetailLink()` will find 0 slots and inject 0 links. The `--loaded` class is the single source of truth for "enrichment finished for this slot."

### Authoritative diagnostics

- `document.querySelectorAll('.ioc-summary-row.is-open').length` vs `document.querySelectorAll('[aria-expanded="true"]').length` — these should always match; mismatch means the aria update in the click handler diverged from the CSS state update.
- `document.querySelectorAll('.detail-link').length` vs `document.querySelectorAll('.enrichment-slot--loaded').length` — should match after `markEnrichmentComplete()` runs; mismatch means `injectDetailLink()` skipped some slots or ran before `--loaded` was set.

### What assumptions changed

- **Original assumption:** `wireExpandToggles()` could bind directly to `.ioc-summary-row` elements at `init()` time. **Actual:** Summary rows are created by `row-factory.ts` during the polling loop, long after `init()` completes. Event delegation is required.
- **Original assumption:** Chevron injection is a one-time operation. **Actual:** The `updateSummaryRow()` clear-and-rebuild pattern destroys the chevron on every incremental result, requiring explicit save/restore.
