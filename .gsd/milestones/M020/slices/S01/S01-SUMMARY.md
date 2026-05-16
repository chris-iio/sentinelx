---
id: S01
parent: M020
milestone: M020
provides:
  - Generated M020 audit artifact and ranked do-now/do-next/later/leave-alone rewrite candidates.
  - Proof requirements and verification lanes attached to audit candidates.
  - Repo-native `audit-m020-template` and `audit-m020` command surface.
requires:
  - slice: None
    provides: S01 has no upstream slice dependency; it consumed docs/project-map.md, the existing optimization audit runner, Make verification lanes, and prior M017 audit patterns encoded in the runner.
affects:
  - S02
  - S03
  - S04
  - S05
key_files:
  - tests/test_optimization_audit.py
  - tools/optimization_audit.py
  - Makefile
  - .gsd/milestones/M020/M020-AUDIT.md
key_decisions:
  - Treated the generated audit runner as the canonical source for M020 audit prose and regenerated artifacts through Make rather than hand-editing.
  - Treated existing passing M020 runner/Makefile implementation as authoritative once contract tests and artifact generation proved compliance.
patterns_established:
  - Milestone-specific generated audit contracts should cover identity, grounding, bucket taxonomy, proof requirements, rerun lanes, default output selection, and failed-capture visibility.
  - Downstream rewrite slices should consume generated audit rankings and attach shipped/rejected outcomes to the same proof-language pattern.
observability_surfaces:
  - Generated audit command-surface rows, capture-command result rows, rerun checklist, proof requirements, and verification lanes in `.gsd/milestones/M020/M020-AUDIT.md`.
drill_down_paths:
  - .gsd/milestones/M020/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M020/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M020/slices/S01/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-05-16T08:37:24.334Z
blocker_discovered: false
---

# S01: M020 Audit Expansion

**Generated the M020 optimization audit surface that ranks aggressive rewrite candidates into do-now, do-next, later, and leave-alone buckets with downstream proof requirements.**

## What Happened

S01 established the audit-led front door for M020. The focused optimization-audit tests now lock the M020 contract for template and baseline modes, including milestone-local output selection, M020 identity language, decisions D081-D083, requirements R094/R095/R099/R100, docs/project-map.md grounding, ranked outcome buckets, proof requirements, rerun lanes, and failed capture-command visibility. The existing runner and Makefile implementation were verified as already satisfying that contract, so the milestone artifact was regenerated through the repo-native `make audit-m020` path rather than hand-edited. The generated `.gsd/milestones/M020/M020-AUDIT.md` is now the authoritative downstream input for S02-S05 target selection and closeout updates.

## Verification

Closeout verification used `gsd_exec`. `make audit-m020 && python3 -m pytest -q tests/test_optimization_audit.py && make verify-fast` passed with exit code 0. A separate artifact inspection over `.gsd/milestones/M020/M020-AUDIT.md` passed with exit code 0, confirming M020 title/identity, do-now/do-next/later/leave-alone buckets, docs/project-map.md grounding, proof and verification language, D081-D083 references, and R094/R095/R099/R100 references. Task-level summaries also record passing `make audit-m020`, focused audit tests, and fast verification.

## Requirements Advanced

- R099 — The audit proof language preserves failure-state, diagnostics, capture-command failure visibility, and redaction guardrails as constraints for later rewrite slices.
- R100 — S01 established the generated audit as the durable documentation surface for rewrite decisions; later slices must update it with shipped/rejected outcomes.

## Requirements Validated

- R094 — Generated `.gsd/milestones/M020/M020-AUDIT.md` via `make audit-m020`; tests and closeout inspection confirmed source-generated M020 identity, docs/project-map.md grounding, ranked candidates, and proof language.
- R095 — Focused audit tests and closeout inspection confirmed do-now, do-next, later, and leave-alone ranked outcomes with downstream proof requirements and verification lanes.

## New Requirements Surfaced

- None.

## Requirements Invalidated or Re-scoped

- None. — 

## Operational Readiness

None.

## Deviations

No source rewrites were needed during T02 because the M020 runner and Makefile implementation were already present and passing the newly added contract tests; the task refreshed and verified the artifact instead.

## Known Limitations

S01 only establishes the audit and proof-selection surface. It does not ship or reject any rewrite target, does not measure live runtime performance, and does not complete final M020 closeout outcome documentation.

## Follow-ups

S02 should consume the do-now ranked target from `.gsd/milestones/M020/M020-AUDIT.md` and either ship or explicitly reject it with focused regression proof. S03 and S04 should follow the same audit-backed proof pattern, and S05 should refresh the audit with final outcomes plus full verification.

## Files Created/Modified

- `tests/test_optimization_audit.py` — Added/verified M020 contract coverage for template and baseline output, default output selection, ranked buckets, proof requirements, and capture-command failure visibility.
- `tools/optimization_audit.py` — Contains the M020 audit generation path, constants, ranked findings, proof language, and milestone-specific output handling verified by S01.
- `Makefile` — Exposes `audit-m020-template` and `audit-m020` targets for repo-native artifact generation.
- `.gsd/milestones/M020/M020-AUDIT.md` — Generated M020 audit artifact for downstream rewrite target selection and proof requirements.
