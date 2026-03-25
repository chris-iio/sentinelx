---
id: T01
parent: S03
milestone: M006
key_files:
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/modules/history.ts
  - app/static/dist/main.js
  - tests/e2e/test_results_page.py
  - .gsd/KNOWLEDGE.md
key_decisions:
  - Confirmed Flask route is /ioc/<ioc_type>/<path:ioc_value> at app/routes.py:386 — this is the single source of truth for detail link hrefs
duration: ""
verification_result: passed
completed_at: 2026-03-25T11:57:24.702Z
blocker_discovered: false
---

# T01: Fix detail link href from /detail/ to /ioc/ in enrichment.ts, history.ts, rebuilt JS bundle, updated E2E test assertion and KNOWLEDGE.md

**Fix detail link href from /detail/ to /ioc/ in enrichment.ts, history.ts, rebuilt JS bundle, updated E2E test assertion and KNOWLEDGE.md**

## What Happened

The `injectDetailLink()` function in both `enrichment.ts` and `history.ts` constructed hrefs using `/detail/<type>/<value>`, but the actual Flask route is `@bp.route("/ioc/<ioc_type>/<path:ioc_value>")` in `app/routes.py:386`. This caused every "View full detail →" link to 404.

Changed the path prefix from `/detail/` to `/ioc/` in both TypeScript modules, rebuilt the JS bundle with `make js`, updated the E2E test assertion in `test_detail_link_injected_after_enrichment_complete` to assert `/ioc/` instead of `/detail/`, and corrected the KNOWLEDGE.md entry that documented the wrong route.

## Verification

1. `grep -c '/ioc/' app/static/dist/main.js` → 1 match (confirms /ioc/ in bundle)
2. `grep -c '/detail/' app/static/dist/main.js` → 0 matches (confirms no residual /detail/)
3. E2E test `test_detail_link_injected_after_enrichment_complete` passes — confirms DOM href uses /ioc/ path
4. Full unit/integration test suite (930 tests) passes with no regressions

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c '/ioc/' app/static/dist/main.js` | 0 | ✅ pass | 50ms |
| 2 | `python3 -m pytest tests/e2e/test_results_page.py::test_detail_link_injected_after_enrichment_complete -x -v` | 0 | ✅ pass | 3140ms |
| 3 | `python3 -m pytest tests/ -x -q --ignore=tests/e2e` | 0 | ✅ pass | 10010ms |


## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `app/static/src/ts/modules/enrichment.ts`
- `app/static/src/ts/modules/history.ts`
- `app/static/dist/main.js`
- `tests/e2e/test_results_page.py`
- `.gsd/KNOWLEDGE.md`
