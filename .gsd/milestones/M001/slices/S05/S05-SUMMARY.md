---
id: S05
parent: M001
milestone: M001
provides:
  - CTX-01 inline context line showing GeoIP/ASN/DNS fields in IOC card header without expanding
  - CTX-02 staleness badge showing oldest cache age in summary row
  - updateContextLine() function in row-factory.ts with provider dedup via data-context-provider
  - VerdictEntry.cachedAt optional field propagating cache metadata through verdict pipeline
requires:
  - slice: S04
    provides: Server-rendered .enrichment-section containers, enrichment.ts context provider branch, row-factory.ts updateSummaryRow()
affects: []
key_files:
  - app/templates/partials/_ioc_card.html
  - app/static/src/ts/modules/row-factory.ts
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/modules/verdict-compute.ts
  - app/static/src/input.css
key_decisions:
  - IP Context provider replaces ASN Intel span when it arrives later (more comprehensive geo data)
  - Staleness badge shows oldest cached_at across providers (worst-case data age, not newest)
  - Error-type results never carry cachedAt — only successful result responses can be cached
patterns_established:
  - data-context-provider attribute on child spans for provider dedup and identification
  - VerdictEntry propagates optional metadata (cachedAt) from API through to summary row rendering
  - CSS :empty pseudo-class for self-hiding placeholder elements (zero JS needed for absent-data case)
observability_surfaces:
  - "document.querySelectorAll('.ioc-context-line:not(:empty)').length — count of IOCs with inline context"
  - "document.querySelectorAll('.staleness-badge').length — count of IOCs showing staleness"
  - "data-context-provider attribute on child spans tracks which provider populated each piece"
  - ".staleness-badge textContent shows relative cache age (e.g., 'cached 4h ago')"
drill_down_paths:
  - .gsd/milestones/M001/slices/S05/tasks/T01-SUMMARY.md
  - .gsd/milestones/M001/slices/S05/tasks/T02-SUMMARY.md
duration: 23m
verification_result: passed
completed_at: 2026-03-17
---

# S05: Context And Staleness

**Inline context line shows GeoIP/ASN/DNS fields in IOC card headers without expanding; staleness badge surfaces oldest cache age in summary rows**

## What Happened

**T01** added a `.ioc-context-line` div to the `_ioc_card.html` template (line 55) between the card header/original block and the enrichment slot. A new `updateContextLine()` function in `row-factory.ts` handles three context providers: IP Context extracts `raw_stats.geo` (country, city, org), ASN Intel extracts `asn` + `prefix` (skipped if IP Context already populated the line), and DNS Records extracts the first 3 A-record IPs for domain IOCs. Each provider's content renders into a `<span>` with a `data-context-provider` attribute for deduplication — when IP Context arrives after ASN Intel, it replaces the ASN span with richer geo data. The function is called from the context provider branch of `enrichment.ts`. CSS `:empty { display: none }` hides the line for IOC types without context providers (hash, URL, CVE). All DOM construction uses `createElement` + `textContent` only (SEC-08).

**T02** extended the `VerdictEntry` interface with an optional `cachedAt?: string` field and populated it from `result.cached_at` in the verdict branch of `enrichment.ts` (error results excluded). `updateSummaryRow()` in `row-factory.ts` now filters entries with `cachedAt`, finds the oldest timestamp, and appends a `.staleness-badge` span showing relative cache age via the existing `formatRelativeTime()` utility. The badge is right-aligned in the flex summary row via `margin-left: auto`.

Both tasks together complete M001 — the final slice in the v1.1 Results Page Redesign.

## Verification

- `make typecheck` — zero TypeScript errors ✅
- `make js-dev` — esbuild bundle compiled (194.9kb) ✅
- `make css` — Tailwind rebuild succeeded ✅
- `pytest tests/ -m e2e --tb=short -q` — 89 passed, 2 failed (pre-existing title-case) ✅
- `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` — only comment in graph.ts (SEC-08) ✅
- Template: `.ioc-context-line` exists in `_ioc_card.html` at line 55 ✅
- CSS: `.ioc-context-line:empty { display: none }` present in input.css at line 1065 ✅
- JS: `updateContextLine` exported from row-factory.ts (line 433), called in enrichment.ts context branch (line 232) ✅
- JS: `VerdictEntry.cachedAt` optional field exists in verdict-compute.ts (line 24) ✅
- JS: `updateSummaryRow()` renders `.staleness-badge` span (row-factory.ts line 314) ✅
- JS: `.staleness-badge` CSS rule present in input.css (line 1473) ✅

## Requirements Advanced

- CTX-01 — Inline context line implemented with IP Context, ASN Intel, and DNS Records providers. Awaiting live UAT visual confirmation.
- CTX-02 — Staleness badge implemented showing oldest cache age via formatRelativeTime(). Awaiting live UAT visual confirmation.

## Requirements Validated

- none — all 7 requirements (VIS-01, VIS-02, VIS-03, GRP-01, GRP-02, CTX-01, CTX-02) await live UAT visual confirmation

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- T01: Added logic to remove ASN Intel span when IP Context arrives later. Not in the plan but necessary for correct dedup when providers arrive in arbitrary order.
- T02: Added `if (oldestCachedAt)` guard around badge creation to satisfy TypeScript strict null checking on `sort()[0]` return type. Plan assumed non-undefined since `cachedEntries.length > 0`, but `sort()[0]` is typed `string | undefined`.
- T02: Error-type results explicitly get `cachedAt: undefined` rather than attempting to read `result.cached_at` on the error discriminated union branch.

## Known Limitations

- Context line content is entirely client-side — if JavaScript is disabled, the `.ioc-context-line` div stays empty (hidden by `:empty` CSS). This is consistent with the existing enrichment model.
- DNS Records A-record display is limited to first 3 IPs. Domains with many A records only show a subset in the header context line (full data still visible in expanded provider detail).
- Staleness badge only appears for verdict-type results (reputation providers). Context-only providers (IP Context, DNS Records, ASN Intel) don't have a staleness indicator in the context line — they show fresh-or-nothing.

## Follow-ups

- none — S05 is the final slice of M001. All seven M001 requirements are implemented and await live UAT for visual validation.

## Files Created/Modified

- `app/templates/partials/_ioc_card.html` — Added `.ioc-context-line` div between header/original and enrichment slot
- `app/static/src/ts/modules/row-factory.ts` — Added `updateContextLine()` (line 433) and staleness badge rendering in `updateSummaryRow()` (line 314)
- `app/static/src/ts/modules/enrichment.ts` — Added `updateContextLine` import/call in context branch; populated `cachedAt` in verdict entry construction
- `app/static/src/ts/modules/verdict-compute.ts` — Added `cachedAt?: string` to VerdictEntry interface
- `app/static/src/input.css` — Added `.ioc-context-line`, `:empty`, `.context-field`, and `.staleness-badge` CSS rules
- `app/static/dist/main.js` — Rebuilt JS bundle (194.9kb)
- `app/static/dist/style.css` — Rebuilt CSS

## Forward Intelligence

### What the next slice should know
- M001 is now complete. All 5 slices shipped. The results page has: verdict badge prominence (VIS-01), micro-bar (VIS-02), section headers (VIS-03), three-section grouping (GRP-01), no-data collapse (GRP-02), inline context line (CTX-01), and staleness badge (CTX-02). The next milestone should treat the results page information architecture as stable.
- The TypeScript module structure is clean: `enrichment.ts` (polling orchestrator), `row-factory.ts` (DOM builders + context line + summary row), `verdict-compute.ts` (pure verdict logic + VerdictEntry interface). Any future DOM work goes in row-factory.ts.

### What's fragile
- Provider arrival order for context line — the dedup logic assumes IP Context always has richer data than ASN Intel. If a future provider offers partial geo data, the replacement logic in `updateContextLine()` may need revision.
- `formatRelativeTime()` is used by both cache badges on detail rows and the staleness badge on summary rows — changes to its output format affect both surfaces.

### Authoritative diagnostics
- `document.querySelectorAll('.ioc-context-line:not(:empty)').length` — gold signal for context line rendering; should equal number of IP/domain IOC cards
- `document.querySelectorAll('.staleness-badge').length` — gold signal for staleness rendering; should be >0 when cached results are served
- `data-context-provider` attributes on spans inside `.ioc-context-line` — trace which provider populated each field

### What assumptions changed
- Plan expected "registrar for domains" in CTX-01 description, but implementation uses DNS Records A-record IPs instead — WHOIS/RDAP registrar data was previously scoped out (GDPR redaction returns low-signal data), so DNS A records provide more actionable domain context.
