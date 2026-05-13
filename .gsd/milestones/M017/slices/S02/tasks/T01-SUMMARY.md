---
id: T01
parent: S02
milestone: M017
key_files:
  - tools/optimization_audit.py
  - tests/test_optimization_audit.py
  - Makefile
  - .gsd/milestones/M017/M017-AUDIT.md
key_decisions:
  - M017 is selected through `--milestone-id M017` and Makefile wrappers while M013 remains the default/backward-compatible audit contract.
  - Failed optional capture commands are durable measurement rows with nonzero exits rather than abort conditions, matching the audit failure-visibility requirement.
duration: 
verification_result: passed
completed_at: 2026-05-12T18:05:45.229Z
blocker_discovered: false
---

# T01: Added an M017 identity-grounded optimization audit contract, tests, and Makefile regeneration targets while preserving the M013 default audit flow.

**Added an M017 identity-grounded optimization audit contract, tests, and Makefile regeneration targets while preserving the M013 default audit flow.**

## What Happened

Updated `tools/optimization_audit.py` so `--milestone-id M017 --mode baseline` renders a milestone-local audit grounded in `docs/project-map.md`, SentinelX's local analyst IOC triage identity, R085/R087, decisions D078-D080, and the S01 seam inventory priority order. The M017 baseline now records do-now/do-next/later/leave-alone findings, explicit S03 target language, the evidence standard, and a clear missing-project-map warning instead of silently claiming grounding. Existing baseline measurement captures and M013 default behavior remain available. Optional capture-command failures are now recorded in the measurement table and surfaced on stderr without aborting unrelated artifact generation. Added M017-specific pytest coverage for project-map grounding, ranked buckets, evidence/S03 language, missing-map behavior, no placeholders, and non-aborting failed captures. Added `audit-m017` and `audit-m017-template` Makefile targets and regenerated `.gsd/milestones/M017/M017-AUDIT.md`.

## Verification

Ran the focused pytest contract suite, CLI help inspection, direct M017 baseline artifact generation, and the new Makefile target. All commands exited 0. The generated artifact contains the M017 identity-grounded contract and no placeholder rows.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest -q tests/test_optimization_audit.py` | 0 | ✅ pass (9 tests) | 1099ms |
| 2 | `python3 tools/optimization_audit.py --help` | 0 | ✅ pass | 60ms |
| 3 | `python3 tools/optimization_audit.py --milestone-id M017 --mode baseline --output .gsd/milestones/M017/M017-AUDIT.md` | 0 | ✅ pass | 221ms |
| 4 | `make audit-m017` | 0 | ✅ pass | 197ms |

## Deviations

Extended capture-command failure behavior so failed optional captures no longer force a nonzero CLI exit; this implements the task's Q5 failure-mode requirement and leaves failure details visible in stderr plus the artifact table.

## Known Issues

Internal synthetic runtime/provider capture still logs a RateLimitBeta 429 backoff message to stderr during successful audit generation; this is pre-existing diagnostic noise from the capture path and does not expose secrets.

## Files Created/Modified

- `tools/optimization_audit.py`
- `tests/test_optimization_audit.py`
- `Makefile`
- `.gsd/milestones/M017/M017-AUDIT.md`
