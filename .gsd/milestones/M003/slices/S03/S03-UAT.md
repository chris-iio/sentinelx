# S03: Detail Page Design Refresh — UAT

**Milestone:** M003
**Written:** 2026-03-21

## UAT Type

- UAT mode: artifact-driven + human-experience
- Why this mode is sufficient: The functional changes (graph label truncation removal, template rewrite, CSS rules) are all verifiable via rendered HTML inspection. The 13 unit tests cover the machine-verifiable surface. Human visual inspection confirms the design tokens apply correctly (zinc surfaces, verdict-only color, typographic hierarchy) — this is the only signal that confirms the subjective "quiet precision" aesthetic matches M002.

## Preconditions

1. Server must be running: `flask run` or `python3 -m flask run`
2. Cache must have at least one enrichment result seeded for a test IOC. Run: `python3 -c "from app.cache import CacheStore; c = CacheStore(); c.store('1.2.3.4', 'ipv4', 'VirusTotal', {'verdict': 'malicious', 'detection_count': 42, 'total_engines': 90, 'scan_date': '2024-01-15', 'cached_at': '2024-01-15T12:00:00Z'})"`
3. Browser pointed at `http://localhost:5000`

## Smoke Test

Navigate to `http://localhost:5000/detail/ipv4/1.2.3.4`. If the page loads without error and you see a `.detail-provider-card` element with a verdict badge, the slice is basically working.

## Test Cases

### 1. Detail page renders with M002 design tokens

1. Navigate to `http://localhost:5000/detail/ipv4/1.2.3.4` (with seeded cache data)
2. Open browser DevTools → Elements
3. Inspect the outer wrapper element
4. **Expected:** The page has a `class="page-ioc-detail"` wrapper div
5. Inspect the IOC value display
6. **Expected:** IOC value (`1.2.3.4`) renders inside a `<code class="detail-ioc-value">` element; the text uses a monospace font (JetBrains Mono or fallback)
7. Inspect a provider result card
8. **Expected:** Provider card has `class="detail-provider-card"` with a visible border and a slightly lighter background than the page (zinc `--bg-secondary` surface, approximately `#18181b`)
9. Inspect the verdict badge inside the card
10. **Expected:** Verdict badge has class `verdict-badge verdict-badge--malicious` (or appropriate verdict); it appears in the header alongside the provider name; it is the ONLY colored element in the card (text and fields use zinc neutrals)

### 2. No inline `<style>` block in rendered HTML

1. Navigate to `http://localhost:5000/detail/ipv4/1.2.3.4`
2. View page source (Cmd+U or right-click → View Page Source)
3. Search for `<style` in the source
4. **Expected:** Zero occurrences of `<style` in the HTML — all styles are in the linked stylesheet. The old CSS-only radio tab implementation used an inline `<style>` block; it must be gone.

### 3. All providers visible simultaneously (stacked cards, no tabs)

1. Seed two providers: VirusTotal (malicious) and Shodan (clean) for `1.2.3.4`
2. Navigate to `http://localhost:5000/detail/ipv4/1.2.3.4`
3. **Expected:** Both provider cards render simultaneously on the page without any tab interface. No radio buttons or CSS-only tab switcher visible. Scroll down confirms both cards are present without any click required.
4. **Expected:** Each card has provider name in `.detail-provider-name` and verdict badge in `.detail-provider-header` — verdict badge is the only colored element per card.

### 4. Graph labels show full provider names (no truncation)

1. Navigate to `http://localhost:5000/detail/ipv4/1.2.3.4` (with VirusTotal result seeded)
2. Open DevTools → Elements, find `#relationship-graph`
3. Read the `data-graph-nodes` attribute
4. **Expected:** The JSON array contains `{"id": "VirusTotal", "label": "VirusTotal", ...}` — full provider name, not a truncated form like `"VirusTota"` (12 chars)
5. If you seed a provider named "Shodan InternetDB" (17 chars): `data-graph-nodes` must contain `"Shodan InternetDB"` verbatim
6. **Expected:** The IOC node in `data-graph-nodes` has `"label": "1.2.3.4"` — full IOC value, not truncated

### 5. SVG graph renders with wider viewBox

1. Navigate to `http://localhost:5000/detail/ipv4/1.2.3.4`
2. Wait for the page to fully load (graph.ts initializes the SVG)
3. Open DevTools → Elements, find the `<svg>` element inside `#relationship-graph`
4. Read the `viewBox` attribute
5. **Expected:** `viewBox="0 0 700 450"` (not the old `0 0 600 400`)
6. Visually confirm the provider nodes are visible and not clipped at the edges for providers with longer names

### 6. Optional fields guarded — empty state renders cleanly

1. Seed a minimal result with no `detection_count`, `scan_date`, or `raw_stats`: `{"verdict": "no_data", "cached_at": null}`
2. Navigate to `http://localhost:5000/detail/ipv4/1.2.3.4`
3. **Expected:** The provider card renders cleanly with only the provider name and verdict badge visible. No empty rows like "Detections: " or "Scan Date: " appear. The `<dl>` inside the card is empty (or omitted), not showing undefined values.

### 7. Back navigation link works

1. Navigate to `http://localhost:5000/detail/ipv4/1.2.3.4`
2. Click the "← Back" link at the top of the page
3. **Expected:** Returns to the index page (`/`). The back link uses `url_for('main.index')`.

### 8. Empty cache state renders without errors

1. Ensure no cache entry exists for a test IOC (e.g., `9.9.9.9`)
2. Navigate to `http://localhost:5000/detail/ipv4/9.9.9.9`
3. **Expected:** Page renders with the IOC value and type badge in the header, a graph section (graph renders with only the IOC center node), and an empty state message in the results section: "No enrichment data available for this IOC." with an "Analyze IOC" link back to the index.

## Edge Cases

### Long IOC value (SHA256 hash) in header

1. Seed a result for a SHA256 hash: any 64-char hex string
2. Navigate to `/detail/sha256/<hash>`
3. **Expected:** The hash renders in full inside `<code class="detail-ioc-value">` with word-break behavior (long value wraps or scrolls horizontally without overflowing outside its container).

### Long provider name in graph

1. Seed a provider named "CIRCL Hashlookup" (16 chars, previously truncated to 12)
2. Navigate to the detail page for that IOC
3. **Expected:** `data-graph-nodes` contains `"CIRCL Hashlookup"` verbatim. The SVG renders this label without truncation (text may overlap neighboring nodes in a dense graph, but must not be sliced programmatically).

### Multiple providers with mixed verdicts

1. Seed three providers: one malicious, one clean, one no_data
2. Navigate to the detail page
3. **Expected:** Three stacked cards render. Each has exactly one `verdict-badge--*` class. The malicious card has `verdict-badge--malicious` (red), the clean card has `verdict-badge--clean` (blue), the no_data card has `verdict-badge--no_data` (zinc neutral). No other bright colors appear.

## Failure Signals

- `AssertionError: 'detail-provider-card' not in html` from pytest → template was not applied or reverted to old tabs
- `AssertionError: '<style>' in html` from pytest → inline style block was reintroduced; template was reverted
- `AssertionError: 'verdict-badge--malicious' not in html` from pytest → verdict badge class missing; verdict-only color is broken
- `AssertionError: 'Shodan InternetDB' not found in data-graph-nodes` from `test_detail_graph_labels_untruncated` → truncation was reintroduced in routes.py or graph.ts
- Page renders with plain browser default styling (no zinc surfaces, standard serif/sans fonts) → `style.css` was not rebuilt or is missing the detail page rules; run `make css` and check `grep -c 'detail-provider-card' app/static/dist/style.css`
- SVG graph shows truncated labels like "VirusTota" (12 chars) → `.slice(0,12)` reintroduced in graph.ts; run `grep -n "slice(" app/static/src/ts/modules/graph.ts`

## Not Proven By This UAT

- **Live runtime graph rendering:** UAT test #4 verifies `data-graph-nodes` attribute content but does not verify the SVG pixels rendered by `graph.ts`. Visual inspection in step #5 covers SVG rendering but requires a running browser with JavaScript enabled.
- **Enrichment end-to-end flow:** This UAT does not test submitting an IOC and navigating to its detail page from the results page. That integration path is covered by S04's E2E tests.
- **Mobile responsive layout:** The detail page has no explicit mobile breakpoints in the new CSS; responsive behavior is not verified here.
- **Performance:** Load time and graph render time for pages with many providers (10+) is not measured.

## Notes for Tester

- The seeded cache data needs to use the exact data model expected by the template: `provider_results` is a list of dicts with keys `provider`, `verdict`, `detection_count`, `total_engines`, `scan_date`, `cached_at`, `raw_stats`. The `CacheStore.get_all_for_ioc()` method returns these dicts from the SQLite cache.
- If the graph SVG is blank or empty, check the browser console for JavaScript errors — `graph.ts` may have failed to initialize. The `#relationship-graph` element must have valid JSON in its `data-graph-nodes` attribute.
- The verdict badge uses `verdict-badge--{verdict}` pattern (e.g. `verdict-badge--malicious`). This is different from the results page `.verdict-label--*` pattern — both co-exist and are intentionally distinct (badge = compact, label = wider pill).
- The `detail-link` CSS class is also used by the results page inline expansion ("View full detail →" link). The detail page itself does not use this class — it uses `.back-link` for navigation. Don't confuse the two.
