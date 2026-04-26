# S04: Integrated intake proof and polish

**Goal:** Close the Intake Workbench milestone by proving the assembled command card, clarified mode control, compact Recent Analyses rail, responsive layout, history resume path, and existing extraction/enrichment/history/security/build behavior together in the real application.
**Demo:** The assembled intake workbench is verified on desktop/mobile, fast paste-to-results still works, history resume works, and existing SentinelX verification remains green.

## Must-Haves

- `R076`: Existing extraction, enrichment, history reload, CSRF/security headers, TypeScript build, generated assets, and E2E behavior remain intact after S01/S02/S03 are assembled.
- `R071`: The primary paste → default Offline mode → Extract → results path is re-proven in a live browser with the final command-card plus recent-rail layout present.
- `R075`: Desktop and mobile browser proof shows the command card remains dominant, the Recent Analyses surface stays secondary, and the mobile layout stacks without horizontal overflow.
- `R070`: GET `/` is proven as a fast analyst intake workbench: stable paste form, clarified mode state, submit enablement, and secondary resume rail coexist without preview or dashboard scope creep.
- History resume remains real: a seeded Recent Analyses row links to `/history/<id>` and reloads the saved analysis results route.
- History listing failures remain fail-open: unavailable recent-history state never blocks the paste form, CSRF token, hidden `mode` input, or Extract enablement.
- **Verification stopping condition:** `tests/test_index_intake_contract.py` contains integrated route/HTML contract assertions for command card + mode + recent history + fail-open states; `tests/e2e/test_homepage.py` contains final assembly browser assertions for desktop, mobile, offline extraction, and history resume; `make verify-fast` and the full browser lane `python3 -m pytest -q tests/e2e` pass.
- **Threat surface:** `/` handles untrusted pasted IOC text on submit and displays previously pasted history snippets from SQLite; all rendered stored text must remain escaped, CSRF must remain present, Offline mode must make no outbound HTTP calls, Online mode must retain its configured-provider guard, and no raw provider keys, tokens, CSRF values, or full results JSON should be exposed in the intake rail.
- **Abuse:** malicious stored history text must not inject markup, malformed or missing history row fields must not break index rendering, a broken history store must not become a denial-of-service for intake, and mode/form tampering must continue to follow existing `/analyze` route validation.
- **Input trust:** current textarea content, hidden `mode`, and persisted `input_text` are untrusted; route tests and browser tests must verify safe display, stable hidden input semantics, and no preview/client parsing surface is introduced.
- **Requirement impact:** directly owns `R076`; supports final validation for active `R070`, `R071`, and `R075`; preserves validated `R013`, `R072`, `R073`, and `R074`.
- **Re-verify:** GET `/` HTML contract, CSRF/security headers, offline no-HTTP route behavior, online no-provider redirect, seeded recent links, history reload route, desktop/mobile hierarchy, TypeScript, generated assets, Vitest form behavior, and full Playwright E2E.
- **Decisions revisited:** keep `D070` server-rendered Recent Analyses, `D071` command-card plus compact rail, `D072` hidden-mode-input preservation, and `D073` exclusions for preview, provider/enrichment rewrites, heavy dashboarding, and results/detail redesign.

## Proof Level

- This slice proves: final-assembly contract + live-browser + repository regression proof for the assembled Intake Workbench.
Real runtime required: yes — Playwright must exercise the live Flask app with CSRF enabled, deterministic seeded history, and real `/analyze` + `/history/<id>` routes.
Human/UAT required: no — route tests, Vitest/TypeScript/build checks, and browser assertions are sufficient for this final proof slice.

## Integration Closure

Upstream surfaces consumed: S01 command-card selectors in `app/templates/index.html` and `app/static/src/input.css`; S02 mode contract in `app/static/src/ts/modules/form.ts` and `#mode-input`/`#mode-toggle-widget`/`#mode-toggle-btn`; S03 bounded `HistoryStore.list_recent(limit=4)` context in `app/routes/analysis.py`, `.recent-analyses-*` DOM states, and live E2E history seeding fixtures.
New wiring introduced in this slice: no new production runtime boundary is expected; the slice adds final integrated tests and only minimal polish/fix wiring if those tests expose composition regressions.
What remains before the milestone is truly usable end-to-end: nothing if the final verification lane passes; failures should be fixed inside this slice rather than deferred.

## Verification

- Runtime signals: preserve the sanitized warning log for index recent-history lookup failures and the existing visible DOM states (`.recent-analysis-row`, `.recent-analyses-empty`, `.recent-analyses-unavailable`, `#mode-status`) as diagnostics.
- Inspection surfaces: `python3 -m pytest -q tests/test_index_intake_contract.py`, `make verify-fast`, `python3 -m pytest -q tests/e2e`, browser DOM/link assertions, existing `/history/<id>` route tests, and existing security/header route checks.
- Failure visibility: selector churn, missing CSRF, stale generated assets, broken mode synchronization, history-store exceptions, desktop/mobile crowding, broken resume links, offline network attempts, and E2E regressions fail focused commands before milestone close.
- Redaction constraints: tests and logs must not print raw provider keys, CSRF token values, full pasted payloads beyond synthetic fixtures, or raw exception messages containing IOC text/secrets.

## Tasks

- [x] **T01: Add final assembled route and security contract proof** `est:0.5d`
  Load the `tdd`, `security-review`, and `verify-before-complete` skills before editing. Start with route/HTML contract coverage that treats the final `/` page as one assembled Intake Workbench, not three independent slice fragments. The task should avoid production behavior changes unless the new contract exposes a real regression; preserve the S01/S02/S03 selectors and fail-open recent-history behavior.

Quality gates — Failure Modes: if `current_app.history_store.list_recent(limit=4)` raises, GET `/` and no-input POST `/analyze` must still render status 200 with `#analyze-form`, `#ioc-text`, `#submit-btn`, `#mode-input`, `#mode-toggle-widget`, CSRF, and a quiet unavailable recent-history state; malformed or missing optional row fields must render safe fallback text; unknown `/history/<id>` behavior remains owned by the existing history route. Load Profile: GET `/` must still do at most one bounded history summary read and no provider calls, background work, polling, or per-row detail loads. Negative Tests: contract tests must cover stored text escaping, no pre-submit preview rail, absent raw results/provider secrets, no-HTTP Offline behavior, Online-without-provider redirect, CSRF/security headers, and sanitized recent-history failure logging.

Steps:
1. Extend `tests/test_index_intake_contract.py` with an integrated workbench contract test that seeds recent rows through a mocked store and asserts command-card selectors, clarified mode copy/status, hidden `mode=offline`, recent row `/history/<id>` links, no preview surfaces, bounded `list_recent(limit=4)`, and escaped stored input text in the same GET `/` response.
2. Add or tighten a fail-open no-input POST contract in `tests/test_index_intake_contract.py` so validation errors that re-render `index.html` still include the recent-history unavailable/empty context plus the full paste form and CSRF contract.
3. If the tests expose a real route/template bug, make the smallest fix in `app/routes/analysis.py` or `app/templates/index.html`; do not introduce a new API, client fetch, preview extraction, provider call, or dashboard surface.
4. Run the focused route/security command and fix failures without weakening the assertions.
  - Files: `tests/test_index_intake_contract.py`, `app/routes/analysis.py`, `app/templates/index.html`, `tests/test_routes.py`, `tests/test_history_routes.py`
  - Verify: python3 -m pytest -q tests/test_index_intake_contract.py tests/test_routes.py::test_offline_mode_makes_no_http_calls tests/test_routes.py::test_analyze_online_without_api_key_redirects_to_settings tests/test_routes.py::test_security_headers_present tests/test_routes.py::test_csrf_token_required tests/test_history_routes.py

- [ ] **T02: Add final browser assembly proof and responsive polish** `est:1d`
  Load the `frontend-design`, `make-interfaces-feel-better`, `accessibility`, and `verify-before-complete` skills before editing. Build on T01's route contract by proving the assembled workbench in a live browser at desktop and mobile sizes, including seeded history resume and the real Offline paste-to-results path. Prefer test/page-object additions first; touch CSS or generated assets only for concrete responsive/polish regressions exposed by the browser assertions.

Quality gates — Failure Modes: if seeded history cannot be created, fix the E2E fixture seam rather than relying on a developer-local `~/.sentinelx/history.db`; if history lookup is unavailable, the browser must still see the form and enabled Extract after text entry; if a recent row link is broken, the click must fail before slice close; if generated assets are stale after CSS/TS fixes, regenerate with `make build` rather than hand-editing `app/static/dist/*`. Load Profile: browser proof should use one or a few deterministic seeded rows, no client polling/fetch/storage, no external provider calls for Offline mode, and no extra runtime beyond existing live-server fixtures. Negative Tests: E2E must cover desktop secondary hierarchy, mobile stacking without horizontal overflow, empty/unavailable recent states, stable mode state, history resume link navigation, and real Offline extraction results.

Steps:
1. Extend `tests/e2e/pages/index_page.py` with any missing high-level helper(s) needed to assert the integrated workbench is ready: command card visible, mode state synchronized, recent rail visible/secondary, row href present, mobile rail below the command card, and no preview surfaces.
2. Add final assembly tests in `tests/e2e/test_homepage.py` that seed deterministic history, assert desktop command-card dominance with the recent rail present, assert mobile stacking/no overflow with the same assembled UI, click a recent row to prove `/history/<id>` resume, and re-prove Offline paste-to-results from the final layout.
3. Preserve or strengthen existing empty/unavailable recent-history tests so they prove the form remains usable and `#submit-btn` enables after IOC text even when history is absent or failing.
4. If assertions reveal composition polish issues, adjust `app/static/src/input.css` only as needed to keep the command card dominant, the rail compact/secondary, focus states visible, and mobile layout overflow-free; then run `make build` to refresh `app/static/dist/style.css` and `app/static/dist/main.js`.
5. Run the focused browser command, then the full browser lane; fix selector, fixture, CSS, or generated-asset regressions without weakening T01's route contract.
  - Files: `tests/e2e/pages/index_page.py`, `tests/e2e/test_homepage.py`, `tests/e2e/test_extraction.py`, `tests/e2e/test_ui_controls.py`, `app/static/src/input.css`, `app/static/dist/style.css`, `app/static/dist/main.js`
  - Verify: python3 -m pytest -q tests/e2e/test_homepage.py tests/e2e/test_ui_controls.py tests/e2e/test_extraction.py::test_extract_mixed_iocs_offline && make verify-fast && python3 -m pytest -q tests/e2e

## Files Likely Touched

- tests/test_index_intake_contract.py
- app/routes/analysis.py
- app/templates/index.html
- tests/test_routes.py
- tests/test_history_routes.py
- tests/e2e/pages/index_page.py
- tests/e2e/test_homepage.py
- tests/e2e/test_extraction.py
- tests/e2e/test_ui_controls.py
- app/static/src/input.css
- app/static/dist/style.css
- app/static/dist/main.js
