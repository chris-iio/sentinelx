---
phase: 11-foundation-design-tokens-base-css
plan: "01"
subsystem: ui
tags: [tailwindcss, fonts, inter, jetbrains-mono, woff2, css-variables, dark-mode]

# Dependency graph
requires: []
provides:
  - Inter Variable woff2 font file at app/static/fonts/InterVariable.woff2
  - JetBrains Mono Variable woff2 font file at app/static/fonts/JetBrainsMonoVariable.woff2
  - "@font-face declarations in input.css for both variable fonts"
  - "color-scheme: dark meta tag in base.html for OS-level dark scrollbars"
  - Font preload links with crossorigin in base.html for both variable fonts
  - darkMode: selector in tailwind.config.js for class-based dark theming
  - "@tailwindcss/forms plugin activated in tailwind.config.js"
affects: [11-02, 11-03, 12-components, all-phases-that-modify-input.css-or-base.html]

# Tech tracking
tech-stack:
  added:
    - Inter Variable woff2 (rsms/inter v4.1, 352KB, weight 100-900)
    - JetBrains Mono Variable woff2 (JetBrains/JetBrainsMono v2.304, 113KB, converted from TTF using fonttools+brotli, weight 100-800)
    - "@tailwindcss/forms plugin (bundled in Tailwind standalone CLI)"
  patterns:
    - Self-hosted variable fonts with @font-face before @tailwind directives
    - Flask url_for() for font preload href references
    - color-scheme meta tag for OS-level dark mode browser chrome

key-files:
  created:
    - app/static/fonts/InterVariable.woff2
    - app/static/fonts/JetBrainsMonoVariable.woff2
  modified:
    - app/static/src/input.css
    - app/templates/base.html
    - tailwind.config.js
    - app/static/dist/style.css

key-decisions:
  - "JetBrains Mono v2.304 zip contains only TTF variable fonts (no woff2) — used fonttools+brotli to convert JetBrainsMono[wght].ttf to woff2 format in-place"
  - "Inter Variable from rsms/inter v4.1 zip at web/InterVariable.woff2 (not root level) — 352KB"
  - "darkMode: selector chosen over darkMode: class (selector is the modern Tailwind v3 approach, supports both .dark class and [data-theme=dark] attribute)"
  - "@font-face declarations placed before @tailwind base to ensure they are in the normal cascade layer, not inside @layer base"

patterns-established:
  - "Pattern 1: @font-face before @tailwind — variable font declarations must appear before @tailwind base; in input.css to ensure correct CSS cascade ordering"
  - "Pattern 2: Flask font URLs — use /static/fonts/ in @font-face src: url() (browser-visible path), use url_for('static', filename='fonts/...') for HTML preload links"
  - "Pattern 3: Font preload crossorigin — font preload links require crossorigin attribute even for same-origin resources to avoid double-fetching"

requirements-completed: [FOUND-02, FOUND-03, FOUND-04, FOUND-07]

# Metrics
duration: 4min
completed: "2026-02-26"
---

# Phase 11 Plan 01: Font Infrastructure & Dark Mode Foundation Summary

**Self-hosted Inter Variable and JetBrains Mono Variable fonts with @font-face, color-scheme meta, preload links, darkMode selector, and @tailwindcss/forms in Tailwind config**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-26T06:31:33Z
- **Completed:** 2026-02-26T06:35:33Z
- **Tasks:** 2
- **Files modified:** 5 (2 created, 3 modified + dist/style.css rebuilt)

## Accomplishments

- Downloaded and installed Inter Variable woff2 (352KB) from rsms/inter v4.1 release zip
- Obtained JetBrains Mono Variable woff2 (113KB) by converting the TTF variable font using fonttools+brotli
- Added @font-face declarations at top of input.css before all @tailwind directives, with correct browser-visible URL paths
- Added color-scheme: dark meta tag and font preload links with crossorigin to base.html
- Configured tailwind.config.js with darkMode: selector and @tailwindcss/forms plugin
- All 224 existing tests pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Download variable fonts and add @font-face declarations** - `92e797e` (feat)
2. **Task 2: Update base.html and tailwind.config.js** - `8146649` (feat)

## Files Created/Modified

- `app/static/fonts/InterVariable.woff2` — Self-hosted Inter Variable font (352KB, weight 100-900)
- `app/static/fonts/JetBrainsMonoVariable.woff2` — Self-hosted JetBrains Mono Variable font (113KB, converted from TTF, weight 100-800)
- `app/static/src/input.css` — Added @font-face declarations for both variable fonts before @tailwind base;
- `app/templates/base.html` — Added color-scheme meta, preload links for both fonts with crossorigin
- `tailwind.config.js` — Added darkMode: 'selector' and @tailwindcss/forms plugin
- `app/static/dist/style.css` — Rebuilt with new Tailwind config (forms plugin styles included)

## Decisions Made

- **JetBrains Mono TTF conversion:** The v2.304 release zip contains only TTF variable fonts, not woff2. Used fonttools+brotli (pip install) to convert `JetBrainsMono[wght].ttf` to woff2 format. The resulting file is valid woff2 (113KB vs 303KB TTF — expected compression ratio).
- **darkMode: selector vs class:** Used `'selector'` (Tailwind v3.3+ default) which activates dark utilities on any CSS selector match, not just `.dark` class. Compatible with future `[data-theme="dark"]` attribute strategy.
- **@font-face placement:** Placed before @tailwind base; to keep them in the global cascade layer, not inside Tailwind's @layer base. This is correct per Tailwind docs and ensures font declarations aren't scoped.
- **Inter extracted from zip subfolder:** The v4.1 release zip has the woff2 at `web/InterVariable.woff2`, not at root. Used Python zipfile module to extract (unzip's glob handling mangled the path).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] JetBrains Mono woff2 variable font not in release zip**
- **Found during:** Task 1 (Download variable fonts)
- **Issue:** The plan specified extracting `fonts/variable/*[wght].woff2` from the JetBrains Mono zip, but v2.304 contains only TTF variable fonts in that directory — no woff2 variable font exists in the release.
- **Fix:** Used `pip install fonttools brotli` and converted `JetBrainsMono[wght].ttf` to woff2 using fonttools' `font.flavor = 'woff2'` approach. Result is a valid woff2 file (113KB).
- **Files modified:** app/static/fonts/JetBrainsMonoVariable.woff2 (created)
- **Verification:** File is 113KB (valid woff2 size), `make css` builds successfully, 224 tests pass
- **Committed in:** 92e797e (Task 1 commit)

**2. [Rule 3 - Blocking] Inter Variable v4.1 direct URL returns 404**
- **Found during:** Task 1 (Download variable fonts)
- **Issue:** The plan's recommended curl URL `https://github.com/rsms/inter/releases/download/v4.1/InterVariable.woff2` returned "Not Found" — the v4.1 release only ships a zip, not individual font files.
- **Fix:** Downloaded `Inter-4.1.zip` and extracted `web/InterVariable.woff2` using Python zipfile (unzip's glob handling failed on the path with special chars in JetBrains Mono case; used Python for consistency).
- **Files modified:** app/static/fonts/InterVariable.woff2 (created)
- **Verification:** File is 352KB (valid woff2 size), matches rsms/inter documented variable font weight range
- **Committed in:** 92e797e (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 - Blocking)
**Impact on plan:** Both fixes were necessary to obtain the font files. The end result is identical to plan intent — valid woff2 variable fonts for both typefaces. No scope creep.

## Issues Encountered

- `unzip` command could not handle `fonts/variable/JetBrainsMono[wght].ttf` path due to bracket characters being interpreted as glob patterns. Resolved by using Python's `zipfile` module for extraction.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Font infrastructure complete: both woff2 files committed, @font-face declarations in place
- Dark mode signal active: color-scheme meta in base.html
- Tailwind build pipeline functional: darkMode selector + forms plugin verified
- Phase 11 Plan 02 (design tokens / CSS custom properties) can proceed immediately
- Plans 02 and 03 both modify input.css — sequential execution required (already planned)

---
*Phase: 11-foundation-design-tokens-base-css*
*Completed: 2026-02-26*
