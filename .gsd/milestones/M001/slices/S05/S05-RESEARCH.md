# S05 ("Context And Staleness") — Research

**Date:** 2026-03-17
**Confidence:** HIGH — all relevant modules read directly; patterns follow established S03/S04 conventions

## Summary

S05 delivers two independent features: **CTX-01** (key context fields visible in the IOC card header without expanding) and **CTX-02** (cache staleness indicator in the summary row). Both are additive — they inject new DOM elements into existing card structure without modifying any existing elements or contracts. Neither requires backend changes, new Python routes, or new TypeScript modules.

**CTX-01** requires `enrichment.ts` to populate a new `.ioc-context-line` element inside the card (between card header and enrichment slot) when a context provider result arrives. The target context fields are:

- **IP IOCs:** GeoIP location from "IP Context" provider (`raw_stats.geo` — pre-formatted as "CC · City · AS12345 (ISP Name)") and ASN from "ASN Intel" provider (`raw_stats.asn`/`raw_stats.prefix`)
- **Domain IOCs:** No registrar data exists in any adapter. Available context is DNS A records from "DNS Records" and cert count from "Cert History" — lower value for inline display. Recommend showing DNS A record IPs if available, otherwise skip for domains.

**CTX-02** adds a staleness badge to the `.ioc-summary-row` when any verdict results were served from cache. The `cached_at` field already exists on `EnrichmentResultItem` and `formatRelativeTime()` already exists in `row-factory.ts`. The staleness indicator surfaces the oldest `cached_at` across all verdict entries for an IOC.

Both features fit cleanly into the existing S03/S04 patterns: new DOM elements created via `createElement + textContent` (SEC-08), new CSS classes in `input.css`, and modifications scoped to `enrichment.ts` and `row-factory.ts`.

## Recommendation

Split into two independent tasks:

1. **CTX-01 (Context fields in card header)** — Modify `enrichment.ts` context provider branch to also populate an inline context element in the card. Add `createContextLine()` to `row-factory.ts`. Add `.ioc-context-line` CSS.
2. **CTX-02 (Staleness indicator in summary row)** — Modify `updateSummaryRow()` in `row-factory.ts` to accept the `iocVerdicts` entries that have `cached_at` and append a staleness badge. Add `.staleness-badge` CSS.

Build CTX-01 first — it's the higher-complexity feature with a timing consideration (context results arrive incrementally during polling). CTX-02 is a straightforward addition to an existing function.

## Implementation Landscape

### Key Files

- **`app/static/src/ts/modules/enrichment.ts`** — The context provider branch (line ~215) currently routes context results only to `.enrichment-section--context`. Must be extended to also populate the inline context line in the card. This is the primary code change for CTX-01.
- **`app/static/src/ts/modules/row-factory.ts`** — Add `createContextLine(result)` function that extracts key fields from `raw_stats` and builds a compact inline element. Modify `updateSummaryRow()` to accept an optional `allResults` parameter (or a separate cached_at array) for staleness.
- **`app/templates/partials/_ioc_card.html`** — Add an empty `.ioc-context-line` placeholder div between the card header (or `.ioc-original`) and the enrichment slot. Server-rendered empty; JS populates it on context result arrival. This follows the S04 pattern of server-rendered containers that JS fills.
- **`app/static/src/input.css`** — Add `.ioc-context-line` and `.staleness-badge` component classes.
- **`app/static/src/ts/types/api.ts`** — No changes needed. `cached_at?: string` and `raw_stats: Record<string, unknown>` are already typed correctly.

### Context Provider Data Available Per IOC Type

**IP IOCs (ipv4/ipv6):**
- "IP Context" (`raw_stats.geo`): Pre-formatted string like "US · San Francisco · AS24940 (Hetzner Online GmbH)". Also has `raw_stats.country_code`, `raw_stats.asname`, `raw_stats.reverse`. **Best candidate for inline display — `geo` is ready to render as-is.**
- "ASN Intel" (`raw_stats.asn`, `raw_stats.prefix`, `raw_stats.rir`, `raw_stats.allocated`): ASN number + CIDR prefix. Overlaps with IP Context's `as_info`. Lower priority for inline display since IP Context already provides ASN.
- "AbuseIPDB" is a verdict provider but has `raw_stats.countryCode` and `raw_stats.isp` — not useful here since IP Context covers this.

**Domain IOCs:**
- "DNS Records" (`raw_stats.a`, `raw_stats.mx`, `raw_stats.ns`, `raw_stats.txt`): DNS record arrays. Could show A record IPs inline.
- "Cert History" (`raw_stats.cert_count`, `raw_stats.earliest`, `raw_stats.latest`, `raw_stats.subdomains`): Cert count and date range.
- No registrar/WHOIS data exists in any adapter. CTX-01 requirement mentions "registrar for domains" but this data is not available. Recommend scoping domain inline context to DNS A records if non-empty, or omitting for domains entirely.

**Hash/URL/CVE IOCs:**
- No context providers serve these types. CONTEXT_PROVIDERS set: "IP Context" (ipv4/ipv6), "DNS Records" (domain), "Cert History" (domain), "ThreatMiner" (ipv4/domain), "ASN Intel" (ipv4/ipv6). Hash, URL, and CVE types have no context providers, so the inline context line stays empty/hidden for those IOC types.

### CTX-01: Inline Context Line Architecture

**Where in the DOM:**
Insert an empty `.ioc-context-line` div in `_ioc_card.html`, positioned after the `.ioc-original` (or after the header if no original), before the enrichment slot `{% include %}`. This is a static placeholder that hides itself via CSS when empty (`:empty { display: none }`).

**When it gets populated:**
In `enrichment.ts`, the context provider branch (line ~215) already has the `result` with `raw_stats`. After appending the context row to `.enrichment-section--context`, also call a new function like `updateContextLine(card, result)` that:
1. Finds `.ioc-context-line` in the card
2. Extracts the appropriate field based on provider name:
   - "IP Context" → use `raw_stats.geo` (the full "CC · City · ASN" string)
   - "ASN Intel" → use `raw_stats.asn` + `raw_stats.prefix` (if IP Context hasn't populated yet)
   - "DNS Records" → use `raw_stats.a` (show first 2-3 A record IPs)
   - Others → skip
3. Appends a small text span to the `.ioc-context-line` (or replaces if same provider re-renders — dedup by provider name)

**Timing concern (resolved):** Context providers may arrive before or after verdict providers. This is not a problem because the `.ioc-context-line` is a separate element from the summary row. It's populated independently of verdict flow. The only edge case is "IP Context" and "ASN Intel" both providing ASN info for the same IP — resolve by giving "IP Context" priority (its `geo` field is more comprehensive). If IP Context has already populated the line, skip ASN Intel's contribution.

### CTX-02: Staleness Badge Architecture

**Where in the DOM:**
Appended to the `.ioc-summary-row` after the micro-bar. A small `.staleness-badge` span saying "cached 4h ago" styled similarly to the existing `.cache-badge` on detail rows.

**When it gets populated:**
`updateSummaryRow()` already rebuilds the summary row on every verdict result. It receives `iocVerdicts[iocValue]` entries. The issue: `VerdictEntry` doesn't currently carry `cached_at`. Two approaches:

- **Option A (recommended):** Pass the raw results alongside verdicts. `enrichment.ts` already has the full `EnrichmentItem` at render time. Add an optional `cachedAt` field to `VerdictEntry` populated from `result.cached_at` when available. `updateSummaryRow()` then checks if any entries have `cachedAt` and shows the oldest.
- **Option B:** Track cached_at separately in a `Record<string, string[]>` map in `enrichment.ts` and pass to `updateSummaryRow()`. More plumbing, no real benefit.

Option A is simpler: add `cachedAt?: string` to the `VerdictEntry` interface in `verdict-compute.ts`, populate it in `enrichment.ts` when `result.cached_at` exists, and read it in `updateSummaryRow()`.

### Build Order

1. **CTX-01 first** — It's the higher-value, higher-complexity feature. Involves template change + enrichment.ts routing + new row-factory function + CSS. Getting the template placeholder and JS population pattern right is the riskiest part.
2. **CTX-02 second** — Simple addition to `updateSummaryRow()` in row-factory.ts + `VerdictEntry` interface extension in verdict-compute.ts + CSS for staleness badge. Low risk, builds on established patterns.
3. **E2E verification + build** — Run full test suite, rebuild JS/CSS bundles.

### Verification Approach

- `make typecheck` — zero TypeScript errors
- `make js-dev` — esbuild bundle compiles
- `make css` — Tailwind rebuild succeeds
- `pytest tests/ -m e2e --tb=short -q` — 89 passed, 2 failed (pre-existing title-case)
- `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` — only comment in graph.ts (SEC-08)
- Verify `.ioc-context-line` exists in template between card header and enrichment slot
- Verify `:empty` CSS rule on `.ioc-context-line` hides it when no context arrives
- Verify `VerdictEntry` now has optional `cachedAt` field
- Verify `updateSummaryRow()` renders staleness badge when `cachedAt` values present
- Verify no existing CSS classes or data attributes were renamed or moved

## Constraints

- **SEC-08**: All DOM construction must use `createElement + textContent`. No `innerHTML` or `insertAdjacentHTML`.
- **No backend changes**: S05 is presentation-only. No new Python routes, no new template context variables. The `cached_at` and `raw_stats` data already flow from Flask to the browser.
- **No registrar data available**: The CTX-01 requirement mentions "registrar for domains" but no adapter returns WHOIS/registrar data. Scope domain inline context to DNS A records or omit.
- **Max-height 750px on `.enrichment-details.is-open`**: S04 forward intelligence warns this may need increase. The context line is *outside* `.enrichment-details` (in the card body, before the slot), so it doesn't affect this cap.
- **`.ioc-context-line` must not break existing card layout**: The `.ioc-card-header` flex layout and the `.ioc-card` data attributes are contracts. The new element sits between the header/original and the enrichment slot — it's additive.

## Common Pitfalls

- **Populating context line from non-context providers** — Only `CONTEXT_PROVIDERS` results should populate the inline context line. Verdict providers like AbuseIPDB also have `countryCode`/`isp` in raw_stats but must NOT be used for CTX-01 — mixing verdict provider data into the context display breaks the information architecture separation established in S03/S04.
- **Duplicate ASN info from IP Context + ASN Intel** — Both providers return ASN data for IP IOCs. Give IP Context priority (its `geo` string is pre-formatted and more useful). If IP Context has already populated the line, don't overwrite with ASN Intel's data.
- **Staleness badge showing on non-cached results** — Only show the staleness badge when at least one verdict entry has a `cachedAt` value. If all results are fresh (no `cached_at` in API response), no badge should appear.
- **Context line visible for IOC types with no context providers** — Hash, URL, CVE types have no context providers. The `.ioc-context-line` container should use `:empty { display: none }` CSS to hide itself automatically when JS doesn't populate it.
