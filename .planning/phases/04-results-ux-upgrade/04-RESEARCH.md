# Phase 4: Results UX Upgrade - Research

**Researched:** 2026-03-03
**Domain:** Frontend UX refactor — TypeScript + HTML templates + CSS (no backend changes)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Summary card content**
- Always-visible summary shows: worst verdict label + source attribution from the most detailed provider
- "Most detailed" = provider with richest stats (e.g., VirusTotal's "45/72 engines" over AbuseIPDB's confidence score)
- Format: `MALICIOUS — VirusTotal: 45/72 engines`
- Consensus pill badge at right edge of summary: `[3/5]` format showing flagged/responded count
- Pill badge color-coded by agreement level: green (0 flagged) → yellow (1-2 flagged) → red (3+ flagged)

**Consensus denominator**
- "Responded" = providers that returned malicious, suspicious, or clean verdicts
- Excludes: unconfigured/skipped providers, error providers, and no-data providers
- No-data does NOT count as a vote — "3/5 flagged" means 3 of 5 providers with actual data flagged it

**Expand/collapse interaction**
- Chevron icon (▶/▼) in card header next to verdict badge — compact accordion pattern
- Cards collapsed by default — summary-only view for scanning
- Smooth slide animation (~200ms) for expand/collapse — consistent with v1.3 motion design
- Multiple cards can be open simultaneously (independent state, not accordion)

**Provider detail rows (expanded section)**
- One compact line per provider: `Name  [VERDICT]  key stat` (e.g., "VirusTotal  [MALICIOUS]  45/72 engines")
- Sorted by severity: malicious providers first, then suspicious, clean, no-data, errors last
- Error rows shown in red: `VirusTotal  [ERROR]  Request timed out` — analyst sees what failed
- Unconfigured/skipped providers NOT shown in detail rows — only providers that ran appear

**Dashboard provider coverage**
- New static text row below existing verdict KPI cards
- Shows: "8 registered · 5 configured · 3 need API keys" (or similar)
- Not interactive — settings link already exists in header gear icon

### Claude's Discretion
- Exact CSS implementation of slide animation (CSS transition vs keyframes)
- Chevron icon implementation (SVG, Unicode, or CSS triangle)
- How to determine "most detailed provider" algorithmically (heuristic for picking the attribution source)
- Provider coverage row exact layout and typography
- How to handle edge case where all providers return no-data (no worst verdict to display)
- Whether to preserve the existing no-data collapsible `<details>` pattern or fold it into the new expandable section

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UX-01 | Each IOC card shows a unified verdict summary aggregated across all providers | `computeWorstVerdict()` already exists in `enrichment.ts`; need summary row in HTML template and `renderSummaryRow()` in TS |
| UX-02 | Clicking a card expands to show per-provider detail rows with individual results | New `.enrichment-details` expandable container; chevron toggle in card header; CSS max-height transition pattern |
| UX-03 | Provider status indicators show which providers contributed data vs. skipped vs. errored | Provider detail rows with per-verdict CSS classes; error rows in red; sorting by `VERDICT_SEVERITY` |
| UX-04 | The settings page shows all registered providers with configuration status | Already shipped in Phase 3 (Plan 03-03) — settings page loops over PROVIDER_INFO with status indicators |
| UX-05 | E2E tests pass for the new results layout | New ResultsPage POM methods for summary row, consensus badge, expand/collapse; existing offline test pattern works |
</phase_requirements>

---

## Summary

This phase is a **pure frontend UX refactor** — no new backend endpoints, no new data models, and no changes to Flask routes. All enrichment data already flows to the browser via the existing `/enrichment/status/<job_id>` polling endpoint. The work is entirely in three layers: HTML templates, TypeScript modules, and CSS.

The architecture is already well-prepared. `computeWorstVerdict()` exists in `enrichment.ts`, `iocVerdicts` already tracks per-provider `{provider, verdict, summaryText}` entries per IOC, and `VERDICT_SEVERITY` provides the sort order for detail rows. The main work is restructuring how results are rendered into cards: instead of appending provider rows directly into `.enrichment-slot`, we build a summary header row first, then route detail rows into a collapsed/expandable container.

The expand/collapse mechanic is pure CSS + vanilla TS — no new libraries needed. The project deliberately avoids Alpine.js or React. The CSS `max-height` transition is the standard pattern for animating height-unknown content in vanilla CSS, which matches how `v1.3 motion design` used transitions throughout (see `--duration-normal: 250ms` and `--ease-out-quart`). The dashboard provider coverage row is a backend-assisted addition: the Flask `analyze` route already computes `provider_counts`; we need to add two more registry query calls for total registered vs. total configured.

**Primary recommendation:** Refactor `renderEnrichmentResult()` in `enrichment.ts` to build a summary row on first result + route all subsequent results into a hidden detail container; add CSS `max-height` transition for the expand/collapse; add provider coverage to `_verdict_dashboard.html` fed from a new `provider_coverage` template variable.

---

## Standard Stack

### Core (already in use — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| TypeScript | 5.8 (esbuild compile) | Frontend logic | Already in use; strict mode enforced |
| Tailwind CSS standalone CLI | latest | CSS utility classes | Already integrated via Makefile `css` target |
| CSS custom properties | native browser | Design tokens | `input.css` defines all verdict/color/motion tokens |
| Playwright | latest | E2E testing | Existing test suite; `tests/e2e/` infrastructure in place |
| pytest | latest | Test runner | Existing unit + integration test suite |

### Supporting (already present)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `VERDICT_SEVERITY` constant | n/a | Severity sort order for detail rows | Use in sort comparator — `["error","no_data","clean","suspicious","malicious"]` |
| `VERDICT_LABELS` constant | n/a | Display labels | Use for summary line and detail badge text |
| `computeWorstVerdict()` | n/a | Worst verdict across providers | Reuse directly — already in `enrichment.ts` |
| `iocVerdicts` accumulator | n/a | Per-provider result tracking | Already populated per-IOC — foundation for both summary and detail rows |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| CSS `max-height` transition | CSS `grid-template-rows: 0 → 1fr` trick | `grid-template-rows` transition is modern and avoids `max-height` over-estimation jank, but has slightly lower browser support. Either works; `max-height` is simpler and well-understood in this codebase. |
| Unicode chevron (▶/▼) | Inline SVG chevron | SVG gives pixel-perfect sizing and inherits currentColor; Unicode is simpler but size/alignment less controllable. Recommend SVG via CSS `content` or an `<svg>` element. |
| `<details>/<summary>` HTML element | Custom div + TS toggle | `<details>` provides free keyboard + accessibility handling but cannot be CSS-animated smoothly. TS-controlled `aria-expanded` + `max-height` gives animation control needed for 200ms slide. |

**Installation:** No new packages needed — this phase is entirely within the existing stack.

---

## Architecture Patterns

### Recommended File Touch Map

```
app/
├── templates/partials/
│   ├── _ioc_card.html              # Add summary row + expand toggle + details container
│   ├── _enrichment_slot.html       # Restructure: summary-first, details-expandable
│   └── _verdict_dashboard.html     # Add provider coverage row
├── routes.py                       # Pass provider_coverage dict to results template
└── static/src/
    ├── ts/modules/enrichment.ts    # Refactor renderEnrichmentResult(), add summary logic
    ├── ts/modules/cards.ts         # Add updateConsensusBadge() exported function
    └── input.css                   # New: summary row, chevron, slide animation, coverage row
```

### Pattern 1: Summary Row — First-Result Construction

The summary row must exist before all provider results arrive (it appears on first result). Construct it on the first result for an IOC, then update it as new results arrive.

**What:** When `renderEnrichmentResult()` fires for an IOC for the first time (no `.ioc-summary-row` yet), create the summary row with current worst verdict + attribution. On each subsequent result, call `updateSummaryRow()` to refresh verdict, attribution text, and consensus badge.

**When to use:** Every call to `renderEnrichmentResult()` should check if `.ioc-summary-row` exists and either create or update it.

```typescript
// Source: enrichment.ts pattern (extending existing VerdictEntry tracking)

interface SummaryAttribution {
  provider: string;
  statText: string;     // e.g., "45/72 engines" or "12 reports"
  detailScore: number;  // higher = more detailed; used to pick "most detailed provider"
}

function computeAttribution(entries: VerdictEntry[]): SummaryAttribution {
  // "Most detailed" heuristic: provider with highest total_engines wins.
  // VirusTotal (72 engines) beats AbuseIPDB (confidence score 0-100).
  // Ties broken by verdict severity (worst verdict wins).
  // For error/no_data entries: skip (never attribution source).
  // Falls back to first non-no_data entry if no engines data.
}

function getOrCreateSummaryRow(slot: HTMLElement): HTMLElement {
  const existing = slot.querySelector<HTMLElement>(".ioc-summary-row");
  if (existing) return existing;

  const row = document.createElement("div");
  row.className = "ioc-summary-row";
  // Insert at top of slot (before any detail rows)
  slot.insertBefore(row, slot.firstChild);
  return row;
}

function updateSummaryRow(
  slot: HTMLElement,
  iocValue: string,
  iocVerdicts: Record<string, VerdictEntry[]>,
  iocResultItems: Record<string, EnrichmentResultItem[]>
): void {
  // Build: [MALICIOUS] — VirusTotal: 45/72 engines  [3/5]
}
```

**Confidence:** HIGH — directly extends existing `VerdictEntry` accumulator pattern.

### Pattern 2: Expand/Collapse with CSS max-height Transition

The project uses CSS transitions throughout (see `--duration-fast: 150ms`, `--duration-normal: 250ms`, `--ease-out-quart`). The `max-height` transition is the right pattern for animating content with unknown height.

**What:** The `.enrichment-details` container starts at `max-height: 0; overflow: hidden`. Toggling `.is-open` class sets `max-height` to a value large enough to accommodate all content (e.g., `500px`). The transition property animates this change.

**When to use:** Applied to the details container div. The chevron button in the card header toggles the class.

```css
/* Source: input.css — new component */
.enrichment-details {
    max-height: 0;
    overflow: hidden;
    transition: max-height var(--duration-normal) var(--ease-out-quart);
}

.enrichment-details.is-open {
    max-height: 500px;  /* generous upper bound; actual height is less */
}

.chevron-toggle {
    transition: transform var(--duration-fast) var(--ease-out-expo);
    cursor: pointer;
}

.chevron-toggle.is-open {
    transform: rotate(90deg);
}
```

```typescript
// Source: enrichment.ts — wired once per card (not per result)
function wireExpandToggle(card: HTMLElement): void {
  const toggle = card.querySelector<HTMLElement>(".chevron-toggle");
  const details = card.querySelector<HTMLElement>(".enrichment-details");
  if (!toggle || !details) return;

  toggle.addEventListener("click", () => {
    const isOpen = details.classList.toggle("is-open");
    toggle.classList.toggle("is-open", isOpen);
    toggle.setAttribute("aria-expanded", String(isOpen));
  });
}
```

**Confidence:** HIGH — `max-height` transition is documented browser standard; consistent with existing motion tokens.

### Pattern 3: Provider Detail Row Sorting

Detail rows must be sorted by severity (malicious first, errors last). Since rows arrive asynchronously, sorting must happen after each new row is appended — use the existing debounced sort pattern from `cards.ts`.

**What:** After appending a new detail row to `.enrichment-details`, re-sort all children by their `data-verdict` attribute using `VERDICT_SEVERITY` index (descending).

```typescript
// Source: VERDICT_SEVERITY already defined in types/ioc.ts
// Pattern mirrors doSortCards() in cards.ts

function sortDetailRows(detailsContainer: HTMLElement): void {
  const rows = Array.from(
    detailsContainer.querySelectorAll<HTMLElement>(".provider-detail-row")
  );
  // Sort descending by severity (malicious=4 first, error=0 last)
  rows.sort((a, b) => {
    const va = VERDICT_SEVERITY.indexOf(
      (a.getAttribute("data-verdict") ?? "no_data") as VerdictKey
    );
    const vb = VERDICT_SEVERITY.indexOf(
      (b.getAttribute("data-verdict") ?? "no_data") as VerdictKey
    );
    return vb - va;  // descending: higher severity first
  });
  rows.forEach((row) => detailsContainer.appendChild(row));
}
```

**Confidence:** HIGH — directly follows existing `doSortCards()` pattern from `cards.ts`.

### Pattern 4: Consensus Badge Computation

**What:** Track responding providers (malicious + suspicious + clean = "responded") and flagging providers (malicious + suspicious = "flagged") per IOC. Update the badge after each result arrives.

```typescript
// Source: extends iocVerdicts accumulator in enrichment.ts

function computeConsensus(entries: VerdictEntry[]): { flagged: number; responded: number } {
  let flagged = 0;
  let responded = 0;
  for (const entry of entries) {
    if (entry.verdict === "malicious" || entry.verdict === "suspicious") {
      flagged++;
      responded++;
    } else if (entry.verdict === "clean") {
      responded++;
    }
    // no_data, error: not counted
  }
  return { flagged, responded };
}

function consensusBadgeClass(flagged: number): string {
  // green = 0 flagged, yellow = 1-2, red = 3+
  if (flagged === 0) return "consensus-badge--green";
  if (flagged <= 2)  return "consensus-badge--yellow";
  return "consensus-badge--red";
}
```

**Confidence:** HIGH — directly implements CONTEXT.md decision; uses existing verdict classification.

### Pattern 5: Provider Coverage in Dashboard

**What:** Pass three integers from Flask `analyze` route to the results template: `registered_count`, `configured_count`, `needs_key_count`. Render as a static text row below the four KPI cards.

**Backend addition to `routes.py` analyze route:**
```python
# Add after building registry (already done):
provider_coverage = {
    "registered": len(registry.all()),
    "configured": len(registry.configured()),
    "needs_key": len(registry.all()) - len(registry.configured()),
}
template_extras["provider_coverage"] = provider_coverage
```

**Template (`_verdict_dashboard.html`):**
```html
{% if provider_coverage %}
<div class="provider-coverage-row">
    {{ provider_coverage.registered }} registered
    &middot; {{ provider_coverage.configured }} configured
    &middot; {{ provider_coverage.needs_key }} need API keys
</div>
{% endif %}
```

**Confidence:** HIGH — `registry.all()` and `registry.configured()` already exist on `ProviderRegistry`.

### Anti-Patterns to Avoid

- **innerHTML for result content:** The codebase enforces `textContent` only (SEC-08). Never use `innerHTML` to build the summary row or detail rows — always `createElement + textContent`.
- **Accordion (one-open-at-a-time) behavior:** CONTEXT.md explicitly states independent state — multiple cards open simultaneously. Do NOT close other cards when one opens.
- **Counting error/no_data as "responded":** CONTEXT.md is explicit — consensus denominator excludes errors and no_data. Only malicious + suspicious + clean count.
- **Sorting inside the `renderEnrichmentResult` hot path without debounce:** The sort is O(n log n) and fires per result arrival. Use a per-card debounce timer (100ms, same as `sortCardsBySeverity`).
- **Hardcoding provider names:** Summary attribution text must use `result.provider` from the API, not a hardcoded string.
- **Animating display:none with CSS transitions:** CSS transitions do not work with `display: none`. Use `max-height: 0` + `overflow: hidden` for the expand/collapse container. This is already the pattern used by `.enrichment-nodata-section`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Slide animation | Custom JS height measurement + animation loop | CSS `max-height` transition | Native browser transition; already used for `.enrichment-nodata-summary::before` rotate; zero JS required |
| Chevron icon | Custom SVG file | Unicode `▶` rotated via CSS `transform: rotate(90deg)` OR inline SVG 4px × 8px | The `.enrichment-nodata-summary::before` already uses `\25B6` (▶) + CSS rotate — same pattern |
| Worst verdict | Custom severity comparison | `computeWorstVerdict()` in `enrichment.ts` | Already implemented, tested, and used |
| Provider sort order | Custom severity string map | `VERDICT_SEVERITY.indexOf()` | Already the pattern in `cards.ts::doSortCards()` |
| XSS-safe DOM construction | String concatenation + innerHTML | `createElement + textContent` | SEC-08 requirement; already enforced throughout |

**Key insight:** This phase has almost zero "new infrastructure" — it reorganizes existing pieces (VerdictEntry accumulator, VERDICT_SEVERITY, computeWorstVerdict, verdict CSS classes) into a new layout. The most novel part is the expand/collapse mechanic, which follows patterns already present in `.enrichment-nodata-section`.

---

## Common Pitfalls

### Pitfall 1: UX-04 is Already Done

**What goes wrong:** Wasting time re-implementing the settings provider listing — it was shipped in Phase 3, Plan 03-03.
**Why it happens:** Phase success criterion #4 says "settings page shows all registered providers with configuration status" — this could be misread as work still needed.
**How to avoid:** Verify before planning. The settings page loops over `PROVIDER_INFO` with `masked_key` and `configured` status. The only valid work here is an E2E test verifying it (if not already covered) or minor polish.
**Warning signs:** If a plan task says "add provider loop to settings template" — that's already done.

### Pitfall 2: Summary Row Needs Data from `EnrichmentResultItem`, Not Just `VerdictEntry`

**What goes wrong:** `VerdictEntry` (the existing accumulator) only stores `{provider, verdict, summaryText}`. The "most detailed provider" heuristic needs `detection_count` and `total_engines` from the raw `EnrichmentResultItem`.
**Why it happens:** The accumulator was designed for worst-verdict computation, not attribution selection.
**How to avoid:** Extend `VerdictEntry` to include `detectionCount` and `totalEngines`, OR maintain a parallel `iocResultItems` accumulator that stores the full `EnrichmentResultItem` per IOC.
**Warning signs:** If summary attribution always shows the wrong provider (e.g., always ThreatFox instead of VirusTotal).

### Pitfall 3: Detail Rows Must Be Created Even When Summary Exists

**What goes wrong:** Thinking "first result = create summary, subsequent results = update summary only." In fact, every result must also create a detail row in `.enrichment-details`.
**Why it happens:** The summary-vs-detail distinction can be misread as "first result vs. subsequent results."
**How to avoid:** Every call to `renderEnrichmentResult()` creates one detail row AND updates the summary. The summary creation is gated on "does summary row exist yet?" — detail row creation is unconditional.

### Pitfall 4: `max-height` Transition Needs a Concrete Upper Bound

**What goes wrong:** Using `max-height: 100%` or `max-height: auto` — neither animates in CSS.
**Why it happens:** Intuitive but wrong. CSS transitions require a numeric start and end value.
**How to avoid:** Use a generous concrete value like `max-height: 600px`. With 8 providers × ~24px per row, actual max is ~200px. 600px provides headroom for future providers.
**Warning signs:** Expand/collapse appears to snap (no animation) — `max-height` is not animating.

### Pitfall 5: Consensus Badge Updates Must Be Incremental

**What goes wrong:** Recomputing consensus by querying all `.provider-detail-row[data-verdict]` elements in the DOM — this creates a coupling between rendering order and badge accuracy.
**Why it happens:** Seems simpler than maintaining an in-memory counter.
**How to avoid:** Track consensus in memory via the `iocVerdicts` accumulator (same pattern as worst-verdict tracking). Call `computeConsensus(iocVerdicts[iocValue])` after each push.

### Pitfall 6: `prefers-reduced-motion` Must Be Respected

**What goes wrong:** Adding new CSS transitions without wrapping them in the reduced-motion media query exemption.
**Why it happens:** Easy to forget when adding new CSS rules.
**How to avoid:** The existing `@media (prefers-reduced-motion: reduce)` block in `input.css` (line 198) sets `transition-duration: 0.01ms !important` globally — new transitions are automatically covered. No special handling needed.

### Pitfall 7: `wireExpandToggle` Must Fire Once, Not Per-Result

**What goes wrong:** Calling `wireExpandToggle()` inside `renderEnrichmentResult()` — this attaches multiple click listeners to the same chevron as results arrive.
**Why it happens:** The toggle button is in `_ioc_card.html` (server-rendered), but `renderEnrichmentResult()` fires N times per IOC.
**How to avoid:** Wire expand toggles at page load (once, in `enrichment.ts init()` or a new `initExpandToggles()` function called from `init()`), not per-result arrival.

---

## Code Examples

### Complete Summary Row Structure (HTML)

```html
<!-- Source: design from CONTEXT.md — new in _enrichment_slot.html -->
<div class="ioc-summary-row">
    <span class="verdict-badge verdict-malicious">MALICIOUS</span>
    <span class="ioc-summary-attribution">VirusTotal: 45/72 engines</span>
    <span class="consensus-badge consensus-badge--red">[3/5]</span>
</div>
<button class="chevron-toggle" aria-expanded="false" aria-label="Toggle provider details">
    <!-- SVG or Unicode ▶ -->
</button>
<div class="enrichment-details">
    <!-- provider detail rows rendered by enrichment.ts -->
</div>
```

### Complete Provider Detail Row Structure (built by TS, SEC-08 safe)

```typescript
// Source: enrichment.ts pattern
function createDetailRow(result: EnrichmentItem, verdict: VerdictKey, statText: string): HTMLElement {
  const row = document.createElement("div");
  row.className = "provider-detail-row";
  row.setAttribute("data-verdict", verdict);

  const nameEl = document.createElement("span");
  nameEl.className = "provider-detail-name";
  nameEl.textContent = result.provider;  // textContent only, never innerHTML

  const badge = document.createElement("span");
  badge.className = "verdict-badge verdict-" + verdict;
  badge.textContent = VERDICT_LABELS[verdict];

  const stat = document.createElement("span");
  stat.className = "provider-detail-stat";
  stat.textContent = statText;  // e.g. "45/72 engines" or "12 reports" or error message

  row.appendChild(nameEl);
  row.appendChild(badge);
  row.appendChild(stat);
  return row;
}
```

### "Most Detailed Provider" Heuristic

```typescript
// Source: CONTEXT.md decision — Claude's discretion for implementation
// Priority: highest total_engines wins. VT (72 engines) > AbuseIPDB (score 0-100 = 1 "engine").
// For providers with total_engines = 1 (MB, TF, URLhaus, etc.), tie-break by severity.

function computeAttribution(entries: VerdictEntry[], resultMap: Record<string, number>): string {
  // entries includes {provider, verdict, summaryText, detectionCount, totalEngines}
  // After extending VerdictEntry or using a parallel accumulator

  const candidates = entries.filter(
    (e) => e.verdict !== "no_data" && e.verdict !== "error"
  );
  if (candidates.length === 0) {
    // Edge case: all no_data — show "no providers flagged this IOC"
    return "";
  }

  // Sort: highest totalEngines first; ties broken by severity descending
  const sorted = [...candidates].sort((a, b) => {
    const engineDiff = (b.totalEngines ?? 0) - (a.totalEngines ?? 0);
    if (engineDiff !== 0) return engineDiff;
    return VERDICT_SEVERITY.indexOf(b.verdict) - VERDICT_SEVERITY.indexOf(a.verdict);
  });

  const best = sorted[0];
  if (!best) return "";
  return best.provider + ": " + best.statText;
}
```

### Dashboard Provider Coverage Template

```html
<!-- Source: CONTEXT.md — below existing verdict KPI cards -->
{% if provider_coverage %}
<div class="provider-coverage-row">
    <span class="coverage-stat">{{ provider_coverage.registered }} registered</span>
    <span class="coverage-sep">&middot;</span>
    <span class="coverage-stat">{{ provider_coverage.configured }} configured</span>
    <span class="coverage-sep">&middot;</span>
    <span class="coverage-stat coverage-stat--warning">
        {{ provider_coverage.needs_key }} need API keys
    </span>
</div>
{% endif %}
```

### E2E Test Pattern for Expand/Collapse

```python
# Source: existing test_results_page.py pattern + Playwright docs
# Tests must use offline mode (no API key needed)

def test_ioc_card_expands_on_chevron_click(page: Page, index_url: str) -> None:
    """Clicking chevron expands the provider details section."""
    results = _navigate_to_results(page, index_url)
    card = results.ioc_cards.first

    details = card.locator(".enrichment-details")
    chevron = card.locator(".chevron-toggle")

    # Initially collapsed (aria-expanded="false")
    expect(chevron).to_have_attribute("aria-expanded", "false")

    chevron.click()

    expect(chevron).to_have_attribute("aria-expanded", "true")
```

Note: In offline mode, there are no enrichment results, so `.ioc-summary-row` will not be present until online mode fires. E2E tests for summary content require a mocked online flow or need to be online-mode only (similar to existing `test_online_mode_indicator` pattern).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| All provider rows appended flat into `.enrichment-slot` | Summary row + expandable detail container | Phase 4 | Analysts can scan at summary level without cognitive overload |
| `<details>/<summary>` for no-data grouping | Custom `max-height` transition for expand/collapse | Phase 4 | Consistent animation control with v1.3 motion design |
| Provider counts hardcoded in `_defaultProviderCounts` | Dynamic `data-provider-counts` from Flask registry | Phase 1 (01-02) | Already done — pending indicator uses real counts |

**Deprecated/outdated after Phase 4:**
- `.enrichment-nodata-section` (`<details>` element): Decision is "Claude's Discretion" whether to fold into the new expandable section or keep. Recommend: fold it in — no-data rows become the lowest-priority entries in the sorted detail rows, eliminating the nested `<details>` inside `<details>` oddity.

---

## Open Questions

1. **No-data edge case: all providers return no_data**
   - What we know: CONTEXT.md marks this as Claude's Discretion
   - What's unclear: Should summary row show `NO DATA — (no providers flagged)` with a neutral consensus `[0/0]`? Or hide the summary row entirely?
   - Recommendation: Show `NO DATA` verdict badge + attribution text "No providers flagged this IOC" + consensus badge `[0/N]` where N = responded providers (0 in this case). This is analyst-informative and consistent with the summary format.

2. **Phase 3 Plans 03-04 through 03-06 not yet complete**
   - What we know: STATE.md notes "Plans 03-04 through 03-06 remain" for Phase 3
   - What's unclear: Whether Phase 4 planning should wait for Phase 3 completion
   - Recommendation: Phase 4 research is valid now — no Phase 3 remaining plans affect the UX layer. Phase 3 plans may add more providers (which would increase provider counts) but the UX pattern is provider-count-agnostic. Safe to plan Phase 4 now.

3. **Extend VerdictEntry or use parallel accumulator?**
   - What we know: `VerdictEntry` currently stores `{provider, verdict, summaryText}`. Attribution needs `detectionCount` and `totalEngines`.
   - What's unclear: Whether extending the existing type is cleaner than maintaining two accumulators
   - Recommendation: Extend `VerdictEntry` to add `detectionCount: number` and `totalEngines: number`. The interface is module-private to `enrichment.ts`, so no external API breakage. Simpler than a second accumulator.

---

## Sources

### Primary (HIGH confidence)

All findings are derived from direct inspection of the project source code at `/home/chris/projects/sentinelx`:

- `app/static/src/ts/modules/enrichment.ts` — `VerdictEntry` interface, `computeWorstVerdict()`, `renderEnrichmentResult()`, `iocVerdicts` accumulator, polling loop structure
- `app/static/src/ts/modules/cards.ts` — `doSortCards()` severity sort pattern, `VERDICT_SEVERITY.indexOf()` usage
- `app/static/src/ts/types/ioc.ts` — `VerdictKey`, `VERDICT_SEVERITY`, `VERDICT_LABELS`, `getProviderCounts()`
- `app/static/src/ts/types/api.ts` — `EnrichmentResultItem`, `EnrichmentErrorItem`, discriminated union shape
- `app/static/src/input.css` — Motion tokens (`--duration-normal`, `--ease-out-quart`), `.enrichment-nodata-section` max-height/CSS transition pattern, `.verdict-badge` component, CSS custom property token system
- `app/templates/partials/_ioc_card.html` — Current card HTML structure
- `app/templates/partials/_enrichment_slot.html` — Current slot (shimmer only)
- `app/templates/partials/_verdict_dashboard.html` — Current 4 KPI cards
- `app/enrichment/registry.py` — `ProviderRegistry.all()`, `ProviderRegistry.configured()`
- `app/enrichment/setup.py` — `PROVIDER_INFO`, `build_registry()` (8 providers)
- `app/routes.py` — `analyze()` route: `provider_counts` JSON already passed to template
- `tests/e2e/test_results_page.py` — E2E test patterns, `_navigate_to_results()` helper
- `tests/e2e/pages/results_page.py` — `ResultsPage` POM structure
- `tests/e2e/conftest.py` — Live server fixture, offline mode test approach
- `.planning/phases/04-results-ux-upgrade/04-CONTEXT.md` — Locked decisions, discretion areas

### Secondary (MEDIUM confidence)

- CSS `max-height` animation pattern: well-documented browser standard; consistent with codebase's own use of `transition` throughout `input.css`
- `VERDICT_SEVERITY` sort pattern for detail rows: directly derived from `doSortCards()` in `cards.ts`

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all findings from direct code inspection
- Architecture: HIGH — directly extends existing `VerdictEntry`, `computeWorstVerdict()`, `VERDICT_SEVERITY` patterns
- Pitfalls: HIGH — derived from reading actual code paths (SEC-08 enforcement, timer handling, existing nodata section pattern)

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (stable codebase; no external dependencies)
