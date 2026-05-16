---
estimated_steps: 7
estimated_files: 3
skills_used: []
---

# T01: Lock diagnostics policy boundary regressions

skills_used: [tdd, verify-before-complete]
Why: S03 is cross-seam and touches diagnostics export/redaction boundaries; tests must lock the public failure-visibility and secret-redaction contract before production changes or rejection reasoning.
Do: Add or tighten focused pytest coverage proving that diagnostics archive assembly, default/runtime diagnostic sources, and redaction all honor the intended shared caps. Cover negative cases: forbidden archive paths including `.gsd`, `.planning`, `.audits`, and `.git`; generated filename bounds; source collection errors or oversized payload truncation; configured secret read errors reported as secret-free metadata; exact-secret longest-first redaction and label length bounds. Do not make tests read gitignored paths; tests should use in-memory/temp fixtures only.
Done when: The focused diagnostics pytest lane passes and fails if assembler/source/redaction caps drift independently or if diagnostic failure states or redaction guardrails are weakened.
Failure Modes (Q5): ConfigStore failures must become secret-free redaction metadata rather than leaked exceptions; source collection errors must remain manifest source records rather than hidden failures; malformed source paths must be rejected before collection.
Load Profile (Q6): Diagnostics payload sanitization should remain bounded by max bytes, max string/list/dict items, and max depth; 10x diagnostic payload size should truncate/omit rather than allocate unbounded output.
Negative Tests (Q7): malformed archive paths, oversized runtime payloads, nested payloads beyond max depth, secret-containing error text, and duplicate/unsafe filenames.

## Inputs

- `app/diagnostics/assembler.py`
- `app/diagnostics/redaction.py`
- `app/diagnostics/sources.py`
- `app/diagnostics/policy.py`
- `tests/test_diagnostic_export_assembler.py`
- `tests/test_diagnostic_redaction.py`
- `tests/test_diagnostic_export_sources.py`

## Expected Output

- `tests/test_diagnostic_export_assembler.py`
- `tests/test_diagnostic_redaction.py`
- `tests/test_diagnostic_export_sources.py`

## Verification

python3 -m pytest -q tests/test_diagnostic_export_assembler.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_sources.py

## Observability Impact

Adds/maintains focused failure-path assertions that diagnostic source errors, truncation, redaction metadata, and archive validation remain visible without leaking secrets.
