# S05: Context And Staleness

**Goal:** Key context fields and cache age are visible in the IOC card header without requiring any accordion expansion.
**Demo:** IP IOCs show GeoIP location (country, city, ASN) in card header; domain IOCs show resolved A record IPs in card header; cached results show staleness indicator ("cached 4h ago") in summary row; all E2E tests pass at baseline.

## Must-Haves

- CTX-01: For IP IOCs, GeoIP location string from "IP Context" provider visible in card header without expanding
- CTX-01: "ASN Intel" provider populates context line only if "IP Context" hasn't already (dedup)
- CTX-01: For domain IOCs, resolved DNS A record IPs visible in card header (no registrar data available in any adapter)
- CTX-01: Context line hides via CSS `:empty` for IOC types with no context providers (hash, URL, CVE)
- CTX-02: Staleness badge shows oldest `cached_at` across all verdict entries for an IOC
- CTX-02: No staleness badge appears when all results are fresh
- All DOM construction uses `createElement + textContent` only (SEC-08)
- E2E baseline maintained: 89 pass, 2 pre-existing failures

## Proof Level

- This slice proves: integration
- Real runtime required: yes (context data arrives asynchronously during enrichment polling)
- Human/UAT required: no

## Verification

- `make typecheck` — zero TypeScript errors
- `make js-dev` — esbuild bundle compiles
- `make css` — Tailwind rebuild succeeds
- `pytest tests/ -m e2e --tb=short -q` — 89 passed, 2 failed (pre-existing title-case only)
- `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` — only comment in graph.ts (SEC-08)
- `grep -n "ioc-context-line" app/templates/partials/_ioc_card.html` — placeholder div present
- `grep -n "updateContextLine" app/static/src/ts/modules/enrichment.ts` — called in context provider branch
- `grep -n "staleness-badge" app/static/src/ts/modules/row-factory.ts` — rendered in updateSummaryRow
- `grep -n "cachedAt" app/static/src/ts/modules/verdict-compute.ts` — field on VerdictEntry interface
- **Failure-path check:** `document.querySelectorAll('.ioc-context-line').length` equals `.ioc-card` count (placeholder always present even when empty), and `document.querySelectorAll('.ioc-context-line:not(:empty)').length` is zero for IOC types with no context providers — confirms `:empty` hiding works and context line never shows stale/wrong data for unsupported types

## Observability / Diagnostics

- Runtime signals: `.ioc-context-line` children carry `data-context-provider` attributes identifying which provider sourced the data; `.staleness-badge` textContent shows relative cache age
- Inspection surfaces: `document.querySelectorAll('.ioc-context-line:not(:empty)').length` — count of IOCs with inline context; `document.querySelectorAll('.staleness-badge').length` — count of IOCs with cached results; per-card: `card.querySelector('.ioc-context-line span')?.getAttribute('data-context-provider')` identifies the source
- Failure visibility: If an IP IOC's `.ioc-context-line` is empty while `.enrichment-section--context` has children, `updateContextLine()` was not called or `raw_stats.geo` was absent. If `.staleness-badge` is missing when expected, check `VerdictEntry` objects for `cachedAt` field presence — missing means `result.cached_at` was not propagated.
- Redaction constraints: none — no PII/secrets in context fields or cache timestamps

## Integration Closure

- Upstream surfaces consumed: S04's server-rendered `.enrichment-section` containers, `enrichment.ts` context provider branch routing, `row-factory.ts` DOM builder patterns, `verdict-compute.ts` `VerdictEntry` interface, `formatRelativeTime()` utility
- New wiring introduced in this slice: `updateContextLine()` call in `enrichment.ts` context branch → `row-factory.ts` function; `cachedAt` field propagation from `enrichment.ts` VerdictEntry construction → `updateSummaryRow()` staleness badge rendering
- What remains before the milestone is truly usable end-to-end: nothing — S05 is the final slice in M001

## Tasks

- [x] **T01: Add inline context line to IOC card header for IP and domain IOCs** `est:30m`
  - Why: Delivers CTX-01 — key context fields visible without expanding. Adds template placeholder, `updateContextLine()` function, enrichment.ts wiring, and CSS.
  - Files: `app/templates/partials/_ioc_card.html`, `app/static/src/ts/modules/row-factory.ts`, `app/static/src/ts/modules/enrichment.ts`, `app/static/src/input.css`
  - Do: Add `.ioc-context-line` div in template between card header/original and enrichment slot. Create `updateContextLine(card, result)` in row-factory.ts with provider-specific extraction (IP Context → `raw_stats.geo`, ASN Intel → `asn+prefix` only if IP Context absent, DNS Records → first 3 A record IPs). Wire call in enrichment.ts context branch. Add `:empty { display: none }` and styling CSS. All DOM via `createElement + textContent` (SEC-08).
  - Verify: `make typecheck && make js-dev && make css` all pass; `grep -n "updateContextLine" app/static/src/ts/modules/enrichment.ts` shows call; SEC-08 grep clean
  - Done when: `.ioc-context-line` placeholder in template, `updateContextLine` exported and called, CSS rules present, builds pass

- [x] **T02: Add staleness badge to summary row and run full E2E verification** `est:25m`
  - Why: Delivers CTX-02 — cache staleness indicator in summary row. Also runs full E2E verification for both CTX-01 and CTX-02.
  - Files: `app/static/src/ts/modules/verdict-compute.ts`, `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/modules/row-factory.ts`, `app/static/src/input.css`
  - Do: Add `cachedAt?: string` to `VerdictEntry` interface. Populate from `result.cached_at` in enrichment.ts verdict branch. In `updateSummaryRow()`, filter entries with `cachedAt`, find oldest, render `.staleness-badge` with `formatRelativeTime()`. Add `.staleness-badge` CSS. Rebuild bundles. Run full E2E suite.
  - Verify: `make typecheck && make js-dev && make css` pass; `pytest tests/ -m e2e --tb=short -q` = 89 pass / 2 fail; SEC-08 grep clean
  - Done when: `VerdictEntry.cachedAt` field exists, staleness badge renders for cached results, no badge for fresh results, E2E baseline maintained

## Files Likely Touched

- `app/templates/partials/_ioc_card.html`
- `app/static/src/ts/modules/row-factory.ts`
- `app/static/src/ts/modules/enrichment.ts`
- `app/static/src/ts/modules/verdict-compute.ts`
- `app/static/src/input.css`
- `app/static/dist/main.js`
- `app/static/dist/style.css`
