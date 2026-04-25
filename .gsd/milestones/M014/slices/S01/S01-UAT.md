# S01: S01 — UAT

**Milestone:** M014
**Written:** 2026-04-25T10:19:21.225Z

# UAT — S01 Runtime state boundary hardening

## Preconditions
- Work from the SentinelX repo root.
- Python 3.10+, Node/npm, and the checked-in tools are available.
- No manual cleanup of `.planning/**` has been performed; the legacy backlog should still exist and remain visible.

## Test Case 1 — Representative path classification
1. Run:
   `python3 tools/runtime_state_boundary.py classify .gsd/milestones/M014/M014-ROADMAP.md .gsd/state-manifest.json .gsd/audit/events.jsonl .planning/STATE.md .bg-shell/manifest.json`
2. Verify the output classifies:
   - `.gsd/milestones/M014/M014-ROADMAP.md` as `durable`
   - `.gsd/state-manifest.json` as `transient`
   - `.gsd/audit/events.jsonl` as `transient`
   - `.planning/STATE.md` as `manual-review`
   - `.bg-shell/manifest.json` as `transient`

**Expected outcome:** The classifier shows the durable/transient/manual-review split exactly as documented, including the fail-closed legacy `.planning/**` behavior.

## Test Case 2 — Supported repo-native verifier
1. Run: `make verify-runtime-boundary`
2. Confirm both focused suites pass before the live audit output:
   - `tests/test_runtime_state_boundary.py`
   - `tests/test_runtime_state_boundary_git.py`
3. Inspect the audit section and verify it reports only `manual-review-path` findings from `.planning/**`.
4. Confirm the command exits successfully.

**Expected outcome:** The supported verifier passes because there are no blocker-class findings, but it still prints the manual-review backlog for operator visibility.

## Test Case 3 — Blocker-focused live audit contract
1. Run:
   `python3 tools/runtime_state_boundary.py audit --format text --fail-on-codes tracked-transient unignored-transient conflicting-rule-match unknown-root`
2. Verify the output includes `manual-review-path` findings for `.planning/**`.
3. Verify the command exits successfully.

**Expected outcome:** Legacy manual-review paths remain surfaced, but they do not fail the supported blocker-focused audit lane.

## Test Case 4 — Broader repo regression check
1. Run: `make verify-fast`
2. Wait for pytest, Vitest, TypeScript, and the production build to finish.

**Expected outcome:** The boundary hardening slice does not regress SentinelX's existing fast verification lane.

## Edge Cases
- If a future edit re-tracks a transient `.gsd`/`.bg-shell` file or stops ignoring one, Test Case 2 or 3 should fail with `tracked-transient` or `unignored-transient`.
- If someone widens the transient cleanup scope into `.planning/**`, Test Case 1 should stop classifying `.planning/STATE.md` as `manual-review`, which is a regression for this slice.
- If conflicting highest-priority classifier rules are introduced, the verifier should fail with `conflicting-rule-match` instead of silently choosing one rule.
