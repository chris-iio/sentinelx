---
estimated_steps: 1
estimated_files: 1
skills_used: []
---

# T02: Add URL IOC end-to-end Playwright tests

Create `tests/e2e/test_url_e2e.py` with E2E tests covering the full URL IOC flow: extraction, card rendering, type badge, filter pill, enrichment with mocked URLhaus/VT response, and detail link navigation to `/ioc/url/...`. Follow the exact patterns established in the email IOC tests in `test_results_page.py` (lines 440-510) — same page objects, same mock setup pattern via `setup_enrichment_route_mock()`, same assertion style.

## Inputs

- ``tests/e2e/test_results_page.py` — email IOC test pattern (lines 440-510) to follow for structure`
- ``tests/e2e/conftest.py` — `setup_enrichment_route_mock()` function and `MOCK_ENRICHMENT_RESPONSE_8888` fixture pattern`
- ``tests/e2e/pages/results_page.py` — ResultsPage page object with `cards_for_type()`, `filter_by_type()`, `visible_cards`, `detail_links``
- ``tests/e2e/pages/index_page.py` — IndexPage page object with `goto()`, `extract_iocs()``
- ``app/static/src/ts/modules/enrichment.ts` — fixed detail link with `/ioc/` path (from T01)`
- ``app/static/dist/main.js` — rebuilt JS bundle (from T01)`

## Expected Output

- ``tests/e2e/test_url_e2e.py` — new test file with 5-7 URL IOC E2E tests covering: card rendering, type badge text, filter pill visibility, filter pill filtering, enrichment surface with mocked response, and detail link href correctness`

## Verification

python3 -m pytest tests/e2e/test_url_e2e.py -x -v
