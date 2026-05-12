# M018: Diagnostic Log Export

**Vision:** Give SentinelX a local-first, analyst-safe diagnostic export that packages the right runtime/app context for debugging provider, settings, polling, and rendering failures without leaking API keys or producing unbounded log dumps.

## Success Criteria

- A diagnostic log export capability exists behind a supported local app path.
- Exports are bounded, deterministic, and include a manifest of included/omitted/truncated sources.
- Sensitive values are redacted before export and proven absent by tests.
- Export failures are visible and safe, not silent or secret-leaking.
- Analysts have concise guidance for generating and sharing the bundle.

## Slices

- [x] **S01: S01** `risk:high` `depends:[]`
  > After this: After this, the project has a precise log-export contract and tested redaction rules before any downloadable bundle is exposed.

- [x] **S02: S02** `risk:high` `depends:[]`
  > After this: After this, a backend service can assemble a deterministic diagnostic bundle from fixture/runtime sources with manifest, bounds, and safe per-source errors.

- [ ] **S03: S03** `risk:medium` `depends:[]`
  > After this: After this, analysts can download a diagnostic export from the app and route tests prove headers, redaction, and error responses.

- [ ] **S04: End-to-end proof and documentation** `risk:medium` `depends:[S03]`
  > After this: After this, a deterministic app-level proof downloads and inspects the log bundle, and docs describe safe sharing and limits.

## Boundary Map

## Boundary Map

- **In:** Diagnostic log/export bundle design, server-side export assembly, provider-secret redaction, bounded file/source inclusion, source manifest, UI/API download path, tests for redaction and content, analyst-facing documentation.
- **Out:** Cloud log shipping, remote telemetry, third-party observability SaaS, multi-user access control, long-term log retention policy beyond local export bounds, SIEM integration.
- **Keep stable:** Existing local-first app posture, existing ConfigStore secret storage, existing history/cache SQLite stores, existing enrichment result rendering, existing GSD/runtime transient-state ignore policy.
