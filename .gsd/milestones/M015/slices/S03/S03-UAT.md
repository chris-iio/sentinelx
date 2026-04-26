# S03: Compact Recent Analyses rail — UAT

**Milestone:** M015
**Written:** 2026-04-26T11:01:54.216Z

# UAT: S03 Compact Recent Analyses rail

## Preconditions

- The SentinelX app is running from the current codebase with built static assets from `make build`.
- Use an isolated test history database or a disposable local profile; do not rely on production analyst history.
- Browser viewport checks should include a desktop-sized viewport and a narrow mobile-sized viewport.

## Test Case 1 — Recent analyses render as compact resume links

1. Seed at least one saved analysis with a recognizable snippet such as `1.2.3.4` and capture its analysis ID.
2. Open `/`.
3. Expected: the paste command card is visible with `#analyze-form`, `#ioc-text`, `#mode-input`, `#mode-toggle-widget`, and `#submit-btn` intact.
4. Expected: a `.recent-analyses-rail` appears as a secondary surface.
5. Expected: at least one `.recent-analysis-row` is visible and its link `href` points to `/history/<seeded-analysis-id>`.
6. Click the recent-analysis link.
7. Expected: the browser navigates to the existing history detail route for that analysis; unknown IDs remain handled by the existing `/history/<id>` 404 behavior.

## Test Case 2 — Empty history does not look like a form error

1. Clear the history store.
2. Open `/`.
3. Expected: the command-card paste form remains visible and usable.
4. Expected: the recent area is either a compact empty state (`.recent-analyses-empty`) or contains no rows; it is visually secondary and does not disable input.
5. Type `8.8.8.8` into `#ioc-text`.
6. Expected: `#submit-btn` becomes enabled according to the existing form behavior.

## Test Case 3 — History listing failure fails open

1. Simulate `HistoryStore.list_recent()` raising during GET `/`.
2. Open `/`.
3. Expected: response/page still succeeds; no error page is shown.
4. Expected: `#ioc-text`, `#mode-input`, `#mode-toggle-widget`, and `#submit-btn` are present.
5. Expected: the page shows a quiet `.recent-analyses-unavailable` state or otherwise omits recent rows; it must not present the issue as a paste-form validation error.
6. Expected: logs contain only sanitized failure context (failure class/context), not raw IOC text, result JSON, provider keys, secrets, or CSRF token values.

## Test Case 4 — Desktop hierarchy keeps intake dominant

1. Open `/` at a desktop viewport.
2. Expected: `.command-card` appears before and larger/more prominent than `.recent-analyses-rail`.
3. Expected: the recent rail is compact and secondary; it does not crowd or visually outrank the paste form, mode toggle, or Extract action.

## Test Case 5 — Mobile layout stacks below command card

1. Open `/` at a mobile viewport.
2. Expected: `.command-card` appears above `.recent-analyses-rail`.
3. Expected: there is no horizontal overflow, and the paste textarea/mode/Extract controls remain the first usable path.

## Test Case 6 — Offline paste-to-results remains unchanged

1. Open `/`.
2. Confirm the hidden `#mode-input` default is `offline`.
3. Paste mixed IOC text into `#ioc-text`.
4. Click Extract.
5. Expected: the app navigates to results and completes the existing offline extraction path without making provider HTTP calls.
6. Expected: recent-history markup does not introduce a pre-submit preview or alter extraction semantics.

## Edge Case — Stored markup-like history text is safe

1. Seed history with user-supplied text containing markup-like characters such as `<script>alert(1)</script>`.
2. Open `/`.
3. Expected: the text is rendered as inert escaped text or a safe fallback, never as executable markup or script.
