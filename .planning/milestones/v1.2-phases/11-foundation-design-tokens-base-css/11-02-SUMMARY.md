---
phase: 11-foundation-design-tokens-base-css
plan: "02"
subsystem: ui
tags: [css-variables, design-tokens, zinc, emerald, teal, verdict-colors, autofill, typography]

# Dependency graph
requires:
  - 11-01 (font infrastructure, @font-face declarations, Tailwind config)
provides:
  - Complete zinc/emerald/teal CSS custom property design token system in :root
  - Verdict color triples (text/bg/border) for all 5 verdict states in :root
  - Typography scale tokens (weight-heading, weight-body, weight-caption, tracking-heading, line-height-body)
  - All component rules updated to reference new verdict triple tokens
  - Autofill override CSS (box-shadow inset trick) for dark input fields
  - Rebuilt dist/style.css with new token values
affects: [11-03, 12-components, all-phases-that-modify-input.css]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Verdict color triple pattern — each verdict state has -text/-bg/-border token triple for consistent tinted-bg styling
    - Opacity-based borders — rgba(255,255,255,0.06/0.10/0.18) instead of solid hex for zinc surface hierarchy
    - Autofill override — box-shadow inset to 100px overrides browser's yellow autofill background on dark inputs

key-files:
  created: []
  modified:
    - app/static/src/input.css
    - app/static/dist/style.css

key-decisions:
  - "Verdict triple token naming: --verdict-{state}-{text|bg|border} — state names match Python backend values (malicious/suspicious/clean/no_data/error), hyphenated in CSS"
  - "Borders switched from solid hex (#30363d) to opacity-based white rgba — enables correct surface layering on zinc backgrounds without per-surface border customization"
  - "Suspicious badge previously used solid #f59e0b with black text (accessibility failure) — now uses amber-950 tinted-bg + amber-400 text + amber-500 border pattern consistent with other verdicts"
  - "Autofill override placed inside @layer components using box-shadow inset trick — the only reliable cross-browser method to prevent yellow autofill background on dark inputs"
  - "text-muted token (zinc-500, #71717a) replaces text-secondary+opacity:0.6 for placeholders — single token at correct luminance eliminates the opacity multiplication complexity"

# Metrics
duration: 2min
completed: "2026-02-26"
---

# Phase 11 Plan 02: Design Token Rewrite Summary

**Complete zinc/emerald/teal CSS custom property system replacing GitHub blue-gray palette, with verdict triple tokens for all five states, typography scale, and autofill override**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-26T06:38:46Z
- **Completed:** 2026-02-26T06:40:46Z
- **Tasks:** 2
- **Files modified:** 2 (input.css and rebuilt dist/style.css)

## Accomplishments

- Replaced the entire :root token block — GitHub blue-gray (#0d1117/#161b22/#1c2128) replaced with zinc hierarchy (#09090b/#18181b/#27272a)
- Added 5 new tokens: --bg-hover, --border-default, --text-muted, --accent-interactive, --accent-subtle
- Upgraded --text-secondary from #8b949e (fails WCAG AA on zinc-900) to #a1a1aa (zinc-400, passes 4.5:1 against zinc-900)
- Removed 5 old single-name verdict tokens, replaced with 15 verdict triple tokens across all 5 verdict states
- Updated all verdict component rules (verdict-dashboard-badge, filter-btn active states, ioc-card border-left, verdict-label, verdict-badge classes) to reference triple tokens
- Fixed suspicious verdict badge: was solid #f59e0b background with black text — now uses tinted-bg pattern consistent with all other verdicts
- Updated placeholder rules to use --text-muted with opacity:1 (replacing text-secondary+opacity:0.6)
- Added autofill override block with box-shadow inset trick to prevent yellow browser autofill background
- Updated --font-ui to start with Inter Variable, --font-mono to JetBrains Mono Variable
- Added 5 typography scale tokens: --weight-heading (600), --weight-body (400), --weight-caption (500), --tracking-heading (-0.02em), --line-height-body (1.6)
- Added color-scheme: dark to :root for OS-level dark mode signal
- `make css` rebuilt dist/style.css successfully
- All 224 unit and integration tests pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite :root token block and typography scale** - `432a5f6` (feat)
2. **Task 2: Update component rules for new token names and add autofill override** - `3c89f2a` (feat)

## Files Created/Modified

- `app/static/src/input.css` — Complete :root rewrite (zinc/emerald/teal palette, verdict triples, typography scale, autofill override, component rule updates)
- `app/static/dist/style.css` — Rebuilt CSS output reflecting all new token values

## Decisions Made

- **Verdict triple token naming:** `--verdict-{state}-{text|bg|border}`. State names match Python backend verdict values (malicious/suspicious/clean/no_data/error). Note: CSS token uses hyphen (`--verdict-no-data-*`) while Python/HTML uses underscore (`no_data`) — this is correct and intentional, following CSS naming conventions.

- **Opacity-based borders:** Switched from solid hex borders (#30363d, #484f58) to `rgba(255, 255, 255, 0.06/0.10/0.18)`. This creates correct visual hierarchy when borders appear on zinc-950, zinc-900, and zinc-800 surfaces — the same opacity produces visually consistent borders regardless of background surface.

- **Suspicious badge fix:** The old suspicious badge used `background-color: #f59e0b; color: #000` — a solid amber background with black text. This was an outlier among all verdict styles and failed to follow the established tinted-bg pattern. The new style uses amber-950 tinted-bg + amber-400 text + amber-500 border, consistent with all other verdicts. Phase 12 COMP-01 will complete this visual treatment.

- **Autofill override technique:** Browser autofill sets an OS-specific background color that cannot be overridden with `background-color`. The only reliable cross-browser workaround is `box-shadow: 0 0 0 100px {color} inset !important` — a large inset box shadow that visually covers the autofill background. The 5000s transition on background-color delays the fade-out until the form is submitted.

- **text-muted for placeholders:** The old approach used `color: var(--text-secondary); opacity: 0.6` — applying opacity to an already-dimmed color. This creates unpredictable rendering since opacity is inherited. `--text-muted` (zinc-500, #71717a) is at exactly the correct luminance for placeholder text with opacity:1, eliminating the multiplication complexity.

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

All plan verification criteria satisfied:

1. :root block contains complete zinc/emerald/teal token set — PASS
2. All verdict component rules use triple tokens — PASS
3. No orphaned single-name verdict token references — PASS (grep returns empty)
4. Typography scale tokens defined (5 tokens) — PASS
5. --font-ui references Inter Variable, --font-mono references JetBrains Mono Variable — PASS
6. Autofill override CSS block present with box-shadow inset trick — PASS
7. `make css` succeeds (Done in 412ms) — PASS
8. All 224 unit/integration pytest tests pass — PASS (pre-existing E2E failure for test_online_mode_indicator is VT API key gate, not a regression)
9. grep for #0d1117, #161b22, #1c2128, #8b949e in :root returns zero matches — PASS

## Self-Check: PASSED

| Item | Status |
|------|--------|
| app/static/src/input.css | FOUND |
| app/static/dist/style.css | FOUND |
| Commit 432a5f6 (Task 1) | FOUND |
| Commit 3c89f2a (Task 2) | FOUND |
| 11-02-SUMMARY.md | FOUND |
