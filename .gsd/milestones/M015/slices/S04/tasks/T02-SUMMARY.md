---
id: T02
parent: S04
milestone: M015
key_files:
  - tests/e2e/pages/index_page.py
  - tests/e2e/test_homepage.py
  - app/static/src/input.css
  - app/static/dist/style.css
  - app/static/dist/main.js
key_decisions:
  - Fixed responsive overflow by widening only the index page shell and constraining the decorative pseudo-element, not by clipping the interactive page shell.
duration: 
verification_result: passed
completed_at: 2026-04-26T11:15:30.984Z
blocker_discovered: false
---

# T02: Added final intake workbench browser assertions and fixed responsive overflow without breaking recent-history resume clicks.

**Added final intake workbench browser assertions and fixed responsive overflow without breaking recent-history resume clicks.**

## What Happened

Extended the index page object with reusable assertions for the assembled workbench, synchronized mode state, absent preview/results surfaces, recent resume hrefs, and full-document horizontal overflow. Strengthened homepage E2E coverage so seeded desktop and mobile recent-history rows prove the rail remains secondary, links to `/history/<id>`, stacks below the command card on mobile, and leaves the form usable when history is empty or unavailable. The new overflow assertion exposed an actual 390px mobile regression: the page rendered 401px wide. I first tried clipping `.page-index`, but focused browser verification showed that clipped the interactive recent-row area and caused Playwright click interception. I replaced that with a source-level layout fix: the index page now gets a wider `site-main` shell for the desktop workbench, and the decorative `.page-index::before` inset no longer extends horizontally outside the page. Rebuilt generated CSS/JS with `make build` and then verified the focused, fast, full E2E, and explicit route-contract lanes.

## Verification

Fresh verification passed after the final CSS and generated-asset rebuild. The focused homepage/UI/offline E2E lane passed 34 tests, `make verify-fast` passed 1026 non-E2E pytest tests plus 87 Vitest tests, TypeScript, and asset build, the full browser E2E suite passed 125 tests, and the explicitly named intake contract file passed 8 tests. The browser assertions now cover desktop command-card dominance, mobile stacking without horizontal overflow, no preview surfaces, stable `#mode-status`, seeded `.recent-analysis-row` hrefs and click navigation, empty/unavailable recent-history states, enabled Extract after IOC entry, and no offline enrichment polling.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -q tests/e2e/test_homepage.py tests/e2e/test_ui_controls.py tests/e2e/test_extraction.py::test_extract_mixed_iocs_offline` | 0 | ✅ pass | 5300ms |
| 2 | `make verify-fast` | 0 | ✅ pass | 11800ms |
| 3 | `python3 -m pytest -q tests/e2e` | 0 | ✅ pass | 42800ms |
| 4 | `python3 -m pytest -q tests/test_index_intake_contract.py` | 0 | ✅ pass | 6100ms |

## Deviations

None. The plan allowed CSS/generated-asset changes when browser assertions exposed responsive polish regressions; the new overflow assertion exposed and drove that fix.

## Known Issues

None.

## Files Created/Modified

- `tests/e2e/pages/index_page.py`
- `tests/e2e/test_homepage.py`
- `app/static/src/input.css`
- `app/static/dist/style.css`
- `app/static/dist/main.js`
