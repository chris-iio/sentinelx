# S02: Identity-Grounded Optimization Audit — UAT

**Milestone:** M017
**Written:** 2026-05-13T08:20:03.760Z

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S02 is a planning/audit workflow slice. Its user-visible output is the generated M017 audit artifact and its executable regeneration contract, not live runtime behavior.

## Preconditions

- Work from the repository root.
- `docs/project-map.md` exists from S01.
- Python test dependencies are available.

## Smoke Test

Run `python3 tools/optimization_audit.py --mode baseline --milestone-id M017 --output .gsd/milestones/M017/M017-AUDIT.md` and confirm `.gsd/milestones/M017/M017-AUDIT.md` exists, is non-empty, and references `docs/project-map.md`.

## Test Cases

### 1. Focused audit contract tests

1. Run `python3 -m pytest -q tests/test_optimization_audit.py`.
2. **Expected:** The suite passes with 9 tests and no failures.

### 2. M017 artifact regeneration

1. Run `python3 tools/optimization_audit.py --mode baseline --milestone-id M017 --output .gsd/milestones/M017/M017-AUDIT.md`.
2. Open the generated audit artifact.
3. **Expected:** It includes the M017 identity-grounded contract, references `docs/project-map.md`, and contains ranked headings for `### do now`, `### do next`, `### later`, and `### leave alone`.

### 3. S03 handoff usability

1. Inspect the generated artifact’s do-now section.
2. Verify it names S03 and the enrichment fan-out/status snapshot path as the current do-now target.
3. Verify concrete seam markers include `app/enrichment`, `app/routes`, and `app/pipeline`.
4. **Expected:** S03 can start from the artifact without reinterpreting SentinelX’s product identity or optimization priorities.

### 4. Placeholder guard

1. Search the generated artifact for `TBD`, `TODO`, and `_Fill during`.
2. **Expected:** No unresolved placeholder text is present.

## Edge Cases

- If `docs/project-map.md` is missing, the runner should not silently claim full identity grounding; tests cover this behavior.
- If an optional capture command fails, artifact generation remains inspectable and records the nonzero capture result instead of hiding the failure.

## Not Proven By This UAT

- No production optimization has shipped yet; S03 must implement the selected target with measurement or explicit code-path proof.
- Full `make verify-fast` and `make verify-deep` are reserved for later integrated milestone proof unless a code-changing optimization touches those runtime surfaces.
