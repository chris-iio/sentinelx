---
id: M014
title: "Local workflow hardening and recovery loop"
status: complete
completed_at: 2026-04-26T02:06:55.863Z
key_decisions:
  - Kept `tools/runtime_state_boundary.py` as the sole durable/transient/manual-review policy source for audits, repair behavior, docs, and tests.
  - Limited automatic runtime-state repair to classifier-approved transient classes: deindex tracked transient files, quarantine unignored transient files, and keep `.planning/**` report-only/manual-review.
  - Standardized the local dev-server lifecycle on `tools/dev_server.py` plus thin Make wrappers, with manager-owned metadata under `.gsd/runtime/dev-server/**`.
  - Single-sourced the local `/api/health` contract in `app/health_contract.py` so API production and dev-server probe validation cannot drift.
  - Retained repo-boundary hardening as sufficient for M014 rather than requiring upstream GSD engine changes.
key_files:
  - tools/runtime_state_boundary.py
  - tools/runtime_state_repair.py
  - tools/dev_server.py
  - app/health_contract.py
  - app/routes/api.py
  - tests/test_runtime_state_boundary.py
  - tests/test_runtime_state_boundary_git.py
  - tests/test_runtime_state_repair.py
  - tests/test_runtime_state_repair_git.py
  - tests/test_api.py
  - tests/test_dev_server.py
  - tests/test_dev_server_process.py
  - Makefile
  - README.md
  - docs/runtime-state-boundary.md
  - .gitignore
  - .gsd/milestones/M014/slices/S04/S04-REVIEW.md
  - .gsd/milestones/M014/slices/S04/S04-LIFECYCLE-PROOF.json
  - .gsd/milestones/M014/slices/S04/S04-CLOSURE-PROOF.md
lessons_learned:
  - `.gitignore` alone is not enough for runtime-state hardening because already-tracked transient files can still wedge git workflows; repo-native proof needs index-aware fixtures and repair behavior.
  - A boundary verifier can stay useful without blocking operators on known legacy backlog by failing on blocker issue codes while still printing manual-review findings.
  - Safe repair should be reversible and policy-owned: preserve working-tree contents on deindex, quarantine rather than delete, and fail closed on ambiguous durable paths.
  - Local process recovery is more trustworthy when status is derived from a live health probe rather than PID files alone; stale and crashed children need explicit metadata.
  - Shared local contracts should be single-sourced when both a producer and operator tooling consumer require exact-match fail-closed semantics.
---

# M014: Local workflow hardening and recovery loop

**M014 hardened SentinelX’s local operator loop by separating durable planning artifacts from transient runtime state, adding a safe classifier-backed repair entrypoint, standardizing local dev-server crash recovery, and closing with fresh full-repo verification.**

## What Happened

M014 addressed the local workflow failure classes at the SentinelX repo boundary. S01 made the durable/runtime split explicit by adding `tools/runtime_state_boundary.py`, aligning `.gitignore`, docs, and `make verify-runtime-boundary`, and proving the stash/pop blocker class with real temp-repo Git fixtures. S02 turned that policy into a conservative repair path through `tools/runtime_state_repair.py` and `make repair-runtime-state`: tracked transient findings are deindexed, unignored transient findings are quarantined, and durable or ambiguous paths such as `.planning/**` remain report-only/manual-review. S03 added the supported local dev-process path through `tools/dev_server.py` and `make dev-server-start|status|restart|stop`, with manager-owned state under `.gsd/runtime/dev-server/**`, localhost-only host validation, live `/api/health` probes, explicit crashed/stale state, and restart metadata. S04 performed the planned seam review/refactor closure, accepted `app/health_contract.py` as the single source of truth for the local health contract, preserved classifier-owned repair policy and thin Make wrappers, and captured final assembly evidence in `S04-REVIEW.md`, `S04-LIFECYCLE-PROOF.json`, and `S04-CLOSURE-PROOF.md`.

Milestone completion verification was rerun in this closeout turn after the final code state. Code-change verification passed even though `HEAD` is already on `main` and the branch self-diff is empty: milestone-scoped recent commits that touch `.gsd/milestones/M014/**` also touched implementation files including `tools/runtime_state_boundary.py`, `tools/runtime_state_repair.py`, `tools/dev_server.py`, `app/routes/api.py`, `app/health_contract.py`, `Makefile`, `README.md`, `docs/runtime-state-boundary.md`, and the focused test suites. Fresh command evidence also passed: the chained verification command exited 0, including focused runtime/repair/dev-server tests, `make repair-runtime-state`, `make verify-runtime-boundary`, and `make verify`; `make verify` reported `1018 passed, 113 deselected` in non-E2E pytest, Vitest `81 passed`, clean TypeScript/build, and E2E pytest `113 passed`. A concise repair/status check then confirmed repair remained conservative (`deindex_count=0`, `quarantine_count=0`, `blocked_count=237`, `failed_count=0`) and the supported dev-server manager was stopped with metadata preserved under `.gsd/runtime/dev-server/status.json`.

## Success Criteria Results

- ✅ Ordinary local git workflows are no longer blocked by transient runtime-state in the observed stash/conflict class. Evidence: S01 temp-repo Git fixtures prove tracked transient `.gsd/audit/events.jsonl` conflicts are surfaced, ignored/untracked transient files stay out of checkout flows, and fresh closeout `make verify-runtime-boundary` exited 0 with only `manual-review-path` findings and zero blocker classes.
- ✅ Durable planning artifacts and transient machine/session state are behaviorally separated at the repo boundary. Evidence: `tools/runtime_state_boundary.py` is the classifier source of truth; durable `.gsd/milestones/**` and ledgers are preserved, `.gsd/runtime/**` and adjacent runtime files are transient, and `.planning/**` is deliberately `manual-review` rather than auto-mutated.
- ✅ One supported repair/recovery entrypoint exists for local runtime-state cleanup and git-workflow repair. Evidence: `make repair-runtime-state` wraps `tools/runtime_state_repair.py`, applies only classifier-backed deindex/quarantine actions, and the fresh closeout JSON summary showed `deindex_count=0`, `quarantine_count=0`, `blocked_count=237`, and `failed_count=0` on the final repo state.
- ✅ One supported local dev-process path exists, including cheap crash recovery for the local SentinelX server. Evidence: `tools/dev_server.py` plus `make dev-server-start|status|restart|stop` own the local lifecycle; S04 lifecycle proof captured start -> exact health -> forced crash -> crashed status -> restart -> healthy -> stop; fresh closeout status confirmed the stopped manager state and metadata path under `.gsd/runtime/dev-server/status.json`.
- ✅ Final proof shows the assembled workflow survives the triggering failure classes and preserves existing SentinelX verification. Evidence: the fresh closeout chained command exited 0 across focused seam tests, repair, boundary verification, and full `make verify`; `make verify` reported `1018` non-E2E pytest passes, `81` Vitest passes, clean TypeScript/build, and `113` E2E passes.

## Definition of Done Results

- ✅ All roadmap slices are complete: `gsd_milestone_status` reported S01, S02, S03, and S04 all `complete`, with task counts 3/3, 2/2, 3/3, and 3/3 done respectively.
- ✅ All slice summaries exist and were read for closeout synthesis: `S01-SUMMARY.md`, `S02-SUMMARY.md`, `S03-SUMMARY.md`, and `S04-SUMMARY.md` are present and record passed verification.
- ✅ Cross-slice integration points work: S02 consumes S01’s classifier instead of adding a second policy table; S03 stores dev-server state under the S01/S02 runtime boundary; S04 re-proved repair, boundary audit, health-contract exact match, crash/restart recovery, and full verification together.
- ✅ Code-change verification passed: branch self-diff is empty because `HEAD` is already on `main`, but milestone-scoped commits touching `.gsd/milestones/M014/**` also touched non-`.gsd` implementation files (`tools/`, `app/`, tests, Make/docs), satisfying the retry-on-main evidence rule.
- ✅ No Horizontal Checklist was present in the M014 roadmap; no unchecked horizontal items remain.

### Decision Re-evaluation

| Decision | Still valid? | Evidence / next action |
|---|---:|---|
| D063 — keep durable planning artifacts in-repo while treating transient state as runtime-only | ✅ Yes | The classifier and verifier retired blocker classes while preserving durable `.gsd/milestones/**`; revisit only if repo-boundary hardening proves insufficient. |
| D064 — add one repo-native repair/recovery entrypoint | ✅ Yes | `make repair-runtime-state` is now the supported entrypoint and converges safely with zero actionable repairs on final state. |
| D065 — standardize one supported local dev-process path | ✅ Yes | `tools/dev_server.py` and Make wrappers provide the lifecycle path with crash/restart proof; heavier supervision remains unnecessary for the current local workflow. |
| D066 — solve at the SentinelX repo boundary first | ✅ Yes | Final proof fixed the observed local failures without upstream GSD engine changes. |
| D067 — use conservative durable/transient/manual-review classification | ✅ Yes | `.planning/**` remains visible and fail-closed while transient blockers are prevented or surfaced. |
| D068 — keep inspection and repair separate, with classifier-backed repair actions only | ✅ Yes | S04 review preserved `runtime_state_boundary.py` as policy source and `runtime_state_repair.py` as the thin mutating companion. |
| D069 — implement local dev lifecycle under `.gsd/runtime/dev-server/**` with `/api/health` probing | ✅ Yes | Lifecycle tests and live proof validated status-from-probe, crash detection, restart metadata, and stopped state. |

## Requirement Outcomes

- R061 (`validated`) — Supported by S01/S04 proof: boundary Git fixtures and fresh `make verify-runtime-boundary` show tracked/unignored transient blocker classes are absent or surfaced explicitly; ordinary git workflows are no longer blocked by the observed transient-state class.
- R062 (`validated`) — Supported by the checked-in classifier, docs, `.gitignore`, tests, and audit output distinguishing durable `.gsd` artifacts, transient runtime state, and `.planning/**` manual-review paths.
- R063 (`validated`) — Supported by `tools/runtime_state_repair.py`, `make repair-runtime-state`, temp-repo Git repair tests, and fresh closeout repair summary with no failed actions and only intentional blocked/manual-review findings.
- R064 (`validated`) — Supported by `tools/dev_server.py`, the fixed `/api/health` contract, focused dev-server tests, and S04 lifecycle proof demonstrating start, crash detection, restart, and stop through the supported workflow.
- R065 (`validated`) — Supported by fresh closeout `make verify` success: `1018` non-E2E pytest passes, `81` Vitest passes, clean TypeScript/build, and `113` E2E passes.
- R069 (`validated`) — Supported by `S04-REVIEW.md`, which records the seam review, refactor-now/leave-alone decisions, and the accepted `app/health_contract.py` single-source refactor.

No requirement status changes were needed during this completion turn because the requirements were already updated to `validated` by their owning slices with evidence.

## Deviations

S01 intentionally narrowed `make verify-runtime-boundary` to fail only on blocker classes while still printing `.planning/**` manual-review findings. S04 discovered the planned shared health-contract refactor was already present in the live repo, so it avoided redundant churn and verified/documented the shipped `app/health_contract.py` seam instead.

## Follow-ups

Legacy `.planning/**` remains a visible `manual-review-path` backlog and should only be migrated by a future reviewed migration path; do not add automatic cleanup for it casually. Revisit upstream GSD runtime-state relocation only if repo-boundary hardening fails to cover future observed workflow blockers. A heavier supervisor is still out of scope unless repeated local operational pain justifies it.
