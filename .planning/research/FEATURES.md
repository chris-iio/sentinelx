# Feature Research — UI Patterns for v1.2 Modern Redesign

**Domain:** Premium dark-first SaaS UI patterns for a security/analyst tool
**Researched:** 2026-02-25
**Confidence:** HIGH (pattern analysis from Linear, Vercel, Stripe, shadcn/ui), MEDIUM (specific implementation values), LOW (where noted)

> **Scope note:** This document supersedes the v1.0 functional feature research (which covered IOC extraction, enrichment providers, and API integrations). That document remains at `.planning/research/FEATURES.md.v1` for reference. This document covers **UI patterns only** — the visual and interaction design patterns that make the existing functional features feel premium. Zero new backend features are in scope.

---

## Context: What Already Exists

The codebase has a functioning dark UI built on CSS custom properties + Tailwind CSS. The color system is GitHub-dark-inspired (zinc/slate backgrounds, green primary button). What it lacks is the premium SaaS treatment applied to each component category. The redesign is not a rewrite — it is a visual elevation of the existing structure.

**Existing design tokens (from `app/static/src/input.css`):**
- Background: `#0d1117` (primary), `#161b22` (secondary), `#1c2128` (tertiary)
- Border: `#30363d` (default), `#484f58` (hover)
- Verdict colors: red `#f85149`, amber `#f59e0b`, green `#3fb950`, gray `#8b949e`
- IOC type accents: blue `#4a9eff`, green `#4aff9e`, cyan `#4aeeee`, orange `#ff9e4a`, red `#ff4a4a`
- Font UI: system-ui stack; Font mono: Fira Code / JetBrains Mono

**The gap:** Components exist structurally but lack the micro-detail that produces the premium feel — hover states are abrupt, borders are flat, the verdict dashboard has no visual weight, cards don't communicate state hierarchy, and the typography lacks the size differentiation of Linear/Vercel dashboards.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Premium dark tool UI patterns that analysts will notice if missing. These are not optional polish — they are the foundation of "this feels like a real product."

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Card border + background differentiation (elevation) | In dark UIs, shadows disappear — border + background contrast is how elevation is communicated. A card that looks identical to the page background feels broken. | LOW | Move from flat `var(--bg-secondary)` cards on `var(--bg-primary)` background to a 3-level system: page bg / card bg / card header bg. Current difference is too subtle. |
| Verdict-colored card left border (thick, 3-4px) | Every security tool with severity levels uses colored left borders to convey verdict at a glance. Present in current code but underutilized — needs more visual weight. | LOW | Increase from 3px to 4px, add a `box-shadow: inset 3px 0 0 var(--verdict-X)` fallback for browsers that need it. |
| Focus ring on all interactive elements | Accessibility requirement and quality signal — premium tools have clearly styled focus rings that match the accent color. Current implementation uses blue (#4a9eff) universally but inconsistently. | LOW | Standardize: all inputs get `0 0 0 3px rgba(accent, 0.25)` ring; emerald/teal for online-mode forms, blue for offline-mode. Remove outline:none-without-replacement entirely. |
| Smooth hover transitions on all interactive elements | Click targets that respond instantly feel cheap; 150ms ease transitions signal quality. Current code has transitions on some elements but not all (missing on verdict-dashboard-badge, IOC cards, enrichment slots). | LOW | Audit all interactive elements, add `transition: all 0.15s ease` or per-property transitions everywhere. |
| Typography weight differentiation | Primary/secondary text hierarchy is the single most effective way to create visual clarity. Current: 1.5rem titles, 0.85rem body, but intermediate levels are missing. | LOW | Add a 3-tier scale: `1.1rem/600` for section headers, `0.875rem/400` for body, `0.75rem/400` for captions/metadata. |
| Monospace font for all IOC values | IOC values (IPs, hashes, domains) must render in monospace for analyst readability. Currently implemented but inconsistently — some enrichment detail rows fall through to system-ui. | LOW | Audit all `.enrichment-detail`, `.provider-result-row`, `.ioc-original` selectors. Confirm `var(--font-mono)` applied universally to IOC data. |
| Accessible color contrast (WCAG AA minimum) | Dark themes routinely fail contrast. The current `#8b949e` secondary text on `#161b22` background is marginal at WCAG AA. | LOW | Test current palette with browser devtools contrast checker. Raise secondary text to `#9ca3af` minimum (Tailwind zinc-400) where needed. |
| Sticky filter bar backdrop blur | A sticky element without background treatment causes text to overlap visually. Current sticky filter bar has `background-color: var(--bg-primary)` but no blur — looks abrupt on scroll. | LOW | Add `backdrop-filter: blur(8px)` with semi-transparent background fallback for the sticky filter bar. Standard pattern in Linear, Vercel, and GitHub's nav. |

### Differentiators (Competitive Advantage)

These patterns make SentinelX feel like a purpose-built security product, not a generic dark dashboard. The reference products for these patterns are Linear (precision, minimal chrome), Vercel (developer-centric data display), and Stripe (status badge system).

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Verdict stat cards with large number display | Vercel/Stripe-style KPI cards: the count is the hero element (`2rem+ monospace`) with the label below in small caps. Currently the verdict dashboard uses inline badge pills — no visual hierarchy between the number and label. | MEDIUM | Replace inline pills with 4 individual stat cards in a horizontal row. Each card: colored top border, large mono number, small label. Malicious = red-tinted border + red number; Clean = green; etc. Active/clickable filter state: card gets tinted background. |
| Card hover elevation effect | Linear cards use `translateY(-1px)` + `border-color` shift on hover to suggest liftability. The analyst scans dozens of IOC cards — hover feedback helps orient which card they're about to interact with. | LOW | Add `transform: translateY(-1px)` + `border-color: var(--border-hover)` + `box-shadow: 0 4px 12px rgba(0,0,0,0.3)` on `.ioc-card:hover`. Transition: `150ms ease`. No hover on verdict-colored border — that stays fixed to avoid confusion with state. |
| Shimmer skeleton for enrichment-pending state | Current: spinner + "Pending enrichment..." text. Premium pattern: a skeleton `<div>` with animated shimmer gradient that mirrors the shape of the enrichment result rows. Matches what Linear, GitHub, and Vercel use while loading content. | MEDIUM | Replace `.spinner-wrapper` with 2-3 skeleton lines per card. CSS: `background: linear-gradient(90deg, var(--bg-tertiary), var(--bg-secondary), var(--bg-tertiary))` animated `background-position` from left to right via `@keyframes shimmer`. Width: full card width. Lines: narrow (1 row badge-height) + wider (detail row height). |
| Progress bar with gradient fill and completion state | Current progress bar exists (`enrich-progress-fill`) with a blue→cyan gradient. The differentiator is a completion animation: when 100% is reached, transition the gradient from blue→cyan to green→emerald and briefly `scale-x` the bar to 102% then back. | LOW | Extend existing `.enrich-progress.complete` class with a `@keyframes complete-pulse` animation. Completion: CSS class swap triggered by JS when count matches total. |
| IOC type pill with dot indicator (not just text) | Linear and Vercel use small colored dot indicators alongside labels to convey category at a glance without relying entirely on text. Current `.ioc-type-badge` is text-only. | LOW | Add a 6px circle `::before` pseudo-element to each `.ioc-type-badge--{type}` rule, colored to match the accent. The dot precedes the type text. Increases scannability on hash-heavy result sets. |
| Search input with search icon prefix | The current `filter-search-input` is a plain text input. Premium pattern (Vercel, Linear, GitHub): a magnifying glass icon positioned absolutely in the left padding of the input, with `padding-left: 2.25rem` to avoid overlap. | LOW | Add a `<span>` or SVG icon wrapper absolutely positioned inside the `.filter-search` container. SVG can be inline or a CSS `background-image: url()` data URI — no image file needed. |
| Verdict badge with colored dot + text (not background fill) | Current `.verdict-label--suspicious` uses `background-color: #f59e0b; color: #000` — a filled badge on a dark background creates harsh contrast and breaks the design language. Premium pattern (Stripe badges): `background: rgba(color, 0.12); border: 1px solid rgba(color, 0.3); color: var(--verdict-color)` — tinted background, colored border, colored text. | LOW | Standardize all verdict badges to the tinted-background pattern. Fix `--suspicious` to use `rgba(245, 158, 11, 0.15)` background + amber text (not solid amber + black text). This aligns all 4 verdict states to the same visual system. |
| Empty state with icon and actionable message | Current `.no-results` is 2 lines of gray text centered in a card. Linear/Vercel empty states: a simple SVG icon (not illustration) at 32-40px, a bold headline, a secondary explanation sentence, and optionally a CTA link. For SentinelX: a magnifying glass or shield icon, "No IOCs detected" headline, "Try pasting a threat report, SIEM alert, or email header" secondary line. | LOW | Replace content inside `.no-results` with a 3-part structure: icon + heading + body. Use a simple SVG path (no external dependency). Centered layout, icon color = `var(--text-secondary)`. |
| Settings section card with descriptive header row | Vercel/Linear settings pages use a pattern: each section is a card with a top-row showing section name (bold, left) + action button (right), then a divider, then the form fields below. Creates clear section boundaries and scannability. Current settings page uses `<h2>` headings with no visual card structure. | MEDIUM | Wrap each settings section in a card with: header row (`display: flex; justify-content: space-between`), a `1px solid var(--border)` divider, then the form content. For the VT API key section: header reads "VirusTotal API" with a "Save" button aligned right. |
| Paste feedback with success animation | Current `.paste-feedback` is plain italic text that appears on paste. Premium pattern: brief appearance with a `transform: translateY(-4px)` + opacity fade in animation. Disappears after 2.5s. Vercel uses similar micro-animation for clipboard confirmations. | LOW | Add `@keyframes feedback-appear { from { opacity: 0; transform: translateY(2px); } to { opacity: 1; transform: translateY(0); } }` to `.paste-feedback`. JS already shows/hides it — just add the CSS animation class on show. |
| Contextual submit button with mode indicator | Already exists (contextual label changes). The differentiator: when Online mode is active, the submit button gets a green/emerald background instead of the default green. When Offline, a subtle blue-tinted variant. This reinforces the mode state without redundancy. | LOW | Add `.btn-primary--online` and `.btn-primary--offline` modifier classes. JS toggles the class when mode changes. Colors: online = `var(--accent-domain)` (#4aff9e) tint; offline = `var(--accent-ipv4)` (#4a9eff) tint. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem like obvious improvements but undermine the tool's design goals or create technical debt.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Glassmorphism / frosted-glass cards | Trendy, looks premium in mockups | `backdrop-filter: blur()` on content cards creates constant GPU compositing overhead. On a results page with 50+ cards this causes scroll jank. Also creates accessibility issues with low contrast over blurred backgrounds. | Use backdrop-filter only on the sticky filter bar (one element, not repeated). Cards use solid backgrounds. |
| Pure black `#000000` background | Maximum contrast, dramatic look | High contrast between pure black and light text causes "halation" (text appears to bleed) for users with astigmatism. OWASP and Nielsen Norman Group both document this as a usability issue for extended reading. | Stay on dark zinc/slate grays: `#0d1117` is correct. Never go below `#0a0a0a` for body background. |
| Animation-heavy micro-interactions | Delightful, premium feel | SOC analysts use this tool under time pressure. Animations that play every time a result card appears (if not respecting `prefers-reduced-motion`) add cognitive load and frustration for power users who run the tool dozens of times per shift. | All animations must be gated by `@media (prefers-reduced-motion: no-preference)`. Durations: 100-200ms max for state changes, never longer. No entrance animations on card grid load. |
| Custom scrollbar styling | Polish signal, frequently requested | Webkit scrollbar CSS is non-standard and not supported in Firefox without `scrollbar-color` CSS. Cross-browser scrollbar styling requires two separate CSS approaches and still looks different per OS. Return on investment is very low. | Leave scrollbars at OS default. If requested, use `scrollbar-color: var(--border) var(--bg-primary)` (Firefox) + `-webkit-scrollbar` (Chrome) as a single low-risk addition, never as a priority. |
| Sidebar navigation | More surface area for features | The tool has 3 pages (input, results, settings). A sidebar would consume 220px of horizontal space on a tool that needs that width for IOC values (hashes are 64 chars). The current top-bar header with Settings nav-link is the correct information architecture for this scope. | Keep flat header. If navigation grows beyond 4 items, consider a `<nav>` with horizontal tabs — never a vertical sidebar for this tool. |
| Dark/light mode toggle | Universal user preference | Adding a light mode doubles the CSS maintenance burden for every new component. This is a security tool used in SOC environments (low-light) — light mode is not a real use case for the user base. | Respond to `prefers-color-scheme: light` with a simple variable swap if demanded, but do not build a toggle UI. Never a priority item. |
| Inline charts / sparklines for verdict trends | Dashboard feel, context about IOC history | Single-shot triage tool — there is no history to chart within a session. Verdict dashboard counts are the correct scope. Charts would require a charting library (adds ~50KB to page weight) for zero functional value. | The 4 verdict stat cards with counts are the correct data visualization. No charts. |
| Tooltip-based information architecture | Detailed provider metadata on hover | Tooltips are inaccessible (keyboard, touch) and create invisible information architecture. Analysts may not discover that provider details live in tooltips. | Use `<details>/<summary>` collapsible sections (already in use for `enrichment-nodata-section`) — visible structure, accessible, no JS required. |
| Infinite scroll for IOC cards | Modern list pattern | A paste of 10 URLs is not a pagination problem — it is a layout problem. The current 2-column grid is the correct approach. Infinite scroll adds JS complexity for a problem that doesn't exist. | Keep current grid. If card count exceeds 100 (rare), address with a "Showing first 100" message and "Show all" reveal — not infinite scroll. |

---

## Feature Dependencies

```
Verdict Stat Cards (differentiator)
    └──requires──> Verdict color system (already exists in --verdict-* variables)
    └──enhances──> Filter bar verdict buttons (clicking stat card = filter)

Card Hover Elevation Effect
    └──requires──> Card border system (already exists)
    └──conflicts with──> Border-left verdict color (don't move the verdict border on hover — it creates state confusion)

Shimmer Skeleton for Enrichment Pending
    └──replaces──> Current spinner-wrapper + enrichment-pending-text
    └──requires──> Same slot dimensions as eventual result rows (must mirror height)
    └──enhances──> Enrichment result arrival (content "replaces" skeleton — no layout shift)

Search Input with Icon Prefix
    └──requires──> Layout adjustment: padding-left on filter-search-input
    └──enhances──> Filter bar visual hierarchy (icon differentiates from verdict/type filters)

Progress Bar Completion Animation
    └──requires──> Existing enrich-progress and .complete CSS class (already exists)
    └──requires──> No new JS — class already toggled by enrichment polling
    └──enhances──> Online mode results page perceived completeness signal

Settings Section Card Pattern
    └──requires──> New .settings-section-card component CSS
    └──conflicts with──> Current plain .settings-section h2 structure (requires HTML refactor)
```

### Dependency Notes

- **Verdict stat cards conflict with current verdict-dashboard-badge pills:** The new stat card pattern replaces the current inline badges. The HTML structure of `results.html` and the verdict-counting JS in `main.js` must both change, but the data attributes (`data-verdict-count`) can be preserved on the new elements.
- **Shimmer skeleton requires known card slot dimensions:** The skeleton must be the same height as the enriched result. If the enrichment slot expands when results arrive, there will be layout shift. Pre-set `min-height` on `.enrichment-slot` to the typical result height (~60px for 2 provider rows).
- **Backdrop-filter on sticky filter bar requires isolation:** The filter bar parent must have `isolation: isolate` to avoid compositing issues with the card grid behind it.

---

## MVP Definition

### v1.2 Launch With (High Visual Impact, Low Complexity)

The minimum set that produces a measurably premium feel. Prioritized by impact-to-effort ratio.

- [x] Fix verdict badge visual system — standardize all 5 verdict states to tinted-bg + colored-border + colored-text (no more solid amber on black) — **highest consistency fix**
- [x] Card hover elevation effect — `translateY(-1px)` + shadow on `.ioc-card:hover` — **1 CSS block, immediate premium feel**
- [x] Typography weight differentiation — add intermediate heading size, tighten caption text — **3 CSS rule changes**
- [x] Focus ring standardization — uniform `0 0 0 3px rgba(accent, 0.25)` across all interactive elements — **accessibility + quality signal**
- [x] Sticky filter bar backdrop-blur — `backdrop-filter: blur(8px)` on `.filter-bar-wrapper` — **1 CSS property**
- [x] Paste feedback animation — `@keyframes` appear animation on `.paste-feedback` — **5 CSS lines**
- [x] IOC type badge dot indicator — `::before` colored dot on `.ioc-type-badge--*` — **8 CSS rules (1 per type)**
- [x] Empty state icon + headline — replace 2 lines of text with icon + bold heading + body — **HTML + 4 CSS rules**
- [x] Search input icon prefix — SVG magnifying glass in `.filter-search` — **1 SVG + 2 CSS rules**

### v1.2 Add After Core Is Solid

- [ ] Verdict stat cards — replace dashboard pill badges with 4 individual KPI cards — **requires HTML refactor + CSS**
- [ ] Shimmer skeleton loading — replace spinner with animated skeleton rows — **new CSS @keyframes + JS class swap**
- [ ] Settings section card pattern — wrap settings in bordered card with header row — **HTML refactor + CSS**
- [ ] Progress bar completion animation — completion pulse on enrichment finish — **2 CSS additions**
- [ ] Mode-aware submit button variant — color shifts when online/offline — **2 CSS modifier classes + 2 JS lines**

### v1.2 Future Consideration

- [ ] Contextual copy button tooltip on hover — "Copy IOC" text appears on hover, auto-fades — defer, complexity vs value unclear
- [ ] Search result highlighting — highlight matched text in IOC value when filter is active — HIGH complexity (requires DOM text manipulation)
- [ ] Header breadcrumb trail — show "Results > 12 IOCs > Online Mode" — LOW value for 2-page nav structure

---

## Feature Prioritization Matrix

| UI Feature | Analyst Value | Implementation Cost | Priority |
|------------|---------------|---------------------|----------|
| Verdict badge visual fix | HIGH (consistency, clarity) | LOW (CSS only) | P1 |
| Card hover elevation | HIGH (premium feel, orientation) | LOW (CSS only) | P1 |
| Focus ring standardization | HIGH (accessibility) | LOW (CSS audit) | P1 |
| Typography differentiation | HIGH (hierarchy, readability) | LOW (CSS only) | P1 |
| Sticky filter backdrop-blur | MEDIUM (polish) | LOW (1 CSS property) | P1 |
| Empty state icon + message | MEDIUM (completeness, UX) | LOW (HTML + CSS) | P1 |
| Search input icon | MEDIUM (discoverability) | LOW (SVG + CSS) | P1 |
| Paste feedback animation | MEDIUM (micro-delight) | LOW (CSS keyframes) | P1 |
| IOC type badge dot | MEDIUM (scannability) | LOW (CSS ::before) | P1 |
| Verdict stat cards (KPI) | HIGH (information hierarchy) | MEDIUM (HTML + JS refactor) | P2 |
| Shimmer skeleton | HIGH (perceived performance) | MEDIUM (new CSS pattern) | P2 |
| Progress bar completion anim | MEDIUM (feedback clarity) | LOW (CSS class extension) | P2 |
| Settings section card | MEDIUM (page completeness) | MEDIUM (HTML refactor) | P2 |
| Mode-aware submit button | LOW (redundant with toggle label) | LOW (CSS modifier) | P2 |
| Custom scrollbar | LOW (cross-browser inconsistent) | MEDIUM (dual CSS) | P3 |
| Copy button tooltip | LOW | MEDIUM | P3 |
| Search result highlighting | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for v1.2 launch — high impact, low cost
- P2: Should have — significant improvement, moderate cost
- P3: Nice to have — defer to v1.3 or later

---

## Pattern Reference by Component

### 1. Card Component Pattern (IOC Cards)

**Reference products:** Linear (issue cards), Vercel (deployment cards), GitHub (PR cards)

**What these products do:**
- Background is 2 levels above page background (not 1)
- 1px border with `rgba(white, 0.08)` to `rgba(white, 0.12)` opacity — not a solid hex color
- On hover: border opacity rises to 0.2, `box-shadow: 0 4px 16px rgba(0,0,0,0.4)`, `translateY(-1px)`
- Left accent border: 3-4px, solid verdict color, does NOT change on hover (state indicator is static)
- Card header: `background` is one step lighter than card body (Linear uses this for the "row header" in issue lists)
- Content density: tight padding (0.75rem) but with enough breathing room in the header row
- Transition: `150ms ease` on transform + border — not `all` (too broad, catches unwanted props)

**What SentinelX currently does vs. what to change:**
- Current: flat `#161b22` card on `#0d1117` page — difference is too subtle
- Change: add a card-header `background: var(--bg-tertiary)` strip for the `.ioc-card-header`
- Current: `border: 1px solid #30363d` (solid hex) — works but not premium
- Change: `border: 1px solid rgba(255,255,255,0.08)` — more luminous feel on dark
- Add: hover elevation as described above

**Tailwind equivalent (if refactoring to utility classes):**
```
border border-white/8 hover:border-white/15 hover:shadow-lg hover:-translate-y-px transition-[border-color,box-shadow,transform] duration-150
```

### 2. Form/Input Pattern (Textarea, Text Inputs)

**Reference products:** Linear (issue description editor), Vercel (env var inputs), Stripe (form fields)

**What these products do:**
- Background: 1 level below card background (deepest surface) — inputs feel "inset"
- Border: `rgba(white, 0.1)` resting, transitions to `rgba(accent, 0.6)` on focus
- Focus ring: `box-shadow: 0 0 0 3px rgba(accent, 0.2)` — not just border change
- Placeholder: `rgba(text, 0.35)` — notably dimmer than body text
- Font: monospace for code-like inputs (IOC textarea), system-ui for label inputs
- No border-radius above 6-8px — rounded corners > 8px feel consumer, not professional
- Transition: `border-color 0.15s ease, box-shadow 0.15s ease` specifically (not `all`)

**What SentinelX currently does vs. what to change:**
- Focus ring uses `rgba(74, 158, 255, 0.1)` — too low opacity, barely visible
- Change to `rgba(74, 158, 255, 0.25)` for the focus ring alpha
- Placeholder is `opacity: 0.6` on `var(--text-secondary)` — effectively near-invisible
- Change placeholder to `color: rgba(var(--text-secondary-rgb), 0.5)` or a fixed mid-gray

### 3. Dashboard/KPI Pattern (Verdict Dashboard)

**Reference products:** Vercel (deployment statistics), Stripe (payment summary), Linear (issue metrics)

**What these products do:**
- 4 stat cards in a horizontal row, each with equal width
- Card structure: top-border in category color (4px), large number in monospace (`2rem`/`700`), label in small-caps (`0.7rem`/`500`/`letter-spacing: 0.08em`)
- Background: the card gets `rgba(category-color, 0.05)` tint when active (filter applied)
- Hover: `rgba(category-color, 0.08)` tint + border color brightens
- The number is the visual anchor — everything else is secondary
- Interactive: clicking a stat card applies a filter (already how current verdict-dashboard works)

**Example markup structure (pseudocode):**
```html
<div class="verdict-stat-card verdict-stat-card--malicious" data-verdict="malicious" tabindex="0">
    <span class="verdict-stat-count" data-verdict-count="malicious">0</span>
    <span class="verdict-stat-label">Malicious</span>
</div>
```

**What SentinelX currently does vs. what to change:**
- Current: inline pills (`.verdict-dashboard-badge`) — all same height as filter buttons
- Change: give verdict stats their own visual level, separate from filter controls
- Current: counts at `0.8rem font-size` in inline pill — hard to scan across multiple cards
- Change: counts to `1.75rem` monospace, labels to `0.7rem` small-caps beneath

### 4. Filter/Search Pattern

**Reference products:** Linear (priority/status filters), Vercel (deployment filter), GitHub (PR filters)

**What these products do:**
- Filter chips are segmented into groups with a subtle separator (`1px border` or `|` glyph) between groups
- Active chip: background tint (not inversion) + colored border + colored text — same approach as verdict badges
- "All" chip: always first, neutral styling (border-only, no tint), gets border highlight when active
- Search input: lives in the same visual row as filter chips, separated by a `margin-left: auto` push
- Search icon: SVG magnifying glass, `14x14px`, positioned with absolute/padding technique
- Typing in search: filter chips don't disappear — both filter and search apply simultaneously (AND logic)
- Clear search: `×` button appears inside the input when non-empty (not a separate button)

**What SentinelX currently does vs. what to change:**
- Current: verdict buttons in row 1, type pills in row 2, search in row 3 — 3 separate rows
- Consider: collapse to 2 rows — verdict+type on row 1, search on row 2. Or even 1 row on desktop.
- Missing: search icon prefix
- Missing: clear (×) button when search has content

### 5. Status/Verdict Indicator Pattern

**Reference products:** Stripe (payment status badges), Linear (issue priority indicators), VMRay (threat verdict system)

**What these products do:**
- 4 verdict states (Malicious, Suspicious, Clean, No Data/Record) use a consistent visual system:
  - Malicious: `rgba(239, 68, 68, 0.15)` bg + `rgba(239, 68, 68, 0.4)` border + `rgb(239, 68, 68)` text
  - Suspicious: `rgba(245, 158, 11, 0.15)` bg + `rgba(245, 158, 11, 0.4)` border + `rgb(245, 158, 11)` text
  - Clean: `rgba(34, 197, 94, 0.15)` bg + `rgba(34, 197, 94, 0.4)` border + `rgb(34, 197, 94)` text
  - No Data: `rgba(148, 163, 184, 0.1)` bg + `rgba(148, 163, 184, 0.25)` border + `rgb(148, 163, 184)` text
- All are the same visual structure: the only difference is the hue — no filled/inverted variants mixed in
- Colored dot (`6px circle`) precedes the text label — provides a second non-color signal (size)
- Font: monospace, all-caps, tight letter-spacing
- No icons beyond the dot — icons add complexity without analyst value

**Critical fix for SentinelX:**
- `verdict-label--suspicious` uses solid `#f59e0b` background with black text — this is an outlier that breaks the system
- Fix: `background-color: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.4)` — matches the other 3 states

### 6. Loading States and Micro-interactions

**Reference products:** GitHub (PR checks), Linear (issue loading), Vercel (deployment progress)

**What these products do:**
- Skeleton screens: 2-3 gray rounded rectangles that mirror the shape of the eventual content
  - Short rectangle (badge-height, 60% width) = where the verdict badge will appear
  - Full-width rectangle (body-height, 100% width) = where the detail row will appear
  - Both have an animated shimmer: `background: linear-gradient(90deg, #1c2128, #21262d, #1c2128)` shifted via `background-position` animation
- Duration: shimmer cycle = 1.5s, linear, infinite
- Completion: no fanfare — content simply replaces skeleton via DOM swap (no crossfade needed)
- Progress bars: linear, thin (4-6px), rounded ends, gradient fill
  - Active: accent gradient (blue→cyan for loading)
  - Complete: success gradient (green→emerald), brief brightness pulse `@keyframes`, then stable
- Micro-interaction timing budget (from Linear's design team): 100-200ms for state changes, 300ms max for entrance/exit, never above 500ms
- All animations must respect `prefers-reduced-motion: reduce` — disable or use `opacity`-only fallback

**What SentinelX currently does vs. what to change:**
- Current: spinner (`enrichment-spinner`) + italic text — functional but not premium
- Change: swap for skeleton rectangles with shimmer (CSS-only, no library)
- Current: progress bar completion changes gradient color (already good) — add brief pulse
- Add: `@media (prefers-reduced-motion: no-preference)` wrapper around all animation CSS

### 7. Typography Hierarchy

**Reference products:** Linear (issue titles), Vercel (dashboard labels), Stripe (settings pages)

**What these products do:**
- 5-level type system: Display (rare) / Heading / Subheading / Body / Caption
- Inter or system-ui at all sizes — no decorative fonts in the tool UI itself
- Headings: `600` weight minimum, `letter-spacing: -0.02em` for tight feel on large text
- Body: `400` weight, `1.5` line-height for readability
- Captions/labels: `500` weight (slightly heavier than body), `0.7-0.75rem`, often uppercase with `letter-spacing: 0.06em`
- Data values (IOC strings, counts, hashes): always monospace — never system-ui for values
- Color: primary text `#e6edf3` (high contrast), secondary `#8b949e` (metadata), caution to use tertiary

**Recommended scale for SentinelX:**
- `--text-display`: `1.75rem / 700 / letter-spacing: -0.03em` — page titles (rarely used)
- `--text-heading`: `1.25rem / 600 / letter-spacing: -0.02em` — section headers, input-title
- `--text-subheading`: `1rem / 600 / letter-spacing: -0.01em` — card section headers
- `--text-body`: `0.875rem / 400 / line-height: 1.5` — body text, descriptions
- `--text-caption`: `0.75rem / 500 / letter-spacing: 0.05em / uppercase` — labels, badges
- `--text-mono`: `0.8125rem / 400 / font-family: var(--font-mono)` — IOC values, hashes

### 8. Empty States

**Reference products:** Linear ("No issues found"), GitHub ("No pull requests"), Vercel ("No deployments")

**What these products do:**
- Simple SVG icon: 32-40px, `var(--text-secondary)` color, stroke-based (not filled)
- Headline: 1 line, `1rem / 600`, `var(--text-primary)` — describes what's empty, not an error
  - "No IOCs detected" not "Error: empty input"
- Body: 1-2 sentences, `0.875rem / 400`, `var(--text-secondary)` — explains what to do next
- Optional CTA: small secondary button, linked back to input
- Layout: centered in a card, `padding: 3rem 2rem`, vertical stack with `gap: 1rem`
- No illustrations — they're for onboarding, not error states. Simple icons only for a tool.

**For SentinelX specifically:**
- Icon: shield with magnifying glass, or simple magnifying glass — communicates "search" not "error"
- Headline: "No IOCs detected"
- Body: "No indicators were found in the pasted text. Supported types: IPv4, IPv6, domain, URL, MD5, SHA1, SHA256, CVE."
- CTA: "← Paste again" linked to input page (already exists as `.back-link`)

### 9. Settings Page Pattern

**Reference products:** Vercel (project settings), Linear (workspace settings), Stripe (API settings)

**What these products do:**
- Page structure: `max-width: 640px`, single column, vertically stacked section cards
- Each section card: `border: 1px solid var(--border)`, `border-radius: 8px`, `overflow: hidden`
- Section card header row: `padding: 1rem 1.5rem`, `background: var(--bg-secondary)`, flex row with:
  - Left: section name (`0.9375rem / 600`) + optional description (`0.8125rem / 400 / var(--text-secondary)`)
  - Right: action button (visible, not hidden in a menu)
- Section divider: `1px solid var(--border)` between header and body
- Section card body: `padding: 1.25rem 1.5rem`, form fields in single column
- Danger zone (if applicable): final card with `border-color: rgba(var(--verdict-malicious-rgb), 0.4)` — red-tinted
- Flash messages: appear above the card stack, auto-dismiss after 4s with `opacity` transition

**For SentinelX settings page:**
- The VT API key section becomes a single card with header row: "VirusTotal API Key" / "Save" button right-aligned
- Below divider: info text + password input + show/hide toggle
- No sidebar, no tabs — single column is correct for 1 setting

---

## Competitor Visual Analysis

| Component | GitHub Dark | Linear | Vercel Dashboard | SentinelX Current | SentinelX v1.2 Target |
|-----------|------------|--------|-----------------|-------------------|----------------------|
| Card surface | `#161b22` on `#0d1117` | `#1e2024` on `#141518` | `#0a0a0a` on `#111111` | `#161b22` on `#0d1117` | Same + card-header strip |
| Card border | `#30363d` solid | `rgba(255,255,255,0.08)` | `rgba(255,255,255,0.1)` | `#30363d` solid | Switch to rgba white |
| Card hover | Border brightens | TranslateY(-1px) + shadow | Border brightens + shadow | No hover state | TranslateY(-1px) + shadow |
| Verdict badges | Filled for states | Tinted bg + colored text | Tinted bg + colored text | 4/5 states tinted, suspicious solid | All 5 states tinted |
| Filter chips | Active = filled bg | Active = tinted bg + colored border | Active = white bg (light mode) | Active = `var(--bg-tertiary)` + white text | Colored-border active state |
| Search input | Icon prefix | Icon prefix | Icon prefix | No icon | Icon prefix |
| Loading | Skeleton shimmer | Skeleton shimmer | Skeleton shimmer | Spinner + text | Skeleton shimmer |
| Progress bar | N/A | Thin gradient | Thin gradient | 6px gradient (good) | Add completion pulse |
| Empty state | Icon + headline + body | Icon + headline | Icon + headline + CTA | 2 gray text lines | Icon + headline + body |
| Settings | Card per section | Card per section | Card per section | Bare h2 + form | Card per section |

---

## Sources

- [Linear UI Redesign Post](https://linear.app/now/how-we-redesigned-the-linear-ui) — MEDIUM confidence (official Linear blog, design decisions documented)
- [Linear Design Style Reference](https://linear.style/) — HIGH confidence (official Linear design system reference site)
- [shadcn/ui Dark Mode Tokens](https://ui.shadcn.com/docs/theming) — HIGH confidence (official shadcn/ui docs, OKLCH values verified)
- [LogRocket: Linear Design Aesthetic](https://blog.logrocket.com/ux-design/linear-design/) — MEDIUM confidence (analysis article, patterns extrapolated from product)
- [Stripe Accessible Color System](https://stripe.com/blog/accessible-color-systems) — HIGH confidence (official Stripe engineering blog, badge design decisions)
- [Aufait UX: Cybersecurity Dashboard Patterns](https://www.aufaitux.com/blog/cybersecurity-dashboard-ui-ux-design/) — MEDIUM confidence (practitioner analysis)
- [VMRay Verdict System](https://www.vmray.com/explained-the-vmray-threat-identifier-vti-scoring-system/) — HIGH confidence (official VMRay docs — confirms 4-state Malicious/Suspicious/Clean/No Data system)
- [Tailwind CSS Hover/Focus States](https://tailwindcss.com/docs/hover-focus-and-other-states) — HIGH confidence (official Tailwind docs)
- [Carbon Design System: Loading Pattern](https://carbondesignsystem.com/patterns/loading-pattern/) — HIGH confidence (IBM design system, skeleton screen specification)
- [Eleken: Filter UI Patterns for SaaS](https://www.eleken.co/blog-posts/filter-ux-and-ui-for-saas) — MEDIUM confidence (UX consultancy analysis, patterns observed across products)
- Existing SentinelX CSS (`app/static/src/input.css`) — HIGH confidence (source of truth for current implementation)

---

*Feature research for: SentinelX v1.2 UI pattern redesign (dark-first premium SaaS)*
*Researched: 2026-02-25*
*Confidence: HIGH (pattern analysis and implementation specifics), MEDIUM (competitor implementation details without source inspection)*
