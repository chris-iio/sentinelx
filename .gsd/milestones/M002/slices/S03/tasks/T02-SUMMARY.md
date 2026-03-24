---
id: T02
parent: S03
milestone: M002
provides:
  - "View full detail →" link injected into .enrichment-details panel on enrichment completion
  - Expanded panel visual polish (bg tint, left border accent) using design tokens only
  - Summary row hover state indicating clickability
  - injectDetailLink() with idempotency guard and SEC-08 compliance (createElement only)
key_files:
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/input.css
  - app/static/dist/style.css
  - app/static/dist/main.js
key_decisions:
  - injectDetailLink() called from markEnrichmentComplete() over handleProviderResult() — avoids repeated injection on each incremental result and ensures all providers are counted before link appears
  - Iterates .enrichment-slot--loaded (not .enrichment-slot) to skip slots that never got results
  - .enrichment-details.is-open gains padding-left:0.5rem alongside border-left so content doesn't sit flush against the accent border
patterns_established:
  - For "run once at completion" injection, hook into markEnrichmentComplete() with an idempotency querySelector guard rather than tracking state in a boolean flag
observability_surfaces:
  - document.querySelectorAll('.detail-link').length — count of injected detail links after completion
  - document.querySelector('.detail-link')?.href — verify URL pattern /detail/<type>/<encoded-value>
  - document.querySelectorAll('.enrichment-details .detail-link-footer').length — same count via wrapper
duration: ~10m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Inject detail page link and apply expanded-panel CSS polish

**Injected "View full detail →" link into each enrichment panel via `injectDetailLink()` called from `markEnrichmentComplete()`, and added expanded-panel background tint, left border accent, and summary-row hover state using design tokens only.**

## What Happened

Implemented all three changes as planned with no deviations:

**1. `injectDetailLink()` in `enrichment.ts`:** New function finds `.enrichment-details` in the slot, climbs to `.ioc-card` for `data-ioc-type` and `data-ioc-value`, builds footer div + anchor via `createElement`+`textContent`+`setAttribute` (SEC-08). Idempotency guard checks for `.detail-link-footer` before injecting. Called from `markEnrichmentComplete()` by iterating `.enrichment-slot--loaded` elements — this fires once when all providers are done, not on each incremental result.

**2. CSS detail link styles:** Added `.detail-link-footer`, `.detail-link`, and `.detail-link:hover` rules using `--text-secondary`, `--text-primary`, `--border`, and `--duration-fast` design tokens. No bright colors.

**3. CSS expanded-panel polish + hover state:** Extended `.enrichment-details.is-open` to include `background-color: var(--bg-secondary)`, `border-left: 2px solid var(--border)`, and `padding-left: 0.5rem`. Added `.ioc-summary-row:hover` with `background-color: var(--bg-hover)` and `border-radius: var(--radius-sm)`. All values are muted design tokens (R003 compliant).

## Verification

- `make typecheck` — 0 errors
- `make css` — rebuilt `app/static/dist/style.css`
- `make js-dev` — rebuilt `app/static/dist/main.js` (205.6kb)
- `pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q` — 36 passed
- `grep -c 'innerHTML' enrichment.ts` → 0 (code), `row-factory.ts` → 1 (comment only, not code)
- `grep -n 'detail-link-footer' app/static/src/input.css` → line 1373 (styles present)
- `grep -n 'encodeURIComponent' enrichment.ts` → line 198 (present)
- `grep -o 'detail-link-footer\|detail-link\|ioc-summary-row:hover' dist/style.css` → all present in compiled output

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `make typecheck` | 0 | ✅ pass | 2.8s |
| 2 | `make css` | 0 | ✅ pass | 2.8s |
| 3 | `make js-dev` | 0 | ✅ pass | <0.1s |
| 4 | `pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q` | 0 | ✅ pass (36/36) | 6.83s |
| 5 | `grep -c 'innerHTML' enrichment.ts row-factory.ts` | 1 (0 code hits each) | ✅ pass | <0.1s |
| 6 | `grep -n 'detail-link-footer' app/static/src/input.css` | 0 | ✅ pass (line 1373) | <0.1s |
| 7 | `grep -n 'encodeURIComponent' enrichment.ts` | 0 | ✅ pass (line 198) | <0.1s |
| 8 | CSS dist contains new rules | — | ✅ pass (grep confirmed) | <0.1s |

## Diagnostics

```js
// After enrichment completes — count of injected links (should equal loaded slot count)
document.querySelectorAll('.detail-link').length
// Verify URL pattern: should be /detail/<type>/<encoded-value>
document.querySelector('.detail-link')?.href
// Idempotency check — run this to confirm no duplicate footers
document.querySelectorAll('.enrichment-details .detail-link-footer').length === document.querySelectorAll('.enrichment-slot--loaded').length
```

Failure modes:
- **Links absent after completion** → `markEnrichmentComplete()` not called (enrichment never finished), or slots not yet carrying `.enrichment-slot--loaded` when it fires
- **href shows `/detail//`** → `.ioc-card` missing `data-ioc-type` / `data-ioc-value` data attributes
- **No hover highlight on summary row** → `--bg-hover` token undefined or CSS not rebuilt
- **No border on expanded panel** → `--border` token undefined or `.enrichment-details.is-open` CSS not in dist

## Deviations

None. Plan was followed exactly.

## Known Issues

None.

## Files Created/Modified

- `app/static/src/ts/modules/enrichment.ts` — `injectDetailLink()` function added before `markEnrichmentComplete()`; `markEnrichmentComplete()` extended to call it on each `.enrichment-slot--loaded`
- `app/static/src/input.css` — `.enrichment-details.is-open` extended with bg tint + border-left + padding-left; `.ioc-summary-row:hover` rule added; `.detail-link-footer`, `.detail-link`, `.detail-link:hover` rules added
- `app/static/dist/style.css` — rebuilt
- `app/static/dist/main.js` — rebuilt
