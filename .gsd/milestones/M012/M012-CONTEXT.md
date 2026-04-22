# M012: Optimization Audit & Next-Work Decision

**Gathered:** 2026-04-22
**Status:** Ready for planning

## Project Description

SentinelX is already a mature threat-intelligence workflow tool: analysts can paste free-form text, extract IOCs, enrich them across multiple providers, review results in the browser, and revisit past analyses. This milestone is not about inventing a new product surface. It is about going through the entire live codebase and deciding whether the current implementation is as optimized and efficient as it could be, where it could be done better or differently, and what the best next work should be so the codebase is strong for continued building.

The work is explicitly whole-codebase in scope: backend/runtime, adapters/enrichment, persistence, routes/API, frontend/rendering, and tests/build/tooling. Historical `.gsd/` artifacts are context, not the thing being optimized.

## Why This Milestone

SentinelX has already gone through multiple cleanup and optimization milestones, which means the easy wins are mostly gone and the remaining opportunities need to be judged more carefully. The risk now is not obvious slowness alone — it is carrying forward hidden waste, awkward seams, or avoidable complexity that makes every future milestone harder.

This milestone exists now because the user wants to make sure the code is as optimized as possible and as efficient as it could be, maybe doing something better or differently, and then best build ourselves to keep building. That means the output must be evidence-first, performance-aware, and useful to future work rather than generic advice.

## User-Visible Outcome

### When this milestone is complete, the user can:

- review a ranked, evidence-backed action plan that says what to do now, next, later, and what to leave alone
- trust that the next optimization or refactor work is grounded in measurements and live-stack behavior rather than optimization theater

### Entry point / environment

- Entry point: local repository analysis and project verification commands
- Environment: local dev
- Live dependencies involved: provider HTTP calls, SQLite databases, Flask routes, frontend polling/render flow

## Completion Class

- Contract complete means: the milestone produces a whole-codebase optimization assessment with explicit findings, severity/ranking, proof notes, and a concrete next-work decision surface
- Integration complete means: findings and any quick wins are proven against the current live stack boundaries — provider HTTP behavior, SQLite stores, Flask request flow, and frontend polling/render coordination
- Operational complete means: none beyond preserving current behavior and not weakening existing runtime/security characteristics during any quick-win changes

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- the major SentinelX subsystems have been reviewed with evidence-backed findings rather than generic recommendations
- the final output clearly distinguishes do-now, do-next, later, and leave-alone work for future building
- any implemented quick wins are verified against the real code paths and live stack boundaries that make SentinelX work today, not just isolated mock-only reasoning

## Architectural Decisions

### Evidence-First Optimization

**Decision:** Optimization findings and changes must be justified by proof: timings, counts, before/after measurements, code-path analysis, complexity reduction, or other concrete evidence.

**Rationale:** The user wants the code to be as optimized and efficient as possible. That only has meaning if claims are evidence-backed. Otherwise the milestone devolves into generic cleanup or opinionated churn.

**Alternatives Considered:**
- Reasoning-first cleanup — rejected because it risks movement without meaningful gain
- Broad cleanup by feel — rejected because the codebase has already been through multiple optimization passes and the remaining work needs a higher proof bar

### Performance-Biased Tie-Breaker

**Decision:** When there is a real tradeoff, default toward performance, as long as the choice does not create obvious fragility or destroy the ability to keep building cleanly.

**Rationale:** The user explicitly chose performance as the default bias. The milestone should not hide behind elegance when there is a clear faster path with acceptable maintainability.

**Alternatives Considered:**
- Maintainability-first as the default — not chosen as the tie-breaker, though maintainability remains relevant when performance differences are negligible

### Ranked Action Plan as the Primary Outcome

**Decision:** The milestone should primarily leave behind a ranked action plan for what to do now, next, later, and what to leave alone. Quick wins are allowed, but the milestone is not a giant refactor blob by default.

**Rationale:** The user’s priority is deciding what to do next from a whole-codebase understanding. That requires ranking and judgment more than raw code churn.

**Alternatives Considered:**
- Plan plus mandatory broad implementation — rejected because it would force action before the audit has earned it
- Rewrite-oriented milestone — rejected unless the evidence later proves that current architecture is the real bottleneck

### Optimize Important Seams, Not Replace Working Architecture

**Decision:** Treat the existing SentinelX architecture as mostly sound and focus on optimizing the important seams: orchestrator/runtime behavior, persistence locking and I/O patterns, frontend enrichment state/render coordination, route/application helper coupling, test/build cost, and any residual adapter duplication.

**Rationale:** Investigation shows strong existing structure: Flask app factory + blueprints, route decomposition, modular TypeScript, SQLite WAL stores, and provider abstraction. The likely wins are in tightening hot paths and awkward seams, not replacing the stack.

**Alternatives Considered:**
- Architecture replacement as the default direction — rejected because there is no evidence yet that the stack choice itself is the problem
- File-count reduction as an end in itself — rejected because smaller is not automatically faster or easier to extend

### Future-You is the Primary Audience

**Decision:** Write findings and recommendations primarily for the user / future self who will continue building SentinelX.

**Rationale:** The user explicitly framed the value as “best build ourselves to keep building.” The milestone should optimize for future decision quality and future velocity, not just present-day inspection.

**Alternatives Considered:**
- Optimize mainly for outside contributors — secondary concern, not the primary audience right now
- Optimize mainly for end-user-visible speed — still relevant, but not the only or primary lens

## Error Handling Strategy

This milestone uses conservative defaults.

Findings must distinguish between performance hotspot, maintainability drag, unnecessary complexity, correctness risk, and not-worth-touching. The audit should never blur those categories.

No speculative fixes are allowed. If a problem cannot be justified with measurement or strong code-path evidence, it stays an observation or open question rather than becoming an action item.

Behavior is preserved by default. This milestone should not silently alter extraction semantics, enrichment semantics, route behavior, API behavior, or UI behavior unless a specific change is justified and then verified.

Any quick wins should be narrow enough to isolate and revert if they regress behavior. Optimization must not weaken SSRF controls, CSP/CSRF posture, host validation, provider safety behavior, or other existing security constraints.

Failure visibility itself counts as an optimization concern. If weak observability, ambiguous state, or hidden retry/background behavior makes the system harder to reason about and slower to build on, that is a valid finding.

## Risks and Unknowns

- The codebase may already be near the point of diminishing returns — if true, the best decision may be to leave major areas alone rather than force more optimization
- Performance-biased decision-making can accidentally justify fragile changes — the milestone must keep proof and rollback clarity high
- The live stack crosses provider HTTP, SQLite, Flask, and frontend polling/render flow — a subsystem can look clean in isolation while still wasting work at integration boundaries
- Existing tests may prove correctness without proving efficiency — additional measurement or profiling may be needed to avoid false confidence
- Some “better or different” ideas may only pay off in later milestones — premature adoption would create churn rather than value

## Existing Codebase / Prior Art

- `app/enrichment/orchestrator.py` — central runtime seam for provider dispatch, concurrency limits, backoff, and job tracking; likely optimization hotspot
- `app/enrichment/adapters/base.py` — current shared HTTP adapter abstraction; useful baseline for judging whether residual duplication remains worth touching
- `app/cache/store.py` — SQLite WAL cache store with persistent connection and locking; audit target for lock/IO patterns and query behavior
- `app/enrichment/history_store.py` — second SQLite WAL store with similar structure; useful for checking whether store patterns are consistently efficient
- `app/routes/analysis.py` — lean request entry point for analysis flow; useful for judging route/app helper coupling and request-path simplicity
- `app/static/src/ts/modules/enrichment.ts` — frontend polling/render coordinator and likely state/render hotspot
- `.gsd/PROJECT.md` — compressed account of prior milestones; confirms that SentinelX has already had significant cleanup and optimization work, so new findings need stronger proof
- `.gsd/DECISIONS.md` — append-only record of prior architectural and performance decisions; important for distinguishing intentional tradeoffs from accidental complexity

## Relevant Requirements

This milestone is primarily evaluative and planning-oriented, but it must preserve and re-check already-validated capabilities that matter to performance and continuity, including:

- `R008` — enrichment polling, export, filtering, detail links, copy buttons, progress bar all working
- `R009` — CSP, CSRF, textContent-only DOM construction, SSRF allowlist, host validation maintained
- `R010` — debounced sorting, polling efficiency, lazy rendering unchanged or improved
- `R014` — per-provider concurrency in the orchestrator preserved
- `R015` — 429 backoff behavior preserved
- `R018` — semaphore/backoff and snapshot correctness preserved
- `R019` — cursor-based polling efficiency preserved
- `R020` — persistent HTTP sessions preserved where still justified
- `R022` — WAL-mode cache store behavior preserved unless evidence supports a better approach
- `R040` — existing test coverage remains a continuity safety net for refactoring-oriented work

## Scope

### In Scope

- whole-codebase optimization review across backend/runtime, adapters/enrichment, persistence, routes/API, frontend/rendering, and tests/build/tooling
- measured benchmarking where practical
- code-path and structural analysis where direct measurement is awkward
- identifying what is already strong and should be left alone
- producing a ranked action plan for immediate, near-term, later, and not-worth-touching work
- implementing proven quick wins when they are clearly justified and low-regret
- treating extensibility and clarity improvements as valid wins when they meaningfully support future building

### Out of Scope / Non-Goals

- style-only cleanup
- generic recommendations without evidence
- optimization theater
- stack replacement or large rewrites unless the audit proves they are the best next move
- historical `.gsd/` artifacts as the primary optimization target
- behavior-changing refactors justified only by taste

## Technical Constraints

- Preserve current user-visible behavior by default
- Do not weaken existing security posture while optimizing
- Prove findings against the current live stack, not just isolated reasoning
- Use measured proof whenever practical; where not practical, document why code-path reasoning is sufficient
- The codebase already carries multiple prior optimization decisions; new recommendations should respect those unless evidence shows they should be revisited

## Integration Points

- Provider HTTP boundaries — audit request volume, retry behavior, session usage, and any avoidable per-request overhead
- SQLite stores — audit locking, connection usage, indexing/query patterns, and any avoidable write/read contention
- Flask routes and app wiring — audit request-path simplicity, helper coupling, and unnecessary work on hot paths
- Frontend polling/render flow — audit incremental result handling, DOM churn, debouncing, and state coordination
- Test/build tooling — audit whether proof loops are unnecessarily slow or noisy for future development

## Testing Requirements

The milestone should use the strongest proof ladder available for each finding and any implemented quick win.

At minimum:
- run and interpret relevant existing tests before and after any changes in touched areas
- collect measured timings where practical (for example targeted pytest timing, build timing, or focused profiling/measurement loops)
- use static/code-path analysis where measurement is awkward, but document the reasoning clearly
- verify that any quick win preserves behavior across the live boundary it touches, not just in isolated unit logic
- preserve continuity requirements around polling, rendering, persistence, route behavior, and security constraints

## Acceptance Criteria

- The major SentinelX subsystems are each reviewed with specific, evidence-backed findings or explicit leave-alone conclusions
- The milestone produces a ranked action plan that clearly distinguishes do now, do next, later, and leave alone
- Findings are backed by measured proof where practical and by explicit code-path reasoning where measurement is not practical
- The audit covers the current live stack: provider HTTP calls, SQLite stores, Flask routes, and frontend polling/render flow
- Any quick wins shipped in the milestone are low-regret, clearly justified, behavior-preserving, and verified
- The final output helps future building by clarifying the best next optimization/refactor work rather than generating generic advice

## Open Questions

- Which subsystem will prove to be the highest-value next target once whole-codebase evidence is collected — current thinking: orchestrator/runtime, persistence patterns, frontend enrichment flow, and test/build loops are the best candidates
- How many quick wins will survive the proof bar without expanding the milestone too far — current thinking: no hard cap, but only changes with strong evidence should land
- Whether any current “good enough” architectural seam actually warrants deeper change — current thinking: assume the current architecture is mostly sound unless the audit proves otherwise
