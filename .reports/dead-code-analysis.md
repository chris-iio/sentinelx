# Dead Code Analysis Report

**Project:** SentinelX
**Date:** 2026-03-09
**Tools Used:** vulture 2.14 (Python), custom AST analysis, TS export cross-reference, template include scan
**Test Baseline:** 574 tests passing (483 unit/integration + 91 E2E)

---

## Summary

| Category | Items Found | Severity |
|----------|-------------|----------|
| Python dead code (vulture) | 0 | Clean |
| TypeScript unused exports | 0 | Clean |
| Unused Python imports | 0 | Clean |
| Unused Python packages | 0 | Clean |
| Unused template partials | 0 | Clean |
| Duplicate function bodies | 1 | Fixed |
| Test-only method (no prod callers) | 1 | SAFE (kept) |

**Verdict: Codebase is clean.** One duplicate function (`verdictSeverityIndex`) extracted to shared module.

---

## Fixed: Duplicate Function

### `verdictSeverityIndex()` -- Identical in Two Modules

**Before:** Defined identically in both `cards.ts:114` and `enrichment.ts:93`.
**After:** Single definition exported from `types/ioc.ts:61`, imported by both consumers.

**Rationale:** The function operates on `VERDICT_SEVERITY` (defined in `types/ioc.ts`), so it belongs alongside that constant. Both `cards.ts` and `enrichment.ts` now import it.

---

## SAFE: Kept Without Change

### `all_provider_keys()` -- Test-Only Method

**File:** `app/enrichment/config_store.py:128`
**Confidence:** SAFE

Method is defined but never called in production code. Only consumed by 3 tests in `tests/test_config_store.py`. Kept as a useful public API for the ConfigStore class.

---

## False Positives Investigated (NOT Dead Code)

### TypeScript Exports -- All Active

All TypeScript exports are actively consumed via import chain from `main.ts`:

| Export | File | Consumer |
|--------|------|----------|
| `init()` | All 8 modules | main.ts |
| `findCardForIoc()` | cards.ts | enrichment.ts |
| `updateCardVerdict()` | cards.ts | enrichment.ts |
| `updateDashboardCounts()` | cards.ts | enrichment.ts |
| `sortCardsBySeverity()` | cards.ts | enrichment.ts |
| `writeToClipboard()` | clipboard.ts | enrichment.ts |
| `attr()` | dom.ts | 5 modules |
| `verdictSeverityIndex()` | ioc.ts | cards.ts, enrichment.ts |
| `VERDICT_SEVERITY` | ioc.ts | ioc.ts (verdictSeverityIndex) |
| `VERDICT_LABELS` | ioc.ts | cards.ts, enrichment.ts |
| `getProviderCounts()` | ioc.ts | enrichment.ts |
| `VerdictKey` | ioc.ts | cards.ts, enrichment.ts, api.ts |
| `EnrichmentResultItem` | api.ts | enrichment.ts |
| `EnrichmentItem` | api.ts | enrichment.ts, export.ts |
| `EnrichmentStatus` | api.ts | enrichment.ts |
| `exportJSON()` | export.ts | enrichment.ts |
| `exportCSV()` | export.ts | enrichment.ts |
| `copyAllIOCs()` | export.ts | enrichment.ts |

### Python Adapter Pattern -- Intentional Duplication

8 adapters each implement `_parse_response()` -- intentional per-provider design since each API returns different response schemas.

### Flask Route Handlers

All Python functions flagged by AST analysis are Flask route handlers, error handlers, `__init__` constructors, or factory functions invoked by the framework.

---

## Dependency Analysis -- All Used

| Package | Import Count | Status |
|---------|-------------|--------|
| Flask 3.1.1 | 5 | Used |
| Flask-Limiter 4.1.1 | 2 | Used |
| Flask-WTF 1.2.2 | 1 | Used |
| iocextract 1.16.1 | 1 | Used |
| iocsearcher 2.7.2 | 1 | Used |
| python-dotenv 1.1.0 | 1 | Used |
| requests 2.32.5 | 7 | Used |

---

## Previously Resolved

| Finding | Status |
|---------|--------|
| 7 unused `import pytest` in test files | Fixed |
| Unused `IOCType` import in test_routes.py | Fixed |
| Unused `csrf_app` variable in test_routes.py | Fixed |
| `TestConfig` class in config.py | Removed |
| `.btn-ghost` CSS class | Removed |
| Stale STATE.md backups | Cleaned |
| `everything-claude-code/` dir | Gitignored |
| Phase 18 artifacts | Archived |
| `pycryptodome` unused package | Uninstalled |
| Missing `.alert-success`/`.alert-warning` CSS | Added |
| Ruff config deprecation | Fixed |
| `verdictSeverityIndex()` duplicate | Extracted to types/ioc.ts |
