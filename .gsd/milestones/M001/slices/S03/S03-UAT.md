# S03: Visual Redesign — UAT

**Milestone:** M001
**Written:** 2026-03-17

## UAT Type

- UAT mode: mixed (artifact-driven builds + live-runtime browser verification)
- Why this mode is sufficient: VIS-01 badge hierarchy and VIS-02 micro-bar proportions are visual-only changes requiring human eye confirmation in a live browser. Section headers and no-data collapse involve interactive DOM behavior that needs runtime testing.

## Preconditions

- `make typecheck && make js-dev && make css` all pass (already verified)
- Flask dev server running: `python -m flask run` from project root
- At least one IOC query completed with enrichment results (mix of malicious, clean, and no-data providers preferred)
- Browser open to results page at `http://127.0.0.1:5000/`

## Smoke Test

Submit an IP address known to have mixed verdicts (e.g. `8.8.8.8` or a test IOC). Verify the results page shows:
1. An enlarged verdict badge in the card header (noticeably larger than provider-row badges)
2. A colored micro-bar below the summary (not a `[3/14]` text badge)
3. Section headers ("Reputation", "Infrastructure Context") separating provider groups
4. No-data providers hidden with a count summary row visible

## Test Cases

### 1. VIS-01: Verdict badge visual hierarchy

1. Submit an IOC that returns a `malicious` worst verdict
2. Inspect the `.verdict-label` in the card header
3. Inspect any `.verdict-badge` on a provider detail row
4. **Expected:** Header `.verdict-label` is visually larger and bolder than provider `.verdict-badge`. In DevTools: `.verdict-label` computed font-size = 14px, font-weight = 700, padding ≈ 4px 12px. `.verdict-badge` computed font-size ≈ 11.5px, font-weight = 600, padding ≈ 2px 8px.

### 2. VIS-02: Micro-bar replaces consensus badge

1. Submit an IOC that returns mixed verdicts (some malicious, some clean, some no-data)
2. Look at the summary row area where the old `[n/m]` consensus badge appeared
3. **Expected:** A horizontal colored bar appears instead of text. Bar has proportional segments — red for malicious, amber for suspicious, green for clean, muted for no_data. Hover over the bar to see a title tooltip with exact counts (e.g. "2 malicious, 0 suspicious, 3 clean, 9 no data").
4. Run in DevTools: `document.querySelectorAll('.verdict-micro-bar').length` — should be ≥ 1
5. Run in DevTools: `document.querySelectorAll('.micro-bar-segment[style*="NaN"]').length` — should be 0

### 3. VIS-03: Category section headers

1. Submit an IOC (IP address works best — it has both reputation and infrastructure providers)
2. Wait for enrichment to complete (all provider rows loaded)
3. **Expected:** "Reputation" header appears above the first reputation provider row. "Infrastructure Context" header appears above the first context provider row (ip-api, DNS, ASN, etc.). Headers are uppercase, muted text, with a subtle border-top separator.
4. Run in DevTools: `document.querySelectorAll('.provider-section-header').length` — should be ≥ 1
5. Check `data-section-label` attribute on headers for correct category names

### 4. GRP-02: No-data collapse and expand toggle

1. Submit an IOC where some providers return `no_data` (most IOCs will have at least a few)
2. **Expected:** No-data provider rows are NOT visible by default. A clickable summary row shows text like "N providers had no data" (where N = count of no-data rows).
3. Click the no-data summary row
4. **Expected:** No-data rows appear below the summary. The summary row's `aria-expanded` attribute changes from `"false"` to `"true"`.
5. Click the summary row again
6. **Expected:** No-data rows hide again. `aria-expanded` changes back to `"false"`.
7. Run in DevTools: `document.querySelector('.no-data-summary-row')?.getAttribute('aria-expanded')` — should return `"true"` or `"false"` matching current state.

### 5. GRP-02: Keyboard accessibility on no-data toggle

1. Tab to the `.no-data-summary-row` element (or focus it via DevTools)
2. Press Enter
3. **Expected:** No-data rows toggle visibility (same as click)
4. Press Space
5. **Expected:** No-data rows toggle again

## Edge Cases

### Zero no-data providers

1. Submit an IOC where ALL providers return a verdict (no `no_data` or `error`)
2. **Expected:** No `.no-data-summary-row` appears. No empty collapse section. Run: `document.querySelectorAll('.no-data-summary-row').length` — should be 0.

### Zero infrastructure context rows

1. Submit a hash IOC (MD5/SHA256) — hashes typically have no IP-based context providers
2. **Expected:** No "Infrastructure Context" header appears. Only "Reputation" header (if reputation rows exist). Run: `document.querySelectorAll('.provider-section-header[data-section-label="Infrastructure Context"]').length` — should be 0.

### All providers return no-data

1. Submit a benign/unknown IOC that most providers have no record for
2. **Expected:** No-data summary row shows the full count. Section headers still appear for any categories that have at least one row with a verdict. If ALL rows are no-data, no section headers appear.

### Single-segment micro-bar

1. Submit an IOC where all providers return the same verdict (e.g. all clean)
2. **Expected:** Micro-bar shows a single full-width segment in the corresponding color. No zero-width segments visible.

## Failure Signals

- Old `[n/m]` text consensus badge visible instead of micro-bar — indicates `updateSummaryRow()` still creating `consensusBadge` span
- No section headers after enrichment completes but provider detail rows exist — indicates `injectSectionHeadersAndNoDataSummary()` not called or threw an error
- `NaN%` in micro-bar segment `style.width` — indicates division-by-zero guard bypassed. Check: `document.querySelectorAll('.micro-bar-segment[style*="NaN"]').length` (expected: 0)
- `.no-data-summary-row` without `aria-expanded` attribute — indicates toggle handler not wired. Check: `document.querySelector('.no-data-summary-row:not([aria-expanded])')` (expected: null)
- No-data rows visible without clicking the summary — indicates `.provider-row--no-data { display: none }` CSS not applied
- JavaScript console errors after enrichment completes — check browser console for errors in `injectSectionHeadersAndNoDataSummary`

## Requirements Proved By This UAT

- VIS-01 — Test case 1 proves verdict label is visually dominant via measurable font-size/weight gap
- VIS-02 — Test case 2 proves micro-bar renders with correct proportional segments and accessible title
- VIS-03 — Test case 3 proves section headers appear after enrichment with correct category labels
- GRP-02 — Test cases 4 and 5 prove no-data collapse with click/keyboard toggle and aria-expanded tracking

## Not Proven By This UAT

- GRP-01 — Three-section grouping at the template level (S04 scope — this slice only injects headers post-enrichment via JS, not server-rendered structure)
- CTX-01, CTX-02 — Context fields and staleness indicator (S05 scope)
- Perceptual effectiveness of micro-bar with extreme distributions (e.g. 1 malicious among 13 clean) — would need real analyst feedback
- Cross-browser rendering of micro-bar (tested only in Chromium via E2E; Firefox/Safari visual parity not verified)

## Notes for Tester

- The 2 pre-existing E2E test failures (`test_page_title` and `test_settings_page_title_tag`) are title-case mismatches ("sentinelx" vs "SentinelX") unrelated to this slice — ignore them.
- `.consensus-badge` CSS still exists in input.css as dead CSS — this is intentional for rollback safety. Do NOT flag it as a bug.
- Section headers are injected by JavaScript post-enrichment, not server-rendered. They appear only after ALL providers for an IOC finish loading. If you see a delay before headers appear, that's expected behavior — S04 will promote headers to the template for instant visibility.
- The micro-bar title tooltip shows raw counts, not percentages — this is by design for analyst transparency.
- `computeConsensus` and `consensusBadgeClass` still exported from verdict-compute.ts — intentionally preserved for API stability during transition. Not a cleanup omission.
