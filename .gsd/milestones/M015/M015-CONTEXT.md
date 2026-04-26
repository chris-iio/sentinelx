# M015: Intake Workbench

**Gathered:** 2026-04-26
**Status:** Ready for planning

## Project Description

SentinelX is a local browser-based threat intelligence hub for SOC analysts. The analyst pastes alerts, email headers, threat reports, or raw IOC blobs; SentinelX extracts, normalizes, classifies, and optionally enriches IOCs against configured providers; results are shown with transparent verdicts, provider details, history reload, and no invented scores.

M015 redesigns the `/` home/input page into a fast **Intake Workbench**. The rest of the product has matured through prior milestones, but the front door is still mostly a textarea, mode toggle, Clear, and Extract. The user’s explicit direction is **go fast**: keep the primary motion as **paste → choose mode → Extract**, keep pre-submit extraction preview out of scope, and add only a **compact list** of Recent Analyses.

## Why This Milestone

The product-facing results, detail, history, enrichment, and local workflow surfaces are now stable. The next highest-leverage design target is the first screen: it should feel as deliberate and analyst-grade as the rest of SentinelX without turning into a dashboard or slowing the primary paste-to-results loop.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Open `/`, immediately paste IOC text into a dominant command card, choose Offline or Online mode, and click Extract without extra staging.
- See a compact Recent Analyses rail/list on the intake page when history exists and click a row to reload `/history/<id>`.
- Use the intake page on desktop or mobile without the Recent Analyses surface crowding out the paste form.
- Continue using the same extraction, enrichment, history reload, CSRF/security, and results behavior as before.

### Entry point / environment

- Entry point: browser route `/`
- Environment: local dev browser via existing Flask app and `tools/dev_server.py` / Make targets
- Live dependencies involved: SQLite history store at `~/.sentinelx/history.db`; existing extraction/enrichment routes; no new external services

## Completion Class

- Contract complete means: route/template contracts prove `/` passes bounded recent-analysis summaries, keeps form semantics, and degrades safely when history listing fails.
- Integration complete means: the home page can submit offline/online through existing `/analyze`, recent rows link into `/history/<id>`, and mode state posts through the existing hidden `mode` input.
- Operational complete means: the final page passes browser/E2E proof on desktop and mobile and full repo verification; no local lifecycle change is required beyond existing dev-server support.

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- From `/`, an analyst can paste IOC text, Extract offline, and land on the existing results page without a new intermediate preview or staging step.
- With seeded history, `/` renders a compact Recent Analyses surface and a recent row reloads the saved analysis through `/history/<id>`.
- If `history_store.list_recent()` fails, `/` still renders the paste form and does not block extraction.
- Desktop and mobile viewport checks show command-card + recent rail/stack behavior without hiding the primary action.
- Existing verification lanes still pass, including focused backend tests, relevant E2E, `make verify-fast`, and final `make verify`.

## Architectural Decisions

### Server-render compact Recent Analyses on the index route

**Decision:** Render the compact Recent Analyses list on `/` using `current_app.history_store.list_recent(limit=...)` in `app/routes/analysis.py`.

**Rationale:** The existing `HistoryStore.list_recent(limit)` already returns exactly the lightweight data needed for a compact start-page list: `id`, truncated input text, mode, total count, top verdict, and timestamp. Server rendering avoids a new API endpoint, keeps the page fast, and matches the current Jinja-based history page pattern.

**Evidence Source:** `app/routes/history.py` uses `list_recent(limit=50)` for `/history`; `app/enrichment/history_store.py` exposes `list_recent(limit)`; `app/templates/history.html` already renders recent-analysis rows.

**Alternatives Considered:**
- Add `/api/history/recent` and fetch client-side — rejected because live refresh is unnecessary and it would add API/test surface for little value.
- Keep history only on `/history` — rejected because the user explicitly chose a compact list on the intake page.

### Use command-card + compact recent rail layout

**Decision:** Make the paste form the dominant command card and place Recent Analyses in a compact secondary rail on desktop, stacked below on mobile.

**Rationale:** The user chose **go fast**. A dashboard or equal-weight history panel would dilute the primary action. A rail/list makes recent work available without changing the page’s mental model from command surface to dashboard.

**Evidence Source:** Current `index.html` is already a compact form; current `input.css` owns `.page-index`, `.input-card`, `.ioc-textarea`, and mode styles; current results/detail pages use quiet precision hierarchy.

**Alternatives Considered:**
- Full dashboard — rejected because it conflicts with go-fast intake.
- Single stacked card — possible, but less clear on desktop and more likely to make recent history compete with the form.

### Clarify existing Offline/Online toggle without replacing semantics

**Decision:** Preserve the existing `#mode-input`, `#mode-toggle-widget`, and `#mode-toggle-btn` contract while improving visual clarity, helper copy, active state, and keyboard/accessibility affordances.

**Rationale:** The current form behavior is stable and tested. Replacing the control with segmented radios may be semantically nice but would add churn. M015’s goal is clarity without changing the underlying submit contract.

**Evidence Source:** `app/templates/index.html` contains the hidden `mode` field and toggle DOM; `app/static/src/ts/modules/form.ts` owns mode switching; `tests/e2e/test_homepage.py` and `tests/e2e/pages/index_page.py` already pin default offline mode and control selectors.

**Alternatives Considered:**
- Segmented controls — rejected unless implementation proves the existing toggle cannot meet accessibility/clarity needs.
- Hide mode choice — rejected because online enrichment should remain discoverable.

## Error Handling Strategy

The paste form is the primary path and must never depend on history. `index()` should catch or otherwise isolate recent-history failures so `/` still renders the form. Recent Analyses supports three quiet states: entries exist, no entries, and history unavailable. The history-unavailable state should be subtle; it must not become a blocking alert or distract from paste-and-go.

Existing behaviors stay intact: empty input shows the current explicit error, online mode with no configured providers redirects to Settings with the existing warning, and provider/enrichment errors remain owned by the existing results/enrichment flow. M015 does not add retry loops, async history refresh, provider recovery, or pre-submit extraction preview.

## Risks and Unknowns

- History failure on `/` could accidentally block the primary form — this would violate go-fast intake and must be retired early.
- Recent Analyses could visually dominate the page — this would turn the workbench into a dashboard and must be controlled through hierarchy and responsive proof.
- Mode clarity changes could break the hidden form contract — preserving `mode` submission and keyboard semantics needs focused tests.
- CSS changes to the front door could regress existing homepage/security/E2E assumptions — final verification must cover old and new selectors.

## Existing Codebase / Prior Art

- `app/routes/analysis.py` — current home route and `/analyze` submit flow; must pass recent summaries while preserving form behavior.
- `app/templates/index.html` — current intake form DOM and Jinja template; primary UI target.
- `app/static/src/ts/modules/form.ts` — current submit enablement, textarea auto-grow, paste feedback, and mode toggle behavior.
- `app/static/src/input.css` — design tokens and component styles for index, mode toggle, history, results, and responsive rules.
- `app/enrichment/history_store.py` — `list_recent(limit)` lightweight history summary contract.
- `app/templates/history.html` — existing Recent Analyses row display and `/history/<id>` links.
- `tests/e2e/pages/index_page.py` and `tests/e2e/test_homepage.py` — existing browser contracts for the homepage.
- `tests/test_history_routes.py` and `tests/test_history_store.py` — existing history summary and failure behavior coverage.

## Relevant Requirements

- R013 — Reactivated input/home page design-language gap; M015 validates it.
- R070 — Fast intake workbench.
- R071 — Preserve paste-to-results flow.
- R072 — Clarified Offline/Online mode choice.
- R073 — Compact Recent Analyses on intake page.
- R074 — History failure does not block intake.
- R075 — Responsive command-card + recent rail layout.
- R076 — Existing extraction, enrichment, history, and security behavior remains intact.
- R077 — Pre-submit extraction preview stays deferred.
- R080/R081/R082 — Heavy dashboard, provider/enrichment changes, and results/detail redesign are out of scope.

## Scope

### In Scope

- Fast home/intake page redesign.
- Dominant paste-and-submit command card.
- Server-rendered compact Recent Analyses rail/list.
- Clarified mode toggle copy/visual state while keeping existing form semantics.
- Quiet no-history and history-unavailable states.
- Desktop and mobile responsive proof.
- Focused backend, TypeScript/build, and browser verification.

### Out of Scope / Non-Goals

- Pre-submit extraction preview.
- Provider/enrichment logic changes.
- Heavy dashboard or equal-weight history/status panels.
- Results/detail page redesign.
- API/automation polish.
- Runtime self-healing or `.planning/**` migration.

## Technical Constraints

- Keep current form action and CSRF behavior.
- Keep `#ioc-text`, `#submit-btn`, `#clear-btn`, `#mode-input`, `#mode-toggle-widget`, and `#mode-toggle-btn` compatible unless tests and downstream code are intentionally updated.
- Avoid a new client-side state system or API endpoint for recent history.
- Use text-safe DOM construction in TypeScript; no `innerHTML` shortcuts.
- Follow quiet precision design language: verdict colors may be loud; chrome stays zinc/muted.
- Preserve existing `HistoryStore.list_recent(limit)` data shape unless a focused, tested extension is necessary.

## Integration Points

- Flask `/` route — supplies recent-analysis summaries to Jinja.
- Flask `/analyze` route — receives unchanged form submission and mode value.
- Flask `/history/<id>` route — compact recent rows link to saved analysis reload.
- SQLite history store — provides lightweight summaries and may fail independently of intake.
- Frontend form module — preserves submit enablement, auto-grow, paste feedback, and mode toggle.
- E2E browser suite — proves fast path, history links, and responsive layout.

## Testing Requirements

- Backend route tests for index rendering with recent entries, no entries, and history-store failure.
- Existing empty-input and online-with-no-provider behavior remains covered or re-checked.
- E2E tests for homepage render, textarea/submit enablement, mode toggle, offline extraction to results, compact recent row visibility/linking, and mobile stacked layout.
- Accessibility checks for keyboard mode toggle, focus-visible behavior, labels/aria, and link names.
- `make verify-fast` and final `make verify` must pass before milestone completion.

## Acceptance Criteria

### S01 — Fast intake command surface

- `/` renders a command-card layout with the paste form as the dominant visual element.
- Textarea auto-grow, paste feedback, Clear, disabled/enabled Extract, CSRF, and offline submit behavior still work.
- Desktop and mobile base layout do not hide or demote the paste form.

### S02 — Mode clarity without semantic churn

- Offline/Online mode choice is clearer through copy, active state, and spacing.
- The hidden `mode` input still posts `offline` or `online` exactly as before.
- Keyboard and aria behavior remain valid.
- Online-with-no-provider redirect/warning behavior remains unchanged.

### S03 — Compact Recent Analyses rail

- Index route fetches a bounded recent-analysis list using `HistoryStore.list_recent(limit)`.
- When entries exist, `/` shows compact recent rows with text, count, verdict, timestamp, and `/history/<id>` link.
- When no entries exist, the recent surface stays quiet.
- When history listing fails, the form still renders and the failure is non-blocking.

### S04 — Integrated intake proof and polish

- Full assembled intake workbench passes desktop and mobile browser checks.
- Fast paste-to-results and recent-analysis resume both work in browser tests.
- Security/CSRF/extraction/history continuity remains intact.
- `make verify-fast` and full `make verify` pass.

## Open Questions

- Exact visual treatment for history-unavailable state: likely a tiny quiet note, but implementation should choose the least distracting option that remains testable.
