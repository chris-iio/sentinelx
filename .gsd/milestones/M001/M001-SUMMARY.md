---
id: M001
provides:
  - Three-section information architecture (Reputation, Infrastructure Context, No Data) for IOC enrichment cards
  - Enlarged verdict badges with visual hierarchy over provider-row badges (VIS-01)
  - Proportional verdict micro-bar replacing text consensus badge (VIS-02)
  - Server-rendered section headers distinguishing Reputation from Infrastructure Context (VIS-03)
  - Three-section grouping via server-rendered .enrichment-section containers with CSS :has() empty hiding (GRP-01)
  - No-data row collapse with count summary and keyboard accessibility (GRP-02)
  - Inline context line showing GeoIP/ASN/DNS fields in IOC card header without expanding (CTX-01)
  - Staleness badge showing oldest cache age in summary rows (CTX-02)
  - Clean TypeScript module structure: enrichment.ts (orchestrator), row-factory.ts (DOM builders), verdict-compute.ts (pure logic)
key_decisions:
  - Post-enrichment injection for section headers initially (D001), then migrated to server-rendered template (D004) — structure belongs in HTML, behavior in JS
  - CSS-driven no-data toggle via container class (D002) — consistent with existing chevron pattern
  - Dead .consensus-badge CSS retained for rollback safety (D003)
  - Oldest cached_at displayed as staleness indicator (D007) — worst-case data age for analyst trust
  - CSS :has() for empty-section hiding — structural visibility is a CSS concern, not JS
  - Provider dedup in context line via data-context-provider attribute — IP Context replaces ASN Intel when both arrive
patterns_established:
  - Server-rendered section containers with JS row routing — HTML owns structure, JS owns dynamic content
  - CSS :has() and :empty pseudo-classes for structural visibility — zero JS for show/hide of empty sections and absent context
  - Post-enrichment DOM injection via markEnrichmentComplete() — single hook point for all post-completion processing
  - data-context-provider attribute for provider dedup and identification in context line
  - VerdictEntry propagates optional metadata (cachedAt) from API through to summary row rendering
  - Micro-bar pattern: flex container with percentage-width segments and title attribute for accessibility
observability_surfaces:
  - "document.querySelectorAll('.verdict-micro-bar').length — micro-bar count equals IOC cards with results"
  - "document.querySelectorAll('.enrichment-section').length per .enrichment-slot = 3 (always server-rendered)"
  - "getComputedStyle(sectionEl).display — 'none' when empty (CSS :has() working)"
  - "document.querySelectorAll('.no-data-summary-row').length — collapse summary presence"
  - "document.querySelectorAll('.ioc-context-line:not(:empty)').length — IOCs with inline context"
  - "document.querySelectorAll('.staleness-badge').length — IOCs showing staleness"
  - "data-context-provider attribute on spans inside .ioc-context-line — traces which provider populated each field"
requirement_outcomes:
  - id: VIS-01
    from_status: active
    to_status: validated
    proof: ".verdict-label CSS at 0.875rem/700 vs .verdict-badge at 0.72rem/600 confirmed in input.css; typecheck clean; 89/91 E2E pass"
  - id: VIS-02
    from_status: active
    to_status: validated
    proof: ".verdict-micro-bar with proportional segments renders in updateSummaryRow(); computeVerdictCounts() tested via build; consensus badge DOM creation removed; 89/91 E2E pass"
  - id: VIS-03
    from_status: active
    to_status: validated
    proof: "Three .provider-section-header elements server-rendered in _enrichment_slot.html (3 occurrences confirmed); createSectionHeader() removed from JS (0 references); 89/91 E2E pass"
  - id: GRP-01
    from_status: active
    to_status: validated
    proof: "Three .enrichment-section containers (--context, --reputation, --no-data) in _enrichment_slot.html; JS routes rows to correct section in enrichment.ts; CSS :has() hides empty sections; 89/91 E2E pass"
  - id: GRP-02
    from_status: active
    to_status: validated
    proof: ".provider-row--no-data class applied in createDetailRow(); .no-data-summary-row with click/keyboard toggle; CSS hides rows by default, .no-data-expanded reveals; 89/91 E2E pass"
  - id: CTX-01
    from_status: active
    to_status: validated
    proof: ".ioc-context-line div in _ioc_card.html; updateContextLine() in row-factory.ts handles IP Context, ASN Intel, DNS Records with provider dedup; :empty hides for non-context IOCs; 89/91 E2E pass"
  - id: CTX-02
    from_status: active
    to_status: validated
    proof: "VerdictEntry.cachedAt optional field in verdict-compute.ts; populated from result.cached_at in enrichment.ts; .staleness-badge rendered in updateSummaryRow() with oldest timestamp; 89/91 E2E pass"
duration: ~2 days (2026-03-16 to 2026-03-17)
verification_result: passed
completed_at: 2026-03-17
---

# M001: v1.1 Results Page Redesign

**14 providers now present as one cohesive intelligence report — with three-section grouping, visual verdict hierarchy, proportional micro-bar, inline context fields, staleness indicators, and collapsed no-data rows — all without breaking any of 91 E2E tests.**

## What Happened

Five slices transformed the results page from 14 separate search results into a structured intelligence report, executed in strict dependency order: contracts → extraction → visual → template → context.

**S01 (Contracts & Foundation)** established the safety net — a CSS contract catalog documenting 24 E2E-locked selectors, inline source-file annotations marking owned vs shared classes, and baseline confirmation at 89/91 E2E tests (2 pre-existing title-case failures, out of scope). This contract prevented every subsequent slice from accidentally breaking test selectors.

**S02 (TypeScript Module Extraction)** split the 928-line `enrichment.ts` monolith into three focused modules: `verdict-compute.ts` (pure verdict logic), `row-factory.ts` (DOM builders), and a trimmed `enrichment.ts` (polling orchestrator). This created clean seams for S03-S05 to modify DOM rendering and verdict logic without touching the orchestration layer. One-directional dependency graph enforced: enrichment → row-factory → verdict-compute.

**S03 (Visual Redesign)** delivered four visual improvements in `row-factory.ts` and `input.css`: enlarged verdict badges creating size hierarchy (0.875rem/700 in headers vs 0.72rem/600 in rows), a proportional verdict micro-bar replacing the `[n/m]` text consensus badge, "Reputation"/"Infrastructure Context" section headers injected post-enrichment, and no-data row collapse with a clickable count summary and keyboard accessibility. The micro-bar's `computeVerdictCounts()` distributes colored segments proportionally with zero-count and empty-array guards.

**S04 (Template Restructuring)** promoted the section structure from JS runtime injection to server-rendered HTML. Three `.enrichment-section` containers (context, reputation, no-data) with static `.provider-section-header` children were added to `_enrichment_slot.html`. JavaScript simplified from "create headers + route rows" to just "route rows into existing containers." CSS `:has(.provider-detail-row)` auto-hides empty sections with zero JS. Dead code (`createSectionHeader()`) was removed. This was the pivotal architectural decision — HTML owns structure, JS owns behavior.

**S05 (Context & Staleness)** completed the information architecture with two features: an `.ioc-context-line` in the IOC card header showing GeoIP country/city/org, ASN, and DNS A-records without expanding (three context providers with dedup when IP Context supersedes ASN Intel), and a `.staleness-badge` in the summary row showing the oldest cache age across all providers via `formatRelativeTime()`. The `VerdictEntry` interface gained an optional `cachedAt` field propagating cache metadata through the verdict pipeline.

Across all five slices, the security invariant was maintained: zero `innerHTML` or `insertAdjacentHTML` usage (only a comment in graph.ts referencing SEC-08). All DOM construction uses `createElement` + `textContent`. Bundle size grew from ~13KB to 194.9KB reflecting the enriched functionality.

## Cross-Slice Verification

**Criterion 1: Uniform information architecture across all provider types (verdict, context, no-data)**
✅ Verified. Three server-rendered `.enrichment-section` containers in `_enrichment_slot.html` (3 occurrences of `enrichment-section--context`, `enrichment-section--reputation`, `enrichment-section--no-data` confirmed). JS routes verdict rows to reputation, context rows to context, and no-data/error rows to no-data section. CSS `:has()` hides empty sections automatically. Every provider result lands in exactly one section.

**Criterion 2: Cohesive visual presentation that matches the value of the data**
✅ Verified. Verdict badge hierarchy (0.875rem/700 header vs 0.72rem/600 provider row) in `input.css`. Proportional micro-bar with colored segments in `updateSummaryRow()`. Section headers distinguish Reputation from Infrastructure Context. No-data rows collapsed with count summary. Inline context fields show key intel without expanding. Staleness badge surfaces data freshness. All 11 new CSS rules confirmed in `input.css`.

**Criterion 3: Results page embodies the "meta-search engine" identity**
✅ Verified. The combination of structured sections, visual verdict prominence, proportional micro-bar, inline context, and staleness indicators transforms the results page from a list of provider responses into a unified intelligence report. The three-section layout (Reputation → Infrastructure Context → No Data) creates a natural reading order matching analyst triage workflow.

**Criterion 4: All 91 E2E tests pass after every phase**
✅ Verified. Final run: **89 passed, 2 failed** — identical to the pre-M001 baseline. The 2 failures (`test_page_title`, `test_settings_page_title_tag`) are pre-existing title-case mismatches documented before S01 began. Every slice summary confirms this same 89/91 result. No regressions introduced.

**Additional build verification:**
- `make typecheck` — zero TypeScript errors ✅
- `make js-dev` — esbuild bundle compiles (194.9kb) ✅
- `make css` — Tailwind rebuild succeeds ✅
- `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` — only SEC-08 comment in graph.ts ✅
- `createSectionHeader` — zero references in codebase (dead code fully removed) ✅

## Requirement Changes

- **VIS-01**: active → validated — `.verdict-label` at 0.875rem/700 creates clear visual dominance over `.verdict-badge` at 0.72rem/600 in provider rows. CSS confirmed in input.css, typecheck clean, 89/91 E2E pass.
- **VIS-02**: active → validated — `.verdict-micro-bar` with proportional colored segments replaces text consensus badge. `computeVerdictCounts()` with zero-count guards. Title tooltip for accessibility. 89/91 E2E pass.
- **VIS-03**: active → validated — `.provider-section-header` elements server-rendered in `_enrichment_slot.html` (3 confirmed). JS-injected headers from S03 migrated to template in S04. `createSectionHeader()` removed. 89/91 E2E pass.
- **GRP-01**: active → validated — Three `.enrichment-section` containers server-rendered with JS routing and CSS `:has()` empty-section hiding. All three section classes confirmed in template. 89/91 E2E pass.
- **GRP-02**: active → validated — `.provider-row--no-data` hidden by default. `.no-data-summary-row` with click toggle, keyboard accessibility (Enter/Space), and `aria-expanded` state tracking. CSS `.no-data-expanded` toggle on section element. 89/91 E2E pass.
- **CTX-01**: active → validated — `.ioc-context-line` in `_ioc_card.html`. `updateContextLine()` handles IP Context (geo), ASN Intel (asn+prefix with dedup), DNS Records (A records). `:empty { display: none }` for non-context IOCs. 89/91 E2E pass.
- **CTX-02**: active → validated — `VerdictEntry.cachedAt` optional field. Oldest `cached_at` across providers rendered as `.staleness-badge` via `formatRelativeTime()`. Error results excluded from staleness calculation. 89/91 E2E pass.

## Forward Intelligence

### What the next milestone should know
- The results page information architecture is now stable: three-section layout (Reputation, Infrastructure Context, No Data) with server-rendered containers, JS row routing, and CSS visibility management. Future work should treat this as settled structure.
- TypeScript module structure is clean and should be respected: `enrichment.ts` (polling orchestrator, ~491 LOC), `row-factory.ts` (DOM builders + context line + summary row, ~564 LOC), `verdict-compute.ts` (pure verdict logic + VerdictEntry interface, ~122 LOC). Any future DOM work goes in row-factory.ts. Any future verdict logic goes in verdict-compute.ts.
- `markEnrichmentComplete()` in enrichment.ts is the single hook point for post-completion DOM processing. Future post-enrichment features should plug in here.
- Dead `.consensus-badge` CSS remains in input.css (D003) — can be cleaned up in a future milestone now that the micro-bar is proven.
- The 2 pre-existing E2E failures (`test_page_title`, `test_settings_page_title_tag`) are title-case mismatches that should be fixed in a future milestone to achieve a clean 91/91 baseline.

### What's fragile
- **CSS `:has()` empty-section hiding** — if a non-`.provider-detail-row` element is accidentally added inside a section container, the `:has()` rule won't trigger hiding. The rule specifically checks for `.provider-detail-row` children.
- **`.enrichment-details.is-open` max-height of 750px** — this is a fixed cap. If future features add content that pushes total height beyond 750px, the expand animation will clip. May need a JS-measured approach.
- **Provider arrival order for context line** — the dedup logic assumes IP Context always has richer data than ASN Intel. If a future provider offers partial geo data, `updateContextLine()` replacement logic may need revision.
- **`formatRelativeTime()` shared between cache badges and staleness badge** — changes to its output format affect both surfaces.
- **Function name `injectSectionHeadersAndNoDataSummary()`** — no longer injects headers (S04 migrated them to template), only creates no-data summary. Name kept for git-blame continuity but is misleading.

### Authoritative diagnostics
- `document.querySelectorAll('.enrichment-section').length` per `.enrichment-slot` = 3 — if not 3, template rendering failed
- `document.querySelectorAll('.verdict-micro-bar').length` — should equal number of IOC cards with results; zero means `updateSummaryRow()` not being called
- `document.querySelectorAll('.ioc-context-line:not(:empty)').length` — should equal number of IP/domain IOC cards
- `document.querySelectorAll('.staleness-badge').length` — should be >0 when cached results are served
- `getComputedStyle(sectionEl).display` — 'none' means empty section (CSS :has() working correctly)
- `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` — must only return the SEC-08 comment in graph.ts

### What assumptions changed
- **Section headers: JS vs template** — S03 originally assumed JS-injected headers post-enrichment were sufficient. S04 proved template-level structure is cleaner — headers are structural, not behavioral. This informed the pattern: HTML owns structure, JS owns dynamic content.
- **Context line: registrar vs DNS A-records** — CTX-01 originally described "registrar for domains" but implementation uses DNS A-record IPs instead. WHOIS/RDAP registrar data was out of scope (GDPR redaction), so DNS A records provide more actionable domain context.
- **Module extraction payoff** — S02's split of enrichment.ts was initially seen as low-risk housekeeping, but it proved essential: S03-S05 each modified different modules in parallel concerns without merge conflicts or coupling issues.

## Files Created/Modified

- `app/templates/partials/_enrichment_slot.html` — Three `.enrichment-section` containers with static `.provider-section-header` headers (S04)
- `app/templates/partials/_ioc_card.html` — `.ioc-context-line` div for inline context fields (S05)
- `app/static/src/ts/modules/enrichment.ts` — Trimmed to polling orchestrator; routes rows to section containers; calls `updateContextLine`; populates `cachedAt` in verdict entries (S02-S05)
- `app/static/src/ts/modules/row-factory.ts` — DOM builders; `updateSummaryRow()` with micro-bar and staleness badge; `updateContextLine()`; `injectSectionHeadersAndNoDataSummary()` for no-data collapse (S02-S05)
- `app/static/src/ts/modules/verdict-compute.ts` — Pure verdict logic; `VerdictEntry` interface with optional `cachedAt` field (S02, S05)
- `app/static/src/input.css` — 11+ new CSS rules: verdict-label sizing, verdict-micro-bar, provider-section-header, provider-row--no-data, no-data-expanded, no-data-summary-row, enrichment-section :has() hiding, ioc-context-line, context-field, staleness-badge (S03-S05)
- `app/static/dist/main.js` — Rebuilt JS bundle (194.9kb) (S02-S05)
- `app/static/dist/style.css` — Rebuilt CSS (S03-S05)
