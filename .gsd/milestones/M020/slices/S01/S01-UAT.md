# S01: M020 Audit Expansion — UAT

**Milestone:** M020
**Written:** 2026-05-16T08:37:24.334Z

# S01: M020 Audit Expansion — UAT

**Milestone:** M020
**Written:** 2026-05-16

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S01 ships a generated audit artifact and command/test contract, not live runtime behavior; artifact generation, contract tests, and inspection prove the slice goal.

## Preconditions

- Repository is checked out in `/home/chris/projects/sentinelx`.
- Python test dependencies and Make targets are available in the local environment.
- No server, seeded data, provider credentials, or analyst IOC payloads are required.

## Smoke Test

Run `make audit-m020` and confirm `.gsd/milestones/M020/M020-AUDIT.md` is regenerated successfully.

## Test Cases

### 1. Generate the M020 audit artifact

1. Run `make audit-m020`.
2. Open or inspect `.gsd/milestones/M020/M020-AUDIT.md`.
3. **Expected:** The artifact exists, is produced by `tools/optimization_audit.py`, references M020, and contains the M020 audit command surface rather than placeholder prose.

### 2. Verify the focused audit contract

1. Run `python3 -m pytest -q tests/test_optimization_audit.py`.
2. **Expected:** The optimization audit test suite passes, including M020 template and baseline contract coverage.

### 3. Confirm ranked downstream inputs

1. Inspect `.gsd/milestones/M020/M020-AUDIT.md` for `do-now`, `do-next`, `later`, and `leave-alone` outcomes.
2. Inspect the same artifact for proof requirements and verification lanes tied to downstream rewrite work.
3. **Expected:** All four buckets are present and the artifact gives S02-S05 enough evidence and proof requirements to consume the ranked candidates.

### 4. Confirm repository fast verification still passes

1. Run `make verify-fast`.
2. **Expected:** The fast verification lane passes after audit generation.

## Edge Cases

### Capture-command failure visibility

1. Review the focused tests covering failed capture commands in `tests/test_optimization_audit.py`.
2. **Expected:** Capture-command failures remain visible as nonzero capture rows instead of being hidden or causing artifact generation to silently omit evidence.

### Milestone-local output selection

1. Run or inspect the M020 audit tests for default output selection.
2. **Expected:** M020 default output resolves to `.gsd/milestones/M020/M020-AUDIT.md`, not an M013/M017 or generic audit path.

## Failure Signals

- `make audit-m020` exits nonzero.
- `.gsd/milestones/M020/M020-AUDIT.md` is missing or contains unresolved placeholders.
- The artifact lacks any of the four ranked buckets: do-now, do-next, later, leave-alone.
- The artifact does not reference proof requirements, verification lanes, or docs/project-map.md grounding.
- `python3 -m pytest -q tests/test_optimization_audit.py` fails.
- `make verify-fast` fails.

## Not Proven By This UAT

- It does not prove any aggressive rewrite has been shipped or rejected; that begins in S02.
- It does not prove live analyst IOC triage behavior end-to-end; later slices and final closeout cover runtime/browser-facing preservation.
- It does not prove final M020 outcome documentation is complete; S02-S05 must update the generated audit/closeout artifacts as rewrite decisions are made.

## Notes for Tester

Treat `.gsd/milestones/M020/M020-AUDIT.md` as generated output. If content is stale or questionable, regenerate through `make audit-m020`; do not hand-edit the artifact.
