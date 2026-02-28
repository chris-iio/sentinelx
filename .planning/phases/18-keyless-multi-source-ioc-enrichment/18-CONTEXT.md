# Phase 18: Home Page Modernization - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Transform the home page into a clean, minimal, contemporary experience. Thinner header with only logo, brand, and settings icon; compact auto-growing textarea starting at ~5 rows; tighter inline form controls; and a simplified footer matching the header's stripped-down tone. Frontend-only — no backend changes.

</domain>

<decisions>
## Implementation Decisions

### Header Elements
- Settings link becomes icon-only (gear icon, no "Settings" text) — keep aria-label for accessibility
- Brand text keeps the emerald accent split: "Sentinel" in emerald-500, "X" in white
- Logo icon + brand text wrapped in an `<a>` linking to home page (`/`)
- "IOC Triage Tool" tagline removed entirely

### Textarea Behavior
- Default rows reduced from 14 to ~5 visible rows
- Auto-grow: textarea expands vertically as content is typed or pasted
- Resize handle removed (`resize: none`) — auto-grow replaces manual resize
- Scrollbar appears inside textarea once max height is reached
- Input card container (bordered card with shadow) stays — provides visual grouping

### Footer
- Footer padding matches header padding for visual symmetry (bookend framing)

### Claude's Discretion
- Exact header padding value (must be visibly thinner than current 0.75rem)
- Textarea max height cap (should be reasonable — not fill entire viewport)
- Auto-grow transition: instant or smooth (pick what feels best)
- Placeholder text: current 4-line IOC examples or shorter single-line hint
- Form controls gap reduction (must be noticeably tighter than current 1rem)
- Whether to remove "IOC Text" form label (keep aria-label if removed)
- Whether to remove input card title ("Extract IOCs") and subtitle
- Footer text content (minimal — current "SentinelX — IOC Triage Tool" is too verbose)
- Footer background color (matching header zinc-900 or transparent)
- Footer font size (current 0.75rem or smaller)

</decisions>

<specifics>
## Specific Ideas

- The header should feel like a utility bar — logo, brand, settings — nothing else
- The page should feel like you land and immediately start typing/pasting — minimal chrome between header and textarea
- Footer should be a whisper, not a statement — symmetric with the header's restraint

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `macros/icons.html`: Jinja2 icon macro for inline SVG Heroicons (already renders cog-6-tooth)
- `logo.svg` in `app/static/images/` — current 28x28 logo icon
- CSS custom properties at `:root` for all design tokens (colors, fonts, spacing, shadows)
- Existing animation keyframes: `fadeIn`, `fadeSlideUp` — used by header, footer, input card
- `.brand-accent` class already styles "Sentinel" in emerald

### Established Patterns
- Jinja2 template inheritance: `base.html` defines header/footer, page templates extend it
- CSS lives in `app/static/src/input.css` → built to `app/static/dist/style.css` via Tailwind
- Vanilla JS in `app/static/main.js` — no framework; event listeners attached on DOMContentLoaded
- BEM-like naming: `.site-header`, `.header-inner`, `.site-logo`, `.site-nav`, `.input-card`
- `@layer components` in CSS for component styles

### Integration Points
- `base.html` (lines 23-31): header template — changes here affect ALL pages (index, results, settings)
- `base.html` (lines 38-40): footer template — same global impact
- `index.html` (lines 1-63): textarea, form controls, input card — index page only
- `input.css` (lines 219-298): header/footer CSS; (lines 308-428): input card/textarea/form CSS
- `main.js` (lines 34-70): submit button + clear button logic tied to textarea by ID
- `main.js` (lines 74-100): mode toggle tied to widget by ID
- Auto-grow JS will need to be added to `main.js` (no existing auto-grow logic)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 18-keyless-multi-source-ioc-enrichment*
*Context gathered: 2026-02-28*
