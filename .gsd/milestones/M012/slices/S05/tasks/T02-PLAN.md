---
estimated_steps: 5
estimated_files: 10
skills_used:
  - test
  - write-docs
  - verify-before-complete
---

# T02: Re-run the focused continuity proof and render the canonical milestone validation artifact

Turn the already-shipped M012 work into a validation artifact a fresh reviewer can trust. Use `.gsd/REQUIREMENTS.md` as the proof index for continuity requirements, the `S01`–`S04` summaries plus the new `S01`–`S03` assessment files as the slice evidence spine, and fresh focused command output as the current-message proof. The canonical write path is `gsd_validate_milestone`; do not hand-write `.gsd/milestones/M012/M012-VALIDATION.md`. If any focused check fails or a continuity requirement cannot be honestly justified, do **not** force a `pass` verdict — either repair the evidence gap first or issue `needs-remediation` with a concrete remediation plan.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| Focused pytest suites and `make verify-fast` | Stop and treat the milestone verdict as blocked until the failing proof surface is understood; do not cite stale success from older slices as a replacement for a current failure | Re-run only the stalled command or a smaller focused subset; do not silently skip the proof class | Treat unexpected output or missing test collection as a failed proof surface that must be explained before validation |
| `.gsd/REQUIREMENTS.md` and slice summary/assessment artifacts | Reconcile the ledger row and slice evidence explicitly in the validation prose; do not leave contradictions implicit | N/A | Missing or inconsistent requirement text is grounds for `needs-remediation`, not hand-wavy pass language |
| `gsd_validate_milestone` | Retry only after fixing the payload/evidence problem; the task is not done until the tool writes `.gsd/milestones/M012/M012-VALIDATION.md` | N/A | If the generated artifact is incomplete or the tool rejects the payload, fix the source evidence or payload structure before claiming closure |

## Load Profile

- **Shared resources**: local pytest/build environment, repository build outputs, and the milestone validation DB/file render path.
- **Per-operation cost**: two focused pytest invocations plus `make verify-fast`, followed by one `gsd_validate_milestone` write.
- **10x breakpoint**: unnecessary escalation to the full deep lane; keep proof focused unless the fresh evidence shows a browser-facing regression or the verdict cannot honestly rely on S03's already-fresh deep-lane evidence.

## Negative Tests

- **Malformed inputs**: missing `S01`–`S03` assessment files, stale requirement references, or validation prose that cites a requirement without a concrete file/command anchor.
- **Error paths**: any failing focused pytest subset, `make verify-fast` failure, or `gsd_validate_milestone` rejection must block a `pass` verdict.
- **Boundary conditions**: `R020` and `R022` may be justified by current code + focused tests without product edits, and browser/deep-lane proof may be cited from `S03` unless fresh evidence forces escalation.

## Steps

1. Re-read `.gsd/REQUIREMENTS.md`, `.gsd/milestones/M012/M012-ROADMAP.md`, `.gsd/milestones/M012/M012-CONTEXT.md`, `.gsd/milestones/M012/slices/S01/S01-SUMMARY.md`, `.gsd/milestones/M012/slices/S02/S02-SUMMARY.md`, `.gsd/milestones/M012/slices/S03/S03-SUMMARY.md`, `.gsd/milestones/M012/slices/S04/S04-SUMMARY.md`, `.gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md`, and the new `S01`–`S03` assessment files to map each success criterion and continuity requirement to a concrete proof surface.
2. Run `python3 -m pytest tests/test_orchestrator.py tests/test_api.py tests/test_routes.py tests/test_http_safety.py tests/test_adapter_contract.py -q` to refresh proof for `R009`, `R014`, `R015`, `R018`, `R019`, and `R020` using the current canonical backend/security/adaptor surfaces.
3. Run `python3 -m pytest tests/test_cache_store.py tests/test_history_store.py tests/test_history_routes.py tests/test_settings.py -q` and then `make verify-fast` to refresh `R022`/`R040` plus the broader non-E2E safety net; only escalate to `make verify-deep` if a fresh browser-facing concern appears or the milestone verdict cannot honestly rely on `S03`'s existing deep-lane evidence.
4. Draft the validation payload with explicit `successCriteriaChecklist`, `sliceDeliveryAudit`, `crossSliceIntegration`, `requirementCoverage`, `verificationClasses`, and `verdictRationale`, citing file paths and command output rather than generic milestone prose.
5. Call `gsd_validate_milestone` for `M012` and verify `.gsd/milestones/M012/M012-VALIDATION.md` exists and reflects the truthful verdict.

## Must-Haves

- [ ] The validation writeup explicitly covers `R008`, `R009`, `R010`, `R014`, `R015`, `R018`, `R019`, `R020`, `R022`, and `R040` using the requirement ledger plus current focused proof.
- [ ] The slice delivery audit accounts for `S01` through `S05`, including the newly created assessment artifacts and S04's keep/change conclusion.
- [ ] The verdict is produced by `gsd_validate_milestone`, not by manually editing `.gsd/milestones/M012/M012-VALIDATION.md`.
- [ ] Any uncovered gap becomes explicit remediation or a blocked verdict instead of being hidden behind milestone-closeout prose.

## Inputs

- `.gsd/REQUIREMENTS.md`
- `.gsd/milestones/M012/M012-ROADMAP.md`
- `.gsd/milestones/M012/M012-CONTEXT.md`
- `.gsd/milestones/M012/slices/S01/S01-SUMMARY.md`
- `.gsd/milestones/M012/slices/S01/S01-ASSESSMENT.md`
- `.gsd/milestones/M012/slices/S02/S02-SUMMARY.md`
- `.gsd/milestones/M012/slices/S02/S02-ASSESSMENT.md`
- `.gsd/milestones/M012/slices/S03/S03-SUMMARY.md`
- `.gsd/milestones/M012/slices/S03/S03-ASSESSMENT.md`
- `.gsd/milestones/M012/slices/S04/S04-SUMMARY.md`
- `.gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md`
- `tests/test_orchestrator.py`
- `tests/test_api.py`
- `tests/test_routes.py`
- `tests/test_http_safety.py`
- `tests/test_adapter_contract.py`
- `tests/test_cache_store.py`
- `tests/test_history_store.py`
- `tests/test_history_routes.py`
- `tests/test_settings.py`
- `Makefile`

## Expected Output

- `.gsd/milestones/M012/M012-VALIDATION.md`

## Verification

python3 -m pytest tests/test_orchestrator.py tests/test_api.py tests/test_routes.py tests/test_http_safety.py tests/test_adapter_contract.py -q && python3 -m pytest tests/test_cache_store.py tests/test_history_store.py tests/test_history_routes.py tests/test_settings.py -q && make verify-fast && test -s .gsd/milestones/M012/M012-VALIDATION.md
