---
id: T01
parent: S01
milestone: M016
key_files:
  - tests/test_emailrep.py
key_decisions:
  - (none)
duration: 
verification_result: passed
completed_at: 2026-05-07T19:11:01.849Z
blocker_discovered: false
---

# T01: Pinned the red EmailRep adapter contract tests for S01.

**Pinned the red EmailRep adapter contract tests for S01.**

## What Happened

Created tests/test_emailrep.py to pin the future EmailRepAdapter public contract before implementation. The tests cover EmailRep-specific verdict mapping for malicious, suspicious, clean, and no_data responses; flattened raw_stats fields including reputation, suspicious, references, risk_flags, domain_reputation, and profiles; key-gated configuration; documented Key and User-Agent headers; URL-encoded lookup URLs; unsupported IOC type rejection; and HTTP 401 propagation through the shared safe_request path. Registry/setup/UI behavior was deliberately not touched because S01/T01 is adapter-local red test work.

## Verification

Ran `python3 -m pytest tests/test_emailrep.py -q`; it exited 2 during collection with `ModuleNotFoundError: No module named 'app.enrichment.adapters.emailrep'`, which is the expected red failure until T02 creates the adapter.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/test_emailrep.py -q` | 2 | ✅ expected red: collection fails only because app.enrichment.adapters.emailrep is missing | 70ms |

## Deviations

None. The task intentionally stops at a red test collection failure because the EmailRep adapter module is not implemented until T02.

## Known Issues

tests/test_emailrep.py currently fails collection with ModuleNotFoundError for app.enrichment.adapters.emailrep; this is the expected red state for T01 and will be resolved in T02.

## Files Created/Modified

- `tests/test_emailrep.py`
