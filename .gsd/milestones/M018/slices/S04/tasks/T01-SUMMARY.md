---
id: T01
parent: S04
milestone: M018
key_files:
  - tests/test_diagnostic_export_e2e_proof.py
key_decisions:
  - Kept the proof at the route level using the Flask test client and deterministic monkeypatching instead of mocking bundle assembly, so it validates final archive behavior through the intended supported surface.
duration: 
verification_result: passed
completed_at: 2026-05-12T12:01:02.835Z
blocker_discovered: false
---

# T01: Added an app-level Flask client proof that downloads the diagnostic ZIP and validates manifest/archive consistency, raw-byte secret redaction, and analyst download headers.

**Added an app-level Flask client proof that downloads the diagnostic ZIP and validates manifest/archive consistency, raw-byte secret redaction, and analyst download headers.**

## What Happened

Created `tests/test_diagnostic_export_e2e_proof.py` with three focused tests. The module patches the diagnostic export route with a deterministic clock and secret-bearing runtime stores, downloads the real `/diagnostics/export` response through the Flask test client, inspects the ZIP archive, validates manifest source/path/count consistency, parses all `runtime/*.json` entries, asserts configured secret bytes are absent from the raw ZIP payload, and checks analyst-facing response headers against the manifest.

## Verification

Ran the required focused pytest command: `python3 -m pytest tests/test_diagnostic_export_e2e_proof.py -v && echo 'PROOF PASS'`. All three proof tests passed and emitted `PROOF PASS`.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/test_diagnostic_export_e2e_proof.py -v && echo 'PROOF PASS'` | 0 | ✅ pass — 3 passed; PROOF PASS emitted | 856ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `tests/test_diagnostic_export_e2e_proof.py`
