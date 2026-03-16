---
phase: 02-typescript-module-extractions
plan: 01
subsystem: ui
tags: [typescript, esbuild, iife, module-extraction, refactoring]

# Dependency graph
requires:
  - phase: 01-contracts-and-foundation
    provides: CSS contracts catalog and E2E baseline (89/91)
provides:
  - verdict-compute.ts — pure verdict computation functions (VerdictEntry, computeWorstVerdict, computeConsensus, computeAttribution, findWorstEntry, consensusBadgeClass)
  - row-factory.ts — DOM row construction (CONTEXT_PROVIDERS, createProviderRow, createContextRow, createDetailRow, updateSummaryRow, getOrCreateSummaryRow)
  - Trimmed enrichment.ts — polling orchestrator and module state only (~317 code lines)
affects: [03-visual-redesign, 04-template-restructuring]

# Tech tracking
tech-stack:
  added: []
  patterns: [pure-extraction-module-split, thin-dispatcher-wrapper, one-directional-dependency-graph]

key-files:
  created:
    - app/static/src/ts/modules/verdict-compute.ts
    - app/static/src/ts/modules/row-factory.ts
  modified:
    - app/static/src/ts/modules/enrichment.ts
    - app/static/dist/main.js

key-decisions:
  - "formatDate exported from row-factory.ts (not private) because renderEnrichmentResult in enrichment.ts needs it for scan_date formatting"
  - "createProviderRow thin dispatcher added to row-factory.ts as stable API surface for Phase 3 visual work"
  - "VERDICT_LABELS and EnrichmentResultItem imports removed from enrichment.ts — only needed by row-factory.ts now"

patterns-established:
  - "Pure extraction pattern: move functions verbatim with only export keyword added, verify after each step"
  - "One-directional dependency graph: enrichment.ts -> verdict-compute.ts, enrichment.ts -> row-factory.ts, row-factory.ts -> verdict-compute.ts (no reverse)"
  - "Thin dispatcher wrapper: createProviderRow routes to existing functions without adding logic"

requirements-completed: []

# Metrics
duration: 8min
completed: 2026-03-17
---

# Phase 2 Plan 1: TypeScript Module Extractions Summary

**928-LOC enrichment.ts monolith split into three focused modules: verdict-compute.ts (pure functions), row-factory.ts (DOM builders), and trimmed enrichment.ts (polling orchestrator) with zero behavioral change and 89/91 E2E pass**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-16T21:00:31Z
- **Completed:** 2026-03-16T21:08:42Z
- **Tasks:** 3
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments
- Extracted 5 pure computation functions into verdict-compute.ts (118 LOC with JSDoc) — zero DOM access, zero side effects
- Extracted all DOM row construction code into row-factory.ts (373 LOC) with CONTEXT_PROVIDERS set and createProviderRow dispatcher
- Trimmed enrichment.ts from 928 to 482 LOC (317 code lines) — now contains only polling orchestrator, module state, and coordinator functions
- Maintained E2E baseline at 89/91 (2 pre-existing title capitalization failures unchanged)
- One-directional dependency graph with no circular imports confirmed by tsc --noEmit

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract verdict-compute.ts** - `8d575ab` (feat)
2. **Task 2: Extract row-factory.ts** - `2537c42` (feat)
3. **Task 3: Verify trimmed enrichment.ts and run E2E** - `5d87347` (refactor)

**Plan metadata:** (pending) (docs: complete plan)

## Files Created/Modified
- `app/static/src/ts/modules/verdict-compute.ts` - Pure verdict computation: VerdictEntry interface + 5 exported functions (computeWorstVerdict, computeConsensus, consensusBadgeClass, computeAttribution, findWorstEntry)
- `app/static/src/ts/modules/row-factory.ts` - DOM row construction: CONTEXT_PROVIDERS set, PROVIDER_CONTEXT_FIELDS, createProviderRow dispatcher, createContextRow, createDetailRow, updateSummaryRow, getOrCreateSummaryRow, plus private helpers (formatDate, formatRelativeTime, createLabeledField, createContextFields, ContextFieldDef)
- `app/static/src/ts/modules/enrichment.ts` - Trimmed to polling orchestrator: sortDetailRows, findCopyButtonForIoc, updateCopyButtonWorstVerdict, updateProgressBar, updatePendingIndicator, showEnrichWarning, markEnrichmentComplete, renderEnrichmentResult, wireExpandToggles, initExportButton, init
- `app/static/dist/main.js` - Rebuilt IIFE bundle (functionally identical)

## Decisions Made
- **formatDate exported from row-factory.ts:** Plan specified formatDate as private, but renderEnrichmentResult in enrichment.ts calls it for scan_date formatting. Exporting it was the minimal fix (Rule 3 auto-fix).
- **createProviderRow thin dispatcher:** Added as specified in plan — routes between createContextRow and createDetailRow based on kind parameter. Provides stable API for Phase 3.
- **Unused imports cleaned:** Removed VERDICT_LABELS and EnrichmentResultItem from enrichment.ts imports since they moved with the row construction code.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Exported formatDate from row-factory.ts**
- **Found during:** Task 2 (row-factory.ts extraction)
- **Issue:** Plan specified formatDate as non-exported private helper in row-factory.ts, but renderEnrichmentResult in enrichment.ts calls formatDate(result.scan_date) at line 284
- **Fix:** Changed formatDate to `export function` in row-factory.ts and added it to the row-factory import in enrichment.ts
- **Files modified:** app/static/src/ts/modules/row-factory.ts, app/static/src/ts/modules/enrichment.ts
- **Verification:** tsc --noEmit passes, make js-dev builds successfully
- **Committed in:** 2537c42 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minimal — single function visibility change from private to exported. No scope creep. No behavioral change.

## Issues Encountered
- LOC counts in acceptance criteria (250-350 for enrichment.ts, 60-100 for verdict-compute.ts, 120-200 for row-factory.ts) were based on code-only estimates. Actual files with full JSDoc documentation are larger (482, 118, 373 respectively) but code lines are within target (317, ~70, ~200). This is cosmetic — the extraction goal is achieved.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 3 (Visual Redesign) can now modify row appearance by editing only row-factory.ts without touching orchestration logic in enrichment.ts
- The createProviderRow dispatcher provides a stable entry point for Phase 3
- CONTEXT_PROVIDERS set is co-located with the rendering code it controls
- All verdict computation is isolated in verdict-compute.ts for independent testing or modification

## Self-Check: PASSED

All files exist. All commits verified.

---
*Phase: 02-typescript-module-extractions*
*Completed: 2026-03-17*
