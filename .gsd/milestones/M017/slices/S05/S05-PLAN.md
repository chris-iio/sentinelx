# S05: Final Integrated Proof + Durable Handoff

**Goal:** Assemble the final M017 proof that SentinelX is now clearly mapped and defensibly optimized: project map, generated optimization audit, requirements coverage, and full verification lane evidence all agree, with fresh `make verify-fast` and `make verify-deep` results.
**Demo:** The project map, audit artifact, requirements coverage, and full verification evidence show SentinelX is clearer and measurably/defensibly optimized.

## Must-Haves

- `docs/project-map.md`, `.gsd/PROJECT.md`, and `.gsd/milestones/M017/M017-AUDIT.md` still describe SentinelX as a local analyst IOC triage app and include the S03/S04 shipped optimization outcomes.
- A durable closeout proof artifact is written outside `.gsd/` so future agents can inspect the milestone result without relying only on GSD summaries.
- R084, R087, R088, and R089 coverage is explicitly mapped to artifacts and verification evidence.
- Fresh closeout verification passes: `npm test -- --run`, `python3 -m pytest -q tests/test_optimization_audit.py tests/e2e/test_results_page.py tests/e2e/test_emailrep_online.py`, `make verify-fast`, and `make verify-deep`.
- No new optimization code is shipped in S05 unless final verification exposes a real blocker; if it does, replan before changing product code.

## Proof Level

- This slice proves: - This slice proves: final-assembly
- Real runtime required: yes — `make verify-deep` exercises the mocked-online browser/runtime lane.
- Human/UAT required: no — proof is automated and artifact-based.

## Integration Closure

- Upstream surfaces consumed: `docs/project-map.md`, `.gsd/PROJECT.md`, `.gsd/milestones/M017/M017-AUDIT.md`, `.gsd/REQUIREMENTS.md`, S03/S04 summaries, `tools/optimization_audit.py`, `tests/test_optimization_audit.py`, `app/static/src/ts/modules/result-application.ts`, `app/static/src/ts/modules/enrichment-status.ts`, `Makefile`, and `package.json`.
- New wiring introduced in this slice: none expected; this is a final assembly and verification slice, not a product-code slice.
- What remains before the milestone is truly usable end-to-end: nothing if the closeout proof artifact exists and both verification lanes pass.

## Verification

- S05 does not add production observability. It validates existing inspection surfaces through audit-generator tests, mocked-online browser e2e diagnostics/status coverage, frontend unit tests, and the repo-native `make verify-fast`/`make verify-deep` command surfaces. Redaction/security behavior remains covered by existing e2e and deep verification lanes.

## Tasks

- [x] **T01: Write the final M017 closeout proof artifact** `est:45m`
  ---
  estimated_steps: 6
  estimated_files: 5
  skills_used:
    - write-docs
    - verify-before-complete
  ---
  - Files: `docs/m017-closeout-proof.md`, `docs/project-map.md`, `.gsd/PROJECT.md`, `.gsd/milestones/M017/M017-AUDIT.md`, `.gsd/REQUIREMENTS.md`
  - Verify: test -s docs/m017-closeout-proof.md && grep -Eq "R084|R087|R088|R089" docs/m017-closeout-proof.md && grep -Ei "incremental|polling|status" docs/m017-closeout-proof.md && grep -Ei "severity|result-application|recount|reorder" docs/m017-closeout-proof.md

- [x] **T02: Run focused closeout regression and fill evidence** `est:1h`
  ---
  estimated_steps: 7
  estimated_files: 6
  skills_used:
    - test
    - verify-before-complete
  ---
  - Files: `docs/m017-closeout-proof.md`, `package.json`, `tools/optimization_audit.py`, `tests/test_optimization_audit.py`, `tests/e2e/test_results_page.py`, `tests/e2e/test_emailrep_online.py`
  - Verify: npm test -- --run && python3 -m pytest -q tests/test_optimization_audit.py tests/e2e/test_results_page.py tests/e2e/test_emailrep_online.py && grep -Ei "npm test -- --run|tests/test_optimization_audit.py|test_results_page.py|test_emailrep_online.py" docs/m017-closeout-proof.md

- [x] **T03: Run full verification lanes and finalize R089 handoff** `est:2h`
  ---
  estimated_steps: 7
  estimated_files: 2
  skills_used:
    - test
    - verify-before-complete
  ---
  - Files: `docs/m017-closeout-proof.md`, `Makefile`
  - Verify: make verify-fast && make verify-deep && grep -Ei "make verify-fast|make verify-deep|R089" docs/m017-closeout-proof.md && test -s docs/m017-closeout-proof.md

## Files Likely Touched

- docs/m017-closeout-proof.md
- docs/project-map.md
- .gsd/PROJECT.md
- .gsd/milestones/M017/M017-AUDIT.md
- .gsd/REQUIREMENTS.md
- package.json
- tools/optimization_audit.py
- tests/test_optimization_audit.py
- tests/e2e/test_results_page.py
- tests/e2e/test_emailrep_online.py
- Makefile
