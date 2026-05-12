# S02: Backend export assembler

**Goal:** Build the backend-only diagnostic export assembler that consumes S01 manifest/redaction primitives, advances owning requirement R083 at backend integration level, preserves supporting R009/R011, produces a deterministic bounded diagnostic bundle from fixture and local runtime sources, records included/omitted/truncated/error outcomes for every considered source, and exposes enough safe metadata for S03 to add an app download route without inventing bundle semantics.
**Demo:** After this, a backend service can assemble a deterministic diagnostic bundle from fixture/runtime sources with manifest, bounds, and safe per-source errors.

## Must-Haves

- A backend-only assembler exists under `app/diagnostics/` and can produce deterministic bundle bytes plus a manifest with `manifest.json` and stable per-source payload paths.
- Source content is redacted before packaging, bounded before inclusion, and represented in the manifest as `included`, `truncated`, `omitted`, or `error`; source failures never abort the whole bundle unless the caller violates the assembler contract.
- Runtime composition can gather safe local app diagnostics from config inventory, cache stats, history summaries, health/dependency checks, and optionally orchestrator/history-save diagnostics without exposing provider secrets or adding any Flask route.
- Focused tests prove deterministic archive output, byte bounds, redaction, safe errors, path/traversal rejection, runtime source composition, and continued absence of `/diagnostics/export` and `/api/diagnostics/export` routes until S03.
- Requirement coverage is explicit: R083 is owned by this slice at backend-assembly proof level; R009/R011 are rechecked through redaction/security and focused regression tests.

## Proof Level

- This slice proves: Integration-level backend proof. Real browser/UAT is not required. Runtime proof should use test-isolated ConfigStore/CacheStore/HistoryStore/application objects and callable source fixtures, not `.gsd/`, `.planning/`, `.audits/`, external provider APIs, or user home secrets.

## Integration Closure

Consumes S01 `app/diagnostics/contract.py` and `app/diagnostics/redaction.py`; composes existing safe runtime surfaces from `app/health_contract.py`, `app/cache/store.py`, `app/enrichment/history_store.py`, `app/enrichment/config_store.py`, `app/enrichment/orchestrator.py`, and `app/routes/_helpers.py` diagnostics accessors. Introduces backend assembly/wiring only; S03 still must add the supported app route, response headers, route-level errors, and analyst affordance. S04 still must run app-level download inspection and documentation.

## Verification

- S02 makes the diagnostic bundle itself the inspection surface: deterministic `manifest.json`, per-source statuses, byte counts, truncation flags, omitted reasons, safe error summaries, redaction counts/labels, and a backend assembly summary/result object. Failure visibility is explicit per-source `error` records with bounded redacted summaries. No public route, UI state, telemetry, or long-term log retention is introduced.

## Tasks

- [x] **T01: Implement deterministic bounded bundle assembly** `est:1h 30m`
  Expected executor `skills_used`: `api-design`, `tdd`, `security-review`.
  - Files: `app/diagnostics/assembler.py`, `app/diagnostics/__init__.py`, `tests/test_diagnostic_export_assembler.py`
  - Verify: python3 -m pytest -q tests/test_diagnostic_export_assembler.py

- [x] **T02: Compose safe runtime diagnostic sources** `est:1h 30m`
  Expected executor `skills_used`: `api-design`, `tdd`, `observability`.
  - Files: `app/diagnostics/sources.py`, `app/diagnostics/__init__.py`, `app/routes/_helpers.py`, `tests/test_diagnostic_export_sources.py`
  - Verify: python3 -m pytest -q tests/test_diagnostic_export_sources.py

- [x] **T03: Prove assembled runtime bundle integration and route boundary** `est:1h`
  Expected executor `skills_used`: `tdd`, `verify-before-complete`, `security-review`, `write-docs`.
  - Files: `tests/test_diagnostic_export_bundle_integration.py`, `docs/diagnostic-export-contract.md`
  - Verify: python3 -m pytest -q tests/test_diagnostic_export_assembler.py tests/test_diagnostic_export_sources.py tests/test_diagnostic_export_bundle_integration.py && python3 -m pytest -q tests/test_diagnostic_redaction.py tests/test_config_store.py tests/test_settings.py

## Files Likely Touched

- app/diagnostics/assembler.py
- app/diagnostics/__init__.py
- tests/test_diagnostic_export_assembler.py
- app/diagnostics/sources.py
- app/routes/_helpers.py
- tests/test_diagnostic_export_sources.py
- tests/test_diagnostic_export_bundle_integration.py
- docs/diagnostic-export-contract.md
