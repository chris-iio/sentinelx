---
estimated_steps: 6
estimated_files: 1
---

# T01: Fix enrichment slot opacity and refine at-a-glance CSS for full-width rows

**Slice:** S02 — At-a-glance enrichment surface
**Milestone:** M002

## Description

The `.enrichment-slot` in `input.css` has `opacity: 0.85` as a placeholder visual signal (added in S01 to make the slot visually subordinate before enrichment data arrives). When enrichment completes, `enrichment.ts` adds the class `.enrichment-slot--loaded` — but no CSS rule resets the opacity. This means all enrichment content (verdict badge, context line, provider stats, micro-bar, staleness badge) renders at 85% opacity permanently.

Additionally, the at-a-glance component styles (`.ioc-summary-row`, `.ioc-context-line`, `.verdict-micro-bar`, `.staleness-badge`) were authored for the old 2-column card grid. In the new S01 single-column full-width layout, spacing and sizing may need adjustment for readability.

This task fixes the opacity bug and tunes the at-a-glance CSS for the new layout. No TypeScript changes — the DOM builders work correctly already.

**Relevant skill:** `frontend-design` (CSS refinement work)

## Steps

1. Open `app/static/src/input.css` and locate the `.enrichment-slot` rule (around line 1143). Confirm it has `opacity: 0.85`.

2. **Add the opacity fix.** After the `.enrichment-slot` base rule block, add:
   ```css
   .enrichment-slot.enrichment-slot--loaded {
       opacity: 1;
       transition: opacity 0.2s ease;
   }
   ```
   Do NOT remove the base `opacity: 0.85` — it serves as the shimmer/placeholder visual signal. The `--loaded` class override is the correct pattern.

3. **Audit `.ioc-context-line` spacing** (around line 1091). Current padding is `0.125rem 1rem 0.25rem`. In the full-width row layout, the left padding (`1rem`) should align with the content inside `.ioc-card` (which has `padding: 0.6rem 1rem`). Since the context line is a direct child of `.ioc-card` and the card already has `1rem` horizontal padding, the context line's own left padding should be `0` to avoid double-padding. Check the actual rendered alignment — if the context line text aligns with the IOC value text above without its own left padding, remove it. If the card padding doesn't apply (e.g., context line is nested differently), keep the `1rem`.

   Look at the template `_ioc_card.html`: `.ioc-context-line` is a direct child of `.ioc-card`. The card has `padding: 0.6rem 1rem`. So the context line inherits the card's horizontal padding. Its own `padding: 0.125rem 1rem` adds an extra 1rem of left padding → total 2rem indent. Fix to `padding: 0.125rem 0 0.25rem` so it aligns with the header content.

4. **Tune `.ioc-summary-row`** (around line 1205). The summary row is inside `.enrichment-slot` which is inside `.ioc-card`. Review:
   - Gap (`0.5rem`) — should be fine for full-width
   - Padding (`0.5rem 0`) — the top padding creates spacing from the context line above; the zero horizontal padding means it inherits the card's 1rem padding. This should be correct.
   - Ensure the `.verdict-badge` inside the summary row is visually secondary to the `.verdict-label` in the card header. The badge has `font-size: 0.72rem` and is a small pill. The header label is larger. This hierarchy should already work — no change expected unless inspection shows otherwise.

5. **Tune `.verdict-micro-bar`** (around line 1253). Current `min-width: 4rem` may be too narrow in a full-width row where there's ample space. Consider increasing to `min-width: 5rem; max-width: 8rem` so the bar has more visual presence in the wider layout without growing unbounded.

6. **Verify no bright non-verdict colors.** Scan the rules you've edited/added to confirm all colors reference `--text-muted`, `--text-secondary`, `--text-primary`, `--bg-*`, `--border*`, or `--verdict-*` tokens only. No raw bright hex values in the at-a-glance components.

7. **Build CSS:** Run `make css` from the project root and confirm it exits 0.

## Must-Haves

- [ ] `.enrichment-slot.enrichment-slot--loaded { opacity: 1; }` rule exists in `input.css`
- [ ] Base `.enrichment-slot` still has `opacity: 0.85` (not removed)
- [ ] `.ioc-context-line` padding adjusted so text aligns with IOC value in card header (no double-padding)
- [ ] `.verdict-micro-bar` width constraints tuned for full-width context
- [ ] No raw bright hex colors introduced in at-a-glance CSS rules
- [ ] `make css` exits 0

## Verification

- `make css` exits 0 (run from project root — uses `tools/tailwindcss` locally)
- `grep -n 'enrichment-slot--loaded' app/static/src/input.css` shows the new opacity rule
- `grep -n 'opacity: 0.85' app/static/src/input.css` still matches the base `.enrichment-slot` rule
- No bright non-verdict colors in the modified rules (manual scan)

## Inputs

- `app/static/src/input.css` — Current S01 state with `opacity: 0.85` on `.enrichment-slot` (line 1151), context line styles (lines 1088-1098), summary row styles (lines 1205+), micro-bar styles (lines 1253+), staleness badge (lines 1497+)
- S01 summary confirms: `.enrichment-slot` is inside `.ioc-card` (which has `padding: 0.6rem 1rem`); `.ioc-context-line` is a direct child of `.ioc-card`; enrichment slot layout is flex-column with gap
- Design tokens available: `--verdict-*` for verdict colors, `--text-muted`/`--text-secondary`/`--text-primary` for text, `--bg-*` for backgrounds, `--border`/`--border-default` for borders
- Build: always use `make css` (not bare tailwindcss binary) — tools are worktree-local

## Expected Output

- `app/static/src/input.css` — Modified with: opacity fix rule for `.enrichment-slot--loaded`, context line padding fix, micro-bar width tuning; `make css` exits 0

## Observability Impact

- **Signal added:** `.enrichment-slot.enrichment-slot--loaded { opacity: 1 }` — when enrichment data arrives and `enrichment.ts` adds the `--loaded` class, opacity transitions from 0.85 → 1. Inspectable via browser devtools computed styles on any `.enrichment-slot.enrichment-slot--loaded` element.
- **Failure state:** If content remains at 85% opacity after enrichment completes, two distinct causes are now diagnosable: (1) CSS issue — rule missing or overridden (check computed `opacity` in devtools); (2) TS pipeline issue — `enrichment-slot--loaded` class never applied (check `document.querySelectorAll('.enrichment-slot--loaded').length === 0` while enriched results are on screen).
- **Context line alignment:** `.ioc-context-line` padding reduced from `0.125rem 1rem` to `0.125rem 0` — text now aligns flush with `.ioc-card` left edge (card provides the `1rem` horizontal padding). Misalignment after this change would indicate the template hierarchy changed (context line no longer a direct child of `.ioc-card`).
