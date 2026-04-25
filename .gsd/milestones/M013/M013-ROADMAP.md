# M013: M013 - SentinelX optimization-audit workflow and shipped full-stack pass

**Vision:** Run a reusable SentinelX-first optimization-audit workflow, publish ranked evidence-backed findings, and ship the high-confidence full-stack fixes that the pass justifies without weakening existing runtime, persistence, security, or analyst-visible behavior.

## Success Criteria

- A checked-in SentinelX-first optimization-audit workflow can be run end-to-end in local dev and emits durable ranked findings rather than ad hoc notes.
- The milestone revisits runtime/provider, request/persistence, and frontend/render seams through one shared evidence vocabulary and continuity guardrail set.
- High-confidence do-now fixes discovered by the pass are shipped, while lower-confidence work is explicitly ranked as do next, later, or leave alone rather than silently dropped.
- Final proof shows the shipped changes preserve R008, R009, R010, R014, R015, R018, R019, R020, R022, and R040 across the live stack.

## Slices

- [x] **S01: S01** `risk:High — if M013 does not first produce a repeatable, evidence-backed audit loop, later slices can devolve into optimization theater and cannot truthfully justify changes to concurrency, WAL persistence, polling, or rendering seams.` `depends:[]`
  > After this: After this: A contributor can run a checked-in SentinelX-first optimization-audit workflow and get a durable ranked artifact with do now / do next / later / leave alone buckets, baseline evidence, and explicit continuity notes for runtime, persistence, request flow, and frontend seams.

- [x] **S02: S02** `risk:High — orchestrator dispatch, retry/backoff, session reuse, and cache interaction are the highest-leverage runtime seams but already encode correctness-critical behavior, so any change must be evidence-backed and narrowly shipped.` `depends:[]`
  > After this: After this: An analyst can run enrichment through the existing UI with the same concurrency/backoff/cache guarantees and either lower measured runtime overhead or a justified leave-alone decision recorded in the ranked audit.

- [x] **S03: S03** `risk:Medium-high — Flask helper/state ownership and WAL-backed stores sit on correctness-heavy seams where unnecessary work may exist, but regressions would directly threaten polling continuity, history durability, and cache behavior.` `depends:[]`
  > After this: After this: Status polling, history reload, cache continuity, and helper diagnostics still behave the same for users while any justified request-path or SQLite hot-path improvement is shipped and the rest is explicitly ranked as keep, later, or do next.

- [x] **S04: S04** `risk:Medium — the analyst-visible polling/render seam is where hidden DOM churn and transport coordination waste will show up, but the slice must preserve live/history parity while also closing the milestone with a truthful rerun of the full audit.` `depends:[]`
  > After this: After this: An analyst sees unchanged live/history enrichment UX with any proven polling/render improvement shipped, and the repo contains the final rerun of the ranked audit showing what shipped now versus what remains deferred.

## Boundary Map

- **S01 — reusable audit/report contract:** establishes the command surface, artifact format, and proof vocabulary later slices must reuse.
- **S02 — provider/runtime boundary:** touches orchestrator dispatch, provider HTTP behavior, backoff/session reuse, and cache hot-path decisions.
- **S03 — Flask/helper ↔ SQLite boundary:** covers status serialization, helper state ownership, cache/history WAL persistence, and continuity diagnostics.
- **S04 — frontend live/history boundary:** covers polling cadence, result application, row rendering cost, and the final rerun tying shipped-now vs deferred outcomes together.
