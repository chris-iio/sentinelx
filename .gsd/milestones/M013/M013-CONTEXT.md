# M013: M013 — Context Draft

**Gathered:** 2026-04-23
**Status:** Ready for planning

## Project Description

M013 is a refactoring/migration plus performance-audit milestone. It should build a reusable optimization-audit workflow and use SentinelX as the proving ground. The milestone is not meant to stop at analysis: it should produce the audit/report, codify the workflow, and ship the resulting high-confidence fixes from a full end-to-end pass.

The workflow should be SentinelX-first, but reusable elsewhere with light editing. It does not need to be over-productized for unknown future repos on day one.

## Why This Milestone

SentinelX has already gone through multiple cleanup and optimization milestones, so the easy wins are mostly gone. What remains needs stronger judgment and stronger proof. The point now is not generic cleanup or optimization theater; it is to make sure the code is as optimized and efficient as it could reasonably be, maybe doing something better or differently, and then best build ourselves to keep building.

This milestone exists now because future work quality depends on whether the current codebase is carrying hidden waste, awkward seams, unnecessary complexity, or slow proof loops that will make every later milestone more expensive.

## User-Visible Outcome

### When this milestone is complete, the user can:

- run or follow a SentinelX-first optimization-audit workflow and review a ranked, evidence-backed outcome
- trust that the workflow did not stop at findings: the high-confidence fixes from the proven pass were actually shipped and verified

### Entry point / environment

- Entry point: local repository workflow plus project verification commands
- Environment: local dev
- Live dependencies involved: provider HTTP calls, SQLite databases, Flask request flow, frontend polling/render coordination

## Completion Class

- Contract complete means: the workflow runs end-to-end, produces ranked findings, and leaves behind artifacts/docs/automation that clearly distinguish do now, do next, later, and leave alone
- Integration complete means: the milestone proves the full live stack boundaries that matter here — provider HTTP behavior, SQLite stores, Flask request flow, and frontend polling/render coordination
- Operational complete means: one whole-codebase proven pass ships the resulting high-confidence fixes without weakening existing runtime or security behavior

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- SentinelX went through one full, evidence-backed optimization pass rather than a partial spot-check
- that pass produced ranked findings and shipped the high-confidence fixes from that pass with verification
- proof reached the full live stack — provider HTTP behavior, SQLite stores, Flask request flow, and frontend polling/render coordination — not just isolated backend surfaces or audit paperwork

## Architectural Decisions

### SentinelX-First Reuse

**Decision:** Build the optimization-audit workflow for SentinelX first, but keep it reusable in other repos with light editing.

**Rationale:** SentinelX is the proving ground and the immediate beneficiary, but the user wants reusable value to come out of the work. Light-edit reuse captures that without forcing early productization overhead.

**Alternatives Considered:**
- SentinelX-only — rejected because the workflow should be reusable
- Cross-repo productized from day one — rejected because it adds structure before the workflow has earned it

### One Proven Pass Defines Done

**Decision:** M013 is done when one whole-codebase optimization pass is completed, ranked findings are produced, and the high-confidence fixes from that pass are shipped or explicitly deferred.

**Rationale:** The user does not want the milestone to stop at a first batch of analysis, but also does not want an endless milestone that can never close because new work always appears.

**Alternatives Considered:**
- Keep draining backlog indefinitely — rejected because it removes any truthful completion bar
- Audit plus roadmap only — rejected because the milestone must ship worthwhile work, not just describe it

### Workflow Assets Are Part of the Deliverable

**Decision:** M013 may ship commands, docs, repeatable checklists/scripts, reports, automation, and code fixes.

**Rationale:** The workflow itself is part of the milestone output. If the repo gets faster but the optimization process stays ad hoc, the milestone misses part of its purpose.

**Alternatives Considered:**
- Docs and reports only — rejected because that leaves too much manual repetition
- Code fixes only — rejected because it loses the reusable workflow value

### Future-You Is the Primary Audience

**Decision:** The primary audience is future-you continuing to build SentinelX; collaborator readability and cross-repo transfer are secondary but still desirable.

**Rationale:** The user’s framing is about best building SentinelX to keep building. The workflow should optimize for future decision quality in this repo first.

**Alternatives Considered:**
- Team-ready now as the primary audience — not the main target on day one
- Cross-repo audience first — rejected because it would bias the milestone toward packaging over proof

### Measured Plus Shipped Proof Bar

**Decision:** Completion proof must show the workflow ran end-to-end, produced ranked findings, and shipped the high-confidence fixes with verification.

**Rationale:** The milestone should feel genuinely complete, not merely well-documented. Green tests alone do not prove that the optimization workflow found and retired meaningful work.

**Alternatives Considered:**
- Measured audit only — rejected because it stops short of delivery
- Repo-wide green bar — rejected because green alone does not prove the audit produced meaningful decisions

### Full Live-Stack Verification

**Decision:** Truthful completion requires proof across provider HTTP behavior, SQLite stores, Flask request flow, and frontend polling/render coordination.

**Rationale:** The real inefficiencies and regressions in SentinelX can live at the seams between these subsystems. Backend-only or workflow-only proof would be too weak.

**Alternatives Considered:**
- Backend-heavy only — rejected because it under-checks the analyst-visible path
- Workflow surface only — rejected because the milestone is about the actual product stack, not just its audit artifacts

## Error Handling Strategy

Treat audit conclusions conservatively. If a finding is not supported by measurements or strong code-path evidence, it remains an observation or open question rather than becoming a required fix.

High-confidence fixes should be narrow, revertible, and verification-backed. Behavior is preserved by default: this milestone should not silently alter extraction semantics, enrichment semantics, route behavior, API behavior, or UI behavior unless a specific change is justified and then verified.

The milestone must also preserve existing security posture. Optimization cannot weaken CSP, CSRF, SSRF controls, host validation, provider safety checks, or other current protections. Failure visibility itself counts as optimization-relevant: if weak observability, ambiguous state, or hidden work makes SentinelX harder to reason about, that is a valid finding.

## Risks and Unknowns

- The audit may surface enough real work to justify follow-on milestones — this matters because M013 needs a truthful close condition without pretending the backlog vanished
- A performance-first bias can create fragile changes if proof is weak — this matters because the user wants improvement, not churn disguised as optimization
- Some subsystems may look fine in isolation but still waste work at integration seams — this matters because full-stack proof is required
- The codebase may already be near the point of diminishing returns in some areas — this matters because “leave alone” must remain a valid and respected outcome

## Existing Codebase / Prior Art

- `app/enrichment/orchestrator.py` — central runtime seam for provider dispatch, concurrency limits, backoff, and job tracking; likely optimization hotspot
- `app/cache/store.py` — SQLite WAL cache store whose lock and I/O patterns matter to the audit
- `app/enrichment/history_store.py` — second SQLite WAL store with similar persistence concerns and continuity constraints
- `app/routes/analysis.py` and related route modules — request-path seams to evaluate for unnecessary work or awkward coupling
- `app/static/src/ts/modules/enrichment.ts` — frontend polling/render coordinator and likely analyst-visible hotspot
- `app/static/src/ts/modules/result-application.ts` — shared live/history rendering seam worth evaluating during the audit
- `.gsd/milestones/M012/M012-CONTEXT.md` — prior optimization milestone framing that this work should build on rather than ignore
- `.gsd/milestones/M012/M012-SUMMARY.md` — evidence of the current keep/change decisions and proof model coming into M013

## Relevant Requirements

- `R008` — preserve enrichment polling, export, filtering, detail links, copy buttons, and progress continuity while optimizing
- `R009` — preserve CSP, CSRF, SSRF allowlist, host validation, and DOM-safety constraints
- `R010` — preserve or improve polling/render efficiency
- `R014` — preserve per-provider concurrency behavior unless evidence proves a better approach
- `R015` — preserve 429 backoff behavior unless evidence proves a better approach
- `R018` — preserve semaphore/backoff and snapshot correctness unless evidence proves otherwise
- `R019` — preserve cursor-based polling efficiency unless evidence proves otherwise
- `R020` — preserve persistent HTTP session behavior where still justified
- `R022` — preserve WAL-mode cache/history store behavior unless evidence supports change
- `R040` — keep strong verification continuity while refactoring and optimizing

## Scope

### In Scope

- whole-codebase optimization review across backend/runtime, adapters/enrichment, persistence, routes/API, frontend/rendering, and tests/build/tooling
- one full proven pass through that workflow on SentinelX
- ranked findings with explicit do now / do next / later / leave alone outcomes
- commands, docs, automation, reports, and code fixes that make the workflow reusable
- shipping the high-confidence fixes discovered by the proven pass
- identifying what is already strong and should be left alone

### Out of Scope / Non-Goals

- optimization theater
- style-only cleanup
- endless backlog draining inside one milestone
- cross-repo productization beyond light-edit reuse
- backend-only proof that ignores the analyst-visible frontend/runtime seam
- behavior-changing refactors justified only by taste

## Technical Constraints

- Preserve current user-visible behavior by default
- Preserve existing security posture while optimizing
- Prefer measurement-backed conclusions whenever practical
- Where direct measurement is awkward, document explicit code-path reasoning rather than hand-wavy claims
- Verify against the full live stack, not just isolated unit logic
- Keep workflow assets reusable with light editing rather than hard-coding them to SentinelX only

## Integration Points

- Provider HTTP boundaries — request volume, retries, session usage, and any avoidable per-request overhead
- SQLite stores — locking, connection usage, indexing/query patterns, and avoidable write/read contention
- Flask request flow — route/app-helper coupling and unnecessary work on hot paths
- Frontend polling/render flow — incremental DOM/state coordination that is visible to the analyst
- Verification workflow — commands, reports, and automation that codify the audit loop and future proof bar

## Testing Requirements

The milestone must prove both the audit workflow and the shipped fixes.

At minimum it should:
- run the relevant repo verification lanes before and after changes
- collect measured timings where practical, or use strong code-path evidence where measurement is not practical
- verify that any shipped fix preserves behavior across the actual subsystem boundary it touches
- include end-to-end proof across provider HTTP behavior, SQLite stores, Flask request flow, and frontend polling/render coordination
- preserve continuity requirements around polling, rendering, persistence, route behavior, and security constraints

## Acceptance Criteria

- M013 completes one full, evidence-backed optimization pass across SentinelX
- The pass leaves behind reusable workflow assets for future runs with light editing in other repos
- The milestone produces ranked findings and clearly distinguishes do now, do next, later, and leave alone
- The high-confidence fixes from that pass are shipped and verified, not merely proposed
- Verification covers the full live stack rather than only backend or paperwork surfaces
- The final output improves future building quality by clarifying what is already strong, what should change now, and what should wait

## Open Questions

- How much of the discovered work will fit inside M013 before it naturally splits into follow-on milestones — current thinking: close after one proven pass plus shipped high-confidence fixes, then carry deeper work forward
- Which subsystem ends up being the highest-value optimization target once the full pass is run — current thinking: keep an open mind, but orchestrator/runtime, persistence seams, frontend coordination, and verification cost remain strong candidates
- Whether any apparently “good enough” seam actually warrants deeper change after full-stack measurement — current thinking: assume existing architecture is mostly sound unless evidence proves otherwise
