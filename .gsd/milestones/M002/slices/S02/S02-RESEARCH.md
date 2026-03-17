# S02: At-a-glance enrichment surface — Research

**Date:** 2026-03-18
**Depth:** Light-to-targeted — the core TypeScript DOM builders and wiring already exist from M001. This slice is CSS polish + integration verification in the new layout context.

## Summary

The at-a-glance enrichment surface is **already built** in TypeScript. `updateSummaryRow()` in `row-factory.ts` constructs verdict badge, attribution text, micro-bar, and staleness badge. `updateContextLine()` populates geo/ASN/DNS context. `enrichment.ts` wires both into the rendering pipeline. All CSS classes exist: `.ioc-summary-row`, `.verdict-badge`, `.verdict-micro-bar`, `.staleness-badge`, `.ioc-context-line`, `.context-field`.

What's missing is **adaptation to the S01 single-column layout**:
1. The `.enrichment-slot` has `opacity: 0.85` (S01 placeholder signal) that never resets when enrichment data arrives — content renders dimmed.
2. The summary row and context line CSS were authored for the old 2-column card grid. In full-width rows, spacing, font sizes, and element proportions may need adjustment for readability at the new width.
3. The compressed verdict dashboard (S01) receives live counts via `updateDashboardCounts()` in `cards.ts` — already wired, but visual integration with the new layout needs verification.
4. No E2E or integration tests exist for the at-a-glance components (summary row, context line, micro-bar, staleness badge). The page object has no selectors for these.

The primary risk is **not code but design quality** — R002 says the at-a-glance surface must be readable without interaction. The work is CSS refinement, the opacity fix, and a verification pass to prove enrichment renders correctly into the new layout.

## Recommendation

Treat S02 as a **CSS-focused polish + integration verification slice**. Do not rewrite the TypeScript DOM builders — they work. Focus on:
1. Fix the `opacity: 0.85` → `1` transition when `.enrichment-slot--loaded` is added
2. Refine CSS for summary row, context line, micro-bar in full-width single-column context
3. Run the app with real enrichment data (or E2E suite) to verify rendering pipeline
4. Ensure the at-a-glance information hierarchy reads cleanly: verdict badge prominent, context line subordinate, micro-bar compact

## Implementation Landscape

### Key Files

- **`app/static/src/input.css`** (1872 lines) — Primary file for S02. Lines 1088-1102: `.ioc-context-line` and `.context-field` styles. Lines 1143-1153: `.enrichment-slot` base (contains the `opacity: 0.85` bug). Lines 1184-1216: `.verdict-badge` and `.ioc-summary-row`. Lines 1253-1270: `.verdict-micro-bar` and segments. Lines 1497-1505: `.staleness-badge`. **Needs:** opacity fix (`.enrichment-slot--loaded { opacity: 1; }`), spacing/sizing adjustments for full-width rows, potential transitions.

- **`app/static/src/ts/modules/row-factory.ts`** (564 lines) — Contains all at-a-glance DOM builders. `updateSummaryRow()` (line 254): verdict badge + attribution + micro-bar + staleness badge. `updateContextLine()` (line 433): geo/ASN/DNS context population. `getOrCreateSummaryRow()` (line 231): summary row insertion before chevron. **Likely no changes needed** unless summary row content needs reordering for visual hierarchy.

- **`app/static/src/ts/modules/enrichment.ts`** (491 lines) — Rendering orchestrator. `renderEnrichmentResult()` (line 201) routes context providers to `updateContextLine()`, reputation providers to `updateSummaryRow()`. Adds `.enrichment-slot--loaded` class. **Likely no changes needed** — wiring is complete.

- **`app/static/src/ts/modules/cards.ts`** (135 lines) — `updateDashboardCounts()` (line 69) updates compressed dashboard KPI counts. `updateCardVerdict()` (line 43) writes `data-verdict` attribute. **No changes needed.**

- **`app/static/src/ts/modules/verdict-compute.ts`** (122 lines) — `VerdictEntry` type includes `cachedAt` field (line 24). `computeAttribution()` returns "Provider: statText" for summary row. **No changes needed.**

- **`app/templates/partials/_ioc_card.html`** — DOM structure: `.ioc-card` → `.ioc-card-header` + `.ioc-original`(optional) + `.ioc-context-line` + `.enrichment-slot`. The context line is an empty div populated by JS. **No changes needed.**

- **`app/templates/partials/_enrichment_slot.html`** — Shimmer → summary row (JS-created) → chevron → expandable details with three sections (context/reputation/no-data). **No changes needed.**

### Existing At-a-Glance DOM Structure (post-S01)

The vertical composition inside each `.ioc-card` (now `flex-direction: column`):

```
.ioc-card [data-ioc-value, data-ioc-type, data-verdict]
├── .ioc-card-header (flex row)
│   ├── .ioc-row-left
│   │   ├── .verdict-label (e.g. "MALICIOUS" — updated by cards.ts)
│   │   ├── .ioc-type-badge (e.g. "IPV4" — muted by S01)
│   │   └── code.ioc-value (the actual IOC string)
│   └── .ioc-card-actions (Copy + Detail buttons)
├── .ioc-original (optional — shows if raw_match differs)
├── .ioc-context-line (empty → populated by updateContextLine: geo, ASN, DNS A)
└── .enrichment-slot (shimmer → replaced by JS)
    ├── .ioc-summary-row (JS-created by getOrCreateSummaryRow)
    │   ├── .verdict-badge (worst verdict pill)
    │   ├── .ioc-summary-attribution ("VirusTotal: 5/72 engines")
    │   ├── .verdict-micro-bar (colored segments)
    │   └── .staleness-badge (optional — "cached 2h ago")
    ├── .chevron-toggle (expand/collapse — hidden until --loaded)
    └── .enrichment-details (collapsed by default — S03 territory)
```

### Build Order

**Task 1: CSS polish — fix opacity, refine at-a-glance styles (~30 min)**
- Fix `.enrichment-slot--loaded { opacity: 1; }` (or remove base `opacity: 0.85` and handle shimmer state differently)
- Audit spacing: `.ioc-context-line` padding, `.ioc-summary-row` gap, `.verdict-micro-bar` width in full-width context
- Ensure verdict badge in summary row is visually prominent but doesn't compete with the `.verdict-label` in the card header (R003: verdict-only color)
- Verify `.ioc-context-line:empty { display: none; }` works correctly (no empty-line jump)
- Consider: add subtle transition on enrichment slot appearance (opacity 0→1 on `--loaded`)
- Build: `make css` + `make typecheck` + `make js-dev`

**Task 2: Integration verification (~20 min)**
- Run `pytest tests/e2e/test_results_page.py -q` to confirm no regressions
- Run `make typecheck` to confirm TS compilation
- Optionally run the app in online mode to visually verify enrichment rendering (if E2E covers it)
- Verify the compressed dashboard receives live counts during enrichment
- Confirm context line populates for IPs (geo from IP Context) and domains (DNS A records)
- Confirm summary row shows verdict badge + attribution + micro-bar for enriched IOCs
- Confirm staleness badge appears for cached results

This order is correct because CSS fixes must land before integration verification — otherwise the opacity bug will make visual verification ambiguous.

### Verification Approach

1. **Contract verification:** `make typecheck` exits 0, `make css` exits 0, `make js-dev` exits 0
2. **Integration verification:** `pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q` — 36 tests pass (same as S01 baseline)
3. **CSS regression check:** `grep -n 'opacity: 0.85' app/static/src/input.css` should no longer match `.enrichment-slot` base rule (or should be overridden by `--loaded` rule)
4. **Visual spot-check (human UAT):** enrichment-slot content at full opacity, context line visible for IP/domain IOCs, summary row readable at full width

## Constraints

- All DOM construction must use createElement + textContent (SEC-08) — but no new DOM builders expected in this slice
- D015: All 16 contract selectors frozen — do not rename `.ioc-card`, `.enrichment-slot`, etc.
- S01 design tokens must be used: `--verdict-*` for verdict colors, `--text-muted`/`--text-secondary` for chrome, `--bg-*` for backgrounds
- Build tools are worktree-local: always use `make css`, `make typecheck`, `make js-dev` — not bare binary calls

## Common Pitfalls

- **Removing opacity instead of overriding** — Don't remove `opacity: 0.85` from the base `.enrichment-slot` rule. It serves as a visual signal that the slot is in shimmer/placeholder state. Instead, add `.enrichment-slot--loaded { opacity: 1; }` so the transition is smooth.
- **Summary row verdict badge competing with header verdict label** — There are now two verdict indicators visible: `.verdict-label` in the header and `.verdict-badge` in the summary row. These serve different purposes (label = current card verdict, badge = worst enrichment verdict) but may visually compete. Keep the summary badge small/secondary — R003 says verdict is the only loud color, not that it should appear twice at full volume.
- **Context line padding in full-width rows** — Current padding is `0.125rem 1rem`. In full-width single-column layout, the left padding must align with the verdict label and value text above. Check visual alignment.

## Open Risks

- **"At-a-glance density" is the core design challenge** per the roadmap — too dense defeats the purpose, too sparse loses information. This slice is where that risk is retired or escalated. If the current DOM structure doesn't read cleanly at full width, minor CSS adjustments (font sizing, spacing, micro-bar width) should be sufficient. If it fundamentally doesn't work, that's a design rethink (unlikely given the structure is sound).
