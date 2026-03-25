# S03: URL IOC End-to-End Polish

**Goal:** URL IOCs pasted in free-form text are extracted, enriched by URLhaus/OTX/VT/ThreatFox, displayed with correct type badge and filter pill, and accessible on the detail page via a working link.
**Demo:** Paste text containing https://evil.example.com/payload.exe — URL extracted, enriched by URLhaus/OTX/VT/ThreatFox, displayed with correct type badge and filter pill, detail page accessible via link.

## Must-Haves

- ## Must-Haves
- Detail link href uses `/ioc/<type>/<value>` (matching the Flask route), not `/detail/`
- KNOWLEDGE.md entry corrected to reflect the actual Flask route
- E2E tests verify URL IOC card rendering, type badge, filter pill, enrichment surface, and detail link navigation
- All existing 960+ tests continue to pass
- ## Verification
- ```bash
- # 1. Rebuilt JS uses /ioc/ not /detail/
- grep -c "/ioc/" app/static/dist/main.js   # > 0
- grep "/detail/" app/static/dist/main.js | grep -v sourcemap | grep -v '//.*detail' | wc -l  # 0 in link-building contexts
- # 2. Unit tests pass
- python3 -m pytest tests/ -x -q --ignore=tests/e2e
- # 3. URL detail route works via test client
- python3 -c "
- import sys; sys.path.insert(0, '.')
- from app import create_app
- app = create_app()
- with app.test_client() as c:
- r = c.get('/ioc/url/https://evil.com/payload.exe')
- assert r.status_code == 200, f'Got {r.status_code}'
- print('URL detail route: OK')
- "
- # 4. Fixed E2E test passes
- python3 -m pytest tests/e2e/test_results_page.py::test_detail_link_injected_after_enrichment_complete -x -v
- # 5. New URL E2E tests pass
- python3 -m pytest tests/e2e/test_url_e2e.py -x -v
- ```

## Proof Level

- This slice proves: Contract — E2E tests exercise the URL flow through the real Flask app with mocked enrichment responses.

## Integration Closure

- Upstream surfaces consumed: `app/routes.py` (Flask route `/ioc/<ioc_type>/<path:ioc_value>`), existing enrichment mock pattern from `tests/e2e/conftest.py`
- New wiring: none — all backend URL support already exists
- What remains: nothing for URL IOC support; S04 (input page redesign) is independent

## Verification

- None — no runtime changes, only bug fix and test coverage.

## Tasks

- [x] **T01: Fix detail link href from /detail/ to /ioc/ and rebuild JS** `est:20m`
  The `injectDetailLink()` function in both `enrichment.ts` and `history.ts` builds hrefs using `/detail/<type>/<value>`, but the Flask route is `@bp.route("/ioc/<ioc_type>/<path:ioc_value>")`. This means every 'View full detail →' link 404s. Fix the path prefix in both TS files, rebuild the JS bundle with `make js`, update the E2E test assertion that validates the broken path, and correct the KNOWLEDGE.md entry that documents the wrong route.
  - Files: `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/modules/history.ts`, `app/static/dist/main.js`, `tests/e2e/test_results_page.py`, `.gsd/KNOWLEDGE.md`
  - Verify: grep -c '/ioc/' app/static/dist/main.js && python3 -m pytest tests/e2e/test_results_page.py::test_detail_link_injected_after_enrichment_complete -x -v && python3 -m pytest tests/ -x -q --ignore=tests/e2e

- [x] **T02: Add URL IOC end-to-end Playwright tests** `est:30m`
  Create `tests/e2e/test_url_e2e.py` with E2E tests covering the full URL IOC flow: extraction, card rendering, type badge, filter pill, enrichment with mocked URLhaus/VT response, and detail link navigation to `/ioc/url/...`. Follow the exact patterns established in the email IOC tests in `test_results_page.py` (lines 440-510) — same page objects, same mock setup pattern via `setup_enrichment_route_mock()`, same assertion style.
  - Files: `tests/e2e/test_url_e2e.py`
  - Verify: python3 -m pytest tests/e2e/test_url_e2e.py -x -v

## Files Likely Touched

- app/static/src/ts/modules/enrichment.ts
- app/static/src/ts/modules/history.ts
- app/static/dist/main.js
- tests/e2e/test_results_page.py
- .gsd/KNOWLEDGE.md
- tests/e2e/test_url_e2e.py
