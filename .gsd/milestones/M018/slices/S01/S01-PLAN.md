# S01: Contract and redaction primitives

**Goal:** Establish the backend-only diagnostic export contract and prove ConfigStore/provider-secret redaction primitives before any bundle assembler or downloadable route exists.
**Demo:** After this, the project has a precise log-export contract and tested redaction rules before any downloadable bundle is exposed.

## Must-Haves

- R083 is owned at contract level: the diagnostic export has a documented, deterministic manifest/source contract with explicit included/omitted/truncated/error states and byte-bound fields.
- Threat Surface (Q3): malicious diagnostic text can contain secrets, control strings, or oversized payloads; primitives must bound metadata, preserve explicit source outcomes, and redact before any future bundle serialization.
- Requirement Impact (Q4): primary requirement is active R083; supporting continuity/security checks are R009 and R011, while existing JSON/CSV/clipboard export continuity in R008 is preserved by not touching current frontend export code in S01.
- Redaction primitives collect configured VirusTotal and generic provider keys from `ConfigStore`, redact exact secrets and common auth/header/query patterns from strings and nested JSON-like data, and do not expose raw keys in serialized output.
- D077 is the structural decision for this slice: diagnostic primitives live under backend-only `app/diagnostics/` and no app route, UI download button, zip creation, or runtime bundle assembly is introduced until later slices.
- Focused pytest commands pass for the new contract/redaction tests plus existing ConfigStore/settings secret-display regressions.

## Proof Level

- This slice proves: Contract proof. Real runtime required: no. Human/UAT required: no. Verification must exercise boundary contracts with unit tests, including malicious/oversized/malformed source records and explicit secret-absence assertions.

## Integration Closure

Upstream surfaces consumed: `app/enrichment/config_store.py`, existing orchestrator/helper diagnostics contracts in `app/enrichment/orchestrator.py` and `app/routes/_helpers.py`, and existing settings secret masking tests. New wiring introduced: backend-only `app/diagnostics/` primitives and developer contract documentation; no Flask route or bundle assembler. Remaining milestone work: S02 assembles deterministic bundles from runtime/fixture sources, S03 exposes the supported local app path, and S04 proves end-to-end download plus analyst guidance.

## Verification

- The slice adds no long-running runtime path. It creates future diagnostic observability vocabulary: manifest source statuses, byte limits, truncation flags, safe error summaries, and redaction counts/labels that S02 can surface without leaking secret values.

## Tasks

- [x] **T01: Define the diagnostic export contract and manifest schema** `est:2h`
  Expected executor `skills_used`: `api-design`, `tdd`, `write-docs`.
  - Files: `app/diagnostics/__init__.py`, `app/diagnostics/contract.py`, `docs/diagnostic-export-contract.md`, `tests/test_diagnostic_export_contract.py`
  - Verify: python3 -m pytest -q tests/test_diagnostic_export_contract.py

- [ ] **T02: Implement ConfigStore-backed redaction primitives** `est:2h`
  Expected executor `skills_used`: `tdd`, `security-review`, `verify-before-complete`.
  - Files: `app/diagnostics/__init__.py`, `app/diagnostics/redaction.py`, `tests/test_diagnostic_redaction.py`
  - Verify: python3 -m pytest -q tests/test_diagnostic_redaction.py tests/test_config_store.py tests/test_settings.py

- [ ] **T03: Prove contract and redaction compose without exposing a bundle route** `est:1h`
  Expected executor `skills_used`: `tdd`, `verify-before-complete`.
  - Files: `tests/test_diagnostic_export_primitives.py`, `docs/diagnostic-export-contract.md`
  - Verify: python3 -m pytest -q tests/test_diagnostic_export_contract.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_primitives.py

## Files Likely Touched

- app/diagnostics/__init__.py
- app/diagnostics/contract.py
- docs/diagnostic-export-contract.md
- tests/test_diagnostic_export_contract.py
- app/diagnostics/redaction.py
- tests/test_diagnostic_redaction.py
- tests/test_diagnostic_export_primitives.py
