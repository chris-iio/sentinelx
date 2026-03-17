# Requirements

## Active

### VIS-01 — Worst verdict is the dominant visual element in each IOC card header

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S03
- Implementation: `.verdict-label` enlarged to 0.875rem/700 in S03/T01; `.verdict-badge` remains at 0.72rem/600. Awaiting live UAT visual confirmation.

Worst verdict is the dominant visual element in each IOC card header

### VIS-02 — Verdict breakdown shows visual count bar of malicious/suspicious/clean/no-data providers (replaces text consensus badge)

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S03
- Implementation: `.verdict-micro-bar` with proportional segments replaces consensus badge text in S03/T01. Title tooltip shows counts. Awaiting live UAT visual confirmation.

Verdict breakdown shows visual count bar of malicious/suspicious/clean/no-data providers (replaces text consensus badge)

### VIS-03 — Provider rows display distinct category labels distinguishing Reputation from Infrastructure

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S03
- Implementation: `.provider-section-header` elements injected post-enrichment in S03/T02. Awaiting live UAT visual confirmation.

Provider rows display distinct category labels distinguishing Reputation from Infrastructure

### GRP-01 — Provider results are grouped into three sections: Reputation, Infrastructure Context, and No Data

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S04

Provider results are grouped into three sections: Reputation, Infrastructure Context, and No Data

### GRP-02 — No-data providers are collapsed by default with a count summary ("5 had no record")

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S03
- Implementation: `.provider-row--no-data` hidden by default; `.no-data-summary-row` with click toggle and keyboard a11y in S03/T02. Awaiting live UAT interaction confirmation.

No-data providers are collapsed by default with a count summary ("5 had no record")

### CTX-01 — Key context fields (GeoIP country, ASN org for IPs; registrar for domains) are visible in IOC card header without expanding

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S05

Key context fields (GeoIP country, ASN org for IPs; registrar for domains) are visible in IOC card header without expanding

### CTX-02 — Cached results show a staleness indicator ("data from 4h ago") in the summary row

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S05

Cached results show a staleness indicator ("data from 4h ago") in the summary row

## Validated

## Deferred

## Out of Scope
