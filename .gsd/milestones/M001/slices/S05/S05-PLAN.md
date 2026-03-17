# S05: Context And Staleness

**Goal:** Key context fields (GeoIP, ASN for IPs; DNS A records for domains) are visible in the IOC card header without expanding, and cached results show a staleness indicator in the summary row.
**Demo:** An IP IOC card displays "US · San Francisco · AS24940 (Hetzner Online GmbH)" between the card header and the enrichment slot before the user expands anything. A domain IOC card shows resolved A record IPs inline. When verdict results were served from cache, the summary row shows "cached 4h ago" next to the micro-bar.

## Must-Haves

- Empty `.ioc-context-line` placeholder in `_ioc_card.html` between the card header/original and the enrichment slot
- `.ioc-context-line` hides itself via CSS `:empty { display: none }` when no context arrives (hash, URL, CVE IOC types)
- `updateContextLine()` in `row-factory.ts` extracts key fields from context provider `raw_stats` and populates the placeholder
- IP Context provider populates the line with `raw_stats.geo`; ASN Intel defers if IP Context already populated
- DNS Records provider populates the line with first 2–3 A record IPs for domain IOCs
- `VerdictEntry` interface extended with optional `cachedAt` field populated from `result.cached_at`
- `updateSummaryRow()` renders a `.staleness-badge` when any verdict entry has `cachedAt`
- All DOM construction uses `createElement + textContent` (SEC-08 — no innerHTML)
- No backend changes — all data already flows from Flask to browser

## Proof Level

- This slice proves: integration
- Real runtime required: no (E2E tests exercise the enrichment flow with mocked API responses)
- Human/UAT required: yes (visual confirmation of context line placement and staleness badge appearance)

## Verification

- `make typecheck` — zero TypeScript errors
- `make js-dev` — esbuild bundle compiles successfully
- `make css` — Tailwind rebuild succeeds
- `pytest tests/ -m e2e --tb=short -q` — 89 passed, 2 failed (pre-existing title-case only)
- `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` — only comment in graph.ts (SEC-08)
- Template: `.ioc-context-line` exists in `_ioc_card.html` between card header/original and enrichment slot
- CSS: `.ioc-context-line:empty { display: none }` rule present in `input.css`
- JS: `updateContextLine` exported from `row-factory.ts` and called in `enrichment.ts` context branch
- JS: `VerdictEntry.cachedAt` optional field exists in `verdict-compute.ts`
- JS: `updateSummaryRow()` renders `.staleness-badge` span when cached entries exist
- **Diagnostic check:** `document.querySelectorAll('.ioc-context-line').length` equals number of `.ioc-card` elements (placeholder always present, hidden when empty)
- **Failure-path check:** For IOC types with no context providers (hash, URL, CVE), `.ioc-context-line` must have `display: none` computed style (`:empty` rule working). Verify via: `getComputedStyle(document.querySelector('.ioc-card[data-ioc-type="hash"] .ioc-context-line')).display === 'none'`

## Observability / Diagnostics

- Runtime signals: `.ioc-context-line` element's `textContent` — non-empty means context arrived and was rendered; `data-context-provider` attribute on child spans tracks which provider populated each piece
- Inspection surfaces: `document.querySelectorAll('.ioc-context-line:not(:empty)').length` — count of IOCs with inline context rendered; `document.querySelectorAll('.staleness-badge').length` — count of IOCs showing staleness
- Failure visibility: If context line stays empty for an IP IOC, check `document.querySelectorAll('.enrichment-section--context .provider-detail-row').length` — if >0, the context row rendered but `updateContextLine` didn't fire. If `.staleness-badge` is absent when expected, inspect `VerdictEntry` objects in `iocVerdicts` for `cachedAt` field presence.
- Redaction constraints: none — GeoIP/ASN data is not PII in this context

## Integration Closure

- Upstream surfaces consumed: S04's server-rendered `.enrichment-section` containers, `enrichment.ts` context provider branch (line ~215), `row-factory.ts` `updateSummaryRow()` and `formatRelativeTime()`, `verdict-compute.ts` `VerdictEntry` interface
- New wiring introduced in this slice: `updateContextLine()` call added to the context provider branch in `enrichment.ts`; `cachedAt` propagation from `result.cached_at` to `VerdictEntry` in the verdict branch of `enrichment.ts`
- What remains before the milestone is truly usable end-to-end: nothing — S05 is the final slice in M001

## Tasks

- [x] **T01: Add inline context line to IOC card header for IP and domain IOCs** `est:45m`
  - Why: Delivers CTX-01 — the higher-complexity feature with template + JS routing + CSS. Context fields visible without expanding give users immediate intelligence value.
  - Files: `app/templates/partials/_ioc_card.html`, `app/static/src/ts/modules/row-factory.ts`, `app/static/src/ts/modules/enrichment.ts`, `app/static/src/input.css`
  - Do: (1) Add empty `.ioc-context-line` div in `_ioc_card.html` after `{% endif %}` for `.ioc-original` and before the `{% if mode == "online" %}` enrichment slot include. (2) Add `updateContextLine(card, result)` function to `row-factory.ts` that extracts context from `raw_stats` based on provider name — IP Context uses `raw_stats.geo`, ASN Intel uses `asn`+`prefix` (skips if IP Context already populated), DNS Records uses `raw_stats.a` array (first 2-3 IPs). Each span gets `data-context-provider` attribute for dedup. (3) Call `updateContextLine` from the context provider branch in `enrichment.ts` (after the context row append, before the return). (4) Add `.ioc-context-line` CSS in `input.css` — `:empty { display: none }`, muted text styling, positioned between header and enrichment slot. (5) All DOM uses `createElement + textContent` only (SEC-08). Only CONTEXT_PROVIDERS results populate the line — never verdict providers.
  - Verify: `make typecheck && make js-dev && make css` all pass; `.ioc-context-line` in template between header and slot; `grep updateContextLine app/static/src/ts/modules/enrichment.ts` shows call in context branch
  - Done when: typecheck clean, bundle builds, CSS rebuilds, context line placeholder in template, `updateContextLine` wired in enrichment.ts context branch

- [x] **T02: Add staleness badge to summary row and run full E2E verification** `est:30m`
  - Why: Delivers CTX-02 — staleness indicator surfaces cache age to users. Also performs final E2E verification for both CTX-01 and CTX-02.
  - Files: `app/static/src/ts/modules/verdict-compute.ts`, `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/modules/row-factory.ts`, `app/static/src/input.css`
  - Do: (1) Add `cachedAt?: string` to `VerdictEntry` interface in `verdict-compute.ts`. (2) In `enrichment.ts` verdict branch, when building VerdictEntry objects, populate `cachedAt: result.cached_at` when `result.cached_at` exists. (3) In `row-factory.ts` `updateSummaryRow()`, after appending the micro-bar, find the oldest `cachedAt` across all entries for the IOC. If any exist, create a `.staleness-badge` span with text like "cached 4h ago" using the existing `formatRelativeTime()`. Append to `summaryRow`. (4) Add `.staleness-badge` CSS in `input.css` — small muted text, consistent with existing `.cache-badge` styling on detail rows. (5) Rebuild bundles with `make js-dev && make css`. (6) Run full E2E suite: `pytest tests/ -m e2e --tb=short -q` — expect 89 pass, 2 pre-existing failures.
  - Verify: `make typecheck && make js-dev && make css` all pass; `pytest tests/ -m e2e --tb=short -q` — 89 passed, 2 failed (pre-existing); `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` — only comment in graph.ts
  - Done when: VerdictEntry has `cachedAt`, staleness badge renders when cached results exist, no SEC-08 violations, E2E baseline maintained (89 pass, 2 pre-existing fail)

## Files Likely Touched

- `app/templates/partials/_ioc_card.html`
- `app/static/src/ts/modules/enrichment.ts`
- `app/static/src/ts/modules/row-factory.ts`
- `app/static/src/ts/modules/verdict-compute.ts`
- `app/static/src/input.css`
- `app/static/dist/main.js`
- `app/static/dist/style.css`
