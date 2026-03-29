# S04: CSS audit + frontend TypeScript dedup — UAT

**Milestone:** M009
**Written:** 2026-03-29T20:21:37.027Z

## UAT: S04 — CSS audit + frontend TypeScript dedup

### Preconditions
- Node.js and npm installed
- `npm install` completed (typescript, esbuild available via npx)
- `tools/tailwindcss` binary present (via `make tailwind-install`)

---

### Test 1: shared-rendering.ts module structure
**Steps:**
1. Open `app/static/src/ts/modules/shared-rendering.ts`
2. Verify it exports `interface ResultDisplay` with fields: verdict, statText, summaryText, detectionCount, totalEngines
3. Verify it exports 4 functions: `computeResultDisplay`, `injectDetailLink`, `sortDetailRows`, `initExportButton`
4. Verify `initExportButton` accepts an `allResults: EnrichmentItem[]` parameter (not closing over module state)

**Expected:** All 4 functions and the interface are present and exported.

---

### Test 2: No private copies remain in consumer files
**Steps:**
1. Run: `grep -c 'function injectDetailLink' app/static/src/ts/modules/enrichment.ts app/static/src/ts/modules/history.ts`
2. Run: `grep -c 'function initExportButton' app/static/src/ts/modules/enrichment.ts app/static/src/ts/modules/history.ts`
3. Run: `grep -c '^function sortDetailRows' app/static/src/ts/modules/history.ts`

**Expected:** All counts are 0.

---

### Test 3: enrichment.ts debounce wrapper retained
**Steps:**
1. Open `app/static/src/ts/modules/enrichment.ts`
2. Search for `sortDetailRows` — there should be a local debounced wrapper function that calls `sharedSortDetailRows()`
3. Verify `sortTimers` map is still present for debounce management

**Expected:** Debounce wrapper exists, delegates to shared synchronous core via `sharedSortDetailRows()`.

---

### Test 4: TypeScript type checking
**Steps:**
1. Run: `make typecheck`

**Expected:** Exit code 0, zero type errors.

---

### Test 5: JavaScript bundle
**Steps:**
1. Run: `make js`
2. Verify `app/static/dist/main.js` exists and is non-empty

**Expected:** Exit code 0, bundle file present (≈28-29kb).

---

### Test 6: CSS build
**Steps:**
1. Run: `make css`
2. Verify `app/static/dist/style.css` exists and is non-empty

**Expected:** Exit code 0, style.css generated.

---

### Test 7: LOC reduction measurement
**Steps:**
1. Run: `wc -l app/static/src/ts/modules/shared-rendering.ts app/static/src/ts/modules/enrichment.ts app/static/src/ts/modules/history.ts`
2. Compute total and compare against baseline (937 lines)

**Expected:** Total ≤ 853 lines (84-line net reduction, ≥80 threshold).

---

### Test 8: CSS audit — no dead selectors
**Steps:**
1. Pick 5 CSS class selectors from `app/static/src/input.css`
2. For each, run: `rg 'selector-name' app/templates/ app/static/src/ts/`
3. Verify each returns at least one match

**Expected:** All sampled selectors are actively referenced.

---

### Edge Case: imports cleaned up in history.ts
**Steps:**
1. Verify history.ts no longer imports `verdictSeverityIndex` from `../types/ioc` (now used only by shared-rendering.ts internally)
2. Verify history.ts no longer imports `exportJSON, exportCSV, copyAllIOCs` from `./export` (now used only by shared-rendering.ts internally)

**Expected:** Unused imports removed. `make typecheck` would catch unused imports if configured with noUnusedLocals, but manual verification confirms clean imports.
