---
estimated_steps: 4
estimated_files: 1
skills_used:
  - test
---

# T02: Test row-factory.ts DOM builders covering all visual redesign requirements

**Slice:** S03 — Visual Redesign
**Milestone:** M001

## Description

Every visual requirement (VIS-01, VIS-02, VIS-03, GRP-01, GRP-02, CTX-01, CTX-02) is implemented through exported functions in `row-factory.ts`. This task writes jsdom-based unit tests proving the DOM output of each function satisfies its requirement. The test framework (vitest + jsdom) was bootstrapped in T01.

Key requirement-to-function mapping:
- **VIS-01** (verdict badge prominence): Tested indirectly — CSS-only change, but `createDetailRow` must produce `.verdict-badge` with correct class. The `.verdict-label` sizing is CSS-only (tested visually, not unit-tested).
- **VIS-02** (micro-bar): `updateSummaryRow()` must create `.verdict-micro-bar` with correct segment counts and widths instead of `.consensus-badge`.
- **VIS-03** (category labels): Template now has `.provider-section-header` elements in `.enrichment-section--context` and `.enrichment-section--reputation`. The JS routes rows to the correct section container. `enrichment.ts` dispatches to sections via `.enrichment-section--reputation` / `.enrichment-section--context` / `.enrichment-section--no-data`.
- **GRP-01** (three sections): Template has three `.enrichment-section` containers. Routing is in `enrichment.ts` (not row-factory). Tested by verifying `createDetailRow` and `createContextRow` produce correct classes that match section selectors.
- **GRP-02** (no-data collapse): `injectSectionHeadersAndNoDataSummary()` creates `.no-data-summary-row` with count text, wires click toggle for `.no-data-expanded`.
- **CTX-01** (inline context): `updateContextLine()` populates `.ioc-context-line` with context provider data.
- **CTX-02** (staleness): `updateSummaryRow()` creates `.staleness-badge` when entries have `cachedAt`.

## Steps

1. Create `app/static/src/ts/modules/row-factory.test.ts`. Import all exported functions from row-factory.ts. Before each test, set up a minimal DOM structure that mirrors the real template (enrichment-slot with enrichment-details, enrichment sections, ioc-context-line, etc.).

2. Write tests for summary row creation and updates:
   - `getOrCreateSummaryRow()`: creates `.ioc-summary-row` with `role="button"`, `tabindex="0"`, `aria-expanded="false"`, and `.chevron-icon-wrapper` SVG. Idempotent — calling twice returns same element.
   - `updateSummaryRow()` — **VIS-02 coverage**: with mixed verdict entries (e.g., 2 malicious, 1 clean, 1 no_data), verify `.verdict-micro-bar` exists, contains correct number of `.micro-bar-segment` children, each with correct `--malicious`/`--clean`/`--no_data` class and percentage width. Verify `title` attribute on micro-bar encodes counts. Verify NO `.consensus-badge` element exists.
   - `updateSummaryRow()` — **CTX-02 coverage**: with entries that have `cachedAt` timestamps, verify `.staleness-badge` exists with "cached Xh ago" text. With no cached entries, verify no staleness badge.
   - `updateSummaryRow()` — edge case: zero-length entries array → early return, no crash.

3. Write tests for detail and context row creation:
   - `createDetailRow()` — verdict rows: verify `.provider-detail-row` class, `data-verdict` attribute, `.verdict-badge` with correct class, `.provider-detail-name` text, `.provider-detail-stat` text. With cache, verify `.cache-badge`.
   - `createDetailRow()` — **GRP-02 coverage**: when verdict is "no_data", verify row has class `provider-row--no-data`. When verdict is "error", also has `provider-row--no-data`. When verdict is "malicious", does NOT have `provider-row--no-data`.
   - `createContextRow()` — **GRP-01 coverage**: verify `.provider-detail-row.provider-context-row`, `data-verdict="context"`, no `.verdict-badge`, context fields rendered from `raw_stats`.
   - `injectSectionHeadersAndNoDataSummary()` — **GRP-02 coverage**: create a slot with `.enrichment-section--no-data` containing 3 `.provider-row--no-data` elements. Call function. Verify `.no-data-summary-row` exists with text "3 providers had no record". Simulate click → verify `.no-data-expanded` class toggles on section. Verify `aria-expanded` updates.
   - `injectSectionHeadersAndNoDataSummary()` — edge case: zero no-data rows → no summary row created.

4. Write tests for CTX-01 inline context:
   - `updateContextLine()` — **CTX-01 coverage**: with "IP Context" provider and `raw_stats.geo`, verify `.context-field` span with `data-context-provider="IP Context"` and geo text. With "ASN Intel" and no prior IP Context, verify ASN span. With "ASN Intel" after IP Context, verify ASN span NOT added (IP Context takes priority). With "DNS Records" and `raw_stats.a` array, verify A-record text. Upsert behavior: calling twice with same provider updates text, doesn't duplicate spans.

## Must-Haves

- [ ] `row-factory.test.ts` covers all 6 exported functions from row-factory.ts
- [ ] VIS-02: test asserts micro-bar segments exist with correct classes and widths
- [ ] GRP-02: test asserts `provider-row--no-data` class on no-data rows AND no-data-summary-row click toggle
- [ ] CTX-01: test asserts context-field spans for IP Context, ASN Intel, DNS Records with correct priority logic
- [ ] CTX-02: test asserts staleness-badge presence/absence based on cachedAt
- [ ] All tests pass: `npx vitest run` zero failures
- [ ] ≥20 test assertions in row-factory.test.ts

## Verification

- `npx vitest run` — all tests pass (both verdict-compute and row-factory), exit code 0
- `npx vitest run --reporter=verbose 2>&1 | grep -c "✓"` ≥ 30 total across both test files

## Inputs

- `app/static/src/ts/modules/row-factory.ts` — the module under test (561 LOC)
- `app/static/src/ts/modules/verdict-compute.ts` — imported by row-factory for VerdictEntry type and computation
- `app/static/src/ts/types/api.ts` — EnrichmentResultItem, EnrichmentItem types
- `app/static/src/ts/types/ioc.ts` — VerdictKey, VERDICT_LABELS
- `app/static/src/ts/modules/verdict-compute.test.ts` — T01 output, confirms test framework works
- `vitest.config.ts` — T01 output, test framework configuration
- `package.json` — T01 output, dependencies

## Expected Output

- `app/static/src/ts/modules/row-factory.test.ts` — new test file with ≥20 assertions covering all visual requirements
