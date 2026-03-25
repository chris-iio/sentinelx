---
estimated_steps: 1
estimated_files: 5
skills_used: []
---

# T01: Fix detail link href from /detail/ to /ioc/ and rebuild JS

The `injectDetailLink()` function in both `enrichment.ts` and `history.ts` builds hrefs using `/detail/<type>/<value>`, but the Flask route is `@bp.route("/ioc/<ioc_type>/<path:ioc_value>")`. This means every 'View full detail →' link 404s. Fix the path prefix in both TS files, rebuild the JS bundle with `make js`, update the E2E test assertion that validates the broken path, and correct the KNOWLEDGE.md entry that documents the wrong route.

## Inputs

- ``app/static/src/ts/modules/enrichment.ts` — contains injectDetailLink() at line 216 with `/detail/` path`
- ``app/static/src/ts/modules/history.ts` — contains detail link building at line 71 with `/detail/` path`
- ``tests/e2e/test_results_page.py` — test_detail_link_injected_after_enrichment_complete at line 403 asserts `/detail/``
- ``.gsd/KNOWLEDGE.md` — entry 'SentinelX detail link route is /detail/...' at line 47 is incorrect`

## Expected Output

- ``app/static/src/ts/modules/enrichment.ts` — line 216 changed from `/detail/` to `/ioc/``
- ``app/static/src/ts/modules/history.ts` — line 71 changed from `/detail/` to `/ioc/``
- ``app/static/dist/main.js` — rebuilt JS bundle with `/ioc/` hrefs`
- ``tests/e2e/test_results_page.py` — assertion at line 415 changed from `/detail/` to `/ioc/``
- ``.gsd/KNOWLEDGE.md` — entry corrected to state route is `/ioc/``

## Verification

grep -c '/ioc/' app/static/dist/main.js && python3 -m pytest tests/e2e/test_results_page.py::test_detail_link_injected_after_enrichment_complete -x -v && python3 -m pytest tests/ -x -q --ignore=tests/e2e
