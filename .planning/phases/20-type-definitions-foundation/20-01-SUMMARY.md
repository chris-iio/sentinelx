---
phase: 20-type-definitions-foundation
plan: "01"
subsystem: ui
tags: [typescript, types, discriminated-union, ioc-enrichment]

# Dependency graph
requires:
  - phase: 19-build-pipeline-infrastructure
    provides: tsconfig.json with strict/isolatedModules/noUncheckedIndexedAccess, TypeScript toolchain

provides:
  - VerdictKey and IocType union types in app/static/src/ts/types/ioc.ts
  - VERDICT_SEVERITY, VERDICT_LABELS, IOC_PROVIDER_COUNTS typed constants in ioc.ts
  - EnrichmentResultItem, EnrichmentErrorItem discriminated union in app/static/src/ts/types/api.ts
  - EnrichmentItem and EnrichmentStatus interfaces in api.ts
  - Type-safe import layer covering all Flask API response shapes

affects:
  - 21-module-conversion
  - 22-module-integration
  - Any TypeScript module that handles enrichment results or verdict display

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Discriminated union pattern: type literal field ('result' | 'error') enables exhaustive narrowing"
    - "import type (not import) for type-only cross-module imports under isolatedModules"
    - "Record<VerdictKey, string> over Record<string, string> for exhaustiveness checking"
    - "as const satisfies readonly VerdictKey[] for preserving tuple literal type on VERDICT_SEVERITY"
    - "string | null (not ?: string) for always-present nullable fields"

key-files:
  created:
    - app/static/src/ts/types/ioc.ts
    - app/static/src/ts/types/api.ts
  modified: []

key-decisions:
  - "IocType excludes 'cve' — CVEs are extracted but never enriched (no IOC_PROVIDER_COUNTS entry)"
  - "scan_date typed as string | null not optional ?: string — field always present but may be null"
  - "raw_stats typed as Record<string, unknown> not object/any — forces downstream narrowing"
  - "VerdictKey applied to verdict field in EnrichmentResultItem, not string — compile-time guard"
  - "as const satisfies pattern used on VERDICT_SEVERITY to preserve tuple while validating values"

patterns-established:
  - "Type-only imports: use 'import type' for all cross-module type references (isolatedModules requirement)"
  - "Discriminated unions: literal type fields as discriminant for exhaustive switch/if-else narrowing"
  - "Typed constants: Record<K, V> with domain union keys instead of Record<string, V>"

requirements-completed: [TYPE-01, TYPE-02, TYPE-03, TYPE-04]

# Metrics
duration: 2min
completed: 2026-03-01
---

# Phase 20 Plan 01: Type Definitions Foundation Summary

**VerdictKey/IocType union types, typed VERDICT_SEVERITY/VERDICT_LABELS/IOC_PROVIDER_COUNTS constants, and EnrichmentResultItem/EnrichmentErrorItem discriminated union interfaces — zero-runtime TypeScript type layer under strict/isolatedModules/noUncheckedIndexedAccess**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-28T15:05:57Z
- **Completed:** 2026-02-28T15:07:50Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `ioc.ts` with VerdictKey (5-member union), IocType (7-member union), and three typed constants (VERDICT_SEVERITY tuple, VERDICT_LABELS Record, IOC_PROVIDER_COUNTS Record) sourced exactly from main.js lines 228-250
- Created `api.ts` with EnrichmentResultItem/EnrichmentErrorItem discriminated union (type literal discriminant) and EnrichmentStatus interface matching Flask `_serialize_result` JSON shape from routes.py
- Verified four type-safety behaviors: Node.js globals rejected, invalid VerdictKey assignment rejected, discriminated union narrowing works, no non-null assertions or DOM access in type files
- `make typecheck` exits 0 and `make js` still produces the IIFE bundle unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1: Create domain types and API response interfaces** - `571eefa` (feat)
2. **Task 2: Verify tsconfig enforcement and type safety** - verification only, no file changes; captured in Task 1 commit

## Files Created/Modified

- `app/static/src/ts/types/ioc.ts` — VerdictKey, IocType union types; VERDICT_SEVERITY as const tuple; VERDICT_LABELS and IOC_PROVIDER_COUNTS as typed Records
- `app/static/src/ts/types/api.ts` — EnrichmentResultItem and EnrichmentErrorItem interfaces with type discriminant; EnrichmentItem union; EnrichmentStatus interface

## Decisions Made

- `IocType` excludes `"cve"` because CVEs are extracted but never enriched (IOC_PROVIDER_COUNTS has no cve key)
- `scan_date` is `string | null` (not `?: string`) because the field is always serialized by Flask but may be null — forcing callers to handle the null case
- `raw_stats` is `Record<string, unknown>` (not `object` or `any`) so downstream code must narrow before accessing fields
- `VerdictKey` applied to `verdict` in `EnrichmentResultItem` rather than `string` — compile-time guard against invalid verdict values
- Used `as const satisfies readonly VerdictKey[]` on VERDICT_SEVERITY to preserve the tuple literal type while validating all array members are valid VerdictKey values

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Type foundation complete — all downstream modules in Phases 21-22 can `import type { VerdictKey } from "./types/ioc"` and `import type { EnrichmentItem } from "./types/api"`
- tsconfig.json unchanged and already correct from Phase 19
- No blockers or concerns

---
*Phase: 20-type-definitions-foundation*
*Completed: 2026-03-01*
