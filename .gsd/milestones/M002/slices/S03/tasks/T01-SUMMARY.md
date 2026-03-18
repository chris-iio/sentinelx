---
id: T01
parent: S03
milestone: M002
provides:
  - Summary row as expand/collapse click target with keyboard Enter/Space support
  - Chevron SVG injected into .ioc-summary-row by row-factory.ts (no standalone button)
  - aria-expanded correctly toggled on .ioc-summary-row
  - max-height increased from 750px to 2000px to prevent provider list clipping
  - CSS chevron rotation targeting .ioc-summary-row.is-open .chevron-icon
key_files:
  - app/templates/partials/_enrichment_slot.html
  - app/static/src/ts/modules/row-factory.ts
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/input.css
  - app/static/dist/style.css
  - app/static/dist/main.js
key_decisions:
  - Chevron wrapper re-appended at end of updateSummaryRow() after textContent="" clear — preserves chevron across incremental enrichment updates
  - chevron-icon-wrapper uses margin-left:auto to float right in the flex row
patterns_established:
  - When a persistent DOM element is placed inside a container that gets cleared via textContent="", save a reference before the clear and re-append after rebuilding other children
observability_surfaces:
  - document.querySelectorAll('.ioc-summary-row.is-open').length — count of expanded panels
  - document.querySelectorAll('.ioc-summary-row .chevron-icon').length — confirms chevron injection ran
  - document.querySelectorAll('[aria-expanded="true"]').length — mirrors is-open count; mismatch = wiring bug
duration: ~20m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Wire summary-row expand toggle and fix max-height clipping

**Replaced standalone `.chevron-toggle` button with summary-row-as-click-target, injected chevron SVG into `.ioc-summary-row` via `createElement`/`createElementNS`, rewired `wireExpandToggles()` to event delegation on `.page-results` for dynamic rows, and raised `max-height` from 750px to 2000px.**

## What Happened

Executed all 4 template/TS/CSS changes as planned, with two important corrections:

**1. Chevron re-append after textContent clear:** `updateSummaryRow()` uses `summaryRow.textContent = ""` (immutable rebuild pattern) which destroys the chevron wrapper on every incremental enrichment update. Fixed by saving the `chevronWrapper` reference before the clear and re-appending it after all other children.

**2. Event delegation for dynamic rows:** The original plan called for `wireExpandToggles()` to query `.ioc-summary-row` once at `init()`. But summary rows don't exist at init time — they're created by `row-factory.ts` during the polling loop. A direct `querySelectorAll` at init would bind 0 handlers. Switched to event delegation: a single `click` + `keydown` listener on the stable `.page-results` ancestor handles all current and future summary rows via `event.target.closest(".ioc-summary-row")`.

## Verification

All verification commands run after both the initial implementation and the chevron re-append fix.

- `make typecheck` — 0 errors
- `make css` — rebuilt `app/static/dist/style.css`
- `make js-dev` — rebuilt `app/static/dist/main.js` (200.8kb)
- `pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q` — 36 passed
- `grep -c 'chevron-toggle' app/templates/partials/_enrichment_slot.html` → 0
- `grep -n 'max-height: 750px' app/static/src/input.css` → no matches
- `grep -c 'innerHTML' app/static/src/ts/modules/enrichment.ts` → 0 (code hits)
- `grep -c 'innerHTML' app/static/src/ts/modules/row-factory.ts` → 0 (code hits; 1 comment mentioning "no innerHTML" is fine)
- `grep -n 'ioc-summary-row' app/static/src/ts/modules/enrichment.ts` → lines 336, 343 (wiring present)
- `grep -o 'max-height:2000px' app/static/dist/style.css` → match confirmed

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `make typecheck` | 0 | ✅ pass | 3.4s |
| 2 | `make css` | 0 | ✅ pass | 0.5s |
| 3 | `make js-dev` | 0 | ✅ pass | 0.1s |
| 4 | `pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q` | 0 | ✅ pass (36/36) | 6.68s |
| 5 | `grep -c 'chevron-toggle' app/templates/partials/_enrichment_slot.html` | 1 (0 matches) | ✅ pass | <0.1s |
| 6 | `grep -n 'max-height: 750px' app/static/src/input.css` | 1 (no matches) | ✅ pass | <0.1s |
| 7 | `grep 'innerHTML' app/static/src/ts/modules/enrichment.ts` (code only) | 1 (no code matches) | ✅ pass | <0.1s |
| 8 | `grep 'innerHTML' app/static/src/ts/modules/row-factory.ts` (code only) | 1 (no code matches) | ✅ pass | <0.1s |
| 9 | `grep -o 'max-height:2000px' app/static/dist/style.css` | 0 | ✅ pass | <0.1s |

## Diagnostics

To inspect expand state at runtime (browser DevTools console):
```js
// How many panels are currently open?
document.querySelectorAll('.ioc-summary-row.is-open').length
// Was the chevron injected into all summary rows?
document.querySelectorAll('.ioc-summary-row .chevron-icon').length
// Does aria state match is-open count?
document.querySelectorAll('[aria-expanded="true"]').length
```

Failure modes and their signals:
- Click does nothing → `wireExpandToggles()` ran before summary rows were created (timing) — rows created after polling starts; may need to rewire on each new row (T02 concern if needed)
- Chevron disappears after first enrichment result → `updateSummaryRow()` chevron re-append fix missing
- Details clipped → `max-height:2000px` not in dist/style.css → CSS not rebuilt (`make css`)
- Pre-enrichment toggle fires → `.enrichment-slot--loaded` guard not present; check CSS rule

## Deviations

**1. Chevron re-append (unplanned fix):** `updateSummaryRow()` uses `summaryRow.textContent = ""` before rebuilding children. The chevron wrapper (injected once by `getOrCreateSummaryRow()`) would have been destroyed on the first incremental update. Added pre-clear save + post-build re-append of `chevronWrapper`.

**2. Event delegation instead of per-element binding (unplanned but necessary):** The plan called for `wireExpandToggles()` to query `.ioc-summary-row` directly. Since summary rows don't exist at `init()` time (they're created during polling), a direct `querySelectorAll` would find 0 elements. Switched to event delegation on `.page-results` so the handler works for all rows created at any point. The old `.chevron-toggle` approach worked because those buttons existed in the server-rendered template before `init()` ran.

## Known Issues

None.

## Files Created/Modified

- `app/templates/partials/_enrichment_slot.html` — removed standalone `<button class="chevron-toggle">` block; updated comment
- `app/static/src/ts/modules/row-factory.ts` — `getOrCreateSummaryRow()` now inserts before `.enrichment-details` and injects chevron SVG + a11y attrs; `updateSummaryRow()` saves/restores chevron wrapper across textContent clear
- `app/static/src/ts/modules/enrichment.ts` — `wireExpandToggles()` rewritten: queries `.ioc-summary-row`, two-step details lookup, click + keyboard handlers, aria-expanded update
- `app/static/src/input.css` — `.ioc-summary-row` gets `cursor:pointer` + `user-select:none`; `.chevron-icon-wrapper` rule added; rotation rule updated to `.ioc-summary-row.is-open`; `max-height` raised to `2000px`; old `.chevron-toggle` rules removed; loaded guard updated to `.ioc-summary-row`
- `app/static/dist/style.css` — rebuilt
- `app/static/dist/main.js` — rebuilt
