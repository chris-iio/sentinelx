# S02: At-a-glance enrichment surface

**Goal:** Online enrichment renders into the S01 single-column layout at full visual fidelity — each row shows verdict badge, real-world context (geo/ASN/DNS), key provider stat line, micro-bar, and staleness badge without any interaction.
**Demo:** After enrichment completes, every IOC row shows at-a-glance data at full opacity — no dimmed content, no layout jumps, no visual regressions from S01.

## Must-Haves

- `.enrichment-slot--loaded` overrides `opacity: 0.85` → `1` with smooth CSS transition
- Context line (`.ioc-context-line`) spacing aligns with verdict label and IOC value in full-width rows
- Summary row (`.ioc-summary-row`) readable at full width: verdict badge prominent but secondary to header `.verdict-label`, attribution text doesn't overflow, micro-bar compact
- Staleness badge visible and right-aligned in summary row
- No new loud colors introduced in enrichment surface (R003 compliance)
- All existing E2E tests pass (36 tests, same as S01 baseline)
- `make css`, `make typecheck`, `make js-dev` all exit 0

## Proof Level

- This slice proves: integration (CSS adaptation renders enrichment data correctly in new layout)
- Real runtime required: no (E2E tests exercise the rendering pipeline)
- Human/UAT required: yes (visual readability is the core design challenge — R002)

## Verification

- `make css` exits 0
- `make typecheck` exits 0
- `make js-dev` exits 0
- `pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q` → 36 passed
- `grep -n 'opacity: 0.85' app/static/src/input.css` — only in `.enrichment-slot` base rule (not in `--loaded` state)
- `.enrichment-slot.enrichment-slot--loaded` rule exists with `opacity: 1`
- No bright non-verdict colors introduced in enrichment surface CSS
- **Failure-path diagnostic:** If enrichment content appears dimmed after load, confirm `.enrichment-slot--loaded` class is present via `document.querySelectorAll('.enrichment-slot--loaded').length` in browser devtools — a count of 0 means enrichment.ts failed to add the class (TS pipeline issue), not a CSS issue

## Observability / Diagnostics

- Runtime signals: `.enrichment-slot--loaded` class presence on DOM element indicates enrichment data has arrived
- Inspection surfaces: Browser devtools computed styles on `.enrichment-slot.enrichment-slot--loaded` should show `opacity: 1`; `.ioc-context-line` should show visible content for IP/domain IOCs
- Failure visibility: dimmed enrichment content (opacity < 1) is the primary visual failure signal

## Integration Closure

- Upstream surfaces consumed: S01 layout (`.ioc-card` flex-column, single-column grid, design tokens), existing TS DOM builders (`row-factory.ts`, `enrichment.ts`)
- New wiring introduced in this slice: none (CSS refinement only — TS pipeline already wired)
- What remains before the milestone is truly usable end-to-end: S03 (inline expand), S04 (export/filter/polish integration), S05 (E2E update)

## Tasks

- [x] **T01: Fix enrichment slot opacity and refine at-a-glance CSS for full-width rows** `est:30m`
  - Why: The `.enrichment-slot` has `opacity: 0.85` that never resets when enrichment arrives — content renders dimmed. Additionally, the summary row, context line, and micro-bar CSS were authored for the old 2-column grid and need spacing/sizing tuning for full-width single-column rows.
  - Files: `app/static/src/input.css`
  - Do: (1) Add `.enrichment-slot.enrichment-slot--loaded { opacity: 1; transition: opacity 0.2s ease; }` rule. (2) Audit and adjust `.ioc-context-line` left padding to align with `.ioc-value` text above. (3) Tune `.ioc-summary-row` gap and `.verdict-badge` sizing to be prominent but secondary to header verdict label. (4) Adjust `.verdict-micro-bar` width constraints for full-width context. (5) Ensure `.staleness-badge` stays right-aligned via `margin-left: auto`. (6) Verify no bright non-verdict colors introduced.
  - Verify: `make css` exits 0, `grep 'enrichment-slot--loaded' app/static/src/input.css` shows opacity rule
  - Done when: `.enrichment-slot.enrichment-slot--loaded` has `opacity: 1` with transition; all at-a-glance component styles tuned for full-width layout; `make css` exits 0

- [ ] **T02: Build verification and integration test suite** `est:20m`
  - Why: Proves the CSS changes integrate correctly with the existing TS rendering pipeline and don't break any DOM contracts or E2E tests.
  - Files: `app/static/src/input.css` (read-only verification), `app/static/src/ts/modules/row-factory.ts` (read-only verification), `app/static/src/ts/modules/enrichment.ts` (read-only verification)
  - Do: (1) Run full build pipeline: `make css`, `make typecheck`, `make js-dev`. (2) Run E2E suite: `pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q`. (3) Verify opacity fix with grep. (4) Verify no bright colors in enrichment surface CSS. (5) If any test fails, diagnose and fix.
  - Verify: All three make targets exit 0; 36 E2E tests pass; opacity fix confirmed
  - Done when: `make css` + `make typecheck` + `make js-dev` all exit 0; `pytest` reports 36 passed; CSS grep confirms opacity override exists

## Files Likely Touched

- `app/static/src/input.css` — Opacity fix, spacing/sizing adjustments for at-a-glance components
