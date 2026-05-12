---
id: T03
parent: S01
milestone: M018
key_files:
  - tests/test_diagnostic_export_primitives.py
  - docs/diagnostic-export-contract.md
key_decisions:
  - Keep S01 as a primitive-composition proof only: redaction runs before manifest serialization, but no bundle assembler or public export route is introduced.
  - Guard both likely future export paths, `/diagnostics/export` and `/api/diagnostics/export`, so later S03 route work must replace this with explicit positive route coverage.
duration: 
verification_result: passed
completed_at: 2026-05-12T05:32:42.110Z
blocker_discovered: false
---

# T03: Added a primitive-composition proof that redacts diagnostic payloads before manifest serialization and guards against premature export routes.

**Added a primitive-composition proof that redacts diagnostic payloads before manifest serialization and guards against premature export routes.**

## What Happened

Created `tests/test_diagnostic_export_primitives.py` with integration-style unit coverage that uses real `ConfigStore` APIs against a temporary config file, builds representative in-memory diagnostic source payloads, redacts configured VT/provider secrets plus common auth-pattern values, then wraps the sanitized results in the backend-only manifest/source-record contract. The test asserts deterministic manifest serialization, visible included/truncated/omitted/error outcomes, truncation at a byte bound for oversized log text, redaction labels/counts, preservation of useful non-secret debugging context, and absence of raw configured or runtime secrets from the serialized bundle-shaped document. Added a route absence guard for `/diagnostics/export` and `/api/diagnostics/export` so S01 cannot accidentally ship a public export surface before later bundle/route slices. Updated `docs/diagnostic-export-contract.md` with an S01 primitive-composition proof note and clarified that S03 should remove or replace the guard with positive route tests.

## Verification

`python3 -m pytest -q tests/test_diagnostic_export_contract.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_primitives.py` passed after the final documentation change: 21 tests passed in 0.18s.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -q tests/test_diagnostic_export_contract.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_primitives.py` | 0 | ✅ pass — 21 passed in 0.18s | 528ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `tests/test_diagnostic_export_primitives.py`
- `docs/diagnostic-export-contract.md`
