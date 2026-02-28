# Pitfalls Research

**Domain:** TypeScript migration of vanilla JS IIFE in a Python/Flask application with strict CSP
**Researched:** 2026-02-28
**Confidence:** HIGH — sourced from esbuild official docs, TypeScript official docs, verified community findings, and direct codebase audit of SentinelX `main.js`

---

## Context: What This Migration Is

The existing `app/static/main.js` is an 856-line IIFE with `"use strict"` that runs in the browser
as a `<script defer>` tag served from Flask's static file endpoint. The CSP is `script-src 'self'`
(no inline scripts, no dynamic code execution, no unsafe-inline). There are Playwright E2E tests
that test DOM behavior driven by this JS. The project has no Node.js build pipeline beyond Tailwind
standalone CLI.

**What v3.0 adds:** TypeScript build pipeline (esbuild or tsc), convert `main.js` IIFE to typed
ES modules, type definitions for DOM interactions and API shapes, source maps. Zero functional changes.

The pitfalls below are calibrated for this exact context — not a generic TS migration.

---

## Critical Pitfalls

### Pitfall 1: CSP Violation from Bundler-Injected Dynamic Code Evaluation

**What goes wrong:**
Webpack and some bundler configurations inject dynamic code evaluation into development bundles
for fast source maps (the `devtool: 'eval'` mode or HMR). This causes the browser to refuse
script execution under `script-src 'self'` CSP. The CSP regression test in
`test_security_audit.py` explicitly asserts `"unsafe-eval" not in csp` — so any bundler-generated
dynamic evaluation breaks both production safety and the regression guard.

The problem also arises through polyfills: Node.js compatibility shims injected by bundlers
(e.g., `regenerator-runtime` for async/generator support) use dynamic code evaluation internally.
`--platform=browser` in esbuild suppresses these polyfills; other bundlers may inject them.

**Why it happens:**
Developers reach for Webpack or Vite without reading CSP implications. Webpack's default
development mode uses eval-based source maps. The mistake is treating source map configuration
as a performance concern, not a security concern.

**Specific risk in SentinelX:**
- `test_csp_header_exact_match` asserts `"unsafe-eval" not in csp` — any dynamic evaluation in bundle breaks this
- The CSP header is set via `after_request` in Flask — the server will NOT change; the bundle must comply
- esbuild with `--format=iife` and `--platform=browser` does NOT inject dynamic code evaluation — it is CSP-safe
- Webpack devtool defaults, Vite dev server HMR, and async/await polyfills can all introduce dynamic evaluation

**How to avoid:**
Use esbuild as the bundler. esbuild IIFE output does not use dynamic code evaluation and
does not inject HMR boilerplate. Its source maps are external files (`--sourcemap=linked`) —
not inline hacks. Explicitly avoid Webpack and Vite for this project.

For source maps, use `--sourcemap=linked` (esbuild default for external maps): generates a
`main.js.map` file and appends `//# sourceMappingURL=main.js.map` to the bundle. Flask serves the
`.map` file statically from `app/static/` — no CSP implications because source maps are not executed.

**Warning signs:**
- Browser console reports CSP violation on page load after introducing the build pipeline
- `test_csp_header_exact_match` fails after introducing the build pipeline
- Any Node.js polyfill appears in bundle output (esbuild with `--platform=browser` suppresses these)
- Scanning the bundle output reveals dynamic code execution patterns (inspect with: `grep -n "unsafe" app/static/main.js`)

**Phase to address:**
Phase 1 (Build Pipeline Setup) — verify CSP compliance before any TypeScript code is converted.
After each build, load the page in browser and check the CSP test passes before proceeding.

---

### Pitfall 2: Module Format Mismatch — ESM Modules Without `type="module"` Script Tag

**What goes wrong:**
TypeScript source files use `import`/`export` syntax (ESM). If esbuild is configured with
`--format=esm` but the HTML still loads the output as `<script src="main.js" defer>` (without
`type="module"`), the browser throws a parse error: `import` declarations are only valid in modules.
The page loads but all JavaScript silently fails.

The inverse also breaks: if `--format=iife` is used (correct for this project) but the TypeScript
source uses top-level `await` or relies on ESM module scoping, esbuild wraps correctly but the
semantics change.

**Why it happens:**
Developers configure TypeScript with `"module": "ESNext"` in tsconfig (for IDE features) but
use esbuild `--format=iife` to produce the actual bundle. This combination works correctly.
The mistake is accidentally switching esbuild to `--format=esm` without updating the HTML template.

**Specific risk in SentinelX:**
`base.html` currently has: `<script src="{{ url_for('static', filename='main.js') }}" defer>`
— no `type="module"`. If the output format changes to ESM, the script tag MUST add `type="module"`.
If `type="module"` is added when using IIFE output, it has no effect but can confuse future readers.

**How to avoid:**
Decide on one output format and fix it:
- **Recommended: IIFE format** — `esbuild --format=iife --platform=browser`. Keep the existing
  script tag unchanged. IIFE wraps all code in a function expression, preventing global scope
  pollution identically to the existing `(function() { ... })()` pattern.
- If ESM is chosen: update `base.html` to `<script type="module" src="..." defer>` and add
  `type="module"` as a documented requirement in the Makefile comment.

Lock the format choice in the Makefile. Do not leave it configurable.

**Warning signs:**
- Browser console: `Uncaught SyntaxError: Cannot use import statement outside a module`
- Page loads but all JS behavior is absent (submit button stays disabled, mode toggle does nothing)
- `type="module"` and IIFE format used simultaneously (mismatch — IIFE does not need it)

**Phase to address:**
Phase 1 (Build Pipeline Setup) — fix format and script tag before writing any TypeScript.

---

### Pitfall 3: Refactoring Behavior While Migrating Types

**What goes wrong:**
The migration adds TypeScript types. During the process, a developer also improves variable
naming, extracts helpers, changes event-listener attachment order, or restructures module
boundaries. The resulting PR mixes type changes with behavioral changes — and a regression is
introduced that is invisible in code review because reviewers focus on type correctness, not
behavioral correctness.

This is the most common cause of Playwright test failures in TS migrations. The tests test
behavior; type changes alone cannot break behavior; therefore any test failure means behavior
changed.

**Why it happens:**
The existing code is 856 lines of old-style JS with `var`, function declarations inside IIFE,
and loop patterns that invite modernization with `Array.from`, `for...of`, arrow functions, and
`const`/`let`. The temptation to modernize is strong. "It's the same logic, just cleaner" is the
lie developers tell themselves as they introduce a subtle closure scope difference.

**Specific risk in SentinelX:**
- `showPasteFeedback()` uses `feedback._timer` — a property set dynamically on a DOM element. This
  is a JavaScript anti-pattern but it works. TypeScript will object to it. The "fix" of using a
  module-level `let pasteFeedbackTimer: number | null = null` is functionally equivalent — but
  moving the state introduces a risk if multiple feedback elements existed (they do not, but the
  behavioral equivalence must be verified deliberately).
- `iocVerdicts` and `iocResultCounts` are closure variables inside `initEnrichmentPolling()`.
  Extracting them to module scope changes their lifetime in ways that could break re-initialization.
- The `Array.prototype.slice.call(grid.querySelectorAll(".ioc-card"))` in `doSortCards()` is a
  legacy `NodeList` pattern. Converting to `Array.from(...)` is equivalent — but verify before doing it.

**How to avoid:**
Strict rule: the TypeScript migration PR contains ZERO behavioral changes. Separate into two phases:
1. **Phase A — Type annotations only.** Rename `.js` to `.ts`, add type annotations, fix type
   errors. Do not change any runtime behavior. Do not rename variables. Do not extract functions.
   Do not change loop style. The only allowed `var` to `let`/`const` changes are where TypeScript
   requires them for correctness.
2. **Phase B — Refactor.** After E2E tests pass on the typed code, create a separate PR to modernize
   the code style.

Run Playwright tests after Phase A before touching anything else.

**Warning signs:**
- E2E tests fail after TS migration for reasons unrelated to types
- The PR diff contains renamed variables, extracted helpers, or restructured modules
- `Array.from`, `for...of`, or arrow functions appear where the original used `for` loops or `forEach`

**Phase to address:**
All migration phases — enforce as a code review rule. If `pytest tests/e2e/` passes after the TS
migration, no behavior changed.

---

### Pitfall 4: querySelector Returns `null` — Boilerplate Strategy Must Be Consistent

**What goes wrong:**
`document.getElementById()` and `document.querySelector()` return `HTMLElement | null` in TypeScript's
DOM typings. With `strict: true` in tsconfig, every DOM query requires a null check or a non-null
assertion (`!`). The temptation is to add `!` everywhere:

```typescript
// Dangerous pattern — silences TypeScript without adding safety:
const form = document.getElementById("analyze-form")!;
```

The problem is that non-null assertion defeats the purpose of strict null checking — it silences
TypeScript without adding safety. Worse, if a future template change removes the element, the
runtime error is a cryptic `Cannot read properties of null` rather than a type error caught at compile time.

The opposite mistake (checking null everywhere with redundant guards) leads to deeply nested
code that is harder to read than the original JavaScript.

**Why it happens:**
TypeScript requires explicit null handling but does not enforce a consistent strategy. Developers
pick the path of least resistance: `!` everywhere, or `if (!el) return` boilerplate that
fragments initialization functions.

**Specific risk in SentinelX:**
`main.js` already uses defensive null checks at the start of each `init*` function:

```javascript
function initSubmitButton() {
    var form = document.getElementById("analyze-form");
    if (!form) return;
    var textarea = document.getElementById("ioc-text");
    var submitBtn = document.getElementById("submit-btn");
    if (!textarea || !submitBtn) return;
    // ... rest of function
}
```

This pattern IS the correct TypeScript pattern — it narrows the type to `HTMLElement` after the
check. The migration should preserve these checks exactly. Do NOT replace them with `!` assertions.

**How to avoid:**
- Preserve the existing `if (!el) return;` guards — they serve as TypeScript type narrowing
- Use `as HTMLInputElement` (type assertion with specific interface) when a more specific DOM
  interface is needed (e.g., `textarea.value` requires `HTMLTextAreaElement`)
- Never use `!` on DOM queries unless you can prove the element is server-rendered on every page
  that runs that JS
- For elements that genuinely cannot be absent (e.g., `document.body`), use `!` only with a comment

**Warning signs:**
- `!` appears on every `getElementById` or `querySelector` call without accompanying comment
- TypeScript errors suppressed with `// @ts-ignore` instead of proper type narrowing
- Type assertion chain: `(document.getElementById("x") as any).value` — two red flags in one line

**Phase to address:**
Phase 2 (TypeScript Conversion) — establish null-check strategy before writing any types.
Document in the PR: "null strategy is preserve existing guards."

---

### Pitfall 5: Timer Types Conflict — `NodeJS.Timeout` vs `number` in Browser Context

**What goes wrong:**
`setTimeout()` in a browser context returns `number`. In Node.js context (and when `@types/node`
is installed as a dev dependency), `setTimeout()` returns `NodeJS.Timeout`. If both type packages
are in scope simultaneously, TypeScript cannot resolve the type of the timer variable and throws:
`Type 'Timeout' is not assignable to type 'number'`.

This matters in `main.js` which uses timers in multiple places:
- `feedback._timer = setTimeout(...)` in `showPasteFeedback()`
- `sortTimer = null; sortTimer = setTimeout(...)` in `sortCardsBySeverity()`
- `clearTimeout(sortTimer)` in `sortCardsBySeverity()`
- `setInterval(...)` in `initEnrichmentPolling()`

**Why it happens:**
`@types/node` is often installed as a dev dependency for other build tooling. Once installed, it
pollutes the global type environment. TypeScript's `lib` setting (`"DOM"`) and `types` compiler
option interact in non-obvious ways.

**How to avoid:**
Three approaches (pick one, document the choice):

Option A — Use `ReturnType<typeof setTimeout>` as the timer type. This derives the correct type
for the actual runtime environment and works regardless of which `@types` are installed:

```typescript
let sortTimer: ReturnType<typeof setTimeout> | null = null;
```

Option B — Use `window.setTimeout()` explicitly. TypeScript always infers `number` for `window.setTimeout`:

```typescript
const intervalId = window.setInterval(pollFn, 750); // type: number
```

Option C — Restrict `@types` in tsconfig so only DOM types are included:

```json
{ "compilerOptions": { "types": [] } }
```

This prevents `@types/node` from polluting global scope.

**Recommended:** Option A (`ReturnType<typeof setTimeout>`) — most portable, no tsconfig surgery needed.

**Warning signs:**
- TypeScript error: `Type 'Timeout' is not assignable to type 'number'`
- `let sortTimer: any = null` used to suppress the error — defeats type safety
- Timer variables typed as `number` compile fine locally but fail in CI where `@types/node` is installed

**Phase to address:**
Phase 2 (TypeScript Conversion) — resolve before converting `initEnrichmentPolling()` and `sortCardsBySeverity()`.

---

### Pitfall 6: `getAttribute()` Always Returns `string | null` — TypeScript Won't Narrow on `hasAttribute()`

**What goes wrong:**
TypeScript's DOM types define `getAttribute(name: string): string | null`. Even after calling
`element.hasAttribute("data-verdict")`, TypeScript does NOT narrow the return type of
`element.getAttribute("data-verdict")` to `string`. Every `getAttribute()` call requires
explicit null handling.

`main.js` calls `getAttribute()` in many places without null checks (because the JS already
guarantees the attribute exists via template rendering). TypeScript will flag every one of these.

**Why it happens:**
TypeScript's type narrowing does not flow from `hasAttribute()` to `getAttribute()` — this is a
known TypeScript limitation (GitHub issue #22238). Developers discover this only when converting
the code and face dozens of type errors.

**How to avoid:**
Use a typed helper that coalesces null to empty string or a default, avoiding null handling at
every call site:

```typescript
function attr(el: Element, name: string, fallback = ""): string {
    return el.getAttribute(name) ?? fallback;
}
```

For verdict attributes specifically, use a type-safe approach with the union type:

```typescript
type Verdict = "malicious" | "suspicious" | "clean" | "no_data" | "error";

function getVerdict(el: Element): Verdict {
    return (el.getAttribute("data-verdict") ?? "no_data") as Verdict;
}
```

**Warning signs:**
- `el.getAttribute("x")!` used everywhere to suppress null
- TypeScript errors: `Object is possibly 'null'` on every `getAttribute` call
- `// @ts-ignore` comments before getAttribute lines

**Phase to address:**
Phase 2 (TypeScript Conversion) — define utility functions before converting DOM manipulation code.

---

### Pitfall 7: Source Map Path Resolution Broken in Flask Static File Serving

**What goes wrong:**
esbuild generates source maps with paths relative to the source files at build time. When Flask
serves `main.js` from `/static/main.js`, the browser DevTools fetches the map at `/static/main.js.map`.
Inside the map, the `sources` array contains paths like `../src/main.ts` — relative to where
esbuild ran, not to how Flask serves them.

If esbuild is run from the project root but the source files are in `app/static/src/`, the
resolved paths in DevTools may point to the wrong location: DevTools shows the TypeScript source
but cannot map breakpoints back to it.

**Why it happens:**
Flask's static file serving adds a URL prefix (`/static/`) that does not correspond to the
file system layout that esbuild uses. Source map `sources` are relative paths that esbuild
resolves from the bundle output file location, not the URL where the browser loads the bundle.

**How to avoid:**
Run esbuild from the directory that makes the relative paths correct:
- Source: `app/static/src/main.ts`
- Output: `app/static/main.js`
- Run esbuild from project root with explicit paths

Verify source maps work by: (1) loading the page in Chrome, (2) opening DevTools Sources tab,
(3) finding `main.ts` under the page's sources, (4) setting a breakpoint on the `initSubmitButton`
function call. If the breakpoint maps to the correct TypeScript line, source maps are working.

Use `--sourcemap=linked` in the esbuild command (generates external map file, appends
`//# sourceMappingURL` comment to bundle). This is the correct setup for Flask static serving
— the map file is a separate HTTP request, not inlined, no CSP implications.

Do NOT use `--sourcemap=inline` — it bloats the JS file and serves source code to any browser
that loads the page. Acceptable for a local tool, but bad practice.

**Warning signs:**
- DevTools Sources tab shows the minified bundle but not the TypeScript source
- Setting breakpoints in TypeScript shows `X` (could not load source) in DevTools
- The `.map` file is not accessible at the expected URL (`/static/main.js.map`)
- DevTools console shows: `Could not load content for main.js.map: HTTP error: status code 404`

**Phase to address:**
Phase 1 (Build Pipeline Setup) — verify source maps in browser before proceeding to TS conversion.

---

### Pitfall 8: Makefile Build Not Integrated — TypeScript Silently Runs Stale JS

**What goes wrong:**
After adding the TypeScript build step, the Makefile has a `ts` or `build` target. But:
1. The developer edits `.ts` files and refreshes the browser — the browser loads the old `main.js`
   because they forgot to run `make ts`.
2. CI runs `pytest tests/e2e/` without first running `make ts` — tests run against the old JS.
3. The `.ts` files diverge from `main.js` for weeks before anyone notices.

This is the most common TypeScript migration productivity failure and produces confusing debugging
sessions ("why isn't my change showing up?").

**Why it happens:**
Adding a build step to a project that previously had none requires updating every workflow that
touches the JS file: development habits, CI scripts, deployment steps, and any documentation
that says "edit `main.js`." This update is easy to miss in the heat of the migration.

**Specific risk in SentinelX:**
- `app/static/main.js` must become a BUILD ARTIFACT, not a source file
- The file must be tracked in git as generated (with a clear comment at the top of the file)
- CI must run `make ts` (or `make build`) before running E2E tests
- Watch mode (`make ts-watch`) should exist for development iteration

**How to avoid:**
As Phase 1 of the build pipeline:
1. Add `ts` and `ts-watch` targets to `Makefile`
2. Update `build` to depend on both `css` and `ts`
3. Add a comment to `app/static/main.js` at the top: `/* GENERATED FILE — edit app/static/src/main.ts instead */`
4. Update any CI or test scripts to run `make build` before tests
5. Document in the project that `.ts` files are the source of truth

**Warning signs:**
- Editing `.ts` file and refreshing browser shows no change
- `main.js` timestamp is older than `main.ts` after editing
- CI passes but local tests fail (or vice versa) because different JS versions are being tested
- PR diff shows changes in both `main.ts` and `main.js` manually synchronized

**Phase to address:**
Phase 1 (Build Pipeline Setup) — establish Makefile integration before writing any TypeScript.

---

### Pitfall 9: Over-Typing with `any` — Defeats the Purpose of the Migration

**What goes wrong:**
The migration hits a complex type: the enrichment result object from the JSON API response, the
`iocVerdicts` accumulator map, or the `event.target` in a DOM event listener. Rather than defining
a proper interface, the developer types it as `any` and moves on. At the end of the migration,
20% of the codebase is `any` and TypeScript provides zero safety for the most important types.

**Why it happens:**
`any` silences TypeScript errors immediately. Under deadline pressure or when stuck on a complex
type, `any` is the zero-friction escape hatch. The intention is always to "fix it later" — which
rarely happens.

**Specific risk in SentinelX:**
The most complex types in `main.js` that developers are likely to punt on:

1. **Enrichment result from API** — the JSON from `/enrichment/status/{job_id}`:

```typescript
// Do NOT use:
function renderEnrichmentResult(result: any) { ... }

// Use instead:
interface EnrichmentResult {
    type: "result" | "error";
    ioc_value: string;
    provider: string;
    verdict?: "malicious" | "suspicious" | "clean" | "no_data";
    detection_count?: number;
    total_engines?: number;
    scan_date?: string;
    error?: string;
}
```

2. **iocVerdicts accumulator** — a map of ioc_value to verdict array:

```typescript
// Do NOT use:
const iocVerdicts: Record<string, any[]> = {};

// Use instead:
interface VerdictEntry { provider: string; verdict: string; summaryText: string; }
const iocVerdicts: Record<string, VerdictEntry[]> = {};
```

3. **Event target in listeners** — `event.target` is `EventTarget | null`, not `HTMLElement`.
   Use the closed-over element reference instead of the event target:

```typescript
// Do NOT use event parameter typed as any:
btn.addEventListener("click", (event: any) => { event.target.getAttribute("data-value"); });

// Use instead — btn is already typed in the closure:
btn.addEventListener("click", () => { btn.getAttribute("data-value"); });
```

**How to avoid:**
Define all API response interfaces in a dedicated `types.ts` module before converting any logic.
The TypeScript migration PR should include `app/static/src/types.ts` with all domain types
defined before any function is converted.

**Warning signs:**
- More than 3 uses of `: any` in converted code
- `Record<string, any>` for the iocVerdicts map
- `event: any` in addEventListener callbacks
- `(result as any).verdict` — type assertion to `any` then property access

**Phase to address:**
Phase 2 (TypeScript Conversion) — write `types.ts` first, before converting `main.js`.

---

### Pitfall 10: Under-Typing with Overly Broad Unions — Accepts Invalid Values

**What goes wrong:**
The opposite problem: types are so broad they accept invalid values and TypeScript provides false
confidence. For example, typing verdict as `string` instead of the specific union type means a
typo in an API response key is not caught.

**Why it happens:**
Getting the union types right requires reading the backend code and API documentation.
Developers in a hurry define `verdict: string` to avoid this investigation.

**Specific risk in SentinelX:**
`VERDICT_SEVERITY = ["error", "no_data", "clean", "suspicious", "malicious"]` is a runtime list
that drives the severity sorting. If typed as `string[]` instead of `Verdict[]`, TypeScript
cannot catch attempts to compare an invalid verdict string.

**How to avoid:**

```typescript
// In types.ts:
export type Verdict = "malicious" | "suspicious" | "clean" | "no_data" | "error";
export type IocType = "ipv4" | "ipv6" | "domain" | "url" | "md5" | "sha1" | "sha256" | "cve";

// VERDICT_SEVERITY becomes:
const VERDICT_SEVERITY: readonly Verdict[] = ["error", "no_data", "clean", "suspicious", "malicious"];

// verdictSeverity function becomes typed:
function verdictSeverity(verdict: Verdict): number {
    return VERDICT_SEVERITY.indexOf(verdict);
}
```

**Warning signs:**
- Constants typed as `string[]` instead of specific union type arrays
- Function parameters accepting `string` where a union type would be more precise
- `VERDICT_LABELS` typed as `Record<string, string>` instead of `Record<Verdict, string>`

**Phase to address:**
Phase 2 (TypeScript Conversion) — define narrow union types in `types.ts` as first step.

---

### Pitfall 11: E2E Tests Break Due to Build Output Race or Stale Artifact

**What goes wrong:**
After the TS pipeline is added, CI runs E2E tests. One of two failure modes:

Mode A — Missing build: CI does not run `make ts` before `pytest tests/e2e/`. The tests run against
the old `main.js`. If the old `main.js` is deleted (because it is now a build artifact), the page
loads without JavaScript and ALL E2E tests fail with `element not found` or timeout errors.

Mode B — Stale build: CI runs the old `main.js` (cached artifact, not rebuilt). Tests pass
for behavior that was removed or renamed in the TypeScript refactor. False green.

**Why it happens:**
CI scripts are written before the build pipeline exists. Adding a new build step requires updating
CI — which is done separately from the migration PR, often forgotten.

**How to avoid:**
- Add `make ts` (or `make build`) to the CI test workflow before the pytest invocation
- Verify in the migration PR that `app/static/main.js` is rebuilt as a step in the test command
- If `main.js` is gitignored (correct for a generated file), CI must always build it before tests
- Add a CI check: verify `main.js` exists before allowing E2E tests to run

**Warning signs:**
- E2E tests fail with `TimeoutError: Locator.expect_to_be_visible: Timeout 30000ms exceeded`
  (not a JS error, element just is not interactive because JS did not load)
- All E2E tests pass in CI but only because they are running against stale correct behavior
- The `app/static/main.js` in CI differs from the local build

**Phase to address:**
Phase 1 (Build Pipeline Setup) — update CI before merging the migration PR.

---

### Pitfall 12: Import Path Extension Mismatch (`.ts` vs `.js`)

**What goes wrong:**
TypeScript sources import other modules. The correct extension in TypeScript ESM imports is `.js`
(the compiled output extension), NOT `.ts`. Developers write `import { initSubmitButton } from './submit'`
(no extension) or `import ... from './submit.ts'` — both can cause resolution issues in different contexts.

This is less relevant for IIFE format (esbuild bundles everything into one file from a single entry point),
but becomes critical if the migration splits `main.ts` into multiple modules.

**Why it happens:**
TypeScript file resolution allows importing without extension in non-bundler mode. But esbuild
requires explicit extensions for proper resolution in some configurations, and `import from './foo.ts'`
is a TypeScript extension that does not follow Node ESM standards.

**Specific risk in SentinelX:**
If `main.ts` is split into `submit.ts`, `polling.ts`, `filter.ts` etc. (a likely refactor),
cross-file imports must use `.js` extension (the compiled output) even though the source is `.ts`.

**How to avoid:**
- If using IIFE format with a single entry point: esbuild handles resolution from a single file —
  extensions less critical because esbuild follows imports through the source directory
- If using ESM format or multiple source files: use `.js` extension in all import statements
- Set `moduleResolution: "bundler"` in tsconfig — designed for esbuild/vite/etc. and allows
  extensionless imports that esbuild resolves correctly
- Document the convention in a comment in the first import statement

**Warning signs:**
- esbuild error: `Could not resolve "./submit.ts"`
- TypeScript error: `An import path cannot end with a '.ts' extension`
- Module not found errors only in the production bundle but not in the IDE

**Phase to address:**
Phase 2 (TypeScript Conversion) — establish import convention before splitting modules.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Type entire codebase as `any` first, fix later | Migration completes fast | "Fix later" never happens; TypeScript provides false safety | Never — define API types first |
| Use `!` on every `getElementById` | Silences null errors instantly | Crashes at runtime if element removed from template | Only with comment proving element is always present |
| Skip `tsc --noEmit` type checking, use only esbuild | Fast builds, no type-check overhead | Type errors accumulate silently; esbuild never catches them | Never — `tsc --noEmit` must run in CI |
| Keep `main.js` in version control as hand-edited source | Avoids CI changes and build step | Developers edit the wrong file; source of truth is ambiguous | Never after pipeline is established |
| Define types inline instead of in `types.ts` | Faster to write | Types duplicated across files; domain model not centralized | Never for shared API shapes |
| Convert entire 856-line file at once | PR is a single commit | Massive diff, hard to review, hard to bisect regressions | Convert function by function for large files |
| Mix refactoring with type annotations | One PR for everything | Behavioral regressions hidden in type changes; test failures hard to attribute | Never — separate type migration from code modernization |

---

## Integration Gotchas

Specific to the SentinelX TypeScript migration context.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Flask static files | Serving `main.ts` directly instead of the compiled `main.js` | esbuild compiles to `app/static/main.js`; Flask serves that; never serve `.ts` files |
| Source maps + Flask | Map file not accessible at `/static/main.js.map` | Output map to `app/static/` alongside `main.js`; Flask serves it automatically |
| Tailwind safelist + TS | Dynamic class names in TypeScript not recognized by Tailwind | TypeScript files should not generate new dynamic classes; class names remain in templates |
| Playwright E2E | Tests use `page.evaluate()` to run JS snippets — these are not typed | Keep `evaluate()` calls untyped; they run in browser scope where types do not apply |
| CSP + tsc `outFile` | tsc `outFile` concatenation mode can produce non-compliant output | Use esbuild for bundling, `tsc --noEmit` for type checking only; never use tsc for production output |
| `feedback._timer` property | TypeScript rejects dynamic properties on DOM elements | Refactor to module-level `let feedbackTimer: ReturnType<typeof setTimeout> | null = null` |
| `CSS.escape()` usage | May seem like an obscure API without types | TypeScript DOM lib includes `CSS.escape()` — ensure `lib` includes `"DOM"` in tsconfig |

---

## Security Mistakes

TypeScript-migration-specific security issues for SentinelX.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Introducing dynamic code execution via bundler (see Pitfall 1) | Breaks CSP, creates code injection vectors | Use esbuild IIFE; explicitly avoid webpack; verify bundle contents after build |
| Switching to `innerHTML` to "fix" a TypeScript DOM typing error | Opens XSS — the existing `textContent` pattern is a deliberate security control (SEC-08) | Preserve all `.textContent` assignments; never change to `.innerHTML` to resolve a type error |
| Adding `style-src 'unsafe-inline'` to fix a build-generated inline style | Weakens CSP globally; no bundler should be generating inline styles | TypeScript does not generate inline styles; investigate the actual source of any inline style CSP violation |
| Including `@types/node` globally in tsconfig without restricting scope | NodeJS types pollute global scope; timer types become ambiguous | Restrict `types` in tsconfig to exclude Node global pollution in browser code |
| Using `as any` to bypass type check on user input or API response data | Defeats type safety on the most security-sensitive data paths | Define strict interfaces for all API response shapes; use `unknown` with runtime validation, not `any` |

---

## UX Pitfalls

TypeScript migration-specific UX risks.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| JS loading fails after migration (format mismatch) | Entire UI becomes static — no button enable/disable, no mode toggle, no polling | Verify E2E tests pass before deployment; test with browser DevTools network tab |
| Source map not found causes console errors | Noisy DevTools console distracts analyst debugging a different issue | Verify map file is accessible and add to Makefile verification step |
| Build output is unminified in production | Slightly larger file size (negligible for local tool; but inconsistent with CSS which IS minified) | Add `--minify` flag to production esbuild command; match CSS build behavior |
| TypeScript errors prevent build, blocking page refresh | Developer productivity loss; page does not update when tsc is blocking | Use esbuild for always-compiling output; run tsc separately as a check; esbuild errors do not block the browser |

---

## "Looks Done But Isn't" Checklist

- [ ] **CSP compliance:** Bundle compiles and loads — but inspect bundle for dynamic code execution patterns; run `pytest tests/test_security_audit.py` to verify CSP assertions pass
- [ ] **Type checking:** esbuild builds successfully — but `tsc --noEmit` must also pass (esbuild does not type-check)
- [ ] **E2E tests:** Tests pass locally — but verify CI runs `make ts` before pytest
- [ ] **Source maps:** DevTools shows "main.js" — but verify it shows "main.ts" with correct line numbers (set a breakpoint to confirm)
- [ ] **Timer types:** Code compiles — but verify timer variables are typed with `ReturnType<typeof setTimeout>` not `any`
- [ ] **API types:** Enrichment polling compiles — but verify `EnrichmentResult` interface matches actual `/enrichment/status/` JSON shape
- [ ] **Behavior preserved:** All TypeScript added — but run `pytest tests/e2e/` and all existing unit tests before marking migration complete
- [ ] **Makefile updated:** New `ts` and `ts-watch` targets added — but verify `build` target now depends on both `css` and `ts`
- [ ] **No innerHTML regressions:** DOM manipulation code compiled — but scan for `.innerHTML` assignments to confirm none were introduced
- [ ] **No inline styles introduced:** Code passes review — but scan for `element.style.color` and `element.style.background` to catch color literals

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| CSP violation from bundler dynamic evaluation | LOW | Switch to esbuild IIFE; remove webpack/vite dependency; rebuild |
| Module format mismatch (ESM without type="module") | LOW | Add `type="module"` to script tag in `base.html` OR switch esbuild to `--format=iife` |
| Behavior regression from refactor-during-migration | MEDIUM | Revert behavioral changes; keep only type annotations; re-run E2E tests |
| Dozens of `!` assertions discovered in review | MEDIUM | Systematic replace with null guards using existing `if (!el) return` pattern |
| Timer type conflicts throughout codebase | LOW | Global find/replace of timer variable types to `ReturnType<typeof setTimeout>` |
| Source maps broken in DevTools | LOW | Fix esbuild output path; verify `main.js.map` accessible at `/static/main.js.map` |
| CI fails because `make ts` not in test pipeline | LOW | Add build step to CI workflow before pytest invocation |
| `any` types throughout — type safety near zero | HIGH | Must re-migrate with proper types; hardest to recover from because requires re-reading all logic |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification Method |
|---------|------------------|---------------------|
| CSP violation from bundler (Pitfall 1) | Phase 1 — Build pipeline | `pytest tests/test_security_audit.py` passes; bundle contents inspected for dynamic code patterns |
| Module format mismatch (Pitfall 2) | Phase 1 — Build pipeline | Load page; check DevTools console for module syntax errors |
| Refactoring behavior during migration (Pitfall 3) | All migration phases — code review | All Playwright E2E tests pass after TS conversion; diff contains no behavioral changes |
| querySelector null strategy (Pitfall 4) | Phase 2 — TS conversion | Review null strategy; no `!` on querySelector without documented justification |
| Timer type conflicts (Pitfall 5) | Phase 2 — TS conversion | `tsc --noEmit` passes; timer types use `ReturnType<typeof setTimeout>` |
| getAttribute null return (Pitfall 6) | Phase 2 — TS conversion | Utility helper `attr()` defined; no raw `getAttribute()` without null handling |
| Source map path resolution (Pitfall 7) | Phase 1 — Build pipeline | Breakpoint in DevTools maps to correct TypeScript line number |
| Makefile/CI not updated (Pitfall 8) | Phase 1 — Build pipeline | CI test job includes `make ts` before pytest; watch mode target exists |
| Over-typing with any (Pitfall 9) | Phase 2 — TS conversion | `types.ts` created with API interfaces; `any` count in codebase is 0 or explicitly justified |
| Under-typing with broad strings (Pitfall 10) | Phase 2 — TS conversion | Verdict, IocType are union types; `verdictSeverity` accepts `Verdict` not `string` |
| E2E test race/stale artifact (Pitfall 11) | Phase 1 — Build pipeline | CI pipeline verified; `main.js` freshness confirmed in CI |
| Import path extension mismatch (Pitfall 12) | Phase 2 — TS conversion | `moduleResolution: "bundler"` in tsconfig; all imports resolve in both esbuild and tsc |

---

## Sources

- esbuild API documentation (format, sourcemap, platform options): https://esbuild.github.io/api/
- esbuild TypeScript caveats (no type checking, no decorator metadata, ignored tsconfig fields): https://esbuild.github.io/content-types/#typescript
- TypeScript: Migrating from JavaScript (official docs): https://www.typescriptlang.org/docs/handbook/migrating-from-javascript.html
- TypeScript DOM Manipulation documentation: https://www.typescriptlang.org/docs/handbook/dom-manipulation.html
- TypeScript tsconfig Reference (lib, types, moduleResolution): https://www.typescriptlang.org/tsconfig/
- getAttribute not narrowed by hasAttribute — known TypeScript limitation: https://github.com/microsoft/TypeScript/issues/22238
- setTimeout return type conflict (NodeJS.Timeout vs number): https://guilhermesimoes.github.io/blog/making-settimeout-return-number-in-typescript
- Heap Engineering: Migrating to TypeScript (avoid refactoring during migration): https://www.heap.io/blog/migrating-to-typescript
- Qualtrics Engineering: Migrating Legacy JS to TypeScript (preserve behavior): https://www.qualtrics.com/eng/typescript-refactor/
- Webpack CSP dynamic evaluation issue: https://github.com/webpack/webpack/issues/5627
- webpack-dev-server unsafe-eval CSP requirement: https://github.com/webpack/webpack/discussions/18073
- EventTarget property access in TypeScript: https://freshman.tech/snippets/typescript/fix-value-not-exist-eventtarget/
- SentinelX codebase: `app/static/main.js` (856 lines, IIFE pattern, all DOM patterns documented)
- SentinelX codebase: `tests/test_security_audit.py` (CSP assertions: no unsafe-eval, no unsafe-inline)
- SentinelX codebase: `app/templates/base.html` (script tag: `defer`, no `type="module"`)

---

*Pitfalls research for: TypeScript migration of vanilla JS IIFE in a Python/Flask application with strict CSP (SentinelX v3.0)*
*Researched: 2026-02-28*
