---
id: M013
title: "M013 — SentinelX optimization-audit workflow and shipped full-stack pass"
status: complete
completed_at: 2026-04-25T07:28:19.969Z
key_decisions:
  - D057: Start M013 with a workflow-first slice so every later optimization change is evaluated against one repeatable evidence model.
  - D058: Split M013 into separate runtime/provider, request/persistence, and frontend/render slices so each seam can be changed and verified independently before final recomposition.
  - D059: Require every optimization outcome to carry measurement or explicit code-path reasoning plus the appropriate verification rerun lane.
  - D060: Keep runtime/provider diagnostics job-local on the orchestrator and accept an explicit keep-decision when the measurements do not justify dispatch-path churn.
  - D061: Preserve `get_status()` as the full-snapshot/history-safe contract while moving live polling to a separate incremental accessor.
  - D062: Ship only coordinator-local DOM/provider-count caching on the frontend and close the milestone with a fresh audit rerun plus captured fast/deep proof.
key_files:
  - tools/optimization_audit.py
  - docs/optimization-audit.md
  - Makefile
  - README.md
  - app/enrichment/orchestrator.py
  - app/routes/_helpers.py
  - app/static/src/ts/modules/result-application.ts
  - app/static/src/ts/modules/enrichment.ts
  - app/static/src/ts/modules/history.ts
  - tests/test_optimization_audit.py
  - tests/test_orchestrator.py
  - tests/test_routes.py
  - tests/test_api.py
  - tests/e2e/test_results_page.py
lessons_learned:
  - Use the audit artifact itself as the durable decision surface so shipped-now vs keep/defer outcomes survive across slices and closeout turns.
  - On correctness-heavy seams, additive hot-path splits are safer than broad rewrites: the incremental status accessor delivered the win while preserving the history-safe full snapshot contract.
  - Frontend/render work can capture a meaningful win by caching stable DOM handles and page-level metadata locally instead of reopening transport, persistence, or DOM-safety contracts.
  - Closeout proof should be generated on the same final state as the audit refresh; embedding fresh fast/deep evidence in the artifact removes handoff ambiguity.
---

# M013: M013 — SentinelX optimization-audit workflow and shipped full-stack pass

**M013 established a reusable optimization-audit workflow, shipped the request/status and frontend/render hot-path fixes it justified, and closed with a fresh full-stack audit rerun plus fast/deep proof on the final state.**

## What Happened

M013 turned optimization work into a repeatable, evidence-backed workflow instead of a series of ad hoc cleanup guesses. S01 established `tools/optimization_audit.py` as the canonical runner, added thin Make wrappers plus README/docs guidance, and published the durable milestone-local audit artifact with fixed ranked buckets (`do now`, `do next`, `later`, `leave alone`), per-seam continuity notes, and a verified rerun checklist. That gave the later slices one shared vocabulary for runtime/provider, request/status, persistence, and frontend/render work.

S02 used that workflow to close the runtime/provider seam honestly. The orchestrator’s job-scoped diagnostics surface stayed bounded and snapshot-safe, the audit capture showed a `1/5 (20%)` cache-hit ratio, and the slice therefore recorded the dispatch/cache-path idea as a measured keep-decision instead of shipping speculative churn that could have weakened per-provider caps, 429 handling, cached-marker safety, or adapter-owned sessions.

S03 then shipped the milestone’s highest-confidence backend win: the live polling hot path moved to an orchestrator-owned incremental status accessor while `get_status()` remained the history-safe full-snapshot contract. That removed the per-poll full-list copy from `/enrichment/status` and `/api/status` without reopening history persistence, helper-owned terminal tombstones, or the WAL-backed cache/history design. The audit artifact was refreshed to mark request/status as shipped work and WAL persistence as a measured keep-decision.

S04 closed the analyst-visible seam without changing live/history ownership or transport contracts. The shared live/history coordinator now caches stable per-IOC DOM handles and page-level provider-count metadata so result application stops repeating whole-document lookups on every update. The slice then regenerated the audit artifact on the same repository state and embedded fresh `verify-fast` / `verify-deep` evidence so the final record truthfully shows what shipped now versus what remains deferred.

## Decision Re-evaluation

| Decision | Re-evaluation | Evidence | Next action |
| --- | --- | --- | --- |
| D057 | Still valid | Starting with the workflow-first S01 prevented optimization theater and let every later slice update one durable ranked artifact. | Keep this pattern for future optimization milestones. |
| D058 | Still valid | Splitting runtime/provider, request/persistence, and frontend/render work into S02/S03/S04 kept each seam narrow enough to verify independently, then rejoin through the final audit rerun. | Reuse seam-based slicing when regression surfaces differ materially. |
| D059 | Still valid | The shipped backend/frontend fixes were backed by code-path reasoning plus final-state proof, while lower-confidence runtime/persistence ideas stayed ranked as keep/defer outcomes. | Preserve measurement-or-reasoning plus rerun-lane discipline. |
| D060 | Still valid | Runtime/provider diagnostics showed the cache-hit/dispatch idea was not strong enough to justify churn, so the keep-decision was the correct outcome. | Revisit only if a future cache-hit-heavy or provider-pain-heavy capture changes the evidence. |
| D061 | Still valid | Separating `get_incremental_status()` from full `get_status()` delivered the hot-path win without breaking history persistence or terminal semantics. | Treat this split as the stable contract going forward. |
| D062 | Still valid | Coordinator-local DOM/provider-count caching delivered the narrow frontend win while preserving live/history ownership, DOM-safety, and final audit truthfulness. | Only revisit broader flush/reorder work if later measurements justify it. |

## Success Criteria Results

- [x] **Reusable audit workflow shipped and runnable end-to-end.** `tools/optimization_audit.py`, `Makefile`, `README.md`, and `docs/optimization-audit.md` were added/updated in S01, and fresh closeout verification reran `python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md` with `EXIT:0` on the final state.
- [x] **All target seams were revisited through one shared evidence vocabulary and guardrail set.** S01 established the ranked audit artifact across runtime/provider, request/status, persistence, and frontend/render; S02 refreshed the runtime/provider seam with bounded diagnostics and measured keep-decisions; S03 shipped the request/status hot-path improvement and re-proved persistence as a keep-decision; S04 shipped the frontend/render coordinator caching path and refreshed the final audit.
- [x] **High-confidence work shipped; lower-confidence work stayed explicitly ranked instead of disappearing.** S03 shipped the incremental request/status path; S04 shipped coordinator-local frontend/render caching; S02 recorded the runtime/provider dispatch/cache idea as a measured keep-decision; S03 kept WAL-backed persistence as an explicit measured keep-decision; the audit artifact preserved `do now`, `do next`, `later`, and `leave alone` buckets through the final rerun.
- [x] **Final proof preserved the milestone’s continuity/security/runtime requirements.** Fresh final-state verification passed in this closeout turn: `make verify-fast` → `982 passed, 113 deselected`, Vitest `81 passed`, clean `npx tsc --noEmit`, successful production build; `make verify-deep` → `113 passed in 36.69s`; audit regeneration exited 0 on the same repository state.

## Definition of Done Results

- [x] **All roadmap slices are complete.** `gsd_milestone_status(M013)` shows S01, S02, S03, and S04 all `complete`, with every slice reporting `3/3` tasks done and zero pending tasks.
- [x] **Slice summaries exist.** `find .gsd/milestones/M013 -maxdepth 4 -type f` confirmed `S01-SUMMARY.md` through `S04-SUMMARY.md` plus all twelve task summaries.
- [x] **Cross-slice integration works on the assembled final state.** The backend/runtime/frontend changes compose cleanly under fresh closeout proof: audit regeneration exited 0, `make verify-fast` passed end-to-end, and `make verify-deep` passed the mocked-online browser lane.
- [x] **Non-.gsd code changes exist.** `git diff --stat HEAD $(git merge-base HEAD origin/main) -- ':!.gsd/'` reported extensive non-`.gsd/` changes across runtime, routes, frontend modules, tests, docs, and build wiring, so M013 did not produce planning artifacts only.
- [x] **Horizontal checklist review.** No separate Horizontal Checklist section was present in the roadmap, so there were no unchecked horizontal items blocking closeout.

## Requirement Outcomes

No requirement statuses changed during M013, so no `gsd_requirement_update` calls were required at closeout.

What changed was the proof surface:

- **R008 / R009 / R010** were preserved as continuity guardrails in the audit workflow and remained satisfied through the shipped request/status and frontend/render changes plus fresh deep verification.
- **R014 / R015 / R018 / R020 / R022** remained validated requirements and were re-proved as measured keep-decisions rather than being reopened speculatively; S02 and S03 refreshed the audit artifact and preserved per-provider caps, 429 behavior, snapshot safety, adapter-owned sessions, and WAL-backed persistence.
- **R019** remained validated and was strengthened by the shipped incremental polling path on `/enrichment/status` and `/api/status`, which kept cursor and terminal semantics while removing the per-poll full-snapshot copy from the hot path.
- **R040** was already in `validated` status before M013; this milestone refreshed its validation evidence on the final state with fresh closeout proof: `make verify-fast` passed (`982 passed, 113 deselected`, Vitest `81 passed`, clean typecheck, successful build), `make verify-deep` passed (`113 passed in 36.69s`), and the audit artifact regenerated successfully (`EXIT:0`).

## Deviations

S02 largely verified and formalized an already-present diagnostics/capture implementation rather than shipping a new runtime/provider code path. More broadly, M013 intentionally treated several seams as explicit keep-decisions when the evidence did not justify churn, so the milestone shipped fewer but safer optimizations than a cleanup-driven plan would have.

## Follow-ups

If future measurements justify it, revisit the remaining deferred frontend work around flush-wide dashboard recount/reorder costs. Reopen runtime/provider dispatch-path changes only after a stronger cache-hit-heavy or provider-pain-heavy capture demonstrates that the current measured keep-decision is no longer the right tradeoff.
