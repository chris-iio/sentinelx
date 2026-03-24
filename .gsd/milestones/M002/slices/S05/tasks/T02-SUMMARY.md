---
id: T02
parent: S05
milestone: M002
provides:
  - 8 new enrichment surface E2E tests covering summary rows, expand/collapse, verdict micro-bar, detail link injection, enrichment-slot loaded state, and offline-mode guard
  - Route-mocking infrastructure (setup_enrichment_route_mock + mocked_enrichment fixture) in conftest.py
  - Updated test_responsive_grid_layout docstring in test_extraction.py
key_files:
  - tests/e2e/test_results_page.py
  - tests/e2e/conftest.py
  - tests/e2e/test_extraction.py
key_decisions:
  - Used **/enrichment/status/** (double glob) in page.route() rather than single-star so the pattern matches across path segments regardless of Playwright glob handling
  - Route mock registered BEFORE navigation in _navigate_online_with_mock() — this is critical; registering after submit races against enrichment.ts first poll
  - Removed /ioc/ href assumption from test_detail_link_injected_after_enrichment_complete; actual route is /detail/<ioc_type>/<ioc_value>
patterns_established:
  - setup_enrichment_route_mock(page) call-before-navigate pattern: always register Playwright route intercepts before the page action that triggers the fetch
  - _navigate_online_with_mock() waits for .ioc-summary-row before returning ResultsPage so all callers get a stable DOM state
observability_surfaces:
  - "python3 -m pytest tests/e2e/ -q --co | grep -c '::test_' → should report 99"
  - "python3 -m pytest tests/e2e/test_results_page.py -v -k 'enrichment or expand or summary_row or detail_link' → 9 enrichment tests"
  - "page.locator('.enrichment-slot--loaded').count() → 0 means route mock was not triggered"
duration: ~35 minutes
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Add enrichment surface tests and update test_responsive_grid_layout docstring

**Added 8 new E2E tests for the S01–S04 enrichment surface using Playwright route mocking; all 99 tests pass.**

## What Happened

Starting from 91 passing E2E tests with zero enrichment surface coverage, this task:

1. **Updated the docstring** of `test_responsive_grid_layout` in `tests/e2e/test_extraction.py` from `"Cards grid uses responsive layout."` to `"Cards grid container is visible (single-column layout)."` — test body and assertions unchanged.

2. **Added route-mocking infrastructure** to `tests/e2e/conftest.py`:
   - `MOCK_ENRICHMENT_RESPONSE_8888` — canned `EnrichmentStatus` JSON with two provider results (`VirusTotal`, `AbuseIPDB`), `complete: true`, for IOC `8.8.8.8 / ipv4`.
   - `setup_enrichment_route_mock(page, response_body=None)` — helper that calls `page.route("**/enrichment/status/**", ...)` to intercept all polling requests and return the canned response.
   - `mocked_enrichment` pytest fixture — pre-registers the mock on the test's `page`; available for tests that prefer fixture injection over explicit setup.

3. **Added `_navigate_online_with_mock()`** helper in `tests/e2e/test_results_page.py` — registers the mock, navigates to index, submits a single IP in online mode, and waits for `.ioc-summary-row` to appear (confirms the full enrichment.ts pipeline fired) before returning `ResultsPage`.

4. **Added 8 new tests** in `tests/e2e/test_results_page.py` under the `# Enrichment surface tests` section:
   - `test_online_mode_has_enrichment_slots` — enrichment slot count == IOC card count
   - `test_enrichment_summary_row_created_after_polling` — `.ioc-summary-row` appears inside `.ioc-card`
   - `test_enrichment_summary_row_has_verdict_micro_bar` — `.verdict-micro-bar` present after mock
   - `test_expand_collapse_toggle` — `.is-open` added to both row + details on click; removed on second click
   - `test_enrichment_details_has_section_containers` — at least one `.enrichment-section` inside open panel
   - `test_detail_link_injected_after_enrichment_complete` — `.detail-link-footer` and `.detail-link` injected; href contains `/detail/`
   - `test_enrichment_slot_loaded_class_added` — `.enrichment-slot--loaded` count ≥ 1
   - `test_offline_mode_no_summary_rows` — `.ioc-summary-row` count == 0 in offline mode

One iteration was needed: the plan assumed the detail link href contained `/ioc/` but the actual Flask route generates `/detail/<ioc_type>/<ioc_value>`. Fixed the assertion to check for `/detail/` instead.

## Verification

Ran three verification commands:

1. **Count check**: `python3 -m pytest tests/e2e/ -q --co | grep -c '::test_'` → **99** (up from 91, +8 new tests).
2. **Full suite**: `python3 -m pytest tests/e2e/ -q` → **99 passed, 0 failed** in 31.24s.
3. **Targeted enrichment tests**: `python3 -m pytest tests/e2e/test_results_page.py -q -k "enrichment or expand or summary_row or detail_link"` → **9 passed** (8 new + `test_offline_mode_no_summary_rows` matched by keyword).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/e2e/ -q --co \| grep -c '::test_'` | 0 | ✅ pass (99 > 91) | <1s |
| 2 | `python3 -m pytest tests/e2e/ -q` | 0 | ✅ pass (99/99) | 31.24s |
| 3 | `python3 -m pytest tests/e2e/test_results_page.py -q -k "enrichment or expand or summary_row or detail_link"` | 0 | ✅ pass (9/9) | 8.21s |

## Diagnostics

- **Route mock not triggered**: if `.enrichment-slot--loaded` count stays at 0 after `_navigate_online_with_mock()`, the Playwright route pattern didn't match the fetch URL. Check the actual URL with `--tracing on` and inspect the network log.
- **Summary row timeout**: `wait_for_selector(".ioc-summary-row", timeout=10_000)` failing means enrichment.ts did not receive/process the mocked response. Enable `--headed` to watch the polling cycle.
- **Expand/collapse failure**: `expect(.ioc-summary-row.is-open).to_have_count(1)` failing points to a regression in the event-delegation handler on `.page-results` (D018).
- **All enrichment tests failing**: run with `--tracing on`, open the trace, and inspect the network tab — if `/enrichment/status/` requests are not intercepted, the route glob pattern may need adjustment.

## Deviations

- **Detail link href path**: The plan stated the link href should contain `/ioc/`. The actual Flask route generates `/detail/<ioc_type>/<ioc_value>`. Test assertion updated to check for `/detail/` instead. No impact on coverage — the assertion still validates that `injectDetailLink()` produced a working URL.

## Known Issues

None.

## Files Created/Modified

- `tests/e2e/test_results_page.py` — 8 new enrichment surface tests + `_navigate_online_with_mock()` helper + `SINGLE_IP_IOC` constant added at bottom of file
- `tests/e2e/conftest.py` — `MOCK_ENRICHMENT_RESPONSE_8888`, `setup_enrichment_route_mock()`, and `mocked_enrichment` fixture added
- `tests/e2e/test_extraction.py` — `test_responsive_grid_layout` docstring updated
- `.gsd/milestones/M002/slices/S05/tasks/T02-PLAN.md` — `## Observability Impact` section added (pre-flight fix)
