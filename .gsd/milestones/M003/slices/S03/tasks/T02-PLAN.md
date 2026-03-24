---
estimated_steps: 5
estimated_files: 4
---

# T02: Rewrite detail template with M002 design tokens and add CSS rules

**Slice:** S03 — Detail Page Design Refresh
**Milestone:** M003

## Description

The detail page (`ioc_detail.html`) defines ~20 CSS classes but **zero** have rules in `input.css` — it renders with only browser defaults and inherited base styles. The inline `<style>` block handles only a CSS-only tab radio visibility hack. This task rewrites the template to use M002 design patterns (zinc surfaces, verdict-only color, consistent typography) and adds all CSS rules to `input.css` inside `@layer components`. It also replaces the CSS-only radio tabs with simple stacked provider cards — showing all providers at once rather than hiding behind tabs. Finally, it adds unit test assertions proving the M002 design tokens are present in rendered HTML, which is the validation evidence for requirement R012.

**Relevant skills:** None needed — this is HTML template + CSS + Python test work.

**Important constraints:**
- CSS rules MUST go inside `@layer components` block in `input.css` (starts at line 228)
- Reuse existing design tokens — do NOT define new custom properties
- Reuse existing classes where they match: `.back-link`, `.ioc-type-badge`, `.ioc-type-badge--*`, `.verdict-badge`, `.verdict-badge--*`
- All Jinja variables stay the same: `ioc_value`, `ioc_type`, `provider_results`, `graph_nodes`, `graph_edges` (the route handler is unchanged)
- SEC-08: no `innerHTML` — template uses Jinja autoescaping, which is safe
- The Flask route is `/ioc/<type>/<value>` — do NOT change this. The `injectDetailLink()` in enrichment.ts uses `/detail/<type>/<value>` which is a pre-existing known issue; do NOT fix it here.

## Steps

1. **Add detail page CSS rules to `app/static/src/input.css`** inside `@layer components`. Add these rules after the existing `.detail-link:hover` rule (around line 1393) and before the `/* ---- Phase 4 Results UX — Provider detail rows ---- */` comment (line 1393). Rules to add:

   ```
   /* ---- Detail page (M002 design refresh) ---- */
   .page-ioc-detail { width: 100%; max-width: 72rem; margin: 0 auto; padding: 2rem 1rem; }
   .detail-header { display: flex; align-items: center; gap: 1rem; margin-bottom: 2rem; flex-wrap: wrap; }
   .detail-title-group { display: flex; align-items: center; gap: 0.75rem; flex: 1; min-width: 0; }
   .detail-ioc-value { font-family: var(--font-mono); font-size: 1.125rem; color: var(--text-primary); word-break: break-all; }
   .detail-section-title { font-size: 0.85rem; font-weight: var(--weight-heading); color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 1rem; }
   .detail-graph-section { background: var(--bg-secondary); border: 1px solid var(--border-default); border-radius: 0.5rem; padding: 1.5rem; margin-bottom: 2rem; }
   .detail-results-section { margin-bottom: 2rem; }
   .detail-provider-card { background: var(--bg-secondary); border: 1px solid var(--border-default); border-radius: 0.5rem; padding: 1.25rem; margin-bottom: 0.75rem; }
   .detail-provider-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; }
   .detail-provider-name { font-size: 0.95rem; font-weight: var(--weight-heading); color: var(--text-primary); }
   .detail-result-fields { display: grid; gap: 0; }
   .result-field { display: flex; align-items: baseline; padding: 0.5rem 0; border-bottom: 1px solid var(--border); }
   .result-field:last-child { border-bottom: none; }
   .result-field dt { width: 9rem; flex-shrink: 0; font-size: 0.8rem; font-weight: var(--weight-caption); color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.04em; }
   .result-field dd { font-size: 0.875rem; color: var(--text-primary); }
   .result-field--raw dd { width: 100%; }
   .raw-stats { display: grid; gap: 0; }
   .raw-stat-entry { display: flex; align-items: baseline; padding: 0.25rem 0; border-bottom: 1px solid var(--border); }
   .raw-stat-entry:last-child { border-bottom: none; }
   .raw-stat-entry dt { width: 12rem; flex-shrink: 0; font-size: 0.78rem; color: var(--text-muted); font-family: var(--font-mono); }
   .raw-stat-entry dd { font-size: 0.78rem; color: var(--text-secondary); font-family: var(--font-mono); }
   .detail-empty { text-align: center; padding: 4rem 2rem; color: var(--text-secondary); }
   .detail-empty p { margin-bottom: 1rem; }
   .graph-empty { text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.85rem; }
   ```

   Use ONLY existing design tokens (`--bg-secondary`, `--border`, `--border-default`, `--text-primary`, `--text-secondary`, `--text-muted`, `--font-mono`, `--weight-heading`, `--weight-caption`). Do not create new custom properties.

2. **Rewrite `app/templates/ioc_detail.html`** — Replace the entire template content. Keep `{% extends "base.html" %}` and `{% block content %}`. New structure:

   - `.page-ioc-detail` wrapper with `data-ioc-value` and `data-ioc-type` attributes (unchanged)
   - Header: `.detail-header` containing `.back-link` (SVG arrow + "Back", same as current but linking to `url_for('main.index')`) and `.detail-title-group` with `<code class="detail-ioc-value">{{ ioc_value }}</code>` + `<span class="ioc-type-badge ioc-type-badge--{{ ioc_type }}">{{ ioc_type | upper }}</span>`
   - Graph section: `.detail-graph-section` with `.detail-section-title` "Provider Relationships" and `#relationship-graph` div with `data-graph-nodes` and `data-graph-edges` (unchanged data attribute wiring)
   - Results section: `.detail-results-section` with `.detail-section-title` "Enrichment Results"
     - If no `provider_results`: `.detail-empty` with message and "Analyze IOC" button
     - If results: iterate `provider_results` — each provider gets a `.detail-provider-card` containing:
       - `.detail-provider-header` with `.detail-provider-name` (provider name) + `.verdict-badge.verdict-badge--{{ verdict }}` (verdict badge)
       - `<dl class="detail-result-fields">` with `.result-field` entries for: Detections (if present), Scan Date (if present), Cached At (if present), Raw Stats (if present, using nested `.raw-stats` dl)
     - **No radio inputs, no tabs, no inline `<style>` block** — all providers visible as stacked cards
   - All `{% if %}` guards for optional fields preserved from current template

3. **Run `make css`** to rebuild the CSS with the new rules. Then run `make js` (though graph.ts was changed in T01, CSS rebuild is the critical step here).

4. **Add unit test assertions to `tests/test_ioc_detail_routes.py`:**
   - In `test_detail_page_with_results`: add assertions that `"detail-provider-card"` is in the HTML and `"verdict-badge--malicious"` is in the HTML (seeded provider has verdict=malicious). Assert `"<style>"` is NOT in the HTML (no inline style block).
   - Add a new test `test_detail_graph_labels_untruncated` that seeds a provider named `"Shodan InternetDB"` (17 chars, previously truncated to 12) and asserts the full name `"Shodan InternetDB"` appears in the rendered HTML response (inside the `data-graph-nodes` JSON attribute). This proves the server-side truncation fix from T01 is working.

5. **Final verification:**
   - `python3 -m pytest tests/test_ioc_detail_routes.py -q` — all tests pass (12 existing + new assertions + new test)
   - `make typecheck` exits 0
   - `wc -c app/static/dist/main.js` ≤ 30,720 bytes

## Must-Haves

- [ ] CSS rules for detail page added inside `@layer components` in `input.css`
- [ ] All CSS rules use only existing design tokens (no new custom properties)
- [ ] Template rewritten — stacked provider cards, no CSS-only radio tabs
- [ ] No inline `<style>` block in the template
- [ ] `.back-link`, `.ioc-type-badge`, `.verdict-badge` classes reused from existing CSS
- [ ] `#relationship-graph` with `data-graph-nodes` and `data-graph-edges` preserved (graph.ts init depends on this)
- [ ] All `{% if %}` guards for optional fields (detection_count, total_engines, scan_date, cached_at, raw_stats) preserved
- [ ] Unit test asserts `detail-provider-card` and `verdict-badge--malicious` in rendered HTML
- [ ] Unit test asserts no `<style>` tag in rendered HTML
- [ ] Unit test asserts untruncated provider name in `data-graph-nodes`
- [ ] `make css && make js` builds without errors
- [ ] All tests pass

## Verification

- `make css && make js` builds without errors
- `python3 -m pytest tests/test_ioc_detail_routes.py -q` — all tests pass
- `make typecheck` exits 0
- `wc -c app/static/dist/main.js` ≤ 30,720 bytes
- `grep -c '<style>' app/templates/ioc_detail.html` returns 0 (no inline styles)

## Inputs

- `app/templates/ioc_detail.html` — current template (107 lines) with CSS-only radio tab pattern and inline `<style>` block. Jinja variables: `ioc_value`, `ioc_type`, `provider_results` (list of dicts with `.provider`, `.verdict`, `.detection_count`, `.total_engines`, `.scan_date`, `.cached_at`, `.raw_stats`), `graph_nodes`, `graph_edges`.
- `app/static/src/input.css` — 1905 lines. `@layer components` starts at line 228. Existing detail-related classes (`.detail-link-footer`, `.detail-link`) at lines 1375–1393. Design tokens in `:root` block (lines ~48–120). Existing patterns to reference: `.back-link` (line 644), `.ioc-type-badge` (defined elsewhere), `.verdict-badge` (line 1191), `.verdict-badge--*` (lines 1205–1210).
- `tests/test_ioc_detail_routes.py` — 12 existing tests. `_seed_cache()` helper seeds virustotal (malicious) and abuseipdb (suspicious) providers. `test_detail_page_with_results` checks for provider names in HTML.
- T01 already removed label truncation in `routes.py` and `graph.ts`.

## Expected Output

- `app/templates/ioc_detail.html` — rewritten with M002 design patterns: stacked provider cards, zinc surfaces, verdict-only color, no inline styles
- `app/static/src/input.css` — ~25 new CSS rules added inside `@layer components` for detail page classes
- `tests/test_ioc_detail_routes.py` — new assertions for design tokens + new `test_detail_graph_labels_untruncated` test
- `app/static/dist/style.css` — rebuilt with new CSS rules
