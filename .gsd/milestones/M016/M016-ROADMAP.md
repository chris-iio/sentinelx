# M016: Email Reputation Depth

**Vision:** Make email IOCs first-class in Online mode by adding one focused, key-gated EmailRep integration with conservative verdict mapping, settings/registry coverage, compact analyst-facing rendering, and deterministic mocked end-to-end proof. The milestone deliberately stops short of raw EML/header phishing triage.

## Success Criteria

- EmailRep is registered as a key-gated provider for IOCType.EMAIL only.
- Configured Online mode reports email provider coverage and can enrich email IOCs without affecting existing provider behavior.
- EmailRep verdict mapping is explicit, conservative, and covered by tests for malicious, suspicious, clean, and no_data responses.
- EmailRep raw_stats are flattened into compact, safe UI context fields using existing textContent/createElement rendering paths.
- A mocked Online-mode E2E proof shows an email IOC rendering an EmailRep verdict/context row without requiring a live third-party key.

## Slices

- [ ] **S01: EmailRep launch-readiness bundle** `risk:high` `depends:[]`
  > After this: A tested EmailRepAdapter exists, EmailRep is registered/settings-visible/key-gated for email IOCs, compact flattened context is available to existing rendering paths, and mocked Online-mode E2E covers email enrichment without a live key.

- [ ] **S02: Reserved / absorbed into S01** `risk:medium` `depends:[S01]`
  > Registry, settings, and email provider coverage were implemented with the bundled S01 change.

- [ ] **S03: Reserved / absorbed into S01** `risk:medium` `depends:[S01]`
  > Compact EmailRep result fields are emitted by the adapter as flattened raw_stats for existing safe UI rendering.

- [ ] **S04: Reserved / absorbed into S01** `risk:high` `depends:[S01]`
  > Mocked Online email enrichment proof was implemented with the bundled S01 change.

## Boundary Map

## Boundary Map

- **In:** EmailRep adapter, provider settings metadata, provider registry integration, allowed host config, EmailRep verdict mapping, compact row-factory context fields, mocked Online-mode E2E proof.
- **Out:** Raw EML parsing, header authentication analysis, broad phishing triage, multiple email reputation providers, required live EmailRep smoke tests.
- **Keep stable:** Existing OTX email exclusion, existing generic ConfigStore provider-key storage, existing BaseHTTPAdapter/safe_request safety path, existing email extraction/filter badge behavior.
