# S03: Detail Page Design Refresh

**Goal:** The per-IOC detail page visually matches the M002 quiet precision design language — zinc surfaces, verdict-only color, consistent typography, graph labels untruncated.
**Demo:** Navigate to `/ioc/ipv4/1.2.3.4` with seeded cache data → page renders with `--bg-secondary` card surfaces, `--text-primary`/`--text-secondary` typography, verdict badges using `verdict-badge--*` classes, and graph SVG showing full provider names like "Shodan InternetDB" and "CIRCL Hashlookup" without truncation.

## Must-Haves

- Graph labels show full provider names (no `.slice(0, 12)` or `[:12]` truncation)
- Graph labels show full IOC values (no `.slice(0, 20)` or `[:20]` truncation)
- SVG viewBox accommodates full-length labels without overflow
- Template uses M002 design tokens exclusively (`--bg-secondary`, `--border`, `--text-primary`, `--text-secondary`, `--font-mono`, `--verdict-*`)
- CSS rules for detail page live inside `@layer components` in `input.css`
- No `innerHTML` anywhere — all DOM construction uses `createElement` + `textContent` (SEC-08)
- Inline `<style>` block from CSS-only tabs either removed or moved to `input.css`
- Provider result fields handle missing data gracefully (`{% if %}` guards)
- All 12 existing `test_ioc_detail_routes.py` tests pass
- `make typecheck` passes after graph.ts changes
- `make css && make js` builds without errors
- Bundle stays ≤ 30KB

## Proof Level

- This slice proves: integration (design tokens applied to rendered HTML)
- Real runtime required: no (unit tests verify rendered HTML contains design tokens)
- Human/UAT required: yes (visual inspection of detail page)

## Verification

- `python3 -m pytest tests/test_ioc_detail_routes.py -q` — all 12 tests pass, plus new assertions for M002 design tokens in rendered HTML
- `make typecheck` — exits 0
- `make css && make js` — builds without errors
- `wc -c app/static/dist/main.js` — ≤ 30,720 bytes
- Unit test asserts `data-graph-nodes` contains full provider name (no truncation) and full IOC value

## Observability / Diagnostics

**Runtime signals:**
- `data-graph-nodes` and `data-graph-edges` attributes on `#relationship-graph` in rendered HTML — inspect with DevTools or `pytest` assertions to verify full provider names and IOC values are present without truncation.
- SVG `viewBox` attribute in rendered DOM — should read `0 0 700 450` after the T01 change; inspect via DevTools → Elements panel or `document.querySelector('svg').getAttribute('viewBox')`.

**Inspection surfaces:**
- `curl http://localhost:5000/ioc/ipv4/1.2.3.4 | grep data-graph-nodes` — prints the JSON blob; confirm provider names like "Shodan InternetDB" appear untruncated.
- `python3 -m pytest tests/test_ioc_detail_routes.py -q -v` — each test name identifies which slice feature is covered.
- `wc -c app/static/dist/main.js` — guards against bundle size regression after graph changes.

**Failure visibility:**
- If truncation returns (e.g. a merge reintroduces `[:12]`), the T02 test `test_detail_graph_labels_untruncated` will catch it by asserting "Shodan InternetDB" appears verbatim in `data-graph-nodes`.
- TypeScript type errors in `graph.ts` surface immediately via `make typecheck` (tsc `--noEmit`).
- A bundle size overflow (> 30KB) fails the `wc -c` check added to slice verification.

**Redaction constraints:**
- Graph data contains raw IOC values (IP addresses, hashes, domains) — do not log `data-graph-nodes` contents to persistent application logs; use only in test assertions and local inspection.

## Integration Closure

- Upstream surfaces consumed: design tokens in `input.css` `:root` block (read-only); `.verdict-badge` / `.verdict-label--*` class definitions (reused)
- New wiring introduced in this slice: none (template + CSS only; no new routes, no new JS modules)
- What remains before the milestone is truly usable end-to-end: S04 adds E2E tests asserting M002 tokens on the detail page; S04 integrates all S01–S03 changes

## Tasks

- [x] **T01: Remove graph label truncation and widen SVG viewBox** `est:25m`
  - Why: Provider names like "Shodan InternetDB" (17 chars) and "CIRCL Hashlookup" (16 chars) are truncated to 12 chars in the SVG graph. IOC values are truncated to 20 chars. Both server-side (`routes.py`) and client-side (`graph.ts`) truncate. This must be fixed before the template rewrite since the graph is embedded in the detail page.
  - Files: `app/routes.py`, `app/static/src/ts/modules/graph.ts`
  - Do: (1) In `routes.py` lines 310 and 318, remove `[:20]` and `[:12]` — pass full strings. (2) In `graph.ts` line 154, remove `.slice(0, 12)` from provider label. (3) In `graph.ts` line 184, remove `.slice(0, 20)` from IOC label. (4) Widen SVG viewBox from `0 0 600 400` to `0 0 700 450` and increase `orbitRadius` from 150 to 170 to give labels more radial space. (5) Adjust `cx` from 300→350, `cy` from 200→225 to re-center in the larger viewBox. (6) Reduce provider label font-size from 11→10 to help fit longer names. (7) SEC-08: keep all `createTextNode()` usage intact.
  - Verify: `make typecheck && make js` exits 0; `python3 -m pytest tests/test_ioc_detail_routes.py::TestIocDetailRoute::test_graph_data_in_context -q` passes; `wc -c app/static/dist/main.js` ≤ 30720
  - Done when: graph.ts has no `.slice()` calls on labels, routes.py has no `[:N]` on label strings, SVG viewBox is `0 0 700 450`, and all builds pass

- [x] **T02: Rewrite detail template with M002 design tokens and add CSS rules** `est:1h`
  - Why: The detail page template defines ~20 CSS classes but zero have rules in `input.css` — it renders with only browser defaults. This task rewrites the template to use M002 design patterns and adds the corresponding CSS rules. Also adds unit test assertions proving design tokens are present in rendered HTML (R012 validation).
  - Files: `app/templates/ioc_detail.html`, `app/static/src/input.css`, `tests/test_ioc_detail_routes.py`
  - Do: (1) Rewrite `ioc_detail.html` keeping the same Jinja variables (`ioc_value`, `ioc_type`, `provider_results`, `graph_nodes`, `graph_edges`). Structure: `.page-ioc-detail` wrapper → header with `.back-link` (reuse results page pattern) + IOC value in `<code>` with `font-family: var(--font-mono)` + `.ioc-type-badge--{type}` → graph section with `#relationship-graph` data attrs → provider results as stacked cards (not CSS-only tabs) using `.detail-provider-card` with `--bg-secondary` surface, each showing provider name, `.verdict-badge--{verdict}`, detection count, scan date, cached_at, raw stats in `.provider-detail-row` pattern → empty state. (2) Remove the inline `<style>` block entirely — replace CSS-only radio tabs with simple stacked provider cards (no tabs needed; detail page shows all providers at once). (3) Add CSS rules inside `@layer components` in `input.css` for: `.page-ioc-detail` (width, padding), `.detail-header` (flex layout), `.detail-title-group` (flex, gap, alignment), `.detail-ioc-value` (mono font, secondary color, word-break), `.detail-section-title` (heading weight, spacing), `.detail-graph-section` (card surface, border, padding), `.detail-provider-card` (bg-secondary surface, border, padding, margin), `.detail-result-fields` (definition list layout), `.result-field` (flex row, border-bottom), `.result-field dt` (text-secondary, width), `.result-field dd` (text-primary), `.raw-stats` (nested dl), `.detail-empty` (centered, muted text). (4) Reuse existing classes where possible: `.back-link`, `.ioc-type-badge`, `.verdict-badge`, `.verdict-badge--*`. (5) All `{% if %}` guards for optional fields preserved. (6) Add unit test assertions in `test_detail_page_with_results` confirming: `page-ioc-detail` class present, `verdict-badge--malicious` present (seeded provider has verdict=malicious), `detail-provider-card` present, no inline `<style>` block in rendered HTML. (7) Add a new test `test_detail_graph_labels_untruncated` that seeds a provider with name "Shodan InternetDB" and asserts the full name appears in `data-graph-nodes` JSON without truncation.
  - Verify: `make css && make js` builds; `python3 -m pytest tests/test_ioc_detail_routes.py -q` — all tests pass (12 existing + new assertions); `make typecheck` exits 0; `wc -c app/static/dist/main.js` ≤ 30720
  - Done when: Detail page HTML renders with M002 design tokens (zinc surfaces, verdict-only color), no inline `<style>` block, stacked provider cards instead of radio tabs, all tests pass, build succeeds

## Files Likely Touched

- `app/routes.py` (lines 310, 318 — remove label truncation)
- `app/static/src/ts/modules/graph.ts` (lines 154, 184 — remove `.slice()`, widen viewBox)
- `app/templates/ioc_detail.html` (full rewrite)
- `app/static/src/input.css` (add detail page CSS rules inside `@layer components`)
- `tests/test_ioc_detail_routes.py` (add design token assertions)
