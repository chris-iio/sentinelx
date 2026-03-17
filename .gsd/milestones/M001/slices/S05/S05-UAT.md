# S05: Context And Staleness — UAT

**Milestone:** M001
**Written:** 2026-03-17

## UAT Type

- UAT mode: mixed
- Why this mode is sufficient: Context line placement and staleness badge appearance are visual features that need human confirmation of layout and readability. Build + E2E tests confirm no regressions but cannot judge visual coherence.

## Preconditions

- App running locally: `flask run` or `make run` on default port
- At least one IP IOC and one domain IOC submitted for enrichment (online mode with provider API keys configured)
- At least one previous enrichment cached (to verify staleness badge — run the same IOC twice with >1 minute gap, or seed cache)

## Smoke Test

Submit an IP address (e.g., `93.184.216.34`) in online mode. Before expanding the IOC card, confirm a line of muted text appears between the IOC value and the enrichment rows showing country/city/org info (e.g., "US · San Francisco · AS24940 (Hetzner Online GmbH)").

## Test Cases

### 1. IP IOC context line displays GeoIP and ASN data

1. Navigate to the search page
2. Enter a known public IP address (e.g., `8.8.8.8`) and submit
3. Wait for enrichment to complete (all provider rows populated)
4. Look at the IOC card **before expanding** — between the IOC value and the enrichment section
5. **Expected:** A muted text line shows geographic context, e.g., "US · Mountain View · AS15169 (Google LLC)". The line should contain country, city, and ASN org separated by middle dots.

### 2. Domain IOC context line displays A-record IPs

1. Navigate to the search page
2. Enter a known domain (e.g., `example.com`) and submit
3. Wait for enrichment to complete
4. Look at the IOC card before expanding
5. **Expected:** A muted text line shows resolved A-record IPs (up to 3), e.g., "A: 93.184.216.34". If the domain has multiple A records, up to 3 are shown.

### 3. Hash IOC has no context line visible

1. Enter a known hash (e.g., a SHA256 from MalwareBazaar) and submit
2. Wait for enrichment to complete
3. Look at the IOC card before expanding
4. **Expected:** No context line is visible — there should be no extra space or blank line between the IOC value and the enrichment section. (The `.ioc-context-line` div exists in DOM but is hidden via `:empty` CSS.)

### 4. Staleness badge appears for cached results

1. Submit an IP address and let enrichment complete
2. Wait at least 1 minute
3. Submit the same IP address again
4. Wait for enrichment to complete (should be fast — served from cache)
5. **Expected:** The summary row shows a staleness badge on the right side, e.g., "cached 2m ago" or "cached 1h ago" depending on cache age. The text should be muted/small and right-aligned relative to the micro-bar.

### 5. Staleness badge absent for fresh results

1. Submit an IP address that has never been queried before (or clear cache first)
2. Wait for enrichment to complete
3. **Expected:** No staleness badge appears in the summary row — only the verdict label and micro-bar are present.

### 6. Multiple IOC types in one submission

1. Enter mixed text containing an IP, a domain, and a hash (e.g., "Check 8.8.8.8 and example.com and 44d88612fea8a8f36de82e1278abb02f")
2. Submit and wait for all enrichment to complete
3. **Expected:**
   - IP card: context line shows GeoIP/ASN data
   - Domain card: context line shows A-record IPs
   - Hash card: no context line visible
   - All three cards render correctly without layout shifts or overlapping elements

## Edge Cases

### ASN Intel arrives before IP Context

1. This is provider timing-dependent and may not be reproducible on demand
2. If observable: ASN Intel initially populates the context line with ASN number + prefix
3. When IP Context subsequently arrives, the ASN span is replaced with the richer geo data
4. **Expected:** Final context line shows full geo info (country · city · org), not duplicate ASN data

### Very old cached data

1. If cache contains data from >24h ago (manually seed or time-shift)
2. Submit the IOC
3. **Expected:** Staleness badge shows appropriate relative time (e.g., "cached 2d ago"), not a raw ISO timestamp

### Context providers return no data

1. Submit an IP that geo-lookup cannot resolve (e.g., a private/reserved IP like `10.0.0.1` if it passes extraction)
2. **Expected:** Context line stays hidden (`:empty` rule) — no blank space appears

## Failure Signals

- Context line shows raw JSON or `[object Object]` instead of formatted text — `updateContextLine()` is accessing wrong property path
- Context line visible for hash/URL/CVE IOC types — `:empty` CSS rule is broken or context providers are incorrectly routing data
- Staleness badge shows raw ISO timestamp instead of relative time — `formatRelativeTime()` is failing silently
- Staleness badge appears on every result including fresh ones — `cachedAt` is being populated from a wrong field
- Layout shift when context line appears — CSS height transition or missing space allocation
- `innerHTML` or `insertAdjacentHTML` found in source — SEC-08 violation (run `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/`)

## Requirements Proved By This UAT

- CTX-01 — Test cases 1, 2, 3, and 6 prove that key context fields are visible in IOC card header without expanding, and correctly absent for non-context IOC types
- CTX-02 — Test cases 4 and 5 prove that staleness indicator appears only when cached results are served and shows meaningful relative time

## Not Proven By This UAT

- VIS-01 through GRP-02 — these were implemented in S03/S04 and should have separate UAT
- Staleness badge behavior when cache is cleared mid-session
- Context line rendering with providers that return partial data (e.g., geo with country but no city)
- Performance impact of context line rendering on pages with many IOCs (50+)

## Notes for Tester

- The context line content depends entirely on which providers are configured and responding. If IP Context provider (ip-api.com) is down, the line may show only ASN Intel data or nothing.
- The "registrar" field mentioned in the original requirement description (CTX-01) is intentionally not implemented — WHOIS/RDAP was previously scoped out due to GDPR redaction. DNS A-records are shown for domains instead.
- The 2 pre-existing E2E test failures (title-case mismatch) are unrelated to S05 and predate the v1.1 redesign.
- To verify diagnostic surfaces in browser console:
  - `document.querySelectorAll('.ioc-context-line:not(:empty)').length` — should match number of IP/domain IOC cards
  - `document.querySelectorAll('.staleness-badge').length` — should be >0 when cached results shown
  - `getComputedStyle(document.querySelector('.ioc-card[data-ioc-type="hash"] .ioc-context-line')).display` — should be `'none'`
