---
estimated_steps: 6
estimated_files: 1
---

# T02: Apply quiet precision design system — verdict-only loud color + typography hierarchy

**Slice:** S01 — Layout skeleton + quiet precision design system
**Milestone:** M002

## Description

This task transforms the visual identity from "wall of colored badges" to quiet precision (decision D011) where verdict severity is the only loud color signal. It's CSS-only work on `input.css`, building on top of T01's structural layout changes. The goal is to deliver requirement R003: analysts see verdict severity instantly because nothing else competes for visual attention.

**Load the `frontend-design` skill** for guidance on typography hierarchy, color restraint, and production-grade polish. The aesthetic direction is "quiet precision" — Linear/Vercel energy. This means: muted neutral chrome, clear typographic hierarchy through weight/size/opacity, verdict color as the sole loud signal, professional-tool visual density.

After completing the CSS changes, this task runs the full verification suite including E2E tests to confirm nothing was broken across both T01 and T02.

## Steps

1. **Read current `input.css`** to understand the current state after T01 changes:
   - Focus on: `.ioc-type-badge--*` variant styles, `.filter-pill--*` active states, verdict color tokens, mode pill styles, any remaining loud non-verdict color

2. **Mute IOC type badge colors** in `input.css`:
   - Find all `.ioc-type-badge--ip`, `.ioc-type-badge--domain`, `.ioc-type-badge--hash`, `.ioc-type-badge--url` (and any other type variants)
   - Replace bright background colors with muted neutral treatment: subtle gray/neutral border, muted text color, no colored background
   - Type should still be identifiable — via text content and subtle shape/border, not color

3. **Mute active filter pill type colors**:
   - Find `.filter-pill--{type}.filter-pill--active` rules
   - Replace bright type-specific active colors with a neutral active state (e.g., dark text, subtle background, no colored border)
   - Verdict filter pills should also use muted treatment for non-active state, but the VERDICT pills can retain their verdict color when active (since verdict IS the allowed loud color)

4. **Establish typography hierarchy**:
   - IOC value (`.ioc-value`) — most prominent: larger font size, bold weight
   - IOC type label (`.ioc-type-badge`) — small, muted, uppercase or caps styling for scannability without loudness
   - Verdict label (`.verdict-label`) — bold with verdict-specific color background (the ONE loud element)
   - Context line (`.ioc-context-line`) — secondary size, medium opacity, lighter weight
   - Action buttons (`.copy-btn`, detail links) — small, muted, visible on hover or always quiet
   - Dashboard counts — compact text, verdict-colored numbers with muted labels
   - Filter pills — small, muted, border-based inactive state

5. **Polish row presentation**:
   - Refine row hover state: subtle background shift, not dramatic
   - Ensure borders between rows are light and consistent
   - Make enrichment area (`.enrichment-slot`) visually subordinate — no prominent styling that draws attention before S02 populates it
   - Verify verdict color tokens are vivid and distinct: malicious=red, suspicious=amber/orange, clean=green, known_good=blue, no_data=gray
   - Mute any remaining loud non-verdict accents (mode pills, misc UI chrome)

6. **Run full verification suite**:
   - `make css` — Tailwind compiles
   - `make typecheck` — TypeScript passes
   - `make js-dev` — Bundle builds
   - `pytest tests/e2e/test_extraction.py -q` — Base results page structure correct
   - `pytest tests/e2e/test_results_page.py -q` — Filter, dashboard, enrichment slot selectors all found
   - If any E2E test fails, inspect the failure and fix — the issue is likely a selector or structure problem from T01 that needs correction

## Must-Haves

- [ ] `.ioc-type-badge--*` variants use muted neutral styling (no bright type-specific background colors)
- [ ] Active filter pills use muted styling (no bright type-specific colors)
- [ ] Verdict labels/badges are the ONLY loud color on the results page
- [ ] Typography creates clear information hierarchy: value > verdict > type > context > actions
- [ ] Enrichment area is visually subordinate (not prominent before S02)
- [ ] All verdict color tokens (malicious, suspicious, clean, known_good, no_data) remain vivid and distinct
- [ ] `make css`, `make typecheck`, `make js-dev` all pass
- [ ] `pytest tests/e2e/test_extraction.py -q` passes
- [ ] `pytest tests/e2e/test_results_page.py -q` passes

## Verification

- `make css` exits 0
- `make typecheck` exits 0
- `make js-dev` exits 0
- `pytest tests/e2e/test_extraction.py -q` exits 0
- `pytest tests/e2e/test_results_page.py -q` exits 0
- Visual inspection: no bright non-verdict colors visible on results page; type badges are muted; verdict badges are vivid

## Inputs

- `app/static/src/input.css` — stylesheet after T01 structural changes
- T01 completion — all template restructuring already done, structural CSS in place

## Expected Output

- `app/static/src/input.css` — complete quiet precision design system: verdict-only loud color, muted type badges, muted filter pills, typography hierarchy, polished row presentation

## Observability Impact

**Signals that change after T02:**
- `make css` stdout — if any class name was mistyped or a Tailwind utility conflicts with a component class, the build emits a warning line; non-zero exit exposes the offending rule
- Browser devtools → Elements panel: `.ioc-type-badge--*` should show `color: var(--text-muted)` and `border-color: var(--border-default)` (no bright accent colors); `.filter-pill--*:active` should show `background-color: var(--bg-tertiary)` not accent; `.verdict-label--*` still shows vivid verdict color
- Browser devtools → Computed styles: `.ioc-value` should show `font-weight: 600` and `font-size: 0.9rem`
- Visual inspection signal: results page has exactly one class of loud color — verdict labels/borders; everything else is zinc-range neutrals

**Failure visibility:**
- If type badge still shows bright color: selector didn't match — inspect element to confirm class name matches template's `ioc-type-badge--{type}` pattern
- If verdict labels lose color: look for conflicting `!important` or specificity override from Tailwind utility class
- If enrichment slot invisible: `opacity: 0.85` + `min-height: 0` is intentional subordinate state; if completely hidden check for `display: none` or zero-height collapse on parent
