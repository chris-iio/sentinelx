# S04: S04 — UAT

**Milestone:** M020
**Written:** 2026-05-16T09:04:14.893Z

# S04: S04 — UAT

**Milestone:** M020
**Written:** 2026-05-16

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S04 resolved a browser-visible optimization decision through deterministic frontend regression tests, generated audit proof, and the mocked-online browser lane; no live external provider or human exploratory UAT is required.

## Preconditions

- Repository dependencies are installed.
- The working tree contains the S04 task outputs, including the generated M020 audit artifact.
- Tests can run locally without real provider credentials because the required browser proof is mocked-online.

## Smoke Test

Run `make verify-deep` and confirm the mocked-online E2E suite passes with 126 tests.

## Test Cases

### 1. Large-result severity gate remains safe

1. Run `npx vitest run app/static/src/ts/modules/result-application.test.ts`.
2. Confirm the suite reports 19 passing tests.
3. **Expected:** The large-result same-severity no-op path and severity-change path remain covered and passing, proving the current gate avoids unnecessary large-result rerender pressure without breaking legitimate result updates.

### 2. Audit records the S04 optimization outcome from source

1. Run `make audit-m020`.
2. Run `python3 -m pytest -q tests/test_optimization_audit.py`.
3. Inspect `.gsd/milestones/M020/M020-AUDIT.md` if needed.
4. **Expected:** The audit regenerates from `tools/optimization_audit.py`, audit tests pass, and the generated artifact records the S04 measured virtualization deferment with evidence and rerun lanes.

### 3. Browser-visible analyst flow still works in mocked-online mode

1. Run `make verify-deep`.
2. Wait for the mocked-online browser/E2E lane to finish.
3. **Expected:** The E2E suite passes, confirming browser-visible result behavior remains intact after the optimization decision.

## Edge Cases

### Virtualization was intentionally not shipped

1. Verify no production TypeScript change was required for result application.
2. Confirm the audit explains the deferment rather than claiming a shipped virtualization rewrite.
3. **Expected:** The outcome is explicit: current severity-change gating is preserved, and virtualization remains deferred until measurement proves it can preserve filtering, sorting, copy/export, detail links, expansion state, and safe text rendering.

## Failure Signals

- The Vitest result-application suite fails, especially large-result no-op or severity-change behavior.
- `make audit-m020` changes or omits the S04 outcome unexpectedly.
- `tests/test_optimization_audit.py` fails audit-language or generated-artifact checks.
- `make verify-deep` fails in browser-visible mocked-online E2E coverage.

## Not Proven By This UAT

- Real external provider runtime behavior is not exercised.
- A future virtualization implementation is not proven safe; it remains deferred pending stronger preservation proof.
- Final milestone-wide `make verify` and full closeout are left for S05.

## Notes for Tester

This slice is a deliberate optimization rejection/deferment with evidence, not a missing implementation. Treat the generated audit and focused tests as the authoritative record of why the existing severity-change gate is currently preferable to a virtualization rewrite.
