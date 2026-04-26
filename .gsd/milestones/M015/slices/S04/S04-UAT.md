# S04: Integrated intake proof and polish — UAT

**Milestone:** M015
**Written:** 2026-04-26T12:00:58.782Z

## UAT Script — S04 Integrated Intake Workbench Proof

### Preconditions

- Run from the repository root with the M015/S04 code present.
- Use the normal test configuration with CSRF enabled and the Playwright live-server fixtures.
- No provider API keys are required; Offline mode must not call external enrichment providers.
- Deterministic history rows are created via the test fixture, not a developer-local `~/.sentinelx/history.db`.

### Test Case 1 — Assembled GET `/` contract with seeded recent history

1. Seed recent history with a stored input containing synthetic IOC text and markup-like characters, then request `GET /`.
   - Expected: response status is 200.
   - Expected: `#analyze-form`, `#ioc-text`, `#submit-btn`, `#clear-btn`, `#mode-input`, `#mode-toggle-widget`, `#mode-toggle-btn`, and CSRF hidden input are present.
   - Expected: `#mode-input` has value `offline`, and `#mode-status` explains Offline local extraction.
   - Expected: exactly one bounded `list_recent(limit=4)` read is made and no provider registry/enrichment call is made.
   - Expected: `.recent-analysis-row` links to `/history/<id>` and stored input text is escaped, not interpreted as markup.
   - Expected: no `.ioc-preview`, `.preview-rail`, or pre-submit results surface exists.

### Test Case 2 — Fail-open no-input POST `/analyze`

1. Force the history store's recent-summary lookup to raise.
2. Submit `POST /analyze` without IOC text.
   - Expected: validation re-renders status 200 with the paste form still present.
   - Expected: CSRF input, hidden `mode`, mode widget, textarea, and submit button remain in the DOM.
   - Expected: `.recent-analyses-unavailable` is shown quietly and no recent rows are rendered.
   - Expected: warning logs are sanitized and do not include pasted IOC content, provider keys, CSRF values, or raw results JSON.
   - Expected: the failure does not block a later valid paste-and-extract submission.

### Test Case 3 — Desktop visual hierarchy with Recent Analyses

1. Set the browser viewport to 1280×720.
2. Seed one recent history row and open `/`.
   - Expected: `.command-card` and `.recent-analyses-rail` are visible.
   - Expected: the command card is positioned before the rail, is at least 2.2× the rail width, and aligns near the rail top.
   - Expected: the rail contains the seeded `.recent-analysis-row` but remains visually secondary.
   - Expected: the document has no horizontal overflow.

### Test Case 4 — Mobile stacking and overflow resistance

1. Set the browser viewport to 390×844.
2. Seed one recent history row and open `/`.
   - Expected: the command card remains visible and usable.
   - Expected: the Recent Analyses rail stacks below the command card.
   - Expected: the rail width stays within the viewport and full-document horizontal overflow is absent.
   - Expected: form actions stack below the textarea and remain tappable.

### Test Case 5 — History resume from the intake rail

1. Seed a recent history row with a known analysis id.
2. Open `/` and click the matching `.recent-analysis-row`.
   - Expected: browser navigates to `/history/<id>`.
   - Expected: `.page-results` is visible and the saved analysis route reloads without re-querying providers.

### Test Case 6 — Offline fast path from the final layout

1. Open `/` in the final assembled layout.
2. Confirm Offline mode is selected by default.
3. Paste synthetic IOC text containing `203.0.113.10` and `malware.example.com`.
4. Click Extract.
   - Expected: submit enables only after text entry.
   - Expected: browser reaches the existing results page.
   - Expected: results mode is Offline and at least two IOC cards render.
   - Expected: no `/enrichment/status/` polling request is made.

### Test Case 7 — Empty and unavailable Recent Analyses remain non-blocking

1. Open `/` with no history rows.
   - Expected: `.recent-analyses-empty` appears, no recent rows appear, and the paste form remains usable.
2. Open `/` while recent-history lookup is forced to fail.
   - Expected: `.recent-analyses-unavailable` appears, no recent rows appear, and entering IOC text enables Extract.

### Test Case 8 — Repository regression lane

1. Run the S04 route/security command.
   - Expected: 27 route/security/history tests pass.
2. Run the focused browser assembly command.
   - Expected: 34 homepage/UI/offline browser tests pass.
3. Run `make verify-fast`.
   - Expected: non-E2E pytest, Vitest, TypeScript, and generated asset build all pass.
4. Run the full browser lane `python3 -m pytest -q tests/e2e`.
   - Expected: the full E2E suite passes with 125 tests.
