# M016: Email Reputation Depth

**Vision:** Make email IOCs first-class in Online mode by adding one focused, key-gated EmailRep integration with conservative verdict mapping, settings/registry coverage, compact analyst-facing rendering, and deterministic mocked end-to-end proof. The milestone deliberately stops short of raw EML/header phishing triage.

## Success Criteria

- EmailRep is registered as a key-gated provider for IOCType.EMAIL only.
- Configured Online mode reports email provider coverage and can enrich email IOCs without affecting existing provider behavior.
- EmailRep verdict mapping is explicit, conservative, and covered by tests for malicious, suspicious, clean, and no_data responses.
- EmailRep raw_stats are flattened into compact, safe UI context fields using existing textContent/createElement rendering paths.
- A mocked Online-mode E2E proof shows an email IOC rendering an EmailRep verdict/context row without requiring a live third-party key.

## Slices

- [ ] **S01: EmailRep adapter contract** `risk:high` `depends:[]`
  > After this: After this, a tested EmailRepAdapter exists and maps representative EmailRep responses into SentinelX verdicts without touching registry or UI behavior.

- [ ] **S02: Registry, settings, and email provider coverage** `risk:medium` `depends:[S01]`
  > After this: After this, configuring an EmailRep key makes Online mode report provider coverage for email IOCs; without a key, email coverage remains zero.

- [ ] **S03: Compact EmailRep result rendering** `risk:medium` `depends:[S01,S02]`
  > After this: After this, mocked EmailRep results render compact reputation and risk context in the existing result row UI without unsafe nested-data dumping.

- [ ] **S04: Mocked Online email enrichment proof** `risk:high` `depends:[S02,S03]`
  > After this: After this, a deterministic browser test submits an email IOC in Online mode and sees an EmailRep verdict/context row without requiring a live EmailRep key.

## Boundary Map

## Boundary Map

- **In:** EmailRep adapter, provider settings metadata, provider registry integration, allowed host config, EmailRep verdict mapping, compact row-factory context fields, mocked Online-mode E2E proof.
- **Out:** Raw EML parsing, header authentication analysis, broad phishing triage, multiple email reputation providers, required live EmailRep smoke tests.
- **Keep stable:** Existing OTX email exclusion, existing generic ConfigStore provider-key storage, existing BaseHTTPAdapter/safe_request safety path, existing email extraction/filter badge behavior.
