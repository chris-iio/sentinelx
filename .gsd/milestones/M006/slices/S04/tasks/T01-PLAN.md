---
estimated_steps: 5
estimated_files: 3
skills_used:
  - frontend-design
  - make-interfaces-feel-better
---

# T01: Audit and refine index page CSS for quiet precision consistency

**Slice:** S04 — Input Page Redesign
**Milestone:** M006

## Description

Fix the `.page-index` flex layout bug and audit all index page CSS rules against the results page design conventions. The index page already uses the correct design tokens but has a layout issue introduced when S01 added the recent analyses list as a second child of `.page-index`. Refine any small inconsistencies, rebuild CSS, and verify the full test suite passes.

**Why this task exists:** R013 requires the input/home page to match the quiet precision design language. The page is 95% there — this task closes the remaining gap with a layout fix and consistency pass.

## Steps

1. **Verify toolchain.** Run `ls tools/tailwindcss` to confirm the CSS build binary is present. If missing, copy it: `cp /home/chris/projects/sentinelx/tools/tailwindcss ./tools/tailwindcss && chmod +x ./tools/tailwindcss`.

2. **Fix `.page-index` layout.** In `app/static/src/input.css`, find the `.page-index` rule (around line 276) and add `flex-direction: column; align-items: center;`. This changes the flex container from row (default) to column so the `.input-card` and `.recent-analyses` stack vertically instead of sitting side-by-side. Keep the existing `justify-content: center` (which now applies to vertical centering — but since `min-height: calc(100vh - 5rem)` and `padding-top: 20vh` are set, the content is pushed down by padding, not centered). Actually, change `justify-content: center` to `justify-content: flex-start` since vertical centering doesn't make sense in a column layout with `padding-top: 20vh` — the padding already positions content.

   Current `.page-index`:
   ```css
   .page-index {
       display: flex;
       justify-content: center;
       align-items: flex-start;
       padding-top: 20vh;
       min-height: calc(100vh - 5rem);
   }
   ```

   Should become:
   ```css
   .page-index {
       display: flex;
       flex-direction: column;
       align-items: center;
       padding-top: 20vh;
       min-height: calc(100vh - 5rem);
   }
   ```

3. **Audit and refine CSS consistency.** Read all index page CSS rules (`.page-index` through `.paste-feedback`, roughly lines 276-490) and all recent analyses rules (`.recent-analyses` through `.recent-analysis-time`, roughly lines 1977-2055). Check each rule against these patterns from the results page:
   - Typography: `font-family` should use `var(--font-ui)` or `var(--font-mono)`, `font-weight` should use `var(--weight-heading)` or `var(--weight-body)` where appropriate, `letter-spacing` should use `var(--tracking-heading)` for headings
   - Colors: all color values should reference CSS custom properties — no hex values outside `:root`
   - Spacing: border-radius should use `var(--radius)` or `var(--radius-sm)`, box-shadows should use `var(--shadow-*)` tokens
   - Transitions: should use `var(--duration-*)` and `var(--ease-out-*)` tokens
   - Font sizes: verify they're appropriate for their role (labels 0.75-0.85rem, body 0.875rem, headings 1rem+)

   Apply any refinements found. Common patterns on the results page:
   - `.recent-analyses-title` should match the `.form-label` pattern: `font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em` — it already does this, verify it's consistent
   - `.recent-analysis-row` hover transition should use design tokens — verify `var(--duration-fast)` and `var(--ease-out-quart)` are used

4. **Review template for structural consistency.** Read `app/templates/index.html` and confirm all class names and IDs that E2E tests assert on are preserved: `.index-hero-brand`, `.ioc-textarea`, `#submit-btn`, `#clear-btn`, `#mode-toggle-widget`, `#ioc-text`, `#analyze-form`, `.brand-accent`, `.page-index`, `.input-card`. Make minor template adjustments only if needed (unlikely — template structure is already correct).

5. **Rebuild and verify.** Run `make css` to rebuild the CSS bundle. Run `make js` to verify no TS regressions. Then run the full test verification chain:
   - `python3 -m pytest tests/e2e/test_homepage.py -v` — all 11 E2E homepage tests pass
   - `python3 -m pytest tests/test_history_routes.py -v` — all 13 history route tests pass
   - `python3 -m pytest --tb=short -q` — full suite passes, zero regressions
   - `grep -c 'page-index\|recent-analyses' app/static/dist/style.css` — confirm classes present in built CSS

## Must-Haves

- [ ] `.page-index` uses `flex-direction: column; align-items: center` so input card and recent analyses stack vertically
- [ ] All index page CSS rules use design token custom properties — no hardcoded colors, font stacks, or radii
- [ ] `make css` builds without error
- [ ] All 11 E2E homepage tests pass
- [ ] All 13 history route tests pass
- [ ] Full test suite passes with zero regressions

## Verification

- `ls tools/tailwindcss` — binary present (exit 0)
- `make css` — CSS builds without error
- `make js` — JS builds without error
- `python3 -m pytest tests/e2e/test_homepage.py -v` — 11/11 pass
- `python3 -m pytest tests/test_history_routes.py -v` — 13/13 pass
- `python3 -m pytest --tb=short -q` — full suite passes, zero regressions
- `grep -c 'page-index' app/static/dist/style.css` — returns ≥1 (class in built output)

## Inputs

- `app/static/src/input.css` — current CSS source with design tokens and index page component rules (lines 276-500 for input page, lines 1977-2065 for recent analyses)
- `app/templates/index.html` — Jinja2 template with `.page-index` > `.input-card` + `.recent-analyses` structure
- `app/templates/base.html` — shared layout (font preloads, `.site-main` wrapper, floating settings nav)

## Expected Output

- `app/static/src/input.css` — refined CSS with layout fix and consistency improvements
- `app/static/dist/style.css` — rebuilt CSS bundle containing all changes
- `app/templates/index.html` — template with any minor structural refinements (all class names preserved)
