# Project Research Summary

**Project:** SentinelX v3.0 — TypeScript Migration
**Domain:** TypeScript build pipeline integration into existing Python/Flask static file architecture
**Researched:** 2026-02-28
**Confidence:** HIGH

## Executive Summary

SentinelX v3.0 is a TypeScript migration of a single 856-line vanilla JS IIFE (`app/static/main.js`) that powers a local SOC analyst triage tool. This is not a new application — it is a type-safety layer added to working code with zero new functional behavior. The recommended approach mirrors the existing Tailwind CSS pipeline exactly: download a standalone esbuild binary (no Node.js runtime), compile TypeScript source to an IIFE bundle, and serve the compiled output from Flask's static file endpoint. The migration decomposes the IIFE into typed ES modules (one per functional area), which esbuild bundles into a single `app/static/dist/main.js` at build time.

The key recommendation is to use esbuild v0.27.3 as a standalone binary (`tools/esbuild`) for bundling, and TypeScript 5.8.3 (installed via npm, dev-only) for type checking via `tsc --noEmit`. This separation — esbuild for transpilation/bundling, tsc for type validation — is the 2025 standard for browser-only TypeScript projects and enables fast incremental builds (~100ms) without a Node.js runtime requirement for production builds. IIFE output format is required because `base.html` uses a plain `<script defer>` tag and the CSP (`script-src 'self'`) must not change.

The primary risks are: (1) CSP violation if any bundler other than esbuild is used, since webpack and Vite inject dynamic code evaluation that breaks the `script-src 'self'` CSP asserted by existing security tests; (2) behavioral regressions from mixing refactoring with type annotations in the same PR — the E2E test suite (224 tests, 97% coverage) must pass after the migration before any code modernization begins; and (3) over-typing with `any` in complex areas like the enrichment polling logic, which defeats the migration's purpose. All three risks are preventable with the discipline of establishing the build pipeline first and type-annotating without refactoring.

## Key Findings

### Recommended Stack

The v3.0 stack adds three components to an otherwise locked-in system. The backend (Python 3.10 + Flask 3.1), CSS pipeline (Tailwind standalone CLI), design tokens, fonts, and Playwright E2E tests are all unchanged. The TypeScript additions are: esbuild standalone binary (`tools/esbuild`) as a parallel to `tools/tailwindcss`, TypeScript 5.8.3 installed via npm once for developer type checking, and a `tsconfig.json` at the project root configured for strict browser-only type checking.

**Core technologies (new additions only):**
- **esbuild 0.27.3 (standalone binary):** TypeScript bundler and minifier — standalone binary via curl (same pattern as Tailwind CLI), natively strips TypeScript types without Node.js, produces IIFE output compatible with the existing CSP and Flask static file serving
- **TypeScript 5.8.3 (npm, dev-only):** Type checking via `tsc --noEmit` — provides `lib.dom.d.ts` for DOM types (built-in, no `@types/*` packages needed), enforces strict null checks and domain type safety; TypeScript 6.0 is currently in beta and must be avoided
- **tsconfig.json:** Strict, browser-targeted, esbuild-compatible configuration — `strict: true`, `isolatedModules: true` (required by esbuild), `lib: ["es2022", "dom", "dom.iterable"]`, `moduleResolution: "Bundler"`, `noEmit: true`

### Expected Features

The migration's feature set is defined by correctness and build tooling, not new user-facing behavior. Behavioral parity with the existing IIFE is the success criterion.

**Must have (table stakes):**
- `strict: true` in tsconfig — without this, TypeScript adds syntax noise with no safety gain; the entire migration value comes from `strictNullChecks` and `noImplicitAny`
- DOM type narrowing for all `querySelector` calls — every `document.getElementById()` returns `HTMLElement | null`; existing `if (!el) return` guards must be preserved and type-annotated
- Type definitions for API response shapes — `EnrichmentResult`, `EnrichmentStatus`, `VerdictKey`, `IocType` interfaces document the Flask API contract and catch field name changes at compile time
- esbuild build pipeline (Makefile `js`, `js-watch`, `typecheck` targets) — without this there is no migration
- Behavioral parity — all 10 `initX` functions must behave identically after migration; the Playwright E2E suite is the verification mechanism

**Should have (valuable, same milestone):**
- Feature-based module splitting — 10 TypeScript modules (`modules/form.ts`, `modules/enrichment.ts`, `modules/filter.ts`, etc.) plus `types/ioc.ts` and `types/api.ts`; modules communicate through the DOM at runtime, not shared in-memory state
- `make typecheck` as a CI gate running `tsc --noEmit` — esbuild never type-checks; without this, type errors accumulate silently
- `modules/enrichment.ts` verdict utility functions (`computeWorstVerdict`, `verdictSeverity`) isolated from DOM manipulation code

**Defer (v4.0+):**
- Vitest unit tests for pure logic functions — the existing E2E tests already verify observable behavior; adding a JS test runtime is a separate decision that should not block the migration
- Zod runtime validation of API responses — SentinelX is a local tool with a controlled internal API; the existing `|| "no_data"` fallback pattern is sufficient
- TypeScript 6.0 upgrade — currently in beta (February 2026); defer until stable

### Architecture Approach

The TypeScript build pipeline slots into the existing Flask static file architecture as a parallel to the CSS pipeline. Source TypeScript files live in `app/static/src/ts/` (parallel to `app/static/src/input.css`). esbuild compiles them to `app/static/dist/main.js` (parallel to `app/static/dist/style.css`). Flask serves the compiled output with no configuration changes. The only template modification is changing the script tag from `filename='main.js'` to `filename='dist/main.js'`. Source maps (`main.js.map`) are generated locally during development via `make js-dev` or `make js-watch` and are excluded from git.

**Major components:**
1. **`app/static/src/ts/types/`** — Shared TypeScript interfaces (`EnrichmentResult`, `EnrichmentStatus`, `VerdictKey`, `IocType`) and typed constants (`VERDICT_SEVERITY`, `VERDICT_LABELS`, `IOC_PROVIDER_COUNTS`); must be created before any module is converted
2. **`app/static/src/ts/modules/`** — One module per `initX` function: `form.ts` (~120 lines), `enrichment.ts` (~350 lines, the largest), `filter.ts` (~130 lines), `clipboard.ts` (~70 lines), `export.ts` (~40 lines), `settings.ts` (~20 lines), `stagger.ts` (~10 lines)
3. **`app/static/src/ts/main.ts`** — Entry point that imports all module init functions and calls `init()` at DOMContentLoaded; esbuild bundles everything from this entry point into a single IIFE
4. **`tools/esbuild` + Makefile targets** — `js` (production, minified), `js-dev` (source map, no minify), `js-watch` (watch mode), `typecheck` (`tsc --noEmit`); `build` target depends on both `css` and `js`

### Critical Pitfalls

1. **CSP violation from bundler-injected dynamic code evaluation** — Webpack and Vite inject `eval`-based source maps and HMR boilerplate that violate `script-src 'self'` CSP, breaking the `test_csp_header_exact_match` security test. Use esbuild exclusively; its IIFE output has no dynamic code execution. Verify CSP compliance in Phase 1 before writing any TypeScript.

2. **Behavioral regression from mixing refactoring with type annotations** — The IIFE has patterns (`feedback._timer` as DOM element property, `Array.prototype.slice.call()`) that invite modernization. Any behavioral change during type migration can introduce bugs invisible in review. Strict rule: the migration PR contains zero behavioral changes. A refactor PR follows only after all E2E tests pass on the typed code.

3. **Timer type conflict (`NodeJS.Timeout` vs `number`)** — If `@types/node` is installed as any dev dependency, `setTimeout()` resolves to `NodeJS.Timeout` instead of `number`, causing type errors throughout enrichment polling and sort debounce code. Use `ReturnType<typeof setTimeout>` for all timer variable types.

4. **`getAttribute()` always returns `string | null` — TypeScript won't narrow on `hasAttribute()`** — Every `getAttribute("data-verdict")` call in enrichment rendering produces a type error. Define a `function attr(el: Element, name: string, fallback?: string): string` utility before converting DOM manipulation code.

5. **Over-typing with `any`** — The `renderEnrichmentResult` function, `iocVerdicts` accumulator map, and event listener targets are the highest-risk spots for `any` escape hatching. Define `EnrichmentResult` and `VerdictEntry` interfaces in `types/api.ts` before converting any enrichment logic. A single `any` in the API response type defeats type safety for the most critical data path.

## Implications for Roadmap

Based on the research dependency chain and the pitfall-to-phase mapping from PITFALLS.md, the migration has a clear 5-phase structure with strict ordering requirements. The ordering is not negotiable — later phases depend on earlier ones.

### Phase 1: Build Pipeline Infrastructure

**Rationale:** Every subsequent phase depends on a working build pipeline. CSP compliance and Makefile integration must be verified before any TypeScript is written. Pitfalls 1, 2, 7, 8, and 11 from PITFALLS.md all manifest at this stage and are cheapest to catch here.

**Delivers:** `tools/esbuild` binary installed; `tsconfig.json` at project root; Makefile `js`, `js-dev`, `js-watch`, `typecheck`, `esbuild-install` targets; `.gitignore` updated to exclude `main.js.map`; `base.html` script tag updated to `dist/main.js`; CSP audit test still passing; CI updated to run `make js` before pytest

**Addresses:** Build pipeline integration (P1 from FEATURES.md)

**Avoids:** CSP violation (Pitfall 1), module format mismatch (Pitfall 2), source map path issues (Pitfall 7), stale JS in CI (Pitfalls 8, 11)

**Research flag:** Standard patterns — well-documented in official esbuild docs, no additional research needed

### Phase 2: Type Definitions Foundation

**Rationale:** All modules depend on shared types. Creating `types/api.ts` and `types/ioc.ts` before converting any logic prevents the `any` escape-hatch trap and ensures the domain model is centralized. This is the highest-leverage investment in the migration.

**Delivers:** `app/static/src/ts/types/api.ts` with `EnrichmentResult`, `EnrichmentStatus` interfaces; `app/static/src/ts/types/ioc.ts` with `VerdictKey`, `IocType` union types, typed `VERDICT_SEVERITY`, `VERDICT_LABELS`, `IOC_PROVIDER_COUNTS` constants; `tsc --noEmit` passes on types alone

**Addresses:** Type definitions for API response shapes, `src/types.ts` with shared interfaces (P1 from FEATURES.md)

**Avoids:** Over-typing with `any` (Pitfall 9), under-typing with broad strings (Pitfall 10)

**Research flag:** Standard patterns — TypeScript interface definitions are well-documented

### Phase 3: Module Extraction (Simple Modules First)

**Rationale:** Extract simpler modules before `enrichment.ts` (the most complex at ~350 lines). Inside-out ordering — no-dependency modules first — minimizes broken intermediate states. Establish the null-check strategy and `getAttribute` helper pattern early, before tackling complex DOM manipulation in enrichment.

**Delivers:** TypeScript modules for clipboard, stagger, settings, form, export, filter (in dependency order); `attr()` helper utility defined; null-guard strategy established; timer types resolved with `ReturnType<typeof setTimeout>`; `tsc --noEmit` passes on all simple modules

**Addresses:** Feature-based module splitting, DOM type narrowing, behavioral parity (P1/P2 from FEATURES.md)

**Avoids:** Refactoring behavior during migration (Pitfall 3), querySelector null strategy inconsistency (Pitfall 4), timer type conflicts (Pitfall 5), getAttribute null return (Pitfall 6), import path extension mismatch (Pitfall 12)

**Research flag:** Standard patterns — module boundaries and expected line counts are documented in ARCHITECTURE.md

### Phase 4: Enrichment Module and Entry Point

**Rationale:** `modules/enrichment.ts` is the largest and most complex module (~350 lines), depending on both type files and verdict utilities. Converting it last means all supporting types and patterns are already established and verified. The entry point (`main.ts`) is created after all modules are working, as it imports from everything.

**Delivers:** `app/static/src/ts/modules/enrichment.ts` with fully typed polling loop, result rendering, verdict accumulation, and card sorting; `app/static/src/ts/main.ts` entry point importing all modules; old `app/static/main.js` deleted; `tailwind.config.js` content paths updated to include `.ts` files

**Addresses:** Behavioral parity (critical P1 from FEATURES.md), all 10 `initX` functions typed

**Avoids:** Behavioral regression (Pitfall 3), `any` types in enrichment (Pitfall 9)

**Research flag:** Standard patterns — architecture blueprint specifies exact module boundaries and dependency order

### Phase 5: Type Hardening and CI Verification

**Rationale:** After all modules compile and the E2E suite passes, a hardening pass catches any compromises made during conversion (stray `any`, broad string types, missing narrowness). The CI verification confirms the build pipeline is correctly integrated end-to-end. esbuild's success does not mean tsc passes — these are separate tools.

**Delivers:** Zero TypeScript errors on `tsc --noEmit`; zero `any` types outside explicitly justified exceptions; all 224+ E2E tests passing against compiled `dist/main.js`; CI pipeline verified with `make js` before pytest; "looks done but isn't" checklist from PITFALLS.md completed (CSP audit, source maps, timer types, API types, no innerHTML regressions)

**Addresses:** `make typecheck` CI target (P2 from FEATURES.md), behavioral parity verification

**Avoids:** All pitfalls — final verification sweep

**Research flag:** Standard patterns — verification and hardening; no new research needed

### Phase Ordering Rationale

- **Pipeline before code:** No TypeScript conversion is possible without a working build pipeline. Phase 1 is a hard prerequisite for everything.
- **Types before modules:** Modules import types. Creating `types/` first means every module has its dependencies available from the first line — without this order, `any` fills the gaps.
- **Simple before complex:** Enrichment is the riskiest module (most DOM manipulation, most state, most complex logic). Converting simpler modules first establishes the patterns (null guards, `getAttribute` helpers, timer types) that enrichment will use.
- **Entry point last:** `main.ts` imports from all modules; creating it before its dependencies guarantees import errors during conversion.
- **Hardening pass always:** esbuild never type-checks. A passing build does not mean passing types. A dedicated hardening phase prevents the "looks done but isn't" failure mode documented in PITFALLS.md.

### Research Flags

All phases have standard, well-documented patterns. No phases require `/gsd:research-phase`:

- **Phase 1:** esbuild binary installation and IIFE Makefile integration are fully documented in official esbuild docs with verified examples
- **Phase 2:** TypeScript interface definitions follow standard patterns; official docs cover all relevant tsconfig options
- **Phase 3:** Module extraction boundaries are documented in ARCHITECTURE.md with explicit module names, functions, and approximate line counts
- **Phase 4:** Enrichment module architecture documented in detail in ARCHITECTURE.md; entry point pattern is a single well-defined import-and-call structure
- **Phase 5:** Verification checklist is fully specified in PITFALLS.md's "Looks Done But Isn't" section

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | esbuild and TypeScript official docs verified via WebFetch; version numbers confirmed; standalone binary download mechanism confirmed identical to existing Tailwind pattern; no inferred recommendations |
| Features | HIGH | TypeScript official migration docs used as primary source; esbuild API reference verified; feature scope is narrow (parity-only migration) which reduces uncertainty; priority tiers are well-reasoned with source citations |
| Architecture | HIGH | esbuild official docs confirm all output format, platform, and sourcemap flags; Flask static serving behavior confirmed from existing project behavior; tsconfig options verified against TypeScript reference; module boundaries derived from direct analysis of the 856-line `main.js` |
| Pitfalls | HIGH | Sourced from esbuild official docs, TypeScript official docs, and direct SentinelX codebase audit (`main.js` pattern analysis, `test_security_audit.py` CSP assertions, `base.html` script tag); pitfalls are specific to this codebase, not generic |

**Overall confidence:** HIGH

### Gaps to Address

- **Minor esbuild `--target` flag discrepancy:** STACK.md recommends `es2022` while ARCHITECTURE.md uses `es2020` in some Makefile examples. Use `es2022` (STACK.md is authoritative on this); standardize in Phase 1 Makefile and document the decision.

- **`feedback._timer` dynamic property pattern:** The existing `showPasteFeedback()` sets `_timer` directly on a DOM element — a pattern TypeScript will reject. Research identifies refactoring to a module-level `let feedbackTimer` as the solution, but the behavioral equivalence must be explicitly verified. Include a dedicated E2E verification step in Phase 3 for this specific function.

- **TypeScript version drift (minor):** TypeScript 5.8.3 is cited as latest stable at research time. If 5.9.x releases before implementation, pin to `typescript@5.8` in the npm install to avoid unexpected behavior changes. Not blocking.

## Sources

### Primary (HIGH confidence)
- esbuild Getting Started (esbuild.github.io/getting-started/) — standalone binary download via curl, v0.27.3 current, no Node.js required
- esbuild API (esbuild.github.io/api/) — `--format=iife`, `--bundle`, `--outfile`, `--sourcemap`, `--platform=browser`, `--target=es2022` flags
- esbuild Content Types (esbuild.github.io/content-types/#typescript) — TypeScript loader behavior, `isolatedModules` requirement, no type checking by design
- TypeScript 5.8 release blog (devblogs.microsoft.com/typescript/announcing-typescript-5-8/) — version confirmation; 6.0 in beta
- TypeScript TSConfig Reference (typescriptlang.org/tsconfig/) — `lib`, `types`, `isolatedModules`, `moduleResolution: "Bundler"`, `strict`, `noEmit`
- TypeScript DOM Manipulation docs (typescriptlang.org/docs/handbook/dom-manipulation.html) — querySelector type hierarchy, null return pattern
- TypeScript Migrating from JavaScript (typescriptlang.org/docs/handbook/migrating-from-javascript.html) — migration strategy
- Total TypeScript tsconfig cheat sheet (totaltypescript.com/tsconfig-cheat-sheet) — bundler workflow configuration
- SentinelX `app/static/main.js` — source of truth for behavior to preserve and type surfaces to cover
- SentinelX `tests/test_security_audit.py` — CSP assertions confirmed (no unsafe-eval, no unsafe-inline)
- SentinelX `app/templates/base.html` — script tag structure confirmed (`defer`, no `type="module"`)

### Secondary (MEDIUM confidence)
- WebSearch: esbuild vs rollup vs webpack comparison 2025 — esbuild fastest, standalone, minimal config; multiple sources agree
- getAttribute not narrowed by hasAttribute — TypeScript issue #22238 documented limitation
- setTimeout return type conflict (guilhermesimoes.github.io) — `ReturnType<typeof setTimeout>` pattern verified against TypeScript issue tracker
- Heap Engineering: Migrating to TypeScript — avoid refactoring during migration
- Qualtrics Engineering: Migrating Legacy JS to TypeScript — preserve behavior guidance
- TypeScript anti-patterns (ducin.dev) — informs anti-features section; consistent with TypeScript team guidance

### Tertiary (LOW confidence)
- typed-query-selector npm — optional querySelector improvement; not recommended for this project scope
- TypeScript strict mode non-monotonicity blog (huonw.github.io) — interaction between `strictNullChecks` and `noImplicitAny`; enable both together via `"strict": true`

---
*Research completed: 2026-02-28*
*Ready for roadmap: yes*
