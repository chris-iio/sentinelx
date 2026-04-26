# S03: Compact Recent Analyses rail

**Goal:** Add a compact, failure-tolerant Recent Analyses rail/list to the intake workbench so saved analyses can be resumed from `/` without making history availability a prerequisite for paste-and-extract.
**Demo:** The intake page shows a compact recent-analysis rail/list when history exists, links into `/history/<id>`, and still renders the paste form if history listing fails.

## Must-Haves

- `R073`: GET `/` reads a bounded recent-analysis summary list from `current_app.history_store.list_recent(limit=4)` or an equivalent small limit, passes it to `index.html`, and renders compact links to `/history/<id>` when history exists.
- `R073`: The recent surface remains visually secondary to the command card on desktop and stacks below the command card on mobile; the paste form, mode toggle, and Extract action remain the dominant interaction.
- `R074`: If recent-history listing raises, GET `/` still returns 200, the paste form still renders with the stable S01/S02 selectors, and the page shows a quiet unavailable state or omits the rail rather than propagating the exception.
- `R074`: Empty history is handled deliberately with a compact empty state or no rows; it must not look like a form error and must not disable `#ioc-text` or `#submit-btn` once text is entered.
- `R076` support: S03 must preserve CSRF output, hidden `mode=offline`, offline no-HTTP route behavior, generated asset consistency, TypeScript validity, and the existing offline paste-to-results E2E path for touched surfaces.
- **Verification stopping condition:** `tests/test_index_intake_contract.py` contains focused route/contract assertions for seeded history rows, empty history, and history-store failure; `tests/e2e/test_homepage.py` contains browser assertions for recent-row visibility/linking and desktop/mobile secondary hierarchy; `make build`, `npx tsc --noEmit`, and focused route/E2E commands pass.
- **Threat surface:** GET `/` gains a read-only DB dependency whose rows include analyst-pasted IOC snippets and analysis IDs; rendered text must remain Jinja-escaped, links must be generated with `url_for('main.history_detail', analysis_id=...)`, and no raw results JSON, provider keys, CSRF tokens, secrets, or unbounded input text should be exposed in the recent rail.
- **Abuse:** hostile or malformed stored history text must not inject markup or script, a bad/unknown analysis ID should continue being handled by the existing `/history/<id>` 404 behavior, and history failures must not become a denial-of-service for intake.
- **Input trust:** recent history rows come from local SQLite persistence but still contain previously user-supplied text; treat them as untrusted display data and keep route tests covering HTML escaping or at least non-executable rendering.
- **Requirement impact:** directly owns `R073` and `R074`, supports `R075` responsive hierarchy and `R076` continuity, and preserves validated `R013` command-card contract.
- **Re-verify:** GET `/` HTML contract, recent summary limit, recent link hrefs, empty/unavailable states, paste form selectors, CSRF/security headers, offline no-HTTP behavior, desktop/mobile layout hierarchy, and real browser offline submit to results.
- **Decisions revisited:** keep `D070` by server-rendering summaries from `HistoryStore.list_recent`; keep `D071` by making recent history compact and secondary; keep `D073` by avoiding preview, provider/enrichment rewrites, heavy dashboarding, or a new client/API state system.

## Proof Level

- This slice proves: - This slice proves: integration contract + browser UI proof for server-rendered recent summaries on the intake page.
- Real runtime required: yes — Playwright must exercise the live Flask app so layout, links, and the existing offline submit path are proven in a browser.
- Human/UAT required: no — focused Flask tests, build/typecheck, and Playwright assertions are sufficient for S03.

## Integration Closure

- Upstream surfaces consumed: S01/S02 `app/templates/index.html` command-card shell and stable selectors (`#analyze-form`, `#ioc-text`, `#submit-btn`, `#clear-btn`, `#mode-input`, `#mode-toggle-widget`, `#mode-toggle-btn`), `app/routes/analysis.py` GET `/`, `app/enrichment/history_store.py::HistoryStore.list_recent`, existing `/history/<id>` route in `app/routes/history.py`, existing history row classes in `app/templates/history.html`, and existing E2E live-server fixtures.
- New wiring introduced in this slice: GET `/` fetches a bounded recent summary list fail-open, `index.html` renders recent/empty/unavailable states in the intake workbench, CSS makes the rail compact and secondary, and browser tests seed a deterministic live-server history row for link/layout proof.
- What remains before the milestone is truly usable end-to-end: S04 still needs assembled desktop/mobile polish and full regression proof across command card, clarified mode, recent history resume, extraction/enrichment/history reload, CSRF/security, TypeScript/build, and E2E lanes.

## Verification

- Runtime signals: server warning log when index recent-history lookup fails, plus explicit DOM states such as `.recent-analyses-rail`, `.recent-analysis-row`, `.recent-analyses-empty`, and `.recent-analyses-unavailable` for route/browser inspection.
- Inspection surfaces: `python3 -m pytest -q tests/test_index_intake_contract.py`, `python3 -m pytest -q tests/test_history_routes.py::TestHistoryListRoute`, focused Playwright homepage tests, browser DOM/link assertions, and existing `/history/<id>` route tests.
- Failure visibility: list_recent exceptions become a localized warning and an unavailable/omitted secondary surface while missing rows, broken hrefs, selector churn, or command-card crowding fail focused tests.
- Redaction constraints: logs should summarize the failure class/context only and must not include raw IOC text, full results JSON, provider keys, secrets, or CSRF token values.

## Tasks

- [x] **T01: Wire fail-open recent summaries into the index route and template contract** `est:0.75d`
  Load the `tdd`, `security-review`, and `verify-before-complete` skills before editing. Start with failing route/HTML contract coverage, then add the smallest server-rendered integration from GET `/` to `HistoryStore.list_recent(limit=4)` and `index.html`. Preserve every S01/S02 command-card selector and form behavior while adding recent, empty, and unavailable states as secondary markup.

Quality gates — Failure Modes: if `current_app.history_store.list_recent()` raises, GET `/` must catch it, log a warning without raw IOC content, and still render the command-card form with status 200; if a returned row is missing optional display fields, the template should degrade to safe text rather than breaking the whole page; if `/history/<id>` receives an unknown ID, the existing 404 behavior remains owned by `app/routes/history.py` and must not be changed. Load Profile: GET `/` adds exactly one bounded SQLite read using a small limit and no provider calls, background work, client fetch, or per-row detail loads; 10x homepage traffic should be limited by the existing SQLite read and should fail open if storage is unhealthy. Negative Tests: route tests must cover seeded rows with links, no-history empty/degraded state, `list_recent` exception, preserved CSRF/form selectors, offline no-HTTP behavior, and safe rendering of stored text containing markup-like characters.

Steps:
1. Update `tests/test_index_intake_contract.py` first: replace the old S01 “no recent rail” expectation with S03 contract tests for seeded recent rows, `/history/<id>` hrefs, bounded `list_recent` limit, empty history, fail-open history exceptions, and preservation of `#analyze-form`, `#ioc-text`, `#submit-btn`, `#mode-input`, `#mode-toggle-widget`, and CSRF hidden input.
2. Adjust `tests/test_history_routes.py` only where it has stale expectations that GET `/` never shows recent analyses; keep dedicated `/history` behavior and `/history/<id>` reload tests intact.
3. Update `app/routes/analysis.py` so GET `/` attempts `current_app.history_store.list_recent(limit=4)` inside a narrow try/except, passes `recent_analyses` and a boolean/error-state flag to `render_template('index.html')`, and logs a sanitized warning on failure.
4. Update `app/templates/index.html` to add a compact secondary `<aside>` or section inside `.intake-workbench` for Recent Analyses, rendering linked rows when `recent_analyses` exists, a compact empty state when the list is empty, and a quiet unavailable state when the route flags a history failure; use `url_for('main.history_detail', analysis_id=entry.id)` and keep Jinja autoescaping intact.
5. Run the focused route/contract command and fix only route/template/test issues before handing styling and browser proof to T02.
  - Files: `app/routes/analysis.py`, `app/templates/index.html`, `tests/test_index_intake_contract.py`, `tests/test_history_routes.py`, `app/enrichment/history_store.py`
  - Verify: python3 -m pytest -q tests/test_index_intake_contract.py tests/test_history_routes.py::TestHistoryListRoute tests/test_routes.py::test_offline_mode_makes_no_http_calls tests/test_routes.py::test_security_headers_present

- [x] **T02: Style the compact rail and prove browser resume links without crowding intake** `est:1d`
  Load the `frontend-design`, `make-interfaces-feel-better`, `accessibility`, and `verify-before-complete` skills before editing. Build on T01's server-rendered contract to make the Recent Analyses surface compact, secondary, keyboard/link accessible, and responsive, then seed deterministic live-server history in E2E so browser tests prove row visibility, `/history/<id>` linking, failure-free intake rendering, and unchanged offline extraction.

Quality gates — Failure Modes: if E2E cannot seed a live-server history row, fix the test fixture seam rather than relying on a developer's real `~/.sentinelx/history.db`; if generated CSS/JS are stale, regenerate through `make build` and do not hand-edit `app/static/dist/*`; if the rail reduces the command card below a dominant width or appears above the paste form on mobile, browser geometry assertions must fail. Load Profile: the rail renders at most the bounded rows T01 supplies, uses no client polling/fetch/storage, and adds only constant-time DOM/CSS work in the browser; 10x history volume should not increase index render beyond the route limit. Negative Tests: browser proof must cover seeded history row link href, no recent rows when empty/unavailable state is present, desktop secondary hierarchy, mobile stacking below the command card, submit enablement after IOC input, and offline paste-to-results navigation.

Steps:
1. Update `app/static/src/input.css` so `.intake-workbench` becomes a desktop command-card-plus-rail layout with the command card dominant, `.recent-analyses-rail` visually secondary, compact recent rows reusing or extending existing history row classes, and mobile stacking that places history below the paste command card without horizontal overflow.
2. Run `make build` after CSS changes so `app/static/dist/style.css` (and any generated bundle if the build touches it) reflects source changes.
3. Extend `tests/e2e/pages/index_page.py` with locators/helpers for `.recent-analyses-rail`, `.recent-analysis-row`, recent empty/unavailable states, and a helper that asserts the command card remains before/dominant over the recent rail.
4. Update `tests/e2e/conftest.py` to isolate the live server's `HistoryStore` to a temp database and expose a deterministic seeding helper for homepage E2E tests; keep existing config-store isolation and mocked-online behavior intact.
5. Extend `tests/e2e/test_homepage.py`: replace the stale “no recent rail” assertion with tests proving seeded recent analyses render as links to `/history/<id>`, desktop rail is secondary to the command card, mobile history stacks below the command card, empty/unavailable states do not block form visibility, and the existing offline submit E2E still reaches results.
6. Run the focused build/typecheck/browser command set and fix layout, fixture, or selector regressions without weakening T01's route contract.
  - Files: `app/static/src/input.css`, `app/static/dist/style.css`, `app/static/dist/main.js`, `tests/e2e/pages/index_page.py`, `tests/e2e/conftest.py`, `tests/e2e/test_homepage.py`
  - Verify: make build
npx tsc --noEmit
python3 -m pytest -q tests/e2e/test_homepage.py tests/e2e/test_extraction.py::test_extract_mixed_iocs_offline

## Files Likely Touched

- app/routes/analysis.py
- app/templates/index.html
- tests/test_index_intake_contract.py
- tests/test_history_routes.py
- app/enrichment/history_store.py
- app/static/src/input.css
- app/static/dist/style.css
- app/static/dist/main.js
- tests/e2e/pages/index_page.py
- tests/e2e/conftest.py
- tests/e2e/test_homepage.py
