---
id: M016
title: "Email Reputation Depth"
status: complete
completed_at: 2026-05-11T19:14:10.351Z
key_decisions:
  - Use one focused EmailRep provider for M016 and exclude raw EML/header triage, broad phishing analysis, multiple providers, live smoke requirements, and diagnostic-log export.
  - Map EmailRep responses conservatively: confirmed abuse to malicious, lower-confidence risk to suspicious, high-reputation no-risk to clean, and absent/unknown reputation to no_data.
  - Flatten selected EmailRep raw_stats fields for UI consumption rather than rendering nested provider payloads.
  - Reuse ConfigStore provider-key storage and central build_registry() for EmailRep instead of adding a new settings or environment-variable mechanism.
  - Keep R083 diagnostic-log export active but future-owned by M018 rather than expanding M016 scope.
key_files:
  - app/enrichment/adapters/emailrep.py
  - app/enrichment/setup.py
  - app/config.py
  - app/static/src/ts/modules/row-factory.ts
  - app/static/src/ts/modules/row-factory.test.ts
  - app/static/src/ts/modules/result-application.test.ts
  - app/static/dist/main.js
  - tests/test_emailrep.py
  - tests/test_adapter_contract.py
  - tests/test_emailrep_registry_settings.py
  - tests/test_emailrep_online_coverage.py
  - tests/e2e/conftest.py
  - tests/e2e/pages/results_page.py
  - tests/e2e/test_emailrep_online.py
  - .gsd/PROJECT.md
  - .gsd/REQUIREMENTS.md
  - .gsd/milestones/M016/M016-LEARNINGS.md
lessons_learned:
  - Provider-count tests for EmailRep should isolate to a single email IOC fixture because domains inside example email addresses can otherwise create unrelated coverage noise.
  - Deterministic third-party provider E2E proof can preserve real browser/settings/polling behavior while mocking only the enrichment status seam and using fake credentials.
  - Validation/context artifacts can drift from the operative roadmap and need reconciliation before milestone closeout.
  - Safe provider rendering is easiest to preserve when backend adapters expose flattened compact fields and frontend tests include malformed nested payloads plus script-like values.
---

# M016: Email Reputation Depth

**SentinelX now supports key-gated EmailRep enrichment for email IOCs in Online mode with conservative verdict mapping, safe compact rendering, and deterministic mocked browser proof.**

## What Happened

M016 turned email IOCs from display-only artifacts into optional first-class Online enrichment targets through one focused EmailRep integration. S01 established the backend EmailRepAdapter contract: email-only support, API-key gating, shared BaseHTTPAdapter/safe_request execution, documented Key and User-Agent headers, URL-encoded lookups, conservative malicious/suspicious/clean/no_data verdict mapping, and flattened UI-facing raw_stats. S02 wired the adapter through the central registry/settings path without inventing a new secret mechanism: ConfigStore provider-key storage drives build_registry(), emailrep.io remains explicitly allowlisted for SSRF protection, missing or failed key lookup leaves email coverage at zero, and a configured key produces exactly one email provider without affecting non-email IOC coverage. S03 consumed the flattened raw_stats contract in the frontend by adding EmailRep to the existing provider-context field whitelist while keeping it a reputation provider; row-factory and result-application tests prove compact fields render safely through createElement/textContent and nested/raw payload dumping is avoided. S04 then proved the full assembled path in the browser: a fake key is saved through the real settings UI, Online submission of an email IOC uses a mocked enrichment status route, the shared polling/result-application path renders EmailRep verdict/context fields, and safety assertions confirm no key echo, no script execution, and no raw JSON/object dumping. S05 reconciled closeout scope, kept R083 diagnostic-log export future-owned by M018, and confirmed the retained EmailRep acceptance evidence. Final closeout verified code-change evidence from milestone commits touching non-.gsd implementation files, all roadmap success criteria, all slices complete with summaries, no unchecked roadmap or horizontal checklist items, and fresh acceptance commands passing: 219 focused pytest tests, 59 Vitest tests, and TypeScript noEmit.

## Success Criteria Results

- EmailRep registered as key-gated provider for IOCType.EMAIL only: met by S01 adapter support guards and S02 registry/settings tests proving configured EmailRep creates exactly one email provider and no non-email coverage.
- Configured Online mode reports email provider coverage and can enrich email IOCs without affecting existing provider behavior: met by S02 provider-count/settings route proof and S04 browser flow showing data-provider-counts email coverage during Online submission.
- EmailRep verdict mapping is explicit, conservative, and covered by tests: met by S01 pytest coverage for malicious, suspicious, clean, no_data, unsupported type, auth/header, URL encoding, and shared adapter contract invariants.
- EmailRep raw_stats are flattened into compact, safe UI context fields using existing textContent/createElement paths: met by S01 flattened stats contract and S03 row-factory/result-application tests for whitelisted compact fields, malformed nested data omission, and script-like values as text.
- Mocked Online-mode E2E proof shows an email IOC rendering an EmailRep verdict/context row without a live third-party key: met by S04 tests/e2e/test_emailrep_online.py saving a fake key, submitting analyst@example.com in Online mode, mocking enrichment status, expanding the row, and asserting EmailRep verdict/context rendering and key redaction.

## Definition of Done Results

- Code-change verification passed: HEAD self-diffed against main, so milestone commit evidence was inspected; commit 7f4e218d touched non-.gsd implementation and test files including app/enrichment/setup.py, app/config.py, app/static/src/ts/modules/enrichment.ts, app/templates/results.html, tests/e2e/test_emailrep_online.py, tests/test_api.py, tests/test_routes.py, and tools/dev_server.py.
- Slice completion passed: gsd_milestone_status reported S01-S05 all complete with all tasks done.
- Summary artifacts passed: S01-S05 SUMMARY.md files exist and contain passed verification evidence.
- Roadmap checklist passed: no unchecked slice items remain and no Horizontal Checklist is present.
- Integration passed: S01 adapter contract feeds S02 registry/settings, S03 compact rendering, and S04 mocked Online proof; S02 provider-count wiring feeds S03/S04; S03 shared row/result rendering feeds S04; S05 reconciles requirement/context scope.
- Fresh verification passed: python3 -m pytest tests/test_emailrep.py tests/test_adapter_contract.py tests/test_emailrep_registry_settings.py tests/test_emailrep_online_coverage.py tests/e2e/test_emailrep_online.py -q produced 219 passed; npx vitest run row-factory/result-application tests produced 59 passed; npx tsc --noEmit succeeded.

## Requirement Outcomes

- R078 transitioned from deferred to validated for EmailRep-backed email IOC reputation depth. Evidence: S01 adapter contract, S02 key-gated registry/settings/provider counts, S03 compact safe rendering, S04 mocked Online browser proof, and final closeout verification.
- R008 remains validated and was re-supported by M016 through provider-count/progress continuity, status polling, result application, and existing settings/results proof.
- R009 remains validated and was re-supported by M016 through emailrep.io allowlist coverage, unknown-provider rejection, secret redaction, CSRF-enabled settings/analyze paths, and safe text-only DOM rendering tests.
- R011 remains validated and was re-supported by M016 through the added mocked Online EmailRep E2E test and page-object locators without reducing existing coverage.
- R016 remains validated for email extraction/display compatibility; M016 extends email IOCs with optional EmailRep Online enrichment under R078 rather than re-proving the original display-only extraction contract.
- R083 remains active and future-owned by M018/TBD; it is explicitly descoped from M016 acceptance and is not a blocker for Email Reputation Depth completion.

## Deviations

- S01 found EmailRep registry/settings references already present beyond the adapter-only plan, so S02 explicitly verified and reconciled those seams instead of assuming them complete.
- S04 added direct isolated-config cleanup in the E2E test because settings saves through the session-scoped live server fixture could otherwise leak configured EmailRep state into sibling tests.
- S05 closeout repaired stale context/requirement framing and descoped R083 to M018 instead of implementing diagnostic-log export inside M016.

## Follow-ups

- Plan M018 diagnostic-log export for R083, including redaction, bounded bundle size, explicit included sources, and browser/API retrieval proof.
- Evaluate MalShare documentation surfaced during S03 as a future intelligence/provider source in a separate research or provider-integration milestone.
- Keep live EmailRep smoke testing optional/future; M016 intentionally relies on deterministic mocked Online proof rather than live third-party availability.
