# Stack Research

**Domain:** Results page redesign — multi-source aggregation UI, CSS layout, animation
**Milestone:** v1.1 Results Page Redesign
**Researched:** 2026-03-16
**Confidence:** HIGH (existing stack verified from codebase; CSS feature support verified against
official MDN/caniuse; Tailwind v4 standalone verified from GitHub Discussions)

---

## Context: Presentation Refinement Only

The existing stack is locked and ships. This document answers one question: **what, if anything,
does the v1.1 results page redesign require beyond what already exists?**

**Existing baseline (do not re-evaluate):**

| Tool | Version | How Used |
|------|---------|----------|
| TypeScript | 5.8 | 13 modules, strict mode, IIFE output via esbuild |
| esbuild | 0.27.3 | Standalone binary, `--target=es2022`, bundles to `dist/main.js` |
| Tailwind CSS | v3.4.17 | Standalone binary (no Node.js), utility classes in templates |
| Custom CSS | input.css (58KB) | Design tokens, keyframes, component classes |
| Jinja2 | Flask 3.1 | Server-side templates, partials, macros |

The CSS design system already has: `--ease-out-expo`, `--ease-out-quart`, `--duration-fast/normal/slow`,
`fadeSlideUp`, `fadeIn`, `slideInFade`, `slideOutFade` keyframes, shimmer-line loading skeleton,
`--card-index` stagger via CSS custom property, verdict color triples, zinc hierarchy tokens.

---

## Verdict: Current Stack Is Sufficient — No New Libraries Required

The redesign can achieve everything it needs through:
1. CSS features already available in the current `input.css` pipeline (Tailwind + custom)
2. ES2022 vanilla TypeScript (already compiled by esbuild)
3. Native browser APIs that ship in all modern browsers

No npm packages, no new standalone binaries, no new Python dependencies.

---

## Recommended Stack

### Core Technologies (unchanged)

| Technology | Version | Purpose | Why Sufficient |
|------------|---------|---------|---------------|
| TypeScript | 5.8 | DOM manipulation, enrichment polling, card reordering | Already handles all dynamic behavior; 13 modules prove the architecture scales |
| esbuild | 0.27.3 | Compiles TS to single IIFE bundle | `--target=es2022` enables all native APIs needed (View Transitions, CSS custom properties) |
| Tailwind CSS | v3.4.17 standalone | Utility classes for layout adjustments | Generates only used classes; CSS Grid/Flexbox utilities are comprehensive |
| Custom CSS (input.css) | — | Design tokens, component classes, keyframes | Already has motion primitives; redesign extends existing keyframes, not replaces them |

### CSS Capabilities to Leverage (Already Available, No New Setup)

These are native CSS features available in the current browser target (Chrome/Edge/Firefox/Safari modern).
They require zero new tools — just new CSS rules in `input.css`.

| Technique | Availability | Purpose in Redesign | Confidence |
|-----------|-------------|---------------------|------------|
| CSS Grid subgrid | Baseline (97%+ support) | Align card sections (header, enrichment zone, footer) across the card grid without JavaScript — headers stay level, stat rows align across cards | HIGH — Chrome 117+, Firefox 71+, Safari 16+ |
| CSS `@container` queries | Baseline (95%+ support) | Cards adapt their internal layout based on their allocated width, not viewport — handles wide vs narrow grid slots without media query hacks | HIGH — Chrome 106+, Firefox 110+, Safari 16+ |
| `view-transition-name` + `document.startViewTransition()` | Baseline Newly Available Oct 2025 | Animate card reordering (sort by severity) so cards glide to their new positions instead of teleporting — same-document transitions work in Chrome 111+, Firefox 133+, Safari 18+ | HIGH for same-document transitions |
| CSS `animation-timeline: view()` (scroll-driven) | ~83% global support, Safari 26+ only | Animate cards entering the viewport — LOW PRIORITY, only suitable as progressive enhancement because Firefox does not support it as of March 2026 | MEDIUM — skip for MVP, add with `@supports` guard later |
| `@starting-style` (entry animation) | Chrome 117+, Firefox 129+, Safari 17.5+ | Animate new detail rows appearing — triggers animation only on element insertion, not every render | HIGH — better than existing JS-managed `fadeSlideUp` for dynamically added rows |
| CSS `color-mix()` | Baseline (95%+ support) | Derive hover/focus states from verdict color tokens without hardcoding more hex values | HIGH |
| CSS `transition: grid-template-rows` | Modern browsers | Animate the expand/collapse of `.enrichment-details` with `grid-template-rows: 0fr` → `1fr` trick — smoother than `max-height` hacks | HIGH — known pattern, works in all modern browsers |

### View Transitions for Card Sort Animation

The existing `doSortCards()` in `cards.ts` re-appends DOM nodes synchronously — cards teleport to
new positions. Wrapping this in `document.startViewTransition()` with `view-transition-name`
CSS properties on each card produces animated FLIP-style movement:

```typescript
// In cards.ts — replace doSortCards() body with:
if ('startViewTransition' in document) {
  document.startViewTransition(() => doSortCards());
} else {
  doSortCards(); // graceful fallback — existing behavior
}
```

This requires assigning `view-transition-name` values. The `--card-index` CSS custom property
pattern already in `ui.ts` provides a template: assign names dynamically from TypeScript using
`card.style.setProperty('view-transition-name', 'ioc-card-' + CSS.escape(iocValue))`.

No new library. Zero bundle size impact. Graceful degradation is built-in — browsers without
support just execute the DOM change without animation.

**Browser support:** Chrome 111+, Edge 111+, Firefox 133+ (Baseline Oct 2025), Safari 18+.
HIGH confidence this is safe for production use.

### `@starting-style` for Provider Row Entry Animation

The current `enrichment.ts` appends provider detail rows with `detailsContainer.appendChild(row)`.
These rows appear instantly. Adding an entry animation requires either a JavaScript class-toggle
trick or `@starting-style`, which specifies the initial painted state when an element is first
inserted:

```css
.provider-detail-row {
  transition: opacity 200ms var(--ease-out-quart), transform 200ms var(--ease-out-quart);
  opacity: 1;
  transform: translateY(0);
}

@starting-style {
  .provider-detail-row {
    opacity: 0;
    transform: translateY(4px);
  }
}
```

No TypeScript changes required. The CSS handles it automatically on element insertion.
Browser support: Chrome 117+, Firefox 129+, Safari 17.5+ — effectively all modern browsers.

### Grid Layout for Multi-Source Presentation

The current `.ioc-cards-grid` uses CSS Grid (from the existing `ioc-cards-grid` class in `input.css`).
For the redesign, the key layout technique is **subgrid** inside each card:

```css
.ioc-card {
  display: grid;
  grid-template-rows: auto auto 1fr; /* header / original / enrichment */
}

/* When cards are in a grid row: subgrid aligns sections across columns */
.ioc-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
}
```

Subgrid lets the enrichment slot expand uniformly within a row — the "meta-search engine" feel
where all cards in a row feel like a coherent table rather than independent boxes.

### Supporting Browser APIs (Already Available at es2022 Target)

| API | Purpose | Notes |
|-----|---------|-------|
| `Intersection Observer` | Lazy-reveal card stagger animations as analyst scrolls | Already in all modern browsers; use instead of scroll-driven CSS animations (better Firefox support) |
| `CSS.escape()` | Safe dynamic CSS selector construction | Already used in `cards.ts` — continue the pattern |
| `document.startViewTransition()` | Card sort animation | Wrap existing `doSortCards()` call |
| `ResizeObserver` | Detect card width changes for container query fallback | Available in all modern browsers if polyfill needed |

---

## Tailwind CSS v4 Consideration

**Verdict: stay on Tailwind v3.4.17 for this milestone.**

Tailwind v4 is available as a standalone binary (confirmed at v4.1.3 from GitHub releases).
The v4 config model shifts from `tailwind.config.js` to `@theme {}` in CSS — a meaningful
migration requiring changes to `input.css` and removal of `tailwind.config.js`.

**Why not v4 for v1.1:**

1. The v3 → v4 migration is a separate task with its own regression surface — utility class
   names changed in some cases; existing `input.css` uses `@tailwind base/components/utilities`
   directives that v4 replaces with `@import "tailwindcss"`.
2. The CSS features needed for the redesign (`container queries`, `subgrid`, `@starting-style`,
   View Transitions) are all native browser features — they do not require Tailwind v4.
3. v4 does add useful utilities (native container query variants `@sm:`, `@lg:`, `@container`
   shorthand) but the project already has full `@container` support through custom CSS.

**Upgrade path:** Tailwind v4 is a natural follow-on for a cleanup milestone after v1.1 ships.
The redesigned CSS will be easier to migrate than the current accumulation of v3 workarounds.

---

## What NOT to Add

| Avoid | Why | What to Use Instead |
|-------|-----|---------------------|
| Chart.js / D3.js / any data viz library | The "data visualization" need for a results page is narrow: conviction bars, engine counts. CSS-only progress bars (width: percentage; background: verdict color) cover 100% of the use case. A 100KB chart library is disproportionate. | CSS `width` percentages + custom properties |
| Framer Motion / GSAP / Anime.js | Animation library for vanilla TS makes no sense. These target React/component frameworks. GSAP is 60KB+. | CSS `@starting-style`, View Transitions API, `transition` property |
| Motion One (JS animation library) | Lower overhead than GSAP but still adds bundle size for capabilities CSS now handles natively. | Native CSS transitions and `@starting-style` |
| Alpine.js / Htmx | Reactive micro-frameworks would require restructuring the existing 13-module TypeScript pattern. High migration cost, no gain for a refinement milestone. | Existing vanilla TS modules |
| Intersection Observer polyfill | Not needed — all modern browsers support it natively. The app is desktop-only, analyst workstations run current browsers. | Native Intersection Observer |
| CSS scroll-driven animations (`animation-timeline: view()`) as primary mechanism | Firefox does not support this as of March 2026 (available only under a flag). Safari only in v26 (beta as of research date). 82% support is not sufficient for a production feature that analysts depend on. | Intersection Observer API in TypeScript — 98%+ support, identical visual result |
| `view-transition-class` (new 2025 feature) | Chrome 139+ only as of March 2026. Too new for production use. | Plain `view-transition-name` per element |
| React / Vue / Svelte | Out of scope per PROJECT.md. The vanilla TS architecture handles this complexity. | Vanilla TypeScript |

---

## Animation Strategy Summary

The redesign has three distinct animation contexts:

| Context | Technique | Rationale |
|---------|-----------|-----------|
| Card entry (page load) | Existing `--card-index` stagger + `fadeSlideUp` keyframe | Already works. Keep as-is. |
| Provider row entry (enrichment arrives) | `@starting-style` CSS rule on `.provider-detail-row` | Zero JS change. Browser animates on element insertion automatically. |
| Card reorder (sort by severity) | `document.startViewTransition()` wrapping `doSortCards()` | 3 lines of TypeScript. FLIP-style animation. Graceful degradation built-in. |
| Shimmer loading skeleton | Already implemented (`shimmer-line` classes) | Keep. Appears before first provider result arrives. |
| Expand/collapse enrichment details | `grid-template-rows: 0fr / 1fr` transition | Replace existing `max-height` approach if used; grid-rows is smoother and avoids flash. |

---

## Build Tool Versions to Keep

| Tool | Current | Upgrade? | Reason |
|------|---------|---------|--------|
| esbuild | 0.27.3 | No | Current, stable. `--target=es2022` already enables View Transitions API. |
| Tailwind CSS standalone | v3.4.17 | No (this milestone) | v4 migration is separate work. |
| tsc | (project version) | No | TypeScript 5.8 supports all needed syntax. |

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Native `document.startViewTransition()` | GSAP FLIP plugin | Only if GSAP is already in the project and you need IE/older browser support |
| `@starting-style` CSS | JS class-toggle + `requestAnimationFrame` trick | Only in projects that still support Firefox 128 or Safari 17.4 |
| CSS Grid subgrid | JavaScript layout synchronization | Only if subgrid is genuinely unavailable (pre-2023 browsers) — not applicable to analyst workstations |
| Intersection Observer for lazy stagger | `animation-timeline: view()` | Use the CSS approach once Firefox ships it without a flag (tentative: Firefox 136+, currently flag-only) |

---

## Version Compatibility

| Feature | Chrome | Firefox | Safari | Notes |
|---------|--------|---------|--------|-------|
| CSS Grid subgrid | 117+ | 71+ | 16+ | Safe — all modern browsers |
| CSS Container queries | 106+ | 110+ | 16+ | Safe — all modern browsers |
| `@starting-style` | 117+ | 129+ | 17.5+ | Safe — all modern browsers |
| `document.startViewTransition()` | 111+ | 133+ | 18+ | Safe — Baseline Oct 2025 |
| `animation-timeline: view()` | 115+ | flag only | 26+ | NOT safe for MVP — use IntersectionObserver instead |
| `color-mix()` | 111+ | 113+ | 16.2+ | Safe |
| `CSS.escape()` | 46+ | 31+ | 8+ | Already used in codebase |

---

## Sources

- [Tailwind CSS v4 standalone CLI — GitHub Discussion #17638](https://github.com/tailwindlabs/tailwindcss/discussions/17638)
  v4.1.3 standalone binary confirmed. v3→v4 migration model documented. MEDIUM confidence on migration scope.
- [Tailwind CSS v4.0 release post](https://tailwindcss.com/blog/tailwindcss-v4)
  v4 CSS feature set confirmed (`@theme`, `@container` native utilities, `starting:` variant). HIGH confidence.
- [What's new in view transitions (2025 update) — Chrome Developers](https://developer.chrome.com/blog/view-transitions-in-2025)
  Same-document view transitions browser support, `match-element` auto-naming, scoped transitions. HIGH confidence.
- [View Transition API — MDN](https://developer.mozilla.org/en-US/docs/Web/API/View_Transition_API)
  API shape, `document.startViewTransition()` method signature. HIGH confidence.
- [animation-timeline: view() — Can I use](https://caniuse.com/mdn-css_properties_animation-timeline_view)
  82.81% global support. Safari iOS 26+ only. Firefox flag-only as of research date. HIGH confidence on support numbers.
- [CSS scroll-driven animations — MDN](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Scroll-driven_animations)
  `animation-timeline: view()` syntax and `@supports` feature detection pattern. HIGH confidence.
- [The New CSS Layout Toolbox: subgrid, container queries — Medium Oct 2025](https://medium.com/@kedarbpatil07/the-new-css-layout-toolbox-subgrid-container-queries-and-more-41cf94ebf821)
  Subgrid 97%+ global support confirmed. MEDIUM confidence (secondary source).
- [Rearrange / Animate CSS Grid Layouts with the View Transition API — Bram.us](https://www.bram.us/2023/05/09/rearrange-animate-css-grid-layouts-with-the-view-transition-api/)
  Grid reorder + View Transitions API pattern. HIGH confidence — direct implementation reference.
- SentinelX codebase: `app/static/src/input.css`, `Makefile`, `app/static/src/ts/modules/cards.ts`,
  `app/static/src/ts/modules/ui.ts`, `app/static/src/ts/modules/enrichment.ts`
  Existing motion tokens, keyframes, stagger implementation, doSortCards() function. HIGH confidence.

---

*Stack research for: SentinelX v1.1 Results Page Redesign*
*Researched: 2026-03-16*
