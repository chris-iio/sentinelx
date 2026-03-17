---
id: T01
parent: S03
milestone: M001
provides:
  - Enlarged verdict-label badge (VIS-01) for scan-target prominence
  - Verdict micro-bar replacing consensus badge text (VIS-02)
  - computeVerdictCounts() helper for verdict distribution
key_files:
  - app/static/src/input.css
  - app/static/src/ts/modules/row-factory.ts
  - app/static/src/ts/modules/verdict-compute.ts
key_decisions:
  - Kept .consensus-badge CSS as dead CSS for safe rollback; only removed DOM creation
  - Kept computeConsensus/consensusBadgeClass exports in verdict-compute.ts for API stability
patterns_established:
  - Micro-bar pattern: flex container with percentage-width segment divs, title attribute for accessibility
  - Visual hierarchy via font-size gap: summary badge 0.875rem vs provider badge 0.72rem
observability_surfaces:
  - document.querySelectorAll('.verdict-micro-bar') — verify micro-bars rendered
  - .verdict-micro-bar[title] attribute — exact verdict counts accessible on hover
  - NaN% widths in element inspector indicate division-by-zero bug (guarded)
duration: 15m
verification_result: passed
completed_at: 2026-03-17T18:10:00+09:00
blocker_discovered: false
---

# T01: Enlarge verdict badge and replace consensus badge with micro-bar

**Enlarged .verdict-label to 0.875rem/700/0.25rem-0.75rem padding and replaced consensus badge [n/m] text with proportional verdict micro-bar in summary rows**

## What Happened

Implemented VIS-01 and VIS-02 visual changes:

1. **VIS-01 (CSS-only):** Increased `.verdict-label` font-size from 0.7rem→0.875rem, weight 600→700, padding enlarged — makes the IOC card header verdict badge the dominant scan target. `.verdict-badge` on provider rows left at 0.72rem/600 to preserve hierarchy gap.

2. **VIS-02 (CSS + TypeScript):** Added `.verdict-micro-bar` and `.micro-bar-segment--{malicious,suspicious,clean,no_data}` CSS classes. Added `computeVerdictCounts()` private helper in row-factory.ts. Replaced the `consensusBadge` span creation in `updateSummaryRow()` with a flex micro-bar div containing percentage-width colored segments. Zero-count segments are skipped; `Math.max(1, total)` guards against NaN widths.

3. **Cleanup:** Removed `consensusBadgeClass` and `computeConsensus` imports from row-factory.ts (no longer consumed). Added API stability comment to verdict-compute.ts exports. Left `.consensus-badge` CSS in place as dead CSS for safe rollback.

## Verification

- `grep -r "consensus.badge\|consensus-badge" tests/e2e/` — zero results (safe to stop creating)
- `make typecheck` — zero TS errors ✅
- `make css` — Tailwind rebuild succeeds ✅
- `make js-dev` — esbuild bundles (178.2kb) ✅
- `pytest tests/ -m e2e --tb=short -q` — 89 passed, 2 failed (pre-existing title-case failures) ✅
- `grep -n "consensusBadge" row-factory.ts` — zero results ✅
- `.verdict-badge` CSS confirmed unchanged at 0.72rem / 2px 8px ✅

### Slice-level verification (partial — T01 of 4):
- [x] `make typecheck` — zero TS errors
- [x] `make js-dev` — esbuild bundle succeeds
- [x] `make css` — Tailwind rebuild succeeds
- [x] `pytest tests/ -m e2e` — 89/91 baseline maintained
- [x] `grep consensus-badge tests/e2e/` — zero results
- [ ] DOM structure verified: `.verdict-micro-bar` contains `.micro-bar-segment` children — not browser-tested (no running app in this context)
- [ ] `.provider-section-header` elements (T02)
- [ ] `.no-data-summary-row` elements (T04)

## Diagnostics

- Inspect micro-bars: `document.querySelectorAll('.verdict-micro-bar')` in browser DevTools
- Check counts: hover any micro-bar to see title tooltip with exact verdict distribution
- Verify hierarchy: compare computed font-size of `.verdict-label` (14px) vs `.verdict-badge` (11.52px)
- Dead CSS: `.consensus-badge` rules remain in input.css for rollback — can be removed in a future cleanup pass

## Deviations

- Fixed a stray duplicate line at the end of row-factory.ts (lines 405-406 had duplicate `result);` + `}`) that was likely from a prior interrupted edit session. Not a planned step but required for typecheck to pass.

## Known Issues

None.

## Files Created/Modified

- `app/static/src/input.css` — Enlarged `.verdict-label` (VIS-01); added `.verdict-micro-bar` and `.micro-bar-segment` classes (VIS-02)
- `app/static/src/ts/modules/row-factory.ts` — Added `computeVerdictCounts()` helper; replaced consensus badge creation with micro-bar in `updateSummaryRow()`; removed unused imports
- `app/static/src/ts/modules/verdict-compute.ts` — Added API stability comment to `consensusBadgeClass` export
