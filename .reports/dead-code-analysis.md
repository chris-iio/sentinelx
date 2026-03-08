# Dead Code Analysis Report

**Project:** SentinelX
**Date:** 2026-03-05
**Tools Used:** vulture 2.14 (Python), manual cross-reference analysis (Python + TypeScript)
**Test Baseline:** 457 unit/integration tests passing (551 total incl. E2E)

---

## Summary

| Category | Items Found | Severity |
|----------|-------------|----------|
| Python dead code (vulture) | 0 | Clean |
| TypeScript unused exports | 0 | Clean |
| Unused Python imports | 0 | Clean |
| Unused Python packages | 0 | Clean |
| Unused template partials | 0 | Clean |
| Unused static assets | 0 | Clean |
| Test-only method (no prod callers) | 1 | SAFE |

**Verdict: Codebase is exceptionally clean.** All previous findings (v1.2, v2.0 reports) resolved.

---

## SAFE: Single Finding

### 1. `all_provider_keys()` — Test-Only Method

**File:** `app/enrichment/config_store.py:107`
**Confidence:** SAFE

Method is defined but never called in production code (`app/`, `run.py`, templates). Only consumed by 3 tests in `tests/test_config_store.py`.

**Recommendation:** Keep — it's a useful public API for future settings features (e.g., displaying all configured keys). Not dead code per se, just unused in current production paths.

---

## False Positives Investigated (NOT Dead Code)

### TypeScript Exports — All Active

All 19 TypeScript exports are actively consumed via import chain from `main.ts`. Previous Phase 22 scaffolding items are now fully integrated:

| Export | File | Consumer |
|--------|------|----------|
| `init()` | All 7 modules | main.ts |
| `findCardForIoc()` | cards.ts | enrichment.ts |
| `updateCardVerdict()` | cards.ts | enrichment.ts |
| `updateDashboardCounts()` | cards.ts | enrichment.ts |
| `sortCardsBySeverity()` | cards.ts | enrichment.ts |
| `writeToClipboard()` | clipboard.ts | enrichment.ts |
| `attr()` | dom.ts | 5 modules |
| `VERDICT_SEVERITY` | ioc.ts | cards.ts, enrichment.ts |
| `VERDICT_LABELS` | ioc.ts | cards.ts, enrichment.ts |
| `getProviderCounts()` | ioc.ts | enrichment.ts |
| Types/Interfaces | api.ts, ioc.ts | Multiple modules |

### Python Adapter Pattern — Intentional Duplication

8 adapters each implement `_parse_response()` — intentional per-provider design since each API returns different response schemas.

### Flask Route Handlers

All Python functions are Flask route handlers, error handlers, or factory functions invoked by the framework — not dead code.

---

## Dependency Analysis — All Used

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
