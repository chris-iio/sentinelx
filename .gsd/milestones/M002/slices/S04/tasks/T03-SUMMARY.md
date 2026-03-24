---
id: T03
parent: S04
milestone: M002
provides:
  - Visual polish verification — all S03 CSS artifacts confirmed in dist (--bg-hover, .ioc-summary-row:hover, chevron rotation, detail-link styles)
  - Production build gate passed — bundle 27,226 bytes (≤ 30KB)
  - Full E2E suite passing — 91/91 (all tests, not just R008 subset)
  - Title case alignment — tests updated to match intentional lowercase "sentinelx" brand
key_files:
  - app/static/src/input.css
  - app/static/dist/style.css
  - app/static/dist/main.js
  - app/templates/base.html
  - tests/e2e/test_homepage.py
  - tests/e2e/test_settings.py
key_decisions:
  - Brand name "sentinelx" stays all-lowercase in <title> — tests updated to match, not the template
  - No CSS polish changes required — all S03 CSS artifacts were already present and well-formed
patterns_established:
  - "Full E2E suite (91 tests) covers more ground than the R008 subset (36 tests) — run pytest tests/e2e/ -q for complete coverage"
  - "--bg-hover token lives in :root at input.css:53 as #3f3f46 (zinc-700) — consistent with btn-secondary-hover and export-dropdown-item:hover"
observability_surfaces:
  - "grep 'bg-hover' app/static/dist/style.css — confirms token compiled through on every CSS rebuild"
  - "wc -c app/static/dist/main.js — bundle size gate; value was 27226 bytes (baseline 26.6KB)"
  - "pytest tests/e2e/ -q — 91/91 is the full suite; the 36/36 in T01/T02 was a subset"
duration: 8m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T03: Visual polish pass, --bg-hover verification, production build gate

**Production build gate passed (27.2KB), all S03 CSS artifacts confirmed, two pre-existing title-case test failures fixed by aligning tests with the intentional lowercase "sentinelx" brand; full suite now 91/91.**

## What Happened

**Step 1 — `--bg-hover` token:**
Found at `input.css:53` — `--bg-hover: #3f3f46;` — defined in the `:root` block as a comment-annotated design token (`/* zinc-700 — hover state */`). Token confirmed present in compiled `dist/style.css` (appearing 7 times across shimmer, hover states, and button variants).

**Step 2 — S03 CSS artifact review:**
All three S03 artifacts confirmed in both source and dist:
- `.ioc-summary-row:hover { background-color: var(--bg-hover); border-radius: var(--radius-sm); }` ✅
- `.ioc-summary-row.is-open .chevron-icon { transform: rotate(90deg); }` ✅
- `.detail-link-footer` and `.detail-link` styles ✅

**Step 3 — Spacing consistency:**
- `.enrichment-details.is-open`: `padding-left: 0.5rem` — consistent with row padding
- `.filter-bar-wrapper`: `margin-bottom: 1rem`, `padding: 0.75rem 0` — consistent with dashboard/results spacing
- `.verdict-dashboard`: `margin-bottom: 0.75rem` — compact gap to filter bar; no excessive whitespace

No CSS changes required.

**Steps 4–5 — Build:**
- `make css` → exit 0 (483ms)
- `make js-dev` → exit 0 (10ms, 205.6KB with inline source map)
- `make js` → exit 0 (5ms, 26.6KB minified)
- `wc -c app/static/dist/main.js` → 27,226 bytes ✅ (≤ 30,000 gate)

**Step 6 — E2E gate:**
First run: 89/91 — two failures in `test_homepage.py::test_page_title` and `test_settings.py::test_settings_page_title_tag`. Both asserted `"SentinelX"` (title-case) but the template renders `"sentinelx"` (all-lowercase). This is an intentional brand choice confirmed by the user — tests were wrong, not the template.

Fix: updated both test assertions to `expect(page).to_have_title("sentinelx")`. Re-run: 91/91 ✅.

Note: the T01/T02 summary referenced "36/36" — that was a subset run of only `test_results_page.py` and `test_extraction.py`. The full suite is 91 tests.

## Verification

All must-haves met:
- `--bg-hover` defined in `input.css:53` and compiled into `dist/style.css`
- S03 CSS artifacts in dist: `.ioc-summary-row:hover`, `.ioc-summary-row.is-open .chevron-icon`, `.detail-link-footer`, `.detail-link`
- `make css && make js-dev` → exit 0
- `make js` → exit 0, 27,226 bytes ≤ 30,000
- `pytest tests/e2e/ -q` → 91/91 pass

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -n 'bg-hover' app/static/src/input.css` | 0 | ✅ pass | <1s |
| 2 | `grep 'bg-hover' app/static/dist/style.css` | 0 | ✅ pass | <1s |
| 3 | `grep 'ioc-summary-row:hover\|chevron-icon\|detail-link' app/static/dist/style.css` | 0 | ✅ pass | <1s |
| 4 | `make css` | 0 | ✅ pass | 1.6s |
| 5 | `make js-dev` | 0 | ✅ pass | 6.3s |
| 6 | `make js` | 0 | ✅ pass | 36.3s |
| 7 | `wc -c app/static/dist/main.js` → 27226 bytes | 0 | ✅ pass | <1s |
| 8 | `pytest tests/e2e/ -q` → 91/91 (after title-case fix) | 0 | ✅ pass | 24.5s |

## Diagnostics

- Token check: `grep 'bg-hover' app/static/src/input.css` → line 53 (source) + `grep 'bg-hover' app/static/dist/style.css` (compiled)
- Bundle size: `wc -c app/static/dist/main.js` — 27,226 bytes; gate is 30,000
- S03 CSS artifacts: `grep 'ioc-summary-row\|chevron-icon\|detail-link' app/static/dist/style.css`
- Full E2E: `python3 -m pytest tests/e2e/ -q` — 91 tests total (72 + 19 split across homepage/results/extraction/settings)

## Deviations

**Title-case test alignment:** Two tests in `test_homepage.py` and `test_settings.py` asserted `"SentinelX"` but the template uses `"sentinelx"`. User confirmed all-lowercase is intentional. Fixed tests to match template (not vice versa). This was not in the original T03 plan but was surfaced by running the full suite rather than the R008 subset.

## Known Issues

None.

## Files Created/Modified

- `app/templates/base.html` — no change (lowercase `sentinelx` is correct; reverted a mistaken capitalize attempt)
- `tests/e2e/test_homepage.py` — updated title assertion from `"SentinelX"` to `"sentinelx"`
- `tests/e2e/test_settings.py` — updated title assertion from `"SentinelX"` to `"sentinelx"`
- `app/static/dist/style.css` — rebuilt (no input.css changes; rebuild confirms clean compile)
- `app/static/dist/main.js` — rebuilt production bundle (27,226 bytes)
- `.gsd/milestones/M002/slices/S04/tasks/T03-PLAN.md` — added `## Observability Impact` section (pre-flight requirement)
