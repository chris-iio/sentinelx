---
id: S01
parent: M002
milestone: M002
provides:
  - Single-column full-width row layout (no 2-column breakpoint on #ioc-cards-grid)
  - display:flex;flex-direction:column on .ioc-card — vertical row composition
  - Compact inline flex bar for verdict dashboard (replaces 5 large KPI boxes)
  - Single-row flex layout for filter bar
  - Quiet precision design system: verdict-only loud color, all type badges + filter pills muted to zinc neutrals
  - Typography hierarchy via font-weight/size/opacity instead of competing color
  - Verdict-colored KPI counts in dashboard as secondary signal
  - Enrichment slot visually subordinate (min-height:0, opacity:0.85) — placeholder for S02
requires: []
affects:
  - S02
  - S03
  - S04
  - S05
key_files:
  - app/static/src/input.css
  - app/templates/partials/_ioc_card.html
  - app/templates/partials/_verdict_dashboard.html
  - app/templates/partials/_filter_bar.html
  - app/templates/results.html
key_decisions:
  - D010 — Single-column full-width IOC rows replacing 2-column card grid
  - D011 — "Quiet precision" design language: verdict-only color, muted typographic hierarchy for everything else
  - D015 — All existing selector names and partial filenames preserved; internals mutated in place (not renamed to .ioc-row etc.)
  - T01 execution: Structural CSS and template DOM were already in target state from milestone initialization; only display:flex;flex-direction:column on .ioc-card was needed
  - T02 execution: All 8 IOC type badge variants collapsed to single neutral rule (color:var(--text-muted), border-color:var(--border-default)); filter pill type-active states replaced with neutral block; mode indicator muted to zinc
patterns_established:
  - "Quiet precision" pattern: loud color restricted to verdict classes only (.verdict-label--malicious/suspicious/clean/known_good/no_data); all chrome/meta elements use zinc neutrals
  - .ioc-card uses flex-direction:column — .ioc-card-header inside uses flex row (header + enrichment slot stack vertically)
  - Type identification via text content + neutral border shape, not color — removes "wall of badges" aesthetic
  - Verdict dashboard: flex-direction:row with border-right dividers, border-top color accent per verdict, verdict-colored count text as secondary signal
  - Filter bar: flex row with flex-wrap for responsive single-row collapse
  - Enrichment slot: visually subordinate (min-height:0, opacity:0.85) signals placeholder state without drawing attention
observability_surfaces:
  - "make css exits 0: Tailwind compiles cleanly (~440ms). Any unknown Tailwind class or bright-color regression shows in stdout."
  - "make typecheck exits 0: zero TS errors confirming all DOM contract selectors intact"
  - "make js-dev exits 0: bundle builds at 194.9kb (esbuild IIFE)"
  - "pytest tests/e2e/test_extraction.py tests/e2e/test_results_page.py -q → 36 passed: confirms contract selector presence in DOM"
  - "Browser devtools: .ioc-type-badge--* computed color must be ~#71717a (zinc-500/text-muted); .verdict-label--malicious must be vivid red"
drill_down_paths:
  - .gsd/milestones/M002/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M002/slices/S01/tasks/T02-SUMMARY.md
duration: ~35min (T01: 15min, T02: ~20min)
verification_result: passed
completed_at: 2026-03-18
---

# S01: Layout skeleton + quiet precision design system

**CSS-only migration from 2-column card grid to single-column row layout with verdict-only color; all 16 DOM contract selectors preserved intact; 36 E2E tests passing.**

## What Happened

This slice executed as two CSS-focused tasks against an already well-structured codebase.

**T01 (Layout skeleton):** On inspection, the milestone worktree had been initialized with the structural CSS and template DOM already targeting the desired state — `#ioc-cards-grid` had `grid-template-columns: 1fr` with no 2-column breakpoint, the verdict dashboard was already a flex row, and the filter bar was already a flex row. The only missing piece was `display:flex;flex-direction:column` on `.ioc-card` itself, which T01 added as the sole CSS change. Build tools (`tools/tailwindcss`, `tools/esbuild`) were absent from the worktree and installed via `make tailwind-install` / `make esbuild-install` before verification.

**T02 (Design system):** Pure CSS work muting all non-verdict loud colors. All 8 IOC type badge variants (ipv4, ipv6, domain, url, md5, sha1, sha256, cve) were collapsed to a single neutral rule: `color: var(--text-muted); border-color: var(--border-default)`. All 8 type-specific filter pill active states were replaced with a single neutral active block (`bg-tertiary`, muted border, `text-primary`). The offline/online mode indicator was muted from bright accent colors to neutral zinc. Verdict KPI counts in the dashboard now use verdict-specific text color as a secondary signal (malicious=red-400, suspicious=amber-400, clean=sky-300, known_good=blue-400, no_data=zinc-400) while labels stay muted. Typography hierarchy was refined: `.ioc-value` bumped to `0.9rem/weight:600`. Enrichment slot made visually subordinate (`min-height:0`, `opacity:0.85`) to signal placeholder state without drawing attention before S02 populates it.

## Verification

- `make css` → exit 0 (Done in 439ms)
- `make typecheck` → exit 0, zero errors
- `make js-dev` → exit 0, 194.9kb bundle
- `pytest tests/e2e/test_extraction.py tests/e2e/test_results_page.py -q` → **36 passed in 6.77s**
- Zero `grid-cols-2` or `repeat(2` in input.css (confirmed single-column)
- `.ioc-card` has `display:flex;flex-direction:column` confirmed
- All 16 contract selectors present: `.ioc-card`, `#ioc-cards-grid`, `#verdict-dashboard`, `.filter-bar-wrapper`, `.enrichment-slot`, `.ioc-context-line`, `.verdict-label`, `.ioc-type-badge`, `.copy-btn`, `[data-ioc-value]`, `[data-ioc-type]`, `[data-verdict]`, `[data-verdict-count]`, `[data-filter-verdict]`, `[data-filter-type]`, `#filter-search-input`

## Requirements Advanced

- **R001** — Single-column layout now active: `#ioc-cards-grid` renders as 1fr at all viewport widths with no 2-column breakpoint
- **R003** — Verdict-only color system in place: all type badges, filter pills, and chrome muted to zinc neutrals; verdict labels and dashboard KPI counts are sole loud color signals
- **R005** — Dashboard compressed to inline flex bar (structural CSS in place; at-a-glance data population is S02)
- **R006** — Filter bar compressed to single flex row (structural CSS in place)

## Requirements Validated

- None validated this slice — visual UAT and full runtime verification deferred to human spot-check

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

**T01:** The plan described substantial template restructuring across all four partials. In practice, the worktree was initialized with the target DOM structure already in place — only the single CSS addition to `.ioc-card` was required. This accelerated T01 significantly (15min vs. estimated 1.5h).

**T02:** No deviations. All planned changes executed as described.

## Known Limitations

- Enrichment slot is visually present but empty and subordinate — S02 must populate it with verdict badge, context line, provider stat line, micro-bar, staleness badge
- Verdict dashboard shows compressed structure but still renders `NO DATA` counts until enrichment completes — cosmetically acceptable but not the final at-a-glance experience (S02)
- Filter bar is structurally compact but filter functionality wiring is unchanged — S04 verifies full integration
- No visual polish pass yet: hover states, transitions, spacing refinements come in S04

## Follow-ups

- **S02:** Populate `.enrichment-slot` with at-a-glance surface — verdict badge, context line, provider stat line, micro-bar, staleness badge using row-factory.ts DOM builders
- **S04:** Polish pass — hover state transitions, row spacing, consistent border treatment under real enrichment data
- **S05:** Rename `.ioc-card` → `.ioc-row` and update partial filenames if desired (D015 deferred this; S05 is the right time when E2E selectors are being updated anyway)

## Files Created/Modified

- `app/static/src/input.css` — Added `display:flex;flex-direction:column` to `.ioc-card` (T01); muted all 8 type badge variants, muted type-active filter pills, muted mode indicator, added verdict-colored KPI counts, refined typography hierarchy, subordinated enrichment slot (T02)

## Forward Intelligence

### What the next slice should know

- **Enrichment slot position:** `.enrichment-slot` is a direct child of `.ioc-card-header` (which is itself a flex row). The slot sits as the second item in the header flex row. When S02 builds the at-a-glance surface, the DOM builders must target `.enrichment-slot` as the container — do not create a parallel container.
- **Design token reference:** All verdict colors live in CSS custom properties: `--verdict-malicious`, `--verdict-suspicious`, `--verdict-clean`, `--verdict-known_good`, `--verdict-no_data`. Typography: `--text-primary`, `--text-secondary`, `--text-muted`. Borders: `--border`, `--border-default`. Background: `--bg-primary`, `--bg-secondary`, `--bg-tertiary`.
- **Selector contract is frozen:** D015 locks all 16 contract selectors. Do not rename `.ioc-card`, `.ioc-type-badge`, etc. in S02 or S03 — that migration is explicitly deferred to S05.
- **Build tools are local:** `tools/tailwindcss` and `tools/esbuild` are installed locally to the worktree. They are not in PATH. Always use `make css`, `make typecheck`, `make js-dev` — not bare binary calls.

### What's fragile

- **Enrichment slot opacity:** `.enrichment-slot` has `opacity:0.85` as a placeholder visual signal. S02 must override or clear this when enrichment data arrives — otherwise rendered enrichment content will be slightly dimmed.
- **Verdict dashboard at-a-glance gap:** The compressed dashboard structure shows counts but has no visual connection to the row results until enrichment completes. This looks slightly disconnected on first render — S02's enrichment surface will close the gap perceptually.
- **Filter pill muting:** Type-active filter pills use a single neutral active block. This is intentional but means active type filters look identical to verdict filters visually. If this creates UX confusion during S04 polish, revisit with a subtle shape/icon differentiator rather than reintroducing color.

### Authoritative diagnostics

- `make typecheck` — First check for any DOM contract breakage. TS errors name the exact missing selector or attribute.
- `pytest tests/e2e/test_results_page.py -q` — Confirms structural DOM contracts at the HTML level; catches partial renames, missing data-* attributes.
- `grep -n 'ioc-type-badge--' app/static/src/input.css` — Quickly verify type badge variants still muted after any future CSS edit.
- Browser devtools computed styles on `.ioc-type-badge--domain` — should show `color: #71717a` (zinc-500 / text-muted). Any bright color there signals a regression.

### What assumptions changed

- **"Substantial template restructuring needed"** — The plan assumed all four template partials needed structural rewriting. In reality, the worktree was initialized with the target DOM structure already in place. S02 planners should re-verify the actual file state rather than assuming the plan's "files likely touched" list reflects pre-existing state.
