# Requirements: v3.0 TypeScript Migration

**Defined:** 2026-02-28
**Core Value:** Type-safe, modular frontend code with zero functional changes — same behavior, better tooling.
**Scope:** Frontend build pipeline and JS→TS conversion only. Zero backend changes. Zero new features.
**Foundation:** esbuild standalone binary (no Node.js), tsc for type-checking only, IIFE output format.

## v3.0 Requirements

### Build Pipeline

- [x] **BUILD-01**: esbuild is installed as a standalone binary (no Node.js/npm required) with a pinned version
- [x] **BUILD-02**: `make js` compiles TypeScript source to a single IIFE bundle at `app/static/dist/main.js`
- [x] **BUILD-03**: `make js-watch` runs esbuild in watch mode for development
- [x] **BUILD-04**: `make js-dev` produces a bundle with inline source maps for browser debugging
- [x] **BUILD-05**: `make typecheck` runs `tsc --noEmit` to validate types without producing output
- [x] **BUILD-06**: `make build` target runs both CSS and JS builds

### Type System

- [x] **TYPE-01**: tsconfig.json uses `strict: true` with `isolatedModules`, `noUncheckedIndexedAccess`, and `"types": []`
- [x] **TYPE-02**: Domain types defined for Verdict, IocType, and verdict severity constants
- [x] **TYPE-03**: API response interfaces defined for enrichment polling endpoint (`/enrichment/status/{job_id}`)
- [x] **TYPE-04**: All DOM element access uses proper null-checking (no non-null assertions)

### Module Structure

- [ ] **MOD-01**: Entry point `main.ts` imports and initializes all feature modules
- [ ] **MOD-02**: Form controls module (submit button, clear, auto-grow textarea, mode toggle, paste feedback)
- [ ] **MOD-03**: Clipboard module (copy IOC values, copy-with-enrichment, fallback copy)
- [ ] **MOD-04**: Enrichment polling module (fetch loop, progress bar, result rendering, warning banner)
- [ ] **MOD-05**: Card management module (verdict updates, dashboard counts, severity sorting)
- [ ] **MOD-06**: Filter bar module (verdict/type/search filtering, dashboard badge click)
- [ ] **MOD-07**: Settings module (API key show/hide toggle)
- [ ] **MOD-08**: UI utilities module (scroll-aware filter bar, card stagger animation)

### Migration Safety

- [ ] **SAFE-01**: All existing Playwright E2E tests pass without modification
- [ ] **SAFE-02**: CSP regression test (`test_security_audit.py`) passes against the new bundle
- [ ] **SAFE-03**: Original `main.js` is deleted after migration is verified complete
- [ ] **SAFE-04**: `base.html` script tag updated to reference `dist/main.js`

## Future Requirements

### Code Quality

- **QUAL-01**: ES5 patterns modernized to ES2022 (`var` → `const/let`, arrow functions, for-of loops)
- **QUAL-02**: Linting with typescript-eslint for style enforcement

### Testing

- **TEST-01**: Unit tests for pure TypeScript utility functions (verdict severity, date formatting)
- **TEST-02**: Pre-commit hook runs `make typecheck` before allowing commits

## Out of Scope

| Feature | Reason |
|---------|--------|
| New user-facing features | v3.0 is infrastructure-only — same behavior, better tooling |
| Backend changes | TypeScript is frontend-only |
| Node.js / npm dependency | Project constraint — esbuild + tsc installed as binaries |
| Framework adoption (React, Vue, etc.) | Vanilla TS is sufficient for this app's complexity |
| ES module `<script type="module">` | IIFE preserves existing CSP and template compatibility |
| Webpack / Vite / Rollup | esbuild is simpler, faster, and has standalone binary |
| Runtime type validation (Zod, io-ts) | API responses are from trusted internal Flask routes |
| `.d.ts` declaration files | Not a library — no consumers need type declarations |
| Jest / Vitest JS test framework | Existing Playwright E2E suite covers all behavior |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BUILD-01 | Phase 19 | Complete |
| BUILD-02 | Phase 19 | Complete |
| BUILD-03 | Phase 19 | Complete |
| BUILD-04 | Phase 19 | Complete |
| BUILD-05 | Phase 19 | Complete |
| BUILD-06 | Phase 19 | Complete |
| TYPE-01 | Phase 20 | Complete |
| TYPE-02 | Phase 20 | Complete |
| TYPE-03 | Phase 20 | Complete |
| TYPE-04 | Phase 20 | Complete |
| MOD-02 | Phase 21 | Pending |
| MOD-03 | Phase 21 | Pending |
| MOD-05 | Phase 21 | Pending |
| MOD-06 | Phase 21 | Pending |
| MOD-07 | Phase 21 | Pending |
| MOD-08 | Phase 21 | Pending |
| MOD-01 | Phase 22 | Pending |
| MOD-04 | Phase 22 | Pending |
| SAFE-03 | Phase 22 | Pending |
| SAFE-04 | Phase 22 | Pending |
| SAFE-01 | Phase 23 | Pending |
| SAFE-02 | Phase 23 | Pending |

**Coverage:**
- v3.0 requirements: 22 total
- Mapped to phases: 22
- Unmapped: 0

---
*Requirements defined: 2026-02-28*
*Last updated: 2026-02-28 — traceability updated after roadmap creation (phases 19-23)*
