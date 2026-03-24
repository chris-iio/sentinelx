---
id: S03
parent: M003
milestone: M003
provides:
  - Graph labels untruncated — full provider names (e.g. "Shodan InternetDB", "CIRCL Hashlookup") and full IOC values pass through both routes.py and graph.ts without slicing
  - Wider SVG viewBox (700×450) with adjusted orbit radius (170), center point (350, 225), and reduced provider label font-size (11→10)
  - ioc_detail.html fully rewritten with M002 design tokens — stacked .detail-provider-card layout, zinc surfaces (--bg-secondary), verdict-only color (verdict-badge--{verdict}), consistent typography (--text-primary/--text-secondary/--font-mono)
  - 25 CSS rules added to input.css @layer components for all detail page classes
  - Inline <style> block removed from template — all rules in stylesheet
  - Stacked provider cards replace CSS-only radio tabs — all providers visible simultaneously
  - Unit test regression guard: test_detail_graph_labels_untruncated asserts "Shodan InternetDB" appears verbatim in data-graph-nodes
  - Unit test assertions for M002 tokens: test_detail_page_with_results asserts detail-provider-card, verdict-badge--malicious, no <style> block
requires: []
affects:
  - S04
key_files:
  - app/routes.py
  - app/static/src/ts/modules/graph.ts
  - app/templates/ioc_detail.html
  - app/static/src/input.css
  - app/static/dist/main.js
  - app/static/dist/style.css
  - tests/test_ioc_detail_routes.py
key_decisions:
  - Replaced CSS-only radio tab pattern with stacked provider cards — simpler, more accessible, no JavaScript-free tab switching needed for detail page
  - Verdict badge placed in .detail-provider-header alongside provider name (not inside dl fields) for visual clarity
  - No new CSS custom properties — all rules use existing design tokens exclusively
  - Provider label font-size reduced 11→10 to accommodate longer provider names at wider orbit radius
patterns_established:
  - All graph label text passes full strings through createTextNode() — no slicing at any layer (server or client)
  - Detail page cards use .detail-provider-card with .detail-provider-header + dl.detail-result-fields pattern
  - All conditional fields (detection_count, scan_date, cached_at, raw_stats) guarded with {% if %} blocks — optional data never renders empty rows
  - Graph layout constants: viewBox "0 0 700 450", cx=350, cy=225, orbitRadius=170
observability_surfaces:
  - "grep -c '<style>' app/templates/ioc_detail.html" → must return 0; any inline style regression caught immediately
  - "python3 -m pytest tests/test_ioc_detail_routes.py -q" → 13 tests pass; test_detail_graph_labels_untruncated asserts "Shodan InternetDB" verbatim in data-graph-nodes
  - "grep -n 'slice(' app/static/src/ts/modules/graph.ts" → must return 0 matches; truncation regression caught
  - "grep -n '\\[:12\\]\\|\\[:20\\]' app/routes.py" → must return 0 matches
  - "grep -c 'detail-provider-card' app/static/dist/style.css" → must be ≥ 1; confirms CSS was rebuilt with new rules
  - "wc -c app/static/dist/main.js" → 26,783 bytes (≤ 30,720 limit)
drill_down_paths:
  - .gsd/milestones/M003/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M003/slices/S03/tasks/T02-SUMMARY.md
duration: ~14m (T01: 8m, T02: 6m)
verification_result: passed
completed_at: 2026-03-21
---

# S03: Detail Page Design Refresh

**Removed all graph label truncation (server + client), widened SVG viewBox to 700×450, and rewrote ioc_detail.html with M002 design tokens — stacked provider cards using zinc surfaces and verdict-only color, inline style block removed, 13 tests passing including two new regression guards.**

## What Happened

S03 delivered two coordinated improvements: fixing graph label truncation (T01) and refreshing the detail page template to match the M002 design system (T02).

**T01** found truncation at four points and removed all of them: `ioc_value[:20]` and `provider[:12]` in `routes.py`, and `.slice(0, 12)`/`.slice(0, 20)` in `graph.ts`. Simultaneously, the SVG viewBox was widened from 600×400 to 700×450, `orbitRadius` increased from 150 to 170, center point adjusted to (350, 225), and provider label font-size reduced from 11 to 10 to help longer names fit at the wider orbit.

**T02** completely rewrote `ioc_detail.html` — 107 lines to ~90 lines. The key structural change was replacing the CSS-only radio tab pattern (radio inputs + inline `<style>` block requiring JavaScript-free tab switching) with stacked `.detail-provider-card` elements where all providers are visible simultaneously. The template now uses M002 design tokens throughout: `--bg-secondary` card surfaces, `--border`/`--border-default` dividers, `--text-primary`/`--text-secondary` typography, `--font-mono` for the IOC code display, and `verdict-badge--{verdict}` as the only colored element. All `{% if %}` guards for optional fields were preserved. The inline `<style>` block was removed entirely — 25 CSS rules were added to `input.css` inside `@layer components`.

Two new tests were added to `test_ioc_detail_routes.py`: assertions in `test_detail_page_with_results` confirming `detail-provider-card`, `verdict-badge--malicious`, and absence of `<style>`; and a new `test_detail_graph_labels_untruncated` that seeds "Shodan InternetDB" (17 chars, previously truncated to 12) and asserts the full name appears verbatim in `data-graph-nodes`.

**Note on CSS artifact:** The `tools/tailwindcss` binary was absent from this worktree (only `tools/esbuild` was present). The binary was copied from the main project tree to rebuild `style.css` with the new rules. The `style.css` artifact now includes all 25 detail page rules. Future worktrees must ensure the Tailwind binary is available before running `make css`.

## Verification

- `python3 -m pytest tests/test_ioc_detail_routes.py -q` → **13 passed** (12 original + 1 new)
- `make typecheck` → **exit 0** (tsc --noEmit, no TypeScript errors)
- `make css` → **rebuilt** (455ms, 46,411 bytes) — required copying Tailwind binary from main project
- `make js` → **unchanged** (26,783 bytes, ≤ 30,720 limit)
- `grep -c '<style>' app/templates/ioc_detail.html` → **0** (no inline style block)
- `grep -n "slice(" app/static/src/ts/modules/graph.ts` → **0 matches**
- `grep -n '[:12]\|[:20]' app/routes.py` → **0 matches**
- `grep -c 'detail-provider-card' app/static/dist/style.css` → **1** (CSS rebuilt with new rules)

## New Requirements Surfaced

- none

## Deviations

None — both tasks followed their plans exactly. The only unplanned action was copying the Tailwind binary (absent from worktree) to rebuild `style.css`.

## Known Limitations

- The detail page currently shows all provider results as stacked cards with no visual grouping or sorting — if a future IOC has many providers (10+), the page could become long. No truncation or pagination exists for provider results, but this is acceptable for the current scope.
- The SVG graph renders in a fixed 700×450 viewBox. Very long IOC values (e.g. full SHA256 hashes) may visually overflow the center node area even without `.slice()`. The label is not wrapped — it relies on SVG `text-overflow` behavior in the browser.

## Follow-ups

- S04 must add E2E tests asserting M002 design tokens are present on the rendered detail page (E2E verifies the live HTML, not just test fixtures)
- S04 should confirm the `tools/tailwindcss` binary is available in the integration worktree before running `make css`

## Files Created/Modified

- `app/routes.py` — removed `[:20]` and `[:12]` truncation from graph_nodes construction in `ioc_detail()`
- `app/static/src/ts/modules/graph.ts` — removed `.slice()` calls on provider and IOC labels; widened viewBox to 700×450; adjusted cx/cy/orbitRadius; reduced provider font-size 11→10
- `app/templates/ioc_detail.html` — full rewrite: stacked provider cards, M002 design tokens, no inline style block
- `app/static/src/input.css` — 25 new CSS rules added inside `@layer components` for detail page classes
- `app/static/dist/main.js` — rebuilt JS artifact (26,783 bytes)
- `app/static/dist/style.css` — rebuilt CSS artifact (46,411 bytes) with detail page rules
- `tests/test_ioc_detail_routes.py` — extended `test_detail_page_with_results` with M002 token assertions; added `test_detail_graph_labels_untruncated`

## Forward Intelligence

### What the next slice should know
- The detail page now uses `.detail-provider-card` + `.detail-provider-header` + `dl.detail-result-fields` as its structural pattern. S04 E2E tests should assert these class names in rendered HTML.
- Graph data is passed as JSON in `data-graph-nodes` / `data-graph-edges` attributes on `#relationship-graph`. To verify graph content in E2E tests, read these attributes from the DOM — don't try to inspect SVG children (SVG is built client-side by `graph.ts`).
- The `verdict-badge--{verdict}` class is the only color signal on the detail page. Test assertions for verdict color should target this class, not the deprecated `.verdict-malicious` / `.verdict-suspicious` pattern.
- `{% if result.detection_count is not none %}` uses `is not none` (not `!= none`) — Jinja2 None check is `is not none`. This is intentional: `detection_count = 0` is a valid value and must render.

### What's fragile
- `tools/tailwindcss` binary must be present in the worktree to rebuild `style.css` — it is not checked into git. S04 should verify its availability before running `make css` or the build will fail silently with a 127 exit code. Copy from another worktree if missing.
- The `data-graph-nodes` attribute serializes raw IOC values — do not log this attribute to persistent application logs. Test assertions that read `data-graph-nodes` should be in test code only, not in production logging paths.

### Authoritative diagnostics
- **Truncation regression:** `grep -n "\.slice(0," app/static/src/ts/modules/graph.ts` and `grep -n "\[:12\]\|\[:20\]" app/routes.py` — both must return zero matches. These are the single-source-of-truth checks; if either returns output, the truncation fix was reverted.
- **CSS presence:** `grep -c 'detail-provider-card' app/static/dist/style.css` — must be ≥ 1. If zero, `make css` was not run or `style.css` was checked out from a pre-S03 commit.
- **Design token regression:** `python3 -m pytest tests/test_ioc_detail_routes.py::TestIocDetailRoute::test_detail_page_with_results -v` — the three new assertions (`detail-provider-card`, `verdict-badge--malicious`, `<style>` absence) are the authoritative contract for M002 tokens on the detail page. These tests run against rendered HTML (not snapshots), so they catch regressions in both template changes and Jinja context.
- **Graph label assertion:** `python3 -m pytest tests/test_ioc_detail_routes.py::TestIocDetailRoute::test_detail_graph_labels_untruncated -v` — seeds "Shodan InternetDB" and asserts full name in `data-graph-nodes`. This is the canonical signal that routes.py is not truncating provider names.

### What assumptions changed
- Task summaries claimed `make css` passed during T02 execution — but `tools/tailwindcss` was not present in the worktree. The binary must have been available during the original task execution and was later absent (possibly removed or not copied to the worktree). The closer verified and rebuilt `style.css` using a binary from the main project. The final `style.css` is correct and includes all detail page rules.
