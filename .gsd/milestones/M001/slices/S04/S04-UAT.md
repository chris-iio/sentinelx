# S04: Template Restructuring — UAT

**Milestone:** M001
**Written:** 2026-03-17

## UAT Type

- UAT mode: mixed (artifact-driven structure checks + live-runtime DOM inspection)
- Why this mode is sufficient: The structural changes are fully verifiable through template inspection, DOM queries, and computed styles. E2E suite covers the rendering pipeline end-to-end. No human judgment calls needed for section grouping correctness.

## Preconditions

- Dev server running (`flask run` or equivalent)
- At least one enrichment lookup completed for an IOC (IP, domain, or hash) with results from multiple providers
- Browser with DevTools available (Chrome 105+ or Firefox 121+ for CSS `:has()` support)

## Smoke Test

Open results page for any IP lookup. Expand an IOC card's chevron. Verify three labeled sections appear: "Infrastructure Context", "Reputation", and "No Data" — with provider rows grouped under the correct section.

## Test Cases

### 1. Three sections present in every IOC card

1. Submit a lookup for a known IP (e.g., `8.8.8.8`)
2. Wait for enrichment to complete
3. Expand the IOC card using the chevron toggle
4. Open DevTools → Console
5. Run: `document.querySelectorAll('.enrichment-section').length`
6. **Expected:** Result is a multiple of 3 (3 per IOC slot). Each `.enrichment-slot` contains exactly 3 `.enrichment-section` children inside `.enrichment-details`.

### 2. Provider rows route to correct sections

1. With the IOC card expanded from test 1, inspect the DOM
2. Run: `document.querySelectorAll('.enrichment-section--reputation .provider-detail-row').length`
3. Run: `document.querySelectorAll('.enrichment-section--context .provider-detail-row').length`
4. Run: `document.querySelectorAll('.enrichment-section--no-data .provider-detail-row').length`
5. **Expected:** Each count is ≥ 0 and the sum equals the total number of provider rows. Reputation providers (VirusTotal, AbuseIPDB, OTX, etc.) appear under Reputation. Context providers (ip-api, DNS Records, ASN Intel, etc.) appear under Infrastructure Context. Providers with no data appear under No Data.

### 3. No orphaned rows outside section containers

1. With any IOC card expanded, run in DevTools Console:
   `document.querySelectorAll('.enrichment-details > .provider-detail-row').length`
2. **Expected:** Returns `0`. All provider rows must be inside `.enrichment-section` containers, never directly inside `.enrichment-details`.

### 4. Empty sections auto-hide via CSS :has()

1. Find an IOC card where at least one section has no provider rows (e.g., an IP with no "no data" providers)
2. In DevTools, find the empty `.enrichment-section` element
3. Run: `getComputedStyle(document.querySelector('.enrichment-section--context')).display` (or whichever section is empty)
4. **Expected:** Returns `"none"` for sections with no `.provider-detail-row` children. The section header is not visible. Sections with rows return `"block"`.

### 5. Section headers are server-rendered (not JS-injected)

1. View page source (Ctrl+U / Cmd+U) for the results page
2. Search for `provider-section-header`
3. **Expected:** Section headers appear in the raw HTML source (server-rendered), not only in the live DOM. Each `.enrichment-slot` template contains exactly 3 `.provider-section-header` elements with text: "Infrastructure Context", "Reputation", "No Data".

### 6. No duplicate section headers

1. Expand an IOC card after enrichment completes
2. Run: `document.querySelectorAll('.provider-section-header').length` and divide by the number of IOC slots
3. **Expected:** Exactly 3 headers per IOC slot. No JS-injected duplicates.

### 7. No-data collapse toggle still works

1. Expand an IOC card that has some no-data providers
2. Find the no-data summary row (e.g., "5 had no record")
3. Click it
4. **Expected:** No-data provider rows become visible. The `.enrichment-section--no-data` element gains the `no-data-expanded` class. Clicking again collapses them.

### 8. Chevron expand/collapse still works

1. Click the chevron toggle on any IOC card
2. **Expected:** `.enrichment-details` expands with `is-open` class. All section containers become visible (if non-empty). Click chevron again — details collapse.

### 9. Sort order within reputation section

1. Expand an IOC card with multiple reputation providers
2. Observe the order of rows in the Reputation section
3. **Expected:** Rows are sorted by verdict severity (malicious → suspicious → clean → unknown → no data), matching the pre-S04 sort behavior. Context rows are NOT affected by sorting — they appear in arrival order within their section.

### 10. Data attributes preserved on .ioc-card

1. Inspect any `.ioc-card` element in DevTools
2. **Expected:** `data-ioc-value`, `data-ioc-type`, and `data-verdict` attributes are present on the `.ioc-card` root element, unchanged from pre-S04 behavior.

## Edge Cases

### IOC with all providers returning no-data

1. Look up an obscure/private IP that most providers won't have data for
2. Expand the IOC card
3. **Expected:** Reputation and Context sections are hidden (CSS `:has()` rule). Only the No Data section is visible with all providers listed. The no-data collapse toggle works normally.

### IOC with all providers returning verdicts (no empty sections)

1. Look up a well-known malicious IP (check VirusTotal for a known bad one)
2. Expand the IOC card
3. **Expected:** All three sections may be visible. No Data section hides if every provider returned a result.

### Rapid multiple lookups

1. Submit a bulk lookup with 3+ IOCs
2. Wait for all enrichment to complete
3. Expand each IOC card
4. **Expected:** Each card independently has 3 sections with correct routing. No cross-card contamination.

## Failure Signals

- **Visible section header with no rows beneath it:** CSS `:has()` not working — check browser version or CSS build
- **Rows appearing outside any section (directly under `.enrichment-details`):** JS routing bug — `querySelector` for section container returning null
- **More than 3 `.provider-section-header` per IOC slot:** JS is still injecting headers — `injectSectionHeadersAndNoDataSummary()` still calling removed `createSectionHeader()`
- **No-data toggle not working:** `.no-data-expanded` class may be toggled on wrong element (should be on `.enrichment-section--no-data`, not `.enrichment-details`)
- **Sort not working:** `sortDetailRows()` may be receiving wrong container (should receive `.enrichment-section--reputation`, not `.enrichment-details`)

## Requirements Proved By This UAT

- **GRP-01** — Test cases 1-6 prove provider results are grouped into three sections: Reputation, Infrastructure Context, and No Data
- **VIS-03** (partial re-validation) — Test case 5 proves category labels are now server-rendered rather than JS-injected, maintaining the visual distinction
- **GRP-02** (non-regression) — Test case 7 proves no-data collapse toggle still works after section restructuring

## Not Proven By This UAT

- **CTX-01** — Context fields in IOC card header (S05 scope)
- **CTX-02** — Staleness indicator (S05 scope)
- **VIS-01, VIS-02** — Verdict badge prominence and micro-bar (S03 scope, not affected by this slice)
- Browser compatibility below Chrome 105 / Firefox 121 / Safari 15.4

## Notes for Tester

- The 2 pre-existing E2E failures (`test_page_title`, `test_settings_page_title_tag`) are title-case mismatches unrelated to this slice. Ignore them.
- CSS `:has()` is the critical mechanism. If testing in an older browser, empty sections will show headers with no content — this is expected degradation, not a bug.
- The max-height on `.enrichment-details.is-open` was increased from 600px to 750px. If an IOC card with many providers appears to clip rows, check whether this value needs further increase.
