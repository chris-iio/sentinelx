---
estimated_steps: 7
estimated_files: 5
skills_used: []
---

# T02: Centralize diagnostics sanitization policy

skills_used: [design-an-interface, verify-before-complete]
Why: The S03 cross-seam audit target is duplicated diagnostics sanitization constants across bundle assembly, runtime source shaping, and redaction. A single policy object reduces drift while preserving the diagnostic export contract.
Do: Ship the refactor if code-path inspection confirms duplicated bounds still exist or the existing implementation needs hardening. Create/maintain `app/diagnostics/policy.py` with an immutable `DiagnosticSanitizationPolicy` and `DIAGNOSTIC_SANITIZATION_POLICY`. Wire assembler archive path and generated filename caps, runtime source byte/string/list/dict/depth caps, and redaction depth/label caps through that policy while preserving existing public helper names where tests or imports rely on them. If the policy is already present and correctly wired, keep production code minimal and document the shipped code-path reasoning in the audit in T03 rather than performing cosmetic churn.
Done when: Diagnostics policy is the single source of truth for the cross-module caps, existing optimized helper names remain stable, and the focused diagnostic lane from T01 passes.
Failure Modes (Q5): Bad diagnostic source input still fails closed; config read errors remain secret-free; unsafe archive/source paths are rejected; circular/deep payloads remain bounded.
Load Profile (Q6): Per diagnostic bundle, sanitization cost stays bounded by policy caps rather than input size; 10x source size should hit truncation/omission before memory pressure.
Negative Tests (Q7): Use T01 regressions for malformed paths, nested/circular payloads, oversized strings/lists/dicts, and secret-bearing errors.

## Inputs

- `tests/test_diagnostic_export_assembler.py`
- `tests/test_diagnostic_redaction.py`
- `tests/test_diagnostic_export_sources.py`
- `app/diagnostics/assembler.py`
- `app/diagnostics/redaction.py`
- `app/diagnostics/sources.py`
- `app/diagnostics/contract.py`
- `app/diagnostics/__init__.py`

## Expected Output

- `app/diagnostics/policy.py`
- `app/diagnostics/assembler.py`
- `app/diagnostics/redaction.py`
- `app/diagnostics/sources.py`
- `app/diagnostics/__init__.py`

## Verification

python3 -m pytest -q tests/test_diagnostic_export_assembler.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_sources.py

## Observability Impact

Keeps the diagnostic bundle manifest/source records and redaction metadata as the inspection surface while moving shared bounds to an immutable policy object.
