---
estimated_steps: 13
estimated_files: 1
skills_used: []
---

# T03: Produce milestone validation evidence for Email Reputation Depth

Expected executor skills: `verify-before-complete`, `write-docs`.

Why: the failed auto-mode gate reported `.gsd/milestones/M016/M016-VALIDATION.md` missing. After T01/T02, S05 must leave a canonical validation artifact instead of relying on conversational claims.

Do:
1. Assemble validation evidence from S01-S04 summaries, the reconciled M016 context, R008/R009/R011/R083 requirement status, D075/D076, and the fresh T02 verification output.
2. Use the DB-backed GSD validation path (`gsd_validate_milestone`) rather than hand-writing `M016-VALIDATION.md` when the tool is available. If the tool requires all slices to be complete, complete S05 tasks/slice first through the normal GSD flow, then run validation immediately afterward.
3. Verdict rule: choose `pass` only if context/requirement scope is coherent, EmailRep success criteria all have evidence, R083 is explicitly future-owned outside M016, and fresh verification passed. Choose `needs-remediation` with a concrete remediation plan if any of those are false.
4. Include a success-criteria checklist covering adapter mapping, settings/registry email provider count, safe compact rendering, mocked Online E2E proof, and descoped non-goals.
5. Include requirement coverage notes for R008, R009, R011, and R083; R083 should be listed as descoped/future M018 coverage, not validated by M016.

Threat Surface (Q3): validation text must not include provider secrets, raw API keys, or environment values.
Requirement Impact (Q4): validates or remediates R008/R009/R011 supporting evidence for M016 and records R083 as out of M016 scope.
Failure Modes (Q5): if validation artifact is absent or empty, auto-mode cannot complete; if verdict is pass despite failed tests or incoherent requirements, closeout lies; if needs-remediation lacks a plan, the next auto iteration cannot act.
Negative Tests (Q7): verify the artifact exists, names Email Reputation Depth, includes a valid verdict, and contains no raw key material.
Done when: `.gsd/milestones/M016/M016-VALIDATION.md` exists, is non-empty, has a truthful verdict, and the verification command passes.

## Inputs

- `.gsd/milestones/M016/M016-CONTEXT.md`
- `.gsd/milestones/M016/M016-ROADMAP.md`
- `.gsd/REQUIREMENTS.md`
- `.gsd/DECISIONS.md`
- `.gsd/milestones/M016/slices/S01/S01-SUMMARY.md`
- `.gsd/milestones/M016/slices/S02/S02-SUMMARY.md`
- `.gsd/milestones/M016/slices/S03/S03-SUMMARY.md`
- `.gsd/milestones/M016/slices/S04/S04-SUMMARY.md`
- `tests/test_emailrep_online_coverage.py`
- `tests/e2e/test_emailrep_online.py`

## Expected Output

- `.gsd/milestones/M016/M016-VALIDATION.md`

## Verification

test -s .gsd/milestones/M016/M016-VALIDATION.md && grep -q "Email Reputation Depth" .gsd/milestones/M016/M016-VALIDATION.md && grep -Eq "pass|needs-remediation" .gsd/milestones/M016/M016-VALIDATION.md

## Observability Impact

Creates the durable validation artifact that future agents and auto-mode gates can inspect to understand pass/remediation status, requirement coverage, evidence commands, and any remaining blockers.
