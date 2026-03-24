# S05: Context And Staleness — UAT

**Milestone:** M001
**Written:** 2026-03-17

## UAT Type

- UAT mode: live-runtime
- Why this mode is sufficient: CTX-01 and CTX-02 both depend on asynchronous enrichment data arriving from real providers. Static artifact inspection can verify template structure and CSS rules but cannot confirm that `updateContextLine()` fires with real geo/ASN/DNS data or that staleness badges render from real `cached_at` timestamps. Live runtime with a real (or fixture-backed) enrichment cycle is required.

## Preconditions

1. Application server is running (`make run` or `flask run`)
2. At least one IP IOC result is available (search a known public IP such as `8.8.8.8` or load a fixture that includes an IP with IP Context / ASN Intel provider results)
3. At least one domain IOC result is available (e.g., `example.com` or a fixture with DNS Records provider results)
4. At least one cached result is available — either a previously searched IOC served from cache, or a fixture that includes `cached_at` timestamps on one or more provider results
5. Browser developer tools available (console access for diagnostic queries)

## Smoke Test

Navigate to a results page for an IP IOC. Within 5 seconds of enrichment completing, the IOC card header should show a one-line context string (e.g., "United States, Mountain View (AS15169 GOOGLE)") without clicking any accordion or expand control.

---

## Test Cases

### 1. IP IOC — GeoIP context visible in card header

1. Search for a known public IP (e.g., `8.8.8.8`).
2. Wait for enrichment to complete (provider rows populate).
3. Inspect the IOC card header — do **not** expand any section.
4. **Expected:** A context line below the IOC value shows GeoIP data: country, city, and ASN in the format "Country, City (ASXXXXX ORG)". The data comes from the "IP Context" provider.
5. Open browser console and run: `document.querySelectorAll('.ioc-context-line:not(:empty)').length`
6. **Expected:** Returns `1` (or more if multiple IP IOCs are present).
7. Run: `document.querySelector('.ioc-context-line span')?.getAttribute('data-context-provider')`
8. **Expected:** Returns `"IP Context"`.

### 2. IP IOC — ASN Intel fallback when IP Context absent

1. Search for an IP IOC where only "ASN Intel" is configured (or mock IP Context to return no-data).
2. Wait for enrichment to complete.
3. Inspect the IOC card header context line.
4. **Expected:** Context line shows ASN + prefix (e.g., "AS15169 / 8.8.8.0/24") from ASN Intel provider.
5. Run: `document.querySelector('.ioc-context-line span')?.getAttribute('data-context-provider')`
6. **Expected:** Returns `"ASN Intel"`.

### 3. IP IOC — IP Context replaces ASN Intel when both fire

1. Search for an IP IOC where both "IP Context" and "ASN Intel" are enabled.
2. Wait for full enrichment.
3. **Expected:** Context line shows only **one** span — the IP Context data (more comprehensive). ASN Intel data is not shown alongside it.
4. Run: `document.querySelectorAll('.ioc-context-line span').length`
5. **Expected:** Returns `1`.
6. Run: `document.querySelector('.ioc-context-line span')?.getAttribute('data-context-provider')`
7. **Expected:** Returns `"IP Context"` (not `"ASN Intel"`).

### 4. Domain IOC — DNS A records visible in card header

1. Search for a domain IOC (e.g., `example.com`).
2. Wait for enrichment to complete.
3. Inspect the domain IOC card header — do **not** expand any section.
4. **Expected:** Context line shows up to 3 resolved A-record IPs (e.g., "93.184.216.34").
5. Run: `document.querySelector('.ioc-context-line span')?.getAttribute('data-context-provider')`
6. **Expected:** Returns `"DNS Records"`.

### 5. Hash/URL/CVE IOC — context line hidden

1. Search for a hash, URL, or CVE IOC.
2. Wait for enrichment to complete.
3. Inspect the IOC card header area where the context line would appear.
4. **Expected:** No context line is visible — the `.ioc-context-line` div is present in the DOM but hidden by CSS (`:empty { display: none }`).
5. Run: `document.querySelector('.ioc-context-line')` — verifies the element exists.
6. **Expected:** Element found (not null).
7. Run: `window.getComputedStyle(document.querySelector('.ioc-context-line')).display`
8. **Expected:** Returns `"none"`.

### 6. Cached IOC — staleness badge in summary row

1. Search for an IOC that returns cached results (previously searched, or use a fixture with `cached_at` timestamps).
2. Wait for enrichment to complete.
3. Inspect the IOC summary row (the collapsed card header with verdict badge and micro-bar).
4. **Expected:** A muted badge to the right of the summary row reads "cached Xh ago" (or "cached Xm ago" for recent cache), where X is the time since the oldest `cached_at` timestamp across all providers.
5. Run: `document.querySelectorAll('.staleness-badge').length`
6. **Expected:** Returns `1` (or more if multiple IOCs have cached results).
7. Run: `document.querySelector('.staleness-badge')?.textContent`
8. **Expected:** String contains "cached" and a relative time unit (e.g., "cached 4h ago", "cached 2d ago").

### 7. Fresh IOC — no staleness badge

1. Search for a new IOC that has never been searched before (guaranteed fresh results).
2. Wait for enrichment to complete.
3. Inspect the IOC summary row.
4. **Expected:** No staleness badge is present.
5. Run: `document.querySelectorAll('.staleness-badge').length`
6. **Expected:** Returns `0`.

---

## Edge Cases

### Multiple providers cached at different ages — oldest wins

1. Search for an IOC where some providers return cached results and others return fresh results.
2. Wait for enrichment.
3. Locate the `.staleness-badge` if present.
4. **Expected:** The badge shows the age of the **oldest** cached_at timestamp among all providers (worst-case data age, not best-case).

### Domain IOC with more than 3 A records

1. Search for a domain that resolves to more than 3 IP addresses.
2. **Expected:** Context line shows exactly 3 IPs (first three), not all of them. No overflow or truncation error.

### Context line DOM structure — :empty rule

1. On any results page, open DevTools and inspect a hash IOC's `.ioc-context-line` element.
2. **Expected:** The div has **no child nodes** (not even whitespace text nodes), confirming the template renders `<div class="ioc-context-line"></div>` without inner whitespace. This is required for the `:empty` CSS rule to fire.

---

## Failure Signals

- **Context line visible but blank for IP IOC:** `updateContextLine()` was called but `result.raw_stats.geo` was absent. Check the network tab for the IP Context provider response — geo field may be missing or null.
- **Context line not visible for IP IOC when IP Context provider has data:** `updateContextLine()` was not called. Check that the `enrichment.ts` context provider branch routes "IP Context" calls to `updateContextLine()`.
- **ASN Intel data still showing alongside IP Context:** The dedup replacement logic failed. Check that `data-context-provider` attribute is being set on ASN Intel spans and that the replacement lookup by attribute works correctly.
- **Staleness badge missing when a cached result is present:** `result.cached_at` was not propagated to `VerdictEntry.cachedAt`. Check that `result.type === "result"` on the cached response (error results do not carry `cachedAt`).
- **Staleness badge shows raw ISO timestamp instead of relative time:** `formatRelativeTime()` failed to parse the timestamp. The timestamp format may not be ISO 8601 UTC.
- **CSS `:empty` not hiding context line for hash IOC:** Inner whitespace is present in the template's `.ioc-context-line` div. Verify `<div class="ioc-context-line"></div>` has no whitespace between tags.
- **E2E regression:** Any test count other than exactly 89 passed / 2 failed indicates a regression. The 2 pre-existing failures are `test_page_title[chromium]` and `test_settings_page_title_tag[chromium]` (title-case mismatch).

---

## Requirements Proved By This UAT

- **CTX-01** — Test cases 1–5 prove that GeoIP/ASN data appears inline in IP IOC headers, DNS A records appear in domain headers, dedup works between IP Context and ASN Intel, and the context line is hidden for unsupported IOC types.
- **CTX-02** — Test cases 6–7 prove that staleness badges appear for cached results with correct relative time and are absent for fresh results.

## Not Proven By This UAT

- Provider configuration edge cases (e.g., what happens if "IP Context" adapter is disabled in settings but "ASN Intel" is enabled — ASN Intel should fill in, but this requires provider config control).
- Very large staleness values (e.g., cache from months ago) — `formatRelativeTime()` may return unexpected strings for extreme durations.
- Concurrent searches — multiple IOCs completing enrichment simultaneously and racing to update context lines.
- Mobile/small viewport rendering — the context line and staleness badge are styled for desktop; truncation on narrow viewports is not tested.

## Notes for Tester

- The two pre-existing E2E failures (`test_page_title` and `test_settings_page_title_tag`) are **expected** and unrelated to S05 work — both test for "SentinelX" but the page title is "sentinelx". Do not investigate these.
- If live provider credentials are not configured, use fixture data with pre-seeded `raw_stats.geo` and `cached_at` fields to trigger context lines and staleness badges without real API calls.
- The staleness badge appears in the **summary row** (the collapsed card header), not inside the accordion sections. Look at the row-level flex container, not the expanded provider detail section.
- `data-context-provider` attributes on context spans are the primary diagnostic tool — they identify which provider won the dedup race and are visible in DevTools element inspector.
