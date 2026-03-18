# S05: E2E test suite update — UAT

**Milestone:** M002
**Written:** 2026-03-18

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S05 is a test-only slice with no UI changes. The artifact is the test suite itself — running it with `pytest -q` is the complete and authoritative verification. No visual inspection needed.

## Preconditions

1. Working directory: `/home/chris/projects/sentinelx/.gsd/worktrees/M002`
2. Python + pytest + playwright installed (existing dev environment)
3. Flask dev server not required — Playwright launches the app via the existing `live_server` fixture
4. No external API keys required — all enrichment tests use Playwright route mocking

## Smoke Test

```bash
python3 -m pytest tests/e2e/ -q
```
**Expected:** `99 passed` in approximately 30–35 seconds.

---

## Test Cases

### 1. Full suite passes with no regressions

```bash
python3 -m pytest tests/e2e/ -q
```
1. Run the command from the working directory.
2. **Expected:** Output ends with `99 passed in XX.XXs` with no FAILED or ERROR lines.
3. Exit code must be 0.

---

### 2. Test count is ≥ 91 (coverage not reduced)

```bash
python3 -m pytest tests/e2e/ -q --co | grep -c '::test_'
```
1. Run the collection-only command.
2. **Expected:** Prints `99` (or higher). Any value ≥ 92 confirms no tests were removed.

---

### 3. ResultsPage page object has all new locators

```bash
grep -c "def \|@property" tests/e2e/pages/results_page.py
```
1. **Expected:** `70` or higher (T01 added properties and methods to reach 70 from the original ~35).

```bash
grep "def expand_row\|def collapse_row\|def is_row_expanded" tests/e2e/pages/results_page.py
```
2. **Expected:** All three lines appear — confirms the three expand/collapse helpers are present.

---

### 4. Enrichment surface tests all pass

```bash
python3 -m pytest tests/e2e/test_results_page.py -q -k "enrichment or expand or summary_row or detail_link"
```
1. Run the targeted keyword filter.
2. **Expected:** `9 passed` (the 8 new enrichment tests + `test_offline_mode_no_summary_rows`).
3. Exit code must be 0.

---

### 5. Inline expand/collapse test verifies `.is-open` toggle

```bash
python3 -m pytest tests/e2e/test_results_page.py -v -k "expand_collapse"
```
1. Run with `-v` to see the test name.
2. **Expected:** `test_expand_collapse_toggle PASSED`
3. This test:
   - Navigates in online mode with a mocked enrichment response
   - Waits for `.ioc-summary-row` to appear
   - Clicks the summary row → asserts `.is-open` present on both row and details panel
   - Clicks again → asserts `.is-open` absent (collapsed state restored)

---

### 6. Detail link injection test uses correct route

```bash
python3 -m pytest tests/e2e/test_results_page.py -v -k "detail_link"
```
1. Run with `-v`.
2. **Expected:** `test_detail_link_injected_after_enrichment_complete PASSED`
3. Confirms `.detail-link-footer` and `.detail-link` are injected, and the href contains `/detail/` (not `/ioc/`).

---

### 7. Offline mode guard test confirms clean separation

```bash
python3 -m pytest tests/e2e/test_results_page.py -v -k "offline_mode_no_summary_rows"
```
1. **Expected:** `test_offline_mode_no_summary_rows PASSED`
2. Confirms that in offline mode, zero `.ioc-summary-row` elements appear — enrichment surface is gated on the online polling pipeline, not accidentally rendered in offline mode.

---

### 8. test_responsive_grid_layout docstring is updated

```bash
grep -A 2 "def test_responsive_grid_layout" tests/e2e/test_extraction.py
```
1. **Expected:** The docstring reads `"Cards grid container is visible (single-column layout)."` — not the old `"Cards grid uses responsive layout."` text.

---

## Edge Cases

### Route mock not triggered (enrichment slots stay unloaded)

1. Run a single enrichment test with verbose output:
   ```bash
   python3 -m pytest tests/e2e/test_results_page.py -v -k "test_enrichment_slot_loaded_class_added" --tracing on
   ```
2. If the test fails, check the Playwright trace (network tab) to confirm whether any `/enrichment/status/` requests were intercepted.
3. **Expected:** Requests matching `**/enrichment/status/**` appear as intercepted (200 from mock), not as real outbound requests.
4. **Failure signal:** If count of `.enrichment-slot--loaded` is 0, the glob pattern did not match the actual URL — compare the actual request URL in the trace against the `**/enrichment/status/**` pattern.

---

### Expand/collapse handler not wiring (event delegation regression)

1. Run:
   ```bash
   python3 -m pytest tests/e2e/test_results_page.py -v -k "expand_collapse" --headed
   ```
2. Watch the Chromium window: after the route-mocked enrichment completes, click the summary row.
3. **Expected:** The row expands with `.is-open` class and the chevron rotates.
4. **Failure signal:** No `.is-open` after click → regression in `wireExpandToggles()` event delegation on `.page-results` (D018). Check `enrichment.ts` for the delegation handler.

---

### Summary row not created (enrichment.ts polling not firing)

1. Run:
   ```bash
   python3 -m pytest tests/e2e/test_results_page.py -v -k "summary_row_created" --headed
   ```
2. **Failure signal:** `wait_for_selector(".ioc-summary-row", timeout=10_000)` times out. This means enrichment.ts received the mocked response but did not call `updateSummaryRow()`. Check whether `getOrCreateSummaryRow()` in row-factory.ts can find the `.ioc-card` container via `data-ioc-value` matching the mock IOC (`8.8.8.8`).

---

## Failure Signals

| Signal | Likely Cause |
|--------|-------------|
| `XX failed` in full suite output | Selector regression in page object or DOM change in S04 output |
| `test_expand_collapse_toggle FAILED` | Event delegation removed or `.is-open` class name changed |
| `test_detail_link_injected...FAILED` | Flask detail route changed or `injectDetailLink()` href builder changed |
| `loaded_enrichment_slots.count()` == 0 | Route mock glob pattern mismatch |
| `test_offline_mode_no_summary_rows FAILED` | Enrichment surface renders unconditionally (JS guard missing) |
| Test count < 99 | Tests removed or file not saved |

---

## Requirements Proved By This UAT

- **R011** — `python3 -m pytest tests/e2e/ -q` → 99 passed; all new S01–S04 DOM elements covered by locators and tests; no coverage reduction (baseline 91, delivered 99); ResultsPage page object updated with complete selector contract

---

## Not Proven By This UAT

- Visual design quality — S05 contains no UI changes; visual proof was completed in S01–S04
- Enrichment pipeline correctness against real external APIs — all S05 tests use route mocking; real provider behavior is outside test scope
- Detail page (R012) and input page (R013) — deferred per roadmap

---

## Notes for Tester

- All enrichment tests use a single canned mock response for `8.8.8.8 / ipv4` with two providers (`VirusTotal`, `AbuseIPDB`). If you want to test a different IOC, update `MOCK_ENRICHMENT_RESPONSE_8888` in `conftest.py` — the fixture is self-contained.
- The `mocked_enrichment` pytest fixture in conftest.py pre-registers the route mock and is available for injection into any test that prefers declarative setup. `setup_enrichment_route_mock(page)` is the imperative equivalent for helper functions.
- Running with `--headed` opens a visible Chromium window — useful for watching the enrichment polling animation, chevron rotation, and expand/collapse transitions in real time.
- Playwright traces (`--tracing on`) write to the test output directory and can be opened with `playwright show-trace` for post-mortem inspection of DOM state around any assertion failure.
