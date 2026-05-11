---
phase: complete-milestone
phase_name: Email Reputation Depth closeout
project: SentinelX
generated: 2026-05-11T19:12:32Z
counts:
  decisions: 5
  lessons: 4
  patterns: 5
  surprises: 3
missing_artifacts: []
---

# M016 Learnings: Email Reputation Depth

### Decisions

- Chose a focused EmailRep-only integration for email IOC reputation depth, explicitly excluding raw EML parsing, header authentication analysis, broad phishing triage, multiple email reputation providers, required live EmailRep smoke tests, and diagnostic-log export.
  Source: M016-ROADMAP.md/Boundary Map

- Chose conservative EmailRep verdict mapping: confirmed abuse signals map to malicious, lower-confidence risk/low-reputation signals map to suspicious, high-reputation no-risk responses map to clean, and absent/unknown reputation maps to no_data.
  Source: S01-SUMMARY.md/What Happened

- Chose flattened compact EmailRep `raw_stats` as the downstream contract instead of preserving nested provider payloads for UI rendering.
  Source: S01-SUMMARY.md/What Happened

- Chose the existing generic ConfigStore/provider registry/settings model for EmailRep keys and registration, with missing or failed key lookup treated as unconfigured rather than aborting registry composition.
  Source: S02-SUMMARY.md/What Happened

- Chose to keep R083 diagnostic-log export active but future-owned by M018 instead of expanding M016 after the EmailRep Online proof surfaced the need.
  Source: S05-SUMMARY.md/What Happened

### Lessons

- Requirement R016 was already validated for email extraction/display; M016 should preserve that compatibility while validating new email reputation depth under R078 rather than re-litigating the original extraction contract.
  Source: M016-VALIDATION.md/Requirement Coverage

- Provider settings tests must isolate the analysis pipeline to a single `IOCType.EMAIL` fixture when asserting EmailRep provider counts, because example email domains can otherwise introduce unrelated domain-provider coverage noise.
  Source: S02-SUMMARY.md/patterns_established

- Deterministic EmailRep Online proof does not require a live third-party key when the browser path saves a fake key through settings and the enrichment status route is mocked before submission.
  Source: S04-SUMMARY.md/What Happened

- Validation/context artifacts can drift from the operative roadmap; S05 had to reconcile stale context and requirement framing to match the completed EmailRep scope.
  Source: S05-SUMMARY.md/What Happened

### Patterns

- Add new HTTP providers through `BaseHTTPAdapter` and shared adapter-contract tests before registry, settings, or UI layers rely on the provider.
  Source: S01-SUMMARY.md/patterns_established

- Key-gated provider integrations should be verified through metadata, registry composition, provider counts, and route-level settings contracts before result-row rendering is added.
  Source: S02-SUMMARY.md/patterns_established

- Provider-specific compact UI rendering should be implemented as explicit field whitelists over flattened adapter contracts rather than raw nested provider dumps.
  Source: S03-SUMMARY.md/patterns_established

- Remote provider context reaching the DOM should be tested with malformed nested data and script-like scalar/list values to prove safe text rendering and omission of unsupported payloads.
  Source: S03-SUMMARY.md/patterns_established

- Provider-specific Online E2E proofs can deep-copy canned status payloads, override the submitted IOC, delegate to the existing route mock helper, and assert results-root metadata plus row-factory output.
  Source: S04-SUMMARY.md/patterns_established

### Surprises

- S01 closeout found the repository already contained EmailRep registry/settings references beyond the adapter-only plan, so downstream slices had to explicitly verify those seams instead of assuming them complete.
  Source: S01-SUMMARY.md/Deviations

- S04 needed direct isolated-config cleanup because the live-server config fixture is session-scoped and saving EmailRep through settings would otherwise leak into subsequent tests.
  Source: S04-SUMMARY.md/Deviations

- The user surfaced MalShare documentation during S03 closeout; it was useful future provider context but intentionally outside the EmailRep-only rendering slice.
  Source: S03-SUMMARY.md/Deviations
