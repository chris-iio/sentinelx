# Project Research Summary

**Project:** SentinelX v1.2 — Modern Dark UI Redesign
**Domain:** Dark-first premium SaaS UI for a Flask/Jinja2 security triage tool
**Researched:** 2026-02-25
**Confidence:** HIGH

## Executive Summary

SentinelX v1.2 is a frontend-only visual elevation of an existing, fully functional IOC triage tool. The backend (Python + Flask), core frontend stack (Tailwind CSS standalone CLI v3.4.x, Alpine.js CSP build, vanilla JS), and CSS custom property design token system are all locked in and working. The redesign does not add features — it closes the gap between "functional dark prototype" and "premium security product" by applying the same design patterns used by Linear, Vercel, GreyNoise, and Snyk. The recommended approach is a layered migration: establish a validated design token system first, then elevate components in dependency order (shared primitives before page-specific components), while keeping all CSS class names and data attributes stable so existing Playwright E2E tests never break.

The target aesthetic is Linear-meets-GreyNoise: a zinc-based near-monochromatic dark foundation (`#09090b` page background, `#18181b` card surface), emerald/teal as the security-domain accent color, crisp Inter Variable typography at precise weights, and verdict badges that use the security industry's universal four-color system (red/amber/emerald/zinc). The highest-impact changes are: (1) replace the current solid amber suspicious badge with the tinted-background/colored-border pattern used by all four verdict states, (2) add card hover elevation via `translateY(-1px)` plus border-color shift, and (3) add a sticky filter bar backdrop-blur. These three changes alone produce a measurably premium result at near-zero implementation cost.

The key risks are accessibility failures that are invisible during development: contrast ratios that pass on a calibrated monitor but fail WCAG AA on secondary surfaces, focus rings made "subtle" to the point of invisibility, and browser autofill overrides that paint yellow into dark inputs on the settings page. All are preventable — but only if contrast verification happens at token-definition time, not after components are built. The migration order (tokens first, components second) directly mitigates this risk.

---

## Key Findings

### Recommended Stack

The existing stack requires only additive changes — no library replacements. The Tailwind standalone CLI (v3.4.19) continues to handle everything via `make css`. Two new self-hosted variable font files (~130KB total) replace the current system font stack: Inter Variable for all UI chrome and JetBrains Mono Variable for all IOC data values. Heroicons v2 inline SVGs handle the 10–15 icons needed with zero npm/CDN dependency. `darkMode: 'selector'` is added to `tailwind.config.js` for future light-mode flexibility, and `@tailwindcss/forms` (bundled in the standalone CLI) is activated for the redesigned textarea and settings inputs. No new Python dependencies. No new npm packages.

Self-hosting is non-negotiable. SentinelX runs on analyst workstations and jump boxes that may have no internet access. The existing CSP (`default-src 'self'`) blocks external font CDNs entirely. All font files go in `app/static/fonts/` with `crossorigin` preload links in `base.html`.

**Core technologies (additions only):**
- Inter Variable (woff2, ~70KB, self-hosted): UI typeface — used by Linear, GitHub, Vercel; one variable file covers all weights 100–900
- JetBrains Mono Variable (woff2, ~60KB, self-hosted): Monospace for IOC values — purpose-built for developer tools, superior legibility over Fira Code at small sizes
- Heroicons v2.2.0 (inline SVG, zero files to install): UI icons — MIT license, `currentColor` inherits text color, zero CSP implications
- `@tailwindcss/forms` (bundled in standalone CLI): CSS reset for textarea/inputs — activated via `require('@tailwindcss/forms')` in config
- `darkMode: 'selector'` config addition: future-proofs for light mode without CSS architecture change

### Expected Features

The redesign divides into two priority tiers based on impact-to-effort ratio. P1 (all CSS-only or near-CSS) delivers the premium feel immediately. P2 (requires HTML structure changes) completes the visual system. Nothing in scope requires new backend functionality.

**Must have — P1 (table stakes, high impact, CSS-only):**
- Verdict badge visual fix — standardize all five verdict states to tinted-background + colored-border + colored-text; eliminate the outlier solid amber/black suspicious badge
- Card hover elevation — `translateY(-1px)` + `box-shadow` + border-color shift on `.ioc-card:hover` at 150ms ease
- Focus ring standardization — `outline: 2px solid var(--accent)` with 2px offset on all interactive elements; replace all low-opacity `box-shadow`-only focus indicators
- Typography weight differentiation — 3-tier scale with Inter Variable at precise weights (-0.02em tracking on headings, 500 weight on captions)
- Sticky filter bar backdrop-blur — `backdrop-filter: blur(12px)` with `zinc-950/95` semi-transparent background
- Empty state with icon and message — shield/search SVG + "No IOCs detected" headline + body copy with supported types
- Search input icon prefix — inline SVG magnifying glass with `padding-left` offset
- Paste feedback animation — `@keyframes` appear/fade on `.paste-feedback`
- IOC type badge dot indicator — `::before` 6px colored circle on each `.ioc-type-badge--{type}`

**Should have — P2 (requires HTML/JS refactor, significant improvement):**
- Verdict stat cards — replace inline dashboard pills with 4 KPI-style cards (large monospace number, colored top border, small-caps label)
- Shimmer skeleton loader — replace spinner with 2–3 animated skeleton rectangles per card during enrichment-pending state
- Settings section card pattern — wrap each settings section in a bordered card with header row (section name left, action button right)
- Progress bar completion animation — brief brightness pulse when enrichment finishes at 100%
- Mode-aware submit button — emerald variant for Online mode, blue-tinted variant for Offline

**Defer to v1.3 or later:**
- Custom scrollbar styling (low cross-browser ROI)
- Search result text highlighting (HIGH complexity, DOM text manipulation)
- Contextual copy-button tooltip (complexity vs. value unclear)

**Anti-features (explicitly excluded):**
- Glassmorphism on content cards (GPU jank at 50+ cards during scroll — use only on sticky filter bar)
- Sidebar navigation (consumes 220px needed for IOC hash display)
- Dark/light mode toggle (doubles CSS maintenance burden, not a real SOC use case)
- Inline charts/sparklines (single-shot tool, no history to chart)

### Architecture Approach

The design system architecture is a two-layer token pattern: CSS custom properties at `:root` define semantic color values (the single source of truth), and `tailwind.config.js` extends `theme.colors` to map token names to Tailwind utility classes for use in templates. Component styles live in `@layer components` using BEM-style class names and `@apply` or direct `var()` references — NOT utility-first class strings in Jinja2 templates. This is the correct pattern for a Jinja2 app where the same card markup appears 50+ times in a loop; utility-first in templates would create massive diffs for every style change and break existing Playwright E2E selectors.

The migration follows a strict dependency order: font infrastructure first, then color token redesign, then base component style elevation, then template partial extraction, then header/footer, then input page, results page, and settings page, finishing with safelist validation. Template partial extraction (creating `_ioc_card.html`, `_verdict_dashboard.html`, `_filter_bar.html`, `_enrichment_slot.html`) is a structural prerequisite for the results page redesign — E2E tests must pass after extraction before any component work begins.

**Major components and responsibilities:**
1. Design token layer (`input.css` `:root`) — single source of truth for all color, spacing, typography; zinc-950/900/800/700 surface hierarchy, emerald/teal accent system, 4-state verdict color triples (text/bg/border per verdict)
2. Component class layer (`@layer components` in `input.css`) — BEM semantic classes (`.ioc-card`, `.verdict-label--malicious`, `.filter-btn`) referencing tokens; no hardcoded hex values
3. Template layer (`base.html` + page templates + `partials/`) — structural HTML with single semantic class names per element; Jinja2 `{% include %}` for extracted partials
4. Build layer (Tailwind standalone CLI via `make css`) — unchanged pipeline; regenerates `dist/style.css` from `input.css` + `tailwind.config.js`

**Concrete target design tokens (from DESIGN-INSPIRATION.md — verified Tailwind v3 hex values):**
```
Surface: #09090b (zinc-950, base) / #18181b (zinc-900, card) / #27272a (zinc-800, inputs) / #3f3f46 (zinc-700, hover)
Borders: rgba(255,255,255,0.06/0.10/0.18) for subtle/default/emphasis
Text: #f4f4f5 (zinc-100, headings) / #d4d4d8 (zinc-300, body) / #a1a1aa (zinc-400, labels) / #71717a (zinc-500, muted)
Accent: #10b981 (emerald-500) / #34d399 (emerald-400, hover) / #022c22 (emerald-950, subtle bg)
Interactive: #14b8a6 (teal-500) for focus rings and secondary interactive elements
Malicious: #f87171 text / #450a0a bg / #ef4444 border
Suspicious: #fbbf24 text / #451a03 bg / #f59e0b border
Clean:      #34d399 text / #022c22 bg / #10b981 border
No Record:  #a1a1aa text / #27272a bg / #3f3f46 border
```

### Critical Pitfalls

The pitfalls research is unusually actionable — it includes specific contrast measurements for the existing codebase, not generic advice.

1. **Contrast assumed, not verified** — The existing `--text-secondary: #8b949e` on `--bg-secondary: #161b22` card surfaces fails WCAG AA (approximately 3.2:1). Upgrade secondary text to zinc-400 (`#a1a1aa`) which achieves ~7:1 on the new zinc-950 base. Run contrast audit on every token pair before implementing any component. This is a Phase 1 gate criterion, not a Phase 4 polish step.

2. **Verdict color recalibration needed** — The suspicious badge (`background: #f59e0b; color: #000`) is an outlier that breaks the visual system and looks harsh on dark backgrounds. All five verdict states must adopt the tinted-background pattern: `rgba(color, 0.15)` bg + colored border + colored text. Re-test all verdict badge contrast ratios against the new zinc-900 card surface after palette change.

3. **Focus ring invisibility** — Current focus rings use 10–25% opacity blue box-shadows that fail WCAG 1.4.11 (3:1 non-text contrast). Replace with `outline: 2px solid var(--accent); outline-offset: 2px` on `:focus-visible`. This is an accessibility requirement, a quality signal, and a code review gate.

4. **Browser autofill overrides dark inputs** — Chrome/Safari apply bright yellow autofill backgrounds that override CSS. The settings page API key field is directly affected. Fix in Phase 1 with `<meta name="color-scheme" content="dark">` + `:root { color-scheme: dark; }` + the `-webkit-autofill` box-shadow override: `box-shadow: 0 0 0 100px var(--surface-2) inset; transition: background-color 5000s`.

5. **Tailwind safelist drift during class rename** — Three risk vectors: (a) utility classes in templates override `@layer components` styles due to layer specificity, (b) partial token renames create split-brain where old and new names coexist, (c) renamed dynamic classes get purged from Tailwind output because the safelist wasn't updated. Mitigation: create a token rename table before any work, grep all templates and `main.js` for affected names, update template + JS + safelist + CSS atomically.

6. **JS color literals bypass the token system** — The existing `main.js` is correct (uses class toggles and data attributes for all color). The risk is new code added during redesign using `element.style.color = "#..."` as a shortcut. Treat as a hard code-review gate across all phases: grep for `style.color` and `style.background` before every commit.

---

## Implications for Roadmap

The architecture research specifies a 9-step migration order with explicit dependencies. This maps to 4 implementation phases, each delivering a testable, shippable increment.

### Phase 1: Foundation (Design Tokens + Base CSS)

**Rationale:** Every subsequent component depends on correct token values. Building components on wrong tokens means double work when contrast failures are caught late. Font infrastructure has zero visual impact and zero risk — it can go first. Color token redesign, autofill fix, scrollbar fix, and `color-scheme` meta tag complete the foundation layer.

**Delivers:** A verified design token system — zinc-based surface hierarchy, emerald/teal accent, four-state verdict color triples — with Inter Variable and JetBrains Mono Variable loading from `app/static/fonts/`. Browser autofill and scrollbar issues resolved. All pages render visually close to current (no structural changes yet), but all color token values reflect the target palette and every text/background pair passes WCAG AA contrast.

**Addresses:** Typography weight differentiation (token level), accessible color contrast (WCAG audit pass), monospace font consistency for IOC values, browser-level dark mode signaling.

**Avoids (from PITFALLS.md):** Contrast failures (Pitfall 1), verdict color saturation issues (Pitfall 2), browser autofill yellow flash (Pitfall 4), invisible box shadows on dark surfaces (Pitfall 5), light scrollbar on Windows (Pitfall 6), pure black background (Pitfall 7), CSS specificity collisions from early token naming (Pitfall 8), font weight anti-aliasing issues (Pitfall 10).

**Gate criterion:** All text/background token pairs verified at 4.5:1+ (normal text) and 3:1+ (UI components) before closing phase.

### Phase 2: Shared Component Elevation

**Rationale:** Header, buttons, badges, and focus rings are used on every page. Elevating them once here means all subsequent page-specific work starts from an elevated baseline. The verdict badge fix (the single most visible design inconsistency) and focus ring standardization both live here as shared primitives.

**Delivers:** Elevated shared primitives — redesigned header/footer, unified verdict badge system (tinted-bg pattern for all five states), standardized focus rings across all interactive elements, button hover/active states, and form element styles from `@tailwindcss/forms`. The Heroicons icon macro (`macros/icons.html`) is created here for shared use in subsequent phases.

**Addresses:** Verdict badge visual fix (P1, highest consistency fix), focus ring standardization (P1, accessibility), smooth hover transitions on all interactive elements (P1), sticky filter bar backdrop-blur (P1).

**Avoids (from PITFALLS.md):** Focus ring invisibility (Pitfall 3), JS color literals in any new code (Pitfall 9 — code review gate active from here forward).

**Stack additions activated:** `@tailwindcss/forms` plugin, `darkMode: 'selector'` config, Heroicons v2 inline SVGs for shared UI icons.

### Phase 3: Results Page Redesign

**Rationale:** The results page is the highest-complexity page and the primary analyst workflow. It must be tackled as a coherent unit after shared primitives are complete. Template partial extraction (architectural prerequisite for maintainability) happens as the first step of this phase — E2E tests must pass after extraction before any component work proceeds.

**Delivers:** Extracted Jinja2 partials (`_ioc_card.html`, `_verdict_dashboard.html`, `_filter_bar.html`, `_enrichment_slot.html`), IOC card hover elevation effect, IOC type badge dot indicators, search input with icon prefix, empty state with icon and message, and either verdict stat KPI cards (P2) or improved inline dashboard (P1 minimum). Shimmer skeleton loader replaces the spinner.

**Addresses:** Card hover elevation (P1), IOC type badge dot indicator (P1), search input icon (P1), empty state (P1), verdict stat cards (P2), shimmer skeleton loader (P2).

**Avoids (from PITFALLS.md):** Utility-first class strings in Jinja2 loops (Architecture Anti-Pattern 1), CSS transitions on all card properties causing scroll jank at 30+ cards (Performance Trap), animations without `prefers-reduced-motion` wrapping (UX Pitfall).

**Phase prerequisite:** Partial extraction must complete and E2E tests must pass before any component-level results page work.

### Phase 4: Input and Settings Page Redesign

**Rationale:** Input and settings pages are simpler and benefit from all shared components built in Phases 2–3. Both are contained changes. Finishing here creates a clean closure.

**Delivers:** A premium input page — Inter Variable typography, refined textarea with teal focus ring, emerald submit button with active state and disabled state, improved mode toggle visual treatment — and a professional settings page with Vercel-style section cards (header row: section name left, action button right), monospace API key input with show/hide toggle, and configured/unconfigured status badges. Paste feedback animation (P1) and mode-aware submit button variant (P2) complete here.

**Addresses:** Paste feedback animation (P1), settings section card pattern (P2), mode-aware submit button (P2), progress bar completion animation (P2).

**Avoids (from PITFALLS.md):** Browser autofill on settings password input (already fixed in Phase 1 — verify here), `<select>` light-theme rendering (fixed in Phase 1 with `color-scheme: dark` — confirm here).

### Phase Ordering Rationale

- Foundation first because wrong tokens mean rework in every subsequent phase; contrast verification is a Phase 1 gate that prevents late-discovered accessibility failures.
- Shared components before pages because every page inherits from the shared component layer; fixing the verdict badge system once in Phase 2 means all three pages receive the fix automatically.
- Results page before input/settings because it is the most complex (750+ line template, multiple partials needed, the most components), and tackling it while context from Phase 2 is fresh reduces context-switching.
- Input/settings last because they are the simplest pages and can be completed quickly as a clean closure.

### Research Flags

No additional research phases needed — this is a visual redesign of an existing codebase with well-documented patterns. All critical decisions are resolved.

**Phases with standard patterns (skip research-phase):**
- **Phase 1:** CSS custom property token systems, self-hosting web fonts, `color-scheme` meta tag — all directly verified against official Tailwind, MDN, and W3C sources at HIGH confidence.
- **Phase 2:** `@tailwindcss/forms`, Heroicons inline SVG, focus ring WCAG compliance — directly documented patterns.
- **Phase 3:** Jinja2 `{% include %}` partial extraction, skeleton shimmer CSS, card hover elevation — established patterns with multiple verified references.
- **Phase 4:** Single-page component work using patterns established in Phases 1–3.

**One implementation gate to track (not a research gap):** The Tailwind safelist in `tailwind.config.js` must be audited whenever any dynamic class name changes during Phase 3. Run `make css` and verify the results page renders after every template change that touches dynamically-applied class names (`ioc-type-badge--{type}`, `verdict-{verdict}` families).

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies verified against official sources. Font file sizes (~70KB Inter, ~60KB JetBrains Mono), plugin compatibility, CSS animation approach, `darkMode: 'selector'` behavior — all confirmed. |
| Features | HIGH | Pattern analysis grounded in official Linear design system, Stripe engineering blog, VMRay docs, and Carbon Design System documentation. Priority tiers (P1/P2/P3) are opinionated but well-reasoned with impact/effort estimates. |
| Architecture | HIGH | Migration order verified against Tailwind v3 official docs. Jinja2 `{% include %}` behavior confirmed. CSP compatibility matrix verified. One naming convention decision to make in Phase 1 (see Gaps below). |
| Pitfalls | HIGH | Specific contrast measurements taken from existing `input.css` values, not estimated. Focus ring WCAG failure confirmed with actual CSS values (10–25% opacity). Autofill override technique sourced from Chrome for Developers docs. |
| Design Inspiration | HIGH | Grounded in verified design system CSS variables (Linear, Vercel Geist), confirmed Tailwind v3 hex values, and direct analysis of security tool UIs (GreyNoise Visualizer, Snyk, CrowdStrike Falcon). |

**Overall confidence: HIGH**

### Gaps to Address

There are no significant research gaps. Two minor implementation decisions to make during Phase 1:

- **Tailwind config naming convention:** Two approaches exist for bridging CSS tokens to Tailwind utilities — the `bg-bg-surface` explicit naming pattern vs. keeping tokens exclusively in `@layer components`. The architecture research recommends the second approach (keep CSS vars in the component layer, only extend Tailwind config for tokens needed directly in Jinja2 HTML). Confirm this choice in Phase 1 and apply consistently.

- **Placeholder contrast threshold:** Design inspiration research identifies zinc-600 (`#52525b`) on zinc-900 as failing WCAG AA at ~2.5:1. Use zinc-500 (`#71717a`) for placeholders — achieves ~4.5:1 on zinc-900, a comfortable margin above the 3:1 UI component minimum.

---

## Sources

### Primary (HIGH confidence)

- Tailwind CSS v3 official docs (v3.tailwindcss.com) — dark mode config, `@apply`, `@layer`, theme extension, standalone CLI plugin bundling
- WCAG 2.1 SC 1.4.3, 1.4.11, 2.4.7; WCAG 2.2 SC 2.4.11 (w3.org) — contrast ratio minimums, focus ring requirements
- MDN — `font-display`, `crossorigin` attribute on preload, `color-scheme` property behavior
- Linear official blog (linear.app/now/how-we-redesigned-the-linear-ui) — Inter typeface choice, spacing system, surface layering
- Linear Design System (linear.style) — typography scale, color token naming, micro-interaction timing
- Vercel Geist CSS variables (vercel.com/geist/colors) — dark mode token naming patterns, status indicator colors
- rsms/inter GitHub releases (github.com/rsms/inter) — Inter Variable font files, SIL OFL license, ~70KB Latin woff2
- JetBrains/JetBrainsMono GitHub releases (github.com/JetBrains/JetBrainsMono) — Mono Variable font, SIL OFL license
- tailwindlabs/heroicons GitHub — v2.2.0 MIT license, inline SVG approach documented
- Carbon Design System (carbondesignsystem.com) — left-border severity card pattern, skeleton loader specification
- Stripe engineering blog — tinted-badge accessible color system (bg/border/text triple)
- Chrome for Developers — scrollbar styling CSS, autofill override technique
- VMRay verdict system docs (vmray.com) — four-state malicious/suspicious/clean/no-data confirmation
- Tailwind v3 color scale (v3.tailwindcss.com/docs/customizing-colors) — zinc/emerald/teal verified hex values

### Secondary (MEDIUM confidence)

- LogRocket: Linear Design Aesthetic — pattern extrapolation from product analysis
- Smashing Magazine 2025: Inclusive Dark Mode — accessible dark theme design principles
- parker.mov: Good Dark Mode Shadows — elevation via surface lightness, not shadow darkening
- Design Shack: Typography in Dark Mode — font weight step-up recommendation for dark themes
- Aufait UX: Cybersecurity Dashboard Patterns — security tool UX conventions
- GreyNoise Visualizer (viz.greynoise.io) — live analysis of premium security tool UI
- shadcn/ui Theming (ui.shadcn.com/docs/theming) — CSS custom property + Tailwind bridge pattern

### Tertiary (LOW confidence)

- None — all key decisions are covered by HIGH or MEDIUM confidence sources.

---

*Research completed: 2026-02-25*
*Ready for roadmap: yes*
