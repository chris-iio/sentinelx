---
estimated_steps: 7
estimated_files: 1
skills_used: []
---

# T01: Write deterministic app-level download proof verifying full archive consistency

Write `tests/test_diagnostic_export_e2e_proof.py` — a focused proof file that downloads the diagnostic ZIP via the Flask test client and verifies the archive is internally consistent at the final-assembly level.

The proof must demonstrate three things:
1. **Manifest-archive consistency**: every `included` source in `manifest.json` has a matching archive entry at its `relative_path`; every archive entry other than `manifest.json` maps to a manifest source record; all `runtime/*.json` entries parse as valid JSON; manifest aggregate counts (`source_count`, `included_count`) match reality.
2. **Raw-byte secret absence**: no configured secret values appear anywhere in the raw ZIP response bytes (use the same secret-injection fixture pattern as `tests/test_diagnostic_export_route.py`).
3. **Download headers for analyst use**: Content-Type is `application/zip`, Content-Disposition is `attachment; filename="sentinelx-diagnostic-YYYY-MM-DD.zip"` (regex-match the date pattern), X-Diagnostic-Sources is an integer string matching `manifest["source_count"]`.

Read `tests/conftest.py` first to locate the `client` fixture and understand how the app is initialised for tests. Read `tests/test_diagnostic_export_route.py` for the exact pattern used to inject test API key values into the environment so secrets can be asserted absent from the bytes.

Keep the test file focused: 3 test functions is the target. Do not duplicate assertions already in `tests/test_diagnostic_export_route.py` — add only what is genuinely new (internal consistency, full JSON parseability of entries).

## Inputs

- `tests/conftest.py`
- `app/routes/diagnostics.py`
- `app/diagnostics/contract.py`
- `tests/test_diagnostic_export_route.py`

## Expected Output

- `tests/test_diagnostic_export_e2e_proof.py`

## Verification

python3 -m pytest tests/test_diagnostic_export_e2e_proof.py -v && echo 'PROOF PASS'
