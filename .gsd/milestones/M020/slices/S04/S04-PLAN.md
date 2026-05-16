# S04: Analyst-Visible Optimization Target

**Goal:** Ship or explicitly reject a browser-visible/live-enrichment-visible optimization target from the M020 audit by measuring large-result frontend render pressure, preserving analyst-facing result behavior, and proving the outcome with focused frontend tests plus make verify-deep.
**Demo:** A browser-visible or live-enrichment-visible optimization is shipped or rejected with focused tests and make verify-deep proof.

## Must-Haves

- A focused frontend regression/measurement proves the selected browser-visible optimization decision, including the large-result same-severity no-op path and severity-change path.
- The implementation either preserves the current severity-change gate or changes the result-application seam only when the measurement justifies it; no virtualization rewrite ships without proof that it preserves filtering, sorting, copy/export, detail links, expansion state, and textContent-safe rendering.
- The generated M020 audit source and artifact record S04 as shipped, rejected, or deferred with evidence and rerun lanes.
- Verification passes: `npx vitest run app/static/src/ts/modules/result-application.test.ts`, `python3 -m pytest -q tests/test_optimization_audit.py`, `make audit-m020`, and `make verify-deep`. If production TypeScript changes, also run `make verify-fast`.

## Proof Level

- This slice proves: Integration/operational proof. This slice touches browser-visible result rendering evidence and therefore requires focused frontend tests and the mocked-online browser lane (`make verify-deep`). Real external provider runtime is not required; deterministic mocked-online/browser-visible proof is sufficient. Human UAT is not required.

## Integration Closure

Upstream surfaces consumed: S01 generated audit rankings, S02/S03 proof pattern, `app/static/src/ts/modules/result-application.ts`, frontend result card helpers, Make verification lanes, and `tools/optimization_audit.py`. New wiring introduced: no new runtime entrypoint unless measurement justifies a code change; the expected durable wiring is audit-source outcome language plus focused frontend measurement proof. Remaining before M020 is fully usable end-to-end: S05 must refresh final audit/closeout and run full `make verify`.

## Verification

- Runtime signals remain the existing analyst-visible result DOM, verdict dashboard counts, card ordering, copy/export/detail link affordances, polling status flow, and E2E browser proof. Failure visibility must remain explicit through DOM state and mocked-online browser failures; no secrets or provider payloads should be logged or added to generated fixtures.

## Tasks

- [x] **T01: Measure large-result render pressure at the severity-change gate** `est:45m`
  Expected executor skills: react-best-practices, tdd, verify-before-complete.
  - Files: `app/static/src/ts/modules/result-application.test.ts`
  - Verify: npx vitest run app/static/src/ts/modules/result-application.test.ts

- [x] **T02: Record the S04 optimization decision in the generated audit source** `est:1h`
  Expected executor skills: write-docs, verify-before-complete.
  - Files: `tools/optimization_audit.py`, `tests/test_optimization_audit.py`, `.gsd/milestones/M020/M020-AUDIT.md`, `app/static/src/ts/modules/result-application.ts`
  - Verify: python3 -m pytest -q tests/test_optimization_audit.py

- [x] **T03: Run focused frontend and mocked-online browser proof** `est:1h`
  Expected executor skills: verify-before-complete, test.
  - Files: `app/static/src/ts/modules/result-application.test.ts`, `tools/optimization_audit.py`, `tests/test_optimization_audit.py`, `.gsd/milestones/M020/M020-AUDIT.md`
  - Verify: make verify-deep

## Files Likely Touched

- app/static/src/ts/modules/result-application.test.ts
- tools/optimization_audit.py
- tests/test_optimization_audit.py
- .gsd/milestones/M020/M020-AUDIT.md
- app/static/src/ts/modules/result-application.ts
