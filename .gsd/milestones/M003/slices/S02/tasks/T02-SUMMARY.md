---
id: T02
parent: S02
milestone: M003
provides:
  - .ioc-type-badge--email selector in input.css (neutral muted styling, consistent with all other IOC types)
  - .filter-pill--email.filter-pill--active selector in input.css (neutral active state)
  - Rebuilt app/static/dist/style.css with both selectors present in minified output
  - 6 E2E tests for email IOC card rendering, filter pill existence, filtering behaviour, active state, reset, and badge CSS class
key_files:
  - app/static/src/input.css
  - app/static/dist/style.css
  - tests/e2e/test_results_page.py
key_decisions:
  - No new architectural decisions; CSS additions follow established neutral-selector pattern (all IOC type badges/pills share the same muted styling)
patterns_established:
  - Playwright to_have_class() with a plain string does exact class-list matching, not substring/regex matching; use a compound CSS selector (.pill--email.pill--active) instead of a regex string when asserting class combos
observability_surfaces:
  - E2E: python3 -m pytest tests/e2e/test_results_page.py -v -k email — 6 tests prove email cards render and filter pill works in a live browser
  - CSS source truth: grep 'email' app/static/src/input.css — both selectors visible at a glance
  - Built artifact: grep 'ioc-type-badge--email' app/static/dist/style.css — confirms selector survived minification
duration: ~15m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T02: Add email CSS selectors and verify end-to-end rendering

**Added `.ioc-type-badge--email` and `.filter-pill--email.filter-pill--active` selectors to input.css, rebuilt CSS, and added 6 passing E2E tests proving email IOC cards render and filter correctly.**

## What Happened

All four steps executed in order:

1. **CSS badge selector** — Added `.ioc-type-badge--email` to the neutral badge selector list at line ~1053 in `app/static/src/input.css`. The new selector joins `.ioc-type-badge--ipv4` through `--cve`, all sharing `color: var(--text-muted); border-color: var(--border-default)`.

2. **CSS active pill selector** — Added `.filter-pill--email.filter-pill--active` to the neutral active pill rule around line ~899 in `app/static/src/input.css`. Same treatment as all other IOC type pills: `border-color: var(--text-secondary); color: var(--text-primary); background-color: var(--bg-tertiary)`.

3. **CSS rebuild** — Ran `make css` (TailwindCSS CLI, 434ms). Output file `app/static/dist/style.css` updated (44 818 bytes). Both selectors confirmed present in the minified output via `grep`.

4. **E2E tests** — Added 6 test functions to `tests/e2e/test_results_page.py` under an "Email IOC rendering" section:
   - `test_email_ioc_card_renders` — at least 1 `.ioc-card[data-ioc-type="email"]` exists after submitting `EMAIL_IOC_TEXT`
   - `test_email_filter_pill_exists` — `.filter-pill--email` is visible in the filter bar
   - `test_email_filter_pill_shows_only_email_cards` — after clicking EMAIL pill, every visible card has `data-ioc-type="email"`
   - `test_email_filter_pill_active_state` — `.filter-pill--email.filter-pill--active` is visible when active
   - `test_all_types_pill_resets_after_email_filter` — "All Types" pill restores the full card count
   - `test_email_cards_have_neutral_type_badge` — `.ioc-type-badge--email` is visible inside email cards

One iteration was needed: the initial two assertions used `to_have_class(r".*regex.*")` strings, but Playwright's `to_have_class()` treats plain strings as exact class-list matches (not patterns). Fixed by switching both to compound CSS selector checks (`page.locator(".cls1.cls2")`).

## Verification

- `grep 'ioc-type-badge--email' app/static/src/input.css` → selector present
- `grep 'filter-pill--email' app/static/src/input.css` → selector present
- `make css` → exits 0, style.css updated
- `python3 -m pytest tests/e2e/test_results_page.py -v -k email` → 6/6 passed
- `python3 -m pytest tests/e2e/ -v` → 105/105 passed (zero regressions)
- `python3 -m pytest tests/test_classifier.py tests/test_extractor.py tests/test_pipeline.py -v` → 85/85 passed
- `make typecheck` → exits 0
- `python3 -c "from app.pipeline.extractor import run_pipeline; r=run_pipeline('user[@]evil[.]com'); assert any(i.value=='user@evil.com' for i in r), r"` → exits 0

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep 'ioc-type-badge--email' app/static/src/input.css` | 0 | ✅ pass | <1s |
| 2 | `grep 'filter-pill--email' app/static/src/input.css` | 0 | ✅ pass | <1s |
| 3 | `make css` | 0 | ✅ pass | 0.4s |
| 4 | `python3 -m pytest tests/e2e/test_results_page.py -v -k email` | 0 | ✅ pass | 2.5s (6 tests) |
| 5 | `python3 -m pytest tests/e2e/ -v` | 0 | ✅ pass | 33s (105 tests) |
| 6 | `python3 -m pytest tests/test_classifier.py tests/test_extractor.py tests/test_pipeline.py -v` | 0 | ✅ pass | 0.2s (85 tests) |
| 7 | `make typecheck` | 0 | ✅ pass | 23s |
| 8 | Pipeline smoke check (defanged email through run_pipeline) | 0 | ✅ pass | <1s |

## Diagnostics

- **Inspect CSS selectors in source:** `grep 'email' app/static/src/input.css` — both badge and pill selectors visible
- **Inspect minified output:** `grep -o 'ioc-type-badge--email[^}]*' app/static/dist/style.css` — selector is present in dist
- **Run email E2E only:** `python3 -m pytest tests/e2e/test_results_page.py -v -k email`
- **Full pipeline smoke:** `python3 -c "from app.pipeline.extractor import run_pipeline; print(run_pipeline('user[@]evil[.]com'))"`

## Deviations

- Two assertions initially used `to_have_class(r".*regex.*")` string patterns. Playwright treats plain string arguments to `to_have_class()` as exact class-list matchers, causing false failures even when the class was present. Fixed by switching to compound CSS selectors (`page.locator(".filter-pill--email.filter-pill--active")`). This is a test-authoring adjustment, not a deviation from what was built.

## Known Issues

None. All must-haves satisfied, all tests pass.

## Files Created/Modified

- `app/static/src/input.css` — added `.ioc-type-badge--email` to neutral badge selector list; added `.filter-pill--email.filter-pill--active` to neutral active pill selector list
- `app/static/dist/style.css` — rebuilt minified CSS including both new email selectors
- `tests/e2e/test_results_page.py` — added 6 email IOC rendering and filtering E2E tests
