---
estimated_steps: 52
estimated_files: 2
skills_used: []
---

# T03: Run full verification lanes and finalize R089 handoff

---
estimated_steps: 7
estimated_files: 2
skills_used:
  - test
  - verify-before-complete
---

# T03: Run full verification lanes and finalize R089 handoff

**Slice:** S05 — Final Integrated Proof + Durable Handoff
**Milestone:** M017

## Description

Run the final repo-native verification lanes required by R089, then finalize the closeout proof with the fresh `make verify-fast` and `make verify-deep` outcomes. This is the final assembly step: it does not add new feature behavior, but proves the real integrated entrypoints still work after M017 project-map and optimization work.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `make verify-fast` | Capture failing subcommand and stop before deep lane unless the failure is a known transient with clear fix | Record timeout as failure; do not claim R089 | Treat missing/unknown target output as Makefile contract failure |
| `make verify-deep` | Capture failing subcommand, browser/e2e failure, or diagnostics failure and leave R089 unsatisfied | Record timeout as failure with last visible output | Treat truncated or contradictory output as inconclusive and rerun the narrow failing lane only for diagnosis |

## Load Profile

- **Shared resources**: local app runtime, browser e2e fixtures, Python/Node test processes, filesystem caches.
- **Per-operation cost**: one fast verification lane plus one deep verification lane, including browser e2e coverage.
- **10x breakpoint**: browser test runtime and local CPU/IO; do not parallelize beyond the Makefile defaults unless the Makefile already does.

## Negative Tests

- **Malformed inputs**: Make targets must exist and produce machine-observable exit codes.
- **Error paths**: Deep lane must include existing diagnostics/redaction/security behavior coverage; failures are blockers, not warnings.
- **Boundary conditions**: If only a narrow flaky browser test fails, record it precisely and rerun that narrow test for diagnosis, but the final closeout still requires a clean deep lane.

## Steps

1. Run `make verify-fast`.
2. If fast verification fails, update `docs/m017-closeout-proof.md` with the failing command summary and stop for diagnosis.
3. Run `make verify-deep` only after the fast lane passes.
4. If deep verification fails, update the proof artifact with the failing command summary and stop for diagnosis; do not mark R089 satisfied.
5. If both pass, update `docs/m017-closeout-proof.md` with exact command strings, exit status, date/time, and concise pass-count highlights from the current output.
6. Finalize the handoff section with what future agents should rerun, what files hold the durable project/audit proof, and a statement that no S05 product-code wiring was introduced.
7. Re-run simple artifact assertions to ensure final edits did not remove requirement coverage or command evidence.

## Must-Haves

- [ ] `make verify-fast` exits 0.
- [ ] `make verify-deep` exits 0.
- [ ] `docs/m017-closeout-proof.md` records both full-lane outcomes and marks R089 evidence as satisfied only if both commands passed.
- [ ] The final artifact lists rerunnable commands and relevant proof files for handoff.

## Verification

- `make verify-fast`
- `make verify-deep`
- `grep -Ei "make verify-fast|make verify-deep|R089" docs/m017-closeout-proof.md`
- `test -s docs/m017-closeout-proof.md`

## Observability Impact

- Signals added/changed: no production signals; final closeout captures the integrated verification state.
- How a future agent inspects this: read `docs/m017-closeout-proof.md`, then rerun `make verify-fast` and `make verify-deep`.
- Failure state exposed: failed Make target/subcommand and last relevant failure output should be summarized in the artifact.

## Inputs

- `docs/m017-closeout-proof.md` — proof artifact updated by T02 and finalized with full-lane evidence.
- `Makefile` — defines `verify-fast` and `verify-deep` entrypoints.

## Expected Output

- `docs/m017-closeout-proof.md` — finalized with fresh full verification evidence and durable handoff notes.

## Inputs

- `docs/m017-closeout-proof.md`
- `Makefile`

## Expected Output

- `docs/m017-closeout-proof.md`

## Verification

make verify-fast && make verify-deep && grep -Ei "make verify-fast|make verify-deep|R089" docs/m017-closeout-proof.md && test -s docs/m017-closeout-proof.md

## Observability Impact

No product observability change. The finalized proof artifact becomes the durable inspection surface for M017 final verification and rerun instructions.
