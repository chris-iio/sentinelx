# S01: Analysis History & Persistence — UAT

**Milestone:** M006
**Written:** 2026-03-25T11:22:35.326Z

## UAT: Analysis History & Persistence

### Preconditions
- SentinelX running locally (`flask run` or equivalent)
- No prior history entries (fresh `~/.sentinelx/history.db` or delete existing)
- Browser with JS enabled

---

### Test 1: Fresh Home Page — No History
1. Navigate to `/`
2. **Expected:** Input form renders normally. No "Recent Analyses" section visible.

### Test 2: Submit Analysis and Verify History Save
1. Navigate to `/`
2. Paste `8.8.8.8 1.1.1.1 evil.com` into the input textarea
3. Select "Online" mode and submit
4. Wait for enrichment to complete (progress bar reaches 100%)
5. **Expected:** Results page renders with 3 IOC cards, verdict badges, enrichment detail rows
6. Note the URL — it contains a job_id (e.g., `/results?job_id=abc123`)

### Test 3: Recent Analyses List Appears
1. Navigate back to `/`
2. **Expected:** A "Recent Analyses" section appears below the input form
3. **Expected:** One entry visible showing:
   - Truncated input text (e.g., `8.8.8.8 1.1.1.1 evil.com`)
   - IOC count: `3`
   - Verdict badge (malicious/suspicious/clean depending on provider responses)
   - Timestamp (just now)

### Test 4: Click History Entry Reloads Full Results
1. Click the recent analysis entry from Test 3
2. **Expected:** URL changes to `/history/<analysis_id>`
3. **Expected:** Full results page renders identically to the live analysis:
   - All 3 IOC cards present
   - Verdict badges on each card
   - Dashboard counts bar populated
   - Enrichment detail rows (reputation providers, context providers) filled
   - Expand/collapse toggles work on each IOC card
   - Export button is enabled and functional
   - Detail links present on IOC cards

### Test 5: History Survives Tab Close
1. Close the browser tab entirely
2. Open a new tab and navigate to `/`
3. **Expected:** Recent analysis from Test 2 still appears in the list
4. Click it
5. **Expected:** Full results page loads identically to Test 4

### Test 6: Multiple Analyses Appear in Chronological Order
1. Submit a second analysis with different IOCs (e.g., `malware.com badip.net`)
2. Navigate to `/`
3. **Expected:** Two entries in Recent Analyses, most recent first
4. **Expected:** Each entry shows its own IOC count and verdict

### Test 7: History Detail 404 for Invalid ID
1. Navigate to `/history/nonexistent-id-12345`
2. **Expected:** 404 error page returned

### Test 8: History Page Verdict Computation
1. Navigate to a history entry via Recent Analyses list
2. **Expected:** Card verdicts match the stored results (no re-computation from providers)
3. **Expected:** Dashboard verdict counts (malicious/suspicious/clean/no_data) sum correctly

### Edge Cases

### Test 9: Very Long Input Text
1. Submit analysis with 200+ characters of IOC text
2. Navigate to `/`
3. **Expected:** Recent analysis entry shows truncated text (≤120 chars) with no layout overflow

### Test 10: HistoryStore DB Absent
1. Delete `~/.sentinelx/history.db`
2. Navigate to `/`
3. **Expected:** Page loads normally with no error, no Recent Analyses section
4. Submit a new analysis
5. Navigate to `/`
6. **Expected:** DB auto-created, new analysis appears in Recent Analyses
