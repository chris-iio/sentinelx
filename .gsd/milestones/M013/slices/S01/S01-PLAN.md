# S01: Reusable audit workflow and baseline ranked pass

**Goal:** Create the reusable audit runner, ranking format, and baseline full-stack findings that every later optimization slice will use to justify shipped changes or leave-alone decisions.
**Demo:** After this: A contributor can run a checked-in SentinelX-first optimization-audit workflow and get a durable ranked artifact with do now / do next / later / leave alone buckets, baseline evidence, and explicit continuity notes for runtime, persistence, request flow, and frontend seams.

## Must-Haves

- The repo exposes a repeatable local workflow for M013 audit runs, including command entrypoints, artifact locations, and a clear distinction between measurement-backed findings and code-path reasoning.
- The first full SentinelX pass produces a durable ranked artifact with `do now`, `do next`, `later`, and `leave alone` buckets across runtime/provider, request/persistence, and frontend/render seams.
- The baseline explicitly maps continuity guardrails R008, R009, R010, R014, R015, R018, R019, R020, R022, and R040 so later slices can retire findings without losing table-stakes behavior.
- The slice records what proof lanes must be rerun after each shipped fix, including deterministic mocked-online browser coverage for live-stack changes.

## Proof Level

- This slice proves: Workflow-level proof plus executable baseline verification: the workflow must run from local dev, emit the ranked artifact, and record the verification lanes later slices must rerun before claiming a keep-worthy optimization.

## Integration Closure

This slice closes when one checked-in workflow ties together provider/runtime, Flask helper/status flow, SQLite WAL stores, and frontend polling/render seams into a single repeatable audit pass with durable ranked output and explicit rerun rules for downstream slices.

## Verification

- Adds durable milestone-local audit artifacts, ranking vocabulary, and comparison points so later slices can explain why a change shipped, was deferred, or was intentionally left alone.

## Tasks

- [x] **T01: Create the reusable audit runner and ranked artifact format** `est:0.75d`
  Add a checked-in command surface for the M013 pass — likely a Make target plus a small helper script or equivalent documented entrypoint — that runs the agreed baseline lanes, captures timing/measurement metadata, and writes milestone-local outputs in a consistent format. Encode the core milestone rule directly into the workflow: a finding must be backed by measurement when practical, otherwise by explicit code-path reasoning, and every output must land in one of `do now`, `do next`, `later`, or `leave alone`.

Keep the workflow SentinelX-first but lightly reusable: the command surface should assume this repo’s current verify lanes and directory layout, while keeping the ranking/report format portable enough for future light-edit reuse.
  - Files: `Makefile`, `tools/optimization_audit.py`, `README.md`, `.gsd/milestones/M013/`
  - Verify: python3 tools/optimization_audit.py --help

- [x] **T02: Run the baseline full-stack audit and publish the first ranked findings** `est:0.75d`
  Use the checked-in workflow to run the first full SentinelX optimization pass across the main seams already identified by research: orchestrator/provider dispatch, Flask helper/request flow, WAL-backed cache/history stores, and frontend polling/render coordination. Capture timings where practical; where direct timing is awkward, write the explicit code-path reasoning that justifies the ranking.

Publish the first durable ranked findings artifact in the milestone directory. The artifact must make keep decisions explicit, not implicit, and it must show how the table-stakes continuity requirements stay guarded while the pass identifies true do-now work.
  - Files: `tools/optimization_audit.py`, `.gsd/milestones/M013/`, `docs/optimization-audit.md`
  - Verify: python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md

- [ ] **T03: Prove the workflow and baseline are trustworthy for downstream slices** `est:0.5d`
  Run the repo’s existing verification lanes through the new workflow and record which proof surfaces later slices must revisit after any shipped optimization. Make deterministic mocked-online browser proof an explicit part of the downstream contract for live-stack changes, alongside the faster local verification lanes.

This task is done only when the milestone directory contains the baseline findings, the workflow entrypoints, and a clear rerun checklist that future slices can follow without reconstructing context from this planning session.
  - Files: `Makefile`, `README.md`, `docs/optimization-audit.md`, `.gsd/milestones/M013/`
  - Verify: make verify-fast && make verify-deep

## Files Likely Touched

- Makefile
- tools/optimization_audit.py
- README.md
- .gsd/milestones/M013/
- docs/optimization-audit.md
