# S03: Visual Redesign — UAT

**Milestone:** M001
**Written:** 2026-03-17

## UAT Type

- UAT mode: live-runtime
- Why this mode is sufficient: All four requirements (VIS-01, VIS-02, VIS-03, GRP-02) produce visible DOM changes that must be verified in a running browser against real enrichment results. Code inspection confirmed correctness, but visual hierarchy and interaction behavior require human confirmation.

## Preconditions

1. `make css && make js-dev` completed successfully (dist files up to date)
2. App running locally: `flask run` or equivalent — accessible at http://127.0.0.1:5000
3. At least one IOC submitted in **online mode** with enrichment results from multiple providers (ideally an IP address for context provider coverage)
4. Enrichment polling completes (progress bar shows "Enrichment complete")

## Smoke Test

After enrichment completes on any IOC card: expand the details (click chevron) and confirm you see section headers ("Reputation", "Infrastructure Context"), colored micro-bar in the summary row, and — if any providers returned no data — a clickable "N providers had no record" summary line.

## Test Cases

### 1. VIS-01 — Verdict badge prominence hierarchy

1. Submit an IP address in online mode (e.g., `8.8.8.8`)
2. Wait for enrichment to complete
3. Inspect the IOC card header — find the verdict label (e.g., "CLEAN", "MALICIOUS")
4. Expand the details (click chevron)
5. Compare the header verdict label to the per-provider verdict badges in detail rows
6. **Expected:** Header `.verdict-label` is visibly larger and bolder than provider row `.verdict-badge` — computed font-size ~14px vs ~11.5px, weight 700 vs 600, with larger padding

### 2. VIS-02 — Verdict micro-bar replaces consensus text

1. On the same IOC card, look at the summary row (below the card header, above the chevron)
2. **Expected:** A thin colored bar (6px tall) appears at the right side of the summary row — NOT a text badge like `[2/5]`
3. Hover over the micro-bar
4. **Expected:** Tooltip shows exact counts, e.g., "1 malicious, 0 suspicious, 3 clean, 2 no data"
5. Verify that segments are proportionally sized — if 3 of 5 providers are clean, the clean (sky blue) segment should be ~60% of the bar width
6. **Expected:** Zero-count segments are not visible (no empty gaps)

### 3. VIS-03 — Category section headers

1. On an IOC card with both context providers (IP Context, DNS Records, etc.) and verdict providers (VirusTotal, AbuseIPDB, etc.), expand the details
2. **Expected:** An "Infrastructure Context" header appears above the context provider rows
3. **Expected:** A "Reputation" header appears above the verdict provider rows
4. **Expected:** Headers are uppercase, small font, muted color, with a border-top separator
5. If the IOC type only has context providers (unlikely) or only verdict providers, only the relevant header should appear

### 4. GRP-02 — No-data collapse and expand

1. Submit an IOC that produces some "no data" or "error" results (e.g., a clean domain where some providers have no record)
2. Expand the details
3. **Expected:** No-data/error provider rows are NOT visible by default
4. **Expected:** A summary line appears: "N providers had no record" (where N is the count of hidden rows)
5. Click the summary line
6. **Expected:** No-data/error rows appear below the summary line; the summary row's `aria-expanded` changes to "true"
7. Click the summary line again
8. **Expected:** No-data rows collapse back to hidden; `aria-expanded` changes to "false"

### 5. GRP-02 — Keyboard accessibility

1. Tab to the "N providers had no record" summary row
2. Press Enter
3. **Expected:** No-data rows expand (same as click)
4. Press Space
5. **Expected:** No-data rows collapse (same as click)

## Edge Cases

### All providers return data (no no-data rows)

1. If an IOC gets results from all providers with no "no_data" or "error" verdicts
2. **Expected:** No "providers had no record" summary row appears. Only section headers are visible.

### Single-provider result

1. Submit a hash IOC that only triggers one provider (e.g., CIRCL Hashlookup)
2. Wait for enrichment to complete
3. **Expected:** Micro-bar shows a single full-width segment. Title tooltip shows correct single count. No NaN% widths in element inspector.

### All providers return no data

1. Submit an obscure IOC that no provider recognizes
2. Expand details
3. **Expected:** Summary line says "N providers had no record". All rows hidden by default. "Reputation" header may or may not appear (depends on whether any verdict providers responded — error counts as a verdict row). No crash, no empty section headers with no rows below them.

## Failure Signals

- Micro-bar shows `NaN%` width segments — division-by-zero bug in `computeVerdictCounts()`
- No micro-bar visible in summary row — `updateSummaryRow()` not creating it; check for JS errors in console
- No section headers after enrichment completes — `injectSectionHeadersAndNoDataSummary` not called; check that `markEnrichmentComplete()` fires
- No-data rows visible by default (not hidden) — `.provider-row--no-data` class not applied or CSS not loaded; check `createDetailRow()` verdict condition
- Console JS errors mentioning `injectSectionHeadersAndNoDataSummary` or `computeVerdictCounts`
- Summary row still shows `[n/m]` text badge instead of micro-bar — old `consensusBadge` code not removed
- Clicking no-data summary row does nothing — event listener not wired; check for JS errors

## Requirements Proved By This UAT

- VIS-01 — Visual badge hierarchy confirmed by human inspection of rendered font sizes
- VIS-02 — Micro-bar rendering, proportional widths, tooltip, and zero-count segment skipping
- VIS-03 — Section headers positioned correctly relative to category groups
- GRP-02 — No-data collapse default state, click toggle, count accuracy, keyboard accessibility

## Not Proven By This UAT

- Pixel-perfect sizing — no automated screenshot comparison; relies on human visual judgment
- Edge cases with >20 providers — current provider set is 14; scaling behavior not tested
- Micro-bar rendering across different browser zoom levels
- Performance impact of post-enrichment DOM injection with very large IOC batches

## Notes for Tester

- The 2 pre-existing E2E failures (test_page_title, test_settings_page_title_tag) are title-case mismatches unrelated to this slice — ignore them.
- `.consensus-badge` CSS remains in the stylesheet as dead CSS — this is intentional for rollback safety. If you see consensus badge rules in DevTools, that's expected; they're just not applied to any DOM elements.
- Section headers only appear AFTER enrichment completes — during active polling, the details container shows unsorted/unsectioned rows. This is by design.
- For best coverage, test with an IP address (triggers both context and verdict providers) and a hash (triggers only verdict providers) to exercise the "one header vs two headers" paths.
