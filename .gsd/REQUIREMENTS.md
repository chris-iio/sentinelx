# Requirements

## Active

### VIS-01 — Worst verdict is the dominant visual element in each IOC card header

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S03

Worst verdict is the dominant visual element in each IOC card header

### VIS-02 — Verdict breakdown shows visual count bar of malicious/suspicious/clean/no-data providers (replaces text consensus badge)

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S03

Verdict breakdown shows visual count bar of malicious/suspicious/clean/no-data providers (replaces text consensus badge)

### VIS-03 — Provider rows display distinct category labels distinguishing Reputation from Infrastructure

- Status: active
- Class: core-capability
- Source: inferred
- Primary Slice: S03

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

No-data providers are collapsed by default with a count summary ("5 had no record")

## Validated

### CTX-01 — Key context fields (GeoIP country, ASN org for IPs; registrar for domains) are visible in IOC card header without expanding

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S05
- Validation: S05 T01: updateContextLine() wired in enrichment.ts context branch; IP Context → geo string, ASN Intel fallback, DNS Records → A-record IPs; :empty CSS hides line for hash/URL/CVE. E2E baseline 89/2 maintained.

Key context fields visible in IOC card header without expanding — GeoIP/ASN for IPs, DNS A records for domains; hidden for hash/URL/CVE via CSS :empty.

### CTX-02 — Cached results show a staleness indicator ("data from 4h ago") in the summary row

- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: S05
- Validation: S05 T02: VerdictEntry.cachedAt propagated from result.cached_at; updateSummaryRow() renders .staleness-badge with formatRelativeTime() for oldest cached timestamp; absent for fresh results. E2E baseline 89/2 maintained.

Cached results show staleness badge ("cached Xh ago") in summary row; absent for fresh results.

## Deferred

## Out of Scope
