# S04: End-to-end proof and documentation

**Goal:** Prove the full route-to-archive pipeline is internally consistent via a deterministic download proof, and provide analyst-facing documentation for safe bundle generation and sharing — closing M018.
**Demo:** After this, a deterministic app-level proof downloads and inspects the log bundle, and docs describe safe sharing and limits.

## Must-Haves

- `tests/test_diagnostic_export_e2e_proof.py` passes with ≥3 test functions: manifest-archive entry consistency, raw-byte secret absence, and download response headers
- Every `included` manifest source has a matching archive entry at its `relative_path`; every archive entry except `manifest.json` has a manifest record and is valid JSON
- No configured secret values appear in the raw ZIP response bytes
- `docs/diagnostic-export-guide.md` exists with ≥5 sections covering generation, contents, redaction, safe sharing, and troubleshooting
- Full diagnostic test suite from all four slices passes together without regression

## Proof Level

- This slice proves: final-assembly

## Integration Closure

S04 verifies the full pipeline from Flask route through assembler to ZIP archive contents. No new wiring is introduced — this slice exercises the production path built in S01–S03. After S04, M018 is ready for milestone validation.

## Verification

- No new runtime signals added — S04 is verification and documentation only. Existing signals remain: X-Diagnostic-Sources response header, manifest.json per-source inventory, ERROR-level server logs on assembly failure.

## Tasks

- [x] **T01: Write deterministic app-level download proof verifying full archive consistency** `est:45m`
  Write `tests/test_diagnostic_export_e2e_proof.py` — a focused proof file that downloads the diagnostic ZIP via the Flask test client and verifies the archive is internally consistent at the final-assembly level.
  - Files: `tests/test_diagnostic_export_e2e_proof.py`
  - Verify: python3 -m pytest tests/test_diagnostic_export_e2e_proof.py -v && echo 'PROOF PASS'

- [ ] **T02: Write analyst guide for safe diagnostic bundle generation and sharing** `est:30m`
  Create `docs/diagnostic-export-guide.md` — an analyst-facing guide (distinct from the developer contract in `docs/diagnostic-export-contract.md`) covering how to use the diagnostic export feature safely.
  - Files: `docs/diagnostic-export-guide.md`
  - Verify: test -f docs/diagnostic-export-guide.md && python3 -c "import re, sys; text=open('docs/diagnostic-export-guide.md').read(); sections=re.findall(r'^## ', text, re.MULTILINE); sys.exit(0 if len(sections) >= 5 else 1)" && echo 'GUIDE PASS'

## Files Likely Touched

- tests/test_diagnostic_export_e2e_proof.py
- docs/diagnostic-export-guide.md
