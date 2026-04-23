---
phase: milestone-closeout
phase_name: M012 Optimization Audit & Next-Work Decision
project: SentinelX
generated: 2026-04-23T03:00:52Z
counts:
  decisions: 4
  lessons: 4
  patterns: 4
  surprises: 3
missing_artifacts: []
---

### Decisions

- Kept the live enrichment status contract additive: terminal metadata (`status`, `terminal`, `terminal_reason`, `error`) was added without replacing the existing success-path payload (`results`, `complete`, `next_since`, progress fields).
  Source: S01-SUMMARY.md/What Happened

- Moved shared live/history stateful result application into `result-application.ts` while leaving polling cadence, terminal handling, and history replay timing inside their owning runtimes.
  Source: S02-SUMMARY.md/What Happened

- Preserved the repo-native verification surface (`make verify-fast`, `make verify-deep`, `make verify`) instead of inventing wrapper commands, and made mocked-online browser proof deterministic only at the E2E fixture boundary.
  Source: S03-SUMMARY.md/What Happened

- Closed persistence/helper follow-through with additive `/settings` diagnostics plus an explicit keep decision for WAL-backed stores, full-results history replay, and cursor polling semantics rather than rewriting those seams without evidence.
  Source: S04-SUMMARY.md/What Happened

### Lessons

- Polling clients must parse meaningful JSON before branching on `resp.ok`; otherwise a terminal 404/failed payload is discarded and the UI can poll forever even though the backend already knows the job is done failing.
  Source: S01-SUMMARY.md/What Happened

- Shared UI surfaces need an explicit runtime owner contract. Without `.page-results[data-results-owner]`, history detail pages can accidentally satisfy live guards and initialize the wrong behavior.
  Source: S02-SUMMARY.md/What Happened

- Deterministic browser proof comes from stubbing orchestration at the test-fixture seam, not from weakening production routes. Keeping the real Flask submit/CSRF/render path intact makes browser failures point at the seam under test.
  Source: S03-SUMMARY.md/What Happened

- Milestone validation has to fail on requirements-ledger drift even when runtime proof is green. A missing canonical requirement row (`R040`) is a real closeout defect, not documentation trivia.
  Source: S05-SUMMARY.md/What Happened

### Patterns

- Harden polling APIs by extending the payload with additive terminal metadata over a stable success schema instead of replacing the existing contract.
  Source: S01-SUMMARY.md/patterns_established

- Extract a shared apply/flush/finalize coordinator for DOM state, but keep transport- and timing-specific behavior in the owning live/history module.
  Source: S02-SUMMARY.md/patterns_established

- Treat `make verify-fast` as the default optimization/refactor proof floor and escalate to `make verify-deep` only when the change crosses a browser-visible seam.
  Source: S03-SUMMARY.md/patterns_established

- Expose helper-owned persistence health through an aggregate inspection surface first; only redesign WAL-backed storage or replay contracts if diagnostics or realistic load measurements prove pain.
  Source: S04-SUMMARY.md/patterns_established

### Surprises

- The planned fast/deep verification command surface already existed in the repo, so S03’s real work was validating and hardening the deterministic deep lane rather than rewriting Makefile targets.
  Source: S03-SUMMARY.md/Deviations

- The persistence/helper seam looked like a plausible optimization target at milestone start, but the best justified shipped change was bounded observability on `/settings`, not a storage rewrite.
  Source: S04-SUMMARY.md/What Happened

- M012 closeout was blocked not by failing code or tests but by requirements-ledger inconsistency: roadmap/context/summaries referenced `R040` before the canonical ledger contained it.
  Source: S05-SUMMARY.md/New Requirements Surfaced
