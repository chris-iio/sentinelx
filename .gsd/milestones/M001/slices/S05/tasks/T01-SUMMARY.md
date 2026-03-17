---
id: T01
parent: S05
milestone: M001
provides:
  - CTX-01 inline context line in IOC card header for IP and domain IOCs
  - updateContextLine() function in row-factory.ts
  - .ioc-context-line CSS with :empty hiding
key_files:
  - app/templates/partials/_ioc_card.html
  - app/static/src/ts/modules/row-factory.ts
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/input.css
key_decisions:
  - IP Context provider replaces ASN Intel span if it arrives later (more comprehensive)
patterns_established:
  - data-context-provider attribute on child spans for dedup and provider identification
observability_surfaces:
  - document.querySelectorAll('.ioc-context-line:not(:empty)').length — count of IOCs with inline context
  - data-context-provider attribute on child spans tracks which provider populated each piece
duration: 15m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T01: Add inline context line to IOC card header for IP and domain IOCs

**Added .ioc-context-line placeholder and updateContextLine() to show GeoIP/ASN/DNS data inline in IOC card headers without expanding**

## What Happened

Added a new `.ioc-context-line` div to the `_ioc_card.html` template between the card header/original block and the enrichment slot. Created `updateContextLine()` in `row-factory.ts` that handles three context providers: "IP Context" (extracts `raw_stats.geo`), "ASN Intel" (extracts `asn` + `prefix`, skips if IP Context already present), and "DNS Records" (extracts first 3 A-record IPs). Each provider's content is rendered into a `<span>` with `data-context-provider` attribute for deduplication. Wired the function call into the context provider branch of `enrichment.ts`. Added CSS rules with `:empty { display: none }` so the line hides for IOC types without context providers (hash, URL, CVE). All DOM construction uses `createElement` + `textContent` only (SEC-08).

## Verification

- `make typecheck` — zero errors ✓
- `make js-dev` — bundle compiled (193.0kb) ✓
- `make css` — Tailwind rebuild succeeded ✓
- `grep -n "ioc-context-line" _ioc_card.html` — shows placeholder at line 55 ✓
- `grep -n "updateContextLine" enrichment.ts` — shows import (line 27) and call (line 232) ✓
- `grep -n "updateContextLine" row-factory.ts` — shows export at line 418 ✓
- `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` — only comment in graph.ts (SEC-08 compliant) ✓
- `.ioc-context-line:empty` rule present in `input.css` at line 1065 ✓
- CSS rules present in built `style.css` ✓

### Slice-level checks (partial — T01 is not final task):
- ✓ Template: `.ioc-context-line` in `_ioc_card.html`
- ✓ CSS: `.ioc-context-line:empty { display: none }` rule present
- ✓ JS: `updateContextLine` exported from `row-factory.ts` and called in `enrichment.ts` context branch
- ✗ JS: `VerdictEntry.cachedAt` — T02 scope
- ✗ JS: `updateSummaryRow()` renders `.staleness-badge` — T02 scope
- ✓ SEC-08: No innerHTML violations

## Diagnostics

- `.ioc-context-line` div is present on every IOC card, hidden via `:empty` CSS when no context providers fire
- Child `<span>` elements carry `data-context-provider` attribute ("IP Context", "ASN Intel", or "DNS Records")
- `document.querySelectorAll('.ioc-context-line:not(:empty)').length` — count of IOCs with inline context rendered
- If context line stays empty for an IP IOC while `.enrichment-section--context .provider-detail-row` has children, `updateContextLine()` was not called or `raw_stats.geo` was absent

## Deviations

- Added logic to remove ASN Intel span when IP Context arrives later (not in plan but necessary for correct dedup when providers arrive out of order)

## Known Issues

None

## Files Created/Modified

- `app/templates/partials/_ioc_card.html` — Added `.ioc-context-line` div between header/original and enrichment slot
- `app/static/src/ts/modules/row-factory.ts` — Added `updateContextLine()` exported function with IP Context / ASN Intel / DNS Records handling
- `app/static/src/ts/modules/enrichment.ts` — Added `updateContextLine` import and call in context provider branch
- `app/static/src/input.css` — Added `.ioc-context-line`, `:empty`, and `.context-field` CSS rules
- `app/static/dist/main.js` — Rebuilt JS bundle
- `app/static/dist/style.css` — Rebuilt CSS
- `.gsd/milestones/M001/slices/S05/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
