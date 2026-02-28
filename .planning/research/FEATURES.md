# Feature Research — TypeScript Migration (v3.0)

**Domain:** TypeScript migration of 856-line vanilla JS IIFE in an existing Python/Flask application
**Researched:** 2026-02-28
**Confidence:** HIGH (TypeScript official docs, esbuild official docs, verified patterns), MEDIUM (module splitting strategy — evidence-based but adapted to this specific file structure), LOW (where noted)

> **Scope note:** This document supersedes the v1.2 UI redesign FEATURES.md (which covered UI patterns for
> SentinelX v1.2). The v1.2 document is preserved below this file's scope. This document covers **TypeScript
> migration features only** — what capabilities a correct TS migration of `app/static/main.js` delivers,
> categorized by necessity. Zero new functional behavior is in scope; behavioral parity with the existing IIFE
> is the goal.

---

## Context: What We Are Migrating

The subject is `app/static/main.js` — an 856-line IIFE (`(function() { "use strict"; ... }())`) containing:

- **10 init functions** called from a single `init()` entry point at DOMContentLoaded
- **No module system** — all functions are local to the IIFE, no imports/exports
- **Browser-only** — uses `document`, `window`, `navigator.clipboard`, `fetch`, `CSS.escape`
- **3 mutable module-level variables** — `VERDICT_SEVERITY`, `VERDICT_LABELS`, `IOC_PROVIDER_COUNTS` (constants), plus `sortTimer` and `rendered`/`iocVerdicts`/`iocResultCounts` (polling state)
- **One external API shape** — the `/enrichment/status/{job_id}` JSON response (the only data contract the JS depends on)

The existing IIFE already has `"use strict"` and clean separation by named function. This is an ideal candidate for direct TypeScript migration: no prototype chain abuse, no closure-heavy state, no dynamic `eval`.

---

## Feature Landscape

### Table Stakes (What a TS Migration Must Deliver)

Features that any correct TypeScript migration is expected to provide. Missing these means the migration is incomplete or provides no value over the original JS.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Strict mode enabled (`"strict": true`)** | The entire point of TS migration is catching the class of bugs that loose JS silently allows. `"strict": true` enables `noImplicitAny`, `strictNullChecks`, `strictFunctionTypes`, `strictBindCallApply`, `strictPropertyInitialization`, `alwaysStrict` in one flag. Without it, TS adds syntax noise with no safety gain. | LOW | Set in `tsconfig.json`. One flag, no code changes needed initially — the migration process will surface violations to fix. |
| **DOM type narrowing for all `querySelector` calls** | The existing code does `document.getElementById("analyze-form")` — in TS strict mode, this returns `HTMLElement \| null`. Every subsequent property access (`.disabled`, `.value`, `.textContent`) is a type error without a null guard. The current code already has null guards (`if (!form) return;`), but they are untyped. | MEDIUM | Pattern: `const el = document.getElementById("submit-btn") as HTMLButtonElement \| null; if (!el) return;`. Use `as HTMLButtonElement` (not `as any`) after a null check — keeps type safety, narrows to the correct interface. Affects all 10 `initX` functions. |
| **Type definitions for API response shape** | `renderEnrichmentResult(result, ...)` uses `result.ioc_value`, `result.provider`, `result.verdict`, `result.type`, `result.detection_count`, `result.total_engines`, `result.scan_date`, `result.error` — all accessed without type safety. A TS interface for the enrichment result shape catches typos in field names and documents the contract. | LOW | Define `interface EnrichmentResult` and `interface EnrichmentStatus` matching the Flask `/enrichment/status/{job_id}` JSON response. No runtime validation needed (internal tool, controlled API). |
| **Timer variable types resolved** | The code uses `var sortTimer = null` and `clearTimeout(sortTimer)` — in TS with DOM lib, `clearTimeout` expects `number \| undefined`. Also `setTimeout` returns `number` in browser but `NodeJS.Timeout` if `@types/node` leaks in. | LOW | Use `ReturnType<typeof setTimeout>` for timer variables, or configure `tsconfig.json` with `"lib": ["DOM", "ES2020"]` and `"types": []` to exclude Node types entirely. The `"types": []` approach is cleanest for a browser-only file. |
| **Source maps generated** | If TS is compiled to JS and the original TS source is not shipped, browser DevTools show compiled output. Analysts debugging issues see line numbers in minified JS, not in the original TypeScript. Source maps link the compiled JS back to TS source. | LOW | `esbuild --sourcemap` or `tsc` with `"sourceMap": true`. Choose `--sourcemap=linked` (external `.js.map` file, referenced by a comment in the `.js`) to avoid inlining the map in the production file. |
| **Build pipeline integration into Makefile** | The project uses `make css` and `make css-watch` for the Tailwind build. The TS build needs equivalent `make js` and `make js-watch` targets. Without Makefile integration, developers must remember a separate command. | LOW | Add `js` and `js-watch` targets to the existing `Makefile`. Pattern: `esbuild src/main.ts --bundle --format=iife --outfile=app/static/main.js --sourcemap`. |
| **Behavioral parity: all existing behavior preserved** | The migration is not a refactor. Every function must behave identically after migration: `initSubmitButton`, `initAutoGrow`, `initModeToggle`, `initCopyButtons`, `initEnrichmentPolling`, `initExportButton`, `initFilterBar`, `initSettingsPage`, `initScrollAwareFilterBar`, `initCardStagger`. | MEDIUM | Run the existing Playwright E2E test suite after migration to verify. No new features, no deleted features, no changed timing. |
| **XSS safety maintained (SEC-08)** | The existing code explicitly avoids `.innerHTML` for untrusted data (uses `.textContent` and `.setAttribute` only). TypeScript does not prevent XSS — it is a developer discipline enforced by code review. The type definitions for API responses must not introduce patterns that tempt future developers to use `.innerHTML`. | LOW | Use `textContent` in all type-annotated rendering functions. Consider naming the `error` field in `EnrichmentResult` carefully (e.g., `errorMessage`) to clarify it is a string, not HTML. |

### Differentiators (Nice-to-Have, but Valuable)

Features that go beyond minimum migration correctness and provide lasting benefit to the codebase.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Feature-based module splitting (10 init functions → 10 modules)** | Breaking the monolithic 856-line IIFE into one module per feature (e.g., `src/submit-button.ts`, `src/enrichment-polling.ts`, `src/filter-bar.ts`) makes future changes surgical. Editing `filter-bar.ts` doesn't risk accidentally breaking `initEnrichmentPolling`. Module boundaries also make unit testing individual features practical for the first time. | MEDIUM | Natural split: 1 module per `initX` function plus `src/types.ts` for shared interfaces and `src/constants.ts` for `VERDICT_SEVERITY`, `VERDICT_LABELS`, `IOC_PROVIDER_COUNTS`. esbuild bundles everything into a single `main.js` at build time — no runtime module loading overhead. |
| **`src/types.ts` with all shared interfaces** | A single file exporting `EnrichmentResult`, `EnrichmentStatus`, `VerdictKey`, `FilterState`, `IocType`, and `ProviderVerdictEntry` creates a living documentation of the data contracts. When the Flask API response changes, the type error is surfaced immediately. | LOW | Depends on: DOM type narrowing (table stakes). The types file is the foundation the other modules import from. Define `type VerdictKey = "malicious" \| "suspicious" \| "clean" \| "no_data" \| "error"` as a union type — more valuable than `string` everywhere. |
| **`src/constants.ts` with typed constant objects** | `VERDICT_SEVERITY`, `VERDICT_LABELS`, and `IOC_PROVIDER_COUNTS` are currently plain objects with no type safety. Typing `VERDICT_LABELS` as `Record<VerdictKey, string>` ensures a new verdict key cannot be added to the API without updating the label table — caught at compile time, not runtime. | LOW | Depends on: `VerdictKey` union type in `src/types.ts`. |
| **Type-safe `querySelector` helper** | Instead of `document.getElementById("foo") as HTMLButtonElement \| null` scattered throughout 10 modules, a typed helper `function getEl<T extends HTMLElement>(id: string): T \| null` reduces duplication and keeps the cast logic in one place. | LOW | Optional but reduces repetition. Alternative: inline casts are fine if the codebase stays small. |
| **`tsconfig.json` with `"lib": ["DOM", "ES2020"]` and `"types": []`** | Explicitly specifying `lib` ensures only browser APIs are available (no accidental Node.js global leakage). `"types": []` prevents `@types/node` from polluting the browser type space, which eliminates the `setTimeout` → `NodeJS.Timeout` confusion that occurs when any dev dependency brings in Node types. | LOW | Small configuration decision with a disproportionate benefit: timer types resolve to `number` (browser) not `NodeJS.Timeout` (Node), which is correct for this codebase. |
| **esbuild over tsc for the build step** | esbuild compiles TypeScript 10-100x faster than `tsc` and requires zero configuration beyond CLI flags. For a single-file output, the build is essentially instantaneous. `tsc --noEmit` can then be used for type-checking without emitting (CI gate), while esbuild handles the actual build. This is the 2025 standard for browser-only TS projects. | LOW | Depends on: esbuild installation (single binary, no npm needed if using the standalone version). esbuild does NOT do type checking — a `make typecheck` target runs `tsc --noEmit` for CI. |
| **Barrel export (`src/index.ts`) omitted intentionally** | A barrel export (`export * from './submit-button'`) is the standard pattern for npm packages. For an application bundled by esbuild with a single entry point (`src/main.ts`), barrel exports add indirection with no benefit. The entry point (`src/main.ts`) imports directly from each module and calls `init()`. Omitting barrels keeps the module graph simple. | LOW | Anti-pattern for this specific project type. See Anti-Features below for the full rationale. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem like natural extensions of a TypeScript migration but introduce complexity, risk, or maintenance burden without proportional value in this specific project.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Zod or io-ts runtime validation of API responses** | "TypeScript interfaces don't prevent bad data at runtime" is true. Runtime validation libraries like Zod parse API responses and throw on shape mismatch. | SentinelX is a local tool with a single controlled Python backend. The API is not public; no external party produces its JSON. Adding 14KB of Zod to validate an internal API introduces a dependency, adds parse overhead on every poll tick (every 750ms), and creates failure modes (poll silently stops if Zod throws) not present in the current code. The existing null-check pattern (`result.verdict || "no_data"`) already handles missing fields gracefully. | Define TypeScript interfaces for documentation and compile-time safety. Use the existing defensive `|| "no_data"` fallbacks for runtime robustness. |
| **Declaration files (`.d.ts`) hand-authored for internal modules** | Declaration files are the standard TypeScript pattern for publishing typed packages. They document module shapes without shipping source. | This is an application, not a library. TypeScript compiles from `.ts` source directly — no hand-authored `.d.ts` needed. If `"declaration": true` is set in tsconfig, the compiler generates them automatically. But for an esbuild-bundled single-file browser app, generated `.d.ts` files are unused and clutter the build output. | Set `"declaration": false` in tsconfig. Types live in `.ts` source files. No `.d.ts` files needed. |
| **Deeply typed CSS class manipulation** | Typed CSS class manipulation libraries (e.g., `clsx`, `classnames`) or custom types for BEM class names (`type BemBlock = "ioc-card" | "verdict-badge" | ...`) add type coverage to the CSS layer. | The existing code does `card.classList.add("filter-btn--active")` — a string. Typing CSS class names requires enumerating every class in the codebase as a union type, which becomes stale as CSS evolves. The maintenance burden exceeds the bug-prevention value. CSS class typos are found immediately by visual inspection, not weeks later in production. | Keep CSS class strings untyped. Type the data attributes (`data-verdict`, `data-ioc-type`) which carry domain logic, not presentation. |
| **Namespaces instead of ES modules** | TypeScript namespaces (`namespace SentinelX { export function init() { ... } }`) were the pre-module TypeScript pattern. tsc compiles them to IIFEs, avoiding any module bundler requirement. | TypeScript's own codebase migrated away from namespaces to ES modules in 2024. Namespaces are a legacy pattern; ES modules with esbuild bundling is the current standard. Namespaces also do not provide the test isolation benefits that true ES modules offer. | Use ES modules (`export function`, `import { } from`). Let esbuild bundle them to an IIFE for browser delivery. |
| **Separate `tsconfig.build.json` and `tsconfig.dev.json`** | Multi-tsconfig setups allow different strictness levels for development vs. production builds, or separate configs for tests. | This project has 856 lines of JS to migrate. A multi-config setup adds tooling complexity for a codebase where a single strict config is appropriate from day one. If the test framework (pytest + Playwright) needs Node types, those are Python-side tests, not TypeScript tests — so the browser tsconfig never needs Node types. | Single `tsconfig.json` with `"strict": true` and `"lib": ["DOM", "ES2020"]`. |
| **Gradual migration with `allowJs: true`** | "Don't convert everything at once" is the official TypeScript migration guidance for large codebases. `allowJs: true` lets the project have mixed `.js` and `.ts` files during migration. | At 856 lines in a single file, this is not a large codebase. A gradual migration adds intermediate states that must be maintained: the file is valid JS but not yet typed, developers must track which parts are migrated, and the build output is uncertain during transition. A single-file project is better migrated in one pass with a clear before/after. | Migrate `main.js` to `main.ts` in a single commit. If the scope feels large, split it into the module files first (as JS), then type each module. But do not maintain a mixed JS/TS state. |
| **CSS Modules or Tailwind class-name type generation** | Fully typed Tailwind (using `tailwind-ts` or code-generated class name types) ensures that Tailwind classes used in JS are valid. | SentinelX does not generate Tailwind class names in JavaScript — it uses static CSS class names from the Jinja2 templates. The JS manipulates data attributes (`data-verdict`, `data-mode`) and a handful of BEM classes. Tailwind type generation is for frameworks (React, Vue) where classes are composed in JS; not for server-rendered templates. | No action needed. The Tailwind build already catches unknown classes by generating CSS only for classes found in templates and JS files. |
| **`as const` assertions on all object literals** | Using `as const` on `VERDICT_SEVERITY`, `VERDICT_LABELS`, `IOC_PROVIDER_COUNTS` creates readonly literal types (`"malicious"` instead of `string`). This is maximally strict. | `as const` on `VERDICT_LABELS` creates the type `{ readonly malicious: "MALICIOUS"; readonly suspicious: "SUSPICIOUS"; ... }`. While technically more precise, it makes the object harder to use as an index target (`VERDICT_LABELS[someStringVar]` fails without a cast). For this use case, `Record<VerdictKey, string>` is more ergonomic and equally safe. | Type the constants as `Record<VerdictKey, string>` or `Record<VerdictKey, number>` respectively, with `VerdictKey` as the union type. Use `as const` only if a downstream function needs to infer literal types from the constant, which is not the case here. |
| **Jest or Vitest for unit tests of the TS modules** | TypeScript enables unit testing individual modules in isolation. Adding Jest or Vitest would allow testing `computeWorstVerdict`, `verdictSeverity`, and `updateDashboardCounts` without a browser. | The existing test suite is pytest (Python) + Playwright (E2E). Adding a JavaScript test framework introduces a second test runtime, second coverage tool, second CI job, and a `package.json` dependency that doesn't currently exist. The E2E tests already cover the observable behavior. For pure logic functions (`computeWorstVerdict`), the Python test suite's integration coverage is sufficient. | Extract pure logic functions (`computeWorstVerdict`, `verdictSeverity`, `formatDate`) to `src/verdict-utils.ts`. Their correctness is verified by the existing E2E tests. If unit tests are desired later, Vitest can be added independently — do not block the TS migration on it. |

---

## Feature Dependencies

```
[src/types.ts — EnrichmentResult, VerdictKey, FilterState]
    └──required by──> src/enrichment-polling.ts
    └──required by──> src/filter-bar.ts
    └──required by──> src/verdict-utils.ts

[src/constants.ts — VERDICT_SEVERITY, VERDICT_LABELS, IOC_PROVIDER_COUNTS]
    └──required by──> src/verdict-utils.ts
    └──required by──> src/enrichment-polling.ts

[src/verdict-utils.ts — verdictSeverity(), computeWorstVerdict()]
    └──required by──> src/enrichment-polling.ts (calls both)
    └──required by──> src/card-management.ts (calls verdictSeverity for sort)

[esbuild build pipeline]
    └──required by──> All TS modules (bundles to single main.js)
    └──enables──> source maps

[Strict mode + DOM types]
    └──required by──> All modules (type errors surface only with strict: true)

[src/main.ts entry point]
    └──imports all init functions──> All feature modules
    └──calls init() at DOMContentLoaded
```

### Dependency Notes

- **Types before modules:** `src/types.ts` must be created before any other module, because `EnrichmentResult` is the shared interface used by both the polling loop and the rendering code. If types come later, the intermediate state has `any` everywhere.
- **Constants before utils:** `VERDICT_SEVERITY` is consumed by `verdictSeverity()`. If `constants.ts` is typed as `Record<VerdictKey, number>`, the function signature can be narrowed to accept `VerdictKey` instead of `string`.
- **Build pipeline before migration:** Confirm esbuild compiles the TS file successfully before trying to add types. Establish the pipeline with a trivial `console.log("hello from TS")` first, then migrate the logic.
- **No conflicts:** All modules communicate through the DOM (data attributes on elements), not through shared in-memory state. This means modules are genuinely independent at runtime even if they share type definitions.

---

## MVP Definition

### Migration Launch With (v3.0 Phase 1)

The minimum needed to ship a correct TypeScript migration with real type safety and a working build pipeline.

- [ ] `tsconfig.json` with `"strict": true`, `"lib": ["DOM", "ES2020"]`, `"types": []`, `"noEmit": true` — type checking config only
- [ ] `src/types.ts` with `EnrichmentResult`, `EnrichmentStatus`, `VerdictKey`, `IocType`, `FilterState`, `ProviderVerdictEntry` interfaces
- [ ] `src/constants.ts` with typed `VERDICT_SEVERITY`, `VERDICT_LABELS`, `IOC_PROVIDER_COUNTS`
- [ ] esbuild build pipeline: `Makefile` targets `js` and `js-watch`, outputting `app/static/main.js` with source maps
- [ ] `src/main.ts` entry point — imports all init functions, calls `init()` at DOMContentLoaded
- [ ] All existing IIFE code migrated to typed ES modules with strict null checks resolved
- [ ] All 10 `initX` functions typed with DOM element narrowing (`HTMLButtonElement | null`, etc.)
- [ ] Behavioral parity verified: existing Playwright E2E suite passes

### Add After Base Migration (v3.0 Phase 2)

Once the migration is working and the build pipeline is established:

- [ ] Feature-based module splitting: one `.ts` file per `initX` function (10 modules + types + constants + main)
- [ ] `src/verdict-utils.ts` for pure logic functions isolated for clarity
- [ ] `make typecheck` CI target (`tsc --noEmit`)

### Future Consideration (v4.0+)

- [ ] Vitest unit tests for pure logic functions in `src/verdict-utils.ts` — defer until a test author wants them; do not add a JS test runtime during the migration itself
- [ ] Zod validation if the enrichment API becomes a public endpoint — not applicable for local tool
- [ ] Upgrade to TypeScript 6.0 when released (strict mode will become the default per the TypeScript team's current trajectory)

---

## Feature Prioritization Matrix

| Feature | Developer Value | Implementation Cost | Priority |
|---------|-----------------|---------------------|----------|
| `tsconfig.json` with strict mode | HIGH — catches null dereferences, typos in field names | LOW — one file, standard config | P1 |
| `src/types.ts` — API response interfaces | HIGH — documents data contract, catches field renames | LOW — ~50 lines of interface definitions | P1 |
| `src/constants.ts` — typed constants | MEDIUM — prevents untyped verdict strings | LOW — 3 const declarations with types | P1 |
| esbuild build pipeline (Makefile targets) | HIGH — useless without a way to build | LOW — 2 Makefile targets, esbuild CLI | P1 |
| DOM type narrowing in all initX functions | HIGH — the core safety benefit of TS | MEDIUM — 10 functions, ~30 null checks to type | P1 |
| Source maps | MEDIUM — debugging compiled output | LOW — one esbuild flag | P1 |
| Behavioral parity (E2E tests pass) | CRITICAL — migration must not break anything | MEDIUM — test-driven verification | P1 |
| Feature-based module splitting | MEDIUM — maintainability, testability | MEDIUM — 10 files instead of 1 | P2 |
| `src/verdict-utils.ts` isolation | LOW — nice for readability | LOW — move 4 functions | P2 |
| `make typecheck` CI target | MEDIUM — catches regressions in CI | LOW — one Makefile target | P2 |
| Vitest unit tests | LOW — E2E already covers behavior | HIGH — new runtime, new config | P3 |
| Zod runtime validation | LOW — internal API, no adversarial input | HIGH — 14KB dependency, poll-loop failure mode | P3 |

**Priority key:**
- P1: Required for the migration to be complete and correct
- P2: Improves the migration outcome but can follow in the same milestone
- P3: Deferred — not a TypeScript migration concern

---

## How Typing Should Go: Depth Guidance

This is the most important judgment call in a TS migration. The principle: **type the domain, not the DOM API.**

### Type deeply (HIGH value):

- **API response shapes** — `EnrichmentResult`, `EnrichmentStatus` — these are the data contracts. A field name change in the Flask route that doesn't match the TypeScript interface is caught at compile time.
- **Verdict values** — `type VerdictKey = "malicious" | "suspicious" | "clean" | "no_data" | "error"` — used in 6+ places. A union type catches unhandled verdict states.
- **IOC types** — `type IocType = "ipv4" | "ipv6" | "domain" | "url" | "md5" | "sha1" | "sha256"` — used as keys in `IOC_PROVIDER_COUNTS`. A union type makes the provider count lookup type-safe.
- **Function signatures** — all `initX()` functions should be `(): void`. Polling state objects (`iocVerdicts`, `iocResultCounts`) should be `Record<string, ...>` with typed value shapes.

### Type minimally (LOW value — use `HTMLElement` casts only):

- **Specific DOM element subtypes** — `as HTMLButtonElement`, `as HTMLTextAreaElement`, `as HTMLInputElement` are appropriate where element-specific properties (`.disabled`, `.value`, `.type`) are accessed. Use the most specific type that fits.
- **`NodeListOf<Element>` from querySelectorAll** — TypeScript returns `NodeListOf<Element>` for attribute selectors. Cast to `NodeListOf<HTMLElement>` when using `.style` or `.classList` — or use `Array.from()` with a type guard filter.

### Do not type (ANTI-PATTERN — no value):

- **CSS class name strings** — `card.classList.add("filter-btn--active")` — the string is correct by inspection
- **Data attribute names** — `card.getAttribute("data-verdict")` — the attribute name is correct by inspection
- **Timer return values beyond `ReturnType<typeof setTimeout>`** — No need for a custom `TimerId` type alias

---

## Sources

- [TypeScript: Migrating from JavaScript](https://www.typescriptlang.org/docs/handbook/migrating-from-javascript.html) — HIGH confidence (official TypeScript docs)
- [TypeScript: DOM Manipulation](https://www.typescriptlang.org/docs/handbook/dom-manipulation.html) — HIGH confidence (official TypeScript docs, querySelector type hierarchy)
- [TypeScript: TSConfig strictNullChecks](https://www.typescriptlang.org/tsconfig/strictNullChecks.html) — HIGH confidence (official TypeScript tsconfig reference)
- [TypeScript: Modules](https://www.typescriptlang.org/docs/handbook/2/modules.html) — HIGH confidence (official TypeScript docs, ES module patterns)
- [esbuild API reference](https://esbuild.github.io/api/) — HIGH confidence (official esbuild docs, IIFE format, source maps, tsconfig options)
- [Timers in TypeScript and Node.js](https://evanshortiss.com/timers-in-typescript) — MEDIUM confidence (single authoritative post, verified against TypeScript issue tracker)
- [Making setTimeout return number](https://guilhermesimoes.github.io/blog/making-settimeout-return-number-in-typescript) — MEDIUM confidence (community post, consistent with official tsconfig `types: []` docs)
- [TypeScript anti-patterns — Tomasz Ducin](https://ducin.dev/typescript-anti-patterns) — MEDIUM confidence (expert practitioner, consistent with TypeScript team guidance)
- [typed-query-selector npm](https://github.com/g-plane/typed-query-selector) — LOW confidence (library exists, mentioned as optional improvement only; not recommended for this project)
- [TypeScript strict mode non-monotonicity](https://huonw.github.io/blog/2025/12/typescript-monotonic/) — MEDIUM confidence (documented interaction between `strictNullChecks` and `noImplicitAny`; recommendation: enable both together via `"strict": true`)
- [TypeScript over-engineering trap — LogRocket](https://blog.logrocket.com/discussing-the-over-engineering-trap-in-typescript/) — MEDIUM confidence (informs anti-features section; consistent with TypeScript team's "type with intent" guidance)
- [TypeScript's Migration to Modules — TypeScript blog](https://devblogs.microsoft.com/typescript/typescripts-migration-to-modules/) — HIGH confidence (official TypeScript team post on namespace → ES module migration; confirms namespaces are deprecated pattern)
- Existing `app/static/main.js` — HIGH confidence (source of truth for behavior to preserve and type surfaces to cover)

---

*Feature research for: SentinelX v3.0 TypeScript Migration*
*Researched: 2026-02-28*
*Confidence: HIGH (core TypeScript and esbuild patterns), MEDIUM (module splitting strategy, depth-of-typing guidance)*
