---
id: T01
parent: S01
milestone: M018
key_files:
  - app/diagnostics/__init__.py
  - app/diagnostics/contract.py
  - docs/diagnostic-export-contract.md
  - tests/test_diagnostic_export_contract.py
key_decisions:
  - Keep diagnostic export contract backend-only and independent of Flask route handlers, filesystem traversal, zip assembly, and gitignored planning/runtime paths.
  - Represent every considered source as included, omitted, truncated, or error so manifests do not silently drop outcomes.
  - Use deterministic source_id ordering and caller-supplied timestamps so serialization is stable and free of wall-clock dependencies.
  - Bound safe error summaries to 120 characters and expose redaction counts/labels without secret values.
duration: 
verification_result: mixed
completed_at: 2026-05-12T05:25:28.624Z
blocker_discovered: false
---

# T01: Added a backend-only diagnostic export manifest contract with deterministic serialization, explicit source outcomes, bounds metadata, documentation, and focused tests.

**Added a backend-only diagnostic export manifest contract with deterministic serialization, explicit source outcomes, bounds metadata, documentation, and focused tests.**

## What Happened

Created the new app.diagnostics package and implemented app.diagnostics.contract as a pure backend contract with frozen dataclasses for DiagnosticSourceRecord and DiagnosticManifest. The contract pins schema version diagnostic-export-manifest/v1, validates explicit statuses included/omitted/truncated/error, validates allowed categories, records byte bounds and redaction metadata, bounds safe error summaries, rejects ambiguous malformed descriptors, sorts manifest sources deterministically by source_id, and provides JSON-safe serialization helpers that do not read clocks or route/runtime state. Added docs/diagnostic-export-contract.md for future S02 implementers covering source classes, manifest statuses, default bounds, redaction-before-export, safe errors, deterministic serialization, and S01 non-goals. Added tests/test_diagnostic_export_contract.py to pin schema version, safe defaults, invalid status/category handling, empty source identifiers, truncation semantics, omitted/error representations, bounded summaries, deterministic serialization, aggregate counts, empty manifests, and duplicate source-id rejection.

## Verification

Ran the required focused pytest command successfully after implementation and style-only wrapping. Also ran a manual line-length check for touched Python files because ruff is not installed in this environment; all touched Python files are within the configured 100-column limit. An attempted ruff check failed because the ruff module is unavailable, not because of code findings.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -q tests/test_diagnostic_export_contract.py` | 0 | ✅ pass | 548ms |
| 2 | `python3 - <<'PY'
from pathlib import Path
for path in [Path('app/diagnostics/__init__.py'), Path('app/diagnostics/contract.py'), Path('tests/test_diagnostic_export_contract.py')]:
    long = [
        (i, len(line.rstrip('\n')))
        for i, line in enumerate(path.read_text().splitlines(True), 1)
        if len(line.rstrip('\n')) > 100
    ]
    print(path)
    print(long[:20] if long else 'ok')
PY` | 0 | ✅ pass | 20ms |
| 3 | `python3 -m ruff check app/diagnostics tests/test_diagnostic_export_contract.py` | 1 | ⚠️ tool unavailable (No module named ruff) | 12ms |

## Deviations

None.

## Known Issues

python3 -m ruff check could not run because ruff is not installed in this environment. The required pytest verification passed.

## Files Created/Modified

- `app/diagnostics/__init__.py`
- `app/diagnostics/contract.py`
- `docs/diagnostic-export-contract.md`
- `tests/test_diagnostic_export_contract.py`
