# M018: Diagnostic Log Export

**Gathered:** 2026-05-12
**Status:** Ready for planning

## Project Description

SentinelX is a local-first threat intelligence hub for SOC analysts. Analysts paste free-form security text, extract IOCs, optionally enrich them through configured providers, and review unified verdicts with per-provider detail while preserving transparency, safe rendering, and local persistence.

## Why This Milestone

M018 exists because provider, polling, rendering, settings, and history failures are currently diagnosed through scattered server logs, browser assertions, and test artifacts. The user explicitly raised robust diagnostic-log export after M016 and chose to keep it as a dedicated operability milestone rather than expanding Email Reputation Depth. The milestone should make support and future agent debugging faster without exposing provider credentials or raw API keys.

## User-Visible Outcome

### When this milestone is complete, the user can:

- From an analysis/results context, download a deterministic diagnostic ZIP for a recent analysis.
- Share the bundle with a maintainer knowing configured provider secrets and raw API keys have been redacted and that included/omitted/truncated/error sources are declared in a manifest.

### Entry point / environment

- Entry point: analysis/results page or history-backed analysis detail path, with a supported local app download route.
- Environment: local dev / browser / production-like local Flask app.
- Live dependencies involved: SQLite history store, in-process enrichment orchestrator diagnostics, provider configuration store; no third-party provider calls are required for deterministic proof.

## Completion Class

- Contract complete means: tests prove the manifest/source contract, byte bounds, redaction primitives, and explicit included/omitted/truncated/error source states.
- Integration complete means: a backend assembler produces a deterministic ZIP from analysis-first sources, route tests prove headers/content/redaction/error behavior, and existing JSON/CSV/clipboard result export remains unaffected.
- Operational complete means: a browser/API proof downloads and inspects a bundle from the real app path after a deterministic mocked Online IOC failure/debug scenario; per-source failures produce partial bundles rather than silent loss.

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- A deterministic mocked Online analysis can be run, then a diagnostic ZIP can be downloaded from the analysis/history context and inspected for manifest, analysis metadata, provider/job diagnostics, polling/status context, health/settings/history-save context, and redaction evidence.
- Configured provider keys and raw API-token-like values are absent from every exported file, including nested diagnostic payloads and source error summaries.
- A failing diagnostic source still yields a safe partial bundle whose manifest marks the source as error/omitted/truncated without leaking exception secrets; the route only fails if the bundle cannot be created safely.
- What cannot be simulated for completion: the actual browser/app download path and archive inspection must be exercised; source inclusion/redaction cannot be accepted from unit tests alone.

## Architectural Decisions

### Analysis-first export entry point

**Decision:** M018 should start diagnostic export from the analysis/results context, including history-backed analysis details where possible.

**Rationale:** R083 is about a recent analysis or runtime session, and the highest-value support story is “why did this IOC enrichment/rendering look wrong?” Existing live results and `/history/<id>` contexts already carry job/analysis identity, provider results, and rendering state without inventing a separate workflow.

**Alternatives Considered:**
- Settings page — useful for configuration failures, but weaker for a specific enrichment job unless the analyst manually selects an analysis.
- Dedicated diagnostics page — clean separation, but more UI/routing surface than needed for the first supportable path.

### Deterministic ZIP with manifest

**Decision:** The exported artifact should be a small deterministic ZIP containing JSON/markdown diagnostic files plus a manifest of included, omitted, truncated, and error sources.

**Rationale:** A ZIP is more supportable than a single large JSON blob or markdown-only report because it can carry machine-readable sources and human-readable guidance while keeping deterministic names and bounded byte counts testable.

**Alternatives Considered:**
- Single JSON file — simpler but harder for humans to inspect and likely to become bulky as sources grow.
- Markdown report only — easiest to read, but weaker for automated support tooling and source-level verification.

### Omit raw pasted input by default

**Decision:** The diagnostic bundle should omit the original pasted analysis text by default and instead include bounded/redacted IOC, provider, status, and analysis metadata.

**Rationale:** Pasted alerts, reports, or email content may contain customer/internal data that provider-key redaction does not make safe. The first milestone should debug enrichment/rendering without making raw analyst input a default support artifact.

**Alternatives Considered:**
- Redacted input excerpt — helpful for extraction failures but higher privacy risk.
- Opt-in raw input — flexible, but adds UI state and proof surface beyond the first complete M018 path.

### Partial bundle failure model

**Decision:** Diagnostic source failures should produce a partial bundle whenever safe, with the manifest marking failed sources and summarizing errors safely.

**Rationale:** The broken subsystem may be the subsystem that needs diagnosis. Returning nothing because one source failed would make the export least useful exactly during support incidents.

**Alternatives Considered:**
- Strict all-or-nothing failure — simpler, but brittle for support.
- Manifest-only fallback — safe, but may not include enough context to debug.

## Error Handling Strategy

Redaction must run before serialization. Each source should be independently bounded and independently recorded in the manifest as included, omitted, truncated, or error. Source failures should be represented by safe summaries that avoid raw exception payloads if they may contain secrets. The download route should return a safe error only when bundle creation itself cannot complete safely; otherwise it should return a partial bundle with visible per-source outcomes. Oversized fields should be truncated deterministically with byte/count metadata. Missing live job diagnostics for a history-backed analysis should be an omitted or unavailable source, not a fatal error.

## Risks and Unknowns

- Mapping live `job_id` diagnostics to history-backed analysis details — live orchestrator diagnostics are in memory and may be unavailable after process restart, so the manifest must distinguish live included vs history unavailable.
- Raw input omission may limit extraction-debug value — acceptable for the first milestone, but future opt-in raw input could be revisited.
- Redaction completeness — provider keys from `ConfigStore`, common auth headers, query tokens, nested JSON-like data, and source errors all need explicit tests.
- Existing result export continuity — the new diagnostic export must not break JSON/CSV/clipboard export covered by R008.
- Bundle size and determinism — archives need stable filenames/order/metadata and source byte limits to avoid flaky tests and unbounded support dumps.

## Existing Codebase / Prior Art

- `app/routes/history.py` — reloads persisted analyses at `/history/<analysis_id>` and renders `results.html` with `results_owner="history"`.
- `app/templates/results.html` — existing analysis/results UI and JSON/CSV/clipboard export controls; likely diagnostic-export affordance location, but existing controls must remain stable.
- `app/routes/_helpers.py` — owns live orchestrator registry, `_get_enrichment_status()`, history-save diagnostics, serialization, and terminal job behavior.
- `app/enrichment/orchestrator.py` — exposes `get_diagnostics(job_id)` with cache, retry, provider, error, and latency aggregates.
- `app/enrichment/history_store.py` — persists input text, IOCs, results, mode, verdict, and timestamps; M018 should avoid raw input export by default.
- `app/enrichment/config_store.py` — stores provider keys and exposes `all_provider_keys()` for ConfigStore-backed redaction inventory.
- `app/health_contract.py` and `tools/dev_server.py` — prior art for secret-free health/runtime metadata and local lifecycle diagnostics.
- `.gsd/DECISIONS.md` D075/D076/D077 — place log export in M018, keep it descoped from M016, and put S01 primitives under backend-only `app/diagnostics/`.

## Relevant Requirements

- R083 — Primary operability requirement: robust diagnostic bundle for recent analysis/runtime session with secrets redacted and enough context to debug provider, polling, rendering, and settings failures.
- R008 — Continuity requirement: existing enrichment polling and JSON/CSV/clipboard export behavior must not regress.
- R009 — Security requirement: CSP, CSRF, textContent-only DOM construction, SSRF allowlist, and host validation posture must be maintained.
- R011 — E2E quality requirement: browser coverage should be updated without reducing coverage; route-mocking infrastructure supports deterministic enrichment surface tests.

## Scope

### In Scope

- Backend-only contract and redaction primitives under `app/diagnostics/`.
- Deterministic diagnostic ZIP assembly with manifest and bounded sources.
- Analysis-first source set: analysis metadata, IOC/provider summaries, live job diagnostics when available, polling/status context, key-presence/settings diagnostics, health/version-style context, and safe history-save diagnostics.
- Browser/app download route and analyst-facing affordance from analysis/results or history detail.
- Documentation/guidance for generating and safely sharing the bundle.
- Unit, route, integration, and browser/API proof that redaction and partial-bundle behavior work.

### Out of Scope / Non-Goals

- Cloud log shipping, remote telemetry, SIEM integration, or third-party observability SaaS.
- Multi-user access control or long-term retention policy beyond local export bounds.
- Raw pasted input export by default.
- Changing provider enrichment semantics or existing JSON/CSV/clipboard result export behavior.
- Live third-party provider calls as a prerequisite for proof.

## Technical Constraints

- Local-first posture: exports are generated by the local Flask app and should not phone home.
- Redaction must cover configured provider secrets and raw API-token-like patterns before data enters archive files.
- Export size and per-source fields must be bounded and manifest-visible.
- ZIP generation must be deterministic enough for tests: stable names/order and no flaky timestamps if practical.
- History/live status differences must be explicit; unavailable live-only diagnostics are not fatal.
- Existing stable form/result controls and current export dropdown behavior must not be renamed or broken.

## Integration Points

- Results/history routes — expose the app download path from the analysis context.
- `HistoryStore` — provides persisted analysis data, with raw input omitted by default.
- `EnrichmentOrchestrator` — provides live job diagnostics when a job is still available.
- Routes helper diagnostics — provides polling/status and history-save context.
- `ConfigStore` — provides provider-secret inventory and key-presence diagnostics.
- Health contract — provides secret-free app/runtime context.
- Browser/E2E route-mocking infrastructure — proves deterministic mocked Online IOC failure/debug export without live provider calls.

## Testing Requirements

Testing must include unit tests for manifest/source contract and redaction primitives; composition tests proving malicious, oversized, nested, and malformed diagnostic records are bounded/redacted; backend assembler tests inspecting deterministic ZIP contents and per-source manifest states; route tests for download headers, archive content, CSRF/security expectations, safe route failures, and partial-bundle behavior; regression tests that existing JSON/CSV/clipboard export and results rendering remain intact; and an app-level browser/API proof that downloads and inspects the diagnostic ZIP after a deterministic mocked Online IOC scenario.

## Acceptance Criteria

- S01: Contract and redaction primitives define the source/manifest vocabulary, byte bounds, and ConfigStore-backed redaction rules without exposing a route or building a bundle.
- S02: Backend assembler creates deterministic ZIP bundles from fixture/runtime sources, with manifest entries for included/omitted/truncated/error sources and safe per-source errors.
- S03: A supported local app route and analysis-page/history-page affordance let analysts download the bundle; route tests prove headers, redaction, and safe errors.
- S04: End-to-end proof downloads and inspects a diagnostic bundle from the app, docs explain safe sharing and limits, and final regression preserves existing result export/rendering behavior.

## Open Questions

- Should a future milestone add an explicit opt-in raw input excerpt for extraction-specific debugging? Current thinking: omit raw input by default for M018.
- Should a standalone diagnostics page be added later for runtime-only failures? Current thinking: analysis-first path is enough for the first complete supportable capability.
- How long should live job diagnostics remain available for recently completed jobs? Current thinking: use existing bounded in-memory orchestrator registry and manifest unavailable diagnostics when evicted/restarted.
