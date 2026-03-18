---
id: T01
parent: S05
milestone: M002
provides:
  - ResultsPage page object with 18+ new locators and helpers for S01–S04 enrichment surface elements
key_files:
  - tests/e2e/pages/results_page.py
key_decisions:
  - Used regex class-match pattern (`r".*is-open.*"`) in expand_row/collapse_row assertions rather than exact-match, to be resilient to additional CSS classes co-existing on the element
patterns_established:
  - Card-scoped locator helpers use `data-ioc-value` attribute selector to target a specific card then chain a descendant selector — keeps selectors robust without requiring numeric indexing
observability_surfaces:
  - "`wc -l tests/e2e/pages/results_page.py` → ~266 lines (was 118) confirms expansion"
  - "`python3 -m pytest tests/e2e/ -q` → 91 passed confirms zero regression"
  - "`grep -c 'def \\|@property' tests/e2e/pages/results_page.py` → 70 confirms locator count"
duration: 3m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Add enrichment surface locators and helpers to ResultsPage page object

**Expanded `ResultsPage` from 118 to 266 lines with 18+ new locators and expand/collapse helpers for the S01–S04 enrichment surface.**

## What Happened

Read the existing `results_page.py` (118 lines) and the task plan's full locator inventory. Fixed the pre-flight observability gaps in both `S05-PLAN.md` (added `## Observability / Diagnostics` section) and `T01-PLAN.md` (added `## Observability Impact` section).

Then rewrote `results_page.py` keeping every existing locator and method unchanged and appending:
- Updated module docstring to reflect single-column layout with enrichment surface
- **Enrichment slots:** `enrichment_slots`, `loaded_enrichment_slots`, `enrichment_details`
- **Summary rows:** `summary_rows`, `expanded_summary_rows`
- **Enrichment elements:** `chevron_wrappers`, `micro_bars`, `staleness_badges`, `attribution_spans`, `detail_link_footers`, `detail_links`, `context_lines`
- **Section containers:** `enrichment_sections`, `section_context`, `section_reputation`, `section_no_data`
- **Card-scoped helpers:** `summary_row_for_card(ioc_value)`, `enrichment_details_for_card(ioc_value)`
- **Expand/collapse helpers:** `expand_row(ioc_value)`, `collapse_row(ioc_value)`, `is_row_expanded(ioc_value) -> bool`

## Verification

Ran `python3 -m pytest tests/e2e/ -q` — all 91 existing tests passed in 25.85s with zero failures. The new locators are purely additive; no existing selector or method was modified.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/e2e/ -q` | 0 | ✅ pass | 25.85s |
| 2 | `wc -l tests/e2e/pages/results_page.py` | 0 | ✅ 266 lines (was ~118) | <1s |
| 3 | `grep -c "def \|@property" tests/e2e/pages/results_page.py` | 0 | ✅ 70 definitions | <1s |

## Diagnostics

- `python3 -m pytest tests/e2e/ -q` — regression guard; 91 expected
- `wc -l tests/e2e/pages/results_page.py` — should be ~266
- `grep "def expand_row\|def collapse_row\|def is_row_expanded" tests/e2e/pages/results_page.py` — confirm all three helpers present
- New locators return `Locator` objects; call `.count()` in a REPL to verify DOM presence in a live browser session

## Deviations

The `expand_row` and `collapse_row` helpers use `to_have_class(r".*is-open.*")` (regex) instead of a simple `to_have_class("is-open")`. This is intentional — Playwright's `to_have_class` with a plain string checks for an exact full-class-list match on some versions; regex avoids fragility when other classes are present.

## Known Issues

None. The new locators will only be exercised (and any selector typos surface) in T02.

## Files Created/Modified

- `tests/e2e/pages/results_page.py` — expanded from 118 to 266 lines; module docstring updated; 18+ new properties and 5 new methods added; all existing code preserved intact
- `.gsd/milestones/M002/slices/S05/S05-PLAN.md` — added `## Observability / Diagnostics` section (pre-flight fix)
- `.gsd/milestones/M002/slices/S05/tasks/T01-PLAN.md` — added `## Observability Impact` section (pre-flight fix)
