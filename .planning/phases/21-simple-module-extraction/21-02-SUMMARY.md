---
phase: 21-simple-module-extraction
plan: "02"
subsystem: ui
tags: [typescript, dom, modules, form, clipboard, timer]

# Dependency graph
requires:
  - phase: 21-01
    provides: "attr() DOM utility helper in utils/dom.ts"
  - phase: 20-type-definitions-foundation
    provides: "ioc.ts shared type layer"
provides:
  - "form.ts init() — submit button state, auto-grow, mode toggle, paste feedback"
  - "clipboard.ts init() — copy button listeners with data-value/data-enrichment"
  - "clipboard.ts writeToClipboard() — exported for Phase 22 enrichment export button"
affects: [22-module-extraction-continued, 23-typescript-bundle]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level timer: let pasteTimer: ReturnType<typeof setTimeout> | null = null"
    - "Non-nullable closure aliases: const ta: HTMLTextAreaElement = textarea after narrowing"
    - "textContent ?? fallback: btn.textContent ?? 'Copy' avoids string|null"
    - "Bare catch block: catch without parameter when error variable is unused"
    - "querySelector<T> overloads for typed DOM element access"

key-files:
  created:
    - app/static/src/ts/modules/form.ts
    - app/static/src/ts/modules/clipboard.ts
  modified: []

key-decisions:
  - "Non-nullable closure aliases (const ta = textarea) used instead of non-null assertions — TypeScript cannot narrow through closures, so binding to a new const after the if-check gives the closure a non-null type without assertions"
  - "pasteTimer at module scope not on HTMLElement — storing timer on element requires a custom property TypeScript rejects; module-level variable is the correct pattern"
  - "writeToClipboard exported from clipboard.ts — Phase 22 enrichment module needs it for the export-all button without duplicating the fallback logic"
  - "Bare catch block (no parameter) in fallbackCopy — error variable is unused, bare catch avoids noUnusedLocals violations"

patterns-established:
  - "Non-nullable closure alias: bind narrowed value to new const for use in nested functions"
  - "Module-level timer pattern: ReturnType<typeof setTimeout> | null initialized to null"
  - "textContent null-coalescing: ?? 'fallback' for guaranteed string type"

requirements-completed: [MOD-02, MOD-03]

# Metrics
duration: 3min
completed: 2026-03-01
---

# Phase 21 Plan 02: Form Controls and Clipboard Module Summary

**form.ts and clipboard.ts extracted from main.js — 5 form functions and 4 clipboard functions ported to strict TypeScript with typed DOM, module-level timer, and no non-null assertions**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-02-28T15:36:29Z
- **Completed:** 2026-02-28T15:39:32Z
- **Tasks:** 2
- **Files modified:** 2 created, 0 modified

## Accomplishments

- Created `modules/form.ts` with `init()` calling three sub-initializers:
  - `initSubmitButton()` — typed `HTMLTextAreaElement` / `HTMLButtonElement` queries, non-nullable closure aliases (`ta`, `sb`) to avoid assertions
  - `initAutoGrow()` — same closure alias pattern for `ta`; focus/blur listeners for `.has-focus` class
  - `initModeToggle()` — uses `attr(w, "data-mode")` from `utils/dom` instead of raw `getAttribute`; `updateSubmitLabel()` as a private helper
  - `showPasteFeedback()` — module-level `pasteTimer: ReturnType<typeof setTimeout> | null` replaces `feedback._timer` property on HTMLElement
- Created `modules/clipboard.ts` with two exports:
  - `init()` — attaches click listeners to `.copy-btn` elements using `attr()` for data attributes
  - `writeToClipboard(text, btn)` — exported for Phase 22 enrichment module's export button
  - `showCopiedFeedback()` — uses `btn.textContent ?? "Copy"` to avoid `string | null`
  - `fallbackCopy()` — bare `catch` block (no parameter), `execCommand("copy")` fallback

## Task Commits

Each task was committed atomically:

1. **Task 1: Create form controls module** — `9bb8a91` (feat)
2. **Task 2: Create clipboard module** — `f36aed2` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `app/static/src/ts/modules/form.ts` — 5 functions: initSubmitButton, initAutoGrow, initModeToggle, updateSubmitLabel, showPasteFeedback; exports init()
- `app/static/src/ts/modules/clipboard.ts` — 4 functions: init, writeToClipboard, showCopiedFeedback, fallbackCopy

## Decisions Made

- **Non-nullable closure aliases** — TypeScript's control flow narrowing does not carry through nested function closures. After `if (!textarea || !submitBtn) return`, binding `const ta: HTMLTextAreaElement = textarea` gives the inner `updateSubmitState` function a non-null reference without resorting to `!` assertions. This pattern is now established for all modules with nested event handlers.
- **Module-level `pasteTimer`** — main.js stored the timer as `feedback._timer` on an HTMLElement, which TypeScript rejects under strict mode (non-standard property). Module scope is the correct storage location; the `ReturnType<typeof setTimeout>` type avoids the `NodeJS.Timeout` conflict.
- **`writeToClipboard` exported** — Phase 22's enrichment module needs to copy multi-IOC export text to clipboard without duplicating the navigator.clipboard + fallback logic. Exporting from clipboard.ts is the correct sharing mechanism.

## Deviations from Plan

None — plan executed exactly as written. The non-nullable closure alias approach was the intended solution (mentioned in plan notes about closures not seeing outer narrowing).

## Issues Encountered

Pre-existing `filter.ts` had typecheck errors in the working tree at the start of this plan run. A second typecheck invocation showed the errors had cleared (transient state from the prior session). No action was required.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `form.ts` and `clipboard.ts` complete the "simple" modules from Phase 21
- Phase 21 Plan 03 (filter and cards modules) can proceed immediately
- `writeToClipboard` from clipboard.ts is ready for import by Phase 22's enrichment module

---
*Phase: 21-simple-module-extraction*
*Completed: 2026-02-28*

## Self-Check: PASSED

- FOUND: app/static/src/ts/modules/form.ts
- FOUND: app/static/src/ts/modules/clipboard.ts
- FOUND: .planning/phases/21-simple-module-extraction/21-02-SUMMARY.md
- FOUND: commit 9bb8a91 (feat(21-02): add form controls module)
- FOUND: commit f36aed2 (feat(21-02): add clipboard module with writeToClipboard export)
