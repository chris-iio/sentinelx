# S02: S02 — Shared result-application path for live and history views — UAT

**Milestone:** M012
**Written:** 2026-04-22T06:26:08.275Z

# UAT — S02 Shared live/history result application

## Preconditions

- SentinelX is running from the current branch with the S02 changes built.
- A live results page can be opened with a job whose enrichment stream includes mixed reputation, context-only, and error/no-data items.
- A history detail page exists for an analysis that stores the same mixed result shape.
- Browser/network inspection is available so requests to `/enrichment/status/<job_id>` can be observed.

## Test Case 1 — Live results page renders the shared result path correctly

1. Open a live results page that has `.page-results[data-results-owner="live"]` and a real `data-job-id`.
   - Expected: the page initializes the live runtime only; no history replay marker takes ownership.
2. Let enrichment complete across at least two poll ticks so `next_since` advances.
   - Expected: subsequent status requests use the cursor path, visible progress advances to complete, and the warning banner remains hidden on success.
3. Inspect one IOC with mixed provider output.
   - Expected: the IOC card shows the correct summary row, verdict badge, provider detail rows, grouped no-data/error rows, and an injected detail link.
4. Click the IOC copy button and inspect its `data-enrichment` payload.
   - Expected: the copied enrichment summary reflects the same summary text shown in the card.
5. Open the export UI.
   - Expected: export controls are enabled once results exist and only one dropdown/toggle interaction occurs per click.

## Test Case 2 — History detail page replays to the same analyst-visible state without polling

1. Open the matching history detail page with `.page-results[data-results-owner="history"]`.
   - Expected: the page replays stored `data-history-results` immediately and never shows a live-loading spinner that depends on polling.
2. Compare the rendered IOC card against the live page for the same IOC/result mix.
   - Expected: summary row text, verdict badge, detail rows, no-data grouping, detail link, progress completion, export readiness, and copy-button enrichment text match the live page outcome.
3. Watch the network panel during and after replay.
   - Expected: no request is sent to `/enrichment/status/history` and no false terminal warning banner appears.

## Test Case 3 — Duplicate initialization does not double-bind behavior

1. Reload a results page or otherwise trigger frontend initialization twice in a dev/test harness.
   - Expected: the active owner remains stable and only one runtime marker is authoritative.
2. Click an expand/collapse row repeatedly, then open/close the export dropdown repeatedly.
   - Expected: each action toggles exactly once per interaction; rows do not double-expand, and the export dropdown does not jitter from stacked listeners.

## Test Case 4 — History contract drift fails safely

1. Render a history page with invalid or malformed `data-history-results` JSON in a test/dev harness.
   - Expected: replay fails loudly for developers instead of silently marking the page complete with bad data.
2. Render a history page missing the owner marker or with an ambiguous explicit live marker.
   - Expected: the page is treated as non-live/static rather than starting status polling.

## Edge Cases

- Empty history payload: page completes replay without enabling export for nonexistent results and without polling.
- Context-only IOC: summary row and copy-button enrichment still render coherently even when no reputation providers produced verdict rows.
- Mixed success + error items: reputation/context rows render while error/no-data entries stay grouped and do not suppress valid detail-link or verdict updates.
- Cursor continuity: live polling continues to request only new results via `?since=` while ending in the same final DOM state the history page replays synchronously.
