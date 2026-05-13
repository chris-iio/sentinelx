# S03: Best Optimization Implementation — UAT

**Milestone:** M017
**Written:** 2026-05-13T08:45:04.764Z

## UAT Type

Automated integration UAT with manual reproduction steps for analyst-visible behavior. Human browser execution was not required for S03 because the slice touched server-side status polling and was covered by route/orchestrator/e2e regression suites.

## Preconditions

- SentinelX is checked out at the completed S03 state.
- Python dependencies are installed for the test suite.
- No real API keys are required; tests use mocked/local providers.
- The M017 audit output path is writable: `.gsd/milestones/M017/M017-AUDIT.md`.

## Numbered Steps

1. Run the focused regression suite: `python3 -m pytest -q tests/test_orchestrator.py tests/test_routes.py tests/test_optimization_audit.py`.
2. Run the fast project verification: `make verify-fast`.
3. Run the deep project verification: `make verify-deep`.
4. Regenerate the M017 audit: `python3 tools/optimization_audit.py --mode baseline --milestone-id M017 --output .gsd/milestones/M017/M017-AUDIT.md`.
5. Re-run audit structure checks: `python3 -m pytest -q tests/test_optimization_audit.py`.
6. Inspect the status polling contract through tests or a local mocked run: submit an enrichment job, poll `/enrichment/status/<job_id>?since=<cursor>`, and confirm responses preserve `status`, `terminal`, `terminal_reason`, `error`, `next_since`, and result deltas.

## Expected Outcomes

- Focused route/orchestrator/audit tests pass.
- `make verify-fast` passes.
- `make verify-deep` passes, including e2e coverage for analyst-facing flows.
- Audit regeneration exits 0 and the M017 audit describes the shipped S03 tail-only status polling proof.
- Normal live polling uses `get_incremental_status()` and does not call the full `get_status()` snapshot.
- Analyst-visible enrichment polling behavior remains compatible: clients receive stable status fields, terminal payloads, errors, `next_since`, and result updates.

## Edge Cases to Verify

- `since` omitted, negative, out of range, or beyond available results.
- Unknown job IDs.
- Evicted job tombstones.
- Failed/terminal jobs.
- Cached-marker tail alignment.
- Full snapshot callers still use `get_status()` where intentionally needed.
- Diagnostics and audit evidence remain redacted and do not expose API keys, tokens, or raw sensitive IOC payloads.

## Not Proven By This UAT

- Production load-test measurements at 10x real analyst volume.
- Browser-perceived rendering optimization for result updates; this remains available for S04 to ship or explicitly reject.
- Long-lived memory-pressure behavior beyond the existing bounded test and diagnostics coverage.
