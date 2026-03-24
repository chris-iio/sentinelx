# S03: Inline expand + progressive disclosure — UAT

**Milestone:** M002
**Written:** 2026-03-18

## UAT Type

- UAT mode: live-runtime + human-experience
- Why this mode is sufficient: Expand/collapse is a DOM interaction requiring browser context. Animation smoothness, visual quality, and keyboard feel require human judgment that automated tests cannot substitute.

## Preconditions

1. Dev server running: `flask run` (or `make dev`) from the worktree root
2. At least one enrichment session available — navigate to the app, submit 3–5 IOCs (mix of IPs, domains, hashes), trigger enrichment, wait for it to complete
3. Browser DevTools console accessible (for diagnostic verification steps)
4. Keyboard navigation working (Tab key not intercepted by OS/browser)

## Smoke Test

Submit a single IP (e.g. `8.8.8.8`), wait for enrichment to complete, click anywhere on the summary row (not just a chevron button). Provider details should expand below the row with a smooth animation.

---

## Test Cases

### 1. Summary row as click target — basic expand/collapse

1. Navigate to results page with at least one fully-enriched IOC
2. Locate an enriched IOC row — it should show the summary surface (verdict badge, context, provider stats)
3. Click anywhere on the summary row (not specifically a chevron)
4. **Expected:** Provider detail panel expands below the row with smooth animation. The chevron icon (right side of summary row) rotates 90°. Row gains visible `.is-open` state.
5. Click the same summary row again
6. **Expected:** Panel collapses with smooth animation. Chevron rotates back to original orientation.

### 2. aria-expanded tracks expand state correctly

1. Open browser DevTools console
2. With all panels collapsed, run: `document.querySelectorAll('[aria-expanded="true"]').length`
3. **Expected:** `0`
4. Expand one IOC row
5. Run: `document.querySelectorAll('[aria-expanded="true"]').length`
6. **Expected:** `1`
7. Verify it matches: `document.querySelectorAll('.ioc-summary-row.is-open').length`
8. **Expected:** Both return `1` (no mismatch)

### 3. Multiple rows expand independently — no accordion collapse

1. Ensure 3+ enriched IOC rows are visible
2. Expand row 1, then expand row 2, then expand row 3
3. **Expected:** All three panels remain open simultaneously. Expanding row 2 does not collapse row 1.
4. Collapse row 2 only
5. **Expected:** Rows 1 and 3 remain open; row 2 collapses

### 4. Keyboard accessibility — Tab + Enter/Space

1. Tab to focus a summary row (should receive visible focus ring)
2. Press Enter
3. **Expected:** Panel expands; `aria-expanded` changes to `"true"`
4. Press Space
5. **Expected:** Panel collapses; `aria-expanded` changes to `"false"`
6. Tab to a different summary row
7. Press Enter
8. **Expected:** Second row expands independently; first row stays collapsed

### 5. "View full detail →" link in expanded panel

1. Expand an enriched IOC row (any type)
2. Scroll to the bottom of the expanded panel
3. **Expected:** "View full detail →" link is visible at the bottom of the details panel
4. Check the link's href (hover to see URL or inspect element)
5. **Expected:** URL matches pattern `/detail/<ioc-type>/<url-encoded-ioc-value>`
   - Example for IP `8.8.8.8`: `/detail/ip/8.8.8.8`
   - Example for domain `example.com`: `/detail/domain/example.com`
   - Example for hash with special chars: value should be `encodeURIComponent()`-encoded
6. Click the "View full detail →" link
7. **Expected:** Navigates to the detail page for that IOC. Back button returns to results page.

### 6. Chevron remains present after incremental enrichment updates

1. Submit IOCs and watch the results page while enrichment is in progress
2. Observe a summary row that is actively updating (provider stats changing as results arrive)
3. After enrichment completes, expand the row
4. **Expected:** Chevron is still present in the summary row (not disappeared). The chevron rotates on expand as expected.
5. In DevTools console, run: `document.querySelectorAll('.ioc-summary-row .chevron-icon').length`
6. **Expected:** Count equals the number of enriched summary rows (one chevron per row)

### 7. Expanded panel visual treatment

1. Expand an IOC row
2. **Expected visual checks:**
   - Expanded panel has a subtle background tint (slightly different from the page background)
   - A left border accent (muted, not bright) is visible on the left edge of the expanded panel
   - Summary row shows a hover highlight when mousing over it (subtle background change)
   - "View full detail →" link uses a muted color (not bright); turns slightly more prominent on hover
   - No bright non-verdict colors anywhere in the expanded panel or detail link

### 8. Pre-enrichment — no summary row, no expand possible

1. Submit IOCs but do not wait for enrichment to start (or use a scenario where enrichment hasn't run)
2. **Expected:** No `.ioc-summary-row` elements are present. No expand/collapse is possible. IOC cards render without a summary row.
3. Once enrichment begins and at least one result arrives, the summary row appears and becomes clickable.

---

## Edge Cases

### IOC value with special characters in detail link

1. Submit a hash value or a domain with encoded characters (e.g. a URL-like string)
2. After enrichment completes, expand the row
3. Check the "View full detail →" href
4. **Expected:** `encodeURIComponent()` is applied — special characters (/, ?, =, etc.) are percent-encoded in the URL path

### Many providers — max-height not clipping

1. Expand an IOC that has many providers (ideally 8+)
2. Scroll through the expanded panel
3. **Expected:** All provider rows are visible. The panel grows to accommodate all content without cutting off at a fixed height. No invisible providers below a clipping boundary.

### Rapid click expand/collapse

1. Click a summary row quickly multiple times (expand, collapse, expand, collapse)
2. **Expected:** Panel state converges correctly — no stuck open/closed state, no duplicated content. aria-expanded reflects the final state.

### Expand then page re-enrichment

1. Expand a row
2. If re-enrichment is triggered (unlikely in normal flow, but possible if polling continues)
3. **Expected:** Chevron remains visible after any summary row update during polling

---

## Failure Signals

- **Click does nothing:** `wireExpandToggles()` event delegation not firing. Check that `.page-results` exists in the DOM and that the event handler is bound. Check browser console for errors.
- **Chevron disappears after first enrichment update:** The `updateSummaryRow()` chevron re-append fix is missing or broken. Run `document.querySelectorAll('.ioc-summary-row .chevron-icon').length` — if 0 after enrichment completes, the save/restore is not working.
- **aria-expanded mismatch:** `document.querySelectorAll('[aria-expanded="true"]').length` ≠ `document.querySelectorAll('.ioc-summary-row.is-open').length` — the aria update in the click handler diverged from the CSS class toggle.
- **Detail link absent:** `markEnrichmentComplete()` never ran (enrichment never finished), or `.enrichment-slot--loaded` not set when it ran. Check `document.querySelectorAll('.enrichment-slot--loaded').length` — if 0, enrichment pipeline issue upstream (S02).
- **Detail link shows `/detail//`:** `.ioc-card` element missing `data-ioc-type` or `data-ioc-value` attributes. Check DOM of a `.ioc-card` element directly.
- **No hover highlight on summary row:** `--bg-hover` CSS token undefined. Check that the token is defined in the design system (input.css variables block).
- **Panel cuts off provider list:** `max-height:2000px` not in compiled CSS. Run `make css` and verify `grep -o 'max-height:2000px' app/static/dist/style.css` returns a match.
- **E2E regression:** 36 tests in `test_results_page.py` and `test_extraction.py` should all pass. Any failures indicate S03 broke an upstream contract.

---

## Requirements Proved By This UAT

- **R004** (Inline expand for full provider breakdown) — Tests 1, 3, 4, 5 directly verify: row-as-click-target, independent multi-row expand, keyboard accessibility, and "View full detail →" link with correct href pattern.
- **R007** (Progressive disclosure) — Tests 1, 7, 8 verify: details hidden by default, revealed on intentional interaction, pre-enrichment state correctly shows no summary row.
- **R003** (Verdict-only color) — Test 7 verifies: expanded panel uses only muted colors; no bright non-verdict colors introduced by S03.

## Not Proven By This UAT

- Export (JSON/CSV/clipboard) — S04
- Dashboard-click-to-filter, verdict sorting, progress bar — S04
- Security contracts (CSP headers, CSRF token, full SEC-08 audit) — S04
- E2E test suite with updated selectors — S05
- Visual quality judgment by a domain expert under real triage load — S04 visual polish pass

## Notes for Tester

- The summary row hover state relies on `--bg-hover` CSS token — if it's subtly broken (transparent background instead of slight highlight), that's a token definition issue to surface to S04, not a blocker.
- The "View full detail →" link only appears after enrichment **completes** (`markEnrichmentComplete()` fires). During enrichment, the expanded panel will show provider rows but no link yet — this is correct behavior.
- The `aria-expanded` mismatch diagnostic in Test 2 is the most reliable signal for wiring correctness — run it routinely.
- Animation smoothness is a gut-check: the expand/collapse transition should feel fluid at ~200-300ms. If it feels instant or jerky, the CSS transition on `max-height` may be missing or the value jump too large.
- Multiple independently open rows (Test 3) is the key UX proof that this is not an accordion — verify this deliberately.
