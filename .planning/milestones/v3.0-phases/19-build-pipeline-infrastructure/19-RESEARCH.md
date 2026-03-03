# Phase 19: Build Pipeline Infrastructure - Research

**Researched:** 2026-02-28
**Domain:** esbuild standalone binary, TypeScript tsc, Makefile integration, Flask static serving
**Confidence:** HIGH

## Summary

Phase 19 establishes the TypeScript build pipeline without writing any TypeScript yet. The deliverables are purely infrastructure: a pinned esbuild binary in `tools/`, five Makefile targets (`js`, `js-dev`, `js-watch`, `typecheck`, updated `build`), a `tsconfig.json` for type-checking only, the `app/static/src/ts/` source directory, a placeholder `main.ts` entry point, a `base.html` script tag update, and `.gitignore` updates for source maps. The existing `app/static/main.js` remains in place alongside the new pipeline — no migration happens in this phase. Success is verified by the CSP regression test still passing against a minimal placeholder bundle.

The esbuild binary installation mirrors the existing Tailwind CLI pattern exactly: download a versioned `.tgz` from the npm registry (not via `npm install`), extract the native binary, and place it at `tools/esbuild`. Node.js is available on the developer machine (via nvm) and is used only to install TypeScript globally or locally as a dev tool for `tsc --noEmit`. No `node_modules` directory is added to the project root. The `tools/` directory is already in `.gitignore`, so the esbuild binary is not committed to git.

The primary risks at this phase are: (1) the wrong esbuild binary platform being downloaded (Linux x64 matches the WSL2 environment), (2) the `base.html` script tag update failing the CSP test if the compiled bundle is not present before tests run, and (3) `tsconfig.json` misconfiguration that causes `tsc --noEmit` to fail on valid code in Phase 20. All three are preventable with the patterns documented here.

**Primary recommendation:** Download esbuild from the npm registry tgz (the same download mechanism as Tailwind), write all five Makefile targets in one commit, wire `base.html` to `dist/main.js`, and verify CSP passes with the placeholder bundle before closing the phase.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BUILD-01 | esbuild is installed as a standalone binary (no Node.js/npm required at runtime) with a pinned version | tgz download from npm registry extracts native binary; see Installation section |
| BUILD-02 | `make js` compiles TypeScript source to a single IIFE bundle at `app/static/dist/main.js` | `--format=iife --bundle --minify --platform=browser --target=es2022 --outfile=` flags; see Code Examples |
| BUILD-03 | `make js-watch` runs esbuild in watch mode for development | `--watch` flag keeps process running, logs on recompile; see Watch Mode section |
| BUILD-04 | `make js-dev` produces a bundle with inline source maps for browser debugging | `--sourcemap=inline` embeds base64-encoded map; Sources panel shows `.ts` files; see Source Maps section |
| BUILD-05 | `make typecheck` runs `tsc --noEmit` to validate types without producing output | `tsc --noEmit` with tsconfig.json; see TypeScript section |
| BUILD-06 | `make build` target runs both CSS and JS builds | Makefile dependency: `build: css js`; see Makefile Patterns section |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| esbuild | 0.27.3 | TypeScript bundler + minifier, IIFE output | Standalone binary, no Node.js runtime, ~100ms builds, CSP-safe IIFE output |
| TypeScript | 5.8.x (pin to 5.8) | Type checking via `tsc --noEmit` | Provides lib.dom.d.ts; 6.0 is still in beta as of Feb 2026 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| GNU Make | system | Build orchestration | Already used for CSS pipeline; consistent pattern |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| npm registry tgz download | `curl https://esbuild.github.io/dl/v0.27.3 \| sh` | The official `dl.sh` approach is simpler but requires platform detection logic; the tgz approach mirrors the existing Tailwind download pattern in the Makefile exactly |
| esbuild standalone binary | Webpack, Vite, Rollup | These inject dynamic code evaluation that breaks CSP; esbuild IIFE output has no eval, no dynamic imports at runtime |
| TypeScript via npm | TypeScript via binary download | No standalone tsc binary available; npm install is acceptable for dev-only tool |

**Installation:**

For esbuild (Linux x64 — matches WSL2 environment):
```bash
# One-time developer setup (mirrors tailwind-install Makefile target)
curl -O https://registry.npmjs.org/@esbuild/linux-x64/-/linux-x64-0.27.3.tgz
tar xzf ./linux-x64-0.27.3.tgz
mv ./package/bin/esbuild ./tools/esbuild
chmod +x ./tools/esbuild
rm -rf ./linux-x64-0.27.3.tgz ./package
```

For TypeScript (dev machine only):
```bash
npm install -g typescript@5.8
# or local dev install if project root gets a package.json
npm install --save-dev typescript@5.8
```

The project currently has no `package.json` at root — TypeScript can be installed globally for development without adding one. If a `package.json` is added, it must be committed but `node_modules/` stays gitignored.

## Architecture Patterns

### Recommended Project Structure
```
tools/
├── tailwindcss          # existing Tailwind standalone CLI
└── esbuild              # new esbuild standalone binary (gitignored)

app/static/
├── src/
│   ├── input.css        # existing Tailwind source
│   └── ts/              # new TypeScript source root
│       └── main.ts      # placeholder entry point (Phase 19 only)
├── dist/
│   ├── style.css        # existing generated CSS
│   └── main.js          # generated JS bundle (committed after build)
└── main.js              # original vanilla JS (still present in Phase 19!)

tsconfig.json            # project root — type checking config
```

The critical detail: `app/static/main.js` (original) and `app/static/dist/main.js` (new bundle) coexist during Phase 19. `base.html` is updated to reference `dist/main.js` in this phase. The original `main.js` is deleted in Phase 22 only.

### Pattern 1: Makefile IIFE Build Target (js)
**What:** Production build — minified IIFE, no source maps
**When to use:** CI, deployment, `make build`
```makefile
ESBUILD  := ./tools/esbuild
JS_ENTRY := app/static/src/ts/main.ts
JS_OUT   := app/static/dist/main.js

js:
	$(ESBUILD) $(JS_ENTRY) \
		--bundle \
		--format=iife \
		--platform=browser \
		--target=es2022 \
		--minify \
		--outfile=$(JS_OUT)
```

### Pattern 2: Makefile Dev Build Target (js-dev)
**What:** Development build — unminified, inline source maps
**When to use:** Local debugging, DevTools breakpoints in TypeScript source
```makefile
js-dev:
	$(ESBUILD) $(JS_ENTRY) \
		--bundle \
		--format=iife \
		--platform=browser \
		--target=es2022 \
		--sourcemap=inline \
		--outfile=$(JS_OUT)
```
`--sourcemap=inline` embeds the full source map as a base64 data URL at the end of the bundle. The browser DevTools Sources panel shows the original `.ts` files, not compiled JavaScript. Source map files (`main.js.map`) are NOT written to disk with `--sourcemap=inline`.

### Pattern 3: Makefile Watch Target (js-watch)
**What:** Continuous rebuild — keeps process alive, recompiles on file change
**When to use:** Active development session
```makefile
js-watch:
	$(ESBUILD) $(JS_ENTRY) \
		--bundle \
		--format=iife \
		--platform=browser \
		--target=es2022 \
		--sourcemap=inline \
		--watch \
		--outfile=$(JS_OUT)
```
esbuild watch mode uses file system polling, scanning a random subset of files every ~2 seconds. In practice for a small project, recompilation after change detection is under 200ms. The process logs `[watch] build finished, watching for changes...` on startup and logs each rebuild. It stays alive until Ctrl+C or stdin is closed.

### Pattern 4: Makefile Typecheck Target
**What:** TypeScript type validation only — no output files
**When to use:** CI gate, pre-commit, manual verification
```makefile
typecheck:
	tsc --noEmit
```
Reads `tsconfig.json` from the project root. Exits 0 on success, non-zero with type errors. esbuild never type-checks; `make typecheck` is the only mechanism that validates types.

### Pattern 5: Updated build Target
**What:** Full build — CSS + JS in parallel via Make
**When to use:** CI, deployment
```makefile
build: css js
```
Make runs `css` and `js` targets. They are independent (different input/output files) so they could run in parallel with `make -j2 build`. Sequential execution is fine for this project size.

### Pattern 6: Makefile esbuild-install Target
**What:** One-time developer setup for esbuild binary
**When to use:** First-time setup, CI provisioning
```makefile
ESBUILD_VERSION := 0.27.3
ESBUILD_PLATFORM := linux-x64

esbuild-install:
	@mkdir -p tools
	curl -sLo /tmp/esbuild.tgz \
		https://registry.npmjs.org/@esbuild/$(ESBUILD_PLATFORM)/-/$(ESBUILD_PLATFORM)-$(ESBUILD_VERSION).tgz
	tar xzf /tmp/esbuild.tgz -C /tmp
	mv /tmp/package/bin/esbuild $(ESBUILD)
	chmod +x $(ESBUILD)
	rm -rf /tmp/esbuild.tgz /tmp/package
	@echo "esbuild $(ESBUILD_VERSION) installed at $(ESBUILD)"
```

### Pattern 7: Placeholder main.ts Entry Point
**What:** Minimal TypeScript file that produces a CSP-safe, functionally-neutral IIFE bundle
**When to use:** Phase 19 only — before any real TypeScript is written
```typescript
// app/static/src/ts/main.ts
// Phase 19 placeholder — replaced in Phases 21-22
// This file exists to verify the build pipeline only.
// All functionality remains in app/static/main.js until Phase 22.

export {};
```
The `export {}` makes this an ES module (required for TypeScript with `isolatedModules: true`). esbuild bundles it into an empty IIFE. The CSP test verifies the Flask response headers, not the JS file content, so an empty bundle passes.

### Pattern 8: tsconfig.json for Browser + esbuild
**What:** Strict, browser-only configuration compatible with esbuild's transpilation model
```json
{
  "compilerOptions": {
    "target": "es2022",
    "lib": ["es2022", "dom", "dom.iterable"],
    "module": "es2022",
    "moduleResolution": "Bundler",
    "strict": true,
    "noEmit": true,
    "isolatedModules": true,
    "noUncheckedIndexedAccess": true,
    "types": [],
    "skipLibCheck": false
  },
  "include": ["app/static/src/ts/**/*.ts"]
}
```
Key options:
- `"noEmit": true` — tsc never writes output files; esbuild handles transpilation
- `"isolatedModules": true` — required by esbuild; prevents constructs that break single-file compilation
- `"moduleResolution": "Bundler"` — esbuild compatibility mode
- `"types": []` — prevents accidental `@types/node` resolution from Node.js being on PATH
- `"lib": ["es2022", "dom", "dom.iterable"]` — provides DOM types without `@types` packages

### Pattern 9: base.html Script Tag Update
**What:** Change Flask url_for from `main.js` to `dist/main.js`
**Current (line 35):**
```html
<script src="{{ url_for('static', filename='main.js') }}" defer></script>
```
**Updated:**
```html
<script src="{{ url_for('static', filename='dist/main.js') }}" defer></script>
```
No other template changes needed. CSP is set in the Flask app (not `base.html`), so this change does not affect CSP headers.

### Anti-Patterns to Avoid
- **`--format=esm`**: ES module format would require `<script type="module">`, which conflicts with `defer` and changes how the bundle loads. The existing `<script defer>` tag requires IIFE format.
- **`--sourcemap` (external)**: Creates a `main.js.map` file that Flask would serve. Use `--sourcemap=inline` for dev builds to keep source maps out of the file system. External source maps should be gitignored if ever created.
- **Installing TypeScript globally before confirming npm availability**: The dev machine has npm via nvm; confirm before adding a project `package.json`.
- **Adding `"type": "module"` to package.json**: If a `package.json` is created at project root, do NOT add `"type": "module"` — this changes how Node.js (including tsc) resolves modules and could conflict with `tailwind.config.js` (CommonJS).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TypeScript transpilation | Custom regex stripping of type annotations | esbuild `--bundle` with `.ts` entry point | esbuild handles JSX, decorators, type imports correctly; regex breaks on template literals, generics |
| Type checking | Parsing TypeScript AST manually | `tsc --noEmit` | TypeScript's type checker is the authoritative implementation |
| Source map generation | Manual base64 encoding of source positions | esbuild `--sourcemap=inline` | Source map format (v3 spec) has corner cases in Unicode, line mapping |
| Binary download | OS detection shell script | Fixed platform + version in Makefile | WSL2 is always linux-x64; platform detection adds complexity for one environment |

**Key insight:** The entire value of this phase comes from using the right tools for each job (esbuild for speed/bundling, tsc for correctness) rather than over-engineering the pipeline.

## Common Pitfalls

### Pitfall 1: Wrong Platform Binary
**What goes wrong:** Downloading `darwin-x64` or `linux-arm64` instead of `linux-x64` for WSL2
**Why it happens:** Copy-pasting from macOS documentation or generic install scripts
**How to avoid:** Hardcode `ESBUILD_PLATFORM := linux-x64` in Makefile; don't use runtime platform detection
**Warning signs:** `Exec format error` when running `./tools/esbuild`

### Pitfall 2: CSP Test Fails Because dist/main.js Doesn't Exist
**What goes wrong:** `test_csp_header_exact_match` passes (it only checks response headers), but other tests that load the page in a browser fail because `url_for('static', filename='dist/main.js')` returns a 404
**Why it happens:** `base.html` updated but `make js` not run before E2E tests
**How to avoid:** Run `make js` as part of CI before pytest; commit the placeholder `dist/main.js` bundle to git so it's available without running the build
**Warning signs:** E2E tests fail with JavaScript console errors about missing script

### Pitfall 3: `tsc --noEmit` Fails on Empty File
**What goes wrong:** A completely empty `main.ts` fails with `error TS1208: ... cannot be compiled under '--isolatedModules'`
**Why it happens:** `isolatedModules: true` requires each file to be a proper module (must have at least one import/export)
**How to avoid:** Use `export {};` as the minimal valid module statement in the placeholder `main.ts`
**Warning signs:** `make typecheck` exits non-zero with isolatedModules error

### Pitfall 4: `types: []` Not Set — Node.js Types Leak In
**What goes wrong:** `ReturnType<typeof setTimeout>` resolves to `NodeJS.Timeout` (not `number`) because Node.js is on PATH and tsc auto-discovers `@types/node`
**Why it happens:** tsc scans the PATH when `types` is omitted from tsconfig
**How to avoid:** Set `"types": []` in tsconfig.json; this prevents ALL implicit `@types` resolution
**Warning signs:** Type errors in Phase 21 timer code that reference `NodeJS.Timeout`; or conversely, existing `setTimeout` in test files type-checks to `NodeJS.Timeout` silently

### Pitfall 5: `tailwind.config.js` Missing `.ts` in content Paths
**What goes wrong:** Tailwind purges classes added in TypeScript files because `tailwind.config.js` `content` array only scans `.js` files
**Why it happens:** Current config is `"./app/static/**/*.js"` — new `.ts` source files are not included
**How to avoid:** Add `"./app/static/src/ts/**/*.ts"` to `content` array in `tailwind.config.js` NOW (Phase 19), before any TypeScript files use dynamic class strings
**Warning signs:** Classes added in `.ts` files (verdict labels, filter classes) missing from the built CSS in later phases

### Pitfall 6: Source Map Files Committed to Git
**What goes wrong:** `make js-dev` or `make js-watch` creates `main.js.map` and it gets accidentally committed
**Why it happens:** `--sourcemap=inline` doesn't create a file, but if someone accidentally uses `--sourcemap` (external), a `.map` file is created
**How to avoid:** Add `app/static/dist/*.map` to `.gitignore`; use `--sourcemap=inline` exclusively in Makefile dev targets
**Warning signs:** `git status` shows `app/static/dist/main.js.map` as untracked

### Pitfall 7: `moduleResolution: "Bundler"` Breaks tsc on Older TypeScript
**What goes wrong:** `"moduleResolution": "Bundler"` was added in TypeScript 5.0; older versions error on it
**Why it happens:** System TypeScript version predates 5.0
**How to avoid:** Pin `typescript@5.8` explicitly; verify `tsc --version` matches before running `make typecheck`
**Warning signs:** `error TS5023: Unknown compiler option 'moduleResolution'` or similar

## Code Examples

Verified patterns from official sources:

### Complete Makefile Addition
```makefile
# SentinelX — Build Tooling
# Requires: tools/tailwindcss (standalone CLI binary)
#           tools/esbuild     (standalone CLI binary)

TAILWIND         := ./tools/tailwindcss
ESBUILD          := ./tools/esbuild
INPUT            := app/static/src/input.css
OUTPUT           := app/static/dist/style.css
JS_ENTRY         := app/static/src/ts/main.ts
JS_OUT           := app/static/dist/main.js
PLATFORM         := linux-x64
ESBUILD_VERSION  := 0.27.3

.PHONY: tailwind-install esbuild-install css css-watch js js-dev js-watch typecheck build

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
	curl -sLo /tmp/esbuild.tgz \
		https://registry.npmjs.org/@esbuild/$(PLATFORM)/-/$(PLATFORM)-$(ESBUILD_VERSION).tgz
	tar xzf /tmp/esbuild.tgz -C /tmp
	mv /tmp/package/bin/esbuild $(ESBUILD)
	chmod +x $(ESBUILD)
	rm -rf /tmp/esbuild.tgz /tmp/package
	@echo "esbuild $(ESBUILD_VERSION) installed at $(ESBUILD)"

## Build CSS (one-shot)
css:
	$(TAILWIND) -i $(INPUT) -o $(OUTPUT) --minify

## Build CSS (watch mode for development)
css-watch:
	$(TAILWIND) -i $(INPUT) -o $(OUTPUT) --watch

## Build JS bundle (production — minified IIFE, no source maps)
js:
	$(ESBUILD) $(JS_ENTRY) \
		--bundle \
		--format=iife \
		--platform=browser \
		--target=es2022 \
		--minify \
		--outfile=$(JS_OUT)

## Build JS bundle (development — unminified, inline source maps)
js-dev:
	$(ESBUILD) $(JS_ENTRY) \
		--bundle \
		--format=iife \
		--platform=browser \
		--target=es2022 \
		--sourcemap=inline \
		--outfile=$(JS_OUT)

## Build JS bundle (watch mode — recompiles on file change)
js-watch:
	$(ESBUILD) $(JS_ENTRY) \
		--bundle \
		--format=iife \
		--platform=browser \
		--target=es2022 \
		--sourcemap=inline \
		--watch \
		--outfile=$(JS_OUT)

## Type-check TypeScript without emitting output
typecheck:
	tsc --noEmit

## Full build (CSS + JS)
build: css js
```

Source: [esbuild API](https://esbuild.github.io/api/) — flags verified; [esbuild Getting Started](https://esbuild.github.io/getting-started/) — tgz download URL pattern verified

### Complete tsconfig.json
```json
{
  "compilerOptions": {
    "target": "es2022",
    "lib": ["es2022", "dom", "dom.iterable"],
    "module": "es2022",
    "moduleResolution": "Bundler",
    "strict": true,
    "noEmit": true,
    "isolatedModules": true,
    "noUncheckedIndexedAccess": true,
    "types": [],
    "skipLibCheck": false
  },
  "include": ["app/static/src/ts/**/*.ts"]
}
```

Source: [TypeScript TSConfig Reference](https://www.typescriptlang.org/tsconfig/) — all options verified; `moduleResolution: "Bundler"` documented for TypeScript 5.0+

### Placeholder main.ts
```typescript
// app/static/src/ts/main.ts
// Phase 19 placeholder — full implementation in Phases 21-22.
// This entry point verifies the build pipeline only.

export {};
```

### Updated .gitignore entries
```
# Source maps (generated locally via make js-dev or js-watch)
app/static/dist/*.map
```

### Updated tailwind.config.js content paths
```javascript
content: [
  "./app/templates/**/*.html",
  "./app/static/**/*.js",
  "./app/static/src/ts/**/*.ts",   // add this line
],
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Webpack for TypeScript bundling | esbuild for bundling + tsc for type checking | 2022-2023 | ~100x faster builds; separation of concerns |
| `moduleResolution: "node"` | `moduleResolution: "Bundler"` | TypeScript 5.0 (2023) | Correct module resolution for bundler workflows |
| TypeScript as a build step (tsc emits JS) | TypeScript as a type checker only (tsc --noEmit) | 2022+ | esbuild handles transpilation faster; tsc stays focused on types |
| `es5` target for broad compatibility | `es2022` target | 2022+ | Modern browsers support es2022; no need for legacy polyfills |

**Deprecated/outdated:**
- `"moduleResolution": "classic"`: The original TypeScript resolution strategy; replaced by `"node"` and now `"Bundler"` for bundler workflows
- `tsc` for bundling: TypeScript compiler can still emit JS, but esbuild is 10-100x faster and handles the same transformations
- TypeScript 6.0: Still in beta as of Feb 2026; do not use

## Open Questions

1. **Does the project need a package.json at root?**
   - What we know: npm is available on the dev machine (nvm); TypeScript can be installed globally or locally; no `package.json` exists at project root currently
   - What's unclear: Whether global TypeScript install (`npm install -g typescript@5.8`) is sufficient, or whether a project-level `package.json` with `devDependencies` is preferred for reproducibility
   - Recommendation: Start with a minimal `package.json` with only `devDependencies: { "typescript": "^5.8.0" }` — this documents the TypeScript dependency explicitly without adding `node_modules` to git (already in `.gitignore`)

2. **ESBUILD_PLATFORM hardcoded vs. detected**
   - What we know: Current environment is WSL2 linux-x64; Tailwind uses `PLATFORM := linux-x64` hardcoded
   - What's unclear: Whether the Makefile should detect platform at runtime for portability
   - Recommendation: Hardcode `linux-x64` to match the existing Tailwind pattern; document it as a variable for easy override (`make esbuild-install PLATFORM=darwin-x64`)

3. **Should dist/main.js be committed after Phase 19?**
   - What we know: The placeholder bundle will be tiny (empty IIFE); Flask needs it present for `url_for` to not 404
   - What's unclear: CI behavior — does CI run `make js` before pytest, or does it rely on committed bundle?
   - Recommendation: Commit the placeholder `dist/main.js` so E2E tests pass without a build step in CI; document that `dist/main.js` is always committed (same as `dist/style.css`)

## Validation Architecture

> nyquist_validation is not set in .planning/config.json — skipping this section.

## Sources

### Primary (HIGH confidence)
- [esbuild Getting Started](https://esbuild.github.io/getting-started/) — standalone binary download via tgz, v0.27.3 current, npm registry URL pattern verified
- [esbuild API](https://esbuild.github.io/api/) — `--format=iife`, `--bundle`, `--outfile`, `--sourcemap=inline`, `--platform=browser`, `--target=es2022`, `--watch`, `--minify` flags all confirmed
- [esbuild dl.sh](https://github.com/evanw/esbuild/blob/main/dl.sh) — URL pattern `https://registry.npmjs.org/@esbuild/{platform}/-/{platform}-$VERSION.tgz` verified; binary at `package/bin/esbuild` within tgz
- [TypeScript TSConfig Reference](https://www.typescriptlang.org/tsconfig/) — `isolatedModules`, `noEmit`, `moduleResolution: "Bundler"`, `types: []`, `noUncheckedIndexedAccess` all documented
- SentinelX `Makefile` — existing `tailwind-install` pattern (curl → chmod) used as template for `esbuild-install`
- SentinelX `app/templates/base.html` — exact `url_for('static', filename='main.js')` confirmed at line 35
- SentinelX `tests/test_security_audit.py` — `test_csp_header_exact_match` checks response headers only, not JS bundle content; confirmed CSP test will pass with empty IIFE bundle
- SentinelX `.gitignore` — `tools/` already gitignored; `app/static/dist/` is explicitly un-ignored; source map `.map` files not currently excluded

### Secondary (MEDIUM confidence)
- [esbuild watch mode documentation](https://esbuild.github.io/api/#watch) — watch behavior confirmed: process stays alive, logs on rebuild, uses polling with ~2s detection window; actual recompile time for small projects well under 200ms
- [WebSearch: esbuild standalone binary tgz extraction 2025](https://www.npmjs.com/package/@esbuild/linux-x64) — npm registry package at v0.27.3; binary path within tgz confirmed

### Tertiary (LOW confidence)
- WebSearch: esbuild `--sourcemap=inline` DevTools behavior — confirmed base64 inline embedding; TypeScript source files appear in Sources panel with inline maps (multiple community sources agree, not verified against official docs directly)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — esbuild v0.27.3 and TypeScript 5.8 verified against official sources; tgz URL pattern verified against dl.sh and npm registry
- Architecture: HIGH — Makefile pattern mirrors existing Tailwind targets exactly; tsconfig options verified against TypeScript reference; base.html change is a one-line diff
- Pitfalls: HIGH — pitfalls sourced from direct codebase audit (`.gitignore` state, `tailwind.config.js` content paths, `base.html` script tag, `pyproject.toml` test config) and official docs

**Research date:** 2026-02-28
**Valid until:** 2026-03-28 (esbuild releases frequently; verify v0.27.3 is still latest before Phase 19 execution)
