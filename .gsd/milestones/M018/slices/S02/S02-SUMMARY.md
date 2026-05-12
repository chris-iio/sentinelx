---
id: S02
parent: M018
milestone: M018
provides:
  - Deterministic backend diagnostic ZIP assembly with manifest and stable archive paths.
  - Default safe runtime source descriptors for local app diagnostics.
  - Secret-free manifest summary and per-source outcome records for S03 route responses/tests.
  - Contract documentation defining S03 route/UI responsibilities.
requires:
  []
affects:
  - S03
  - S04
key_files:
  - app/diagnostics/assembler.py
  - app/diagnostics/sources.py
  - app/diagnostics/redaction.py
  - app/routes/_helpers.py
  - tests/test_diagnostic_export_assembler.py
  - tests/test_diagnostic_export_sources.py
  - tests/test_diagnostic_export_bundle_integration.py
  - docs/diagnostic-export-contract.md
key_decisions:
  - Diagnostic export backend assembly is dependency-injected and route-free; route semantics stay in S03.
  - Every considered runtime source must appear in the manifest as included, truncated, omitted, or error.
  - Configuration inventory exports labels/counts only, never provider key values.
  - Source failures are isolated as bounded redacted manifest error records; descriptor contract violations fail fast before collection.
patterns_established:
  - Validate all diagnostic source descriptors and archive paths before collecting any source.
  - Redact payloads and error summaries before archive writing, then apply byte bounds.
  - Represent missing optional runtime dependencies as omitted manifest records rather than silently dropping them.
  - Use dependency injection for runtime diagnostic sources so route tests can stay deterministic.
observability_surfaces:
  - Manifest source statuses for included/truncated/omitted/error outcomes.
  - DiagnosticBundle.summary with aggregate counts and archive size.
  - Per-source safe error summaries and redaction metadata.
  - History-save diagnostics snapshot and copied orchestration diagnostics snapshot.
drill_down_paths:
  - .gsd/milestones/M018/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M018/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M018/slices/S02/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-05-12T08:41:17.038Z
blocker_discovered: false
---

# S02: Backend export assembler

**Built and proved the backend-only diagnostic export assembler and runtime source composition contract.**

## What Happened

S02 delivered the backend-only diagnostic export assembly layer. T01 added a deterministic archive assembler that validates source descriptors before collection, writes a stable `manifest.json`, applies source bounds, redacts payloads and source error summaries, records omitted/truncated/error outcomes, and rejects unsafe archive paths. T02 added dependency-injected runtime source composition for safe config inventory, cache stats, recent history summaries, history-save diagnostics, health checks, and optional orchestration snapshots; it also exposed a narrow copied orchestration diagnostics accessor and strengthened bearer-token redaction. T03 added an integration proof that assembles the default runtime sources into a stable secret-free ZIP archive, proves omitted/error behavior for missing or failing runtime dependencies, confirms routes remain absent for this backend-only slice, and updates the diagnostic export contract documentation for the next implementer.

The slice now gives S03 a clear backend service surface: build sources, assemble bundle, inspect summary/manifest, and return bytes from a supported route without inventing backend semantics.

## Verification

Fresh slice/task verification passed after final edits: the diagnostic assembler/source/integration suite passed 20 tests, and the redaction/config/settings regression suite passed 51 tests. The integration suite inspects actual archive bytes and Flask URL rules to prove deterministic backend assembly, redaction, omitted/error records, and continued route absence.

## Requirements Advanced

- R083 — Backend assembly and runtime source proof now exists: deterministic bundle bytes, manifest inventory, bounds, redaction, safe errors, and no route exposure.
- R009 — Redaction tests and integration archive inspection rechecked that configured provider secrets and bearer tokens are absent from exported bytes and manifest summaries.
- R011 — Bounded per-source collection, safe errors, and explicit omitted/error records improve local failure visibility without silent export failures.

## Requirements Validated

None.

## New Requirements Surfaced

- None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

None.

## Deviations

T02 expanded shared redaction primitives to handle standalone bearer-token prose discovered during source composition tests. T03 corrected an initial integration-test expectation: label-only config inventory should not count as a redaction event when secret values are never exported.

## Known Limitations

No Flask route, response headers, browser/UI affordance, or analyst download workflow exists yet; those remain intentionally deferred to S03/S04.

## Follow-ups

S03 must add the supported local app download route, response headers, route-level bounded error handling, and analyst affordance. S03 should replace the route-absence guard with positive route tests that inspect the downloaded archive and headers.

## Files Created/Modified

- `app/diagnostics/assembler.py` — Backend-only deterministic ZIP assembler with manifest, bounds, redaction, safe error records, and path validation.
- `app/diagnostics/sources.py` — Backend runtime diagnostic source descriptors for config inventory, cache stats, history summaries, history-save diagnostics, health checks, and optional orchestration diagnostics.
- `app/diagnostics/__init__.py` — Public backend diagnostics exports.
- `app/diagnostics/redaction.py` — Shared redaction support for configured secrets and bearer-token prose.
- `app/routes/_helpers.py` — Narrow copied orchestration diagnostics accessor plus history-save diagnostics used by runtime sources.
- `tests/test_diagnostic_export_assembler.py` — Assembler unit proof for deterministic output, bounds, redaction, safe errors, and unsafe path rejection.
- `tests/test_diagnostic_export_sources.py` — Runtime source composition proof for injected stores, missing/failing dependencies, redaction, and omitted source records.
- `tests/test_diagnostic_export_bundle_integration.py` — Integration proof that default runtime sources assemble into a deterministic secret-free archive and that export routes remain absent.
- `docs/diagnostic-export-contract.md` — Cold-reader contract doc for backend diagnostic export assembly and S03 route/UI responsibilities.
