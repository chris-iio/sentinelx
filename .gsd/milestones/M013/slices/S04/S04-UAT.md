# S04: Frontend polling/render shipped fixes and final rerun — UAT

**Milestone:** M013
**Written:** 2026-04-25T07:18:25.487Z

# UAT — S04 Frontend polling/render shipped fixes and final rerun

## Preconditions
- Local SentinelX app is running from the final M013/S04 repository state.
- Use the deterministic mocked-online results flow already exercised by `tests/e2e/test_results_page.py` so provider output is stable.
- Have one saved analysis available so the same IOC can be opened through both live results and history replay.

## Test Case 1 — Live enrichment parity on the shipped coordinator path
1. Start a live analysis for a known IOC used by the mocked-online flow (for example the IPv4 IOC covered by the results-page test harness).
2. Wait for enrichment polling to complete.
3. Inspect the results page header/root container.
4. Inspect the IOC card once the slot is marked loaded.
5. Use the copy button and open the detail link.

**Expected outcomes**
- The page root exposes the live owner/runtime markers (`.page-results[data-results-owner][data-results-runtime]`) for the live run.
- The IOC card reaches `.enrichment-slot--loaded` and renders the same analyst-visible surface as before S04: worst-verdict summary row, context line, provider counts, copy button, detail link, filters/export controls, and progress text.
- The pending indicator clears when all expected provider results arrive.
- Copy uses the IOC value already shown in the card, and the detail link opens the IOC detail page without breaking the current results page state.

## Test Case 2 — History replay parity through the same shared coordinator
1. Open the saved analysis from the history/recent-analyses surface.
2. Wait for the history results page to finish synchronous replay.
3. Compare the IOC card content against the live run from Test Case 1.
4. Expand and collapse the IOC row.

**Expected outcomes**
- The page root switches to the history owner/runtime markers rather than the live ones.
- The same summary row, context/reputation text, copy affordance, detail link, filters, and loaded-slot styling appear for the saved result.
- Expand/collapse still works, and the shared coordinator does not require live polling to rebuild the visible card state.

## Test Case 3 — Interaction continuity after repeated result application
1. On either the live or history page, use verdict filters, type filters, and text search to narrow the result set.
2. Clear the filters.
3. Trigger any repeated-result UI path already covered by the mocked-online flow (multiple provider updates for the same IOC).

**Expected outcomes**
- Filtering/search behavior is unchanged and does not remove copy/detail/export affordances.
- The worst verdict shown for the IOC converges correctly after repeated provider updates.
- No duplicate summary rows or broken loaded-state markers appear after repeated updates.

## Test Case 4 — Final audit proof artifact is current and truthful
1. Open `.gsd/milestones/M013/M013-AUDIT.md` generated during the slice closeout.
2. Inspect the frontend/render ranked finding and seam note.
3. Inspect the capture table.

**Expected outcomes**
- The audit says the coordinator-local DOM-handle cache shipped in S04.
- The only deferred frontend/render work left explicit is flush-wide dashboard recount/reorder follow-up.
- The capture table includes fresh `verify-fast` and `verify-deep` rows from the same final repository state used for closeout.

## Edge Cases
- Missing or malformed `data-provider-counts` metadata should fail soft without breaking card rendering or preventing the pending indicator from reaching a valid fallback state.
- Context-only, provider-error, and mixed provider result sets must still render text-only rows safely with the same copy/detail-link behavior.
- If the audit rerun prints the synthetic RateLimitBeta 429 line to stderr, treat it as expected capture noise unless the command exits non-zero or the generated capture table is missing.
