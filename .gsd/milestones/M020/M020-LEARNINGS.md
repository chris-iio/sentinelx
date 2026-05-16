---
phase: complete-milestone
phase_name: Milestone Closeout
project: sentinelx
generated: 2026-05-16T00:00:00Z
counts:
  decisions: 5
  lessons: 4
  patterns: 4
  surprises: 3
missing_artifacts: []
---

# M020 Learnings

### Decisions

- Chose generated audit source as the canonical record for M020 optimization outcomes rather than hand-editing `.gsd/milestones/M020/M020-AUDIT.md`, so tests and `make audit-m020` keep closeout language reproducible.
  Source: S01-SUMMARY.md/Key decisions; S05-SUMMARY.md/Key decisions; S06-SUMMARY.md/Key decisions

- Treated the route IOC helper centralization target as shipped because shared grouping/template/API payload ownership already lived in `app/routes/_helpers.py` and focused route/API/history tests proved the seam.
  Source: S02-SUMMARY.md/Key decisions

- Preserved route-level helper imports as compatibility and regression seams rather than removing them for cosmetic cleanup.
  Source: S02-SUMMARY.md/Key decisions; S02-SUMMARY.md/Deviations

- Treated diagnostics policy centralization as a shipped keep-decision because `app/diagnostics/policy.py` already provided immutable caps consumed by assembler, sources, and redaction modules.
  Source: S03-SUMMARY.md/Key decisions; S03-SUMMARY.md/Deviations

- Deferred frontend virtualization, major storage redesign, broad UI/product redesign, and new external provider integrations because current evidence did not justify those risky rewrites within M020.
  Source: S04-SUMMARY.md/Key decisions; S06-SUMMARY.md/Requirements Validated

### Lessons

- Code-path reasoning can be the correct proof surface for optimization targets when the intended refactor already exists and runtime measurement would not add meaningful signal.
  Source: S02-SUMMARY.md/Patterns established; S03-SUMMARY.md/Patterns established

- Compatibility imports can be real public seams in tests and route behavior, so apparent cleanup should be reverted when regression evidence shows downstream reliance.
  Source: S02-SUMMARY.md/Deviations

- Deferred-scope requirements need explicit non-claim language and tests; otherwise validation can pass behaviorally while still missing durable coverage for what did not ship.
  Source: S06-SUMMARY.md/What Happened; M020-VALIDATION.md/Validation Requires Attention

- Browser-visible optimization should not be shipped solely because a large-result path exists; focused work-count or gate behavior can prove deferral is safer than introducing a virtualization rewrite.
  Source: S04-SUMMARY.md/What Happened; S04-SUMMARY.md/Known Limitations

### Patterns

- Pair every generated optimization audit update with focused tests that assert outcome language, proof commands, failure visibility, redaction guardrails, and deferred-scope boundaries.
  Source: S03-SUMMARY.md/Patterns established; S06-SUMMARY.md/Patterns established

- Close aggressive-refactor slices with a three-part proof: generated audit outcome, focused seam regressions, and the appropriate Make verification lane.
  Source: S02-SUMMARY.md/Patterns established; S05-SUMMARY.md/Patterns established

- Use final milestone closeout to combine lane-specific evidence rather than broadening claims beyond what those lanes exercise.
  Source: S05-SUMMARY.md/Key decisions; S05-SUMMARY.md/Verification

- Treat deferred requirements as first-class validation outcomes by documenting explicit non-claims, preserved contracts, and the evidence required to revisit them.
  Source: S06-SUMMARY.md/Patterns established; S06-SUMMARY.md/Requirements Validated

### Surprises

- Two high-ranked refactor targets were already implemented correctly, so the milestone delivered stronger tests and generated documentation rather than production rewrites for those seams.
  Source: S02-SUMMARY.md/Deviations; S03-SUMMARY.md/Deviations

- The validation artifact was passing but still flagged for freshness/coverage attention, requiring a fresh final `make verify` and explicit closeout synthesis before completion.
  Source: M020-VALIDATION.md/Validation Requires Attention; gsd_exec-7f88e173/M020 fresh closeout verification

- S06 noted that its task environment lacked the dedicated requirement-update tool, leaving requirement ledger synchronization as a closeout consideration.
  Source: S06-SUMMARY.md/Deviations
