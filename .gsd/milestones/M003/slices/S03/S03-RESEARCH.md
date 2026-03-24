# S03 — Detail Page Design Refresh — Research

**Date:** 2026-03-20
**Depth:** Targeted

## Summary

The detail page (`ioc_detail.html`) is a design regression: it defines ~20 CSS classes (`.page-ioc-detail`, `.detail-header`, `.detail-title-group`, `.detail-graph-section`, `.detail-tabs`, `.tab-labels`, `.tab-label`, `.tab-panels`, `.tab-panel`, `.detail-result-fields`, `.result-field`, `.raw-stats`, `.detail-empty`, etc.) but **zero of them have CSS rules in `input.css`**. The page renders with only browser defaults and inherited base styles. The inline `<style>` block inside the template handles only the CSS-only tab radio visibility hack, not the layout or design tokens.

The fix is straightforward: rewrite `ioc_detail.html` to use M002 design patterns (zinc surfaces, verdict-only color, consistent typography), add the corresponding CSS rules to `input.css` using existing design tokens, and remove the graph label truncation in both `routes.py` (server-side `[:12]`/`[:20]`) and `graph.ts` (client-side `.slice(0, 12)`/`.slice(0, 20)`). Four provider names currently truncate: "CIRCL Hashlookup" (16 chars), "Shodan InternetDB" (17), "OTX AlienVault" (14), "MalwareBazaar" (13).

## Recommendation

**Template rewrite + CSS additions + graph truncation fix.** No structural changes to routes or JS modules beyond graph.ts label slicing.

1. Rewrite `ioc_detail.html` to use M002 design language — keep the same data flow (server passes `provider_results`, `graph_nodes`, `graph_edges`), just change HTML structure and class names to use existing component patterns from the results page.
2. Add detail page CSS rules inside the existing `@layer components` block in `input.css`, using only existing design tokens (`--bg-secondary`, `--border`, `--text-secondary`, `--verdict-*`, `--font-mono`, etc.).
3. Remove the `.slice(0, 12)` and `.slice(0, 20)` truncation in `graph.ts`. Remove the `[:12]` and `[:20]` truncation in `routes.py`. Use CSS/SVG text-overflow or increase the viewBox to accommodate full labels.
4. The inline `<style>` tab hack in the template can be replaced with a clean CSS approach in `input.css`.

## Implementation Landscape

### Key Files

- **`app/templates/ioc_detail.html`** — Full template rewrite. Currently 107 lines. Structure: header (back link + IOC value + type badge), graph section, tabbed provider results. Keep the same Jinja variables (`ioc_value`, `ioc_type`, `provider_results`, `graph_nodes`, `graph_edges`) — the route doesn't change.
- **`app/static/src/input.css`** — Add CSS rules for detail page classes. Must go inside the `@layer components` block (lines ~197–1906). Reuse existing tokens only — no new custom properties.
- **`app/static/src/ts/modules/graph.ts`** — Line 154: `node.label.slice(0, 12)` truncates provider labels. Line 184: `iocNode.label.slice(0, 20)` truncates IOC label. Remove both. The SVG viewBox is `600×400` with `orbitRadius=150` — labels should fit if the viewBox is widened slightly or text-anchor positioning is adjusted.
- **`app/routes.py`** — Lines 310 and 318: server-side label truncation `ioc_value[:20]` and `provider[:12]`. Remove both truncations — pass full strings, let the SVG renderer handle overflow.
- **`tests/test_ioc_detail_routes.py`** — Existing unit tests for the detail route. 7 tests covering 200/404/empty/populated/graph-data/no-annotation. These should continue passing without modification (route behavior unchanged).

### Reference Files (read-only patterns to follow)

- **`app/templates/results.html`** — M002 results page structure. Reference for page-level layout pattern (`.page-results`, `.results-header`, `.back-link`).
- **`app/templates/partials/_ioc_card.html`** — IOC card structure with verdict labels, type badges, copy buttons. Pattern for `.ioc-type-badge--*` and `.verdict-label--*` usage.
- **`app/templates/partials/_enrichment_slot.html`** — Enrichment detail section structure. Pattern for `.enrichment-section`, `.provider-section-header`, `.enrichment-details`.
- **`app/static/src/input.css`** — Design tokens (`:root` block, lines 33–110). Component patterns for cards, badges, typography hierarchy. The `.provider-detail-row`, `.provider-detail-name`, `.provider-detail-stat` classes are already defined and can be reused on the detail page for provider result fields.

### Build Order

1. **Graph truncation fix first** — smallest, most isolated change. Modify `graph.ts` (remove `.slice()`) and `routes.py` (remove `[:N]`). Widen SVG viewBox if needed. Verify with existing `test_graph_data_in_context` unit test. This unblocks the template rewrite since the graph is embedded in the detail page.

2. **CSS rules second** — add all detail page component rules to `input.css` inside `@layer components`. This can be designed to match the template structure before the template itself is rewritten, since the class names are known. Run `make css` to compile.

3. **Template rewrite third** — depends on the CSS rules being in place. Rewrite `ioc_detail.html` using M002 patterns:
   - Header: back link + IOC value (mono font) + type badge (neutral zinc)
   - Graph section: provider relationships SVG (existing `graph.ts` renders into `#relationship-graph`)
   - Provider results: replace CSS-only radio tabs with stacked provider cards or a simpler tab approach. Each provider shows verdict badge, detection count, scan date, raw stats using `.provider-detail-row` pattern.
   - Empty state: reuse `.detail-empty` with design tokens

4. **Verify** — `make css && make js` to rebuild. Run `python3 -m pytest tests/test_ioc_detail_routes.py -q` to confirm unit tests pass. Run `make typecheck` to confirm no TS errors. Visual inspection of `/ioc/ipv4/1.2.3.4` with seeded cache data.

### Verification Approach

- `make typecheck` — must exit 0 after graph.ts changes
- `make css && make js` — must build without errors
- `python3 -m pytest tests/test_ioc_detail_routes.py -q` — all 9 existing tests pass
- `wc -c app/static/dist/main.js` — still ≤ 30KB (graph.ts change removes ~20 chars, negligible)
- **Visual**: navigate to `/ioc/ipv4/1.2.3.4` with seeded cache — page should show zinc surfaces, verdict-only color, untruncated graph labels
- **E2E tests for design tokens** — S04 will add E2E assertions verifying M002 tokens are present on the detail page. S03 delivers the template + CSS that S04 tests against.

## Constraints

- All DOM construction must use `createElement` + `textContent` (SEC-08) — no innerHTML. The graph.ts module already follows this; the template uses Jinja autoescaping.
- CSS rules must go inside `@layer components` — not unbounded utility classes — to avoid specificity conflicts (documented in input.css header).
- Bundle must stay ≤ 30KB after JS changes.
- `make typecheck` must pass after any TS changes.
- The route handler (`routes.py` `ioc_detail()`) public API must not change — same template variables, same URL pattern.

## Common Pitfalls

- **Route path mismatch** — The Flask route is `/ioc/<type>/<value>` but `injectDetailLink()` in enrichment.ts hardcodes `/detail/<type>/<value>`. This is a pre-existing known issue documented in KNOWLEDGE.md. S03 does not change routing — the detail page URL stays at `/ioc/...`. Do not "fix" the link path as part of this slice.
- **CSS-only tabs inline `<style>` block** — The current template generates `<style>` rules via Jinja `{% for %}` loops for tab radio visibility. If replacing tabs with a different pattern, remove this inline style block entirely to avoid stale CSS rules. If keeping CSS-only tabs, move the generic rules to `input.css` and keep only the per-tab `:checked` selectors inline.
- **Graph viewBox overflow** — Removing label truncation means labels like "Shodan InternetDB" (17 chars) and "CIRCL Hashlookup" (16 chars) may overflow the 600×400 SVG viewBox. Either widen the viewBox (e.g., `0 0 700 450`) or increase `orbitRadius` from 150 to ~170 to give labels more space. The SVG has `width="100%"` so the container scales.
- **Verdict badge class names** — The detail page currently uses `.verdict-badge--*` (with `--` BEM modifier). The results page uses `.verdict-label--*`. These are different class systems. The rewrite should use whichever is already defined in `input.css` — both `.verdict-badge` (line ~1190) and `.verdict-label--*` (lines ~1074–1082) exist. Use `.verdict-badge` for inline small badges, `.verdict-label--*` for the primary verdict indicator.

## Open Risks

- **Provider result data shape variability** — The template iterates `provider_results` and accesses `.verdict`, `.detection_count`, `.total_engines`, `.scan_date`, `.cached_at`, `.raw_stats`. Different providers populate different subsets. The template must handle missing fields gracefully (current template already uses `{% if %}` guards). Verify all provider adapters' return shapes haven't changed since the template was last updated.
