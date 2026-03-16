# Phase 3: Visual Redesign - Research

**Researched:** 2026-03-17
**Domain:** CSS/TypeScript UI modification — verdict badge prominence, micro-bar, category labels, no-data collapse
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VIS-01 | Worst verdict badge is the dominant visual element in each IOC card header — noticeably larger and higher-contrast than provider row verdicts | `.verdict-label` CSS resizing; no class rename required; `cards.ts updateCardVerdict()` already writes the class |
| VIS-02 | Verdict breakdown shows visual count bar of malicious/suspicious/clean/no-data providers — replaces `[2/5]` text consensus badge | `updateSummaryRow()` in `row-factory.ts` is the only producer; `.consensus-badge` CSS replacement; `computeConsensus()` already tracks the counts needed |
| VIS-03 | Provider rows within Reputation and Infrastructure sections display a distinct category label | `createDetailRow()` and `createContextRow()` in `row-factory.ts` are the row factories; category labels require knowing which group each provider belongs to |
| GRP-02 | No-data providers are collapsed by default — only a count summary ("5 had no record") is visible without interaction | `createDetailRow()` in `row-factory.ts` creates all verdict rows; `renderEnrichmentResult()` in `enrichment.ts` decides whether to append; CSS toggle via class or `details`/`summary` element |

</phase_requirements>

---

## Summary

Phase 3 makes four targeted visual changes to the results page: enlarging the worst-verdict badge in each IOC card header (VIS-01), replacing the text consensus badge with a horizontal count bar (VIS-02), adding category section labels to provider rows (VIS-03), and collapsing no-data provider rows by default with a count summary (GRP-02).

All four changes are confined to two files: `app/static/src/input.css` (CSS changes) and `app/static/src/ts/modules/row-factory.ts` (DOM builder changes). The `enrichment.ts` orchestrator needs one small addition for GRP-02: it must count no-data providers and build the collapsed summary element instead of adding individual no-data rows to the details container. No template files change in Phase 3 (template restructuring is Phase 4). No new libraries are needed.

The 24 E2E-locked CSS selectors from CSS-CONTRACTS.md are all preserved. The changes are additive — new classes and elements, not renames of existing locked selectors. The critical risk is the no-data collapse (GRP-02): it must not break the expand-toggle wiring or the `.is-open` state that E2E tests may depend on. The collapse must be implemented as a JavaScript-controlled show/hide, not a hidden DOM element, so that expand reveals the full provider list without a DOM repopulation.

**Primary recommendation:** Implement the four requirements as four independent, sequentially verifiable tasks. CSS-only changes (VIS-01, VIS-03 partial) first, then DOM builder changes (VIS-02, VIS-03, GRP-02). Run `make typecheck && make js-dev` after each TS task, full E2E suite after the final task.

---

## Standard Stack

### Core (unchanged from existing project)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Tailwind CSS standalone | (existing) | Utility classes for new layout wrappers | Already in use; `make css` rebuilds |
| TypeScript | 5.8 | DOM builder changes in row-factory.ts | Already in use |
| esbuild | 0.27.3 | Bundles TS modules into main.js | Already in use |

### No new dependencies

Phase 3 adds no new libraries. All required capabilities are already in the codebase:
- `computeConsensus()` in `verdict-compute.ts` already returns `{flagged, responded}` — the micro-bar needs `malicious + suspicious` as "flagged", `clean` as "clean", and counts are derivable from the `VerdictEntry[]` array
- The verdict color tokens (`--verdict-malicious-bg`, etc.) in `:root` are already defined and available
- The `CONTEXT_PROVIDERS` set already distinguishes context-only providers from verdict providers — category label routing is already implicit in this set

### What we know about providers and categories

The CONTEXT_PROVIDERS set contains: `["IP Context", "DNS Records", "Cert History", "ThreatMiner", "ASN Intel"]`.

For VIS-03, "Reputation" providers are the verdict providers (not in CONTEXT_PROVIDERS): VirusTotal, MalwareBazaar, ThreatFox, AbuseIPDB, Shodan InternetDB, CIRCL Hashlookup, GreyNoise Community, URLhaus, OTX AlienVault.

"Infrastructure Context" providers are those in CONTEXT_PROVIDERS: IP Context, DNS Records, Cert History, ThreatMiner, ASN Intel.

The category label is derivable from `CONTEXT_PROVIDERS.has(result.provider)` — no new data structure needed.

---

## Architecture Patterns

### Recommended File Scope

```
app/static/src/input.css                    # VIS-01, VIS-02 (new classes), VIS-03 (new class), GRP-02 (new class)
app/static/src/ts/modules/row-factory.ts    # VIS-02 (updateSummaryRow rebuild), VIS-03 (label injection), GRP-02 (no-data builder)
app/static/src/ts/modules/enrichment.ts     # GRP-02 (no-data counting + summary row call change)
```

Template files (`_enrichment_slot.html`, `_ioc_card.html`, `results.html`) are NOT modified in Phase 3. Template restructuring is Phase 4.

### Pattern 1: VIS-01 — Verdict Badge Prominence (CSS-only)

**What:** The `.verdict-label` in `.ioc-card-header` is currently `font-size: 0.7rem` with `padding: 0.1rem 0.4rem`. Making it the dominant visual element means increasing its size relative to the provider-row `.verdict-badge` (currently `0.72rem`). The card header badge needs to be meaningfully larger.

**Approach:** Modify `.verdict-label` in `input.css` directly. No class rename (`.verdict-label` is E2E-locked). Increase `font-size`, `padding`, possibly `font-weight`. The provider-row `.verdict-badge` stays at its current size — the contrast is achieved by increasing only `.verdict-label`.

**Current sizes:**
- `.verdict-label`: `font-size: 0.7rem`, `padding: 0.1rem 0.4rem`, `border-radius: 2rem`
- `.verdict-badge` (provider rows): `font-size: 0.72rem`, `padding: 2px 8px`, `border-radius: 2rem`

Both are nearly identical in current code — there is no hierarchy. Phase 3 must create clear size differentiation.

**Recommended target:**
- `.verdict-label`: `font-size: 0.875rem`, `padding: 0.25rem 0.75rem` — significantly larger
- `.verdict-badge`: unchanged at `0.72rem` / `2px 8px`

This is a pure CSS change. Zero TypeScript changes needed.

**Warning:** The CSS-CONTRACTS.md "Information Density Acceptance Criteria" requires `.verdict-label` to remain always visible. This change makes it more visible — not less. No regression risk.

### Pattern 2: VIS-02 — Micro-Bar Replacing Consensus Badge

**What:** Replace `updateSummaryRow()`'s consensus badge (`[2/5]` text) with a horizontal count bar showing proportional segments: malicious (red), suspicious (amber), clean (sky), no-data (zinc). The bar encodes proportion visually instead of textually.

**DOM structure (new):**
```
.ioc-summary-row
  .verdict-badge.verdict-{worst}   ← unchanged (VIS-01 makes this larger via CSS)
  .ioc-summary-attribution         ← unchanged
  .verdict-micro-bar               ← NEW: replaces .consensus-badge
    .micro-bar-segment.micro-bar-segment--malicious  (width: N%)
    .micro-bar-segment.micro-bar-segment--suspicious (width: N%)
    .micro-bar-segment.micro-bar-segment--clean      (width: N%)
    .micro-bar-segment.micro-bar-segment--no_data    (width: N%)
```

**Data source:** `computeConsensus()` returns `{flagged, responded}`. Phase 3 needs more granularity — counts of malicious, suspicious, clean, no_data separately. These are computable from `VerdictEntry[]` directly:

```typescript
// In row-factory.ts — new helper replacing consensusBadgeClass usage in updateSummaryRow
function computeVerdictCounts(entries: VerdictEntry[]): {
  malicious: number; suspicious: number; clean: number; no_data: number; total: number
} {
  let malicious = 0, suspicious = 0, clean = 0, no_data = 0;
  for (const e of entries) {
    if (e.verdict === "malicious") malicious++;
    else if (e.verdict === "suspicious") suspicious++;
    else if (e.verdict === "clean") clean++;
    else no_data++;  // error, known_good, no_data all group here for bar purposes
  }
  return { malicious, suspicious, clean, no_data, total: entries.length };
}
```

**CSS (new classes — not E2E locked):**
```css
.verdict-micro-bar {
    display: flex;
    height: 6px;
    border-radius: 3px;
    overflow: hidden;
    min-width: 4rem;
    flex-shrink: 0;
    background-color: var(--bg-tertiary);  /* fallback if all no-data */
}

.micro-bar-segment {
    height: 100%;
    transition: width var(--duration-fast) ease;
    min-width: 0;
}

.micro-bar-segment--malicious  { background-color: var(--verdict-malicious-border); }
.micro-bar-segment--suspicious { background-color: var(--verdict-suspicious-border); }
.micro-bar-segment--clean      { background-color: var(--verdict-clean-border); }
.micro-bar-segment--no_data    { background-color: var(--bg-hover); }
```

**Implementation location:** `updateSummaryRow()` in `row-factory.ts`. Remove the `consensusBadge` creation lines; add the micro-bar creation block.

**Critical: `.consensus-badge` is an E2E-locked runtime class** (CSS-CONTRACTS.md line 80). It MUST NOT be removed from the DOM silently. The E2E contracts say it must be "visible without hover" — but Phase 3 replaces it with the micro-bar. The resolution: `updateSummaryRow()` still creates a `.consensus-badge` element but gives it `style="display:none"` (hidden, still present in DOM for any E2E selectors), OR the test actually only asserts presence in the "visible without hover" information density criteria, not in E2E Playwright selectors.

**Re-checking CSS-CONTRACTS.md:** The `.consensus-badge` IS in the JS-Created Runtime Classes table (line 80 of CSS-CONTRACTS.md) — it is NOT in the E2E-Locked Selectors table. The E2E tests query `.verdict-labels()`, `.ioc_cards()`, etc. — there is NO E2E test that directly queries `.consensus-badge`. It is only listed under information density criteria ("Visible without hover — analyst needs consensus count at a glance").

**Resolution:** The micro-bar satisfies "consensus count at a glance" (it is visually richer). The `.consensus-badge` class can be removed from `updateSummaryRow()` with no E2E selector breakage. However, to preserve the information density contract (consensus count readable at a glance), the micro-bar must encode the counts clearly — a tooltip or `title` attribute on the bar segments showing the count is a simple addition. Or add a small text `N flagged` alongside the bar. The planner must decide: the research finding is that `.consensus-badge` E2E is not tested by Playwright but IS required by the information density criteria.

### Pattern 3: VIS-03 — Category Labels in Provider Rows

**What:** Each provider row inside `.enrichment-details` should show a visual category label ("Reputation" or "Infrastructure") so analysts can tell which section they are reading.

**Approach options:**

Option A — Label injected into each row (simple): Add a `.provider-category-label` span to each `createDetailRow()` and `createContextRow()` row. Cheap DOM, but adds repeated text per row.

Option B — Separator row injected once per group (better UX): Insert a non-provider separator row (`<div class="provider-section-header">Reputation</div>`) before the first row in each category. This is closer to what Phase 4 will do structurally, but Phase 3 does it purely via JS row insertion, not template changes.

Option C — CSS pseudo-element on first row of each group using `data-verdict` context: This requires CSS attribute selectors that can detect "first context row" or "first non-context row" — hard to do without `data-group` attribute.

**Recommended: Option B** — inject a section header separator row for each category. The separator is created in JS when the first row of each type appears. This is consistent with the Phase 4 direction (template restructuring will eventually provide these sections statically), so Phase 3 lays the dynamic groundwork.

**Implementation in `renderEnrichmentResult()` in `enrichment.ts`:**
```typescript
// Track whether section header has been injected per IOC
const sectionHeadersInjected: Record<string, { reputation: boolean; infrastructure: boolean }> = {};
```

OR, simpler: the section header is injected once per details container the first time a row of that type is added. Use a `data-section-header` attribute sentinel to detect if it was already injected.

**Injection point:** In `renderEnrichmentResult()`, before appending the row to `detailsContainer`, check if the category's section header exists and inject it if not.

**New DOM elements (not E2E-locked):**
```typescript
// New helper in row-factory.ts
export function createSectionHeader(label: string): HTMLElement {
  const header = document.createElement("div");
  header.className = "provider-section-header";
  header.setAttribute("data-section-label", label);
  header.textContent = label;
  return header;
}
```

```css
/* New CSS in input.css */
.provider-section-header {
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    padding: 0.4rem 0.5rem 0.15rem;
    margin-top: 0.25rem;
    border-top: 1px solid var(--border);
}

.provider-section-header:first-child {
    margin-top: 0;
    border-top: none;
}
```

**Important:** The `sortDetailRows()` function in `enrichment.ts` re-sorts `.provider-detail-row` elements. After sorting, context rows are pinned to top. Section headers (`.provider-section-header`) are NOT `.provider-detail-row` elements — they will NOT be moved by the sort. The sort only moves `.provider-detail-row` elements. This means after a sort, rows may move ahead of or behind the section header. **This is the critical interaction risk for VIS-03 + GRP-02.**

**Mitigation:** Section headers must be injected AFTER sorting stabilizes, or the section header injection must be deferred to after enrichment is complete. Alternatively, phase the section header injection to `markEnrichmentComplete()` rather than per-result — but that delays the label appearance.

The simplest safe approach: do NOT inject section headers per-result. Instead, create a `injectSectionHeaders(detailsContainer)` function called from `markEnrichmentComplete()` that scans the sorted rows and inserts labels in the correct position. This avoids the sort interaction entirely.

### Pattern 4: GRP-02 — No-Data Collapse

**What:** No-data provider rows (verdict === "no_data" or verdict === "error") are hidden by default. A count summary row ("5 had no record") is shown in their place. Clicking the summary expands the full list.

**Key decision — where is the collapsed section?**

Option A — Inside `.enrichment-details` (expanded with chevron): The no-data rows go inside `.enrichment-details` but wrapped in a collapsible sub-section. The main chevron toggle expands the details; within the details, no-data rows start hidden.

Option B — The no-data section is SEPARATE from `.enrichment-details`: A second expandable section below `.enrichment-details` holds no-data rows. This requires adding a new element to the slot.

**Recommended: Option A** — keep all rows inside `.enrichment-details` for simplicity. Add a `.no-data-toggle` row inside `.enrichment-details` that acts as a sub-toggle for the no-data subset. The no-data rows themselves get class `.provider-row--no-data` and are hidden by CSS until the toggle is activated.

**DOM structure in `.enrichment-details` after GRP-02:**
```
.enrichment-details (hidden until chevron click)
  .provider-section-header "Reputation"    ← VIS-03 (after sort stabilizes)
  .provider-detail-row[data-verdict=malicious]
  .provider-detail-row[data-verdict=clean]
  .provider-section-header "Infrastructure" ← VIS-03
  .provider-context-row[data-verdict=context]
  .no-data-summary-row                     ← NEW: "5 had no record ▶"
  .provider-detail-row.provider-row--no-data[data-verdict=no_data]  ← hidden by default
  .provider-detail-row.provider-row--no-data[data-verdict=no_data]
```

**New class `.provider-row--no-data`** is additive — does not conflict with existing `.provider-detail-row` E2E-locked behavior. The `data-verdict="no_data"` attribute remains unchanged on the row (locked contract).

```css
/* New CSS */
.provider-row--no-data {
    display: none;
}

.no-data-expanded .provider-row--no-data {
    display: flex;
}

.no-data-summary-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.35rem 0.5rem;
    font-size: 0.75rem;
    color: var(--text-muted);
    cursor: pointer;
    border-top: 1px solid var(--border);
    transition: color var(--duration-fast) ease;
}

.no-data-summary-row:hover {
    color: var(--text-secondary);
}
```

**TypeScript — toggle wiring:** The `.no-data-summary-row` click handler toggles `.no-data-expanded` on the `.enrichment-details` container (or a wrapper `<div>` inside it). Since `wireExpandToggles()` is called once in `init()` before enrichment starts, the no-data toggle must use event delegation or be wired separately.

**When is the no-data summary row created?** Options:
1. Per-result: when the first no-data result arrives, create the summary row and hide subsequent no-data rows — but the count is unknown at that time.
2. Post-enrichment: when `markEnrichmentComplete()` fires, scan all `.provider-detail-row[data-verdict=no_data]` elements and inject the summary row with the count.

**Recommended: post-enrichment injection.** Avoids intermediate states where the count is wrong. The summary row is injected in a new function called from `markEnrichmentComplete()`.

**Concern:** GRP-02 says "collapsed by default." If no-data rows don't appear until enrichment completes, there is no collapse transition — they simply never appear initially, which is acceptable for the "default" requirement. If providers arrive one at a time, no-data rows appear and disappear as they arrive — this would be jarring. So no-data rows should be hidden from the moment they are created, and the summary row injected after complete.

**Implementation flow:**
1. `createDetailRow()` — if verdict is "no_data" or "error", add class `provider-row--no-data` to the row (display: none via CSS)
2. `renderEnrichmentResult()` — no change; still appends the row normally (it's just hidden)
3. New function `injectNoDataSummary(detailsContainer)` — counts `.provider-row--no-data` elements, creates `.no-data-summary-row` with count text, inserts it before the first `.provider-row--no-data` element, wires click to toggle `.no-data-expanded` on container
4. `markEnrichmentComplete()` — calls `injectNoDataSummary()` for each `.enrichment-details` element on the page
5. Also call `injectSectionHeaders()` here for VIS-03 injection

### Anti-Patterns to Avoid

- **Renaming `.consensus-badge`:** It is in the JS-Created Runtime Classes table. Even though no E2E Playwright test queries it, the information density contract requires consensus to be visible. Remove its creation only after confirming no E2E query touches it.
- **Injecting section headers per result during sorting:** `sortDetailRows()` moves `.provider-detail-row` elements — it does not move non-`.provider-detail-row` elements. Headers injected per-result will become mispositioned after sort. Use post-enrichment injection.
- **Using CSS `display:none` on rows that E2E tests count:** The no-data rows must remain in the DOM (`display:none` is fine) — E2E tests that count `.provider-detail-row` elements would fail if rows were removed. However, the current E2E suite runs offline mode only — no provider rows exist in offline mode. No E2E test counts `.provider-detail-row` elements. This is safe.
- **Adding Tailwind utilities to existing elements (`.verdict-label`, `.provider-detail-row`):** Violates CSS Layer Ownership Rule from CSS-CONTRACTS.md. Only use Tailwind for new wrapper elements (`.verdict-micro-bar`, `.provider-section-header`).
- **Breaking the `sortDetailRows()` interaction:** This function sorts all `.provider-detail-row` elements and pins `data-verdict="context"` rows to top. No-data rows (`.provider-row--no-data`) are `.provider-detail-row` — they will be sorted too. Post-enrichment section headers and no-data summary rows (which are NOT `.provider-detail-row`) will stay in place during sort. This is correct behavior.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Proportional bar segments | Manual pixel calculation | CSS `flex` with percentage widths | `flex` handles proportional sizing with `width: {pct}%` set by JS |
| Category detection | New provider-category mapping structure | `CONTEXT_PROVIDERS.has(provider)` | Already distinguishes context vs verdict providers |
| Consensus count data | New tracking object | `VerdictEntry[]` already in `iocVerdicts[ioc_value]` | Loop the existing array at summary-row creation time |
| Animation for no-data expand | Custom JS animation | CSS `max-height` transition (same as `.enrichment-details.is-open` pattern) | Already proven pattern in the codebase |

**Key insight:** All the data needed for the four visual changes already exists in `iocVerdicts[ioc_value]` (a `VerdictEntry[]` array) and `CONTEXT_PROVIDERS`. No new state, no new API responses, no new data structures.

---

## Common Pitfalls

### Pitfall 1: Misidentifying which classes are E2E-locked vs runtime-only

**What goes wrong:** Removing `.consensus-badge` from `updateSummaryRow()` or renaming it breaks E2E tests silently if a Playwright test queries it. Checking CSS-CONTRACTS.md shows `.consensus-badge` is in the "JS-Created Runtime Classes" table (DO NOT RENAME) — but examining `results_page.py` and the test files confirms NO E2E test queries `.consensus-badge` directly via Playwright. The information density criteria require consensus to be visible but not via a specific class selector.

**How to avoid:** Before removing any class from DOM construction, grep the entire `tests/e2e/` directory for the class name. If no hits, it is safe to replace — but the information density requirement still must be met by the replacement element.

**Warning signs:** After removing `.consensus-badge`, run `grep -r "consensus-badge" tests/e2e/` — should return zero results.

### Pitfall 2: sortDetailRows() disrupting injected section headers

**What goes wrong:** Section headers are injected into `.enrichment-details` after the first few results arrive. Then `sortDetailRows()` fires (debounced 100ms) and re-orders `.provider-detail-row` elements. The headers are NOT `.provider-detail-row` so they don't move — but the rows that were below them now sort to positions above them, leaving the "Reputation" header in the wrong place.

**How to avoid:** Inject section headers ONLY after enrichment completes (in `markEnrichmentComplete()`). During live enrichment, rows render without category labels. Once all providers have responded, sort is stable, and the headers are injected in one pass over the final sorted order.

**Warning signs:** "Reputation" label appears below malicious rows; context rows appear above "Infrastructure" label.

### Pitfall 3: No-data rows hidden before no-data summary row exists

**What goes wrong:** `createDetailRow()` hides no-data rows immediately (Phase 3 approach). If enrichment never completes (e.g., network error stops polling mid-way), `markEnrichmentComplete()` never fires, the no-data summary row is never injected, and the analyst sees only verdict rows with no indication that no-data providers exist.

**How to avoid:** Also trigger `injectNoDataSummary()` and `injectSectionHeaders()` when enrichment is marked complete due to timeout or error. In `markEnrichmentComplete()` — the existing function already handles the "all done" state. Alternatively, inject the no-data summary row as each no-data result arrives (count = 1, 2, 3... updated per result). This avoids the completion dependency.

**Recommended alternative:** Update the no-data summary row count per-result: when a no-data result arrives, check if `.no-data-summary-row` exists in the container; if not, create it (count=1); if yes, increment its count. This gives live feedback during enrichment and does not depend on completion.

### Pitfall 4: VIS-01 size increase breaking `.ioc-card-header` layout

**What goes wrong:** `.ioc-card-header` uses `display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap`. The `.verdict-label` is `flex-shrink: 0`. Increasing its size from `0.7rem / 0.1rem 0.4rem` to `0.875rem / 0.25rem 0.75rem` increases its minimum size on the row. For IOCs with long values (`ioc-value` is `flex: 1`), this may push `.ioc-card-actions` to wrap to the next line.

**How to avoid:** Test the header layout with a long URL IOC (e.g., `https://malware.example.com/path/to/beacon/payload.exe`) after the size change. The `flex-wrap: wrap` on `.ioc-card-header` is a safety net — wrapping is acceptable. Confirm that `.verdict-label` remains within the `.ioc-card-header` row and is visible without horizontal scroll.

### Pitfall 5: Micro-bar width calculation with zero total providers

**What goes wrong:** If `entries.length === 0` (shouldn't happen, but defensive coding), dividing by total for percentage widths produces NaN or Infinity, which sets `style.width = "NaN%"`.

**How to avoid:** Guard with `if (total === 0) return` before computing percentages, or use `Math.max(1, total)` as the denominator.

---

## Code Examples

### VIS-01: CSS change to verdict-label

```css
/* Source: input.css — EXISTING .verdict-label block, modify in place */
/* After Phase 3 change — .verdict-label is the IOC card header badge */
.verdict-label {
    font-family: var(--font-mono);
    font-size: 0.875rem;        /* UP from 0.7rem — creates hierarchy vs .verdict-badge (0.72rem) */
    font-weight: 700;           /* UP from 600 */
    letter-spacing: 0.03em;
    text-transform: uppercase;
    padding: 0.25rem 0.75rem;   /* UP from 0.1rem 0.4rem — visually dominant */
    border-radius: 2rem;
    flex-shrink: 0;
}
```

### VIS-02: Micro-bar in updateSummaryRow

```typescript
// Source: row-factory.ts — replace the consensus badge block in updateSummaryRow()

// Private helper — compute per-verdict counts from entries
function computeVerdictCounts(entries: VerdictEntry[]): {
  malicious: number; suspicious: number; clean: number; noData: number; total: number;
} {
  let malicious = 0, suspicious = 0, clean = 0, noData = 0;
  for (const e of entries) {
    if (e.verdict === "malicious") malicious++;
    else if (e.verdict === "suspicious") suspicious++;
    else if (e.verdict === "clean") clean++;
    else noData++;  // error, known_good, no_data
  }
  return { malicious, suspicious, clean, noData, total: entries.length };
}

// Inside updateSummaryRow() — replaces consensusBadge block:
const counts = computeVerdictCounts(entries);
const total = Math.max(1, counts.total);

const microBar = document.createElement("div");
microBar.className = "verdict-micro-bar";
microBar.setAttribute("title",
  `${counts.malicious} malicious, ${counts.suspicious} suspicious, ` +
  `${counts.clean} clean, ${counts.noData} no data`
);

const segments: Array<[number, string]> = [
  [counts.malicious,  "malicious"],
  [counts.suspicious, "suspicious"],
  [counts.clean,      "clean"],
  [counts.noData,     "no_data"],
];
for (const [count, verdict] of segments) {
  if (count === 0) continue;
  const seg = document.createElement("div");
  seg.className = "micro-bar-segment micro-bar-segment--" + verdict;
  seg.style.width = Math.round((count / total) * 100) + "%";
  microBar.appendChild(seg);
}
summaryRow.appendChild(microBar);
```

### VIS-03 + GRP-02: Post-enrichment injection function

```typescript
// New exported function in row-factory.ts
export function injectSectionHeadersAndNoDataSummary(slot: HTMLElement): void {
  const detailsContainer = slot.querySelector<HTMLElement>(".enrichment-details");
  if (!detailsContainer) return;

  // --- Section headers (VIS-03) ---
  const rows = Array.from(detailsContainer.querySelectorAll<HTMLElement>(".provider-detail-row"));
  let lastSection: "infrastructure" | "reputation" | null = null;

  for (const row of rows) {
    const isContext = row.classList.contains("provider-context-row");
    const section = isContext ? "infrastructure" : "reputation";
    if (section !== lastSection) {
      lastSection = section;
      const label = section === "infrastructure" ? "Infrastructure Context" : "Reputation";
      const header = document.createElement("div");
      header.className = "provider-section-header";
      header.textContent = label;
      detailsContainer.insertBefore(header, row);
    }
  }

  // --- No-data summary (GRP-02) ---
  const noDataRows = detailsContainer.querySelectorAll<HTMLElement>(".provider-row--no-data");
  if (noDataRows.length === 0) return;

  const summaryRow = document.createElement("div");
  summaryRow.className = "no-data-summary-row";
  const count = noDataRows.length;
  summaryRow.textContent = count + " provider" + (count !== 1 ? "s" : "") + " had no record";

  const firstNoData = noDataRows[0];
  if (firstNoData) {
    detailsContainer.insertBefore(summaryRow, firstNoData);
  }

  summaryRow.addEventListener("click", () => {
    const expanded = detailsContainer.classList.toggle("no-data-expanded");
    summaryRow.setAttribute("aria-expanded", String(expanded));
  });
}
```

### GRP-02: createDetailRow modification

```typescript
// In createDetailRow() — add no-data class when verdict is no_data or error
export function createDetailRow(
  provider: string,
  verdict: VerdictKey,
  statText: string,
  result?: EnrichmentItem
): HTMLElement {
  const row = document.createElement("div");
  // Add provider-row--no-data class for hidden-by-default behavior (GRP-02)
  const isNoData = verdict === "no_data" || verdict === "error";
  row.className = "provider-detail-row" + (isNoData ? " provider-row--no-data" : "");
  // ... rest unchanged
```

### Build verification sequence

```bash
# After CSS changes:
make css

# After each TS file change:
make typecheck && make js-dev

# Phase gate:
pytest tests/ -m e2e --tb=short -q
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Text consensus badge `[2/5]` | Visual micro-bar (Phase 3) | Phase 3 | Encodes proportion, not just count; analyst reads severity distribution at a glance |
| No hierarchy between header verdict and row verdicts | `.verdict-label` noticeably larger than `.verdict-badge` | Phase 3 | Card header verdict becomes dominant scan target |
| No category label in provider rows | Section headers "Reputation" / "Infrastructure Context" | Phase 3 | Analyst knows at a glance which section they are reading without expanding all rows |
| No-data rows always visible in expanded view | Hidden by default, count summary visible | Phase 3 | Reduces cognitive load; analyst focuses on signal providers |

---

## Open Questions

1. **Should the no-data summary row be injected per-result or post-enrichment?**
   - What we know: Post-enrichment injection avoids mid-stream count updates; per-result injection handles the "enrichment fails to complete" edge case.
   - What's unclear: Whether analysts care about seeing "N had no record" update live during enrichment.
   - Recommendation: Per-result injection with live count updates. Creates a `.no-data-summary-row` on first no-data result; updates `textContent` on each subsequent one. More resilient to incomplete enrichment.

2. **Does the `.consensus-badge` class need to remain in the DOM for any E2E test?**
   - What we know: `grep -r "consensus.badge" tests/e2e/` — research confirms no E2E Playwright test queries `.consensus-badge`. It is only in the CSS-CONTRACTS runtime classes table as "DO NOT RENAME."
   - What's unclear: Whether "DO NOT RENAME" means "must stay in DOM" or just "do not change the class name if it exists."
   - Recommendation: The research finding is that no E2E test will break if `.consensus-badge` is removed from DOM construction. The planner should have the task executor run `grep -r "consensus" tests/e2e/` as a verification step before removing the class to confirm zero Playwright queries.

3. **Is `font-size: 0.875rem` for `.verdict-label` the right size, or should it be larger?**
   - What we know: Provider row `.verdict-badge` is `0.72rem`. The IOC card header `.ioc-type-badge` is `0.65rem`. The `.verdict-label` currently is `0.7rem` — barely visible hierarchy.
   - What's unclear: Whether `0.875rem` is "noticeably larger" enough to satisfy VIS-01's "dominant visual element" requirement, or if it needs to be `1rem+`.
   - Recommendation: `0.875rem` with `font-weight: 700` and `padding: 0.25rem 0.75rem` should create clear visual dominance. The planner can adjust in the plan.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + playwright-pytest (E2E) |
| Config file | `tests/e2e/conftest.py` |
| Quick run command | `pytest tests/ -m e2e --tb=short -q` |
| Full suite command | `pytest tests/ -m e2e --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VIS-01 | `.verdict-label` is visually larger than `.verdict-badge` in card header | Visual / CSS diff | Manual review (no automated pixel test in suite) | Manual only |
| VIS-02 | Micro-bar present in summary row; `.consensus-badge` `[2/5]` text absent | DOM structure | `pytest tests/ -m e2e --tb=short -q` — existing E2E catches regressions; micro-bar presence manual | Existing E2E |
| VIS-03 | Section headers "Reputation" and "Infrastructure Context" visible after enrichment | E2E online-mode test needed | `pytest tests/ -k "section_header" --tb=short` | ❌ Wave 0 — no test exists for section headers |
| GRP-02 | No-data rows hidden by default; count summary visible; expand works | E2E online-mode test needed | `pytest tests/ -k "no_data_collapse" --tb=short` | ❌ Wave 0 — no test exists for no-data collapse |
| (all) | No regression in 89/91 existing E2E tests | E2E suite | `pytest tests/ -m e2e --tb=short` | ✅ Existing |

**Note on VIS-01:** Pixel-level badge size testing is not feasible in the current Playwright suite (no screenshot comparison). VIS-01 is validated by human review after `make css` + browser reload. The planner should add a manual verification step.

**Note on VIS-03, GRP-02:** Both require enrichment results (online mode) to be visible. The current E2E suite runs exclusively in offline mode. New E2E tests for section headers and no-data collapse require an online-mode test fixture. This is a Wave 0 gap.

### Sampling Rate

- **Per CSS change:** `make css` then browser reload
- **Per TS file change:** `make typecheck && make js-dev`
- **Per task commit:** `pytest tests/ -m e2e --tb=short -q` — confirm 89/91 baseline
- **Phase gate:** Full suite + manual browser verification of VIS-01/VIS-03/GRP-02 in online mode

### Wave 0 Gaps

- [ ] `tests/e2e/test_visual_redesign.py` — covers VIS-03 (section headers after enrichment) and GRP-02 (no-data collapse/expand); requires online-mode fixture
- [ ] Online-mode E2E fixture — mock enrichment server returning controlled verdict mix (no existing mock; may use recorded responses or a simple stub)

*(VIS-01 and VIS-02 do not require new test infrastructure — VIS-01 is manual visual review, VIS-02 breaks no existing selector and is visible in the DOM after enrichment.)*

---

## Sources

### Primary (HIGH confidence)

- Direct code reading: `app/static/src/ts/modules/row-factory.ts` (373 LOC — complete DOM builder inventory)
- Direct code reading: `app/static/src/ts/modules/enrichment.ts` (482 LOC — orchestrator, `renderEnrichmentResult`, `markEnrichmentComplete`, `sortDetailRows`)
- Direct code reading: `app/static/src/ts/modules/verdict-compute.ts` (118 LOC — `computeConsensus`, `VerdictEntry`)
- Direct code reading: `app/static/src/input.css` (1744 LOC — all CSS variable tokens, `.verdict-label`, `.verdict-badge`, `.ioc-card-header`, `.ioc-summary-row`, `.consensus-badge` definitions)
- Direct code reading: `.planning/phases/01-contracts-and-foundation/CSS-CONTRACTS.md` — locked selectors, runtime classes, information density criteria
- Direct code reading: `tests/e2e/pages/results_page.py` — all Playwright selectors (no `.consensus-badge` query confirmed)
- Direct code reading: `tests/e2e/test_results_page.py`, `tests/e2e/test_extraction.py` — test coverage verified
- Direct code reading: `app/templates/partials/_ioc_card.html`, `_enrichment_slot.html` — DOM structure entering Phase 3

### Secondary (MEDIUM confidence)

- `grep -r "consensus" tests/e2e/` — confirmed no Playwright selector queries `.consensus-badge` directly
- Phase 2 SUMMARY.md — confirmed `createProviderRow` dispatcher and dependency graph

### Tertiary (LOW confidence — none)

All findings are from direct code inspection. No speculative claims.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — unchanged from Phases 1 and 2; no new libraries
- Architecture patterns: HIGH — all code paths read directly; `sortDetailRows` interaction is the one risk area, and mitigation is specified
- CSS specificity: HIGH — CSS Layer Ownership Rule is documented; no Tailwind-vs-component conflicts in the proposed changes
- Pitfalls: HIGH — based on direct code reading; sortDetailRows interaction confirmed by tracing the function
- Wave 0 test gaps: HIGH — confirmed by grepping E2E tests; online-mode tests don't exist

**Research date:** 2026-03-17
**Valid until:** Stable for this phase; Phase 4 template restructuring will change `_enrichment_slot.html` and `_ioc_card.html`, which may require re-reading those files before Phase 4 planning.

---

## Appendix: Current vs Target DOM for the Enrichment Slot

### Current summary row DOM (post Phase 2, pre Phase 3)

```html
<div class="ioc-summary-row">
  <span class="verdict-badge verdict-malicious">Malicious</span>
  <span class="ioc-summary-attribution">VirusTotal: 45/72 engines</span>
  <span class="consensus-badge consensus-badge--red">[3/5]</span>
</div>
```

### Target summary row DOM (post Phase 3)

```html
<div class="ioc-summary-row">
  <span class="verdict-badge verdict-malicious">Malicious</span>
  <span class="ioc-summary-attribution">VirusTotal: 45/72 engines</span>
  <div class="verdict-micro-bar" title="3 malicious, 0 suspicious, 2 clean, 4 no data">
    <div class="micro-bar-segment micro-bar-segment--malicious" style="width: 33%"></div>
    <div class="micro-bar-segment micro-bar-segment--clean" style="width: 22%"></div>
    <div class="micro-bar-segment micro-bar-segment--no_data" style="width: 44%"></div>
  </div>
</div>
```

### Current `.ioc-card-header` DOM (pre Phase 3)

```html
<div class="ioc-card-header">
  <code class="ioc-value">185.220.101.45</code>
  <span class="ioc-type-badge ioc-type-badge--ipv4">IPV4</span>
  <span class="verdict-label verdict-label--malicious">MALICIOUS</span>   ← 0.7rem
  <div class="ioc-card-actions">...</div>
</div>
```

### Target `.ioc-card-header` DOM (post Phase 3, VIS-01)

```html
<div class="ioc-card-header">
  <code class="ioc-value">185.220.101.45</code>
  <span class="ioc-type-badge ioc-type-badge--ipv4">IPV4</span>
  <span class="verdict-label verdict-label--malicious">MALICIOUS</span>   ← 0.875rem, larger padding
  <div class="ioc-card-actions">...</div>
</div>
```

No HTML changes — only CSS changes to `.verdict-label`.
