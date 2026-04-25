---
phase: M013
phase_name: SentinelX optimization-audit workflow and shipped full-stack pass
project: SentinelX
generated: 2026-04-25T07:29:16Z
counts:
  decisions: 4
  lessons: 4
  patterns: 4
  surprises: 3
missing_artifacts: []
---

### Decisions

- Start optimization milestones with a workflow-first slice that ships the reusable audit runner, ranked artifact format, and baseline findings before touching subsystem code.
  Source: DECISIONS.md/D057

- Split optimization work by regression seam — runtime/provider, request/persistence, and frontend/render — so each slice can ship or defer changes independently and the final slice can close with one truthful rerun.
  Source: DECISIONS.md/D058

- Preserve `EnrichmentOrchestrator.get_status()` as the history-safe full snapshot and add a separate incremental accessor for live polling instead of rewriting persistence around deltas.
  Source: DECISIONS.md/D061

- Keep the frontend win narrow: cache stable IOC DOM handles and page-level provider-count metadata inside the shared coordinator, then close with a fresh audit rerun plus captured fast/deep proof.
  Source: DECISIONS.md/D062

### Lessons

- Browser proof becomes brittle when tests anchor to shared utility classes instead of semantic page structure; targeting the named Cache and History Save Diagnostics sections fixed the ambiguity without weakening verification.
  Source: S01-SUMMARY.md/Deviations

- A runtime optimization slice can legitimately end in a measured keep-decision. The `1/5 (20%)` cache-hit runtime capture showed the dispatch/cache shortcut was not strong enough to justify new churn across a correctness-heavy seam.
  Source: S02-SUMMARY.md/What Happened

- Splitting full-history reads from live-polling reads is an effective way to retire hot-path waste without forcing history persistence or terminal semantics to reconstruct state from deltas.
  Source: S03-SUMMARY.md/patterns_established

- Closeout proof is more reusable when the audit artifact itself records which verification lanes were rerun on the final repository state instead of leaving that knowledge in task prose.
  Source: PROJECT.md/Current State

### Patterns

- Use one checked-in audit artifact to hold ranked findings, continuity guardrails, and rerun obligations rather than scattering optimization notes across task summaries.
  Source: S01-SUMMARY.md/Patterns Established

- Keep runtime/provider observability aggregate and job-local: bounded orchestrator counters are safe to snapshot, while mutable diagnostics on shared adapters are not.
  Source: S02-SUMMARY.md/Patterns Established

- Split full-history and live-polling reads into separate orchestrator contracts: full snapshots for history/persistence callers, incremental tails for hot-path polling.
  Source: S03-SUMMARY.md/patterns_established

- Reduce render-path waste by caching stable DOM handles and one-time provider-count metadata inside the shared live/history coordinator instead of reopening transport, persistence, or DOM-safety contracts.
  Source: PROJECT.md/Architecture / Key Patterns

### Surprises

- The settings-page deep test failure came from two sections intentionally sharing the same utility-class hook, so the proof seam had to move to semantic headings rather than looser assertions.
  Source: S01-SUMMARY.md/Deviations

- Much of the planned S02 runtime/provider implementation was already present locally, which turned the slice into a verification-and-keep-decision exercise rather than a code-heavy optimization pass.
  Source: S02-SUMMARY.md/Deviations

- The lightweight local audit captures were strong enough to justify shipping the hot-path wins and deferring deeper runtime/persistence churn, which is a better outcome than forcing extra changes to satisfy a preconceived "optimization" plan.
  Source: S01-SUMMARY.md/Known Limitations
