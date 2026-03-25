---
id: T02
parent: S03
milestone: M006
key_files:
  - tests/e2e/test_url_e2e.py
key_decisions:
  - Followed exact email IOC test structure from test_results_page.py — same page objects, same mock setup via setup_enrichment_route_mock(), same assertion style
  - Created URL-specific mock enrichment response with URLhaus + VirusTotal providers rather than reusing the IP-focused MOCK_ENRICHMENT_RESPONSE_8888
  - Used mixed IOC text (URL + IP + domain) for filter pill tests that need multiple card types to verify filtering actually hides non-URL cards
duration: ""
verification_result: passed
completed_at: 2026-03-25T12:02:34.358Z
blocker_discovered: false
---

# T02: Add 8 URL IOC end-to-end Playwright tests covering extraction, card rendering, type badge, filter pill, enrichment surface, and detail link href

**Add 8 URL IOC end-to-end Playwright tests covering extraction, card rendering, type badge, filter pill, enrichment surface, and detail link href**

## What Happened

Created `tests/e2e/test_url_e2e.py` with 8 E2E tests covering the full URL IOC flow. The tests follow the exact patterns established in the email IOC tests in `test_results_page.py`:

1. **Card rendering** (`test_url_ioc_card_renders`) — submits text containing `https://evil.example.com/payload.exe` in offline mode, asserts at least 1 `.ioc-card[data-ioc-type='url']` renders.
2. **Type badge** (`test_url_type_badge_text`) — verifies `.ioc-type-badge--url` is visible and contains "URL" text.
3. **Filter pill visibility** (`test_url_filter_pill_exists`) — asserts `.filter-pill--url` appears in the filter bar with "URL" text.
4. **Filter pill filtering** (`test_url_filter_pill_shows_only_url_cards`) — uses mixed IOC text (URL + IP + domain), clicks URL pill, verifies only URL-type cards remain visible.
5. **Filter pill active state** (`test_url_filter_pill_active_state`) — clicks URL pill, asserts `.filter-pill--url.filter-pill--active` is visible.
6. **All Types reset** (`test_all_types_pill_resets_after_url_filter`) — filters by URL, then clicks "All Types", verifies full card count is restored.
7. **Enrichment summary row** (`test_url_enrichment_summary_row_created`) — uses online mode with mocked URLhaus/VT enrichment response, verifies `.ioc-summary-row` appears inside a URL-type card.
8. **Detail link href** (`test_url_detail_link_href_correct`) — after mocked enrichment completes, verifies `.detail-link` href contains `/ioc/url/` and the IOC domain, confirming the T01 href fix works end-to-end.

The mock enrichment response uses URL-specific providers (URLhaus + VirusTotal) with `ioc_type: "url"` to match the actual enrichment pipeline behavior.

## Verification

All 8 new URL E2E tests pass. Full E2E suite (113 tests) passes with no regressions.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/e2e/test_url_e2e.py -x -v` | 0 | ✅ pass | 5370ms |
| 2 | `python3 -m pytest tests/e2e/ -x -q` | 0 | ✅ pass | 42910ms |


## Deviations

Created 8 tests instead of the planned 5-7 — added separate tests for type badge text and enrichment summary row creation to match the granularity of the email IOC test pattern.

## Known Issues

None.

## Files Created/Modified

- `tests/e2e/test_url_e2e.py`
