# Dead Code Analysis Report

**Project:** SentinelX
**Date:** 2026-02-25
**Baseline:** 224 tests passing, 97% coverage

## Summary

| Category | Count | Action |
|----------|-------|--------|
| SAFE to remove | 2 | Remove |
| CAUTION (verify) | 1 | Simplify |
| FALSE POSITIVES | 15+ | No action |

## Findings

### SAFE — Dead Code to Remove

#### 1. `app/enrichment/adapters/__init__.py` — Unused re-exports

**Lines 5-9:** Re-exports `MBAdapter`, `TFAdapter`, `VTAdapter` with `__all__`.
**Evidence:** Zero imports from `app.enrichment.adapters` package init across entire codebase.
All consumers import directly from individual modules:
- `app/routes.py` → `from app.enrichment.adapters.virustotal import VTAdapter`
- `tests/test_vt_adapter.py` → `from app.enrichment.adapters.virustotal import VTAdapter`
- `tests/test_routes.py` → imports from individual modules

**Action:** Strip re-export imports and `__all__`; keep docstring only.

#### 2. `package.json` + `node_modules/` — Unused npm dependency

**File:** `package.json` declares `glob: ^13.0.6`
**Evidence:** `tailwind.config.js` uses only `import('tailwindcss').Config` type annotation — does not use the `glob` npm package. Tailwind standalone CLI is used for CSS builds (no Node.js runtime needed). The `glob` package and `node_modules/` directory serve no purpose.

**Action:** Remove `package.json`, `package-lock.json`, and `node_modules/`.

### CAUTION — Verify Before Action

#### 3. `app/config.py:47-53` — Empty `validate()` method

**Lines 47-53:** `Config.validate()` is a documented no-op (`pass`/empty body).
Called from `app/__init__.py:61`.
**Assessment:** Intentional placeholder per SEC-03 comments — VT API key validation is done per-request in routes. However, the call + empty method is dead weight. Could be removed, but it's an extension point for future validation.

**Action:** Keep as-is (intentional design decision). Flag for review if requirements change.

### FALSE POSITIVES — No Action Needed

| Finding | Reason it's not dead code |
|---------|--------------------------|
| `create_app` (app/__init__.py:20) | Flask app factory — called from `run.py` and tests |
| `set_security_headers` (app/__init__.py:70) | Flask `@after_request` decorator — framework-invoked |
| `request_entity_too_large` (app/__init__.py:81) | Flask `@errorhandler(413)` — framework-invoked |
| `rate_limit_exceeded` (app/__init__.py:86) | Flask `@errorhandler(429)` — framework-invoked |
| `index`, `analyze`, `settings_get/post`, `enrichment_status` | Flask route handlers — `@bp.route()` decorator |
| `TestConfig` (app/config.py:56) | Used by tests via `create_app({'TESTING': True, ...})` pattern |
| `VIRUSTOTAL_API_KEY`, `DEBUG`, `TESTING`, etc. | Config class attributes — accessed by Flask's config system |
| `from __future__ import annotations` | PEP 563 — implicitly used for type annotation evaluation |
| `import requests.exceptions` | Used as namespace: `requests.exceptions.Timeout`, etc. |
| `lookup` duplicates across adapters | Intentional polymorphism — each adapter implements interface |

## Tools Used

- **vulture 2.14** (80% + 60% confidence levels)
- **Custom AST analysis** (unused imports, unreachable code, duplicate definitions)
- **Manual grep analysis** (cross-file import tracing)
- **Codebase structure analysis** (template references, JS function calls)
