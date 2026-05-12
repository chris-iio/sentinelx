---
id: T01
parent: S02
milestone: M018
key_files:
  - app/diagnostics/assembler.py
  - app/diagnostics/__init__.py
  - tests/test_diagnostic_export_assembler.py
key_decisions:
  - Descriptor and path validation happens before any source callable is evaluated, so malformed/duplicate descriptors fail fast without trusting partial bundle bytes.
  - ZIP entries use `ZIP_STORED`, fixed DOS timestamp metadata, manifest-first ordering, and sorted payload paths to make archive bytes deterministic.
  - Source payloads are redacted before serialization/encoding and source exception messages are redacted before being stored in manifest `safe_error_summary` fields.
duration: 
verification_result: passed
completed_at: 2026-05-12T06:07:45.805Z
blocker_discovered: false
---

# T01: Added a backend-only deterministic diagnostic bundle assembler with redaction, path safety, bounded payloads, and manifest outcome records.

**Added a backend-only deterministic diagnostic bundle assembler with redaction, path safety, bounded payloads, and manifest outcome records.**

## What Happened

Created `app/diagnostics/assembler.py` with `DiagnosticSource`, `DiagnosticBundle`, and `assemble_diagnostic_bundle(...)`. The assembler validates descriptors, duplicate source IDs, duplicate archive paths, and unsafe archive paths before invoking source callables; processes sources in stable source-id order; redacts text/payload content before encoding; truncates included bytes to each source bound; captures intentional omissions; converts source exceptions into bounded redacted manifest error records; and writes a deterministic ZIP archive with `manifest.json` plus stable payload entries. Updated `app/diagnostics/__init__.py` to export the backend assembler API. Added focused assembler tests covering deterministic two-run archive equality, redaction-before-write, mixed outcomes, source exceptions with secrets, duplicate validation fail-fast behavior, unsafe path rejection, oversized truncation, and safe unserializable object representation.

## Verification

Ran the required focused verification command `python3 -m pytest -q tests/test_diagnostic_export_assembler.py`, which passed with 14 tests. Also ran the diagnostic export regression set (`contract`, `primitives`, and `assembler`) to confirm existing S01 manifest/redaction behavior and package exports still pass, with 27 tests passing.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -q tests/test_diagnostic_export_assembler.py` | 0 | ✅ pass — 14 tests passed | 654ms |
| 2 | `python3 -m pytest -q tests/test_diagnostic_export_contract.py tests/test_diagnostic_export_primitives.py tests/test_diagnostic_export_assembler.py` | 0 | ✅ pass — 27 tests passed | 530ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `app/diagnostics/assembler.py`
- `app/diagnostics/__init__.py`
- `tests/test_diagnostic_export_assembler.py`
