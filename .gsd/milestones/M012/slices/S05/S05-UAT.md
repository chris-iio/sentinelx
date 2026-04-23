# S05: Validation evidence closure — UAT

**Milestone:** M012
**Written:** 2026-04-22T17:38:35.322Z

# UAT: M012 validation evidence closure

## Preconditions
- Repository is at the completed `M012/S05` state.
- The canonical task outputs already exist in `.gsd/milestones/M012/slices/S05/tasks/`.
- Python/Node dependencies are installed so the focused pytest suites and `make verify-fast` can run.

## Test Case 1 — Slice assessment coverage exists through the canonical artifact path
1. Run:
   - `test -s .gsd/milestones/M012/slices/S01/S01-ASSESSMENT.md`
   - `test -s .gsd/milestones/M012/slices/S02/S02-ASSESSMENT.md`
   - `test -s .gsd/milestones/M012/slices/S03/S03-ASSESSMENT.md`
2. Open each assessment file and confirm it names:
   - the seam proved by that slice,
   - the downstream slice(s) that consumed it,
   - a roadmap-confirmed verdict with no extra reassessment required before S05.

**Expected outcome:** all three files exist, are non-empty, and explicitly connect S01 terminal-status continuity, S02 live/history parity, and S03 fast/deep verification-lane proof to downstream M012 work.

## Test Case 2 — Focused continuity proof is still green at closeout time
1. Run `python3 -m pytest tests/test_orchestrator.py tests/test_api.py tests/test_routes.py tests/test_http_safety.py tests/test_adapter_contract.py -q`.
2. Run `python3 -m pytest tests/test_cache_store.py tests/test_history_store.py tests/test_history_routes.py tests/test_settings.py -q`.
3. Run `make verify-fast`.

**Expected outcome:**
- backend/security/adapter proof passes (`266 passed`),
- persistence/helper proof passes (`73 passed`),
- `make verify-fast` passes with non-E2E pytest, Vitest, TypeScript, and build all green.

## Test Case 3 — Milestone validation artifact truthfully captures the remaining blocker
1. Open `.gsd/milestones/M012/M012-VALIDATION.md`.
2. Confirm the **Slice Delivery Audit** has entries for `S01` through `S05`.
3. Confirm **Requirement Coverage** explicitly addresses `R008`, `R009`, `R010`, `R014`, `R015`, `R018`, `R019`, `R020`, `R022`, and `R040`.
4. Confirm the verdict is `needs-remediation`, not `pass`.
5. Confirm the remediation plan explains that `R040` is cited by M012 planning/context/summaries but has no canonical row in `.gsd/REQUIREMENTS.md`.

**Expected outcome:** the validation artifact exists, cites current proof surfaces, and makes the remaining blocker explicit instead of hiding it in milestone-closeout prose.

## Edge Case — Ledger reconciliation path
1. Add or reconcile the missing canonical `R040` requirement row through the requirements toolchain.
2. Re-run milestone validation.

**Expected outcome:** if the requirement ledger is restored and the same focused proof remains green, the milestone can be re-validated without reopening shipped product-code slices.
