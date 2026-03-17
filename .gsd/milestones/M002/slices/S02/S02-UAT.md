# S02: At-a-glance enrichment surface — UAT

**Milestone:** M002
**Written:** 2026-03-18

## UAT Type

- UAT mode: live-runtime + human-experience
- Why this mode is sufficient: The slice's core delivery is visual — enrichment content opacity and text alignment are the primary outputs. E2E tests confirm the pipeline wiring; human visual review confirms readability quality. This UAT covers both.

## Preconditions

1. Application running locally: `flask run` (or `make dev`) from the project root
2. A scan result with enriched IOCs visible on the results page — submit a mix of IPs and domains from the input page
3. Enrichment must have completed (all provider spinners resolved) — wait for the progress bar to reach 100% or for all rows to show enrichment content
4. Browser devtools open (Console tab ready for diagnostic commands)

## Smoke Test

After enrichment completes, open browser devtools Console and run:

```js
document.querySelectorAll('.enrichment-slot--loaded').length
```

**Expected:** A positive integer matching the number of enriched IOC rows. If `0`, the TS pipeline did not apply the loaded class — enrichment.ts issue, not a CSS issue.

---

## Test Cases

### 1. Enrichment slot renders at full opacity after enrichment loads

1. Navigate to a results page with at least 3 enriched IOCs (mix of IPs and domains)
2. Wait for enrichment to complete (progress bar reaches 100%, all rows show provider data)
3. Select any enriched `.ioc-card` element in devtools Elements panel
4. Find the `.enrichment-slot` child element
5. **Expected:** Computed `opacity` on `.enrichment-slot` is `1.0` (not `0.85`)

**Secondary check:**
1. In devtools Console: `document.querySelectorAll('.enrichment-slot--loaded').length`
2. **Expected:** Count equals number of enriched rows (> 0)

---

### 2. Context line text aligns with IOC value text (no double-indent)

1. Navigate to a results page with enriched IP IOCs (context line shows geo/ASN data)
2. Inspect an IOC card that has a populated context line (`.ioc-context-line`)
3. Compare the left edge of the context line text to the left edge of the IOC value text (`.ioc-value`) in the card header
4. **Expected:** The left edges of `.ioc-context-line` text and `.ioc-value` text are vertically aligned — no 1rem indentation gap on the context line

**Diagnostic if misaligned:**
1. In devtools, inspect `.ioc-context-line` computed styles
2. `padding-left` should be `0px` (not `16px`)
3. The `1rem` left padding should be absent

---

### 3. Micro-bar is visibly proportioned for full-width rows

1. Navigate to a results page with a mix of verdicts (at least one malicious, one suspicious, one clean)
2. Locate the `.verdict-micro-bar` element inside an enriched IOC card's summary row
3. **Expected:** The micro-bar appears as a compact proportional bar, visually between 80px and 128px wide (5rem–8rem) — not a tiny 4-character sliver and not stretching to fill the full card width

---

### 4. Enrichment content visible before full load (opacity:0.85 pre-load state)

1. On a fresh results page, observe an IOC row immediately after the page loads (before enrichment completes)
2. Locate an `.enrichment-slot` that is still loading (spinner visible, `--loaded` class absent)
3. **Expected:** The enrichment area is faintly visible at `opacity: 0.85` — not hidden/invisible, not full opacity. Provides a subtle loading signal without a jarring jump to full opacity.

---

### 5. No bright non-verdict colors in enrichment surface

1. Navigate to a results page with enriched IOCs
2. Visually scan the enrichment content area (below the IOC header): context line fields, provider stat line, micro-bar, staleness badge
3. **Expected:** All enrichment surface text uses muted gray/dim tones. The only saturated, loud color in the row should be the verdict badge (malicious=red, suspicious=yellow, clean=green, known_good=emerald, no_data=gray). No bright blues, purples, teals, or oranges in context/provider text.

---

### 6. Opacity transition is smooth

1. Navigate to a results page, watching an IOC row that's still loading
2. Observe the moment enrichment data appears in that row
3. **Expected:** The enrichment slot fades from `opacity: 0.85` to `opacity: 1.0` with a smooth 0.2s ease transition — no abrupt flash or jump

---

### 7. All 36 E2E tests still pass (regression check)

1. From project root in terminal: `pytest tests/e2e/test_results_page.py tests/e2e/test_extraction.py -q`
2. **Expected:** `36 passed` with no failures, no errors, no warnings about missing elements

---

## Edge Cases

### Context line empty for hash IOCs

1. Submit a result containing SHA256 hash IOCs
2. After enrichment, inspect the `.ioc-context-line` for a hash row
3. **Expected:** Context line is empty (no geo/ASN/DNS data for hashes) — the `.ioc-context-line:empty` CSS rule hides it cleanly. No empty-line gap in the layout.

### Multiple enriched rows — all get opacity:1

1. Submit a result with 10+ IOCs, wait for full enrichment
2. In devtools Console: `document.querySelectorAll('.enrichment-slot--loaded').length`
3. **Expected:** Count equals number of successfully enriched rows. Rows with no provider data may not have `--loaded` — confirm behavior is consistent.

### Micro-bar with all-clean results

1. Navigate to a result set where all IOCs are clean (no malicious/suspicious verdicts)
2. Locate `.verdict-micro-bar` in a clean IOC's summary row
3. **Expected:** Micro-bar shows solid green fill. Width still within 5rem–8rem bounds. No rendering artifact from an all-one-color bar.

---

## Failure Signals

- **Enrichment content visually dim after enrichment completes:** `.enrichment-slot--loaded` class not being applied by enrichment.ts — TS pipeline issue
- **Context line text indented ~16px from IOC value text:** `.ioc-context-line` padding-left not 0 — CSS change may have been lost or overridden
- **Micro-bar too narrow (< ~64px) or stretching full card width:** `.verdict-micro-bar` min/max-width rules missing or overridden
- **Any non-verdict bright colors visible in enrichment area:** R003 violation — check for new CSS rules with raw hex values
- **36 E2E tests fail:** Regression from CSS change breaking a DOM contract
- **Build fails (`make css` non-zero exit):** CSS syntax error introduced

---

## Requirements Proved By This UAT

- **R002** — At-a-glance enrichment surface (verdict badge, context line, provider stat line, micro-bar, staleness badge) renders at full opacity and correct alignment without any interaction
- **R003** — Enrichment surface uses only muted design tokens; no bright non-verdict colors present in at-a-glance area
- **R005** — Micro-bar proportion rendering is visually clean in full-width single-column layout

---

## Not Proven By This UAT

- **R002 full validation:** Dense readability under real analyst triage load — requires an analyst reviewing an actual threat intelligence scan result, not synthetic test data
- **Inline expand (R007):** Not built yet — S03 delivers this
- **Export, filter, search (R008):** Not validated in this slice — S04 integration verification
- **CSP/CSRF security contracts:** Not verified in this slice — S04 security verification

---

## Notes for Tester

- The opacity transition (0.2s ease) is subtle — you may need to refresh the page and watch carefully to catch the pre-load→loaded transition, especially on fast local enrichment runs.
- Context line alignment is easiest to check by selecting both `.ioc-value` and `.ioc-context-line` in devtools and comparing their left edge position in the Elements panel layout overlay.
- If enrichment runs very fast locally, the loading state (opacity:0.85) may be hard to observe. This is fine — the important thing is that loaded state is full opacity.
- The `opacity: 0.85` base rule on `.enrichment-slot` is intentional — don't flag it as a bug. The `--loaded` override bringing it to `1.0` is the fix this slice delivered.
