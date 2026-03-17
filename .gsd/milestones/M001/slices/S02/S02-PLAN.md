# S02: TypeScript Module Extractions

**Goal:** Split the 928-LOC enrichment.ts monolith into three focused modules — verdict-compute.ts (pure functions ~80 LOC), row-factory.ts (DOM builders ~150 LOC), and trimmed enrichment.ts (polling orchestrator ~300 LOC) — with zero behavioral change.
**Demo:** Three TypeScript modules compile cleanly; createProviderRow dispatcher provides stable API for Phase 3; all 89/91 E2E tests pass unchanged.

## Must-Haves


## Tasks

- [x] **T01: 02-typescript-module-extractions 01** `est:8min`
  - Extract the 928-LOC enrichment.ts monolith into three focused modules with zero behavioral change.

Purpose: Isolate verdict computation (pure functions) and DOM row construction (row-factory) from the polling orchestrator so that Phase 3 (Visual Redesign) can modify row appearance in a single file without touching orchestration logic.

Output: Three TypeScript modules — verdict-compute.ts (~80 LOC), row-factory.ts (~150 LOC), enrichment.ts trimmed to ~300 LOC — that compile cleanly and produce an identical IIFE bundle.

## Files Likely Touched

- `app/static/src/ts/modules/verdict-compute.ts`
- `app/static/src/ts/modules/row-factory.ts`
- `app/static/src/ts/modules/enrichment.ts`
