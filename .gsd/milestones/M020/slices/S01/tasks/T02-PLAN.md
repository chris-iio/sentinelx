---
estimated_steps: 1
estimated_files: 3
skills_used: []
---

# T02: Implement M020 audit generation in the runner and Makefile

Why: R094/R095 require the M020 artifact to be source-generated and ranked; the existing runner only has generic/M013 and M017 milestone-specific paths. Do: update `tools/optimization_audit.py` with M020 constants, default output/template paths, M020-specific ranked findings and stance sections, an M020 rerun checklist, command-surface/default-output selection, and baseline language that distinguishes do-now, do-next, later, and leave-alone candidates with proof requirements. Ground the candidate list in `docs/project-map.md` seams and M020 decisions/requirements, while avoiding secrets or analyst IOC data. Update `Makefile` variables, `.PHONY`, and targets for `audit-m020-template` and `audit-m020`. Preserve existing M013/M017 behavior and keep capture-command failure rows visible. Done when the focused audit tests pass and `make audit-m020` writes the milestone artifact.

## Inputs

- `tools/optimization_audit.py`
- `Makefile`
- `tests/test_optimization_audit.py`
- `docs/project-map.md`

## Expected Output

- `tools/optimization_audit.py`
- `Makefile`

## Verification

python3 -m pytest -q tests/test_optimization_audit.py

## Observability Impact

Extends the audit runner's command surface and generated measurement/rerun sections so future agents can inspect M020 target selection and failed optional captures from the artifact itself.
