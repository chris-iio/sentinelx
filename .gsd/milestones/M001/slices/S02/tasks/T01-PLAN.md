# T01: 02-typescript-module-extractions 01

**Slice:** S02 — **Milestone:** M001

## Description

Extract the 928-LOC enrichment.ts monolith into three focused modules with zero behavioral change.

Purpose: Isolate verdict computation (pure functions) and DOM row construction (row-factory) from the polling orchestrator so that Phase 3 (Visual Redesign) can modify row appearance in a single file without touching orchestration logic.

Output: Three TypeScript modules — verdict-compute.ts (~80 LOC), row-factory.ts (~150 LOC), enrichment.ts trimmed to ~300 LOC — that compile cleanly and produce an identical IIFE bundle.

## Must-Haves

- [ ] "verdict-compute.ts exists with 5 exported pure functions and 1 exported interface, zero DOM access"
- [ ] "row-factory.ts exists with all DOM row-building code, CONTEXT_PROVIDERS set, and a createProviderRow dispatcher"
- [ ] "enrichment.ts is trimmed to the polling orchestrator and state owner only — no verdict computation, no row building"
- [ ] "All 91 E2E tests pass unchanged — zero behavioral change"
- [ ] "TypeScript strict mode compiles cleanly with no errors"

## Files

- `app/static/src/ts/modules/verdict-compute.ts`
- `app/static/src/ts/modules/row-factory.ts`
- `app/static/src/ts/modules/enrichment.ts`
