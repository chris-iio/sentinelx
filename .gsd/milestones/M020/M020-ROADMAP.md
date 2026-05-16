# M020: Audit-Led Aggressive Refactor and Deep Optimization

**Vision:** Refactor the SentinelX codebase and do a deep optimization pass through audit-led aggressive rewrites, preserving analyst workflow behavior while shipping or explicitly rejecting high-confidence optimization targets with strict proof.

## Success Criteria

- A generated M020 audit artifact ranks aggressive rewrite candidates across SentinelX seams and is produced from source rather than hand-edited prose.
- At least the highest-confidence aggressive rewrite target is shipped or explicitly rejected with measurement or code-path reasoning plus regression proof.
- SentinelX preserves the analyst IOC triage loop: intake, extraction, enrichment, results, history/detail, diagnostics, filtering, copy, and export.
- Strict verification lanes pass according to touched seams, including final make verify.
- Generated audit and closeout artifacts explain what changed, what was left alone, and why.

## Slices

- [x] **S01: S01** `risk:high` `depends:[]`
  > After this: A generated M020 audit artifact exists, ranks aggressive rewrite candidates across SentinelX seams, and distinguishes do-now, do-next, later, and leave-alone outcomes with proof requirements.

- [x] **S02: S02** `risk:high` `depends:[]`
  > After this: The top audit-ranked rewrite or optimization is shipped or explicitly rejected with evidence, focused regression tests, and make verify-fast proof.

- [x] **S03: S03** `risk:high` `depends:[]`
  > After this: A second audit-ranked target that crosses module boundaries is completed or rejected, with the audit updated to record the outcome and behavior-preservation proof.

- [x] **S04: S04** `risk:medium` `depends:[]`
  > After this: A browser-visible or live-enrichment-visible optimization is shipped or rejected with focused tests and make verify-deep proof.

- [x] **S05: S05** `risk:medium` `depends:[]`
  > After this: The M020 audit reflects shipped/rejected outcomes, final make verify passes, and closeout proof confirms SentinelX’s analyst loop still works end-to-end.

- [x] **S06: S06** `risk:medium` `depends:[]`
  > After this: After this: Generated audit and closeout evidence explicitly cover deferred storage redesign R101, major UI/product redesign R102, external provider integration R103, and the S02 to S04 analyst-visible contract handoff, with audit tests and final verification rerun.

## Boundary Map

### S01 → S02

Produces:
- Generated M020 audit artifact and ranked do-now/do-next/later/leave-alone rewrite candidates.
- Proof requirements and verification lanes attached to each candidate.

Consumes:
- docs/project-map.md, tools/optimization_audit.py, Makefile verification lanes, and prior M017 proof model.

### S02 → S03

Produces:
- Outcome for the highest-ranked rewrite target: shipped implementation or explicit rejection with evidence.
- Focused regression tests and refreshed audit outcome language.

Consumes:
- S01 ranked target list and proof requirements.

### S02 → S04

Produces:
- Baseline implementation/audit pattern for tying shipped or rejected targets to verification evidence.

Consumes:
- S01 ranked target list and any preserved analyst-visible contracts from S02.

### S03 → S05

Produces:
- Cross-seam rewrite or rejection outcome with audit evidence and behavior-preservation proof.

Consumes:
- S02 proof pattern and updated audit artifact.

### S04 → S05

Produces:
- Analyst-visible or live-enrichment-visible optimization outcome with make verify-deep proof when applicable.

Consumes:
- S01 audit rankings, S02/S03 contracts, and browser/live-enrichment continuity guardrails.
