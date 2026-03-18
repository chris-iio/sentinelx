---
estimated_steps: 7
estimated_files: 3
---

# T02: Add enrichment surface tests and update test_responsive_grid_layout docstring

**Slice:** S05 — E2E test suite update
**Milestone:** M002

## Description

The current 91-test suite has zero coverage of the enrichment surface features added in S01–S04: inline expand/collapse, summary row rendering, verdict micro-bar, staleness badge, detail link injection, and enrichment section containers. This task adds new E2E tests that exercise these features using Playwright route mocking to simulate the enrichment API, avoiding any dependency on external API keys.

The key challenge is that `.ioc-summary-row` and related elements are JS-created — they only exist after `enrichment.ts` processes at least one polling response. Playwright's `page.route()` can intercept `**/enrichment/status/*` and return canned JSON that triggers the full JS rendering pipeline.

**Skill:** `test` skill is relevant for matching existing test patterns.

## Steps

1. **Update `test_responsive_grid_layout` docstring** in `tests/e2e/test_extraction.py` (line ~275). Change the docstring from `"Cards grid uses responsive layout."` to `"Cards grid container is visible (single-column layout)."`. Do NOT change the test name or assertions — the `#ioc-cards-grid` selector is still valid.

2. **Add a route-mocking helper** in `tests/e2e/conftest.py`. Create a fixture or helper function that:
   - Intercepts `**/enrichment/status/*` via `page.route()`
   - Returns a valid `EnrichmentStatus` JSON response with `complete: true` and a list of `EnrichmentResultItem` entries (one per IOC per provider)
   - The canned response must include fields that trigger summary row rendering: `ioc_value`, `ioc_type`, `provider`, `verdict`, `detection_count`, `total_engines`, `scan_date`, `raw_stats`
   - Example canned data for a single IOC (`8.8.8.8`, type `ipv4`):
     ```json
     {
       "total": 2,
       "done": 2,
       "complete": true,
       "results": [
         {
           "type": "result",
           "ioc_value": "8.8.8.8",
           "ioc_type": "ipv4",
           "provider": "VirusTotal",
           "verdict": "clean",
           "detection_count": 0,
           "total_engines": 70,
           "scan_date": "2026-03-15T12:00:00Z",
           "raw_stats": {}
         },
         {
           "type": "result",
           "ioc_value": "8.8.8.8",
           "ioc_type": "ipv4",
           "provider": "AbuseIPDB",
           "verdict": "clean",
           "detection_count": 0,
           "total_engines": 1,
           "scan_date": "2026-03-15T12:00:00Z",
           "raw_stats": {"abuse_confidence_score": 0}
         }
       ]
     }
     ```
   - The fixture should be a callable that takes `page` and sets up the route, so individual tests can call it before navigation. Or implement it as a helper function that tests call directly with `page.route(...)`.

3. **Write a helper function to navigate in online mode with mocked enrichment**. In the test file (or conftest), create a function like `_navigate_online_with_mock(page, index_url, text, mock_results)` that:
   - Sets up `page.route("**/enrichment/status/*", ...)` with the canned response
   - Navigates to index, submits text in online mode
   - Waits for `.ioc-summary-row` to appear (with a reasonable timeout) — this confirms enrichment.ts processed the mocked response and row-factory.ts created the summary row
   - Returns `ResultsPage`

4. **Write new tests in `tests/e2e/test_results_page.py`**. Add a new section at the bottom with a clear comment header. Tests to add:

   **a. `test_online_mode_has_enrichment_slots`** — Navigate in online mode (mocked), assert `.enrichment-slot` count equals the number of IOC cards.

   **b. `test_enrichment_summary_row_created_after_polling`** — Navigate in online mode (mocked), wait for polling to complete, assert `.ioc-summary-row` count ≥ 1. Verify it's inside an `.ioc-card`.

   **c. `test_enrichment_summary_row_has_verdict_micro_bar`** — After mocked enrichment, assert `.verdict-micro-bar` is present within a summary row.

   **d. `test_expand_collapse_toggle`** — After mocked enrichment, click a `.ioc-summary-row`, assert `.is-open` class is added to both the summary row and its sibling `.enrichment-details`. Click again, assert `.is-open` is removed from both.

   **e. `test_enrichment_details_has_section_containers`** — After mocked enrichment + expand, assert `.enrichment-section--context`, `.enrichment-section--reputation`, and `.enrichment-section--no-data` exist inside `.enrichment-details`.

   **f. `test_detail_link_injected_after_enrichment_complete`** — After mocked enrichment (with `complete: true`), assert `.detail-link-footer` and `.detail-link` are present. The link's `href` should contain `/ioc/` path.

   **g. `test_enrichment_slot_loaded_class_added`** — After mocked enrichment, assert `.enrichment-slot--loaded` count ≥ 1.

   **h. `test_offline_mode_no_summary_rows`** — Navigate in offline mode, assert `.ioc-summary-row` count is 0. (Complement to existing `test_offline_mode_cards_have_no_enrichment_slot`.)

5. **Important constraints for route mocking:**
   - The enrichment polling endpoint is `GET /enrichment/status/<job_id>` — the `job_id` is dynamic (generated by Flask on each submission). The route mock pattern `**/enrichment/status/*` catches any job_id.
   - The first poll response triggers `handleProviderResult()` in enrichment.ts, which calls `getOrCreateSummaryRow()` in row-factory.ts. The mock must return at least one result item.
   - When `complete: true`, `markEnrichmentComplete()` fires, which calls `injectDetailLink()`. The mock should return `complete: true` to trigger this.
   - The polling loop runs every 750ms. After mocking, use `page.wait_for_selector(".ioc-summary-row", timeout=5000)` or Playwright `expect().to_be_visible()` to wait for the JS rendering.
   - Use `page.wait_for_selector(".detail-link-footer", timeout=5000)` to wait for the detail link injection (fires on `complete: true` after all results processed).

6. **Important constraint for expand/collapse testing:**
   - Expand/collapse uses event delegation on `.page-results` ancestor (per D018). Clicking `.ioc-summary-row` toggles `.is-open` on both the summary row AND the adjacent `.enrichment-details` element.
   - Use `page.locator(".ioc-summary-row").first.click()` to trigger expand.
   - Then assert: `expect(page.locator(".ioc-summary-row.is-open")).to_have_count(1)` and `expect(page.locator(".enrichment-details.is-open")).to_have_count(1)`.
   - Click again to collapse, assert both `.is-open` counts go to 0.

7. **Run full suite:** `python3 -m pytest tests/e2e/ -q`. All original 91 tests must pass, plus the new tests. Count should be > 91. Use `python3 -m pytest tests/e2e/ -q --co | grep -c '::test_'` to verify the count before running.

## Must-Haves

- [ ] `test_responsive_grid_layout` docstring updated (not the test name or assertions)
- [ ] Route-mocking helper/fixture that intercepts `**/enrichment/status/*`
- [ ] At least 6 new tests exercising enrichment surface features
- [ ] Expand/collapse test verifies `.is-open` on both summary row and details panel
- [ ] All 91 original tests still pass
- [ ] Total test count > 91

## Verification

- `python3 -m pytest tests/e2e/ -q --co | grep -c '::test_'` → count > 91
- `python3 -m pytest tests/e2e/ -q` → all pass, 0 failures
- `python3 -m pytest tests/e2e/test_results_page.py -q -k "enrichment or expand or summary_row or detail_link"` → new tests pass specifically

## Inputs

- `tests/e2e/pages/results_page.py` — updated in T01 with all new locators. T01 added properties like `summary_rows`, `enrichment_slots`, `loaded_enrichment_slots`, `enrichment_details`, `micro_bars`, `detail_link_footers`, `detail_links`, `expanded_summary_rows`, `enrichment_sections`, etc. Also added `expand_row(ioc_value)`, `collapse_row(ioc_value)`, `is_row_expanded(ioc_value)` helpers.
- `tests/e2e/conftest.py` — current conftest with `live_server`, `index_url`, `browser_context_args` fixtures
- `tests/e2e/test_results_page.py` — current file with 18 filter/UX tests plus `_navigate_to_results` helper
- `tests/e2e/test_extraction.py` — contains `test_responsive_grid_layout` at line ~275
- Enrichment API contract: `GET /enrichment/status/<job_id>` returns `EnrichmentStatus` JSON (see `app/static/src/ts/types/api.ts` for the full shape)
- Key timing: enrichment.ts polls every 750ms. `.ioc-summary-row` appears after first `handleProviderResult()` call. `.detail-link-footer` appears after `markEnrichmentComplete()` (when `complete: true`).
- The results page template (`app/templates/results.html`) puts `data-job-id` on `.page-results` in online mode — this drives enrichment.ts `init()`. The mock must intercept the fetch that enrichment.ts makes to `/enrichment/status/<job_id>`.

## Observability Impact

**New signals after T02:**

- **Test count delta**: `python3 -m pytest tests/e2e/ -q --co | grep -c '::test_'` reports 99 (up from 91). A drop back to 91 means the enrichment test section was removed or not loaded.
- **Route mock intercept**: `setup_enrichment_route_mock()` in conftest.py registers a Playwright route on `**/enrichment/status/**`. If the mock is NOT triggered, enrichment slots remain in the unloaded state — `page.locator(".enrichment-slot--loaded").count()` returns 0, clearly distinguishable from a selector bug.
- **Summary row timing**: `_navigate_online_with_mock()` calls `page.wait_for_selector(".ioc-summary-row", timeout=10_000)`. A timeout here means enrichment.ts did not process the mocked response — check that the route pattern matches the actual fetch URL (visible in Playwright network trace).
- **Detail link timing**: `page.wait_for_selector(".detail-link-footer", timeout=10_000)` validates that `markEnrichmentComplete()` fired. Failure indicates `complete: true` in the mock did not propagate — check the `injectDetailLink` path in enrichment.ts.
- **Expand/collapse failure**: `expect(page.locator(".ioc-summary-row.is-open")).to_have_count(1)` reports the exact selector that was absent, pointing to a regression in the event-delegation handler on `.page-results`.

**How a future agent inspects this task:**
- Run `python3 -m pytest tests/e2e/test_results_page.py -v -k "enrichment or expand or summary_row or detail_link"` to see per-test pass/fail for enrichment surface.
- Add `--tracing on` for a Playwright trace zip that captures DOM snapshots around every `expect()` call.
- Add `--headed` to observe the enrichment animation in real time.

**Failure state visibility:**
- Route mock not registered → `.enrichment-slot--loaded` count 0, all enrichment tests timeout.
- Wrong mock pattern → network request succeeds against real server (which may 404 or return empty), enrichment.ts sees no results.
- JS regression in enrichment.ts → `.ioc-summary-row` never appears; `wait_for_selector` times out with clear message.

## Expected Output

- `tests/e2e/test_results_page.py` — 6–8 new tests added at the bottom of the file
- `tests/e2e/test_extraction.py` — docstring updated on `test_responsive_grid_layout`
- `tests/e2e/conftest.py` — route-mocking helper/fixture added
- Full suite: all tests pass, count > 91
