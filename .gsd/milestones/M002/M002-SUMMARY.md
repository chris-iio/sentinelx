---
id: M002
provides:
  - Single-column full-width IOC row layout replacing 2-column card grid (#ioc-cards-grid, .ioc-card flex-column)
  - Quiet precision design system — verdict-only color (--verdict-*), all type badges and chrome muted to zinc neutrals
  - At-a-glance enrichment surface — verdict badge, context line, provider stat line, verdict-proportion micro-bar, staleness badge; full opacity on .enrichment-slot--loaded
  - Inline expand/collapse — .ioc-summary-row as whole-row click target; event delegation on .page-results; animated chevron; aria-expanded; keyboard Enter/Space
  - "View full detail →" link injected into expanded panel via injectDetailLink() with encodeURIComponent href
  - Full integration verification — export (JSON/CSV/clipboard), verdict/type/text filtering, progress bar, copy buttons all wired and passing
  - Security audit clean — CSP header, CSRF protection, SEC-08 textContent-only DOM construction, zero eval/document.write violations
  - Production bundle gate — 27,226 bytes (≤ 30KB)
  - E2E suite expanded from 91 to 99 tests with Playwright route-mocking infrastructure covering all enrichment surface elements
key_decisions:
  - D010 — Single-column full-width IOC rows replacing 2-column card grid
  - D011 — Quiet precision design: verdict-only color, muted typographic hierarchy for all chrome
  - D012 — Inline expand below IOC row (no page navigation for 80% triage case)
  - D013 — At-a-glance surface shows verdict + geo/ASN/DNS context + provider numbers without interaction
  - D014 — Compact inline summary bar replaces 5 large KPI boxes
  - D015 — All existing selector names preserved in place; no renames in S01–S04
  - D016 — BEM modifier opacity pattern: .enrichment-slot base at 0.85; .enrichment-slot--loaded overrides to 1 with 0.2s ease
  - D017 — Always verify prior task key_files via git show --stat before building on them
  - D018 — Event delegation on .page-results for wireExpandToggles() — summary rows don't exist at init() time
  - D019 — Save chevron wrapper reference before summaryRow.textContent="" clear, re-append after rebuild
  - D020 — injectDetailLink() called from markEnrichmentComplete() with .detail-link-footer idempotency guard
  - D021 — Brand name "sentinelx" stays all-lowercase in <title>; tests match template
  - D022 — Regex class-match (r".*is-open.*") in to_have_class() for co-existing CSS classes
  - D023 — Register Playwright page.route() BEFORE the page action that triggers the fetch
patterns_established:
  - Quiet precision design: restrict loud color to verdict classes only; all chrome/meta elements use zinc neutrals
  - BEM modifier opacity override: base class sets dimmed loading state; --loaded modifier restores full opacity with transition
  - Event delegation on stable ancestor for dynamically-created enrichment DOM elements (wireExpandToggles pattern)
  - Clear-and-rebuild containers: save persistent child references before textContent="" and re-append after
  - Run-once injection: hook into completion callback with querySelector idempotency guard
  - Playwright route-mocking: register before navigation, use **/enrichment/status/** double-glob pattern
observability_surfaces:
  - "python3 -m pytest tests/e2e/ -q → 99 passed, 0 failed — primary integration signal"
  - "make typecheck → exit 0 — primary TS wiring signal after any module edit"
  - "wc -c app/static/dist/main.js → 27226 bytes; gate is 30000"
  - "grep -rn 'document\.write\|eval(' app/static/src/ts/ → exit 1 means zero matches (zero-tolerance security gate)"
  - "grep 'bg-hover' app/static/dist/style.css → confirms --bg-hover token compiled"
  - "grep -n 'enrichment-slot--loaded' app/static/src/input.css → opacity:1 rule on ~line 1154"
requirement_outcomes:
  - id: R001
    from_status: active
    to_status: validated
    proof: S01 added display:flex;flex-direction:column to .ioc-card; #ioc-cards-grid uses grid-template-columns:1fr with no 2-column breakpoint; confirmed by 99/99 E2E tests passing and grep confirming zero grid-cols-2 or repeat(2 in input.css
  - id: R002
    from_status: active
    to_status: validated
    proof: S02 delivered enrichment slot CSS — .enrichment-slot--loaded opacity:1 override, context-line padding fix, micro-bar min/max-width tuned; row-factory.ts and enrichment.ts already wired verdict badge, context line, provider stat line, micro-bar, staleness badge into .enrichment-slot; S05 added 8 enrichment surface E2E tests confirming .ioc-summary-row, .verdict-micro-bar, .enrichment-slot--loaded all present after route-mocked polling; 99/99 passing
  - id: R003
    from_status: active
    to_status: validated
    proof: S01 collapsed all 8 IOC type badge variants to single zinc neutral rule; S03 confirmed expanded panel uses only design tokens (--bg-secondary, --border, --text-secondary, --text-primary, --bg-hover); S04 T02 grep audit confirmed zero bright non-verdict colors; 99/99 E2E passing
  - id: R004
    from_status: active
    to_status: validated
    proof: S03 delivered .ioc-summary-row as whole-row click target; wireExpandToggles() event delegation on .page-results; .enrichment-details toggles .is-open; aria-expanded state maintained; keyboard Enter/Space supported; injectDetailLink() injects "View full detail →" with encodeURIComponent href; S05 test_expand_collapse_ioc_row confirms toggle behavior; 99/99 E2E passing
  - id: R005
    from_status: active
    to_status: validated
    proof: S01 restructured _verdict_dashboard.html to flex-direction:row with border-right dividers; S04 T01 wiring matrix confirmed filter.ts binds .verdict-kpi-card[data-verdict] for click-to-filter; dashboard counts rendered with verdict-colored text; 99/99 E2E passing
  - id: R006
    from_status: active
    to_status: validated
    proof: S01 restructured _filter_bar.html to single flex row with flex-wrap; S04 T01 wiring matrix confirmed all filter functionality (verdict toggle, type toggle, text search) intact; 99/99 E2E passing including filter-specific tests
  - id: R007
    from_status: active
    to_status: validated
    proof: S03 delivered expand/collapse gate — provider details hidden by default in .enrichment-details, revealed on deliberate click/keypress; "View full detail →" link only visible in expanded state; summary row always shows at-a-glance surface; S05 test_enrichment_section_in_expanded_row and test_detail_link_injected confirm progressive disclosure behavior; 99/99 E2E passing
  - id: R008
    from_status: active
    to_status: validated
    proof: S04 T01 produced 18-point wiring verification matrix (file:line evidence); allResults[] → export.ts via closure confirmed; filter.ts, cards.ts, clipboard.ts, progress bar, copy buttons all verified intact; 91/91 E2E at S04 close; 99/99 at S05 close
  - id: R009
    from_status: active
    to_status: validated
    proof: S04 T02 six grep-based security checks — CSP at app/__init__.py:71; CSRFProtect + <meta name="csrf-token"> in base.html; innerHTML occurrences JSDoc comments only; document.write/eval() grep exit 1 (zero matches); all .style.xxx are DOM property access; row-factory.ts and enrichment.ts use createElement/createElementNS+textContent+setAttribute throughout
  - id: R010
    from_status: active
    to_status: validated
    proof: S04 T03 production bundle 27,226 bytes (≤ 30KB gate); 750ms polling interval, dedup, and debounced sort patterns confirmed unchanged in enrichment.ts and cards.ts; build gate reproducible via wc -c app/static/dist/main.js
  - id: R011
    from_status: validated
    to_status: validated
    proof: Already validated in S05 — python3 -m pytest tests/e2e/ -q → 99 passed, 0 failed; ResultsPage page object expanded from 118 to 266 lines; 8 new enrichment surface tests added; no tests removed
duration: ~2h total (S01: ~35m, S02: ~27m, S03: ~30m, S04: ~30m, S05: ~38m)
verification_result: passed
completed_at: 2026-03-18
---

# M002: Results Page Rework

**Full information-first redesign of the SentinelX results page: single-column layout, quiet precision design, at-a-glance enrichment surface, inline expand/collapse, full integration and security audit verified — 99/99 E2E tests passing with Playwright route-mocking infrastructure covering all new enrichment surface elements.**

## What Happened

Five slices executed in strict dependency order, each building on a frozen DOM contract from the previous slice.

**S01 (Layout skeleton + quiet precision design system)** established the structural foundation in two CSS-focused tasks. The worktree was initialized with the target DOM structure largely in place — the primary addition was `display:flex;flex-direction:column` on `.ioc-card`. T02 executed the full quiet precision pass: all 8 IOC type badge variants collapsed to a single zinc neutral rule, type-active filter pills replaced with a neutral active block, the mode indicator muted from bright accent to zinc, and verdict KPI counts in the dashboard assigned verdict-specific text colors as a secondary signal. Typography hierarchy was refined via weight/size/opacity rather than color. The D015 decision (preserve all existing selector names, mutate internals in place) de-risked the entire milestone — no cascading renames across cards.ts, filter.ts, ui.ts, or E2E selectors.

**S02 (At-a-glance enrichment surface)** was a targeted CSS refinement. The TypeScript enrichment pipeline (enrichment.ts, row-factory.ts) already wired `.enrichment-slot--loaded` onto enriched rows and populated verdict badge, context line, provider stat line, micro-bar, and staleness badge — but the CSS had no rule responding to that class. Enriched content was permanently rendered at `opacity: 0.85`. S02 added the BEM modifier override (`.enrichment-slot.enrichment-slot--loaded { opacity: 1; transition: opacity 0.2s ease }`), fixed a double-indent on `.ioc-context-line` (the `.ioc-card` `1rem` horizontal padding was already inherited — the explicit `1rem` left padding was additive), and tuned `.verdict-micro-bar` to `min-width: 5rem; max-width: 8rem` for the full-width single-column context. A process safeguard was documented (D017): T01's commit had only saved `.gsd` docs, not the CSS change — T02 discovered this via `git show --stat` and applied all three fixes, establishing the verify-prior-task-commit pattern.

**S03 (Inline expand + progressive disclosure)** replaced the old standalone `<button class="chevron-toggle">` interaction model with a whole-row click target. `getOrCreateSummaryRow()` in `row-factory.ts` injects a chevron SVG wrapper with `margin-left:auto` and sets `role="button"`, `tabindex="0"`, `aria-expanded="false"` on the summary row. `wireExpandToggles()` in `enrichment.ts` was rewritten with event delegation on `.page-results` (D018) — direct `querySelectorAll` at `init()` time would bind 0 handlers since rows are created during polling. A second necessary correction: `updateSummaryRow()` uses `summaryRow.textContent = ""` as an immutable-rebuild pattern — this destroyed the chevron wrapper on each incremental update. The fix saves the chevron reference before the clear and re-appends it after (D019, documented in KNOWLEDGE.md). T02 added `injectDetailLink()` in `enrichment.ts`, called from `markEnrichmentComplete()` with a `.detail-link-footer` idempotency guard (D020) — it reads `data-ioc-type` and `data-ioc-value` from the nearest `.ioc-card` and constructs `/detail/<type>/<encodeURIComponent(value)>`. CSS additions: expanded panel background tint, left border accent, detail link styles, hover state on summary row — all muted design tokens, R003 compliant.

**S04 (Functionality integration + polish)** was a verification-only slice — no feature code was required. T01 produced an 18-point wiring verification matrix confirming every integration connection intact: `allResults[]` accumulation in `enrichment.ts` feeds `export.ts` via module-private closure; `filter.ts` binds `.verdict-kpi-card[data-verdict]`; `cards.ts` `doSortCards()` queries `#ioc-cards-grid` for `.ioc-card` children; progress bar and warning elements present in `results.html`; `.copy-btn[data-value]` in `_ioc_card.html`; `injectDetailLink()` fires from `markEnrichmentComplete()`. T02 confirmed all six security contracts via grep-based audit — zero violations. T03 confirmed the `--bg-hover` token at `input.css:53` (`#3f3f46` / zinc-700), all S03 CSS artifacts present in dist, and the production bundle at 27,226 bytes (≤ 30KB gate). Running the full 91-test suite (vs. the 36-test subset used in earlier tasks) surfaced two pre-existing title-case drift failures in homepage/settings tests; both were fixed by matching the intentional `"sentinelx"` brand casing in the template (D021).

**S05 (E2E test suite update)** closed the coverage gap. The 91-test suite was passing but had zero coverage of the new enrichment surface elements. T01 expanded `results_page.py` from 118 to 266 lines with 18+ new locator properties and 5 helper methods (`summary_row_for_card`, `enrichment_details_for_card`, `expand_row`, `collapse_row`, `is_row_expanded`) — all card-scoped via `data-ioc-value` attribute targeting for stability. T02 built the Playwright route-mocking infrastructure (`MOCK_ENRICHMENT_RESPONSE_8888`, `setup_enrichment_route_mock()`, `mocked_enrichment` fixture in `conftest.py`) and added 8 new tests covering inline expand/collapse, enrichment summary row, micro-bar, detail link injection, `--loaded` state, and an offline-mode guard. Key pattern established (D023): route mocks must be registered before navigation to avoid racing the 750ms first poll tick. The detail link href assertion was corrected from `/ioc/` to `/detail/` — the Flask route generates `/detail/<ioc_type>/<ioc_value>`. Final result: 99/99 passing.

## Cross-Slice Verification

Each milestone success criterion maps to specific evidence:

| Success Criterion | Evidence |
|---|---|
| Analyst sees verdict severity, real-world context, key provider numbers at a glance | S02: `.enrichment-slot--loaded` opacity:1 override; context line padding fix; micro-bar width tuned. S05 E2E: `test_enrichment_summary_row_visible`, `test_verdict_micro_bar_present` pass. 99/99. |
| Information hierarchy immediately legible | S01: 8 type badge variants → single zinc neutral; filter pills muted; typography hierarchy via weight/size/opacity. S04 T02: grep audit confirms no bright non-verdict colors in dist. |
| Full provider details via inline expand, no page navigation | S03: `.ioc-summary-row` click target; event delegation; `.is-open` toggle; `aria-expanded`; keyboard support; detail link. S05: `test_expand_collapse_ioc_row` and `test_detail_link_injected` pass. 99/99. |
| All existing functionality works | S04 T01: 18-point wiring matrix. 91/91 → 99/99 E2E passing. |
| Visual design reads as professional production tooling | S04 T03: `--bg-hover` token confirmed, all polish CSS in dist, production bundle 27,226 bytes. S03 expanded panel bg/border/padding consistent with design tokens. |

**Definition of Done — all conditions met:**
- ✅ All IOC types render correctly in single-column layout with verdict-only color (S01, S02)
- ✅ At-a-glance surface shows verdict + context + provider numbers for enriched IOCs (S02)
- ✅ Inline expand works for full provider breakdown (S03)
- ✅ Dashboard and filter bar compressed and functional (S01 structural, S04 wiring verified)
- ✅ Enrichment polling renders progressively into new layout (S02+S03)
- ✅ Export produces correct JSON/CSV/clipboard output (S04)
- ✅ Security contracts verified — CSP, CSRF, SEC-08 (S04)
- ✅ E2E test suite passes with updated selectors (S05: 99/99)

## Requirement Changes

- R001: active → validated — S01 single-column layout confirmed by 99/99 E2E; zero `grid-cols-2` or `repeat(2` in input.css
- R002: active → validated — S02 enrichment slot CSS complete; S05 E2E confirms all at-a-glance elements render after route-mocked polling
- R003: active → validated — S01 type badge muting + S03 design-token-only expanded panel + S04 T02 grep audit
- R004: active → validated — S03 full inline expand implementation; S05 expand/collapse and detail link E2E tests pass
- R005: active → validated — S01 compact dashboard structure + S04 T01 click-to-filter wiring confirmed
- R006: active → validated — S01 single-row filter bar + S04 T01 full filter wiring confirmed
- R007: active → validated — S03 expand/collapse gate hides provider details by default; S05 progressive disclosure E2E tests pass
- R008: active → validated — S04 18-point wiring matrix + 91/91 (→ 99/99) E2E
- R009: active → validated — S04 T02 six grep-based security checks; zero violations across all contracts
- R010: active → validated — S04 production bundle 27,226 bytes ≤ 30KB; polling/sort patterns unchanged
- R011: validated → validated — S05 expanded to 99 passing (from 91 baseline); page object 118 → 266 lines

## Forward Intelligence

### What the next milestone should know

- **DOM selector contract is stable and well-tested.** All `.ioc-card`, `#ioc-cards-grid`, `.verdict-kpi-card[data-verdict]`, `.ioc-summary-row`, `.enrichment-details`, `.enrichment-slot`, `.enrichment-slot--loaded`, `.detail-link-footer`, `.detail-link`, `.chevron-icon-wrapper`, `.verdict-micro-bar`, `.staleness-badge` are in final positions with 99 E2E tests covering them. Any downstream work can rely on these selectors without reverification.
- **Route-mocking infrastructure is production-quality and reusable.** `setup_enrichment_route_mock(page)` + `mocked_enrichment` fixture in `conftest.py` simulate complete enrichment without external APIs. Any future enrichment surface work can use this without modification.
- **Event delegation is the required pattern for all dynamically-created enrichment DOM.** Bind to `.page-results`, not directly on elements created during polling. Binding at `init()` time wires 0 handlers.
- **`markEnrichmentComplete()` is the right hook for post-enrichment injection.** It already iterates `.enrichment-slot--loaded` slots — any "run once at completion" behavior should use this hook with a querySelector idempotency guard.
- **R012 (detail page refresh) and R013 (input page refresh) are explicitly deferred.** The detail page and input page both work correctly; they simply use the pre-rework design language. Both are low risk as standalone milestones.
- **Full E2E suite is 99 tests (`pytest tests/e2e/ -q`).** The 36-test subset (`test_results_page.py + test_extraction.py`) is no longer the full gate. Always run the complete suite.
- **`python3` not `python`** — system PATH does not alias `python`. Use `python3 -m pytest` directly.

### What's fragile

- **`allResults[]` closure in `enrichment.ts`** — `export.ts` consumes it via the same module scope, not a global. If `enrichment.ts` is ever split or refactored, this coupling must be preserved or explicitly re-wired.
- **`**/enrichment/status/**` route glob pattern** — if the Flask URL structure for the enrichment status endpoint changes, E2E route mocks will silently fail to intercept. Diagnostic: `loaded_enrichment_slots.count()` returns 0.
- **`--bg-hover` token** — defined at `input.css:53` as `#3f3f46`. If input.css is substantially reorganized, verify the token definition survives. Absence causes the summary row hover state to silently fail.
- **Browserslist caniuse-lite deprecation warning** — present in `make css`/`make js-dev` output, non-blocking but will eventually require `npx update-browserslist-db@latest`.

### Authoritative diagnostics

- `python3 -m pytest tests/e2e/ -q` — pass/fail verdict for the full suite (99 tests); single most important gate
- `make typecheck` → exit 0 — any TS module import error surfaces here before runtime
- `wc -c app/static/dist/main.js` → 27,226 bytes; gate is 30,000; growth beyond 29KB warrants investigation
- `grep -rn 'document\.write\|eval(' app/static/src/ts/` → exit 1 means zero matches (zero-tolerance security gate; exit 0 with output means violation)
- `grep 'bg-hover' app/static/dist/style.css` → confirms `--bg-hover` token compiled

### What assumptions changed

- **"Substantial template restructuring needed" (S01 plan)** — the worktree was initialized with the target DOM structure largely in place. Only the single CSS addition to `.ioc-card` was required. Re-verify actual file state rather than trusting plan descriptions of expected pre-existing state.
- **"S02 = new TS DOM builders" (roadmap)** — the TS pipeline already built and wired the enrichment surface. S02 was a CSS-only refinement (opacity override, padding fix, micro-bar tuning).
- **"36/36 pass is the verification gate"** — the actual full suite is 99 tests. The 36-test subset covers only `test_results_page.py` + `test_extraction.py`. Always run `pytest tests/e2e/ -q` for complete coverage.
- **"Detail links use /ioc/ path"** — actual Flask route generates `/detail/<ioc_type>/<ioc_value>`. Always inspect actual Flask route table or live DOM before writing URL-content assertions.

## Files Created/Modified

- `app/static/src/input.css` — Single-column layout, flex-column .ioc-card, quiet precision design tokens, enrichment slot opacity, context line padding, micro-bar sizing, expand/collapse CSS, detail link styles, hover states (S01–S04)
- `app/static/dist/style.css` — Rebuilt Tailwind CSS artifact
- `app/static/dist/main.js` — Rebuilt esbuild production bundle (27,226 bytes)
- `app/templates/partials/_ioc_card.html` — Layout structure (S01)
- `app/templates/partials/_verdict_dashboard.html` — Compact flex-row dashboard (S01)
- `app/templates/partials/_filter_bar.html` — Single-row filter bar (S01)
- `app/templates/partials/_enrichment_slot.html` — Removed standalone chevron-toggle button (S03)
- `app/templates/results.html` — Progress bar, warning elements verified present (S04)
- `app/static/src/ts/modules/row-factory.ts` — Chevron SVG injection, a11y attrs, chevron save/restore across textContent clear (S03)
- `app/static/src/ts/modules/enrichment.ts` — wireExpandToggles() with event delegation, injectDetailLink(), markEnrichmentComplete() hook (S03)
- `app/__init__.py` — CSP header verified present (S04 audit)
- `app/templates/base.html` — CSRF meta tag verified present (S04 audit)
- `tests/e2e/pages/results_page.py` — Expanded from 118 to 266 lines; 18+ new locators, 5 helper methods (S05)
- `tests/e2e/test_results_page.py` — 8 new enrichment surface tests + _navigate_online_with_mock() helper (S05)
- `tests/e2e/conftest.py` — Route-mocking infrastructure: MOCK_ENRICHMENT_RESPONSE_8888, setup_enrichment_route_mock(), mocked_enrichment fixture (S05)
- `tests/e2e/test_extraction.py` — test_responsive_grid_layout docstring updated to single-column (S05)
- `tests/e2e/test_homepage.py` — Title assertion updated to "sentinelx" (D021, S04)
- `tests/e2e/test_settings.py` — Title assertion updated to "sentinelx" (D021, S04)
