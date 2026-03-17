# S04: Template Restructuring — UAT

**Milestone:** M001
**Written:** 2026-03-17

## UAT Type

- UAT mode: mixed (artifact-driven structure checks + live-runtime visual confirmation)
- Why this mode is sufficient: Template structure and JS routing can be verified via DOM inspection. Visual correctness of section grouping and empty-section hiding requires live runtime with real enrichment data.

## Preconditions

- `make build` completes (typecheck + js-dev + css)
- Flask dev server running (`python3 run.py` or `flask run`)
- At least one API key configured (VirusTotal recommended) for enrichment results
- Browser with CSS `:has()` support (Chrome 105+, Firefox 121+, Safari 15.4+)

## Smoke Test

1. Navigate to the app, paste `8.8.8.8` into the input, submit
2. Wait for enrichment to complete (all provider badges resolve)
3. Click the chevron toggle to expand the provider details
4. **Expected:** Three labeled sections visible — "Infrastructure Context", "Reputation", "No Data" — each containing the appropriate provider rows. No duplicate headers. No orphaned rows outside sections.

## Test Cases

### 1. Three sections render for IP IOC

1. Submit `8.8.8.8` for enrichment
2. Wait for all providers to complete
3. Expand the IOC card details via chevron toggle
4. **Expected:** Three `.enrichment-section` containers present in the DOM. "Infrastructure Context" section contains context providers (ip-api, ASN Intel). "Reputation" section contains verdict-bearing providers (VirusTotal, AbuseIPDB, GreyNoise, etc.). "No Data" section contains providers that returned no results.

### 2. Empty section hiding

1. Submit a hash IOC: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
2. Wait for enrichment to complete
3. Expand the IOC card
4. **Expected:** "Infrastructure Context" section is not visible (no context providers for hash IOCs). Only "Reputation" and possibly "No Data" sections are visible. Inspect with DevTools: the `.enrichment-section--context` element exists in DOM but has `display: none`.

### 3. No-data collapse toggle works within section

1. Submit `8.8.8.8` for enrichment
2. Wait for completion, expand card
3. Locate the "No Data" section — it should show a summary row like "N providers had no data"
4. Click the summary row
5. **Expected:** Individual no-data provider rows expand below the summary within the `.enrichment-section--no-data` container. The `.no-data-expanded` class is on `.enrichment-section--no-data`. Click again to collapse.

### 4. Section headers are static (not JS-injected)

1. Open browser DevTools, navigate to the Network tab
2. Submit any IOC and wait for enrichment
3. Before enrichment starts, inspect `.enrichment-details` in the DOM
4. **Expected:** Three `.provider-section-header` elements ("Infrastructure Context", "Reputation", "No Data") are already present in the HTML before any JavaScript runs. They are server-rendered, not injected.

### 5. Sort order within reputation section

1. Submit `8.8.8.8` for enrichment
2. Wait for completion, expand card
3. **Expected:** Within the "Reputation" section, provider rows are sorted by verdict severity (malicious first, then suspicious, then clean). Context rows in the "Infrastructure Context" section are in their natural order (not re-sorted).

### 6. Chevron toggle still works

1. Submit any IOC, wait for enrichment
2. Click the chevron toggle to expand
3. **Expected:** Details panel smoothly expands showing all sections. Chevron rotates. Click again to collapse. The `.enrichment-details` container is the immediate next sibling of `.chevron-toggle`.

## Edge Cases

### All providers return no data

1. Submit a very obscure/private IP like `192.168.1.1` or a random hash
2. Wait for enrichment to complete
3. Expand the card
4. **Expected:** "Reputation" section is hidden (no verdict rows). "No Data" section is visible with summary row and all providers listed. "Infrastructure Context" may have ip-api/ASN results or be hidden if no context data either. CSS `:has()` correctly hides sections with zero `.provider-detail-row` children.

### Domain IOC (no ASN/ip-api context)

1. Submit `example.com`
2. Wait for enrichment, expand card
3. **Expected:** Context section shows DNS/crt.sh/ThreatMiner if they returned data. If no context providers return data, context section is hidden. Reputation section shows verdict providers. Section grouping is correct by provider type.

### Rapid multiple IOC submission (bulk mode)

1. Paste multiple IOCs (e.g., `8.8.8.8 1.1.1.1 example.com`)
2. Wait for all to complete
3. Expand each card
4. **Expected:** Each IOC card has its own three-section structure. Row routing is correct per-card — no cross-contamination between IOC cards.

## Failure Signals

- **Visible section header with no rows below it** — CSS `:has()` rule not being applied (check browser support or CSS build)
- **Provider rows appearing outside any section** — JS routing in `renderEnrichmentResult()` targeting wrong container
- **Duplicate section headers** — `injectSectionHeadersAndNoDataSummary()` still injecting headers (should be dead code now)
- **No-data toggle not working** — `.no-data-expanded` being toggled on wrong element (should be `.enrichment-section--no-data`)
- **Details panel clipped when expanded** — max-height 750px insufficient for the number of providers
- **Console errors about missing `.enrichment-section--*` selectors** — template not rendering section containers

## Requirements Proved By This UAT

- **GRP-01** — Test cases 1-5 prove provider results are grouped into three sections (Reputation, Infrastructure Context, No Data) with correct routing and empty-section hiding

## Not Proven By This UAT

- **VIS-01, VIS-02** — Verdict badge prominence and micro-bar (S03 scope, not retested here)
- **CTX-01** — Context fields in card header (S05 scope)
- **CTX-02** — Staleness indicator (S05 scope)
- **GRP-02** — No-data collapse was built in S03; test case 3 covers its continued operation within the new section structure but doesn't re-prove the original implementation

## Notes for Tester

- The 2 pre-existing E2E failures (`test_page_title`, `test_settings_page_title_tag`) are title-case mismatches unrelated to this slice — ignore them.
- CSS `:has()` is the key mechanism. If testing in an older browser, empty sections will remain visible with just the header — this is a known limitation, not a bug.
- DevTools inspection is valuable: check `getComputedStyle(el).display` on each `.enrichment-section` to confirm hiding behavior. Check `document.querySelectorAll('.enrichment-section').length` to confirm all 3 are always in the DOM.
- The function `injectSectionHeadersAndNoDataSummary()` still exists in code — its name is now misleading (it only does no-data summary, no header injection). This is intentional for git-blame continuity.
