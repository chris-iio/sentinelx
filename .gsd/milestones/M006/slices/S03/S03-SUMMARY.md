---
id: S03
parent: M006
milestone: M006
provides:
  - 8 E2E Playwright tests for URL IOC flow (extraction → rendering → filtering → enrichment → detail link)
  - Verified detail link href uses /ioc/ prefix across enrichment.ts and history.ts
requires:
  []
affects:
  []
key_files:
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/modules/history.ts
  - app/static/dist/main.js
  - tests/e2e/test_results_page.py
  - tests/e2e/test_url_e2e.py
  - .gsd/KNOWLEDGE.md
key_decisions:
  - Detail link href uses /ioc/<type>/<value> matching the Flask route, not /detail/ — confirmed by grepping routes.py:386
  - URL E2E tests follow the exact email IOC test pattern (same page objects, same mock setup, same assertion style) for consistency
  - URL-specific mock enrichment response uses URLhaus + VirusTotal providers rather than reusing the IP-focused MOCK_ENRICHMENT_RESPONSE_8888
patterns_established:
  - URL E2E test pattern in test_url_e2e.py — reusable template for adding E2E tests for other IOC types (same structure as email tests)
  - Mixed IOC text pattern for filter pill tests — submit text containing URL + IP + domain to verify filtering actually hides non-target cards
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M006/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M006/slices/S03/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-25T12:04:52.798Z
blocker_discovered: false
---

# S03: URL IOC End-to-End Polish

**Fixed broken detail link hrefs (/detail/ → /ioc/) and added 8 E2E Playwright tests proving full URL IOC flow: extraction, card rendering, type badge, filter pill, enrichment, and detail link navigation.**

## What Happened

This slice addressed a bug and a testing gap for URL IOCs. The backend URL support was already complete (extraction, enrichment by URLhaus/OTX/VT/ThreatFox, Flask detail route with path converter), but the frontend detail links pointed to the wrong route and no E2E tests existed to catch it.

**T01 — Fix detail link href:** The `injectDetailLink()` function in both `enrichment.ts` and `history.ts` built hrefs using `/detail/<type>/<value>`, but the Flask route is `@bp.route("/ioc/<ioc_type>/<path:ioc_value>")`. Every "View full detail →" link therefore 404'd. Changed both TS files to use `/ioc/`, rebuilt with `make js`, updated the existing E2E assertion in `test_detail_link_injected_after_enrichment_complete`, and corrected the KNOWLEDGE.md entry. 930 unit tests pass, 0 regressions.

**T02 — URL E2E test suite:** Created `tests/e2e/test_url_e2e.py` with 8 Playwright tests following the exact email IOC test patterns from `test_results_page.py` — same page objects, same `setup_enrichment_route_mock()`, same assertion style. Tests cover: card rendering, type badge ("URL"), filter pill visibility, filter pill filtering (only URL cards visible when active), filter pill active state CSS, "All Types" reset, enrichment summary row with URLhaus/VT mock, and detail link href containing `/ioc/url/`. A URL-specific mock enrichment response was created with URLhaus + VirusTotal providers rather than reusing the IP-focused mock.

## Verification

All 6 slice-level verification checks passed:

1. `grep -c '/ioc/' app/static/dist/main.js` → 1 (confirms /ioc/ in built JS)
2. `grep '/detail/' app/static/dist/main.js | grep -v sourcemap | grep -v '//.*detail' | wc -l` → 0 (no residual /detail/ in link-building contexts)
3. `python3 -m pytest tests/ -x -q --ignore=tests/e2e` → 930 passed in 10.18s
4. Flask test client `GET /ioc/url/https://evil.com/payload.exe` → HTTP 200
5. `python3 -m pytest tests/e2e/test_results_page.py::test_detail_link_injected_after_enrichment_complete -x -v` → PASSED
6. `python3 -m pytest tests/e2e/test_url_e2e.py -x -v` → 8 passed in 4.77s

## Requirements Advanced

None.

## Requirements Validated

- R033 — 8 E2E Playwright tests verify URL IOC extraction, card rendering with type badge, filter pill, enrichment with mocked URLhaus/VT, and detail link href at /ioc/url/. Flask test client confirms /ioc/url/https://evil.com/payload.exe returns HTTP 200. 930 unit tests pass.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

T02 produced 8 tests instead of the planned 5–7, adding separate tests for type badge text and enrichment summary row creation to match the granularity of the email IOC test pattern. No other deviations.

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

- `app/static/src/ts/modules/enrichment.ts` — Changed injectDetailLink() href from /detail/ to /ioc/
- `app/static/src/ts/modules/history.ts` — Changed injectDetailLink() href from /detail/ to /ioc/
- `app/static/dist/main.js` — Rebuilt JS bundle with corrected /ioc/ href
- `tests/e2e/test_results_page.py` — Updated detail link E2E assertion from /detail/ to /ioc/
- `tests/e2e/test_url_e2e.py` — New: 8 URL IOC E2E Playwright tests
- `.gsd/KNOWLEDGE.md` — Corrected detail link route documentation entry
- `.gsd/PROJECT.md` — Updated current state to reflect S03 completion
