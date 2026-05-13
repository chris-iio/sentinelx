---
estimated_steps: 55
estimated_files: 6
skills_used: []
---

# T02: Run focused closeout regression and fill evidence

---
estimated_steps: 7
estimated_files: 6
skills_used:
  - test
  - verify-before-complete
---

# T02: Run focused closeout regression and fill evidence

**Slice:** S05 — Final Integrated Proof + Durable Handoff
**Milestone:** M017

## Description

Run the focused closeout lanes that directly protect the shipped M017 optimization claims, then update `docs/m017-closeout-proof.md` with the real command outcomes. This task proves the audit generator still records shipped S03/S04 outcomes and that the browser-visible results/EmailRep analyst paths still pass after the frontend render behavior touched in S04.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| Vitest/npm test lane | Capture failing test names and stop; do not continue to broad proof as if frontend is healthy | Re-run once only if infrastructure appears hung; otherwise record timeout | Treat invalid test output as failure and inspect package/test config |
| Pytest focused e2e/audit lane | Capture failing node/test and stop before declaring closeout | Re-run only a narrowed failing test if needed for diagnosis | Treat fixture or mocked-online setup errors as blockers |

## Load Profile

- **Shared resources**: local test browser/runtime fixtures, npm/Vitest process, pytest workers if configured.
- **Per-operation cost**: one frontend test run plus focused audit/results/EmailRep pytest suites.
- **10x breakpoint**: browser fixture startup time and local CPU are the likely bottlenecks, not app data size.

## Negative Tests

- **Malformed inputs**: Audit tests must reject stale unresolved S04 target language and require shipped severity-gate proof.
- **Error paths**: Focused e2e must preserve mocked-online behavior without external provider calls.
- **Boundary conditions**: Results/history/detail and provider-only render deltas remain covered by existing focused tests rather than new brittle timing assertions.

## Steps

1. Run `npm test -- --run` from the repo root.
2. Run `python3 -m pytest -q tests/test_optimization_audit.py tests/e2e/test_results_page.py tests/e2e/test_emailrep_online.py`.
3. If either command fails, capture the failure in `docs/m017-closeout-proof.md` and stop for diagnosis; do not mark S05 complete.
4. If both pass, update the proof artifact with the exact command strings, pass/fail status, and useful pass-count summary from the current run.
5. Confirm the artifact still references R087/R088 and both S03/S04 optimization themes after the evidence update.
6. Do not edit generated `.gsd` audit or requirement files unless the focused tests reveal the generator itself is wrong; if that occurs, fix source generator/tests and regenerate through the established command path.
7. Keep secret/provider data out of the evidence; mocked-online proof should not require external credentials.

## Must-Haves

- [ ] `npm test -- --run` exits 0.
- [ ] Focused audit/results/EmailRep pytest command exits 0.
- [ ] `docs/m017-closeout-proof.md` records the fresh focused command outcomes.
- [ ] No external provider credentials or secrets appear in the proof artifact.

## Verification

- `npm test -- --run`
- `python3 -m pytest -q tests/test_optimization_audit.py tests/e2e/test_results_page.py tests/e2e/test_emailrep_online.py`
- `grep -Ei "npm test -- --run|tests/test_optimization_audit.py|test_results_page.py|test_emailrep_online.py" docs/m017-closeout-proof.md`

## Observability Impact

- Signals added/changed: no runtime signals; closeout evidence captures focused regression command outcomes.
- How a future agent inspects this: read `docs/m017-closeout-proof.md` and rerun the listed commands.
- Failure state exposed: failing command, failing suite, and summary should be recorded in the artifact if verification fails.

## Inputs

- `docs/m017-closeout-proof.md` — proof artifact created by T01 and updated with focused evidence.
- `package.json` — defines the npm/Vitest test command.
- `tools/optimization_audit.py` — generator source under audit regression.
- `tests/test_optimization_audit.py` — audit proof regression tests.
- `tests/e2e/test_results_page.py` — browser-visible results/history/detail regression tests.
- `tests/e2e/test_emailrep_online.py` — mocked-online EmailRep analyst-flow regression tests.

## Expected Output

- `docs/m017-closeout-proof.md` — updated with fresh focused regression evidence.

## Inputs

- `docs/m017-closeout-proof.md`
- `package.json`
- `tools/optimization_audit.py`
- `tests/test_optimization_audit.py`
- `tests/e2e/test_results_page.py`
- `tests/e2e/test_emailrep_online.py`

## Expected Output

- `docs/m017-closeout-proof.md`

## Verification

npm test -- --run && python3 -m pytest -q tests/test_optimization_audit.py tests/e2e/test_results_page.py tests/e2e/test_emailrep_online.py && grep -Ei "npm test -- --run|tests/test_optimization_audit.py|test_results_page.py|test_emailrep_online.py" docs/m017-closeout-proof.md

## Observability Impact

No production observability change. This task preserves failure visibility by recording current focused regression outcomes and the exact rerunnable commands in the closeout proof artifact.
