---
id: T03
parent: S01
milestone: M016
key_files:
  - .gsd/milestones/M016/slices/S01/T03-OFFLINE-BASELINE.md
key_decisions:
  - Use Flask test-client Offline POST as the deterministic baseline path and include split pipeline/render timings rather than adding a durable benchmark script.
duration: 
verification_result: passed
completed_at: 2026-05-09T15:21:34.080Z
blocker_discovered: false
---

# T03: Captured a repeatable Offline /analyze runtime baseline and S04 speed target for a 50-IOC paste.

**Captured a repeatable Offline /analyze runtime baseline and S04 speed target for a 50-IOC paste.**

## What Happened

Followed the inlined T03 execution contract as authoritative and created `.gsd/milestones/M016/slices/S01/T03-OFFLINE-BASELINE.md` after confirming the artifact did not already exist. The baseline uses a deterministic Flask test-client `POST /analyze` in Offline mode with a 14-line, 1,578-character representative IOC paste that extracts 50 unique IOCs across CVE, domain, email, IPv4, hash, and URL types. The benchmark also split `run_pipeline()` plus `group_by_type()` from server-side `results.html` rendering so S04 can distinguish extraction cost from template cost. Results show full Offline POST p95 at 9.074 ms, pipeline/grouping p95 at 7.581 ms, and render-only p95 at 1.018 ms; the artifact sets a candidate S04 preservation target of <=12 ms p95 for this shape and recommends optimizing extraction/classification first if regressions appear. I also ran the existing S01 adapter-contract pytest command because the slice roadmap still names EmailRep contract coverage.

## Verification

Verified the benchmark command executed successfully and captured raw JSON output in `.gsd/exec/be3938ef-78a1-4f66-9ca4-1613f5b36304.stdout`. Verified the written artifact contains the required exact command, input shape, timing results, environment caveats, and S04 target. Ran the slice-level adapter contract suite `python3 -m pytest tests/test_emailrep.py tests/test_adapter_contract.py -q`, which passed with 198 tests.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 - <<'PY' ... PY (inline Flask test-client Offline /analyze benchmark)` | 0 | ✅ pass | 950ms |
| 2 | `python3 - <<'PY' ... PY (artifact contract verification for T03-OFFLINE-BASELINE.md)` | 0 | ✅ pass | 17ms |
| 3 | `python3 -m pytest tests/test_emailrep.py tests/test_adapter_contract.py -q` | 0 | ✅ pass | 470ms |

## Deviations

The slice roadmap/task title still describes EmailRep shared adapter contract coverage, but the inlined T03 task plan provided by auto-mode was the Offline runtime baseline; I followed the inlined task contract and additionally ran the EmailRep adapter-contract pytest command to preserve the slice-level proof.

## Known Issues

No implementation issues found. The baseline is server-side/test-client only and explicitly does not measure browser DOM, CSS, JavaScript, or network latency.

## Files Created/Modified

- `.gsd/milestones/M016/slices/S01/T03-OFFLINE-BASELINE.md`
