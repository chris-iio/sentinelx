# Requirements

## Active

## Validated

### VIS-01 — Worst verdict is the dominant visual element in each IOC card header

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S03
- Implementation: `.verdict-label` enlarged to 0.875rem/700 in S03/T01; `.verdict-badge` remains at 0.72rem/600.
- Validation: CSS confirmed in input.css; typecheck clean; 89/91 E2E pass; M001 milestone verification passed.

Worst verdict is the dominant visual element in each IOC card header

### VIS-02 — Verdict breakdown shows visual count bar of malicious/suspicious/clean/no-data providers (replaces text consensus badge)

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S03
- Implementation: `.verdict-micro-bar` with proportional segments replaces consensus badge text in S03/T01. Title tooltip shows counts.
- Validation: updateSummaryRow() renders micro-bar with computeVerdictCounts(); build clean; 89/91 E2E pass; M001 milestone verification passed.

Verdict breakdown shows visual count bar of malicious/suspicious/clean/no-data providers (replaces text consensus badge)

### VIS-03 — Provider rows display distinct category labels distinguishing Reputation from Infrastructure

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S03
- Implementation: `.provider-section-header` elements server-rendered in Jinja template (_enrichment_slot.html) since S04/T01.
- Validation: 3 .provider-section-header elements in template confirmed; createSectionHeader() removed from JS; 89/91 E2E pass; M001 milestone verification passed.

Provider rows display distinct category labels distinguishing Reputation from Infrastructure

### GRP-01 — Provider results are grouped into three sections: Reputation, Infrastructure Context, and No Data

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S04
- Implementation: Three server-rendered `.enrichment-section` containers in `_enrichment_slot.html` (context, reputation, no-data) with JS routing in `enrichment.ts` and CSS `:has()` empty-section hiding.
- Validation: 3 .enrichment-section containers in template confirmed; JS routing targets section-specific containers; CSS :has() hides empty sections; 89/91 E2E pass; M001 milestone verification passed.

Provider results are grouped into three sections: Reputation, Infrastructure Context, and No Data

### GRP-02 — No-data providers are collapsed by default with a count summary ("5 had no record")

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S03
- Implementation: `.provider-row--no-data` hidden by default; `.no-data-summary-row` with click toggle and keyboard a11y in S03/T02. Toggle targets `.enrichment-section--no-data` since S04.
- Validation: CSS hides .provider-row--no-data by default; .no-data-summary-row with click/keyboard toggle confirmed; aria-expanded state tracking; 89/91 E2E pass; M001 milestone verification passed.

No-data providers are collapsed by default with a count summary ("5 had no record")

### CTX-01 — Key context fields (GeoIP country, ASN org for IPs; registrar for domains) are visible in IOC card header without expanding

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S05
- Implementation: `.ioc-context-line` placeholder in `_ioc_card.html`, `updateContextLine()` in row-factory.ts handles IP Context (geo), ASN Intel (asn+prefix, deduped by IP Context), DNS Records (A records). `:empty { display: none }` hides for non-context IOC types.
- Validation: .ioc-context-line in template confirmed; updateContextLine() exported from row-factory.ts; called in enrichment.ts context branch; :empty CSS rule at line 1065; 89/91 E2E pass; M001 milestone verification passed.

Key context fields (GeoIP country, ASN org for IPs; registrar for domains) are visible in IOC card header without expanding

### CTX-02 — Cached results show a staleness indicator ("data from 4h ago") in the summary row

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S05
- Implementation: `VerdictEntry.cachedAt` optional field populated from `result.cached_at` in enrichment.ts. `updateSummaryRow()` renders `.staleness-badge` with oldest cache age via `formatRelativeTime()`.
- Validation: VerdictEntry.cachedAt field in verdict-compute.ts confirmed; .staleness-badge CSS rule confirmed; rendered in updateSummaryRow(); 89/91 E2E pass; M001 milestone verification passed.

Cached results show a staleness indicator ("data from 4h ago") in the summary row

## Deferred

## Out of Scope
