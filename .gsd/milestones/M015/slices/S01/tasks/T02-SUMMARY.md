---
id: T02
parent: S01
milestone: M015
key_files:
  - app/static/src/input.css
  - app/static/dist/style.css
  - app/static/dist/main.js
  - tests/e2e/pages/index_page.py
  - tests/e2e/test_homepage.py
key_decisions:
  - Preserved all stable form-control selectors and route behavior; limited the task to component CSS and test/POM coverage.
duration: 
verification_result: passed
completed_at: 2026-04-26T08:44:08.261Z
blocker_discovered: false
---

# T02: Styled the index command card and proved its responsive offline extraction fast path.

**Styled the index command card and proved its responsive offline extraction fast path.**

## What Happened

Updated `app/static/src/input.css` so the existing T01 command-card DOM now presents as a dominant analyst intake surface: centered workbench, elevated command card, stronger header hierarchy, larger textarea well, tactile buttons, and mobile stacking without changing the stable form-control IDs. Rebuilt generated assets through `make build`, which updated `app/static/dist/style.css` and `app/static/dist/main.js` via the normal Tailwind/esbuild pipeline. Updated `tests/e2e/pages/index_page.py` with `.page-index`, `.intake-workbench`, `.command-card`, command-card header/copy, and form-shell locators while preserving the downstream selectors for `#ioc-text`, `#submit-btn`, `#clear-btn`, `#mode-input`, `#mode-toggle-widget`, and `#mode-toggle-btn`. Extended `tests/e2e/test_homepage.py` with targeted Playwright assertions for command-card visibility, desktop/mobile hierarchy, initial disabled Extract state, Extract enabling after synthetic input, absence of S01 preview/recent rails, and a real offline submit that reaches results.

## Verification

Ran `make build` after CSS changes to regenerate assets rather than editing generated CSS manually. Ran `npx tsc --noEmit` after the final code changes. Ran the focused Playwright homepage and offline extraction proof (`python3 -m pytest -q tests/e2e/test_homepage.py tests/e2e/test_extraction.py::test_extract_mixed_iocs_offline`), which passed 18 tests and exercised the real browser flow. Also ran the Flask index DOM contract (`python3 -m pytest -q tests/test_index_intake_contract.py`), which passed 2 tests and confirmed the stable selector/form contract remains intact.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `make build` | 0 | ✅ pass | 2400ms |
| 2 | `npx tsc --noEmit` | 0 | ✅ pass | 3300ms |
| 3 | `python3 -m pytest -q tests/e2e/test_homepage.py tests/e2e/test_extraction.py::test_extract_mixed_iocs_offline` | 0 | ✅ pass | 3300ms |
| 4 | `python3 -m pytest -q tests/test_index_intake_contract.py` | 0 | ✅ pass | 2800ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `app/static/src/input.css`
- `app/static/dist/style.css`
- `app/static/dist/main.js`
- `tests/e2e/pages/index_page.py`
- `tests/e2e/test_homepage.py`
