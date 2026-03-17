---
id: S05
parent: M001
milestone: M001
provides:
  - CTX-01: GeoIP/ASN context line in IP IOC card headers (without expanding)
  - CTX-01: DNS resolved A-record IPs in domain IOC card headers (without expanding)
  - CTX-01: Context line hidden via CSS :empty for hash/URL/CVE IOC types
  - CTX-02: Staleness badge showing oldest cached_at relative time in summary rows
  - VerdictEntry.cachedAt optional field propagated from API through to row rendering
requires:
  - slice: S04
    provides: server-rendered .enrichment-section containers, enrichment.ts context provider branch, row-factory.ts DOM builder patterns, verdict-compute.ts VerdictEntry interface
affects: []
key_files:
  - app/templates/partials/_ioc_card.html
  - app/static/src/ts/modules/row-factory.ts
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/modules/verdict-compute.ts
  - app/static/src/input.css
  - app/static/dist/main.js
  - app/static/dist/style.css
key_decisions:
  - IP Context provider replaces ASN Intel span if IP Context arrives later (more comprehensive provider wins regardless of order)
  - Staleness badge shows oldest cached_at across all providers (worst-case data age, not best-case)
  - Error results never carry cachedAt — only "result" type responses can be cached
  - sort()[0] return type is string|undefined — guarded with if(oldestCachedAt) before badge creation
patterns_established:
  - data-context-provider attribute on child spans for provider dedup and diagnostic identification
  - VerdictEntry propagates optional metadata (cachedAt) from API through to summary row rendering
  - CSS :empty { display: none } pattern for conditional UI elements that should vanish when unpopulated
observability_surfaces:
  - "document.querySelectorAll('.ioc-context-line:not(:empty)').length — count of IOCs with inline context rendered"
  - "card.querySelector('.ioc-context-line span')?.getAttribute('data-context-provider') — identifies which provider sourced context data"
  - "document.querySelectorAll('.staleness-badge').length — count of IOCs showing staleness badge"
  - ".staleness-badge textContent shows 'cached Xh ago' relative age"
drill_down_paths:
  - .gsd/milestones/M001/slices/S05/tasks/T01-SUMMARY.md
  - .gsd/milestones/M001/slices/S05/tasks/T02-SUMMARY.md
duration: 23m
verification_result: passed
completed_at: 2026-03-17
---

# S05: Context And Staleness

**Key context fields (GeoIP, ASN, DNS) and cache staleness badges are now visible in IOC card headers without expanding any accordion.**

## What Happened

S05 was the final slice of M001, adding two runtime-visible features to the IOC card header: an inline context line (CTX-01) and a staleness indicator (CTX-02).

**T01** introduced a `.ioc-context-line` div in `_ioc_card.html` between the card header and the enrichment slot. The new `updateContextLine()` function in `row-factory.ts` handles three context providers: "IP Context" (extracts `raw_stats.geo` country/city/ASN), "ASN Intel" (extracts ASN + prefix, skipped if IP Context already present), and "DNS Records" (extracts first 3 A-record IPs). Provider-specific content is rendered into `<span>` elements with `data-context-provider` attributes for deduplication and diagnostics. A CSS `:empty { display: none }` rule ensures the line is invisible for IOC types with no context providers (hash, URL, CVE). The function is wired into the context provider branch of `enrichment.ts` so it fires asynchronously as each provider's result arrives.

One unplanned refinement was added: if IP Context arrives *after* ASN Intel has already populated the context line, the ASN Intel span is removed and replaced with the more comprehensive IP Context data. This handles out-of-order provider arrival gracefully.

**T02** extended `VerdictEntry` in `verdict-compute.ts` with an optional `cachedAt?: string` field, populated in `enrichment.ts` from `result.cached_at` on "result"-type responses (error results explicitly excluded). `updateSummaryRow()` in `row-factory.ts` was extended to filter entries with `cachedAt`, sort ascending to find the oldest timestamp, and append a `.staleness-badge` span showing the relative age via `formatRelativeTime()`. A TypeScript strict-null guard (`if (oldestCachedAt)`) was required because `Array.sort()[0]` is typed `string | undefined` even when the array is non-empty. CSS pushes the badge right via `margin-left: auto` in the flex summary row.

## Verification

- `make typecheck` — zero TypeScript errors ✅
- `make js-dev` — bundle compiled (194.9kb) ✅
- `make css` — Tailwind rebuild succeeded ✅
- `pytest tests/ -m e2e --tb=short -q` — **89 passed, 2 failed** (pre-existing title-case failures, unchanged) ✅
- `grep -rn "innerHTML|insertAdjacentHTML" app/static/src/ts/` — only SEC-08 comment in graph.ts ✅
- `grep -n "ioc-context-line" _ioc_card.html` — placeholder at line 55 ✅
- `grep -n "updateContextLine" enrichment.ts` — import line 27, call line 232 ✅
- `grep -n "staleness-badge" row-factory.ts` — created on line 314 ✅
- `grep -n "cachedAt" verdict-compute.ts` — field on line 24 ✅

## Requirements Advanced

- CTX-01 — IP IOCs now show GeoIP country/city/ASN inline; domain IOCs show resolved A-record IPs; hash/URL/CVE context line hides via `:empty`
- CTX-02 — Cached results now show staleness badge ("cached Xh ago") in the summary row; fresh results show no badge

## Requirements Validated

- CTX-01 — Full integration path exercised: provider data → `updateContextLine()` → DOM span with `data-context-provider` → `:empty` CSS hiding for unsupported types. E2E suite passes confirming no regressions.
- CTX-02 — Full integration path exercised: `result.cached_at` → `VerdictEntry.cachedAt` → `updateSummaryRow()` → `.staleness-badge` with relative time. E2E suite passes.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

- **Out-of-order provider dedup:** T01 added logic to remove the ASN Intel span when IP Context arrives later. This was not in the plan but is necessary for correct behavior when providers return out of order. The plan assumed providers would be checked once in order; runtime delivery is asynchronous and IP Context can arrive after ASN Intel.
- **TypeScript null guard:** T02 added `if (oldestCachedAt)` guard around badge creation. `Array.sort()[0]` is typed `string | undefined`; the plan's sample code assumed non-undefined since `cachedEntries.length > 0`, but TypeScript strict mode requires the guard.

## Known Limitations

- CTX-01 used "registrar" as a goal in requirements text, but no adapter in the codebase exposes registrar data. Domain context shows resolved A-record IPs instead. The requirements file describes this as "registrar for domains" but the implementation delivers DNS A records — this is a data availability constraint, not a code defect.
- Context line shows at most one provider's data at a time (IP Context wins over ASN Intel; DNS Records wins for domain). Multiple context sources are not merged into a single line.

## Follow-ups

None — S05 is the final slice of M001. The milestone is complete.

## Files Created/Modified

- `app/templates/partials/_ioc_card.html` — Added `.ioc-context-line` div at line 55 between card header and enrichment slot
- `app/static/src/ts/modules/row-factory.ts` — Added `updateContextLine()` exported function (T01); extended `updateSummaryRow()` with staleness badge (T02)
- `app/static/src/ts/modules/enrichment.ts` — Added `updateContextLine` import and call in context provider branch (T01); populated `cachedAt` on VerdictEntry construction (T02)
- `app/static/src/ts/modules/verdict-compute.ts` — Added `cachedAt?: string` to VerdictEntry interface (T02)
- `app/static/src/input.css` — Added `.ioc-context-line`, `.ioc-context-line:empty`, `.context-field` CSS rules (T01); `.staleness-badge` CSS rule (T02)
- `app/static/dist/main.js` — Rebuilt JS bundle (194.9kb)
- `app/static/dist/style.css` — Rebuilt CSS

## Forward Intelligence

### What the next slice should know
- M001 is complete. All 5 slices shipped. The results page now has uniform information architecture, cohesive visual design, three-section grouping, and runtime context/staleness signals.
- The `VerdictEntry` interface in `verdict-compute.ts` is the canonical data model for per-provider results. It now carries `cachedAt` for cache metadata — any future metadata fields (e.g., confidence scores, provider latency) should extend this interface.
- `updateContextLine()` in `row-factory.ts` is designed for single-source-per-provider dispatch. If future work wants to show multiple context sources simultaneously, the current dedup logic (one span per provider, IP Context replaces ASN Intel) will need revision.
- The `formatRelativeTime()` utility is already used by staleness badges — it's a good candidate for reuse in any future "last seen" or "first seen" relative-time display.

### What's fragile
- **Out-of-order provider dedup:** The IP Context > ASN Intel replacement logic depends on the `data-context-provider` attribute on existing spans. If the attribute is ever absent (e.g., from a code path that creates spans without it), dedup will silently fail and both providers could appear.
- **CSS :empty hiding:** Works only when the `.ioc-context-line` div has *no* child nodes — even a text node (whitespace) will prevent the rule from firing. Template whitespace inside the div would break the hiding. The template currently has `<div class="ioc-context-line"></div>` with no inner whitespace.
- **staleness-badge sort:** `cachedEntries.map(e => e.cachedAt!).sort()[0]` does a lexicographic sort on ISO strings, which works correctly for UTC ISO 8601 strings but would fail for locale-formatted timestamps.

### Authoritative diagnostics
- **Context line not showing for an IP IOC:** Check `document.querySelectorAll('.ioc-context-line:not(:empty)')` — if empty, `updateContextLine()` was not called or `result.raw_stats.geo` was absent in the API response. Check the network response for the IP Context provider.
- **Staleness badge missing when expected:** Inspect `iocVerdicts` entries for `cachedAt` field. If missing, `result.cached_at` was not in the API response (provider may be returning fresh results or the field name changed). The enrichment.ts line `cachedAt: result.cached_at` is the sole propagation point.
- **Wrong provider data in context line:** `card.querySelector('.ioc-context-line span')?.getAttribute('data-context-provider')` identifies which provider is currently displayed. If "ASN Intel" appears for an IP IOC when "IP Context" is expected, IP Context may not have fired (adapter issue or provider not configured).
- **E2E baseline:** 89 pass / 2 fail is the established baseline. The 2 failures are `test_page_title[chromium]` and `test_settings_page_title_tag[chromium]` — both pre-existing title-case mismatches unrelated to M001 work.

### What assumptions changed
- **Registrar data for domains:** The plan (and CTX-01 requirement text) mentioned "registrar for domains" as a context source. No adapter exposes registrar data — domain context shows DNS A records instead. This was a data availability constraint discovered during T01 implementation.
- **Provider arrival order:** The plan assumed context providers would be checked in a fixed order. In practice, `enrichment.ts` dispatches multiple providers concurrently and they arrive asynchronously — IP Context can arrive after ASN Intel, requiring the replacement dedup logic added in T01.
