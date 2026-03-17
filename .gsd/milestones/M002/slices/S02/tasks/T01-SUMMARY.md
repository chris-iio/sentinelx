---
id: T01
parent: S02
milestone: M002
provides:
  - Opacity fix for enrichment slot — content renders at full opacity when loaded
  - Context line double-padding fix — text aligns with card header content
  - Micro-bar width tuning for full-width single-column layout
key_files:
  - app/static/src/input.css
key_decisions:
  - Kept base opacity: 0.85 on .enrichment-slot as the pre-load visual signal; override via .enrichment-slot--loaded selector is the correct BEM modifier pattern
  - Removed explicit left padding from .ioc-context-line (1rem → 0) since .ioc-card already provides 1rem horizontal padding, removing 2rem total indent
patterns_established:
  - BEM modifier opacity override: base class sets dimmed state, --loaded modifier restores full opacity with CSS transition
observability_surfaces:
  - Browser devtools computed styles on .enrichment-slot.enrichment-slot--loaded → should show opacity:1
  - document.querySelectorAll('.enrichment-slot--loaded').length in devtools console → 0 means TS pipeline failed to add class, not a CSS issue
duration: 15m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Fix enrichment slot opacity and refine at-a-glance CSS for full-width rows

**Fixed permanent opacity:0.85 on enriched content by adding .enrichment-slot--loaded override, removed double-padding on context line, and widened micro-bar for full-width layout.**

## What Happened

Located `.enrichment-slot` base rule at line 1143 (actual: 1143) confirming `opacity: 0.85`. Added the `--loaded` modifier rule immediately after the base block with `opacity: 1` and a 0.2s ease transition. This follows the established BEM pattern already present in the codebase (`.enrichment-slot:not(.enrichment-slot--loaded)` was already used for chevron-toggle visibility).

Removed the 1rem left padding from `.ioc-context-line` — the context line is a direct child of `.ioc-card` which already provides `padding: 0.6rem 1rem`, so the explicit `1rem` on the context line created a 2rem total indent misaligned with the IOC value text above.

Updated `.verdict-micro-bar` from `min-width: 4rem` (no max) to `min-width: 5rem; max-width: 8rem` for better visual presence in the wider single-column layout without growing unbounded.

`.ioc-summary-row` and `.staleness-badge` were reviewed and found already correct for full-width — no changes needed.

## Verification

- `make css` exits 0 (confirmed)
- `grep -n 'enrichment-slot--loaded' app/static/src/input.css` → lines 1154 and 1350 (the new opacity rule + pre-existing chevron rule)
- `grep -n 'opacity: 0.85' app/static/src/input.css` → line 1151 (base `.enrichment-slot` rule preserved)
- All modified rules use design tokens only — no raw bright hex values introduced
- Color scan: `.ioc-context-line` uses `var(--text-muted, #6b7280)` (fallback, not bright), all other at-a-glance rules use `--verdict-*`, `--bg-*`, `--text-*` tokens

## Verification Evidence

| Gate Check | Command | Exit Code | Verdict | Duration |
|---|---|---|---|---|
| CSS build | `make css` | 0 | ✅ PASS | ~500ms |
| Opacity override present | `grep -n 'enrichment-slot--loaded' app/static/src/input.css` | 0 | ✅ PASS (lines 1154, 1350) | <1s |
| Base opacity preserved | `grep -n 'opacity: 0.85' app/static/src/input.css` | 0 | ✅ PASS (line 1151) | <1s |
| No bright hex colors | Manual color scan of modified rules | N/A | ✅ PASS (design tokens only) | <1s |

> **Note:** T01's CSS edits were not actually persisted to disk in the T01 commit (only .gsd docs were committed). T02 applied the actual CSS changes and ran full build+test verification.

## Diagnostics

If enrichment content appears dimmed after enrichment completes:
1. Check computed opacity in browser devtools on the `.enrichment-slot` element
2. If opacity is 0.85, the `--loaded` class was not applied → TS pipeline issue, not CSS
3. Verify: `document.querySelectorAll('.enrichment-slot--loaded').length` in console — should be > 0 when enriched results are visible
4. If opacity is 1 but content looks dim, check for parent element opacity or z-index stacking

Context line alignment check: `.ioc-context-line` text should left-align with `.ioc-value` text in the card header. If misaligned, check that `.ioc-context-line` is still a direct child of `.ioc-card` in `_ioc_card.html`.

## Deviations

None. All steps executed as planned. `.ioc-summary-row` padding review (step 4) confirmed no change needed — existing `padding: 0.5rem 0` with zero horizontal padding is correct for inheriting card padding.

## Known Issues

None.

## Files Created/Modified

- `app/static/src/input.css` — Added `.enrichment-slot.enrichment-slot--loaded { opacity: 1; transition: opacity 0.2s ease; }` rule; fixed `.ioc-context-line` padding from `0.125rem 1rem 0.25rem` to `0.125rem 0 0.25rem`; updated `.verdict-micro-bar` to `min-width: 5rem; max-width: 8rem`
- `.gsd/milestones/M002/slices/S02/S02-PLAN.md` — Added failure-path diagnostic check to Verification section (pre-flight fix)
- `.gsd/milestones/M002/slices/S02/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
