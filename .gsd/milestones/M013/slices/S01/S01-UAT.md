# S01: S01 — UAT

**Milestone:** M013
**Written:** 2026-04-24T01:03:29.971Z

# S01 UAT — Reusable optimization audit workflow and baseline ranked pass

## Preconditions

1. Work from the repo root with project Python and Node dependencies installed.
2. Ensure `make`, `python3`, and the browser test dependencies used by `make verify-deep` are available.
3. Remove any assumption that the audit artifact is hand-maintained; this UAT treats `tools/optimization_audit.py` as the source of truth.
4. Start from the current M013 worktree so `.gsd/milestones/M013/` is writable.

## Test Case 1 — Discover the workflow entrypoints

1. Run `python3 tools/optimization_audit.py --help`.
   - Expected: Help text lists both `template` and `baseline` modes.
   - Expected: Help text shows `--capture-command LABEL::COMMAND` so later slices can attach measured proof to the artifact.
2. Run `make audit-m013-template`.
   - Expected: `.gsd/milestones/M013/M013-AUDIT-TEMPLATE.md` is created or refreshed.
   - Expected: The template contains the fixed ranked buckets `do now`, `do next`, `later`, and `leave alone`.

## Test Case 2 — Generate the baseline audit artifact

1. Run `python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md`.
   - Expected: The command exits successfully and rewrites `.gsd/milestones/M013/M013-AUDIT.md`.
2. Open `.gsd/milestones/M013/M013-AUDIT.md`.
   - Expected: The artifact includes the sections `Workflow contract`, `Command surface`, `Verification lanes`, `Verified rerun checklist`, `Continuity guardrails`, and `Ranked findings`.
   - Expected: Ranked findings are populated, not blank.
   - Expected: The `do now` row names the request/status cursor-native optimization and the `leave alone` rows keep WAL persistence and provider backoff/session behavior explicit.

## Test Case 3 — Prove verification captures are part of the artifact contract

1. Run:
   `python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md --capture-command 'verify-fast::make verify-fast' --capture-command 'verify-deep::make verify-deep'`
   - Expected: The command exits successfully after both proof lanes complete.
2. Re-open `.gsd/milestones/M013/M013-AUDIT.md`.
   - Expected: The `Measurement captures` table includes rows for `verify-fast` and `verify-deep` with exit code `0`.
   - Expected: The `Verified rerun checklist` explicitly says `make verify-deep` is required for live enrichment orchestration, polling/status flow, shared result application, or analyst-visible DOM/state changes.

## Test Case 4 — Confirm the docs explain the downstream contract

1. Open `docs/optimization-audit.md` and `README.md`.
   - Expected: Both document the audit runner and repo-native entrypoints.
   - Expected: The docs explain the evidence rule: measurement when practical, code-path reasoning otherwise.
   - Expected: The docs distinguish between the reusable template artifact and the populated M013 baseline artifact.

## Test Case 5 — Keep the deep proof deterministic instead of weakening it

1. Run `python3 -m pytest -q tests/e2e/test_settings.py::test_cache_section_visible[chromium] tests/test_optimization_audit.py`.
   - Expected: The targeted pytest command passes.
2. Review the settings-page assertions in the page object/test.
   - Expected: The test anchors to the `Cache` and `History Save Diagnostics` headings instead of relying on one duplicated utility-class selector.
   - Expected: The deep proof stays strict while remaining deterministic.

## Edge Cases

- If a future slice adds `--capture-command` entries and one command fails, the artifact should still be written but the runner must exit non-zero so the slice cannot claim completion on partial proof.
- `leave alone` rows are valid output, not placeholders; removing them or leaving a seam unranked fails the audit contract.
- Any live-stack change that touches polling, result application, or analyst-visible DOM/state must refresh the artifact and rerun `make verify-deep`, not just `make verify-fast`.
- If later measurements overturn the current ranking, the existing row should be updated in place inside `.gsd/milestones/M013/M013-AUDIT.md` rather than creating disconnected side notes.
