# S01: S01 — UAT

**Milestone:** M012
**Written:** 2026-04-22T04:07:42.947Z

# S01 UAT — Enrichment failure visibility and runtime baseline

## Preconditions

1. Start the app in a local dev/test environment with the current `main` worktree.
2. Ensure at least one provider is configured for online enrichment testing.
3. Have one simple IOC ready (for example `8.8.8.8`) and a browser session that can submit the normal analysis form.
4. For terminal-state checks, use the mocked/status-test harness or a dev setup where the status endpoint can be forced to return the terminal payloads described below.

## Test Case 1 — Successful online enrichment still completes normally

1. Open the analysis page.
   - Expected: The normal paste form is visible.
2. Submit a known IOC in **online** mode.
   - Expected: The results page loads with the enrichment progress UI visible.
3. Let polling complete.
   - Expected: Provider rows render incrementally while polling is active.
   - Expected: The progress text eventually reads `Enrichment complete`.
   - Expected: Export becomes enabled only after completion.
4. Expand an IOC row.
   - Expected: Provider detail rows are visible and the detail link still points to the IOC detail page.

## Test Case 2 — Unknown job ID becomes an explicit terminal analyst-visible state

1. Trigger or simulate a poll against `/enrichment/status/<job_id>` where the backend returns:
   - `status: failed`
   - `terminal: true`
   - `terminal_reason: unknown`
   - `error: Enrichment job was not found.`
2. Observe the results page after the next polling tick.
   - Expected: Polling stops.
   - Expected: A visible warning/banner appears with the backend error message.
   - Expected: The progress text is replaced with the same terminal failure message.
   - Expected: Export does not become enabled from this terminal failure.

## Test Case 3 — Evicted job state is distinguishable from never-found jobs

1. Trigger or simulate a poll where the backend returns:
   - `status: failed`
   - `terminal: true`
   - `terminal_reason: evicted`
   - `error: Enrichment job status was evicted from memory.`
2. Observe the results page.
   - Expected: Polling stops after that response.
   - Expected: The analyst-visible message specifically indicates eviction/rerun rather than a generic parse or network failure.
   - Expected: Previously rendered results, if any, remain visible; the UI does not revert to a spinner-only state.

## Test Case 4 — Failed orchestrator job surfaces as terminal failure without hiding prior progress

1. Trigger or simulate a poll where the backend returns:
   - `status: failed`
   - `terminal: true`
   - `terminal_reason: job_failed`
   - a non-empty `error` message
2. Observe the results page.
   - Expected: Polling stops.
   - Expected: The terminal error text is shown to the analyst.
   - Expected: No silent endless retries continue after the terminal response.

## Test Case 5 — Cursor polling contract remains stable

1. Start an online enrichment run.
2. Inspect polling requests in the browser network panel.
   - Expected: The first request uses `?since=0`.
3. Wait for one or more results to arrive.
   - Expected: Subsequent poll requests advance `since` to the backend-provided `next_since` value.
   - Expected: New results append without duplicating already-rendered provider rows.

## Edge Cases

- Terminal 404 responses must still be parsed and displayed; they are not generic transport failures.
- A successful run must still end in `Enrichment complete`, not a failure banner.
- Compatibility verification files (`tests/test_routes_helpers.py`, `tests/test_api_enrichment.py`, `tests/test_analysis_page.py`) must remain runnable so plan-driven slice verification does not fail on stale filenames.
