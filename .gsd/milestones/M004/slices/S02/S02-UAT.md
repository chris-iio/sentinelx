# S02 UAT: IO Performance & Polling Protocol

## Preconditions

- SentinelX running locally (`flask run` or `make run`)
- At least one API key configured (e.g., VirusTotal) for live enrichment
- Browser with DevTools available (Network tab)
- `curl` or `httpie` available for API testing
- SQLite CLI available (`sqlite3`)

---

## Test Case 1: Polling Cursor — `?since=` Returns Only New Results

**Objective:** Verify that the enrichment status endpoint returns deltas, not the full list.

1. Submit 5+ IOCs via the input form (e.g., `8.8.8.8 1.1.1.1 evil.com malware.exe 192.168.1.1`).
2. Open DevTools → Network tab. Filter to `enrichment/status`.
3. Observe polling requests — each should include `?since=N` in the URL.
4. **Expected:** Early poll ticks return 1-3 results each. Later ticks return 0-1 results. The `next_since` field in each JSON response increments monotonically.
5. **Expected:** No duplicate IOC results appear in the rendered list. No skipped IOCs.
6. Open a separate terminal and run:
   ```bash
   # After enrichment completes, verify full-list retrieval still works
   curl -s http://localhost:5000/enrichment/status/<job_id>?since=0 | python3 -m json.tool | grep next_since
   ```
7. **Expected:** `next_since` equals the total number of results. All results present.

## Test Case 2: Polling Cursor — Backward Compatibility (no `?since=` param)

1. After submitting IOCs and getting a `<job_id>`, run:
   ```bash
   curl -s http://localhost:5000/enrichment/status/<job_id> | python3 -m json.tool
   ```
2. **Expected:** Response contains all results (same as `?since=0`) and includes `next_since` field.

## Test Case 3: Polling Cursor — Beyond-Length `since` Value

1. Run:
   ```bash
   curl -s "http://localhost:5000/enrichment/status/<job_id>?since=9999" | python3 -m json.tool
   ```
2. **Expected:** `results` array is empty (`[]`). `next_since` equals total result count (not 9999). No error.

## Test Case 4: Session Reuse — No Bare requests.get/post in Adapters

**Objective:** Confirm all adapters use persistent sessions.

1. Run:
   ```bash
   grep -rn 'requests\.get\|requests\.post' app/enrichment/adapters/*.py
   ```
2. **Expected:** Zero output lines (exit code 1 from grep).
3. Run:
   ```bash
   grep -rl 'self._session' app/enrichment/adapters/*.py | wc -l
   ```
4. **Expected:** Output is `12`.

## Test Case 5: ipinfo.io HTTPS — Public IP Lookup

**Objective:** Verify the ip-api adapter now uses ipinfo.io over HTTPS.

1. Submit a public IP (e.g., `8.8.8.8`) for enrichment.
2. In DevTools Network tab or server logs, confirm no outbound requests to `ip-api.com`.
3. Check the rendered GeoIP context for the IP.
4. **Expected:** Country, city, ASN, and ISP fields populated from ipinfo.io response. No flags or proxy/hosting indicators (these fields are empty by design).
5. Run:
   ```bash
   grep 'http://' app/enrichment/adapters/ip_api.py
   ```
6. **Expected:** Zero output (all URLs use HTTPS).

## Test Case 6: ipinfo.io — Private IP Handling

**Objective:** Verify private IPs return no_data, not an error.

1. Submit `192.168.1.1` (or `10.0.0.1`) for enrichment.
2. **Expected:** The IP Context row shows `no_data` verdict — no error message, no enrichment error badge.
3. Expand the IOC row and check the IP Context provider detail.
4. **Expected:** Empty raw_stats. No stack trace or "HTTP 404" error surfaced to the user.

## Test Case 7: ALLOWED_API_HOSTS Configuration

1. Run:
   ```bash
   grep 'ipinfo.io' app/config.py
   ```
2. **Expected:** `ipinfo.io` is present in `ALLOWED_API_HOSTS`.
3. Run:
   ```bash
   grep 'ip-api.com' app/config.py
   ```
4. **Expected:** Zero output. `ip-api.com` has been removed.

## Test Case 8: CacheStore — WAL Mode + Persistent Connection

1. Submit IOCs and let enrichment complete (this populates the cache).
2. Run:
   ```bash
   sqlite3 ~/.sentinelx/cache.db "PRAGMA journal_mode;"
   ```
3. **Expected:** Output is `wal`.
4. Run the same IOCs again.
5. **Expected:** Results load faster (from cache). No "database locked" errors in server logs.

## Test Case 9: CacheStore — purge_expired Exists

1. Run:
   ```bash
   grep 'def purge_expired' app/cache/store.py
   ```
2. **Expected:** Method signature `purge_expired(self, ttl_seconds: int) -> int` exists.
3. To test manually (Python REPL):
   ```python
   from app.cache.store import CacheStore
   store = CacheStore("/tmp/test_purge.db")
   count = store.purge_expired(3600)  # delete entries older than 1 hour
   print(f"Purged {count} entries")
   ```
4. **Expected:** Returns 0 on empty DB without error.

## Test Case 10: ConfigStore — Cached Config Read

1. Open Settings page in the browser.
2. Set a new API key for any provider (e.g., VirusTotal).
3. Immediately read back the key from Settings.
4. **Expected:** The new key is reflected immediately (write-through invalidation works — no stale cache).
5. Run:
   ```bash
   grep '_cached_cfg' app/enrichment/config_store.py
   ```
6. **Expected:** Cache variable referenced in `_read_config()` (return cached) and `_save_config()` (invalidate).

## Test Case 11: Full Test Suite Regression Check

1. Run:
   ```bash
   python3 -m pytest tests/ --ignore=tests/e2e -x -q
   ```
2. **Expected:** ≥839 tests pass with zero failures.
3. Run:
   ```bash
   python3 -m pytest tests/ -x -q
   ```
4. **Expected:** ≥944 tests pass (including E2E).

## Edge Cases

### EC-1: Empty Enrichment Job + Cursor
Submit an empty input or input with no valid IOCs. The enrichment status should return `results: []` and `next_since: 0` without errors.

### EC-2: ipinfo.io Timeout
If ipinfo.io is unreachable (simulate by blocking the host), the adapter should return an `EnrichmentError` with "Timeout" or "Connection failed" — not crash.

### EC-3: Rapid Settings Key Changes
Change an API key in Settings 3 times in quick succession, reading back after each change. Each read should reflect the most recent write (config cache is properly invalidated on each save).

### EC-4: Multiple Browser Tabs Polling Same Job
Open the same enrichment results page in 2 browser tabs. Both should render results correctly — the `?since=` cursor is per-tab (each tab tracks its own `since` counter). No duplication or skipping across tabs.
