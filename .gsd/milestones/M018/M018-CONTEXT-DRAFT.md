# M018: Refactor Audit + Targeted Cleanup Draft

## Vision

User wants SentinelX "checked again" for refactor opportunities. This is not a broad cleanup pass for its own sake. The milestone should re-check the current codebase after M017, identify evidence-backed maintainability/refactor opportunities across key seams, and only ship targeted cleanup where current evidence says it is worth doing.

## Reflection

M018 is primarily refactoring/migration work, with backend and frontend seams in play. It likely fits as one focused milestone if scoped as an audit-led refactor pass: first inspect/rank opportunities, then ship worthwhile cleanup, then verify behavior remains stable.

## Scope Confirmed

Included:
- Re-check the current SentinelX codebase after M017.
- Identify maintainability/refactor opportunities across backend routes/helpers, enrichment orchestration/provider boundaries, cache/history persistence access, frontend polling/result rendering/history parity, tests/fixtures/proof tooling, and stale docs/audit artifacts.
- Rank findings into do-now/do-next/leave-alone style buckets.
- Ship evidence-backed refactors where clear wins exist.
- Preserve analyst-facing behavior unless a change is explicitly justified and verified.

Excluded:
- No rewrite.
- No feature expansion.
- No cleanup merely because something is imperfect.
- No broad formatting/style churn.
- No changes to provider behavior, verdict semantics, IOC extraction semantics, history behavior, or diagnostics/security boundaries unless equivalence is proven.

Deferred / conditional:
- Larger architectural migrations become future milestones or do-next findings.
- Risky seams should be documented and left alone unless the audit produces strong evidence that fixing them now is safer than deferring.

Boundary:
- M018's core outcome is a fresh, code-grounded refactor assessment plus targeted fixes where the assessment finds current, worthwhile cleanup opportunities.

## Architectural Decisions Confirmed

### Refactor audit as first-class artifact

Decision: Create a dedicated M018 refactor audit artifact, likely `.gsd/milestones/M018/M018-REFACTOR-AUDIT.md`.

Rationale: Refactor opportunities need different ranking language than optimization work. Performance evidence is not the only signal; maintainability risks, duplication, test brittleness, misleading artifacts, and boundary confusion matter too.

Alternative considered: Extend `tools/optimization_audit.py`.
Why not: That would blur faster with cleaner/safer, and future agents may misread cleanup findings as optimization claims.

### Broad cleanup allowed, evidence-gated

Decision: M018 may ship any cleanup that is justified by the audit, including moderate cross-seam refactors if they are the right target.

Rationale: User explicitly said all cleanup is possible and to do as the agent sees fit. The safety bar shifts from small-only to evidence-backed and verified.

Alternative considered: Low-risk behavior-preserving refactors only.
Why not: Too restrictive for the ask; it could leave the best current cleanup untouched.

### Seam-map-first investigation

Decision: Start from `docs/project-map.md` and prior M017 audit/proof artifacts, then inspect code around the highest-signal seams.

Rationale: The codebase already has a durable seam inventory. Starting there avoids random cleanup and keeps the audit connected to known analyst-facing boundaries.

Alternative considered: Blind whole-repo scan first.
Why not: Useful as a supplement, but not as the primary planning model; it risks over-weighting easy textual smells over important seams.

## Evidence So Far

- `.gsd/STATE.md` shows no active milestone; all prior milestones complete.
- `docs/project-map.md` is the current seam inventory and names core architecture seams.
- `M017-SUMMARY.md` says future optimization/refactor work should start from `docs/project-map.md`, regenerate audit artifacts, and preserve the measurement/code-path proof bar.
- `docs/optimization-audit.md` provides an established ranked-audit vocabulary and proof model that M018 can adapt without conflating refactor with optimization.

## Open Questions

- How conservative failure handling should be when the audit finds cleanup that is attractive but risky.
- Exact quality bar and verification lanes for audit-only findings versus shipped refactors.
