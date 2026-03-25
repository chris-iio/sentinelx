---
id: T01
parent: S04
milestone: M006
key_files:
  - app/static/src/input.css
  - app/static/dist/style.css
key_decisions:
  - Replace transition: all with explicit property list on .btn to follow 'never use transition: all' principle from design skill
  - Map .alert-error hardcoded #ff6b6b to var(--verdict-malicious-text) design token for consistency
duration: ""
verification_result: passed
completed_at: 2026-03-25T12:16:12.138Z
blocker_discovered: false
---

# T01: Fix .page-index flex layout to column and align all index page CSS transitions/colors with design token system

**Fix .page-index flex layout to column and align all index page CSS transitions/colors with design token system**

## What Happened

The `.page-index` container was using the default `flex-direction: row`, causing the `.input-card` and `.recent-analyses` sections to sit side-by-side instead of stacking vertically. This was introduced when S01 added the recent analyses list as a second child of `.page-index`.

Fixed the layout by changing `.page-index` to `flex-direction: column; align-items: center` and removing the now-unnecessary `justify-content: center` (vertical centering makes no sense with `padding-top: 20vh`).

Audited all index page CSS rules (lines 276–500) and recent analyses rules (lines 1977–2055) against the results page design conventions. Found and fixed several token consistency issues:

1. **Mode toggle track transition**: Hardcoded `0.2s ease` → `var(--duration-fast) var(--ease-out-quart)`
2. **Mode toggle thumb transition**: Hardcoded `0.2s ease` → `var(--duration-fast) var(--ease-out-quart)`
3. **Mode toggle label transition**: Hardcoded `0.15s ease` → `var(--duration-fast) var(--ease-out-quart)`
4. **`.btn` base rule**: `transition: all` → explicit property list (background-color, border-color, color, opacity, transform) per the "never use transition: all" principle
5. **`.alert-error` color**: Hardcoded `#ff6b6b` → `var(--verdict-malicious-text)` to use the design token

Confirmed the recent analyses section was already fully tokenized — `.recent-analyses-title` matches the `.form-label` pattern, `.recent-analysis-row` uses `var(--duration-fast) var(--ease-out-quart)` for hover transitions.

Template verified: all 10 class names and IDs that E2E tests assert on are present and unchanged.

## Verification

All verification checks pass:
- `ls tools/tailwindcss` — binary present (exit 0)
- `make css` — CSS builds without error
- `make js` — JS builds without error (30.2kb bundle)
- `python3 -m pytest tests/e2e/test_homepage.py -v` — 11/11 pass
- `python3 -m pytest tests/test_history_routes.py -v` — 13/13 pass
- `python3 -m pytest --tb=short -q` — 1043 passed, zero regressions
- `grep -c 'page-index\|recent-analyses' app/static/dist/style.css` — returns 1 (classes in built output)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `ls tools/tailwindcss` | 0 | ✅ pass | 50ms |
| 2 | `make css` | 0 | ✅ pass | 500ms |
| 3 | `make js` | 0 | ✅ pass | 100ms |
| 4 | `python3 -m pytest tests/e2e/test_homepage.py -v` | 0 | ✅ pass | 7000ms |
| 5 | `python3 -m pytest tests/test_history_routes.py -v` | 0 | ✅ pass | 3400ms |
| 6 | `python3 -m pytest --tb=short -q` | 0 | ✅ pass | 67000ms |
| 7 | `grep -c 'page-index|recent-analyses' app/static/dist/style.css` | 0 | ✅ pass | 50ms |


## Deviations

None. All changes align with the task plan. The plan suggested removing `justify-content: center` and the implementation did exactly that.

## Known Issues

None.

## Files Created/Modified

- `app/static/src/input.css`
- `app/static/dist/style.css`
