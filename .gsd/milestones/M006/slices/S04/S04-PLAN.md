# S04: Input Page Redesign

**Goal:** Home page matches results page design language — zinc tokens, Inter Variable typography, quiet precision aesthetic. Recent analyses list styled consistently. Layout handles both empty and populated history states cleanly.
**Demo:** Home page matches results page design language — zinc tokens, Inter Variable typography, quiet precision aesthetic. Recent analyses list styled consistently.

## Must-Haves

- `.page-index` layout stacks input card and recent analyses list vertically (not side-by-side)
- All index page CSS rules use design tokens from `:root` — no hardcoded colors, fonts, or radii
- Recent analyses list visually coheres with results page patterns (same border treatment, spacing rhythm, typography scale)
- `make css` builds without error and new/changed classes appear in `app/static/dist/style.css`
- All 11 E2E homepage tests pass
- All 13 history route tests pass
- Full test suite passes with zero regressions

## Proof Level

- This slice proves: Contract — CSS builds, all existing tests pass, visual consistency verified by grep-checking token usage.

## Integration Closure

Upstream: consumes recent analyses list HTML structure from S01 (index.html, input.css recent-analyses classes).
New wiring: none — CSS-only changes to existing elements.
Remaining: nothing — this is the final slice in M006.

## Verification

- None — CSS-only changes with no runtime behavior changes.

## Tasks

- [x] **T01: Audit and refine index page CSS for quiet precision consistency** `est:30m`
  Fix the `.page-index` flex layout bug (row→column for proper stacking of input card + recent analyses), audit all index page CSS rules against results page conventions, refine any inconsistencies, rebuild CSS, and verify full test suite passes.

**Context:** The index page (`index.html`) already uses design tokens (zinc surfaces, Inter Variable font, sky-blue accents) established in M002. S01 added a recent analyses list below the input form with proper tokens. However, `.page-index` uses `display: flex` without `flex-direction: column`, causing the input card and recent analyses list to sit side-by-side instead of stacking vertically. This task fixes that layout bug and performs a final consistency audit.

**Key constraint:** All CSS changes must stay inside `@layer components`. No Tailwind utility classes on elements with component class styles. All existing CSS class names must be preserved (E2E tests assert on them). Template changes, if any, must preserve all class names and structural elements that tests depend on (`.index-hero-brand`, `.ioc-textarea`, `#submit-btn`, `#clear-btn`, `#mode-toggle-widget`, etc.).

**CRITICAL:** The `tools/tailwindcss` binary may be missing in the worktree. Run `ls tools/tailwindcss` first. If missing: `cp /home/chris/projects/sentinelx/tools/tailwindcss ./tools/tailwindcss && chmod +x ./tools/tailwindcss`.
  - Files: `app/static/src/input.css`, `app/templates/index.html`, `app/static/dist/style.css`
  - Verify: ls tools/tailwindcss && make css && make js && python3 -m pytest tests/e2e/test_homepage.py -v && python3 -m pytest tests/test_history_routes.py -v && python3 -m pytest --tb=short -q

## Files Likely Touched

- app/static/src/input.css
- app/templates/index.html
- app/static/dist/style.css
