# S02: Recent Analyses → Dedicated /history Page — UAT

**Milestone:** M010
**Written:** 2026-04-04T05:25:43.780Z

## UAT: S02 — Recent Analyses → Dedicated /history Page

### Preconditions
- SentinelX running locally (`flask run` or `python -m app`)
- At least one past analysis stored in history (submit IOCs through the home page first)

### Test Cases

#### TC1: Home page shows only the paste form
1. Navigate to `/`
2. **Expected:** Page shows the IOC input textarea and submit button
3. **Expected:** No "Recent Analyses" heading, no analysis list, no collapse toggle
4. **Expected:** Page title is visible, nav bar shows History (clock) and Settings (cog) icons

#### TC2: History page lists recent analyses
1. Navigate to `/history`
2. **Expected:** Page heading reads "Recent Analyses"
3. **Expected:** Each row shows: truncated input text, IOC count with plural handling, verdict badge (colored by top verdict), timestamp
4. **Expected:** Each row is a clickable link to `/history/<analysis_id>`
5. Click any analysis row
6. **Expected:** Redirects to the full results page for that analysis with all enrichment data

#### TC3: History page empty state
1. Clear all history (or use a fresh database)
2. Navigate to `/history`
3. **Expected:** Page shows "No analyses yet. Submit some IOCs to get started."
4. **Expected:** No `.recent-analyses-list` element rendered

#### TC4: Nav bar History link
1. From any page (`/`, `/history`, `/settings`, results page)
2. **Expected:** Nav bar contains a clock icon link labeled "History" (aria-label)
3. Click the clock icon
4. **Expected:** Navigates to `/history`

#### TC5: History page error handling
1. Simulate a `list_recent()` failure (e.g., corrupt or locked database)
2. Navigate to `/history`
3. **Expected:** Server returns 500 error (exception propagates, no silent empty page)

#### TC6: Rate limiting
1. Send 31 rapid requests to `/history` within 60 seconds
2. **Expected:** Request #31 returns HTTP 429

### Edge Cases
- Analysis with exactly 1 IOC shows "1 IOC" (no plural "s")
- Analysis with 0 IOCs shows "0 IOCs"
- Very long input text is truncated in the list row (CSS overflow handling)
- History page with 50+ analyses shows exactly 50 (the limit parameter)
