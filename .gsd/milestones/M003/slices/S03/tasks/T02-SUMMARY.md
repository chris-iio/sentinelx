---
id: T02
parent: S03
milestone: M003
provides:
  - M002 design tokens applied to detail page (zinc surfaces, verdict-only color, consistent typography)
  - Stacked provider cards replace CSS-only radio tabs — all providers visible at once
  - No inline <style> block in template — all rules in input.css @layer components
  - Unit test regression guard for untruncated graph labels ("Shodan InternetDB")
key_files:
  - app/templates/ioc_detail.html
  - app/static/src/input.css
  - app/static/dist/style.css
  - tests/test_ioc_detail_routes.py
key_decisions:
  - Replaced CSS-only radio tab pattern with stacked provider cards for simpler, more accessible layout
  - Verdict badge placed in .detail-provider-header alongside provider name (not inside dl fields) for visual clarity
  - No new CSS custom properties — all rules use existing design tokens exclusively
patterns_established:
  - Detail page cards use .detail-provider-card with .detail-provider-header + dl.detail-result-fields pattern
  - All conditional fields (detection_count, scan_date, cached_at, raw_stats) guarded with {% if %} blocks — optional data never renders empty rows
observability_surfaces:
  - "grep -c '<style>' app/templates/ioc_detail.html" — must return 0; any inline style regression caught immediately
  - "python3 -m pytest tests/test_ioc_detail_routes.py -q" — test_detail_page_with_results asserts detail-provider-card and verdict-badge--malicious; test_detail_graph_labels_untruncated asserts "Shodan InternetDB" in data-graph-nodes
  - "curl http://localhost:5000/ioc/ipv4/1.2.3.4 | grep detail-provider-card" — confirms stacked card markup is rendered
  - "wc -c app/static/dist/main.js" — bundle size guard (26,648 bytes, well under 30,720 limit)
duration: 6m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T02: Rewrite detail template with M002 design tokens and add CSS rules

**Rewrote `ioc_detail.html` with stacked provider cards using zinc surfaces and verdict-only color; added 25 CSS rules to `input.css` inside `@layer components`; added M002 design token assertions and untruncated-label regression test — all 13 tests pass.**

## What Happened

Four coordinated changes across three files:

1. **`app/static/src/input.css`** — Inserted 25 new CSS rules inside `@layer components`, immediately after the `.detail-link:hover` rule (line ~1392). All rules use existing design tokens: `--bg-secondary`, `--border`, `--border-default`, `--text-primary`, `--text-secondary`, `--text-muted`, `--font-mono`, `--weight-heading`, `--weight-caption`. No new custom properties were defined.

2. **`app/templates/ioc_detail.html`** — Completely rewritten from 107 lines to ~90 lines. Key changes:
   - Removed the CSS-only radio tab pattern (radio inputs + inline `<style>` block) that required JavaScript-free tab switching
   - Replaced with stacked `.detail-provider-card` elements — all providers visible simultaneously, no hidden panels
   - Moved the verdict badge into `.detail-provider-header` alongside the provider name (not inside the field list)
   - All `{% if %}` guards for optional fields (`detection_count`, `scan_date`, `cached_at`, `raw_stats`) preserved exactly as before
   - `#relationship-graph` with `data-graph-nodes` and `data-graph-edges` preserved unchanged (graph.ts init depends on this)

3. **`tests/test_ioc_detail_routes.py`** — Two additions:
   - Extended `test_detail_page_with_results` with three new assertions: `"detail-provider-card"` in HTML, `"verdict-badge--malicious"` in HTML, `"<style>"` NOT in HTML
   - Added new `test_detail_graph_labels_untruncated`: seeds a provider named `"Shodan InternetDB"` (17 chars, previously truncated to 12 in T01) and asserts the full name appears in rendered HTML

4. **`app/static/dist/style.css`** — Rebuilt via `make css` to include the new rules.

## Verification

- `make css` — Tailwind rebuilt `style.css` in 471ms, no errors
- `make js` — esbuild rebuilt `main.js` (26.0kb), no errors (unchanged from T01)
- `python3 -m pytest tests/test_ioc_detail_routes.py -q` — 13 passed (12 original + 1 new) in 0.42s
- `make typecheck` — tsc `--noEmit` exited 0
- `wc -c app/static/dist/main.js` — 26,648 bytes (≤ 30,720 limit)
- `grep -c '<style>' app/templates/ioc_detail.html` — returns 0 (no inline style block)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `make css` | 0 | ✅ pass | 471ms |
| 2 | `make js` | 0 | ✅ pass | 10ms |
| 3 | `python3 -m pytest tests/test_ioc_detail_routes.py -q` | 0 (13 passed) | ✅ pass | 0.42s |
| 4 | `make typecheck` | 0 | ✅ pass | ~3s |
| 5 | `wc -c app/static/dist/main.js` | 0 (26648 ≤ 30720) | ✅ pass | <1s |
| 6 | `grep -c '<style>' app/templates/ioc_detail.html` | 1 (count=0) | ✅ pass | <1s |

## Observability Impact

**New runtime signals added by this task:**

- **`detail-provider-card` in rendered HTML** — every provider result now renders as a `.detail-provider-card` div; absence of this class means the results section regressed to tabs or empty state. Check with: `curl http://localhost:5000/ioc/ipv4/1.2.3.4 | grep detail-provider-card`
- **`verdict-badge--<verdict>` classes** — verdict color is expressed exclusively via these classes (no inline styles); presence in HTML proves verdict-only coloring is working. Check with: `curl http://localhost:5000/ioc/ipv4/1.2.3.4 | grep verdict-badge--`
- **Absence of `<style>` in template** — `grep -c '<style>' app/templates/ioc_detail.html` must return 0; any accidental re-introduction of inline styles is immediately detectable.
- **`test_detail_graph_labels_untruncated`** — pytest test asserts `"Shodan InternetDB"` appears verbatim in the rendered `data-graph-nodes` attribute; if T01's truncation removal is ever reverted, this test fails with a clear message.

**Failure visibility:**
- If stacked cards regress to tabs, `test_detail_page_with_results` fails on `assert "detail-provider-card" in html`
- If verdict coloring is lost, `assert "verdict-badge--malicious" in html` fails
- If inline styles return, `assert "<style>" not in html` fails
- If label truncation returns, `test_detail_graph_labels_untruncated` fails on the "Shodan InternetDB" assertion

## Diagnostics

- **Verify card layout rendered:** `curl http://localhost:5000/ioc/ipv4/1.2.3.4 2>/dev/null | grep -o 'detail-provider-card'` — one match per seeded provider
- **Verify verdict badges:** `curl http://localhost:5000/ioc/ipv4/1.2.3.4 2>/dev/null | grep 'verdict-badge--'`
- **Verify no inline style:** `grep -c '<style>' app/templates/ioc_detail.html` — must be 0
- **Verify CSS rules added:** `grep -c 'detail-provider-card' app/static/src/input.css` — must be ≥ 1
- **Run test suite:** `python3 -m pytest tests/test_ioc_detail_routes.py -v` — each test name identifies which slice feature it covers

## Deviations

None — implementation followed the plan exactly. The verdict badge placement in `.detail-provider-header` (rather than inside the `<dl>` field list) matches the plan's description of `.detail-provider-header` containing "provider name + verdict badge".

## Known Issues

None.

## Files Created/Modified

- `app/templates/ioc_detail.html` — rewritten with M002 design patterns: stacked provider cards, zinc surfaces, verdict-only color, no inline styles
- `app/static/src/input.css` — 25 new CSS rules added inside `@layer components` for detail page classes
- `app/static/dist/style.css` — rebuilt artifact with new CSS rules
- `tests/test_ioc_detail_routes.py` — extended `test_detail_page_with_results` with M002 token assertions; added `test_detail_graph_labels_untruncated` regression test
