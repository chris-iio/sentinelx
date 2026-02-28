# Stack Research

**Domain:** TypeScript migration of vanilla JS frontend in a Flask project (SentinelX v3.0)
**Researched:** 2026-02-28
**Confidence:** HIGH (esbuild standalone binary, tsconfig options), HIGH (TypeScript version), HIGH (CSP compatibility), MEDIUM (Makefile integration patterns)

---

## Context: What Already Exists (Do Not Change)

This is a SUBSEQUENT MILESTONE research document. The following stack is locked in and working — do not re-research or modify it:

- Python 3.10 + Flask 3.1 — backend, unchanged
- Tailwind CSS standalone CLI v3.4.17 — CSS build via `tools/tailwindcss` binary, `make css`
- Vanilla JS IIFE — `app/static/main.js` (856 lines, one file)
- CSS custom properties + design tokens — `app/static/src/input.css`
- Inter Variable + JetBrains Mono Variable — self-hosted fonts
- Heroicons v2 inline SVG via Jinja2 macros
- pytest + Playwright E2E — 224 tests, 97% coverage
- CSP: `default-src 'self'; script-src 'self'` — strict, prohibits unsafe-eval

**Project constraint: No Node.js runtime.** The project uses standalone binaries (like the Tailwind CLI). This constraint MUST be preserved.

---

## What We Need to Add

The v3.0 milestone adds:

1. A **TypeScript bundler** (standalone binary, no Node.js) to transpile `.ts` to `.js`
2. A **TypeScript compiler config** (`tsconfig.json`) for type checking and IDE support
3. A **type-check step** (separate from bundling) to catch type errors
4. An updated **Makefile** with `js`, `js-watch`, and `typecheck` targets
5. An updated **`base.html`** pointing to the output bundle instead of `main.js`

---

## Recommended Stack

### Core Technologies (New Additions Only)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| esbuild standalone binary | 0.27.3 | TypeScript bundler + minifier | Standalone binary download via curl (same pattern as Tailwind CLI). Natively understands TypeScript — strips types without a Node.js runtime. Produces IIFE output with source maps. 10-100x faster than webpack. No config file required for simple use. |
| TypeScript (npm package, dev-only) | 5.8.3 | Type checking via `tsc --noEmit` | Provides `tsc` for type checking only — esbuild handles transpilation. Install via npm once for development; DOM types are built-in (lib.dom.d.ts). No separate @types packages needed. |
| `tsconfig.json` | N/A | TypeScript compiler configuration | Configures strict type checking, DOM lib, isolatedModules (required for esbuild), target ES2022. esbuild reads select fields (target, strict, verbatimModuleSyntax). |

### Supporting Libraries (No New Runtime Dependencies)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Built-in `lib.dom` | Ships with TypeScript | DOM type definitions (HTMLElement, HTMLTextAreaElement, fetch, CSS, etc.) | Activated via `"lib": ["es2022", "dom", "dom.iterable"]` in tsconfig — no separate package needed |

**Note:** No `@types/*` packages are needed. The DOM types are bundled inside TypeScript's `lib.dom.d.ts`. The project has no npm dependencies at runtime — only esbuild (as a binary) and TypeScript (for type-checking only, dev workflow only).

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `tools/esbuild` | Standalone binary for bundling TypeScript to IIFE JS | Downloaded via curl from esbuild.github.io/dl/v0.27.3; same `tools/` directory as Tailwind CLI |
| `tsc` (from `npm install -D typescript`) | Type checking only — `tsc --noEmit` | Does NOT emit JS; esbuild handles transpilation. Run as `make typecheck` |
| Makefile `js` target | One-shot TypeScript build | Runs esbuild to produce `app/static/dist/main.js` with source maps |
| Makefile `js-watch` target | Development rebuild on file change | esbuild `--watch` flag; fast incremental rebuilds |
| Makefile `typecheck` target | CI-safe type validation | Runs `tsc --noEmit` against `tsconfig.json` |

---

## esbuild Standalone Binary

esbuild distributes standalone native binaries that require zero Node.js runtime. The download mechanism is identical to the existing Tailwind CLI pattern.

### Download Command

```bash
# Linux x64 (current dev environment) — installs to current directory
curl -fsSL https://esbuild.github.io/dl/v0.27.3 | sh
mv esbuild tools/esbuild
chmod +x tools/esbuild
```

Or manual download from npm registry (no npm needed):

```bash
curl -O https://registry.npmjs.org/@esbuild/linux-x64/-/linux-x64-0.27.3.tgz
tar xzf linux-x64-0.27.3.tgz
mv package/bin/esbuild tools/esbuild
chmod +x tools/esbuild
```

**Verified:** esbuild v0.27.3 is the current stable release (February 2026). The binary is approximately 8MB and self-contained.

### esbuild CLI Flags for This Project

```bash
./tools/esbuild \
  app/static/src/main.ts \
  --bundle \
  --format=iife \
  --platform=browser \
  --target=es2022 \
  --sourcemap \
  --minify \
  --outfile=app/static/dist/main.js
```

**Flag rationale:**

| Flag | Value | Why |
|------|-------|-----|
| `--bundle` | (no value) | Inlines all TS imports into a single output file — matches Flask's single static file serving |
| `--format=iife` | iife | Wraps bundle in an immediately-invoked function expression — same structure as current `main.js`; no global scope pollution; matches `script-src 'self'` CSP |
| `--platform=browser` | browser | Configures esbuild for browser targets; disables Node.js built-ins; sets correct globals |
| `--target=es2022` | es2022 | Match tsconfig target; ES2022 is supported in all modern browsers and Playwright test environment |
| `--sourcemap` | (no value) | Emits linked `.js.map` file alongside output; browser DevTools map minified code back to `.ts` source |
| `--minify` | (no value) | Minifies for production; esbuild minification is safe and very fast |
| `--outfile` | `app/static/dist/main.js` | Output goes to the existing dist directory alongside `style.css` |

**esbuild TypeScript support:** esbuild natively strips TypeScript type annotations and transpiles syntax. It does NOT type-check. Run `tsc --noEmit` separately for type safety.

**esbuild `isolatedModules` requirement:** esbuild processes each file independently (no cross-file type information). Therefore `isolatedModules: true` must be set in `tsconfig.json` — this prevents TypeScript code patterns that require full type system knowledge (e.g., `const enum` re-exports, ambient namespace merging).

---

## tsconfig.json Configuration

### Recommended `tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "lib": ["es2022", "dom", "dom.iterable"],

    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,

    "isolatedModules": true,
    "verbatimModuleSyntax": true,

    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "moduleDetection": "force",

    "noEmit": true
  },
  "include": ["app/static/src/**/*.ts"],
  "exclude": ["node_modules"]
}
```

### Key Decision Rationale

| Option | Value | Why |
|--------|-------|-----|
| `target` | `ES2022` | Modern but stable; supported in Playwright test browsers; matches esbuild `--target=es2022`; avoids TypeScript 6.0 beta churn |
| `module` | `ESNext` | Lets us write `import`/`export` in source files; esbuild handles bundling into IIFE |
| `moduleResolution` | `Bundler` | Designed for bundler-mediated resolution; understands package.json `exports` fields; correct for esbuild workflows |
| `lib` | `["es2022", "dom", "dom.iterable"]` | DOM types (HTMLElement, fetch, CSS.escape, etc.) are built into TypeScript — no extra packages needed |
| `strict` | `true` | Enables strictNullChecks, noImplicitAny, strictFunctionTypes — the migration's primary value |
| `noUncheckedIndexedAccess` | `true` | Array index access returns `T or undefined` — catches the many array-to-DOM lookups in main.js |
| `isolatedModules` | `true` | Required for esbuild — prevents TS patterns that need cross-file type information |
| `verbatimModuleSyntax` | `true` | Ensures `import type` is used for type-only imports — esbuild-safe |
| `noEmit` | `true` | `tsc` only type-checks; esbuild handles JS emit |

### What `noEmit: true` Means

`tsc --noEmit` validates types without writing `.js` files. This is the standard pattern when using esbuild as the transpiler:

```
tsc --noEmit       -> type errors -> fail build (no output written)
esbuild main.ts    -> produces dist/main.js -> served by Flask
```

Both steps run independently. In a Makefile `build` target, run `typecheck` before `js` so type errors fail the build before output is written.

---

## Module Structure for Migration

The 856-line IIFE in `main.js` decomposes naturally into these TypeScript modules:

```
app/static/src/
    main.ts               <- entry point; calls init(), imports all modules
    types.ts              <- shared type definitions (Verdict, IOCType, EnrichmentResult)
    submit.ts             <- initSubmitButton(), initModeToggle(), updateSubmitLabel()
    textarea.ts           <- initAutoGrow(), showPasteFeedback()
    clipboard.ts          <- initCopyButtons(), writeToClipboard(), fallbackCopy()
    polling.ts            <- initEnrichmentPolling(), renderEnrichmentResult(), updateProgressBar()
    cards.ts              <- updateCardVerdict(), updateDashboardCounts(), sortCardsBySeverity()
    filters.ts            <- initFilterBar(), applyFilter()
    settings.ts           <- initSettingsPage()
    ui.ts                 <- initScrollAwareFilterBar(), initCardStagger()
```

**esbuild bundles all of these into a single `app/static/dist/main.js` IIFE.** Flask serves only the output file — no ES module imports in the browser, no `<script type="module">` tag needed, no import maps. The module structure is a build-time concern only.

### Key Types to Define in `types.ts`

```typescript
type Verdict = 'malicious' | 'suspicious' | 'clean' | 'no_data' | 'error';

type IOCType = 'ipv4' | 'ipv6' | 'domain' | 'url' | 'md5' | 'sha1' | 'sha256' | 'cve';

interface EnrichmentResult {
  ioc_value: string;
  provider: string;
  type: 'result' | 'error';
  verdict?: Verdict;
  detection_count?: number;
  total_engines?: number;
  scan_date?: string;
  error?: string;
}

interface PollResponse {
  done: number;
  total: number;
  complete: boolean;
  results: EnrichmentResult[];
}

interface VerdictEntry {
  provider: string;
  verdict: Verdict;
  summaryText: string;
}
```

---

## Makefile Integration

```makefile
ESBUILD  := ./tools/esbuild
TS_ENTRY := app/static/src/main.ts
JS_OUT   := app/static/dist/main.js

## Download esbuild standalone binary (no Node.js required)
esbuild-install:
	@mkdir -p tools
	curl -fsSL https://esbuild.github.io/dl/v0.27.3 | sh
	mv esbuild $(ESBUILD)
	chmod +x $(ESBUILD)
	@echo "esbuild installed at $(ESBUILD)"

## Compile TypeScript to IIFE bundle (one-shot, minified)
js:
	$(ESBUILD) $(TS_ENTRY) \
		--bundle \
		--format=iife \
		--platform=browser \
		--target=es2022 \
		--sourcemap \
		--minify \
		--outfile=$(JS_OUT)

## Watch mode for development (no minify for readable DevTools)
js-watch:
	$(ESBUILD) $(TS_ENTRY) \
		--bundle \
		--format=iife \
		--platform=browser \
		--target=es2022 \
		--sourcemap \
		--outfile=$(JS_OUT) \
		--watch

## Type-check TypeScript (no JS output — requires tsc in PATH)
typecheck:
	tsc --noEmit

## Full build: CSS + JS
build: css js
```

**Note:** `--minify` is omitted from `js-watch` so DevTools source maps remain readable during development.

---

## CSP Compatibility

The existing CSP is `default-src 'self'; script-src 'self'`. The TypeScript migration must not break this.

| Concern | Status | Notes |
|---------|--------|-------|
| IIFE output format | SAFE | IIFE wraps code in a function — produces static code without dynamic code execution |
| Source maps | SAFE | `.js.map` files are served from `/static/dist/` — same origin. Browser DevTools fetches them; CSP does not restrict sourcemap file fetching |
| esbuild IIFE output | SAFE | esbuild IIFE format produces deterministic static output; no dynamic code execution patterns |
| Import syntax | NOT USED | esbuild bundles everything into one IIFE; no dynamic import() or ESM in output; script type="module" not needed |
| TypeScript `const enum` | AVOID | esbuild handles const enum within a single file but cross-file const enum usage requires full type information; use regular enum or string literals instead |

**The CSP header does not need to change.** The output is a single IIFE `.js` file served from `/static/dist/` — identical security posture to the current `main.js`.

---

## Output File Location

Current: `app/static/main.js` (source and output are the same file — no build step)

After migration:

```
app/static/
    src/
        main.ts           <- TypeScript source (entry point)
        types.ts
        submit.ts
        ...               <- remaining modules
    dist/
        style.css         <- existing Tailwind output (unchanged)
        main.js           <- NEW: esbuild output bundle
        main.js.map       <- NEW: source map for debugging
    main.js               <- KEEP during transition; DELETE after migration complete
```

`base.html` update (one-line change):

```html
<!-- Before -->
<script src="{{ url_for('static', filename='main.js') }}" defer></script>

<!-- After -->
<script src="{{ url_for('static', filename='dist/main.js') }}" defer></script>
```

The `defer` attribute stays — it is important for DOM-ready initialization logic.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| esbuild (standalone binary) | tsc emit mode (no bundler) | If you only have one TS file and want zero tooling — but this project needs a multi-file module structure |
| esbuild (standalone binary) | Rollup | Rollup produces cleaner output for library authoring with better tree-shaking; esbuild is faster and has a standalone binary with no Node.js required |
| esbuild (standalone binary) | Webpack | If you need heavy plugin ecosystem (CSS loaders, HMR dev server, code splitting for SPAs) — wrong scale for a Flask static script |
| esbuild (standalone binary) | Vite | Vite is a dev server + build tool designed for framework SPAs; requires Node.js; no standalone binary |
| esbuild (standalone binary) | Bun | Excellent bundler but introduces a new runtime dependency; esbuild binary is simpler for this scope |
| esbuild (standalone binary) | Parcel | Good zero-config DX but requires Node.js; no standalone binary |
| IIFE output format | ESM output (`--format=esm`) | Use ESM if you need native browser module loading with import maps; IIFE is simpler for Flask's single-script static serving and requires no HTML changes beyond the src path |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Webpack | Requires Node.js runtime; no standalone binary; enormous config overhead for a simple browser script | esbuild standalone binary |
| Vite | Requires Node.js; designed for SPAs with HMR dev server — wrong fit for Flask multi-page app | esbuild standalone binary |
| `tsc` emit mode | Produces one JS file per TS file without bundling; requires separate bundler anyway; much slower than esbuild | esbuild for transpilation + bundling; `tsc --noEmit` for type checking only |
| `ts-node` or `tsx` | Runtime TS execution — not needed; we are building browser JS, not running TS server-side | Not applicable |
| `const enum` in TypeScript | esbuild cannot inline const enum values from other files in isolated module mode — produces runtime errors | Use regular `enum` or `as const` object literals |
| `namespace` merging | Requires cross-file type information — breaks with `isolatedModules: true` | Use ES module `import`/`export` |
| `emitDecoratorMetadata` | Not supported by esbuild | Not needed for this project (no framework decorators) |
| Node.js as build runtime | Breaks the project constraint of standalone binaries only | esbuild binary; `tsc` installed once for dev type-checking |
| `--format=esm` output | Requires `<script type="module">` in HTML; more complex serving | `--format=iife` — self-contained, same security model as current setup |
| TypeScript 6.0 | Currently in beta (February 2026); breaking changes possible; not yet stable | TypeScript 5.8.3 (latest stable) |

---

## Stack Patterns by Variant

**If developing locally (fast iteration):**
- Use `make js-watch` (esbuild `--watch` flag)
- Skip `--minify` for readable DevTools output
- Source maps enabled — browser maps errors back to `.ts` files

**If running CI or full build:**
- Run `make typecheck` first (fails on type errors before any file is emitted)
- Then run `make build` (runs `make css` + `make js` with `--minify`)
- Playwright E2E tests run against the built `dist/main.js`

**If adding a new TypeScript module:**
- Create `app/static/src/new-module.ts`
- Export functions, import in `main.ts`
- esbuild bundles everything automatically — no build config change needed

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| esbuild 0.27.3 | TypeScript 5.x source files | esbuild natively strips TS types; does not require TypeScript installed to transpile |
| esbuild 0.27.3 | `tsconfig.json` (selected fields) | Reads: `target`, `strict`, `verbatimModuleSyntax`, `experimentalDecorators`, `jsxFactory` |
| TypeScript 5.8.3 | `isolatedModules: true` | Required; warns on patterns esbuild cannot handle across files |
| TypeScript 5.8.3 | `lib: ["es2022", "dom", "dom.iterable"]` | DOM types built-in; no `@types/dom` package needed |
| esbuild IIFE output | Flask `script-src 'self'` CSP | IIFE format produces static code with no dynamic code execution patterns |
| esbuild `--sourcemap` | Playwright E2E tests | Source maps do not affect test execution; Playwright tests against DOM behavior |
| esbuild `--target=es2022` | Chromium (Playwright default browser) | Chromium fully supports ES2022 |

---

## Installation

```bash
# 1. Install esbuild standalone binary (no Node.js required)
mkdir -p tools
curl -fsSL https://esbuild.github.io/dl/v0.27.3 | sh
mv esbuild tools/esbuild
chmod +x tools/esbuild

# 2. Install TypeScript for type checking (dev only — requires Node.js once)
npm install -D typescript@5.8.3
# This creates node_modules/ and package.json
# Add node_modules/ to .gitignore

# 3. Create tsconfig.json (see recommended configuration above)

# 4. Verify tools
./tools/esbuild --version       # -> 0.27.3
npx tsc --version               # -> Version 5.8.3
```

**Alternative if Node.js is unavailable for `tsc`:** Type checking can be deferred to a CI environment that has Node.js, while the esbuild binary handles local development builds. The `make typecheck` target would be CI-only in that scenario. Source maps still provide debugging support locally.

---

## Sources

- esbuild getting started (esbuild.github.io/getting-started/) — confirmed standalone binary download via curl, v0.27.3 current, no Node.js required (HIGH confidence)
- esbuild output formats (esbuild.github.io/api/#output-formats) — confirmed IIFE, ESM, CJS formats; browser platform default; IIFE wraps in function expression (HIGH confidence)
- esbuild TypeScript content types (esbuild.github.io/content-types/#typescript) — confirmed native TS type stripping, isolatedModules requirement, no type checking performed (HIGH confidence)
- esbuild sourcemap docs (esbuild.github.io/api/#sourcemap) — confirmed linked/inline/external/both modes (HIGH confidence)
- @esbuild/linux-x64 npm registry — confirmed v0.27.3 is latest stable (HIGH confidence)
- TypeScript 5.8 release blog (devblogs.microsoft.com/typescript/announcing-typescript-5-8/) — v5.8 released Feb 28 2025 (HIGH confidence)
- TypeScript 6.0 beta announcement — confirmed 6.0 is in beta as of Feb 2026; 5.9.x is latest stable series (MEDIUM confidence — search result summary)
- Total TypeScript tsconfig cheat sheet (totaltypescript.com/tsconfig-cheat-sheet) — confirmed `module: "preserve"`, `moduleResolution: "Bundler"`, `noEmit: true` for bundler workflows (HIGH confidence)
- TypeScript isolatedModules docs (typescriptlang.org/tsconfig/isolatedModules.html) — confirmed required for per-file transpilers like esbuild (HIGH confidence)
- WebSearch: esbuild vs rollup vs webpack comparison 2025 — confirmed esbuild is fastest, standalone, minimal config; webpack requires Node.js; Rollup better for libraries (MEDIUM confidence — multiple sources agree)
- WebSearch: DOM types built into TypeScript lib — confirmed DOM types are in lib.dom.d.ts bundled with TypeScript; no separate package needed (HIGH confidence)

---

*Stack research for: SentinelX v3.0 TypeScript Migration*
*Researched: 2026-02-28*
