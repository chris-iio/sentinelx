# S04: Functionality integration + polish

**Goal:** Export (JSON/CSV/clipboard), dashboard-click-to-filter, verdict sorting, progress bar, warning banners all work. Security contracts verified. Visual polish pass complete.
**Demo:** Full E2E suite passes (36/36), security audit produces clean evidence, production build ≤30KB, CSS polish applied.

## Must-Haves

- Export (JSON/CSV/clipboard) works end-to-end — `allResults[]` accumulation in enrichment.ts feeds export.ts correctly
- Dashboard-click-to-filter wired — `.verdict-kpi-card[data-verdict]` click triggers `applyFilter()`
- Verdict sorting works — `sortCardsBySeverity()` reads `data-verdict` from `.ioc-card` children of `#ioc-cards-grid`
- Progress bar renders — `#enrich-progress-fill` and `#enrich-progress-text` present in DOM
- Warning banner shows on error — `#enrich-warning` present in DOM
- Copy buttons work — `.copy-btn` with `data-value` present in `_ioc_card.html`
- Detail links fire — `injectDetailLink()` in `markEnrichmentComplete()` confirmed working
- CSP headers present in `app/__init__.py`
- CSRF protection active (`CSRFProtect`, `<meta name="csrf-token">`)
- No `innerHTML` in production TS code (SEC-08 compliance)
- No `document.write` or `eval()` in TS code
- All `.style.xxx` assignments are DOM property access, not style element injection
- `--bg-hover` design token is defined and wired
- Production build size ≤ 30KB minified JS
- TypeScript compiles with 0 errors
- Full E2E suite passes (36/36)

## Proof Level

- This slice proves: integration (full pipeline verification) + compliance (security contracts)
- Real runtime required: no (E2E tests exercise runtime paths)
- Human/UAT required: yes (S03-UAT.md visual items — deferred to human review, not blocking)

## Verification

- `make typecheck` — 0 errors
- `make css && make js-dev` — successful build
- `make js` — production build ≤ 30KB
- `pytest tests/e2e/ -q` — 36/36 pass
- Security audit evidence documented in T02 summary (grep results for innerHTML, CSP, CSRF, eval, document.write)
- `--bg-hover` token confirmed defined in `input.css`

## Integration Closure

- Upstream surfaces consumed: All S01–S03 DOM structure, data-* attributes, enrichment pipeline, expand/collapse wiring
- New wiring introduced in this slice: none (verification + CSS polish only)
- What remains before the milestone is truly usable end-to-end: S05 (E2E test suite update with new selectors)

## Tasks

- [ ] **T01: Verify integration pipeline — export, filter, sort, progress, warnings, copy, detail links** `est:30m`
  - Why: R008 requires all existing functionality works after the S01–S03 rework. This task produces evidence that the pipeline is intact, or surfaces specific breakages to fix.
  - Files: `app/static/src/ts/modules/export.ts`, `app/static/src/ts/modules/filter.ts`, `app/static/src/ts/modules/cards.ts`, `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/modules/clipboard.ts`, `app/templates/results.html`, `app/templates/partials/_verdict_dashboard.html`, `app/templates/partials/_filter_bar.html`, `app/templates/partials/_ioc_card.html`
  - Do: Run `make typecheck`, `make css`, `make js-dev`, and full E2E suite. Then code-review each wiring point: (1) export.ts reads `allResults[]` from enrichment.ts — verify accumulation path, (2) filter.ts binds `.verdict-kpi-card[data-verdict]` click and reads `data-verdict`/`data-ioc-type`/`data-ioc-value` from `.ioc-card` — verify selectors present in templates, (3) cards.ts `sortCardsBySeverity()` reads `data-verdict` from `.ioc-card` children of `#ioc-cards-grid` — verify selector chain, (4) `#enrich-progress-fill`/`#enrich-progress-text`/`#enrich-warning` present in results.html, (5) `.copy-btn` with `data-value` in `_ioc_card.html`, (6) `injectDetailLink()` called from `markEnrichmentComplete()`. Document each check result. If any wiring is broken, fix it.
  - Verify: `make typecheck` 0 errors, `make css && make js-dev` exit 0, `pytest tests/e2e/ -q` 36/36 pass, all wiring checks documented
  - Done when: Verification matrix documented with pass/fail for each R008 sub-feature, E2E 36/36, no regressions

- [ ] **T02: Audit security contracts — CSP, CSRF, SEC-08 textContent-only** `est:20m`
  - Why: R009 requires security posture doesn't regress during the UI redesign. This task produces grep-based evidence for compliance.
  - Files: `app/__init__.py`, `app/templates/base.html`, `app/static/src/ts/modules/*.ts`
  - Do: (1) `grep -c 'innerHTML' app/static/src/ts/modules/*.ts` — must be 0 in executable code (comments are OK, verify any non-zero count), (2) `grep -n 'Content-Security-Policy' app/__init__.py` — CSP header present, (3) `grep -n 'csrf' app/__init__.py app/templates/base.html` — CSRF protection active with CSRFProtect and meta tag, (4) `grep -rn 'document\.write\|eval(' app/static/src/ts/` — 0 matches, (5) review all `.style.xxx` assignments in enrichment.ts and filter.ts — confirm DOM property access not inline style element injection, (6) verify all DOM construction in row-factory.ts and enrichment.ts uses createElement+textContent+setAttribute pattern. Document each audit result.
  - Verify: All grep checks produce expected results, no innerHTML in executable code, no eval/document.write, all DOM construction SEC-08 compliant
  - Done when: Security audit evidence documented with pass/fail for each R009 sub-contract

- [ ] **T03: Visual polish pass, --bg-hover verification, production build gate** `est:30m`
  - Why: R010 requires performance doesn't regress and visual quality is production-grade. This task verifies the `--bg-hover` design token (flagged as fragile by S03), applies any CSS polish needed, and runs the final production build gate.
  - Files: `app/static/src/input.css`, `app/static/dist/style.css`, `app/static/dist/main.js`
  - Do: (1) Verify `--bg-hover` token is defined in `input.css` `:root` or `@theme` block — if undefined, add it with an appropriate muted value consistent with the quiet precision design system, (2) review S03 forward intelligence items: hover state visible on `.ioc-summary-row`, chevron rotation smooth in CSS, detail link present in dist CSS, (3) check spacing consistency — expanded panel padding, filter bar alignment, dashboard-to-results gap, (4) if any CSS adjustments needed, edit `input.css` only — no TS changes, (5) rebuild: `make css && make js-dev` then `make js` for production, (6) verify production build size: `wc -c app/static/dist/main.js` ≤ 30KB, (7) final E2E gate: `pytest tests/e2e/ -q` — 36/36 pass. Skill note: load the `lint` skill if any formatting issues arise.
  - Verify: `--bg-hover` token defined and compiled into dist CSS, `make js` production build ≤ 30KB, `pytest tests/e2e/ -q` 36/36 pass
  - Done when: `--bg-hover` confirmed or added, production build ≤ 30KB, final E2E 36/36, CSS polish applied if needed

## Files Likely Touched

- `app/static/src/ts/modules/export.ts` (read-only verification)
- `app/static/src/ts/modules/filter.ts` (read-only verification)
- `app/static/src/ts/modules/cards.ts` (read-only verification)
- `app/static/src/ts/modules/enrichment.ts` (read-only verification)
- `app/static/src/ts/modules/clipboard.ts` (read-only verification)
- `app/static/src/ts/modules/row-factory.ts` (read-only verification)
- `app/templates/results.html` (read-only verification)
- `app/templates/partials/_verdict_dashboard.html` (read-only verification)
- `app/templates/partials/_filter_bar.html` (read-only verification)
- `app/templates/partials/_ioc_card.html` (read-only verification)
- `app/__init__.py` (read-only security audit)
- `app/templates/base.html` (read-only security audit)
- `app/static/src/input.css` (may receive CSS polish edits)
- `app/static/dist/style.css` (rebuilt)
- `app/static/dist/main.js` (rebuilt)
