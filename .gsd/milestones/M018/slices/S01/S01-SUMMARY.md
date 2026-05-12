---
id: S01
parent: M018
milestone: M018
provides:
  - S02 can build a deterministic bundle assembler on a tested manifest/source-record contract.
  - S02/S03 can use redaction primitives before serializing any diagnostic source content.
  - S03 has explicit route non-goal tests to replace with positive route/header tests when the supported download path is added.
  - S04 has documented analyst-facing contract vocabulary for explaining included, omitted, truncated, and errored sources.
requires:
  []
affects:
  - S02
  - S03
  - S04
key_files:
  - app/diagnostics/__init__.py
  - app/diagnostics/contract.py
  - app/diagnostics/redaction.py
  - docs/diagnostic-export-contract.md
  - tests/test_diagnostic_export_contract.py
  - tests/test_diagnostic_redaction.py
  - tests/test_diagnostic_export_primitives.py
key_decisions:
  - Diagnostic export primitives remain backend-only under `app/diagnostics/` for S01, with no Flask route, UI control, filesystem traversal, zip creation, or runtime bundle assembly.
  - Every considered diagnostic source must serialize an explicit outcome (`included`, `omitted`, `truncated`, or `error`) so future manifests do not silently drop sources.
  - Manifest serialization is deterministic by source id and uses caller-supplied timestamps rather than wall-clock dependencies.
  - Public redaction inventory/manifest metadata may expose labels and counts, but raw configured provider keys stay private to in-process exact-match candidates.
  - Exact configured-secret redaction runs before broader case-insensitive header/query/token patterns.
  - S01 guards likely future routes (`/diagnostics/export`, `/api/diagnostics/export`) as absent until S03 intentionally adds supported route coverage.
patterns_established:
  - Frozen backend contract dataclasses with validation and JSON-safe serialization for diagnostic manifest data.
  - Explicit source-status vocabulary for included, omitted, truncated, and error outcomes.
  - Safe error summaries bounded to a fixed length before serialization.
  - ConfigStore-backed exact-secret redaction plus fallback pattern redaction for common auth/header/query/JSON secret forms.
  - Non-mutating nested diagnostic payload traversal with cycle, depth, and unserializable-object guards.
  - Route-absence guard tests to preserve backend-only scope until a later slice exposes the supported app path.
observability_surfaces:
  - Diagnostic manifest schema version and deterministic source ordering.
  - Per-source status, category, byte bounds, truncation flags, safe error summaries, and omitted reasons.
  - Aggregate manifest counts for included/omitted/truncated/error source outcomes.
  - Redaction counts and safe redaction labels without raw secret values.
drill_down_paths:
  - .gsd/milestones/M018/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M018/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M018/slices/S01/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-05-12T05:38:30.251Z
blocker_discovered: false
---

# S01: Contract and redaction primitives

**Established the backend-only diagnostic export manifest contract and ConfigStore-backed redaction primitives, with tests proving deterministic outcomes, bounded metadata, secret absence, and no premature export route.**

## What Happened

S01 delivered the contract-level foundation for M018 without exposing a downloadable bundle or app route. T01 added `app/diagnostics/contract.py` and documentation for a deterministic diagnostic export manifest: schema versioning, explicit per-source outcomes (`included`, `omitted`, `truncated`, `error`), byte-bound fields, bounded safe error summaries, duplicate source-id rejection, caller-supplied timestamps, and deterministic serialization by source id. T02 added `app/diagnostics/redaction.py` with backend-only ConfigStore-backed secret collection and safe public inventory metadata; exact configured secrets are redacted before broader Authorization/API-key/query/token/secret patterns, and nested JSON-like payload traversal copies caller data while guarding cycles, depth, and unserializable values. T03 proved the two primitives compose by redacting representative diagnostic payloads before manifest serialization, preserving useful non-secret context, recording redaction labels/counts, bounding oversized content, and asserting likely future export paths are still absent until S03 intentionally adds positive route coverage.

Gate closure: Q3 threat surface is addressed at primitive level by bounding source metadata/error strings and proving redaction before serialization for malicious strings, common credential patterns, nested payloads, and oversized content. Q4 requirement impact is constrained: R083 is advanced at contract/redaction level, R009/R011 security and test-continuity posture are preserved, and existing JSON/CSV/clipboard export code for R008 was not touched. Q8 operational readiness is intentionally primitive-focused: health signal is deterministic manifest serialization plus redaction counts/labels; failure signal is explicit per-source `error` status with safe bounded summaries; recovery procedure is to inspect the manifest outcome and rerun/replace only the failing source collector in later assembler work; monitoring gaps remain because no runtime bundle assembler, Flask route, UI affordance, or production telemetry exists in S01.

## Verification

Fresh closeout verification used `gsd_exec` only. `python3 -m pytest -q tests/test_diagnostic_export_contract.py` passed with 11 tests in 0.03s (exit 0). `python3 -m pytest -q tests/test_diagnostic_redaction.py tests/test_config_store.py tests/test_settings.py` passed with 51 tests in 0.53s (exit 0). `python3 -m pytest -q tests/test_diagnostic_export_contract.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_primitives.py` passed with 21 tests in 0.19s (exit 0). Closeout reviewer and security subagents reported no blocking issues; the security review confirmed the diagnostic suite still passed and no closeout-blocking leakage risk was surfaced.

## Requirements Advanced

- R083 — Established and tested the contract-level manifest/source vocabulary, bounds metadata, redaction metadata, and ConfigStore-backed secret redaction primitives required before assembling or exposing a diagnostic bundle.
- R009 — Preserved security posture by redacting configured provider secrets and common auth patterns before serialization and by keeping the export surface backend-only in S01.
- R011 — Added focused contract/redaction/composition tests and reran existing ConfigStore/settings secret-display regressions successfully.

## Requirements Validated

- R083 — Contract-level proof only: focused tests show deterministic manifest serialization, explicit source outcomes, byte bounds, safe errors, and absence of configured/runtime secrets from serialized primitive output. Full diagnostic export capability remains active for later S02-S04 validation.

## New Requirements Surfaced

- None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

None.

## Deviations

None.

## Known Limitations

S01 intentionally does not introduce a bundle assembler, public Flask route, UI download button, zip/tar creation, runtime source collection, or end-to-end browser proof. Those are deferred to S02-S04.

## Follow-ups

S02 should consume `app/diagnostics/contract.py` and `app/diagnostics/redaction.py` to assemble deterministic diagnostic bundles from fixture/runtime sources with safe per-source errors. S03 should replace the route-absence guard with positive route/download tests. S04 should add end-to-end download inspection and analyst guidance.

## Files Created/Modified

- `app/diagnostics/__init__.py` — Introduces and exports backend-only diagnostic primitives.
- `app/diagnostics/contract.py` — Defines validated manifest/source-record contract and deterministic serialization helpers.
- `app/diagnostics/redaction.py` — Implements ConfigStore-backed and pattern-based redaction for strings and nested JSON-like diagnostic data.
- `docs/diagnostic-export-contract.md` — Documents the S01 contract, source statuses, bounds, redaction expectations, non-goals, and downstream slice guidance.
- `tests/test_diagnostic_export_contract.py` — Covers manifest/schema/status/bounds/error/determinism behavior.
- `tests/test_diagnostic_redaction.py` — Covers ConfigStore-backed secret collection/redaction and nested/pattern fallback behavior.
- `tests/test_diagnostic_export_primitives.py` — Proves redaction composes with manifest serialization and no export routes are exposed in S01.
