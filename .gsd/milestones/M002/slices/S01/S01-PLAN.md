# S01: Layout skeleton + quiet precision design system

**Goal:** Convert the results page from a 2-column card grid to a single-column full-width row layout with verdict-only color, compressed dashboard, and compact filter bar — while preserving every existing DOM contract selector so TS, filtering, export, and E2E continue to work unchanged.

**Demo:** After submitting IOCs in offline mode, the results page renders as a clean single-column list of full-width rows. Verdict severity badges are the only loud color — type badges, filter pills, and chrome are all muted. The dashboard is a compressed inline summary. The filter bar is a single compact row. All existing functionality (filtering, copy, detail links, enrichment slot presence) works without modification.

## Must-Haves

- `.ioc-cards-grid` renders as single-column at all viewport widths (2-column breakpoint removed)
- `.ioc-card` elements render as full-width horizontal rows, not card boxes
- Verdict color (malicious/suspicious/clean/known_good/no_data) is the only loud color on the page
- `.ioc-type-badge` uses muted neutral styling — no bright type-specific background colors
- Active filter pills use muted styling — no bright type-specific colors
- `#verdict-dashboard` renders as compressed inline summary, not 5 large KPI boxes
- `.filter-bar-wrapper` renders as a single compact row
- All contract selectors preserved unchanged: `.ioc-card`, `#ioc-cards-grid`, `#verdict-dashboard`, `.filter-bar-wrapper`, `.enrichment-slot`, `.ioc-context-line`, `.verdict-label`, `.ioc-type-badge`, `.copy-btn`, `[data-ioc-value]`, `[data-ioc-type]`, `[data-verdict]`, `[data-verdict-count]`, `[data-filter-verdict]`, `[data-filter-type]`, `#filter-search-input`
- `.ioc-context-line` placeholder preserved in row skeleton for S02
- `.enrichment-slot` subtree preserved intact for S02/S03

## Proof Level

- This slice proves: contract (DOM selector contract preserved across layout migration)
- Real runtime required: yes (visual layout verification, filter/copy functional check)
- Human/UAT required: yes (visual design quality — "does this read as professional tooling?")

## Observability / Diagnostics

**Runtime inspection surfaces:**
- `make css` stdout — Tailwind reports unused/unknown classes; any "warn" lines indicate selector drift
- `make typecheck` stderr — TypeScript errors expose broken DOM contract (e.g. `Property X does not exist on type HTMLElement`)
- Flask dev server logs (`flask run`) — template render errors (Jinja2 `UndefinedError`) indicate missing/renamed variables
- Browser devtools → Elements panel: inspect `.ioc-card`, `#ioc-cards-grid`, `#verdict-dashboard` to verify rendered DOM structure

**Failure visibility:**
- CSS compile failure: `make css` exits non-zero; stdout includes the offending Tailwind class or PostCSS error
- TS contract break: `make typecheck` exits non-zero; error message names the missing selector or attribute
- Template error: Flask 500 page in browser with Jinja2 traceback; `flask run` stderr shows the specific partial and line
- Layout regression: Browser renders 2-column grid instead of single column — visible immediately on `/analyze` results page

**Redaction constraints:** No secrets or PII appear in CSS/template files. Build tool output is safe to log.

**Diagnostic check (failure path):**
- After any template edit, verify with: `python -c "from app import create_app; app = create_app(); app.test_client()" 2>&1 | grep -i error` — catches import-time template errors before browser load

## Verification

- `make css` — Tailwind CSS compiles cleanly with reworked design tokens
- `make typecheck` — TypeScript compilation passes (no selector contract breakage in TS)
- `make js-dev` — Browser bundle builds successfully
- `pytest tests/e2e/test_extraction.py -q` — Catches `#ioc-cards-grid`, `.ioc-card`, base results page regressions
- `pytest tests/e2e/test_results_page.py -q` — Catches filter bar, verdict dashboard, enrichment slot structural regressions
- Manual spot check on `/analyze`: submit sample IOCs offline, verify single-column layout, verdict-only color, filter functionality
- `make typecheck` exits non-zero if any DOM contract selector is renamed — inspectable failure state

## Integration Closure

- Upstream surfaces consumed: none (first slice)
- New wiring introduced: none (template + CSS only; no new TS modules or runtime hooks)
- What remains before milestone is truly usable end-to-end: S02 (enrichment at-a-glance), S03 (inline expand), S04 (functionality integration + polish), S05 (E2E suite update)

## Tasks

- [x] **T01: Convert grid layout to single-column rows — restructure templates + structural CSS** `est:1.5h`
  - Why: Delivers R001 (single-column full-width layout). Restructures all template internals for row-based composition and updates layout CSS. This is the structural migration that carries contract-break risk.
  - Files: `app/templates/results.html`, `app/templates/partials/_ioc_card.html`, `app/templates/partials/_verdict_dashboard.html`, `app/templates/partials/_filter_bar.html`, `app/static/src/input.css`
  - Do: (1) Restructure `_ioc_card.html` internals from card header/body/footer to horizontal row layout (identity → meta → actions) while keeping `.ioc-card` root with all data-* attributes, all child hooks (`.ioc-value`, `.ioc-type-badge`, `.verdict-label`, `.copy-btn`, `.ioc-context-line`, `.enrichment-slot`). (2) Compress `_verdict_dashboard.html` internals to inline summary bar — keep `#verdict-dashboard` root, `[data-verdict-count]`, `.verdict-kpi-card[data-verdict]` click targets. (3) Compact `_filter_bar.html` into single-row layout — keep `.filter-bar-wrapper`, `[data-filter-verdict]`, `[data-filter-type]`, `#filter-search-input`. (4) Simplify `results.html` composition around dashboard → filter → list. (5) Update `input.css` structural rules: remove `min-width:768px` 2-column breakpoint on `#ioc-cards-grid`, restyle `.ioc-card` spacing/borders for full-width row feel, compress dashboard CSS, compact filter bar CSS. **Critical constraint:** Do NOT rename/remove any contract selectors. Do NOT restructure `.enrichment-slot` subtree.
  - Verify: `make css` passes; `make typecheck` passes; `make js-dev` passes
  - Done when: Results page renders as single-column full-width rows at all viewport widths, dashboard is compressed, filter bar is a single row, and all three build commands pass

- [x] **T02: Apply quiet precision design system — verdict-only loud color + typography hierarchy** `est:1.5h`
  - Why: Delivers R003 (verdict-only color). Transforms the visual identity from "wall of colored badges" to quiet precision where verdict severity is the only loud signal. Also polishes the structural changes from T01 into a production-quality visual system.
  - Files: `app/static/src/input.css`
  - Do: (1) Mute `.ioc-type-badge--*` variant styles — replace bright background colors with neutral border/text treatment (e.g., subtle gray border, muted text color). (2) Mute active filter pill type colors — `.filter-pill--{type}.filter-pill--active` should use neutral active state, not bright type color. (3) Mute any remaining loud non-verdict accents (mode pills, miscellaneous badges). (4) Refine typography hierarchy for row content: use font-weight, font-size, and opacity to create information hierarchy instead of color (IOC value = prominent, type label = small muted, context line = secondary, actions = quiet). (5) Ensure verdict color tokens remain vivid and are the strongest visual signal — check malicious (red), suspicious (amber), clean (green), known_good (blue), no_data (gray) are distinct and prominent. (6) Polish row hover states, borders, spacing for professional feel. (7) Keep enrichment area visually subordinate — do not make half-rendered enrichment slots prominent. Run full verification: `make css`, `make typecheck`, `make js-dev`, `pytest tests/e2e/test_extraction.py -q`, `pytest tests/e2e/test_results_page.py -q`. **Skill note:** Load the `frontend-design` skill for guidance on typography, color restraint, and production-grade polish. The aesthetic direction is "quiet precision" (D011) — Linear/Vercel energy, not dark-ops density.
  - Verify: `make css` passes; `make typecheck` passes; `make js-dev` passes; `pytest tests/e2e/test_extraction.py -q` passes; `pytest tests/e2e/test_results_page.py -q` passes
  - Done when: Verdict badges are the only loud color anywhere on the results page; type badges, filter pills, and all chrome use muted neutral styling; typography creates clear information hierarchy through weight/size/opacity; all build commands and E2E tests pass

## Files Likely Touched

- `app/templates/results.html`
- `app/templates/partials/_ioc_card.html`
- `app/templates/partials/_verdict_dashboard.html`
- `app/templates/partials/_filter_bar.html`
- `app/static/src/input.css`
