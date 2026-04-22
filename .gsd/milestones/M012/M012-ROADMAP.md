# M012: Optimization Audit & Next-Work Decision

**Vision:** Produce an evidence-backed optimization roadmap for SentinelX that proves where current cost and risk actually live, ships the highest-leverage low-regret improvement through the real product surface, and leaves a ranked next-work plan future work can trust.

## Success Criteria

- Major SentinelX subsystems are reviewed with specific evidence-backed findings or explicit leave-alone conclusions.
- The milestone leaves a ranked action plan that distinguishes do now, do next, later, and leave alone work.
- At least one high-risk live seam improvement ships through the real analyst workflow so future optimization decisions are grounded in observable behavior, not theory.
- Continuity requirements R008, R009, R010, R014, R015, R018, R019, R020, R022, and R040 have an explicit ownership path across the milestone.

## Slices

- [x] **S01: S01** `risk:High — this is the live seam where provider backoff, job eviction, polling semantics, and analyst trust all converge; if we cannot surface terminal states and measure real latency here, every later optimization decision is weaker.` `depends:[]`
  > After this: An analyst can run enrichment through the existing UI and see explicit terminal states for missing/evicted/failed jobs instead of silent endless polling, with verification evidence that the live status path still preserves cursor polling, concurrency/backoff behavior, and current security boundaries.

- [x] **S02: S02** `risk:Medium-high — current duplicate coordination between live polling and history replay is a future-change and performance seam, but the exact extraction boundary should be chosen after S01 confirms the status contract shape.` `depends:[]`
  > After this: A user sees the same enrichment cards, detail rows, progress, and verdict rendering whether results arrive live or are replayed from history, with one shared application path carrying the behavior.

- [ ] **S03: Fast default proof loop and deterministic expensive lane** `risk:Medium — the codebase is already fast in build/typecheck paths, but the full verification loop is expensive enough to shape future velocity; we need a user-trustworthy split between default and slower evidence lanes.` `depends:[S01]`
  > After this: A contributor can run a clearly documented fast verification lane for touched optimization work and a separate slower lane for deeper confidence, without accidental real backoff sleeps or ambiguous proof expectations.

- [ ] **S04: Persistence and helper-layer next-work decision** `risk:Medium-low — storage and helper seams look healthy today, so this slice should only advance if earlier evidence still points to contention, write amplification, or unnecessary request-path work.` `depends:[S01,S02,S03]`
  > After this: The milestone closes with a ranked, evidence-backed decision on whether cache/history/helper-path changes are warranted now, later, or should be left alone, with any shipped quick win proven against the real stack boundary it touches.

## Boundary Map

- **Backend ↔ Frontend status contract:** S01 hardens terminal status semantics and analyst-visible failure handling.
- **Frontend live ↔ history rendering path:** S02 unifies result application once S01 stabilizes the contract.
- **Developer ↔ verification loop:** S03 clarifies fast and slow proof lanes while preserving coverage.
- **Routes/helpers ↔ persistence:** S04 converts evidence into a keep/change decision and only ships justified low-regret follow-through.
