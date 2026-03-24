# S01: Layout skeleton + quiet precision design system — UAT

**Milestone:** M002
**Written:** 2026-03-18

## UAT Type

- UAT mode: live-runtime + artifact-driven
- Why this mode is sufficient: S01 is template + CSS changes only (no new TS modules or runtime hooks). Build artifact checks verify contract preservation. Live-runtime browser check verifies visual layout and design quality. 36 E2E tests confirm structural DOM integrity.

## Preconditions

1. Working directory: `/home/chris/projects/sentinelx/.gsd/worktrees/M002`
2. Build tools installed: `make tailwind-install && make esbuild-install` (if not already present)
3. All three builds pass: `make css && make typecheck && make js-dev`
4. 36 E2E tests pass: `pytest tests/e2e/test_extraction.py tests/e2e/test_results_page.py -q`
5. Flask dev server running: `flask run` (default port 5000) with `FLASK_ENV=development`
6. Browser open to `http://localhost:5000`

## Smoke Test

Submit a batch of sample IOCs offline (paste `8.8.8.8, google.com, 1.2.3.4, d41d8cd98f00b204e9800998ecf8427e` into the input box, select Offline mode, click Analyze). The results page must render as a vertical list of full-width rows — **not** a 2-column grid.

## Test Cases

### 1. Single-column layout at all viewport widths

1. Submit sample IOCs and navigate to the results page
2. In browser devtools, inspect `#ioc-cards-grid` — verify `grid-template-columns` is `1fr` (single column)
3. Resize viewport to 1440px, 1024px, 768px, 375px (mobile)
4. **Expected:** At every breakpoint, IOC rows span the full available width. No 2-column layout appears at any viewport size. Long SHA256 hashes do not cause horizontal overflow.

### 2. IOC card renders as horizontal row, not card box

1. On the results page with IOC results visible, inspect a single `.ioc-card` element in devtools
2. **Expected:** `.ioc-card` has `display: flex; flex-direction: column`. The card header region contains: verdict badge (left), IOC type badge, IOC value (monospace), copy button — all in a horizontal flex row. No card-style border box or elevated shadow around individual cards. A subtle `border-bottom` separator between rows.

### 3. Verdict-only color — type badges are muted

1. On the results page, visually scan all IOC type badges (e.g., "IPV4", "DOMAIN", "SHA256")
2. Open devtools → computed styles on any `.ioc-type-badge--*` element
3. **Expected:** All type badges show muted neutral color (`color` ≈ `#71717a`, zinc-500). No bright blue for IPv4, no bright green for domain, no bright yellow for hash. Type is still readable as text label. A subtle border is visible around the badge.

### 4. Verdict badges are the only loud color

1. On the results page with a mix of verdicts (submit some known-good and some malicious IOCs, or use cached/offline mode with pre-tagged IOCs)
2. Visually scan the full page
3. **Expected:** The only vivid color on the page is verdict severity — malicious rows show vivid red badge, suspicious show amber, clean show green, known_good show blue. All other elements (headers, type indicators, filter pills, copy buttons, page chrome) are muted zinc/neutral tones.

### 5. Verdict dashboard is compressed inline

1. On the results page, locate `#verdict-dashboard`
2. **Expected:** Dashboard renders as a compact horizontal bar (not 5 large stacked KPI boxes). All 5 verdict categories (malicious, suspicious, clean, known_good, no_data) visible in a single row with count numbers. Each count uses verdict-specific text color (red, amber, sky, blue, zinc). Labels below counts are muted. Dashboard does not push IOC rows below the fold.

### 6. Filter bar is a single compact row

1. On the results page, locate `.filter-bar-wrapper`
2. **Expected:** Verdict filter pills, type filter pills, and text search input all appear in a single horizontal row (may wrap on mobile). Filter bar does not occupy 3 stacked rows. Total filter bar height is visually compact.

### 7. Contract selectors all present

Run the following grep checks (must all return matches):

```bash
# IOC card root with data attributes
grep 'class="ioc-card"' app/templates/partials/_ioc_card.html

# Grid container
grep 'id="ioc-cards-grid"' app/templates/results.html

# Verdict dashboard
grep 'id="verdict-dashboard"' app/templates/partials/_verdict_dashboard.html

# Verdict count data attribute (all 5)
grep 'data-verdict-count' app/templates/partials/_verdict_dashboard.html | wc -l  # → 5

# Filter bar contract
grep 'filter-bar-wrapper\|data-filter-verdict\|data-filter-type\|filter-search-input' app/templates/partials/_filter_bar.html

# IOC card child hooks
grep 'ioc-context-line\|verdict-label\|ioc-type-badge\|copy-btn\|enrichment-slot' app/templates/partials/_ioc_card.html

# No 2-column breakpoint in CSS
grep 'grid-cols-2\|repeat(2' app/static/src/input.css  # → no output
```

**Expected:** All greps return matches except the last one (which must return no output).

### 8. Filtering still works after layout migration

1. On the results page with multiple IOCs of different types, click a verdict filter pill (e.g., "CLEAN")
2. **Expected:** Rows not matching the verdict filter disappear. Active verdict pill changes visual state.
3. Click a type filter pill (e.g., "IPV4")
4. **Expected:** Only IPv4 rows remain visible. Active type filter pill uses neutral muted active state (not bright color).
5. Type a substring in the search box
6. **Expected:** Rows filter to only those whose IOC value contains the substring.

### 9. Copy button works

1. On the results page, click the copy icon on any IOC row
2. **Expected:** IOC value is copied to clipboard. Copy button shows a brief "copied" visual state, which reverts to neutral (not bright green — muted per T02).

### 10. Enrichment slot placeholder is present but subordinate

1. On the results page in offline mode (no enrichment), inspect `.enrichment-slot` on any IOC row
2. **Expected:** `.enrichment-slot` is present in the DOM (required for S02). It is visually invisible or extremely subtle — no prominent placeholder box, no loading spinner, no bright color. The enrichment area does not visually compete with the IOC value or verdict badge.

## Edge Cases

### Long SHA256 hash display

1. Submit a SHA256 hash IOC (64-char hex string) and view the results page
2. **Expected:** Hash renders in full in the `.ioc-value` element at `0.9rem` monospace weight. It may truncate with `text-overflow:ellipsis` or wrap — but must not cause horizontal page overflow or break the row layout.

### Mobile viewport (375px)

1. In browser devtools, set viewport to 375px width
2. Navigate to results page with IOC results
3. **Expected:** Single-column layout maintained. Filter bar wraps gracefully. Verdict dashboard wraps or scrolls but remains usable. No horizontal overflow on the page body.

### All five verdict states visible simultaneously

1. Submit IOCs that cover all five verdicts (use cached data or mock responses)
2. **Expected:** Dashboard shows all 5 verdict counts with correct verdict-specific text color. Verdict badges on rows show distinct vivid colors for each verdict type. No two verdict categories share the same color.

## Failure Signals

- **2-column grid appears at any viewport width** — `#ioc-cards-grid` has a media query breakpoint or `grid-template-columns` other than `1fr`
- **Bright colored type badges** — `.ioc-type-badge--*` computed color is not zinc/neutral; design system regression
- **Type-active filter pill shows bright color** — filter pill active state using old `accent-ipv4` or `accent-domain` colors
- **Verdict badge missing or wrong color** — `.verdict-label--malicious` not vivid red; contrast between verdicts unclear
- **Contract selector missing** — any grep in Test Case 7 returns no output (or returns 5 for data-verdict-count)
- **`make typecheck` non-zero exit** — TS error names a broken DOM contract selector
- **E2E test failure** — any of the 36 tests in test_extraction.py or test_results_page.py fails
- **Enrichment slot absent from DOM** — `.enrichment-slot` not present; S02 would have no target to populate
- **Dashboard still 5 large KPI boxes** — verdict dashboard not compressed to inline bar

## Requirements Proved By This UAT

- **R001** — Single-column full-width layout confirmed via devtools grid inspection and visual check at all viewports
- **R003** — Verdict-only color confirmed via computed styles on `.ioc-type-badge--*` and visual scan of the full page
- **R005 (partial)** — Dashboard structural compression confirmed; data population is S02
- **R006 (partial)** — Filter bar structural compaction confirmed; full functionality integration is S04
- **R008 (partial)** — Filtering, copy, detail links verified as working after layout migration

## Not Proven By This UAT

- **R002** — At-a-glance enrichment surface (verdict badge + context + provider numbers) — requires S02
- **R004** — Inline expand for full provider breakdown — requires S03
- **R007** — Progressive disclosure mechanism — requires S03
- **R008 (full)** — Export (JSON/CSV/clipboard), enrichment polling, progress bar — requires S02/S04
- **R009** — Security contracts (CSP, CSRF, SEC-08) — formally verified in S04
- **R010** — Performance (polling efficiency, debounced sort) — verified in S04
- **R011** — E2E suite with updated selectors — S05

## Notes for Tester

- **Offline mode is sufficient for this UAT.** S01 is template + CSS only — enrichment data is not needed to verify layout or design system changes.
- **The enrichment slot will be empty.** This is expected and intentional. The opacity:0.85 subordinate styling means it's visually invisible — don't flag this as missing content.
- **Verdict filter pills should retain vivid color when active.** Only *type* filter pill active states were muted. If verdict filter pills look muted when active, that is a regression from T02.
- **Build tool versions are local.** `tools/tailwindcss` and `tools/esbuild` installed locally to this worktree. Use `make` targets, not bare binaries.
- **Visual quality gut-check:** The page should feel like a production CLI tool or analysis dashboard — quiet, precise, no competing visual noise. If it still feels like a wall of colored badges, something regressed.
