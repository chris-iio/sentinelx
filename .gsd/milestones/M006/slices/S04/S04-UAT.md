# S04: Input Page Redesign — UAT

**Milestone:** M006
**Written:** 2026-03-25T12:21:23.370Z

## UAT: S04 — Input Page Redesign

### Preconditions
- SentinelX running locally (`make run` or Flask dev server)
- Browser with DevTools available
- At least one past analysis saved (submit IOCs in online mode to populate history)

### Test 1: Vertical stacking layout
1. Open the home page (`/`)
2. **Expected:** Input card (textarea, buttons, mode toggle) appears above the recent analyses list, stacked vertically — not side-by-side
3. Resize browser to narrow width (< 600px)
4. **Expected:** Layout remains vertically stacked; no horizontal overflow or overlap

### Test 2: Design token consistency — transitions
1. Open DevTools → Inspect the mode toggle track element (`.mode-toggle-track`)
2. **Expected:** `transition` property references CSS custom properties, not hardcoded `0.2s ease`
3. Inspect the mode toggle thumb (`.mode-toggle-thumb`)
4. **Expected:** `transition` uses `var(--duration-fast)` and `var(--ease-out-quart)` (resolved values)
5. Inspect the mode toggle labels (`.mode-toggle-label`)
6. **Expected:** `transition` uses design tokens, not hardcoded `0.15s ease`

### Test 3: Button transition — no 'transition: all'
1. Inspect the Submit button (`#submit-btn`) or Clear button (`#clear-btn`)
2. **Expected:** `transition` property lists explicit properties (background-color, border-color, color, opacity, transform) — NOT `transition: all`
3. Click Submit button
4. **Expected:** Smooth background/border/color transition on hover/active states

### Test 4: Alert error token
1. Submit empty input or trigger a validation error
2. Inspect `.alert-error` element if visible
3. **Expected:** `color` property resolves to the `--verdict-malicious-text` token value — not hardcoded `#ff6b6b`

### Test 5: Recent analyses visual coherence
1. Navigate to `/` with at least one past analysis in history
2. **Expected:** Recent analyses list appears below the input card
3. **Expected:** Row hover transitions are smooth, using the same easing as results page elements
4. Click a recent analysis row
5. **Expected:** Navigates to `/history/<id>` and shows full results

### Test 6: Empty history state
1. Clear history data (or use a fresh browser/profile)
2. Navigate to `/`
3. **Expected:** No recent analyses section visible (or an empty state message) — no broken layout or orphan headings

### Test 7: Full regression — E2E homepage tests
1. Run `python3 -m pytest tests/e2e/test_homepage.py -v`
2. **Expected:** All 11 tests pass

### Test 8: Full regression — history route tests
1. Run `python3 -m pytest tests/test_history_routes.py -v`
2. **Expected:** All 13 tests pass

### Test 9: Full suite regression
1. Run `python3 -m pytest --tb=short -q`
2. **Expected:** 1043+ tests pass, zero failures
