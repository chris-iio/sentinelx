---
phase: 19-build-pipeline-infrastructure
plan: 01
subsystem: infra
tags: [esbuild, typescript, makefile, build-pipeline, iife, tsconfig]

# Dependency graph
requires: []
provides:
  - esbuild 0.27.3 standalone binary install target (make esbuild-install)
  - JS build targets: js, js-dev, js-watch, typecheck
  - Updated build target combining css+js pipelines
  - tsconfig.json with strict browser-only TypeScript config
  - Placeholder main.ts entry point at app/static/src/ts/main.ts
  - .gitignore source map exclusion rule
  - tailwind.config.js TypeScript source path inclusion
affects:
  - 19-02 (if it exists — TypeScript module conversion will use this pipeline)
  - 20-type-definitions (will use tsconfig.json and typecheck target)
  - 21-module-conversion (will build via make js/js-dev)
  - 22-module-conversion (will build via make js/js-dev)
  - All future phases doing TS development

# Tech tracking
tech-stack:
  added:
    - esbuild 0.27.3 (standalone binary, linux-x64, installed to tools/)
    - TypeScript 5.8.3 (npm global install, tsc for type-checking only)
  patterns:
    - Standalone binary pattern for build tools (no Node.js runtime in production)
    - IIFE output format for CSP-safe browser delivery
    - noEmit tsconfig — esbuild transpiles, tsc only type-checks
    - Inline source maps (not external) — no .map files committed

key-files:
  created:
    - tsconfig.json
    - app/static/src/ts/main.ts
    - app/static/dist/main.js
  modified:
    - Makefile
    - .gitignore
    - tailwind.config.js

key-decisions:
  - "esbuild 0.27.3 pinned via ESBUILD_VERSION — mirrors existing tailwind-install standalone binary pattern"
  - "IIFE output format mandatory — preserves CSP (script-src self) and <script defer> compatibility"
  - "noEmit: true in tsconfig — tsc only type-checks, esbuild handles transpilation/bundling"
  - "inline source maps (--sourcemap=inline) not external — .gitignore excludes *.map to prevent accidental commits"
  - "types: [] in tsconfig — prevents @types/node pollution if npm packages ever installed"
  - "moduleResolution: Bundler — required for esbuild import resolution compatibility"
  - "TypeScript 5.8.3 installed globally via npm (tsc on PATH) — dev-only tooling, not a runtime dependency"

patterns-established:
  - "Standalone binary pattern: curl tgz from npm registry → extract → move binary → chmod +x"
  - "JS build pipeline: make js (prod minified IIFE) / make js-dev (inline sourcemap) / make js-watch (watch mode)"
  - "Type-check gate: make typecheck runs tsc --noEmit, reads project root tsconfig.json"
  - "Build combines css+js: make build depends on both css and js targets"

requirements-completed: [BUILD-01, BUILD-02, BUILD-03, BUILD-04, BUILD-05, BUILD-06]

# Metrics
duration: 2min
completed: 2026-02-28
---

# Phase 19 Plan 01: Build Pipeline Infrastructure Summary

**esbuild 0.27.3 standalone binary pipeline with IIFE output, 5 Makefile targets (js/js-dev/js-watch/typecheck/build), and strict tsconfig.json for browser-only TypeScript type-checking**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-28T14:15:46Z
- **Completed:** 2026-02-28T14:17:38Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Full JS build pipeline infrastructure established: esbuild 0.27.3 installed, 5 new Makefile targets working
- tsconfig.json configured for strict browser-only TypeScript (strict, isolatedModules, noUncheckedIndexedAccess, types:[])
- Placeholder main.ts entry point with `export {}` confirms isolatedModules compatibility; compiles to 25-byte IIFE

## Task Commits

Each task was committed atomically:

1. **Task 1: Create tsconfig.json, placeholder main.ts, and update config files** - `fa31053` (chore)
2. **Task 2: Add esbuild-install target and all JS build targets to Makefile** - `74e7f2a` (chore)
3. **Task 3: Install esbuild binary and verify all build targets work** - `4d4ed74` (feat)

**Plan metadata:** (docs commit — created after this summary)

## Files Created/Modified

- `tsconfig.json` — strict browser TypeScript config: target es2022, isolatedModules, noUncheckedIndexedAccess, types:[], noEmit
- `app/static/src/ts/main.ts` — placeholder entry point with `export {}` for pipeline verification
- `app/static/dist/main.js` — compiled IIFE bundle from placeholder: `"use strict";(()=>{})();`
- `Makefile` — added ESBUILD/JS_ENTRY/JS_OUT/ESBUILD_VERSION variables; esbuild-install/js/js-dev/js-watch/typecheck targets; updated build to css+js
- `.gitignore` — added `app/static/dist/*.map` exclusion rule
- `tailwind.config.js` — added `./app/static/src/ts/**/*.ts` to content array

## Decisions Made

- TypeScript 5.8.3 installed globally via npm (Rule 3 — blocking: `tsc` not found on PATH, required for `make typecheck`)
- All other decisions followed the plan exactly as specified

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed TypeScript 5.8 globally via npm**
- **Found during:** Task 3 (Install esbuild and verify all targets)
- **Issue:** `make typecheck` requires `tsc` on PATH; `which tsc` returned not found
- **Fix:** Ran `npm install -g typescript@5.8` — installed TypeScript 5.8.3 to ~/.nvm path
- **Files modified:** None (global npm install, no project files changed)
- **Verification:** `tsc --version` outputs `Version 5.8.3`, `make typecheck` exits 0
- **Committed in:** Not committed (global tool, no project file change)

---

**Total deviations:** 1 auto-fixed (blocking tool installation)
**Impact on plan:** Necessary to satisfy the `make typecheck` target. Plan notes "if tsc is not found, install via npm install -g typescript@5.8" — this is the documented fallback, not a deviation in spirit.

## Issues Encountered

None beyond the TypeScript global install covered above.

## User Setup Required

None - no external service configuration required. The esbuild binary is downloaded by `make esbuild-install` and TypeScript is installed globally. Both are available immediately after running those commands.

## Next Phase Readiness

- Build pipeline is fully operational: `make js`, `make js-dev`, `make js-watch`, `make typecheck`, `make build` all exit 0
- `app/static/src/ts/` directory established as TypeScript source root
- TypeScript configuration ready for strict type-checking of browser modules
- Subsequent phases can begin converting JS → TS incrementally, building via `make js` and type-checking via `make typecheck`
- No blockers

---
*Phase: 19-build-pipeline-infrastructure*
*Completed: 2026-02-28*
