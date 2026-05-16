---
estimated_steps: 1
estimated_files: 1
skills_used: []
---

# T01: Add M020 audit contract tests

Why: S01 is only useful if the M020 audit shape is locked before the runner is changed; tests must prove generated output rather than hand-edited prose. Do: extend `tests/test_optimization_audit.py` with temp-path tests for `--milestone-id M020 --mode template` and `--mode baseline`. Assert the M020 artifact title, decisions D081-D083, requirements R094/R095/R099/R100, `docs/project-map.md` grounding, all four buckets, aggressive rewrite candidate seams, proof requirements, rerun lanes, and no unresolved placeholder rows in baseline output. Keep tests self-contained and do not read `.gsd/` files. Include negative/robustness assertions that default-output selection for M020 is milestone-local and that the audit still records capture-command failures instead of hiding them. Done when the new tests fail against the current runner for missing M020 support and pass after T02.

## Inputs

- `tests/test_optimization_audit.py`
- `tools/optimization_audit.py`
- `docs/project-map.md`

## Expected Output

- `tests/test_optimization_audit.py`

## Verification

python3 -m pytest -q tests/test_optimization_audit.py

## Observability Impact

Adds regression coverage for the generated audit as the diagnostic surface, including nonzero capture-command visibility and placeholder-free ranked output.
