# Architecture Research

**Domain:** TypeScript build pipeline integration into Flask static file architecture (SentinelX v3.0)
**Researched:** 2026-02-28
**Confidence:** HIGH — esbuild official docs verified via WebFetch, binary download mechanism confirmed, script tag options confirmed against browser CSP specs

---

## Context: What This Research Covers

This is a SUBSEQUENT MILESTONE research document. The backend (Python + Flask), CSS pipeline (Tailwind standalone CLI via `make css`), and runtime architecture are locked in. This document covers ONLY how a TypeScript build pipeline slots into the existing Flask static file serving architecture.

**Existing pipeline (do not change):**

```
app/static/src/input.css  →  [Tailwind CLI standalone binary]  →  app/static/dist/style.css
```

**Target pipeline (new, parallel to CSS):**

```
app/static/src/ts/main.ts  →  [esbuild standalone binary]  →  app/static/dist/main.js
```

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Source Layer                                 │
│  ┌──────────────────────────┐  ┌──────────────────────────────┐     │
│  │  app/static/src/ts/      │  │  app/static/src/input.css    │     │
│  │  ├── main.ts             │  │  (Tailwind source)            │     │
│  │  ├── modules/            │  └──────────────────────────────┘     │
│  │  │   ├── form.ts         │                                        │
│  │  │   ├── enrichment.ts   │                                        │
│  │  │   ├── filter.ts       │                                        │
│  │  │   └── clipboard.ts    │                                        │
│  │  └── types/              │                                        │
│  │      ├── ioc.ts          │                                        │
│  │      └── api.ts          │                                        │
│  └──────────────────────────┘                                        │
├─────────────────────────────────────────────────────────────────────┤
│                         Build Layer                                  │
│  ┌──────────────────────────┐  ┌──────────────────────────────┐     │
│  │  tools/esbuild           │  │  tools/tailwindcss           │     │
│  │  (standalone binary,     │  │  (standalone binary,         │     │
│  │   no Node.js)            │  │   no Node.js)                │     │
│  │                          │  │                              │     │
│  │  make js                 │  │  make css                    │     │
│  │  make js-watch           │  │  make css-watch              │     │
│  └──────────────────────────┘  └──────────────────────────────┘     │
├─────────────────────────────────────────────────────────────────────┤
│                        Distribution Layer                            │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │  app/static/dist/                                         │       │
│  │  ├── style.css        ← Tailwind output (committed)       │       │
│  │  ├── main.js          ← esbuild output (committed)        │       │
│  │  └── main.js.map      ← source map (dev builds only)      │       │
│  └──────────────────────────────────────────────────────────┘       │
├─────────────────────────────────────────────────────────────────────┤
│                         Flask Runtime                                │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │  Flask static file serving (url_for('static', ...))      │       │
│  │  app/templates/base.html:                                 │       │
│  │    <script src="{{ url_for('static',                      │       │
│  │      filename='dist/main.js') }}" defer></script>         │       │
│  └──────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Core Decision: esbuild as Standalone Binary

### Recommendation: esbuild, IIFE output, single bundle, committed dist

esbuild is the right choice because it mirrors the exact pattern already used by Tailwind CSS in this project:

| Dimension | Tailwind Standalone CLI | esbuild Standalone Binary |
|-----------|------------------------|--------------------------|
| Node.js required | No | No |
| Download method | GitHub releases binary | `curl https://esbuild.github.io/dl/v0.27.3 \| sh` |
| Install location | `tools/tailwindcss` | `tools/esbuild` |
| Makefile invocation | `$(TAILWIND) -i ... -o ...` | `$(ESBUILD) app/static/src/ts/main.ts ...` |
| Output committed | Yes (`dist/style.css`) | Yes (`dist/main.js`) |
| Watch mode | `--watch` | `--watch` |

**No npm. No node_modules. No package.json.** The project stays Node-free. esbuild is distributed as a precompiled Go binary for every platform. The download script at `https://esbuild.github.io/dl/v0.27.3` (or `latest`) is identical in concept to how a developer would `curl` the Tailwind binary from GitHub releases.

**Confidence: HIGH** — esbuild official docs confirm standalone binary installation via curl, version 0.27.3 is current (as of 2026-02-28). Source: [esbuild Getting Started](https://esbuild.github.io/getting-started/)

---

## Output Format Decision: IIFE vs ESM

### Recommendation: IIFE format (preserve existing script tag pattern)

The current `base.html` has:

```html
<script src="{{ url_for('static', filename='main.js') }}" defer></script>
```

**IIFE keeps this tag unchanged.** ESM would require `<script type="module" src="...">` which has different loading semantics (`defer` is implicit with modules but `async` behavior differs from `defer`).

| Criterion | IIFE (`--format=iife`) | ESM (`--format=esm`) |
|-----------|----------------------|---------------------|
| Script tag | `<script src="..." defer>` — unchanged | `<script type="module" src="...">` — changes template |
| CSP compatibility | `script-src 'self'` — OK (external file) | `script-src 'self'` — OK (external file) |
| Browser support | All modern browsers | Chrome 61+, Firefox 60+, Safari 11+ (fine for this tool) |
| Scope isolation | Implicit (IIFE wraps) | Implicit (module scope) |
| DOMContentLoaded | Keep existing guard in `main.ts` | `defer` is implicit |
| Code splitting | Not supported in IIFE | Supported (requires multiple `<script>` tags) |
| Flask template change | None | Must update `base.html` |

**IIFE is the right call** for this migration because:

1. The `base.html` script tag does not change — zero risk of breaking anything.
2. The existing code already uses an IIFE wrapper `(function() { ... }())`. The TypeScript source can drop that wrapper and let esbuild produce it.
3. Code splitting is unnecessary for 856 lines. A single bundle is the simplest correct answer.
4. CSP constraint is `script-src 'self'` — both formats are compatible since both are external files. This is not a differentiator.

**esbuild CLI flags for IIFE:**

```bash
tools/esbuild \
  app/static/src/ts/main.ts \
  --bundle \
  --format=iife \
  --outfile=app/static/dist/main.js \
  --platform=browser \
  --target=es2020
```

**Confidence: HIGH** — esbuild API docs confirm `--format=iife` is the browser default when bundling, and that it wraps output in an IIFE. Source: [esbuild API](https://esbuild.github.io/api/)

---

## Source File Location

### Recommendation: `app/static/src/ts/` — parallel to existing CSS source

```
app/static/
├── src/
│   ├── input.css              ← existing Tailwind source
│   └── ts/                    ← NEW: TypeScript source root
│       ├── main.ts            ← entry point (replaces main.js)
│       ├── modules/           ← split by feature
│       │   ├── form.ts        ← initSubmitButton, initAutoGrow, initModeToggle
│       │   ├── enrichment.ts  ← initEnrichmentPolling, renderEnrichmentResult, etc.
│       │   ├── filter.ts      ← initFilterBar, initScrollAwareFilterBar
│       │   ├── clipboard.ts   ← initCopyButtons, writeToClipboard, fallbackCopy
│       │   └── export.ts      ← initExportButton
│       └── types/             ← shared TypeScript interfaces
│           ├── ioc.ts         ← IocType, IocVerdict, IocCard types
│           └── api.ts         ← EnrichmentResult, EnrichmentStatus API shapes
├── dist/
│   ├── style.css              ← Tailwind output (existing)
│   ├── main.js                ← esbuild output (replaces root main.js)
│   └── main.js.map            ← source map (dev builds)
├── fonts/                     ← existing
├── images/                    ← existing
├── vendor/                    ← existing (if any)
└── main.js                    ← DELETED after migration (moved to dist/)
```

**Rationale for `src/ts/` placement:**

- Consistent with `src/input.css` — all build sources live under `src/`
- TypeScript files are never served directly by Flask (no accidental exposure)
- esbuild has a clear `src/ts/main.ts → dist/main.js` boundary that matches the CSS `src/input.css → dist/style.css` boundary

**Critical: the template script tag path must update** when moving from `main.js` to `dist/main.js`:

```html
<!-- BEFORE (base.html) -->
<script src="{{ url_for('static', filename='main.js') }}" defer></script>

<!-- AFTER (base.html) -->
<script src="{{ url_for('static', filename='dist/main.js') }}" defer></script>
```

This is the only template change required. The `defer` attribute stays. Flask serves `app/static/dist/main.js` from `url_for('static', filename='dist/main.js')` because `app/static/` is Flask's static folder root. No Flask configuration changes needed.

---

## Module Splitting Strategy

### Recommendation: Multiple source modules, single output bundle

The 856-line IIFE has 10 logical feature groups. Split them into TypeScript modules at the source level, but let esbuild bundle them into a single `dist/main.js` output. This provides:

- Maintainability: each module has one responsibility
- Type safety: shared interfaces imported explicitly (no global variable leakage)
- No template changes: single `<script>` tag in `base.html` remains

**Module boundaries (by functional group):**

| Module | Functions | Lines (~) |
|--------|-----------|-----------|
| `types/ioc.ts` | IocType, IocVerdict, VerdictLabel, ProviderCount types | ~30 |
| `types/api.ts` | EnrichmentResult, EnrichmentStatus API response shapes | ~20 |
| `modules/form.ts` | initSubmitButton, initAutoGrow, initModeToggle, updateSubmitLabel | ~120 |
| `modules/clipboard.ts` | initCopyButtons, writeToClipboard, fallbackCopy, showCopiedFeedback | ~70 |
| `modules/enrichment.ts` | initEnrichmentPolling, renderEnrichmentResult, updateCardVerdict, updateDashboardCounts, sortCardsBySeverity, all helpers | ~350 |
| `modules/filter.ts` | initFilterBar, initScrollAwareFilterBar | ~130 |
| `modules/export.ts` | initExportButton | ~40 |
| `modules/settings.ts` | initSettingsPage | ~20 |
| `modules/stagger.ts` | initCardStagger | ~10 |
| `main.ts` | init(), DOMContentLoaded guard | ~20 |

**`main.ts` entry point pattern:**

```typescript
import { initSubmitButton, initAutoGrow, initModeToggle } from './modules/form';
import { initCopyButtons } from './modules/clipboard';
import { initEnrichmentPolling } from './modules/enrichment';
import { initFilterBar, initScrollAwareFilterBar } from './modules/filter';
import { initExportButton } from './modules/export';
import { initSettingsPage } from './modules/settings';
import { initCardStagger } from './modules/stagger';

function init(): void {
    initSubmitButton();
    initModeToggle();
    initAutoGrow();
    initCopyButtons();
    initFilterBar();
    initEnrichmentPolling();
    initExportButton();
    initSettingsPage();
    initScrollAwareFilterBar();
    initCardStagger();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
```

esbuild bundles all imports into a single `dist/main.js` IIFE. No module loader runs in the browser. No `import` statements appear in the output.

---

## IIFE to ESM Transition Inside TypeScript Source

### Pattern: ES module syntax in source, IIFE in output

The current `main.js` uses a single-file IIFE. TypeScript source uses ES module syntax (`import`/`export`) because:

1. TypeScript's module system works with `import`/`export`
2. esbuild converts ES module imports into inlined bundle code at build time
3. The browser receives a single IIFE — it never sees `import` statements

**What changes in the TypeScript source vs the current JS IIFE:**

```typescript
// BEFORE (main.js — old IIFE pattern)
(function () {
  "use strict";
  var VERDICT_SEVERITY = [...];
  function verdictSeverity(verdict) { ... }
  function initSubmitButton() { ... }
  // ... 856 lines ...
  function init() { ... }
  if (document.readyState === "loading") { ... }
}());

// AFTER (modules/enrichment.ts — ES module)
import type { EnrichmentResult, IocVerdictEntry } from '../types/api';

const VERDICT_SEVERITY: string[] = ['error', 'no_data', 'clean', 'suspicious', 'malicious'];

export function verdictSeverity(verdict: string): number {
    const idx = VERDICT_SEVERITY.indexOf(verdict);
    return idx === -1 ? -1 : idx;
}

export function initEnrichmentPolling(): void {
    // ...
}
```

The IIFE wrapper is gone from source — esbuild adds it at bundle time via `--format=iife`.

**Shared constants across modules** — move to `types/` or a `constants.ts` file and import:

```typescript
// types/ioc.ts
export const VERDICT_SEVERITY = ['error', 'no_data', 'clean', 'suspicious', 'malicious'] as const;
export type VerdictSeverity = typeof VERDICT_SEVERITY[number];

export const VERDICT_LABELS: Record<string, string> = {
    malicious:  'MALICIOUS',
    suspicious: 'SUSPICIOUS',
    clean:      'CLEAN',
    no_data:    'NO DATA',
    error:      'ERROR',
};

export const IOC_PROVIDER_COUNTS: Record<string, number> = {
    ipv4: 2, ipv6: 2, domain: 2, url: 2,
    md5: 3, sha1: 3, sha256: 3,
};
```

---

## Makefile Integration

### Recommendation: Add `js` and `js-watch` targets parallel to `css` and `css-watch`

```makefile
# SentinelX — Build Tooling
TAILWIND := ./tools/tailwindcss
ESBUILD  := ./tools/esbuild

INPUT_CSS := app/static/src/input.css
OUTPUT_CSS := app/static/dist/style.css

INPUT_TS  := app/static/src/ts/main.ts
OUTPUT_JS := app/static/dist/main.js

PLATFORM := linux-x64

.PHONY: tailwind-install esbuild-install css css-watch js js-watch js-dev build typecheck

## Download Tailwind standalone CLI binary
tailwind-install:
	@mkdir -p tools
	curl -sLo $(TAILWIND) \
		https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.17/tailwindcss-$(PLATFORM)
	chmod +x $(TAILWIND)
	@echo "Tailwind CLI installed at $(TAILWIND)"

## Download esbuild standalone binary
esbuild-install:
	@mkdir -p tools
	curl -fsSL https://esbuild.github.io/dl/v0.27.3 | sh
	mv esbuild $(ESBUILD)
	@echo "esbuild installed at $(ESBUILD)"

## Build CSS (one-shot, minified)
css:
	$(TAILWIND) -i $(INPUT_CSS) -o $(OUTPUT_CSS) --minify

## Build CSS (watch mode)
css-watch:
	$(TAILWIND) -i $(INPUT_CSS) -o $(OUTPUT_CSS) --watch

## Build JS (one-shot, minified, no source map — production)
js:
	$(ESBUILD) $(INPUT_TS) \
		--bundle \
		--format=iife \
		--platform=browser \
		--target=es2020 \
		--minify \
		--outfile=$(OUTPUT_JS)

## Build JS (dev mode: source map, no minify)
js-dev:
	$(ESBUILD) $(INPUT_TS) \
		--bundle \
		--format=iife \
		--platform=browser \
		--target=es2020 \
		--sourcemap \
		--outfile=$(OUTPUT_JS)

## Build JS (watch mode, with source map)
js-watch:
	$(ESBUILD) $(INPUT_TS) \
		--bundle \
		--format=iife \
		--platform=browser \
		--target=es2020 \
		--sourcemap \
		--watch \
		--outfile=$(OUTPUT_JS)

## TypeScript type checking (requires tsc — run separately from esbuild)
typecheck:
	tsc --noEmit

## Full production build
build: css js
```

**Note on esbuild-install:** The `curl | sh` script auto-detects the platform and writes `esbuild` to the current directory. The `mv esbuild $(ESBUILD)` line moves it to `tools/`. This is equivalent to the Tailwind installation pattern. Alternatively, download the npm tarball directly:

```bash
# Platform-specific npm tarball (no npm required — it's just a .tgz)
curl -sLo /tmp/esbuild.tgz \
  https://registry.npmjs.org/@esbuild/linux-x64/-/linux-x64-0.27.3.tgz
tar -xzf /tmp/esbuild.tgz --strip-components=2 -C tools/ package/bin/esbuild
chmod +x tools/esbuild
```

The tarball approach is more explicit and version-pinned, matching the existing Tailwind install pattern exactly.

---

## tsconfig.json

### Recommendation: Strict, browser-targeted, esbuild-compatible

Place `tsconfig.json` at the project root (alongside `tailwind.config.js`):

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "isolatedModules": true,
    "skipLibCheck": true,
    "outDir": "app/static/dist",
    "rootDir": "app/static/src/ts"
  },
  "include": ["app/static/src/ts/**/*"],
  "exclude": ["node_modules"]
}
```

**Key settings explained:**

- `"target": "ES2020"` — esbuild respects this for syntax lowering. Covers all modern browsers including Chrome 80+, Firefox 78+, Safari 14+. Appropriate for analyst workstations.
- `"lib": ["ES2020", "DOM", "DOM.Iterable"]` — includes `document`, `querySelectorAll`, `NodeList` iteration types. Required because the code is heavily DOM-manipulating.
- `"module": "ESNext"` + `"moduleResolution": "Bundler"` — tells TypeScript the module format for source files. esbuild handles the actual bundling; this tells `tsc --noEmit` how to resolve imports.
- `"strict": true` — enables `strictNullChecks`, `noImplicitAny`, etc. This is the primary value of the migration.
- `"isolatedModules": true` — required by esbuild. esbuild processes each file independently (no cross-file type inference), so TypeScript must be configured to match. This catches patterns that would fail in esbuild (e.g., `export type` vs `export`).
- `"outDir"` — only used by `tsc --noEmit` / IDE tooling, not esbuild. esbuild's `--outfile` flag takes precedence.

**Confidence: HIGH** — tsconfig settings verified against TypeScript official docs and esbuild content-types docs confirming `isolatedModules` requirement.

---

## Source Map Strategy

### Recommendation: Source maps in dev builds, omitted from production

esbuild generates external source maps with `--sourcemap`, placing `main.js.map` alongside `main.js` in `app/static/dist/`.

```
app/static/dist/
├── main.js          ← contains `//# sourceMappingURL=main.js.map` comment
└── main.js.map      ← source map referencing app/static/src/ts/...
```

**Flask serves source maps automatically** — no configuration required. Flask's static file handler serves any file under `app/static/` at `url_for('static', filename=...)`. When the browser's DevTools loads `main.js`, it follows the `sourceMappingURL` comment and fetches `main.js.map` from `app/static/dist/main.js.map`. Flask serves this transparently.

**CSP impact:** Source map files are fetched by DevTools, not by the page itself. They are not constrained by `script-src`. No CSP changes needed.

**Workflow:**

- `make js-dev` — builds with `--sourcemap` for local debugging (no minification, readable output)
- `make js` — builds minified, no source map (committed to repo for production)
- `make js-watch` — watch mode with source maps for active development

**Whether to commit source maps:** Do NOT commit `main.js.map` to the repository. Source maps belong in dev builds only. Add to `.gitignore`:

```gitignore
app/static/dist/main.js.map
```

The committed `dist/main.js` is the minified production build. Source maps are regenerated locally during development via `make js-dev` or `make js-watch`.

---

## Integration Points

### New Files

| File | Purpose | Notes |
|------|---------|-------|
| `app/static/src/ts/main.ts` | TypeScript entry point | Replaces root `main.js` as source of truth |
| `app/static/src/ts/modules/form.ts` | Form/textarea/toggle init functions | |
| `app/static/src/ts/modules/enrichment.ts` | Polling loop, result rendering | Largest module (~350 lines) |
| `app/static/src/ts/modules/filter.ts` | Filter bar, scroll-aware bar | |
| `app/static/src/ts/modules/clipboard.ts` | Copy buttons, clipboard API | |
| `app/static/src/ts/modules/export.ts` | Export button handler | |
| `app/static/src/ts/modules/settings.ts` | Settings page API key toggle | |
| `app/static/src/ts/modules/stagger.ts` | Card stagger animation index | |
| `app/static/src/ts/types/ioc.ts` | IocType, VerdictSeverity, VERDICT_LABELS, IOC_PROVIDER_COUNTS | Shared constants and types |
| `app/static/src/ts/types/api.ts` | EnrichmentResult, EnrichmentStatus API shapes | Typed API response interfaces |
| `tsconfig.json` | TypeScript compiler config for type checking | At project root |
| `tools/esbuild` | esbuild standalone binary | Parallel to `tools/tailwindcss` |
| `app/static/dist/main.js` | esbuild output (new location) | Committed; replaces root `main.js` |

### Modified Files

| File | Change | Risk |
|------|--------|------|
| `app/templates/base.html` | Script tag: `'main.js'` → `'dist/main.js'` | Low — single line change |
| `Makefile` | Add `esbuild-install`, `js`, `js-dev`, `js-watch`, `typecheck` targets; update `build` to include `js` | Low — additive |
| `tailwind.config.js` | Update `content` to include `.ts` files in addition to `.js` | Low — Tailwind scans for utility classes |
| `.gitignore` | Add `app/static/dist/main.js.map` | Low |

### Deleted Files

| File | Reason |
|------|--------|
| `app/static/main.js` | Replaced by compiled `app/static/dist/main.js`; TypeScript source becomes the canonical file |

### Tailwind config: scan TypeScript source

The existing `tailwind.config.js` content scan includes `app/static/**/*.js`. After migration, TypeScript source files must also be scanned so Tailwind can extract any utility classes referenced in TypeScript strings:

```javascript
content: [
  "./app/templates/**/*.html",
  "./app/static/src/ts/**/*.ts",  // NEW: scan TypeScript source
  // Remove: "./app/static/**/*.js" (or keep for backward compat)
  "./app/static/dist/main.js",    // scan compiled output for dynamic classes
],
```

**Important:** The Tailwind safelist in `tailwind.config.js` (verdict/type/filter dynamic class names) must remain unchanged. These dynamic classes are applied by JavaScript at runtime; they are not statically analyzable. The safelist already handles this correctly.

---

## Data Flow: TypeScript Module to Browser

```
Developer edits app/static/src/ts/modules/enrichment.ts
    ↓
make js-watch detects change
    ↓
tools/esbuild bundles all modules → app/static/dist/main.js (IIFE)
    ↓
Browser requests page → Flask serves base.html
    ↓
base.html: <script src=".../dist/main.js" defer></script>
    ↓
Browser downloads and executes dist/main.js
    ↓
IIFE self-executes → calls init() on DOMContentLoaded
    ↓
init() calls all module init functions
```

**Type checking (separate from build):**

```
Developer runs: make typecheck
    ↓
tsc --noEmit reads tsconfig.json
    ↓
Checks all .ts files for type errors
    ↓
Reports errors (does NOT produce output files)
    ↓
Errors fixed in TypeScript source
    ↓
make js (or make js-watch) rebuilds the bundle
```

---

## Architectural Patterns

### Pattern 1: Module-per-Feature with Shared Types

**What:** Each logical feature area (enrichment polling, filter bar, clipboard) gets its own TypeScript module. Shared data structures and constants live in `types/`.

**When to use:** Always for this migration. The existing IIFE has 10 clear functional groupings — these become modules.

**Trade-offs:** Slightly more files to navigate, but each file has one purpose and is independently testable. esbuild bundles them with zero overhead.

**Example:**

```typescript
// types/api.ts — shared API response shapes
export interface EnrichmentResult {
    type: 'result' | 'error';
    ioc_value: string;
    provider: string;
    verdict?: string;
    detection_count?: number;
    total_engines?: number;
    scan_date?: string;
    error?: string;
}

export interface EnrichmentStatus {
    complete: boolean;
    done: number;
    total: number;
    results: EnrichmentResult[];
}
```

```typescript
// modules/enrichment.ts — imports the shared types
import type { EnrichmentResult, EnrichmentStatus } from '../types/api';
import { VERDICT_SEVERITY, VERDICT_LABELS, IOC_PROVIDER_COUNTS } from '../types/ioc';
```

### Pattern 2: Null-Safe DOM Element Access

**What:** Every `document.getElementById()` call returns `HTMLElement | null`. TypeScript enforces checking before use.

**When to use:** Always — this is the primary safety improvement over the current JS where `if (!form) return;` is a manual convention.

**Example:**

```typescript
// Pattern: early return with null guard (mirrors existing JS convention, now enforced by compiler)
function initSubmitButton(): void {
    const form = document.getElementById('analyze-form') as HTMLFormElement | null;
    if (!form) return;

    const textarea = document.getElementById('ioc-text') as HTMLTextAreaElement | null;
    const submitBtn = document.getElementById('submit-btn') as HTMLButtonElement | null;
    if (!textarea || !submitBtn) return;

    // TypeScript now knows textarea and submitBtn are non-null here
    textarea.addEventListener('input', () => {
        submitBtn.disabled = textarea.value.trim().length === 0;
    });
}
```

### Pattern 3: Typed Fetch with Interface Assertions

**What:** The enrichment polling `fetch('/enrichment/status/' + jobId)` currently uses `data.results` with no type check. TypeScript interfaces enforce the expected API shape.

**When to use:** Any fetch() call that parses JSON.

**Trade-offs:** Does not validate at runtime — TypeScript types are erased. The existing pattern of checking `if (!data) return` is preserved. For a local tool, full runtime validation (zod) is overkill.

**Example:**

```typescript
import type { EnrichmentStatus } from '../types/api';

async function pollStatus(jobId: string): Promise<EnrichmentStatus | null> {
    const resp = await fetch(`/enrichment/status/${jobId}`);
    if (!resp.ok) return null;
    return resp.json() as Promise<EnrichmentStatus>;
}
```

---

## Anti-Patterns

### Anti-Pattern 1: ESM Output Format

**What people do:** Use `--format=esm` because "ES modules are modern."

**Why it's wrong for this project:** ESM requires `<script type="module">` in `base.html`, changing the loading behavior. `defer` is already implicit on modules, but `async` is not — the behavior difference is subtle and easy to get wrong. More importantly, ESM is unnecessary when there is a single bundle and no dynamic `import()` needed.

**Do this instead:** `--format=iife`. Preserves the existing script tag. Matches browser behavior the current code relies on.

### Anti-Pattern 2: Separate Output Files per Module

**What people do:** Use `--outdir` with multiple entry points, generating `dist/form.js`, `dist/enrichment.js`, etc.

**Why it's wrong:** Requires multiple `<script>` tags in `base.html` in the correct order. Load order errors become a runtime problem. Flask caching/fingerprinting becomes more complex.

**Do this instead:** Single entry point (`main.ts`) that imports all modules. Single `--outfile=dist/main.js` output. esbuild inlines all imports — no network overhead.

### Anti-Pattern 3: Type Assertions Replacing Guards

**What people do:** Use `as HTMLElement` to silence null errors without guarding:

```typescript
// WRONG: crashes at runtime if element is absent
const btn = document.getElementById('submit-btn') as HTMLButtonElement;
btn.disabled = true; // TypeError: Cannot set property 'disabled' of null
```

**Why it's wrong:** Type assertions bypass TypeScript's null safety. The existing JS already has `if (!submitBtn) return;` guards that prevent this — TypeScript should enforce them, not bypass them.

**Do this instead:**

```typescript
// CORRECT: guard + assertion only when known non-null
const btn = document.getElementById('submit-btn') as HTMLButtonElement | null;
if (!btn) return;
btn.disabled = true; // safe
```

### Anti-Pattern 4: Running `tsc` to Emit JS (Instead of esbuild)

**What people do:** Configure `tsc` to compile TypeScript to JavaScript (remove `"noEmit"`, set `"outDir"`).

**Why it's wrong:** `tsc` is 10-100x slower than esbuild. It cannot bundle. It produces one output file per input file, requiring a separate bundling step. esbuild handles both transpilation and bundling in one pass.

**Do this instead:** Use `tsc --noEmit` for type checking ONLY. Use esbuild for transpilation and bundling.

### Anti-Pattern 5: Committing Source Maps

**What people do:** Commit `main.js.map` alongside `main.js`.

**Why it's wrong for this project:** Source maps expose the TypeScript source structure in production. For a security tool, this is a minor information disclosure. More practically, source maps are large and change on every rebuild — they create noise in git history.

**Do this instead:** Add `app/static/dist/main.js.map` to `.gitignore`. Generate source maps locally during development with `make js-dev` or `make js-watch`.

---

## Build Order for v3.0 Migration

The TypeScript migration has a clear dependency chain that determines implementation order:

```
Phase 1: Infrastructure
    ├── Download tools/esbuild binary
    ├── Add tsconfig.json
    ├── Update Makefile (js, js-dev, js-watch, typecheck, esbuild-install targets)
    ├── Update .gitignore (main.js.map)
    └── Verify: make js compiles an empty main.ts to dist/main.js without errors

Phase 2: Type Definitions
    ├── Create types/ioc.ts (VERDICT_SEVERITY, VERDICT_LABELS, IOC_PROVIDER_COUNTS, type aliases)
    ├── Create types/api.ts (EnrichmentResult, EnrichmentStatus interfaces)
    └── Verify: tsc --noEmit passes on types alone

Phase 3: Module Extraction (one module at a time, inside-out order)
    ├── types/ioc.ts and types/api.ts (no deps — do first)
    ├── modules/clipboard.ts (depends only on DOM types)
    ├── modules/stagger.ts (no cross-module deps)
    ├── modules/settings.ts (no cross-module deps)
    ├── modules/form.ts (no cross-module deps)
    ├── modules/export.ts (depends on clipboard)
    ├── modules/filter.ts (no cross-module deps)
    └── modules/enrichment.ts (depends on types/ioc, types/api — do last, largest)

Phase 4: Entry Point and Template Update
    ├── Create main.ts importing all modules
    ├── Update base.html script tag: 'main.js' → 'dist/main.js'
    ├── Verify: make js succeeds
    ├── Verify: browser loads page, all features work
    ├── Delete app/static/main.js (old file)
    └── Update tailwind.config.js content paths

Phase 5: Type Hardening
    ├── Run tsc --noEmit, fix all type errors
    ├── Add strictest DOM type annotations
    └── Verify: 0 TypeScript errors, all E2E tests pass
```

**Why this order:** Types before modules (modules depend on types). Simple modules before complex ones. Entry point last (it imports all modules — any module error blocks entry point). Template update after bundle is confirmed working.

---

## Scaling Considerations

This is a local tool with one user. Scaling is not a concern. The architecture discussion is about maintainability, not performance.

| Concern | Current (vanilla JS) | After TypeScript Migration |
|---------|---------------------|--------------------------|
| Adding a new feature | Edit single 856-line file | Add to relevant module, import in main.ts |
| Finding a bug in enrichment | Grep 856 lines | Open modules/enrichment.ts directly |
| API shape changes | Update JS, hope nothing breaks | Update types/api.ts, tsc catches all callers |
| New developer onboarding | Read entire IIFE | Read module by module |
| Build time | N/A (no build) | ~100ms for esbuild full rebuild |
| Type errors caught | Only runtime | At development time via tsc |

---

## Sources

- [esbuild Getting Started](https://esbuild.github.io/getting-started/) — standalone binary download via curl, platform support, latest version 0.27.3 (HIGH confidence — official docs, WebFetch verified)
- [esbuild API](https://esbuild.github.io/api/) — `--format=iife`, `--bundle`, `--outfile`, `--sourcemap`, `--platform`, `--target` flags (HIGH confidence — official docs, WebFetch verified)
- [esbuild Content Types](https://esbuild.github.io/content-types/) — TypeScript loader behavior, `isolatedModules` requirement, no type checking by design (HIGH confidence — official docs, WebFetch verified)
- [TypeScript TSConfig Reference](https://www.typescriptlang.org/tsconfig/) — `lib`, `target`, `moduleResolution: "Bundler"`, `isolatedModules` options (HIGH confidence — official docs)
- [esbuild FAQ](https://esbuild.github.io/faq/) — why no type checking, `tsc --noEmit` as the recommended pattern (HIGH confidence — official docs)
- esbuild IIFE format — `script-src 'self'` CSP compatibility: both IIFE and ESM work with `script-src 'self'` as external files; confirmed via MDN CSP docs (HIGH confidence)
- WebSearch: esbuild 0.27.3 is latest version as of 2026-02-28 (MEDIUM confidence — multiple sources agree)
- Flask static file serving — Flask automatically serves all files under `app/static/` at `/static/` URL prefix; `url_for('static', filename='dist/main.js')` works without configuration (HIGH confidence — Flask 3.1 docs, confirmed from existing project behavior)

---

*Architecture research for: TypeScript build pipeline integration — SentinelX v3.0*
*Researched: 2026-02-28*
