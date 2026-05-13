---
phase: complete-milestone
phase_name: Project Clarity & Aggressive Optimization
project: sentinelx
generated: 2026-05-13T00:00:00Z
counts:
  decisions: 5
  lessons: 4
  patterns: 4
  surprises: 2
missing_artifacts: []
---

# M017 Learnings

### Decisions

- Start optimization with `docs/project-map.md` and a refreshed `.gsd/PROJECT.md`, then use those artifacts as the identity anchor for selecting work.
  Source: DECISIONS.md/D078

- Rank M017 optimization targets by SentinelX's product identity as a local analyst IOC triage app, prioritizing intake, enrichment/results, history/detail, diagnostics, and proof surfaces.
  Source: DECISIONS.md/D079

- Require measurement when practical, or explicit code-path reasoning plus regression proof, for aggressive optimization changes.
  Source: DECISIONS.md/D080

- Preserve full-snapshot enrichment status APIs for intentional callers while routing normal status polling through tail-only `get_incremental_status()`.
  Source: S03-SUMMARY.md/Key Decisions

- Keep S05 as evidence assembly only and use `docs/m017-closeout-proof.md` as the durable non-GSD proof artifact instead of shipping additional product code during closeout.
  Source: S05-SUMMARY.md/Key Decisions

### Lessons

- A validation artifact with a `pass` verdict is useful but still needs freshness/current-artifact checks before milestone completion.
  Source: M017-VALIDATION.md/Verdict Rationale

- S03 found the desired incremental polling implementation and focused tests were already present, so the correct closeout action was to prove, preserve, and regenerate audit evidence rather than duplicate code.
  Source: S03-SUMMARY.md/Deviations

- S04 initially lacked the required `npm test -- --run` command surface; adding a minimal package test script made the frontend verification lane repo-native and repeatable.
  Source: S04-SUMMARY.md/Deviations

- External provider behavior remains represented by deterministic mocked-online and runtime lanes during this milestone; live third-party validation was intentionally not part of closeout proof.
  Source: S05-SUMMARY.md/Known Limitations

### Patterns

- Generated optimization audit artifacts should be backed by testable generator contracts that reject stale target language after an optimization ships.
  Source: S03-SUMMARY.md/Patterns Established

- Frontend render optimizations should use behavior-focused DOM contract tests that cover both negative no-op/provider-only paths and positive severity/order-changing paths.
  Source: S04-SUMMARY.md/Patterns Established

- Final optimization closeout should combine artifact assertions, focused regression lanes, and full repo-native verification lanes.
  Source: S05-SUMMARY.md/Patterns Established

- Artifact-only clarity slices can close with structural verification, but downstream optimization slices must ground findings in concrete seam file paths from the project map.
  Source: S01-SUMMARY.md/Patterns Established

### Surprises

- The first code-change diff against the integration branch was a self-diff retry, so milestone-scoped commit evidence was needed to prove non-GSD implementation files changed.
  Source: M017 closeout verification/code-change guard

- S04 only needed `result-application.ts` even though adjacent browser modules were listed as likely touch points, because the optimization already existed but was shadowed by a duplicate broad flush declaration.
  Source: S04-SUMMARY.md/Deviations
