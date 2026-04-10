# Dead Code Analysis Report

**Project:** SentinelX
**Date:** 2026-04-10
**Scope:** Runtime code only (`app/`, `app/templates/`, `app/static/src/ts/`, runtime-served assets)
**Tools Used:** `rg` cross-reference scans, Python AST symbol scan, template/route/static reference checks

---

## Summary

| Category | Result | Status |
|----------|--------|--------|
| TypeScript exports | 0 actionable unused exports | Clean |
| Python runtime symbols | 0 actionable dead functions/classes | Clean |
| Runtime templates/partials | 0 orphaned templates | Clean |
| Runtime static assets | 0 unreferenced served assets | Clean |
| Report staleness | 1 stale historical claim removed | Fixed |

**Verdict:** no actionable dead runtime code found in the current codebase.

---

## Findings

### 1. Previous report was stale

The prior version of this report referenced `annotations.ts` as an active TypeScript export source. That file is no longer present in the repository, so the historical report was not a reliable current source of truth.

**Action taken:** this report now reflects the current runtime surface only.

---

## Verified Live Runtime Surface

### TypeScript entrypoint and import chain are active

- [`app/static/src/ts/main.ts`](../app/static/src/ts/main.ts) imports and initializes the frontend modules.
- Cross-reference scan of all exported TS symbols in `app/static/src/ts/**/*.ts` found no unreferenced runtime exports.
- Type-only exports in [`app/static/src/ts/types/api.ts`](../app/static/src/ts/types/api.ts) and [`app/static/src/ts/types/ioc.ts`](../app/static/src/ts/types/ioc.ts) are consumed by runtime modules and tests.

### Flask routes are framework entrypoints, not dead code

Naive symbol scans reported these functions as unreferenced:

- [`app/routes/api.py:30`](../app/routes/api.py#L30) `api_analyze`
- [`app/routes/api.py:102`](../app/routes/api.py#L102) `api_status`

These are live because they are registered via `@bp_api.route(...)` on the API blueprint, which is imported by [`app/routes/__init__.py`](../app/routes/__init__.py) and registered in [`app/__init__.py`](../app/__init__.py).

### Templates and served assets are referenced

- [`app/templates/base.html`](../app/templates/base.html) serves:
  - `static/dist/style.css`
  - `static/dist/main.js`
  - `static/images/logo.svg`
  - both font files in `app/static/fonts/`
- Route handlers render the current template set through `render_template(...)`.
- Partial includes under `app/templates/partials/` are referenced from `results.html` and `_ioc_card.html`.

---

## Safe To Keep

### `Config.validate()` is live

- Definition: [`app/config.py:48`](../app/config.py#L48)
- Runtime use: [`app/__init__.py:73`](../app/__init__.py#L73)

This is not dead code. It remains a startup validation hook invoked by the app factory.

### `requires_api_key` is live production behavior

- Protocol declaration: [`app/enrichment/provider.py:38`](../app/enrichment/provider.py#L38)
- Runtime read: [`app/enrichment/orchestrator.py:97`](../app/enrichment/orchestrator.py#L97)

This attribute is used in production to decide which adapters receive semaphore-based concurrency limits.

### `all_provider_keys()` is test-only but intentional

- Definition: [`app/enrichment/config_store.py:138`](../app/enrichment/config_store.py#L138)
- Test use: [`tests/test_config_store.py:110`](../tests/test_config_store.py#L110)

This is still not called by production code, but it is an intentional test-facing API and not dead runtime code under the selected audit scope.

---

## Reproduction Notes

The conclusions above were based on:

- TS export cross-reference scan across `app/static/src/ts` and `tests`
- Python AST scan for top-level functions/classes under `app/`, followed by repo-wide reference checks
- Template reachability scan for `render_template(...)`, `{% include %}`, `{% extends %}`, and `url_for('static', ...)`

If this report is refreshed later, Flask-decorated route handlers should continue to be treated as live entrypoints rather than dead symbols.
