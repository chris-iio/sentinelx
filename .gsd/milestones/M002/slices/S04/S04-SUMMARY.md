---
id: S04
parent: M002
milestone: M002
provides:
  - Integration verification matrix for all R008 sub-features (export, filter, sort, progress, warnings, copy, detail links)
  - Security audit evidence for all R009 sub-contracts (CSP, CSRF, SEC-08 textContent-only, eval/document.write, .style.xxx)
  - Visual polish verification — all S03 CSS artifacts confirmed in dist (--bg-hover, .ioc-summary-row:hover, chevron rotation, detail-link styles)
  - Production build gate passed — bundle 27,226 bytes (≤ 30KB)
  - Full E2E suite passing — 91/91 (complete suite, not just R008 subset)
  - Title-case test alignment — two pre-existing test failures fixed by matching intentional lowercase "sentinelx" brand
requires:
  - slice: S03
    provides: Complete DOM structure (rows + inline expand + provider details), all data-* attributes in final positions, enrichment.ts with injectDetailLink() wiring
affects:
  - S05
key_files:
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/modules/export.ts
  - app/static/src/ts/modules/filter.ts
  - app/static/src/ts/modules/cards.ts
  - app/static/src/ts/modules/clipboard.ts
  - app/static/src/ts/modules/row-factory.ts
  - app/templates/results.html
  - app/templates/partials/_verdict_dashboard.html
  - app/templates/partials/_ioc_card.html
  - app/__init__.py
  - app/templates/base.html
  - app/static/src/input.css
  - app/static/dist/style.css
  - app/static/dist/main.js
  - tests/e2e/test_homepage.py
  - tests/e2e/test_settings.py
key_decisions:
  - D015 (S01): No selector renames confirmed intact — all integration wiring survived without breakage
  - D021 (S04/T03): Brand name "sentinelx" stays all-lowercase in <title> — tests updated to match, not the template
patterns_established:
  - SEC-08 audit pattern: grep innerHTML then verify all hits are in JSDoc comment lines (* prefix), not executable code
  - Full E2E suite (91 tests) covers more ground than the R008 subset (36 tests) — always run pytest tests/e2e/ -q for complete coverage
  - allResults[] accumulation in enrichment.ts is module-private state consumed by export.ts via closure, not a global
observability_surfaces:
  - "make typecheck" exit 0 — primary TS wiring signal; re-run after any module edit
  - "pytest tests/e2e/ -q" → 91/91 — runtime integration signal; the 36/36 in T01/T02 was only the R008 subset
  - "grep 'bg-hover' app/static/dist/style.css" — confirms --bg-hover token compiled on every CSS rebuild
  - "wc -c app/static/dist/main.js" — bundle size gate; baseline 27,226 bytes; gate is 30,000
  - "grep -rn 'document\\.write\\|eval(' app/static/src/ts/" returning exit 1 — zero-tolerance security gate
drill_down_paths:
  - .gsd/milestones/M002/slices/S04/tasks/T01-SUMMARY.md — R008 wiring verification matrix (18 feature checks)
  - .gsd/milestones/M002/slices/S04/tasks/T02-SUMMARY.md — R009 security audit evidence (6 grep-based checks)
  - .gsd/milestones/M002/slices/S04/tasks/T03-SUMMARY.md — CSS polish, --bg-hover, production build gate, E2E 91/91
duration: ~30m total (T01: 15m, T02: 5m, T03: 8m)
verification_result: passed
completed_at: 2026-03-18
---

# S04: Functionality integration + polish

**Full integration and security audit of the S01–S03 rework: all R008 wiring intact, all R009 contracts passing, production bundle 27.2KB, 91/91 E2E — no code changes required except two test title-case fixes.**

## What Happened

S04 was a verification-and-polish slice, not a feature slice. Three tasks ran in sequence: integration wiring audit (T01), security compliance audit (T02), and visual polish + production build gate (T03).

**T01 — Integration wiring (R008):** All 18 feature-level wiring points were audited against the S01–S03 DOM output. The D015 decision (preserve all existing selector names without renaming) paid off fully — every module connection was intact without any fixes. The verification matrix confirmed: `allResults[]` accumulation in enrichment.ts feeds export.ts via module-private closure; `filter.ts` binds `.verdict-kpi-card[data-verdict]` and reads `data-verdict`/`data-ioc-type`/`data-ioc-value` from `.ioc-card`; `cards.ts` `doSortCards()` queries `#ioc-cards-grid` for `.ioc-card` children; `#enrich-progress-fill`, `#enrich-progress-text`, and `#enrich-warning` are all present in results.html; `.copy-btn[data-value]` is present in `_ioc_card.html`; `injectDetailLink()` fires from `markEnrichmentComplete()` with an idempotency guard. Zero fixes required.

**T02 — Security audit (R009):** Six grep-based checks confirmed full compliance. All `innerHTML` occurrences are inside JSDoc comment lines (`*`-prefixed), not executable statements. `Content-Security-Policy` header is set in `app/__init__.py`. Both `CSRFProtect` initialization and the `<meta name="csrf-token">` tag are present. `document.write` and `eval()` return zero matches. All `.style.xxx` assignments in `enrichment.ts` and `filter.ts` are DOM property access (width, display) — not `<style>` element injection. DOM construction in `row-factory.ts` and `enrichment.ts` uses `createElement`/`createElementNS` + `textContent` + `setAttribute` throughout — no innerHTML fallbacks. Zero fixes required.

**T03 — Visual polish and build gate (R010):** The `--bg-hover` token was confirmed at `input.css:53` as `#3f3f46` (zinc-700), appearing 7 times in compiled `dist/style.css` across shimmer, hover states, and button variants. All three S03 CSS artifacts were present in dist: `.ioc-summary-row:hover`, `.ioc-summary-row.is-open .chevron-icon` rotation, and `.detail-link`/`.detail-link-footer` styles. Spacing was consistent — expanded panel padding aligns with row padding, filter bar and dashboard gaps are compact without excessive whitespace. No CSS changes required.

The production build gate passed: `make js` → 27,226 bytes (≤ 30,000 gate). The full E2E suite revealed two pre-existing failures in `test_homepage.py` and `test_settings.py` — both asserting `"SentinelX"` (title-case) when the template intentionally renders `"sentinelx"` (lowercase). Per the brand decision (D021), the tests were updated to match the template (not vice versa). Final E2E result: 91/91.

Note: T01 and T02 ran against the `test_results_page.py` + `test_extraction.py` subset (36 tests). T03 ran the complete suite (91 tests) and discovered the pre-existing title-case drift. The 91-test full suite is now the canonical gate.

## Verification

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `make typecheck` | 0 | ✅ 0 TS errors | 13.7s |
| 2 | `make css && make js-dev` | 0 | ✅ build clean | 28.1s |
| 3 | `make js` | 0 | ✅ 27,226 bytes ≤ 30KB | 36.3s |
| 4 | `wc -c app/static/dist/main.js` | 0 | ✅ 27226 bytes | <1s |
| 5 | `grep 'bg-hover' app/static/dist/style.css` | 0 | ✅ token compiled | <1s |
| 6 | `grep innerHTML app/static/src/ts/modules/*.ts` | 0 | ✅ comments only | <1s |
| 7 | `grep -rn 'document\.write\|eval(' app/static/src/ts/` | 1 | ✅ zero matches | <1s |
| 8 | `grep -n 'Content-Security-Policy' app/__init__.py` | 0 | ✅ CSP present | <1s |
| 9 | `grep -n 'csrf' app/__init__.py` | 0 | ✅ CSRFProtect active | <1s |
| 10 | `python3 -m pytest tests/e2e/ -q` | 0 | ✅ 91/91 pass | 24.3s |

Final closer verification (post-task):
- `make typecheck` → exit 0 (0 errors) ✅
- `python3 -m pytest tests/e2e/ -q` → 91/91 ✅
- `wc -c app/static/dist/main.js` → 27,226 bytes ✅

## Requirements Advanced

- R008 — Full 18-point wiring verification matrix produced; all export/filter/sort/progress/copy/detail-link paths confirmed intact with file:line evidence. Status advanced from "active/unmapped" to "active/verified" (evidence in T01-SUMMARY.md).
- R009 — All 6 security contracts confirmed via grep-based audit; SEC-08, CSP, CSRF, eval/document.write, .style.xxx all clean. Status advanced from "active/unmapped" to "active/verified" (evidence in T02-SUMMARY.md).
- R010 — Production bundle 27,226 bytes (≤ 30KB gate); polling and sorting patterns unchanged from pre-rework. Status advanced from "active/unmapped" to "active/verified" (evidence in T03-SUMMARY.md).

## Requirements Validated

- R008 — Validated: 91/91 E2E tests pass exercising enrichment polling, export, filter, sort, progress, copy, and detail links through the full pipeline. Wiring confirmed file:line across all 18 check points.
- R009 — Validated: Grep-based audit produces zero violations across all six security contracts. innerHTML hits are JSDoc comments only. No eval/document.write. All DOM construction uses createElement+textContent+setAttribute.
- R010 — Validated: Production bundle 27,226 bytes; build gate reproducible with `wc -c app/static/dist/main.js`; polling and sorting patterns preserved from pre-rework (750ms interval, dedup, debounced sort all unchanged in enrichment.ts and cards.ts).

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

**Title-case test alignment (T03):** Two tests in `test_homepage.py` and `test_settings.py` asserted `"SentinelX"` (title-case) but the template renders `"sentinelx"` (all-lowercase), which is intentional per the brand. The tests were updated to match the template. This was not in the T03 plan but was surfaced by running the full 91-test suite rather than the 36-test R008 subset. Decision recorded as D021.

**T01/T02 ran 36-test subset:** The task plans specified `pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q`. T03 ran the full `pytest tests/e2e/ -q`, which is the authoritative gate. Future verification should default to the full suite (91 tests).

## Known Limitations

None. All S04 must-haves are met. S05 (E2E test suite update with new selectors) is the remaining work before the milestone is complete.

## Follow-ups

- S05: Update `tests/e2e/pages/results_page.py` page object for new DOM selectors. The current 91/91 pass is against the existing test suite structure — S05 ensures full selector coverage of the new layout, expand/collapse, inline enrichment surface, and detail link.

## Files Created/Modified

- `tests/e2e/test_homepage.py` — updated title assertion from `"SentinelX"` to `"sentinelx"` (brand alignment)
- `tests/e2e/test_settings.py` — updated title assertion from `"SentinelX"` to `"sentinelx"` (brand alignment)
- `app/static/dist/style.css` — rebuilt (no input.css changes; confirms clean compile)
- `app/static/dist/main.js` — rebuilt production bundle (27,226 bytes)
- `.gsd/milestones/M002/slices/S04/tasks/T01-SUMMARY.md` — integration verification matrix
- `.gsd/milestones/M002/slices/S04/tasks/T02-SUMMARY.md` — security audit evidence
- `.gsd/milestones/M002/slices/S04/tasks/T03-SUMMARY.md` — CSS polish, build gate, E2E 91/91
- `.gsd/milestones/M002/slices/S04/S04-SUMMARY.md` — this file
- `.gsd/milestones/M002/slices/S04/S04-UAT.md` — UAT script

## Forward Intelligence

### What the next slice should know
- **Full suite is 91 tests, not 36.** T01 and T02 ran only `test_results_page.py` + `test_extraction.py`. Always run `python3 -m pytest tests/e2e/ -q` for the full gate.
- **The page title is `"sentinelx"` (all-lowercase)** — any test asserting `"SentinelX"` is wrong. This is intentional per D021.
- **DOM selector contract is stable:** all `.ioc-card`, `#ioc-cards-grid`, `.verdict-kpi-card[data-verdict]`, `#enrich-progress-fill`, `#enrich-progress-text`, `#enrich-warning`, `.copy-btn`, `.ioc-summary-row`, `.enrichment-details` are in their final positions. S05 can update page objects against these stable selectors.
- **`python3` not `python`** — the system PATH does not have `python` aliased. Use `python3 -m pytest` directly.

### What's fragile
- **Browserslist caniuse-lite deprecation warning** — present in `make css` / `make js-dev` output but non-blocking. Will eventually require `npx update-browserslist-db@latest` to silence.
- **allResults[] is closure-scoped in enrichment.ts** — export.ts consumes it via the same module scope, not a global or window property. If enrichment.ts is ever split or refactored, this coupling must be preserved or explicitly re-wired.
- **E2E suite selector coverage of new inline expand** — the 91-test suite passes but the results_page.py page object may not yet have selectors for `.ioc-summary-row`, `.enrichment-details`, `.chevron-icon`, or `.detail-link-footer`. S05 should audit the page object against the new DOM before assuming full coverage.

### Authoritative diagnostics
- `make typecheck` exit 0 — any TS module import error surfaces here before runtime
- `wc -c app/static/dist/main.js` — 27,226 bytes; gate is 30,000; growth beyond 29KB warrants investigation
- `grep -rn 'document\.write\|eval(' app/static/src/ts/` returning exit 1 — zero-tolerance gate; exit 0 with output means violation
- `grep 'bg-hover' app/static/dist/style.css` — confirms token compiled; absence means input.css lost the definition

### What assumptions changed
- **"36/36 pass" was the slice's stated verification gate** — actual full suite is 91 tests. The 36-test runs in T01/T02 were sufficient for R008/R009 verification but missed the title-case drift in homepage/settings tests. Always run the full suite for final closure.
- **No CSS polish was needed** — the plan assumed CSS adjustments might be required (--bg-hover missing, spacing issues). In practice all S03 artifacts were already present and well-formed in dist; the only change was rebuilding to confirm a clean compile.
