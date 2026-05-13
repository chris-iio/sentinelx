# M017: Project Clarity & Aggressive Optimization

**Vision:** Figure out what SentinelX is now, make that understanding durable, and optimize the project aggressively from that product/codebase identity.

## Success Criteria

- SentinelX has a durable current-state project map that explains the product, analyst loop, architecture seams, and optimization priorities.
- The M017 optimization audit is refreshed against that project map and ranks current opportunities with evidence-backed do-now/do-next/later/leave-alone outcomes.
- At least one best-current optimization ships with measurement when practical or explicit code-path reasoning plus regression proof, unless the audit proves no code change is justified now.
- Existing analyst-facing IOC intake, enrichment, results, history/detail, diagnostics, and security behavior remain intact.
- Final closeout passes both make verify-fast and make verify-deep.

## Slices

- [x] **S01: S01** `risk:high` `depends:[]`
  > After this: SentinelX has a separate project map plus refreshed project summary that explains what it is, who it serves, main analyst loop, architecture seams, and optimization priorities.

- [x] **S02: S02** `risk:high` `depends:[]`
  > After this: The audit runner/artifact is refreshed for M017, grounded in the project map, with ranked current findings and explicit do-now/do-next/later/leave-alone decisions.

- [x] **S03: S03** `risk:high` `depends:[]`
  > After this: The highest-value optimization from the M017 audit is shipped with measurement or code-path proof and behavior-preserving tests.

- [x] **S04: S04** `risk:medium` `depends:[]`
  > After this: Any remaining high-confidence optimization tied to intake/results/history/diagnostics is shipped or explicitly rejected, with browser-visible analyst flow proof if touched.

- [x] **S05: S05** `risk:medium` `depends:[]`
  > After this: The project map, audit artifact, requirements coverage, and full verification evidence show SentinelX is clearer and measurably/defensibly optimized.

## Boundary Map

### S01 → S02

Produces:
- `docs/project-map.md` current-state product/codebase map.
- Refreshed `.gsd/PROJECT.md` current-state identity.
- Concrete optimization seam inventory.

Consumes:
- Existing README, requirements, M012/M013 summaries/audit, codebase structure.

### S02 → S03

Produces:
- M017 audit artifact with ranked findings.
- Chosen do-now optimization target and proof requirements.

Consumes:
- S01 project map and existing `tools/optimization_audit.py` workflow.

### S03 → S04

Produces:
- First shipped best-current optimization with focused evidence.
- Updated audit rows showing shipped/deferred/leave-alone outcomes.

Consumes:
- S02 ranked target and relevant touched seam contracts.

### S04 → S05

Produces:
- Secondary optimization or explicit evidenced rejection.
- Analyst-flow regression evidence for touched surfaces.

Consumes:
- S03 code changes and audit state.

### S05 final assembly

Produces:
- Final audit/project-map/requirements alignment.
- Full make verify-fast and make verify-deep proof.
