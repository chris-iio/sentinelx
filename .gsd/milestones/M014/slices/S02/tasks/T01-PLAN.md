---
estimated_steps: 4
estimated_files: 4
skills_used:
  - debug-like-expert
  - test
  - verify-before-complete
---

# T01: Implement classifier-backed repair CLI and safe action table

**Slice:** S02 — Recovery tooling and safe cleanup
**Milestone:** M014

## Description

Create the mutating repair surface on top of S01's inspection-only boundary tool. This task closes the highest-risk seam first: action selection must stay classifier-owned and conservative before any repo-native wrapper or live-repo usage exists.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| Shared helpers/constants from `tools/runtime_state_boundary.py` | Stop and expose the missing seam instead of copying glob rules into a second tool | N/A | Treat ambiguous classifications as blocked/manual-review, not as permission to mutate |
| Local Git CLI for tracked-transient repair | Fail loudly and preserve the working tree if `git rm --cached -- <path>` does not succeed | Keep operations local and bounded; no long-running commands expected | Report stderr and leave the finding unresolved rather than hiding the error |
| CLI/report contract for later automation | Exit non-zero on actionable failures and emit machine-readable output for later wrappers/docs | N/A | Reject unsupported flags/paths with clear usage text |

## Load Profile

- **Shared resources**: Git index state plus the classifier-owned boundary rule table.
- **Per-operation cost**: one audit plus bounded per-finding action selection; no directory-wide recursion or blanket deletes.
- **10x breakpoint**: accidental re-derivation of rules or broad filesystem mutation outside the audited findings.

## Negative Tests

- **Malformed inputs**: unsupported roots, empty path lists, dry-run invocations, and repeated runs with nothing actionable.
- **Error paths**: `git rm --cached` failures, conflicting/manual-review findings, and unknown-root findings that must stay blocked.
- **Boundary conditions**: tracked transient files that are already ignored, findings that mix actionable and blocked paths, and a clean repo with zero actionable repairs.

## Steps

1. Add `tools/runtime_state_repair.py` that imports `audit_paths`, normalization helpers, and issue-code constants from `tools/runtime_state_boundary.py` and maps each finding to an explicit action.
2. Implement conservative CLI/report behavior with `--repo-root`, `--format`, and `--dry-run`, keeping `tracked-transient` as the only mutating action in this task.
3. Add focused pytest coverage in `tests/test_runtime_state_repair.py` for action planning, dry-run summaries, tracked-transient deindex behavior, and report-only handling of manual-review/conflicting/unknown findings.
4. Expose only the minimal shared helper seams needed from `tools/runtime_state_boundary.py`; keep `audit` itself inspection-only.

## Must-Haves

- [ ] Only classifier findings drive repair actions; no second rule table appears.
- [ ] `tracked-transient` repair uses `git rm --cached -- <path>` and preserves working-tree contents.
- [ ] `manual-review-path`, `conflicting-rule-match`, and `unknown-root` remain report-only blockers.
- [ ] The CLI supports dry-run plus text/JSON output for later wiring and diagnostics.

## Verification

- `python3 -m pytest -q tests/test_runtime_state_repair.py`
- `python3 tools/runtime_state_repair.py --help`

## Observability Impact

- Signals added/changed: repair summaries expose per-issue action counts plus dry-run/apply mode.
- How a future agent inspects this: `python3 tools/runtime_state_repair.py --format text|json` and `python3 -m pytest -q tests/test_runtime_state_repair.py`.
- Failure state exposed: blocked findings, Git stderr, and no-op status are explicit in CLI output.

## Inputs

- `tools/runtime_state_boundary.py` — authoritative classifier, issue codes, and audit helpers to reuse instead of copying rules.
- `tests/test_runtime_state_boundary.py` — examples of representative classifications and CLI behavior that the repair tool must preserve.
- `tests/test_runtime_state_boundary_git.py` — real Git fixture patterns that later repair integration tests should mirror.
- `.gitignore` — current ignored transient subtree definitions, including `.gsd/runtime/` where quarantine will later live.

## Expected Output

- `tools/runtime_state_repair.py` — the new classifier-backed repair CLI.
- `tests/test_runtime_state_repair.py` — focused unit coverage for action selection, dry-run, and blocked/manual behavior.
- `tools/runtime_state_boundary.py` — only if a minimal shared helper export is needed to support import-safe repair logic.
