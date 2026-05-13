# S05: Final Integrated Proof + Durable Handoff — UAT

**Milestone:** M017
**Written:** 2026-05-13T18:11:05.839Z

# S05: Final Integrated Proof + Durable Handoff — UAT

**Milestone:** M017
**Written:** 2026-05-13

## UAT Type

- UAT mode: artifact-driven with live-runtime automated verification
- Why this mode is sufficient: S05 is a final assembly and proof slice. Its user-visible outcome is the durable closeout artifact plus passing repository verification lanes, and `make verify-deep` exercises the mocked-online browser/runtime e2e lane.

## Preconditions

- Repository dependencies are installed.
- The working tree contains the completed S01-S04 M017 artifacts and code changes.
- Test environment supports the repo-native Node, Python, and browser/e2e test lanes used by `make verify-fast` and `make verify-deep`.

## Smoke Test

1. Open `docs/m017-closeout-proof.md`.
2. Confirm it references R084, R087, R088, and R089.
3. Confirm it includes the S03 incremental polling/status proof, the S04 result-application severity-gate proof, and final `make verify-fast` / `make verify-deep` evidence.
4. **Expected:** The document gives a future agent a single non-GSD artifact explaining why M017 is clearer and defensibly optimized.

## Test Cases

### 1. Closeout artifact covers all required proof areas

1. Run `test -s docs/m017-closeout-proof.md`.
2. Run greps for `R084|R087|R088|R089`, `incremental|polling|status`, `severity|result-application|recount|reorder`, and `make verify-fast|make verify-deep|R089`.
3. **Expected:** All assertions pass, proving the artifact is present and contains the required requirement and optimization evidence.

### 2. Focused closeout regressions pass

1. Run `npm test -- --run`.
2. Run `python3 -m pytest -q tests/test_optimization_audit.py tests/e2e/test_results_page.py tests/e2e/test_emailrep_online.py`.
3. **Expected:** Frontend tests and focused audit/results/EmailRep pytest lanes exit 0.

### 3. Full verification lanes pass

1. Run `make verify-fast`.
2. Run `make verify-deep`.
3. **Expected:** Fast verification exits 0, and deep e2e/browser verification exits 0 with the expected e2e suite passing.

## Edge Cases

### Generated GSD artifacts are not the only source of truth

1. Inspect `docs/m017-closeout-proof.md` without opening `.gsd/` summaries.
2. **Expected:** The proof remains understandable to a future agent as a durable docs artifact, while GSD summaries point back to it.

### No new optimization code in final assembly

1. Compare the slice plan with the files modified by S05.
2. **Expected:** S05 only updates closeout/requirement evidence and does not introduce new production optimization code unless verification had exposed a blocker.

## Failure Signals

- `docs/m017-closeout-proof.md` is missing, empty, or lacks R084/R087/R088/R089 coverage.
- The proof artifact omits either the S03 incremental polling/status outcome or the S04 result-application severity-gate outcome.
- `npm test -- --run`, focused pytest, `make verify-fast`, or `make verify-deep` exits non-zero.
- R089 remains unvalidated after final full-lane verification.

## Not Proven By This UAT

- It does not add new product functionality or new production observability surfaces.
- It does not prove live third-party service behavior beyond the repository's mocked-online/runtime e2e coverage.
- It does not replace future regression testing for post-M017 changes.

## Notes for Tester

This UAT is intentionally evidence- and automation-driven. Human exploratory testing is not required for S05 because the slice goal is final integrated proof and durable handoff, not a new analyst-facing interaction.
