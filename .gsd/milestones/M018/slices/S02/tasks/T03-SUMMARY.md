---
id: T03
parent: S02
milestone: M018
key_files:
  - tests/test_diagnostic_export_bundle_integration.py
  - docs/diagnostic-export-contract.md
key_decisions:
  - Treat the assembled ZIP archive and manifest as the public backend inspection surface for S02.
  - Keep configuration secret inventory label-only; absence of secret values does not necessarily imply a redaction event if values were never exported.
  - Preserve the diagnostic export route absence proof until S03 adds route-level safety tests.
duration: 
verification_result: mixed
completed_at: 2026-05-12T08:39:58.563Z
blocker_discovered: false
---

# T03: Added backend diagnostic bundle integration proof and updated the contract doc for S02/S03 boundaries.

**Added backend diagnostic bundle integration proof and updated the contract doc for S02/S03 boundaries.**

## What Happened

Created `tests/test_diagnostic_export_bundle_integration.py` to prove the public backend diagnostics API can compose default runtime sources into a deterministic ZIP archive with stable paths, a complete manifest, per-source byte bounds, redacted cache/orchestration bearer-token payloads, label-only config secret inventory, and no leaked provider secret values. The integration proof also covers missing/failing runtime dependencies becoming explicit `omitted` or `error` manifest records without aborting unrelated sources, and keeps the `/diagnostics/export` plus `/api/diagnostics/export` route boundary closed for the backend-only slice.

Updated `docs/diagnostic-export-contract.md` for a cold reader implementing S03: it now distinguishes S01 primitive proof, S02 backend archive/runtime composition proof, redaction-before-export ordering, deterministic archive behavior, safe error summaries, runtime source inventory, and the route/UI responsibilities that remain out of scope until the next slice.

## Verification

Fresh T03 verification passed after the final code/doc edits: `python3 -m pytest -q tests/test_diagnostic_export_assembler.py tests/test_diagnostic_export_sources.py tests/test_diagnostic_export_bundle_integration.py` passed 20 tests, then `python3 -m pytest -q tests/test_diagnostic_redaction.py tests/test_config_store.py tests/test_settings.py` passed 51 tests.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -q tests/test_diagnostic_export_bundle_integration.py` | 1 | ❌ fail — initial assertion expected too many redaction events | 6800ms |
| 2 | `python3 -m pytest -q tests/test_diagnostic_export_bundle_integration.py` | 0 | ✅ pass — 3 passed | 7300ms |
| 3 | `python3 -m pytest -q tests/test_diagnostic_export_assembler.py tests/test_diagnostic_export_sources.py tests/test_diagnostic_export_bundle_integration.py && python3 -m pytest -q tests/test_diagnostic_redaction.py tests/test_config_store.py tests/test_settings.py` | 0 | ✅ pass — 20 passed, then 51 passed | 7600ms |

## Deviations

The first integration test run exposed an incorrect assertion that config inventory should count as a redaction event. I corrected the test because config inventory is label-only and never exports the secret value; only exported bearer-token payloads should contribute redaction events in that scenario.

## Known Issues

None.

## Files Created/Modified

- `tests/test_diagnostic_export_bundle_integration.py`
- `docs/diagnostic-export-contract.md`
