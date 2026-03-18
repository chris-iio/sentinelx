# S04: Functionality integration + polish — UAT

**Milestone:** M002
**Written:** 2026-03-18

## UAT Type

- UAT mode: artifact-driven (build outputs + E2E suite) + human-experience (visual polish spot-check)
- Why this mode is sufficient: S04 is a verification slice, not a feature slice. All wiring was pre-existing from S01–S03. The 91-test E2E suite exercises every functional pipeline at runtime. Human-experience check is needed only to confirm visual polish landed correctly.

## Preconditions

1. Server running: `python3 app/app.py` (or `flask run`) on `http://localhost:5001`
2. Build current: `make css && make js-dev` exit 0
3. A previously enriched session available to browse (or run a fresh enrichment with any IOC set)

## Smoke Test

Navigate to the results page of any enriched session. The page should render with:
- Single-column IOC rows (no 2-column grid)
- Compact verdict dashboard at the top (not 5 large KPI boxes)
- Single-row filter bar
- Each enriched row showing verdict badge, context line, provider stat line, micro-bar

If this renders correctly, the S01–S03 foundation is intact and S04's integration work is confirmed at the surface level.

## Test Cases

### 1. Export pipeline — JSON export

1. Navigate to any enriched session results page
2. Click the **Export** button (top-right area) to open the dropdown
3. Click **Export JSON**
4. **Expected:** Browser downloads a `.json` file containing all enriched IOC results. File is valid JSON with an array of enrichment items. Each item contains `ioc_type`, `ioc_value`, and provider result data.

### 2. Export pipeline — CSV export

1. Navigate to any enriched session results page
2. Click the **Export** button → click **Export CSV**
3. **Expected:** Browser downloads a `.csv` file. First row is a header line. Each subsequent row corresponds to one IOC. No blank rows or malformed columns.

### 3. Export pipeline — Clipboard export

1. Navigate to any enriched session results page
2. Click the **Export** button → click **Copy to clipboard**
3. Paste into a text editor (`Cmd+V` / `Ctrl+V`)
4. **Expected:** Pasted content is a JSON representation of all enriched results. No JavaScript error in browser console. If clipboard API is denied (insecure origin), the browser console shows a handled error — not a silent failure or crash.

### 4. Dashboard-click-to-filter

1. Navigate to any enriched session with mixed verdicts (malicious + suspicious + clean, or similar)
2. In the compact verdict dashboard, click the **malicious** count/label
3. **Expected:** IOC list filters to show only `malicious` verdict rows. Other rows are hidden. Active filter indicator appears.
4. Click the **malicious** label again (or click **All**)
5. **Expected:** All rows become visible again. Filter is cleared.

### 5. Verdict sort

1. Navigate to any enriched session with mixed verdicts
2. Click the **Sort by severity** control (or verify the default sort is severity-descending)
3. **Expected:** Malicious IOCs appear first, then suspicious, then clean/known_good/no_data. Rows are reordered — not re-fetched.

### 6. Progress bar during active enrichment

1. Submit a new enrichment session with 3–5 IOCs
2. **Expected:** While enrichment is in progress, `#enrich-progress-fill` width increases from 0% toward 100% as each IOC completes. `#enrich-progress-text` shows a ratio like "2/5" or a percentage. Progress bar disappears (or completes) when all IOCs are done.

### 7. Warning banner on enrichment error

1. (If testable:) Simulate an enrichment failure by disconnecting network mid-session, or find an existing session with a partial-error result
2. **Expected:** `#enrich-warning` banner becomes visible with a human-readable warning message. Message content is set via `textContent` (inspect DOM to confirm — no `innerHTML` used).

### 8. Copy button on IOC card

1. Navigate to any enriched session results page
2. Find the copy button (📋 icon) on any IOC row
3. Click the copy button
4. Paste into a text editor
5. **Expected:** The IOC value (IP address, domain, hash) is pasted — matching `data-value` attribute on the `.copy-btn` element. Browser console shows no error.

### 9. Detail page link (post-expansion)

1. Click any enriched IOC row to expand it inline
2. Scroll to the bottom of the expanded panel
3. **Expected:** A "View full detail →" link is present. Click it — browser navigates to `/detail/<ioc_type>/<encoded_ioc_value>`. Detail page loads with the correct IOC context.

### 10. Inline expand / collapse (regression from S03)

1. Click any enriched IOC row summary
2. **Expected:** Enrichment details panel expands inline below the summary row. Chevron icon rotates 90°. `aria-expanded="true"` on the summary row.
3. Click the same row again
4. **Expected:** Panel collapses. Chevron returns to 0°. `aria-expanded="false"`.

### 11. Filter by IOC type

1. In the filter bar, select a specific IOC type (e.g., "IP" or "domain")
2. **Expected:** Only rows matching that type are visible. Other types are hidden. Type is read from `data-ioc-type` on `.ioc-card` elements.

### 12. Text search filter

1. In the filter bar, type a partial value (e.g., first 4 characters of a known IP or domain)
2. **Expected:** Only rows whose IOC value contains the typed string are visible. Search is live (no submit required). Clearing the search restores all rows.

## Edge Cases

### Clipboard denied on insecure origin

1. Access the app over HTTP (not HTTPS) or `localhost` without clipboard API support
2. Click **Copy to clipboard**
3. **Expected:** A console error is logged (unhandled promise rejection from clipboard.writeText), but the page does not crash, no error banner appears, and the user is not left in a broken state.

### Export with zero enriched results

1. Navigate to a session that completed enrichment but all IOCs returned `no_data`
2. Click **Export JSON**
3. **Expected:** A valid JSON file downloads containing an array of no_data result objects (not an empty file or error).

### Progress bar at 100%

1. Navigate to a session where enrichment has fully completed
2. **Expected:** Either the progress bar is at 100% and visible, or it has been hidden/removed. No stale partial-progress state (e.g., "3/5" frozen on a fully completed session).

### Expand after re-filter

1. Filter the results to a subset (e.g., by verdict)
2. Click an expanded row within the filtered set
3. **Expected:** Inline expand works correctly even when some rows are hidden by filter. The `.is-open` class toggles correctly; hidden rows don't interfere.

## Failure Signals

- **Export produces empty file or no download:** `allResults[]` accumulation in enrichment.ts is broken. Check browser console for `[export]` errors.
- **Dashboard click does nothing:** filter.ts `init()` failed to bind `.verdict-kpi-card[data-verdict]` — check console for `[filter]` errors or missing `#verdict-dashboard`.
- **Progress bar frozen or invisible:** `#enrich-progress-fill` or `#enrich-progress-text` missing from DOM, or `updateProgressBar()` selector mismatch — inspect results.html.
- **Copy button pastes wrong value or nothing:** `data-value` missing from `.copy-btn` in `_ioc_card.html`, or clipboard.ts `init()` failed to bind — check console for `[clipboard]` errors.
- **Detail link missing after expand:** `injectDetailLink()` not called from `markEnrichmentComplete()`, or idempotency guard blocked re-injection after DOM update — add breakpoint on `enrichment.ts` `markEnrichmentComplete()`.
- **Inline expand not working:** event delegation on `.page-results` ancestor broken — check `wireExpandToggles()` in enrichment.ts and confirm `.page-results` element exists in results.html.
- **Console JS errors on page load:** TS module init error — run `make typecheck` to surface the root cause.

## Requirements Proved By This UAT

- R008 — Export (JSON/CSV/clipboard), verdict filtering, type filtering, text search, detail page links, copy buttons, progress bar all exercised end-to-end.
- R009 — SEC-08 textContent-only confirmed via DOM inspection of warning banner (no innerHTML). CSP/CSRF verified via server audit (T02 grep evidence).
- R010 — Production bundle size gate confirmed (27,226 bytes ≤ 30KB). Performance perception verified by smooth expand/collapse transitions and responsive filter.

## Not Proven By This UAT

- **E2E selector coverage of new DOM structure (R011):** The 91/91 E2E pass covers functional pipelines but `tests/e2e/pages/results_page.py` page object may not yet have selectors for `.ioc-summary-row`, `.enrichment-details`, or `.detail-link-footer`. S05 audits and updates this.
- **SSRF allowlist and host validation (R009 partial):** These are server-side enforcement contracts verified in M001 and unchanged by the UI rework. UAT of UI changes does not re-prove server-side security logic.
- **Operational verification under real triage load:** Not tested with large IOC sets (50+ IOCs). Polling efficiency and sort debounce under load are assumed from the unchanged implementation.

## Notes for Tester

- The full E2E suite (91 tests) is the fastest way to verify the functional pipeline: `python3 -m pytest tests/e2e/ -q`
- The page title is `"sentinelx"` (all-lowercase) — this is intentional per the brand decision (D021)
- If testing enrichment flow, use `localhost:5001` not an external IP — the app runs locally
- `python` is not aliased on this system; use `python3` directly
- The Browserslist caniuse-lite deprecation warning in build output is cosmetic and non-blocking
- Build artifacts in `app/static/dist/` are committed — no rebuild needed before testing unless source files were changed
