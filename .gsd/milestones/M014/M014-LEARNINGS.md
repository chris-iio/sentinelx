---
phase: completion
phase_name: structured-learnings-extraction
project: SentinelX
generated: 2026-04-26T02:06:22Z
counts:
  decisions: 5
  lessons: 5
  patterns: 5
  surprises: 3
missing_artifacts: []
---

# M014 Learnings: Local workflow hardening and recovery loop

### Decisions

- Keep one authoritative runtime-state classifier as the policy source for ignore rules, audits, repair behavior, docs, and dev-loop alignment; avoid parallel durable/transient rule tables.
  Source: S01-SUMMARY.md/Key decisions

- Make repo-native repair conservative and classifier-backed: deindex tracked transient files, quarantine unignored transient files, and keep durable or ambiguous paths report-only/manual-review.
  Source: S02-SUMMARY.md/Key decisions

- Standardize the supported local SentinelX process loop on `tools/dev_server.py` plus thin Make wrappers, with all manager-owned metadata under `.gsd/runtime/dev-server/**`.
  Source: S03-SUMMARY.md/Key decisions

- Single-source the local `/api/health` contract in `app/health_contract.py` so the API producer and dev-server probe consumer share exact fail-closed semantics.
  Source: S04-REVIEW.md/refactor-now

- Solve M014 at the SentinelX repo boundary first rather than requiring upstream GSD runtime-state changes; revisit upstream relocation only if repo-local hardening proves insufficient.
  Source: DECISIONS.md/D066

### Lessons

- `.gitignore` alone does not retire git workflow blockers when transient files are already tracked; the repair loop must understand index state and prove behavior in real temporary repositories.
  Source: S01-SUMMARY.md/What Happened

- A verifier can keep legacy ambiguity visible without blocking routine work by failing only on blocker issue codes while still printing manual-review findings.
  Source: S01-SUMMARY.md/Deviations

- Safe local cleanup needs reversible or non-destructive actions first: preserve working-tree contents on deindex, quarantine rather than delete, and fail closed on ambiguous paths.
  Source: S02-SUMMARY.md/Operational Readiness

- PID files are insufficient process truth; local lifecycle status should derive from a live health probe and convert stale or crashed children into explicit recovery metadata.
  Source: S03-SUMMARY.md/What Happened

- Completion proof is strongest when focused seam tests, operator commands, live lifecycle proof, and full repository verification are run on the same final state.
  Source: S04-CLOSURE-PROOF.md/Commands run

### Patterns

- Use a checked-in classifier plus issue codes as a shared contract between inspection, mutation, documentation, and tests.
  Source: S01-SUMMARY.md/Patterns established

- Keep mutating repair tools as thin companions to inspection tools; the mutator should consume issue codes, not recreate policy.
  Source: S02-SUMMARY.md/Patterns established

- Expose repo-native Make targets as thin wrappers over one checked-in CLI implementation to prevent operator-surface drift.
  Source: S03-SUMMARY.md/Patterns established

- Use fixed metadata-only health contracts for local lifecycle probes and reject payload drift instead of accepting broad diagnostic responses.
  Source: S03-SUMMARY.md/Patterns established

- When both producer and consumer require exact local contract agreement, move shared constants into one module and test both sides against it.
  Source: S04-SUMMARY.md/Patterns established

### Surprises

- The live repo retained a large `.planning/**` backlog, but treating it as report-only/manual-review allowed workflow hardening to pass without unsafe migration.
  Source: S01-SUMMARY.md/Known Limitations

- The planned S04 shared health-contract refactor was already present in the live repo, so closure avoided redundant churn and recorded the no-op/refactor boundary instead.
  Source: S04-SUMMARY.md/Deviations

- The final repo state was already on `main`, so code-change verification had to use milestone-scoped commit evidence rather than an ordinary branch diff.
  Source: M014-SUMMARY.md/Definition Of Done
