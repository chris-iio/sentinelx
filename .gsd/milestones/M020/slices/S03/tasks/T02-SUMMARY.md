---
id: T02
parent: S03
milestone: M020
key_files:
  - app/diagnostics/policy.py
  - app/diagnostics/assembler.py
  - app/diagnostics/redaction.py
  - app/diagnostics/sources.py
  - app/diagnostics/__init__.py
  - tests/test_diagnostic_export_assembler.py
  - tests/test_diagnostic_redaction.py
  - tests/test_diagnostic_export_sources.py
key_decisions:
  - Kept production code unchanged after inspection proved diagnostics sanitization policy centralization was already complete and verified by focused regression tests.
duration: 
verification_result: passed
completed_at: 2026-05-16T08:49:44.113Z
blocker_discovered: false
---

# T02: Confirmed diagnostics sanitization caps are centralized through the shared immutable policy object without requiring cosmetic production churn.

**Confirmed diagnostics sanitization caps are centralized through the shared immutable policy object without requiring cosmetic production churn.**

## What Happened

Inspected the diagnostics policy, archive assembler, redaction, runtime source composition, package exports, and T01 regression tests. The existing implementation already provides app/diagnostics/policy.py with frozen-slot DiagnosticSanitizationPolicy and DIAGNOSTIC_SANITIZATION_POLICY, exports both from app/diagnostics/__init__.py, and wires assembler archive path/generated filename caps, runtime source byte/string/list/dict/depth caps, and redaction depth/label caps through policy-derived constants. Because the code-path inspection and focused tests showed the intended cross-seam refactor was already shipped, I preserved production code as-is rather than making cosmetic churn.

## Verification

Ran a code-path scan of the diagnostics policy wiring and the required focused diagnostic lane. The scan showed literal policy defaults isolated in policy.py with downstream modules using DIAGNOSTIC_SANITIZATION_POLICY-derived aliases/fields, and pytest passed 74 diagnostic export/redaction/source tests covering malformed paths, nested/circular payloads, oversized strings/lists/dicts, source truncation, omitted/error manifest states, config read failures, and secret redaction behavior.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 - <<'PY'
from pathlib import Path
for path in ['app/diagnostics/policy.py','app/diagnostics/assembler.py','app/diagnostics/redaction.py','app/diagnostics/sources.py','app/diagnostics/__init__.py']:
    text=Path(path).read_text()
    print(f'## {path}')
    for i,line in enumerate(text.splitlines(),1):
        if any(tok in line for tok in ['MAX_', 'max_', '16 * 1024', '= 240', '= 25', '= 50', '= 5', '= 120', '= 20', '= 64', 'DIAGNOSTIC_SANITIZATION_POLICY']):
            print(f'{i}: {line.strip()}')
PY` | 0 | ✅ pass | 20ms |
| 2 | `python3 -m pytest -q tests/test_diagnostic_export_assembler.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_sources.py` | 0 | ✅ pass | 544ms |

## Deviations

No production files were edited because the requested policy object and cross-module wiring were already present and covered by T01 regressions; this follows the task instruction to avoid cosmetic churn when the implementation is already correct.

## Known Issues

None.

## Files Created/Modified

- `app/diagnostics/policy.py`
- `app/diagnostics/assembler.py`
- `app/diagnostics/redaction.py`
- `app/diagnostics/sources.py`
- `app/diagnostics/__init__.py`
- `tests/test_diagnostic_export_assembler.py`
- `tests/test_diagnostic_redaction.py`
- `tests/test_diagnostic_export_sources.py`
