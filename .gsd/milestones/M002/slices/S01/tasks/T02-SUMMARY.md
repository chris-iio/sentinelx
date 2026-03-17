---
id: T02
parent: S01
milestone: M002
provides:
  - Quiet precision design system: verdict-only loud color, muted type badges, muted filter pills, typography hierarchy
key_files:
  - app/static/src/input.css
key_decisions:
  - IOC type badges collapsed to single neutral rule (color=text-muted, border=border-default) — all 8 type variants muted
  - Filter pill type-active states replaced with neutral active treatment — only verdict filter pills retain loud color when active
  - Dashboard KPI counts now use verdict-specific text color — counts are secondary verdict signal, labels stay muted
  - Mode indicator muted to neutral zinc — was using bright accent-ipv4 blue and accent-domain green
patterns_established:
  - "Quiet precision" pattern: loud color restricted to verdict classes only; all chrome/meta elements use zinc neutrals
  - Type identification via text content + neutral border shape, not color
  - Enrichment slot subordinate styling: min-height=0, opacity=0.85 — signals placeholder state without drawing attention
observability_surfaces:
  - make css stdout — Tailwind warns on unknown classes; bright-color regressions visible in browser devtools computed styles on .ioc-type-badge--*
  - Browser devtools Elements panel: .ioc-type-badge--* must show color=var(--text-muted); .verdict-label--* must show vivid verdict-* colors
duration: ~20min
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: Apply quiet precision design system — verdict-only loud color + typography hierarchy

**Muted all IOC type badge and filter pill type-colors to neutral zinc; verdict labels and dashboard KPI counts are the sole loud color signals on the results page.**

## What Happened

CSS-only work on `app/static/src/input.css`. The prior state had bright accent colors on `.ioc-type-badge--*` and `.filter-pill--{type}.filter-pill--active` that competed with verdict labels.

Changes made:
1. **IOC type badges** — all 8 type variants collapsed to `color: var(--text-muted); border-color: var(--border-default)`. Type still identifiable by text label and dot pseudo-element.
2. **Filter pill active states** — all 8 type-specific active rules replaced with a single neutral block (`bg-tertiary`, `text-secondary` border, `text-primary` text). Verdict pills left untouched.
3. **Typography hierarchy** — `.ioc-value` bumped from `0.83rem/normal` to `0.9rem/600` weight.
4. **Dashboard KPI counts** — added verdict-colored count rules per card variant (malicious=red-400, suspicious=amber-400, clean=sky-300, known_good=blue-400, no_data=zinc-400). Labels stay muted.
5. **Mode indicator** — muted offline/online pill from bright accent colors to neutral zinc.
6. **Copy button copied state** — muted from accent-domain green to neutral text-primary.
7. **Enrichment slot** — `min-height: 0`, `opacity: 0.85` — visually subordinate before S02 populates it.

## Verification

```
make css         → exit 0 (Done in 445ms)
make typecheck   → exit 0
make js-dev      → exit 0 (194.9kb bundle)
pytest tests/e2e/test_extraction.py tests/e2e/test_results_page.py -q → 36 passed in 7.05s
```

## Diagnostics

- `grep 'ioc-type-badge--ipv4' app/static/src/input.css` → should show `color: var(--text-muted)`
- `grep -A3 'filter-pill--ipv4.filter-pill--active' app/static/src/input.css` → should show neutral bg-tertiary
- Browser devtools: any `.ioc-type-badge--domain` computed color should be `#71717a` (zinc-500)

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `app/static/src/input.css` — Quiet precision design system: muted type badges, muted filter pills, verdict-colored KPI counts, typography hierarchy, subordinate enrichment slot
- `.gsd/milestones/M002/slices/S01/tasks/T02-PLAN.md` — Added Observability Impact section (preflight requirement)
