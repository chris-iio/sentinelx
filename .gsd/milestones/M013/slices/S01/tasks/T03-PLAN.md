---
estimated_steps: 2
estimated_files: 4
skills_used: []
---

# T03: Prove the workflow and baseline are trustworthy for downstream slices

Run the repo’s existing verification lanes through the new workflow and record which proof surfaces later slices must revisit after any shipped optimization. Make deterministic mocked-online browser proof an explicit part of the downstream contract for live-stack changes, alongside the faster local verification lanes.

This task is done only when the milestone directory contains the baseline findings, the workflow entrypoints, and a clear rerun checklist that future slices can follow without reconstructing context from this planning session.

## Inputs

- `Baseline audit artifact from T02`
- `Existing verify-fast / verify-deep lanes`
- `Deterministic mocked-online browser test seam`

## Expected Output

- `Verified rerun checklist for downstream slices`
- `Recorded proof-lane expectations for fast and deep verification`
- `Milestone-local evidence showing the workflow completed end-to-end`

## Verification

make verify-fast && make verify-deep

## Observability Impact

Pins the exact proof surfaces that make future optimization work auditable instead of relying on memory or informal norms.
