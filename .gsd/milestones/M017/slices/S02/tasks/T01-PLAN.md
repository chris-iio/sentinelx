---
estimated_steps: 8
estimated_files: 3
skills_used: []
---

# T01: Teach the audit runner the M017 identity-grounded contract

Why: S02 must not merely copy the old M013 audit; the runner needs a current M017 contract grounded in SentinelX's S01 project map and decisions D078-D080. Executor skills: test, write-docs, verify-before-complete.

Do:
1. Update `tools/optimization_audit.py` so `--milestone-id M017 --mode baseline` writes an M017-flavored audit artifact that references `docs/project-map.md`, SentinelX's analyst IOC triage identity, R085/R087, D078-D080, and the S01 seam inventory priorities.
2. Preserve backward compatibility for the existing default/M013 assertions unless intentionally generalized; do not remove the current measurement/capture command behavior.
3. Add M017-specific assertions to `tests/test_optimization_audit.py` using a temporary output path, not `.gsd/`, covering project-map grounding, ranked buckets, explicit evidence standard, S03 target language, and no placeholder rows.
4. Add or generalize `Makefile` variables/targets so contributors can regenerate `.gsd/milestones/M017/M017-AUDIT.md` without memorizing CLI flags (for example `audit-m017` and, if useful, `audit-m017-template`).
5. Keep generated audit content deterministic enough for tests while allowing command-capture timestamps/durations to remain dynamic.

Failure Modes (Q5): If `docs/project-map.md` is missing at execution time, the runner should still fail or render a clear note rather than silently claiming identity grounding; if a capture command fails, existing capture metadata should record nonzero exit rather than aborting unrelated artifact generation. Load Profile (Q6): Per-generation cost should remain bounded to local file reads plus optional capture commands; no network or long-running runtime path is introduced. Negative Tests (Q7): Tests should cover at least one M017 baseline run and preserve existing malformed diagnostics/capture escaping tests.

## Inputs

- `tools/optimization_audit.py`
- `tests/test_optimization_audit.py`
- `Makefile`
- `docs/project-map.md`
- `.gsd/PROJECT.md`
- `.gsd/milestones/M013/M013-AUDIT.md`

## Expected Output

- `tools/optimization_audit.py`
- `tests/test_optimization_audit.py`
- `Makefile`

## Verification

python3 -m pytest -q tests/test_optimization_audit.py

## Observability Impact

Adds/updates audit CLI and Makefile inspection surfaces; pytest failures localize broken artifact contracts before downstream optimization work consumes them.
