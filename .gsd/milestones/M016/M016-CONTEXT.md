# M016: Email Reputation Depth

**Gathered:** 2026-05-09
**Status:** Ready for validation remediation

## Project Description

SentinelX is a local-first threat-intel evidence workbench. Its analyst loop is: paste messy security text, extract observables, choose Offline or Online intentionally, enrich when configured, and show transparent provider evidence clearly enough that the analyst can decide what matters.

M016 focuses that loop on email IOCs. Prior work already made email extraction/display first-class; this milestone makes Online mode treat email addresses as enrichable when a focused EmailRep key is configured, while keeping the UI compact, safe, and deterministic to test without a live third-party credential.

## Why This Milestone

Email addresses are common in phishing reports, abuse reports, and pasted analyst notes. Before M016, SentinelX could extract and display email IOCs but deliberately excluded them from enrichment provider coverage. That left Online mode with a visible capability gap: an analyst could paste an email address, but no configured provider could add reputation context.

M016 closes that gap narrowly. It adds one key-gated EmailRep provider for `IOCType.EMAIL`, wires it into settings and provider coverage, renders compact EmailRep context through the existing safe row-factory/result-application paths, and proves the assembled Online browser flow through a mocked status route. The milestone does not turn SentinelX into a phishing-header triage platform or broaden the provider surface beyond EmailRep.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Save an EmailRep API key through the existing Settings page without the raw key being echoed back.
- Paste an email IOC such as `analyst@example.test` into the local SentinelX browser app.
- Choose Online mode and see email provider coverage when EmailRep is configured.
- Review an EmailRep verdict and compact reputation/risk context in the existing result row UI.
- Expand the email result row for details while staying inside the safe, text-only rendering model used for other providers.

### Entry point / environment

- Entry point: local browser app, primarily `/settings`, `/`, Online analysis submission, `/enrichment/status/<job_id>`, result rows, and shared live result application.
- Environment: local dev / browser with deterministic tests. Live EmailRep credentials may be configured by an operator, but M016 validation does not require or publish live EmailRep smoke-test output.
- Live dependencies involved: EmailRep only when a key is configured and the user runs Online mode; mocked Online proof is used for repeatable validation.

## Completion Class

- Contract complete means: `EmailRepAdapter` supports `IOCType.EMAIL` only, requires a key, uses the existing BaseHTTPAdapter/safe_request safety path, and maps EmailRep responses conservatively into SentinelX verdicts.
- Integration complete means: settings metadata, registry construction, provider counts, Online status polling, and result application all treat configured EmailRep email coverage coherently without changing non-email provider behavior.
- UI complete means: EmailRep raw stats are flattened into compact scalar/list context fields and rendered with `createElement`/`textContent` through existing row-factory paths, with unsupported nested data omitted rather than dumped.
- Operational proof complete means: a deterministic mocked Online E2E test proves the browser flow from settings save through Online email submission to rendered EmailRep context without requiring a live EmailRep key.

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- EmailRep is registered as a key-gated provider for email IOCs only.
- Without a configured EmailRep key, email provider coverage remains zero and existing Offline/Online behavior does not regress.
- With a configured EmailRep key, Online mode reports email provider coverage and can launch an email enrichment job.
- EmailRep verdict mapping is explicit, conservative, and tested for malicious, suspicious, clean, and no_data-style responses.
- Mocked Online proof demonstrates an email IOC rendering an EmailRep verdict and compact context row in the browser.
- Safe rendering constraints remain intact: EmailRep values are inserted as text, nested raw payloads are not dumped, and raw provider keys are not echoed in settings, tests, or validation artifacts.

## Architectural Decisions

### Focus M016 on EmailRep depth, not broad phishing triage

**Decision:** Treat M016 as Email Reputation Depth: one focused EmailRep provider integration plus settings/registry/UI/E2E proof.

**Rationale:** Email extraction already exists, but Online enrichment did not cover email IOCs. EmailRep is a narrow, key-gated provider that closes the immediate email reputation gap without expanding SentinelX into raw EML parsing or full phishing investigation.

**Alternatives Considered:**
- Raw EML/header authentication triage — too broad and requires a separate parsing/authentication model.
- Multiple email reputation providers — unnecessary before proving one complete path.
- Live EmailRep smoke testing as a validation requirement — brittle and credential-dependent; deterministic mocked E2E proof is the milestone proof surface.

---

### Reuse existing provider and rendering safety paths

**Decision:** Implement EmailRep through the existing adapter registry, settings metadata, BaseHTTPAdapter/safe_request path, provider-count contract, and row-factory/result-application rendering path.

**Rationale:** The existing architecture already handles configured providers, Online progress, result application, and safe DOM construction. Reusing it avoids a provider-specific UI or unsafe raw JSON renderer.

**Alternatives Considered:**
- Provider-specific EmailRep renderer — higher risk, more DOM safety surface, and inconsistent with existing result rows.
- Dumping raw EmailRep JSON for transparency — unsafe and noisy; compact whitelisted fields provide analyst value without exposing nested payloads.

---

### Descope diagnostic log export to M018

**Decision:** Robust redacted diagnostic log export is not an M016 acceptance criterion; it is future M018 work tracked by R083 and D075/D076.

**Rationale:** Diagnostic bundle export is valuable operability work, but it cuts across provider, polling, rendering, settings, redaction, boundedness, and UI/API retrieval. Adding it to M016 would muddy validation of the EmailRep integration and require a separate proof surface.

**Alternatives Considered:**
- Implement diagnostic export in M016/S05 — rejected because S05 is validation remediation, not new production operability scope.
- Remove R083 — rejected because the user-raised need remains valid and should keep traceability into M018.

## Error Handling Strategy

M016 preserves SentinelX’s explicit provider failure model. EmailRep configuration state determines whether email IOCs have Online provider coverage. Provider failures should surface through the existing enrichment result/error path rather than hidden UI states. Offline mode remains local-only and does not call EmailRep. Online mode must continue to distinguish configured-provider coverage, progress, terminal errors, and provider failures through the existing status contract.

Settings and validation text must never echo raw EmailRep keys. Test fixtures may use fake key values only to exercise configuration flow and redaction behavior; validation artifacts should name key presence/configuration, not secret values.

## Risks and Unknowns

- EmailRep response semantics may evolve; conservative verdict mapping and explicit parser tests reduce this risk.
- EmailRep only covers email IOCs; domains, URLs, IPs, hashes, and other IOC types must continue through existing providers unchanged.
- Compact context rendering can become noisy if too many raw fields are exposed; M016 intentionally whitelists flattened fields and omits nested payloads.
- Live EmailRep smoke tests are credential- and network-dependent; M016 uses mocked Online E2E proof for deterministic closeout.
- Diagnostic export remains important but outside M016; R083 points to M018 so validation does not treat it as a blocker here.

## Existing Codebase / Prior Art

- `.gsd/REQUIREMENTS.md` — canonical requirement ledger, including R008/R009/R011 continuity and R083 future diagnostic export.
- `.gsd/DECISIONS.md` — D074 for safe EmailRep rendering and D075/D076 for M018 diagnostic-export ownership and M016 closeout reconciliation.
- `app/enrichment/adapters/emailrep.py` — EmailRep adapter and verdict/raw_stats mapping.
- `app/enrichment/registry.py` — provider registry and configured-provider construction.
- `app/settings.py` / settings templates — provider key metadata and redacted settings display.
- `app/routes/analysis.py` and `app/routes/enrichment.py` — Online provider counts, job setup, and status polling.
- `app/static/src/ts/modules/row-factory.ts` — compact provider-context rendering using safe DOM construction.
- `app/static/src/ts/modules/result-application.ts` — shared live/history result application.
- `tests/e2e/test_emailrep_online.py` — deterministic mocked Online browser proof.

## Relevant Requirements

- R008 — Enrichment polling, export, filtering, detail links, copy behavior, and progress surfaces remain continuity requirements while adding EmailRep Online coverage.
- R009 — CSP, CSRF protection, textContent-only DOM construction, SSRF allowlist, and host validation remain security requirements across the EmailRep settings/adapter/UI path.
- R011 — E2E tests must cover the new DOM structure and Online browser behavior without reducing existing coverage.
- R083 — Robust redacted diagnostic log bundle export is explicitly future M018 work, not an M016 implementation or validation blocker.

## Scope

### In Scope

- EmailRep adapter for `IOCType.EMAIL`.
- Conservative EmailRep verdict mapping and flattened raw_stats fields.
- Provider registry and settings integration for an EmailRep API key.
- Online provider-count coverage for configured EmailRep email enrichment.
- Compact EmailRep rendering through existing safe result-row paths.
- Deterministic mocked Online E2E proof for email IOC enrichment and rendering.
- Requirement/context reconciliation so M016 validation reflects the actual EmailRep roadmap.

### Out of Scope / Non-Goals

- Raw EML parsing.
- Header authentication analysis such as SPF/DKIM/DMARC phishing triage.
- Broad phishing investigation workflows.
- Multiple email reputation providers.
- Required live EmailRep smoke tests.
- Robust diagnostic log export; this is tracked as future M018/R083 work.
- New production observability surfaces beyond existing settings, status, result, and test artifacts.

## Technical Constraints

- Preserve existing Offline/Online semantics and non-email provider behavior.
- EmailRep must be key-gated and should not claim provider coverage when unconfigured.
- EmailRep must use the existing HTTP safety controls and allowed-host validation.
- Settings UI and validation artifacts must never echo raw provider secrets.
- UI rendering must use safe DOM construction (`createElement`, `textContent`, attributes) rather than `innerHTML` for provider/input data.
- Mocked Online E2E proof must not require a live EmailRep key or external network call.
- History replay must not re-query providers.

## Integration Points

- Settings provider metadata and key persistence/redaction.
- Provider registry and configured-provider counts.
- Online analysis job setup and enrichment status polling.
- EmailRep adapter verdict/raw_stats parsing.
- Shared live result application and row-factory provider-context rendering.
- Browser E2E fixtures and page objects for deterministic Online proof.

## Testing Requirements

M016 should combine adapter/unit proof, registry/settings proof, safe rendering proof, and browser proof.

Required proof classes:

- Adapter tests for supported type, configured/unconfigured behavior, HTTP safety path, and representative EmailRep verdict mapping.
- Registry/settings tests proving EmailRep appears as a configurable key-gated provider and raw keys remain redacted.
- Provider-count tests proving configured EmailRep contributes email provider coverage and unconfigured EmailRep does not.
- Frontend/TypeScript tests for compact EmailRep context rendering through safe existing paths.
- Browser proof for mocked Online email enrichment rendering, including progress/terminal state, verdict/context visibility, and no live key dependency.
- Continuity/security proof for R008/R009/R011 where touched surfaces overlap enrichment polling, CSRF/settings, safe rendering, and E2E coverage.

## Acceptance Criteria

- EmailRep enriches only email IOCs and leaves existing provider behavior stable.
- Configuring EmailRep through settings enables email provider coverage in Online mode.
- EmailRep verdict mapping is conservative, explicit, and covered by tests.
- EmailRep raw_stats render as compact whitelisted context fields, not raw JSON dumps.
- The mocked Online E2E test proves an email IOC can render EmailRep verdict/context through the real browser flow.
- Raw EmailRep keys are redacted and absent from settings assertions, tests, and validation text.
- R008, R009, and R011 are represented in M016 validation as supporting continuity/security/E2E coverage.
- R083 remains recorded but points to M018 diagnostic log export ownership rather than blocking M016.

## Open Questions

- Which additional email reputation sources, if any, should follow EmailRep in a future milestone?
- Should raw EML/header-authentication triage become its own milestone after diagnostic export work lands?
- What user-facing diagnostic bundle shape should M018 expose: browser download, API endpoint, CLI artifact, or a combination?
