# S04 Research: Input Page Redesign

**Depth:** Light — CSS/template polish applying the existing quiet precision design language already established across results, detail, and settings pages.

**Target Requirement:** R013 (active) — Update the input/home page to match the quiet precision design language established in M002 — zinc tokens, Inter Variable typography, consistent spacing and color approach.

---

## Summary

The input page (`index.html`) and its CSS already use the correct design tokens (zinc surfaces, Inter Variable, sky-blue accents). The "redesign" is mostly about **visual polish and consistency refinement** — the heavy design system lift was done in M002. S01 added the recent analyses list with correct tokens. The remaining work is CSS-only and template-minor: tightening spacing, ensuring the recent analyses list visually matches results page patterns, and verifying the build pipeline produces correct output.

**This is straightforward work with low risk.** The design system exists, the tokens exist, the patterns exist. The task is to audit the current input page against results page conventions and make targeted CSS/template adjustments.

---

## Recommendation

Single task. Audit index.html + input page CSS rules against the results/settings page patterns, apply any refinements needed for visual consistency, rebuild CSS with `make css`, and verify with existing E2E tests plus a visual check.

---

## Implementation Landscape

### What exists today

1. **`app/templates/index.html`** — Jinja2 template extending `base.html`. Contains:
   - `.page-index` wrapper (flex, centered, `padding-top: 20vh`)
   - `.input-card` (transparent bg, no border, 720px max-width) — already matches the "no card chrome" quiet precision pattern
   - `.index-hero` with `.index-hero-brand` (Inter Variable, 1.5rem, weight 600)
   - Form with `.ioc-textarea`, mode toggle, Clear/Extract buttons
   - Recent analyses list (`.recent-analyses`) added by S01 — already uses zinc tokens, verdict badges, mono font

2. **`app/static/src/input.css`** — All CSS in `@layer components`. Key input-page rules:
   - `.page-index` — flex center, `padding-top: 20vh`
   - `.input-card` — transparent bg, no border, no shadow, `fadeSlideUp` animation
   - `.index-hero-brand` — Inter Variable, 1.5rem/600
   - `.ioc-textarea` — `--bg-secondary`, `--border`, `--font-mono`, focus glow
   - `.form-options`, `.mode-toggle-*`, `.paste-feedback` — all use design tokens
   - `.recent-analyses*` — added by S01, already uses `--bg-secondary`, `--border`, `--font-mono`, verdict badges
   - Responsive breakpoint at 640px for `.input-card`, `.form-options`

3. **`app/templates/base.html`** — Shared layout with Inter Variable + JetBrains Mono Variable font preloads, floating settings nav, `<main class="site-main">` wrapper.

4. **Design tokens** — All defined in `:root` in `input.css`: zinc surface hierarchy (`--bg-primary` through `--bg-hover`), opacity-based borders, zinc text scale, sky-blue accent, verdict color triples, typography vars (`--font-ui`, `--font-mono`, `--weight-heading`, etc.), shape vars (`--radius`, `--radius-sm`), motion vars.

### What the results page does that the index page should match

Both pages already share:
- Same `base.html` layout (fonts, settings nav, site-main wrapper)
- Same design tokens (zinc surfaces, borders, text colors)
- Same button styles (`.btn`, `.btn-primary`, `.btn-secondary`)

The index page is already well-aligned. Areas to audit for consistency:
- **Recent analyses list styling** — does it feel like a natural sibling of the filter bar / IOC cards? The S01 implementation used `--bg-secondary` background and `--border` which matches. Verdict badges reuse the same classes as results page.
- **Typography consistency** — hero brand uses `1.5rem/600`, results header uses `1rem/600` for `.ioc-count`. Both appropriate for their context.
- **Spacing** — `padding-top: 20vh` pushes content down on the index page, which is intentional for a focused input experience. Results page uses `2rem 1.5rem` padding. No conflict.

### Files that will be touched

- `app/static/src/input.css` — CSS adjustments (if any needed after audit)
- `app/templates/index.html` — Template adjustments (if any needed after audit)
- No JS changes expected — `form.ts` handles all input page interactions correctly

### Build pipeline

- `make css` — runs `./tools/tailwindcss` standalone CLI
- **CRITICAL**: `tools/tailwindcss` binary may be missing in worktree (see KNOWLEDGE.md). Must verify presence before building: `ls tools/tailwindcss`
- After CSS build: verify new/changed classes appear in `app/static/dist/style.css`

### Existing test coverage

- **E2E tests** (`tests/e2e/test_homepage.py`): 10 tests covering page title, branding, textarea, form elements, mode toggle, security headers, CSRF. These test structural presence, not visual styling.
- **Route tests** (`tests/test_history_routes.py`): 4 index-specific tests covering recent analyses list rendering, verdict badges, error handling.
- All 977+ tests must continue to pass after changes.

### Constraints

- CSS changes must stay inside `@layer components` (CSS Layer Ownership Rule from input.css header)
- No Tailwind utility classes on elements that have component class styles (specificity conflict rule)
- Security: textContent-only DOM construction (SEC-08), CSP headers must be maintained
- Reduced motion media query already handles animation accessibility
- Template changes must preserve all existing CSS class names that E2E tests assert on (`.index-hero-brand`, `.ioc-textarea`, `#submit-btn`, `#clear-btn`, `#mode-toggle-widget`, etc.)

### Skill suggestions

No new skills needed. The `frontend-design` and `make-interfaces-feel-better` skills from `<available_skills>` are relevant references for the planner/executor but don't need installation — the design language is already codified in the CSS tokens.

---

## Verification Strategy

1. `ls tools/tailwindcss` — confirm binary present before build
2. `make css` — CSS builds without error
3. `make js` — JS builds without error (no TS changes expected, but verify no regressions)
4. `python3 -m pytest tests/e2e/test_homepage.py -v` — all 10 E2E homepage tests pass
5. `python3 -m pytest tests/test_history_routes.py -v` — all 13 route tests pass
6. `python3 -m pytest --tb=short -q` — full suite passes, zero regressions
7. Grep check: any new CSS classes appear in `app/static/dist/style.css`
