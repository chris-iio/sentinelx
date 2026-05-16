# S02: Highest-Risk Rewrite Target — UAT

**Milestone:** M020
**Written:** 2026-05-16T08:45:34.274Z

# S02: Highest-Risk Rewrite Target — UAT

**Milestone:** M020
**Written:** 2026-05-16

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S02 is a backend/refactor proof slice with no new live-provider dependency or analyst-facing UI flow; the required evidence is generated audit content plus Flask/test-client route execution and fast verification lanes.

## Preconditions

- Worktree contains the completed S02 task outputs.
- Python test dependencies and Node/build dependencies are installed as expected by the project.
- No live enrichment provider credentials are required; tests use local/test-client execution.

## Smoke Test

Run `make verify-fast` from the project root. Expected: command exits 0 and completes the fast verification lane without route, audit, or asset-build failures.

## Test Cases

### 1. Focused route/API/history contracts remain stable

1. Run `python3 -m pytest -q tests/test_routes.py tests/test_api.py tests/test_history_routes.py`.
2. Confirm analysis route rendering still exposes grouped IOC template context.
3. Confirm API responses still serialize the expected IOC grouping/payload shape.
4. Confirm history replay still reconstructs grouping behavior, including empty and negative paths.
5. **Expected:** 130 tests pass; no online-admission, missing-provider, diagnostics, grouping, or history replay regressions appear.

### 2. Generated audit records the S02 shipped outcome

1. Run `python3 -m pytest -q tests/test_optimization_audit.py`.
2. Inspect `.gsd/milestones/M020/M020-AUDIT.md` if needed.
3. **Expected:** audit tests pass and the generated audit records the route IOC helper rewrite as shipped with proof requirements, focused route verification, failure-visibility, and redaction guardrail language.

### 3. Fast implementation lane passes

1. Run `make verify-fast`.
2. **Expected:** command exits 0, covering the project’s fast verification path and asset build checks.

## Edge Cases

### Empty or negative route paths

1. Run the focused route/API/history pytest command.
2. **Expected:** tests covering empty input, no-provider redirects/paths, and history replay safety pass without hidden exceptions or changed response shapes.

### Compatibility seam remains intact

1. Review `app/routes/analysis.py`, `app/routes/api.py`, and `app/routes/history.py` imports if a future refactor touches helper symbols.
2. **Expected:** route modules may expose helper imports as compatibility/test seams while `_helpers.py` remains the implementation owner; removing those imports requires updating public regressions deliberately.

## Failure Signals

- Focused route/API/history tests fail, especially grouped IOC rendering, serialized API payload shape, history replay grouping, or empty/no-provider cases.
- Audit tests fail or generated M020 audit no longer records the S02 outcome and proof language.
- `make verify-fast` fails in tests or asset build steps.
- Generated audit drops failure-state visibility or redaction guardrails for the helper rewrite.

## Not Proven By This UAT

- Full M020 end-to-end analyst loop; that remains for later slices and final `make verify` in S05.
- Live provider behavior or browser-visible performance improvements; S02 intentionally avoided live providers and browser runtime because the target was route/helper centralization.
- The second cross-seam target and analyst-visible optimization target planned for S03 and S04.

## Notes for Tester

This slice may look like a small code delta because the desired helper extraction was already present. The shipped outcome is the combination of confirmed centralized ownership, compatibility-seam preservation, new focused regressions, and generated audit documentation that records why no additional production rewrite was needed.
