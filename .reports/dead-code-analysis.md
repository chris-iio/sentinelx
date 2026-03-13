# Dead Code Analysis Report

**Project:** SentinelX
**Date:** 2026-03-14
**Tools Used:** custom AST analysis, TS export cross-reference, template/route cross-reference, CSS class scan
**Test Baseline:** 758 tests (757 passing, 1 pre-existing failure in test_analyze_deduplicates)

---

## Summary

| Category | Items Found | Severity |
|----------|-------------|----------|
| Python dead code (vulture) | 0 | Clean |
| TypeScript unused exports | 0 | Clean |
| Unused Python imports | 0 | Clean |
| Unused Python packages | 0 | Clean |
| Unused template partials | 0 | Clean |
| Test-only method (no prod callers) | 1 | SAFE (kept) |

**Verdict: Codebase is clean.** All actionable dead code has been removed.

---

## SAFE: Kept Without Change

### `all_provider_keys()` -- Test-Only Method

**File:** `app/enrichment/config_store.py:128`
**Confidence:** SAFE

Method is defined but never called in production code. Only consumed by 3 tests in `tests/test_config_store.py`. Kept as a useful public API for the ConfigStore class.

### `Config.validate()` -- Intentional No-Op Hook

**File:** `app/config.py:50`
**Confidence:** SAFE

Empty method with docstring explaining it's a deliberate no-op. The VT API key is configured via Settings page, not at startup. Kept as a validation hook for future use.

### `requires_api_key` -- Protocol Attribute

**File:** `app/enrichment/provider.py:38` + all 8 adapters
**Confidence:** SAFE

Part of the `Provider` protocol, never read in application code (only in tests). Kept for protocol completeness; `PROVIDER_INFO` in `setup.py` serves the UI role.

### `.alert-warning` CSS -- Defensive Definition

**File:** `app/static/src/input.css:309`
**Confidence:** CAREFUL

No `flash("...", "warning")` exists today, but the class completes the alert triad and costs ~4 lines. Kept as forward-looking defensive CSS.

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
| `writeToClipboard()` | clipboard.ts | export.ts |
| `attr()` | dom.ts | 5 modules |
| `verdictSeverityIndex()` | ioc.ts | cards.ts, enrichment.ts |
| `VERDICT_LABELS` | ioc.ts | cards.ts, enrichment.ts |
| `getProviderCounts()` | ioc.ts | enrichment.ts |
| `VerdictKey` | ioc.ts | cards.ts, enrichment.ts, api.ts |
| `EnrichmentResultItem` | api.ts | enrichment.ts |
| `EnrichmentItem` | api.ts | enrichment.ts, export.ts |
| `EnrichmentStatus` | api.ts | enrichment.ts |
| `exportJSON()` | export.ts | enrichment.ts |
| `exportCSV()` | export.ts | enrichment.ts |
| `copyAllIOCs()` | export.ts | enrichment.ts |
| `init()` | annotations.ts | main.ts |

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
| `Config.DEBUG` attribute (never read) | Removed (2026-03-11) |
| `writeToClipboard` unused import in enrichment.ts | Removed (2026-03-11) |
| `VERDICT_SEVERITY` unnecessary export | Made private (2026-03-11) |
| `analyze_url` unused E2E fixture | Removed (2026-03-11) |
| Unused imports: `json`, `time` (test_cache_store) | Removed (2026-03-11) |
| Unused imports: `call`, `pytest` (test_registry_setup) | Removed (2026-03-11) |
| `OTX_BASE` unused constant (test_otx) | Removed (2026-03-11) |
| 8 unused ResultsPage POM methods | Removed (2026-03-11) |
| 3 unused SettingsPage POM methods/attrs | Removed (2026-03-11) |
| `test_save_api_key` duplicate test | Removed (2026-03-11) |
| MEMORY.md stale `bulk.py` reference | Updated (2026-03-11) |
| Unused `import pytest` in test_ioc_detail_routes.py | Removed (2026-03-14) |
| Unused `import pytest` in test_provider_protocol.py | Removed (2026-03-14) |
| Unused `routes_module` alias in test_ioc_detail_routes.py | Cleaned up (2026-03-14) |
