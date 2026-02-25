# Stack Research

**Domain:** Dark-first UI redesign for Flask security tool (SentinelX v1.2)
**Researched:** 2026-02-25
**Confidence:** HIGH (Tailwind dark mode, font delivery), MEDIUM (plugin compatibility with standalone CLI), HIGH (icon delivery approach)

---

## Context: What Already Exists

This is a SUBSEQUENT MILESTONE research document. The backend (Python + Flask) and base frontend stack (Tailwind CSS standalone CLI + Alpine.js CSP build + vanilla JS) are locked in and working. This document covers only the additions and changes needed for a Linear/Vercel-quality dark-first UI.

**Existing stack (do not re-research or change):**
- Tailwind CSS standalone CLI (v3.4.x) — generates `app/static/dist/style.css` via `make css`
- Alpine.js CSP build v3.x (~15KB) — vendored at `app/static/vendor/alpine.csp.min.js`
- Vanilla JS — enrichment polling, clipboard
- CSS custom properties — design tokens in `app/static/src/input.css`

---

## Recommended Stack

### Core Technologies (Additions/Changes Only)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Tailwind CSS darkMode: 'selector' | v3.4.19 | Class-based dark mode | Already using standalone CLI; `darkMode: 'selector'` in tailwind.config.js activates `dark:` variant when `.dark` class is on `<html>`. Replaced `'class'` strategy in v3.4.1. |
| Inter Variable Font | 4.1 (woff2) | UI typeface | Used by Linear, Notion, GitHub, Vercel. Variable font = single ~70KB woff2 file covers weights 300–900. Self-hosted as static files — no CDN, works offline, no privacy leak. |
| JetBrains Mono Variable | 2.x (woff2) | Monospace typeface | Purpose-designed for developer tools; superior code legibility to Fira Code and Cascadia at small sizes; currently used in `--font-mono`. Variable font (~60KB Latin woff2). |
| Heroicons v2 | 2.2.0 | UI icons (inline SVG) | Made by the Tailwind team; MIT licensed; copy SVGs directly into templates — zero npm, zero runtime dependency, zero CDN call. Stroke-based = inherits `currentColor` — trivially theme-able with Tailwind text utilities. |

### CSS Architecture (No New Libraries)

The existing CSS custom properties system in `input.css` is the right foundation. Changes needed are configuration and token additions — not new libraries.

| Change | What | Why |
|--------|------|-----|
| `tailwind.config.js` — add `darkMode: 'selector'` | Enables `dark:` Tailwind variants | Allows selective dark overrides as refactor progresses; dark-first = all base styles are dark already, `dark:` variant used for edge cases only |
| `tailwind.config.js` — extend `theme.colors` | Map CSS var tokens into Tailwind palette | Lets Tailwind utilities like `bg-surface-primary` work instead of raw `var()` everywhere |
| `tailwind.config.js` — add `@tailwindcss/forms` | Standardize form element base styles | Standalone CLI bundles first-party plugins; `require('@tailwindcss/forms')` just works. Forms plugin gives sensible reset for textarea, select, checkbox — needed for redesign |
| `input.css` — replace `--font-ui` system stack | Replace `-apple-system, BlinkMacSystemFont, 'Segoe UI'` with `'Inter Variable', system-ui` | Inter Variable is the target typeface; system fallback retained for load ordering |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @tailwindcss/forms | bundled with standalone CLI | CSS reset for form elements (textarea, input, select) | Use for redesigned form elements on input page |
| @tailwindcss/typography | bundled with standalone CLI | `prose` class for readable block content | Use only if adding settings page prose content; NOT needed for IOC cards or filter UI |
| Inter Variable font files | 4.1 | Self-hosted woff2 | Required — download from rsms/inter GitHub release, copy to `app/static/fonts/` |
| JetBrains Mono Variable font files | 2.x | Self-hosted woff2 | Required — download from JetBrains/JetBrainsMono GitHub release |
| Heroicons SVG files | 2.2.0 | Inline SVG icons | Copy individual SVGs from heroicons.com directly into Jinja2 templates as needed |

### Development Tools (No Changes)

The existing Makefile `css` and `css-watch` targets continue to work. No new build tooling needed.

---

## Tailwind Dark Mode Configuration

**The project is already dark-first.** All CSS custom property tokens in `input.css` define a dark color scheme as the baseline. There is no light mode. The `darkMode` config key is needed only if:

1. A future milestone adds light mode toggle (not in v1.2 scope)
2. Individual `dark:` variant utilities are needed alongside the CSS custom property system

**Recommended approach for v1.2:** Add `darkMode: 'selector'` to `tailwind.config.js` now, but rely primarily on CSS custom properties (not `dark:` utility variants) for theming. This:
- Is consistent with the existing architecture
- Does not require any JavaScript theme toggle
- Keeps templates clean (no `dark:bg-gray-900 bg-white` pairs everywhere)
- Future-proofs for light mode without a CSS architecture change

**tailwind.config.js change:**

```javascript
module.exports = {
  darkMode: 'selector',  // ADD THIS LINE
  content: [
    "./app/templates/**/*.html",
    "./app/static/**/*.js",
  ],
  // ... rest unchanged
};
```

**Why 'selector' not 'media':** `media` strategy bases dark mode on OS preference (`prefers-color-scheme`). Since this is dark-only in v1.2 and may support user toggle later, `selector` (`.dark` class on `<html>`) gives explicit control. If we ever add light mode, a one-line JS toggle enables it.

**Why not Tailwind v4:** The project uses the v3 standalone CLI binary. Tailwind v4 drops `tailwind.config.js` entirely (CSS-first config via `@custom-variant`). Migrating to v4 is a separate milestone decision; v3.4.19 is the current production-stable v3 release and the standalone CLI is still distributed for it.

---

## Font Strategy: Self-Hosting for Offline Use

SentinelX runs on analyst workstations and jump boxes that may have no internet access. Every font must be self-hosted. No Google Fonts, no Bunny Fonts, no CDN.

### Inter Variable (UI Font)

**What it is:** The standard font for developer/SaaS dark UIs. Used by Linear, GitHub, Vercel, Notion, Figma. Designed by Rasmus Andersson specifically for screen readability. Nine weights in a single variable font file.

**File sizes (Latin subset, woff2):**
- Full variable (all weights 100–900): ~70KB woff2
- Static weight files (e.g., 400 only): ~30KB each

**Recommendation:** Download the variable woff2 (Latin subset) from the rsms/inter GitHub releases. One file, all weights covered.

**@font-face declaration:**

```css
@font-face {
  font-family: 'Inter Variable';
  src: url('/static/fonts/inter-latin-variable.woff2') format('woff2-variations');
  font-weight: 100 900;
  font-style: normal;
  font-display: swap;
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6,
    U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122,
    U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;
}
```

**CSS custom property update:**

```css
--font-ui: 'Inter Variable', system-ui, -apple-system, sans-serif;
```

**Where to get:** https://github.com/rsms/inter/releases — download `Inter.zip`, extract `Inter-Variable.woff2` (already Latin-subsettable via the web export).

Alternatively use the pre-built Fontsource dist file at `@fontsource-variable/inter/files/inter-latin-wght-normal.woff2` — same file, available via npm extract without using npm at runtime.

### JetBrains Mono Variable (Monospace Font)

**What it is:** Purpose-built for developer tool UIs and code display. Better x-height at small sizes than Fira Code. Used in JetBrains IDEs, increasing adoption in security tooling UIs. OFL licensed, free.

**File sizes (Latin subset, woff2):** ~60KB variable woff2.

**@font-face declaration:**

```css
@font-face {
  font-family: 'JetBrains Mono Variable';
  src: url('/static/fonts/jetbrains-mono-latin-variable.woff2') format('woff2-variations');
  font-weight: 100 800;
  font-style: normal;
  font-display: swap;
}
```

**CSS custom property update:**

```css
--font-mono: 'JetBrains Mono Variable', 'Fira Code', 'Cascadia Code', monospace;
```

**Where to get:** https://github.com/JetBrains/JetBrainsMono/releases — download `JetBrainsMono-*.zip`, extract the variable woff2 from the `fonts/webfonts/` directory.

### Font Loading and CSP

The existing CSP is `default-src 'self'`. Self-hosted fonts at `/static/fonts/` are served from self-origin — no CSP changes needed. Do NOT use Google Fonts or any external font CDN.

**font-display: swap** is mandatory — it prevents invisible text during font load in slow environments (e.g., cold-start Flask on a jump box).

### What NOT to Use for Fonts

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Google Fonts CDN | External network call; breaks offline environments; privacy concern | Self-hosted woff2 |
| Geist (Vercel's font) | Strong brand association with Vercel product; also Inter is more universally legible | Inter Variable |
| Bunny Fonts or similar CDN | Same offline/privacy problem as Google Fonts | Self-hosted woff2 |
| Multiple static weight files | Each weight = separate HTTP request; variable font is one request, all weights | Single variable woff2 per family |
| `font-display: block` | Delays text rendering; bad UX on slow starts | `font-display: swap` |

---

## Icon Library: Heroicons v2

**Recommended approach:** Inline SVG, copied directly from heroicons.com into Jinja2 templates. No npm, no runtime JS, no CDN.

**Why Heroicons over alternatives:**

| Library | Pro | Con | Verdict |
|---------|-----|-----|---------|
| Heroicons v2 | Tailwind team; MIT; outline + solid + mini; `currentColor` inherits text color; 316 icons | Smaller set than Lucide | **Recommended** |
| Lucide | 1000+ icons; open source fork of Feather | lucide-static sprite requires npm or manual file management | Skip — overkill for ~15 icons needed |
| Phosphor | 9000+ icons, 6 styles including duotone | Too large; duotone needs 2-color CSS; more complex | Skip |
| Bootstrap Icons | Well-known set | Bootstrap-associated aesthetic doesn't fit Linear-style design language | Skip |

**CSP compatibility:** Inline SVG is `self`-served (embedded in HTML response). Zero CSP implications. No `script-src` changes. No external image sources.

**Dark theme behavior:** All Heroicons outline icons use `stroke="currentColor"`. Set `class="text-gray-400"` (or equivalent CSS var) on the SVG element — it inherits the text color from Tailwind or the parent CSS. Works identically in dark and light contexts without any extra CSS.

**How to use in Jinja2 templates:**

```html
<!-- Copy SVG from heroicons.com, add class attribute -->
<svg class="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24"
     stroke-width="1.5" stroke="currentColor">
  <path stroke-linecap="round" stroke-linejoin="round"
        d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196..." />
</svg>
```

**For Jinja2 template reuse:** Create a `macros/icons.html` with `{% macro icon_search() %}...{% endmacro %}` for each icon used more than once. Keeps templates DRY without needing an icon font or sprite system.

---

## CSS Animations and Micro-Interactions

**Recommendation: Native CSS only. No animation libraries.**

The existing `input.css` already has all needed animation primitives:
- `transition: ... 0.15s ease` on buttons and interactive elements
- `@keyframes spin` for the enrichment spinner
- `transition: width 0.3s ease` on the progress bar

For a Linear-quality dark UI, the target is **functional motion** — not decoration. Timing guidelines from the research:
- Hover state transitions: 120–150ms ease
- State change (toggle, active): 150–200ms ease-in-out
- Appearance (modal, card): 200–250ms ease-out
- Dismissal/hide: 100–150ms ease-in (faster than appear)

**New CSS-only primitives to add (no library needed):**

```css
/* Fade-in for results cards */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}

.ioc-card {
  animation: fadeInUp 200ms ease-out;
}

/* Pulse for loading state */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.4; }
}

.skeleton {
  animation: pulse 1.5s ease-in-out infinite;
}
```

**CSP compatibility:** All CSS animations are in the stylesheet served from self-origin. No `style-src 'unsafe-inline'` needed. No JS animation library = no eval risk. The existing CSP (`default-src 'self'`) requires no changes.

### What NOT to Add for Animations

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| GSAP | 100KB+; complex license for commercial use; eval-based core features | Native CSS `@keyframes` |
| Framer Motion | React-specific | Native CSS |
| Animate.css | 80KB+ for features we won't use | Write the 3–4 `@keyframes` we need inline |
| Web Animations API (WAAPI) | Requires JS for orchestration; we want CSS-first | CSS transitions + `@keyframes` |
| `transition: all` | Causes GPU-intensive repaints on every CSS property | Specify exact properties: `transition: opacity 0.2s, transform 0.2s` |

---

## Tailwind Plugins Assessment

The Tailwind standalone CLI bundles all first-party plugins. They can be required in `tailwind.config.js` without npm.

| Plugin | Verdict | Rationale |
|--------|---------|-----------|
| `@tailwindcss/forms` | **Add** | Provides sensible CSS reset for textarea, input, and select. v1.2 is redesigning the input form heavily — forms plugin prevents browser default styling from bleeding through. Activate with `require('@tailwindcss/forms')`. |
| `@tailwindcss/typography` | **Skip for now** | The `prose` class is for long-form text content. SentinelX has no editorial content. The IOC cards are not prose. Adding it bloats the CSS for no gain. |
| `@tailwindcss/container-queries` | **Skip** | Container queries are for component-level responsive design. Desktop-only tool with fixed max-width layout doesn't need them. |
| `@tailwindcss/aspect-ratio` | **Skip** | No images or media in this tool. |

**Adding @tailwindcss/forms:**

```javascript
// tailwind.config.js
module.exports = {
  darkMode: 'selector',
  content: [...],
  plugins: [
    require('@tailwindcss/forms'),  // ADD THIS
  ],
};
```

Note: `@tailwindcss/forms` resets browser form element defaults but does NOT force light-mode colors. It uses CSS custom properties or Tailwind utilities layered on top. Our existing CSS custom properties will override the reset's color defaults correctly.

---

## Tailwind Theme Extension for Design Tokens

To bridge CSS custom properties and Tailwind utilities, extend the theme so that e.g. `bg-surface-primary` works:

```javascript
// tailwind.config.js — theme.extend
theme: {
  extend: {
    colors: {
      'surface': {
        'primary':   'var(--bg-primary)',
        'secondary': 'var(--bg-secondary)',
        'tertiary':  'var(--bg-tertiary)',
      },
      'content': {
        'primary':   'var(--text-primary)',
        'secondary': 'var(--text-secondary)',
      },
      'border': {
        DEFAULT:     'var(--border)',
        'hover':     'var(--border-hover)',
      },
      'accent': {
        'emerald':   '#10b981',  // Tailwind emerald-500 (target accent)
        'teal':      '#14b8a6',  // Tailwind teal-500
      },
    },
    fontFamily: {
      'ui':   ['Inter Variable', 'system-ui', 'sans-serif'],
      'mono': ['JetBrains Mono Variable', 'Fira Code', 'monospace'],
    },
  },
},
```

This allows writing `text-content-secondary` or `bg-surface-primary` in templates, which maps to the CSS custom property tokens — maintaining the single source of truth in `input.css` `:root` while enabling Tailwind utility patterns.

---

## Installation / Setup Steps

No npm, no Node.js. The standalone CLI workflow is preserved.

```bash
# 1. Download Inter Variable font
mkdir -p app/static/fonts
# From https://github.com/rsms/inter/releases
# Extract Inter-Variable.woff2 → app/static/fonts/inter-latin-variable.woff2
# Approximate size: ~70KB

# 2. Download JetBrains Mono Variable font
# From https://github.com/JetBrains/JetBrainsMono/releases
# Extract fonts/webfonts/JetBrainsMono[wght].woff2 → app/static/fonts/jetbrains-mono-variable.woff2
# Approximate size: ~60KB

# 3. Update tailwind.config.js
# Add darkMode: 'selector' and @tailwindcss/forms plugin (see above)

# 4. Regenerate CSS
make css
```

**No new Python dependencies.** No new npm packages. No new Alpine plugins.

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Inter Variable (self-hosted) | Geist (Vercel's font) | Geist is closely branded to Vercel product; Inter is the neutral standard across Linear, GitHub, Figma, Notion — more appropriate for a security tool |
| Heroicons v2 (inline SVG) | Lucide (SVG sprite) | Lucide sprite requires a build step or npm; Heroicons inline is zero-infrastructure; 316 icons is more than enough |
| Heroicons v2 (inline SVG) | Font Awesome | Font icon fonts require extra HTTP requests, have worse accessibility than SVG, and carry unused glyphs |
| Native CSS @keyframes | Animate.css | 80KB for ~15KB worth of animations we'd actually use; our 3-4 keyframes take 20 lines |
| @tailwindcss/forms plugin | Custom form resets | Forms plugin is the battle-tested Tailwind-native approach; avoids browser quirks with textarea and select |
| darkMode: 'selector' | darkMode: 'media' | Media strategy can't be toggled by JS; selector gives future flexibility |
| CSS custom properties | Tailwind dark: variants everywhere | Custom properties = single source of truth; dark: variants in every class list = verbose and fragile |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Google Fonts or any external CDN | Offline environments (jump boxes); privacy; CSP violation risk | Self-hosted woff2 |
| GSAP, Framer Motion | JS-based animation; eval risk; payload bloat | Native CSS `@keyframes` and `transition` |
| Alpine.js plugins (Collapse, etc.) | CSP build doesn't support plugin injection via CDN; would need vendoring | Vanilla JS for any animation-driven state changes |
| @tailwindcss/typography plugin | No prose content in this tool | Skip |
| @tailwindcss/container-queries | Desktop-only fixed-width layout, no component-level responsive breakpoints needed | Skip |
| Tailwind v4 | Would require migration from tailwind.config.js to CSS-first config, breaking the existing Makefile and standalone CLI binary setup | Stay on v3.4.19 |
| `transition: all` | Triggers paint on every CSS property including layout; expensive | Always specify exact properties in transition |
| Dark-mode-only icon libraries (e.g., themed icon sets) | Add dependency for zero benefit over inline SVG | Heroicons v2 inline SVG |
| Phosphor Icons duotone style | Requires 2-color CSS tricks; complex for dark themes | Heroicons outline (single `currentColor`) |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Tailwind CSS standalone CLI v3.4.19 | `tailwind.config.js` format | Last v3.x stable release (Dec 2024); standalone CLI binary bundled with first-party plugins |
| @tailwindcss/forms | Tailwind v3.4.x | Bundled in standalone CLI; `require('@tailwindcss/forms')` in config |
| Inter Variable woff2 | All modern browsers (Chrome 66+, Firefox 62+, Safari 11+) | `format('woff2-variations')` |
| JetBrains Mono Variable woff2 | Same modern browser support | `format('woff2-variations')` |
| Heroicons v2.2.0 | Static SVG; no browser compatibility concern | Inline SVG works everywhere |
| Alpine.js CSP build v3.x | Existing; no changes | No new Alpine plugins |

---

## Sources

- Tailwind v3 dark mode docs (v3.tailwindcss.com/docs/dark-mode) — class vs selector strategy, confirmed `darkMode: 'selector'` replaced `'class'` in v3.4.1 (HIGH confidence)
- Tailwind CSS GitHub releases (github.com/tailwindlabs/tailwindcss/releases) — confirmed v3.4.19 is latest v3.x stable (HIGH confidence)
- Tailwind standalone CLI docs (tailwindcss.com/blog/standalone-cli) — confirmed first-party plugins bundled; `require('@tailwindcss/forms')` works without npm (HIGH confidence)
- Inter font GitHub (github.com/rsms/inter) — confirmed variable woff2 availability, ~70KB Latin subset (HIGH confidence)
- JetBrains Mono GitHub (github.com/JetBrains/JetBrainsMono) — confirmed variable woff2, OFL license (HIGH confidence)
- Heroicons v2 GitHub (github.com/tailwindlabs/heroicons) — confirmed v2.2.0, MIT license, inline SVG approach documented (HIGH confidence)
- Vercel Geist design system colors (vercel.com/geist/colors) — confirmed CSS custom property token naming patterns and teal/green accent usage (HIGH confidence)
- Fontsource Inter docs (fontsource.org/fonts/inter/install) — confirmed self-hosting approach, woff2-variations format string (HIGH confidence)
- Linear UI redesign post (linear.app/now/how-we-redesigned-the-linear-ui) — confirmed Inter is Linear's typeface (HIGH confidence — official source)
- WebSearch: CSS micro-interactions timing (120–220ms range), "functional motion" as 2025 standard (MEDIUM confidence — multiple sources agree)
- WebSearch: @tailwindcss/typography dark mode with `prose-invert` class (MEDIUM confidence — docs verified)

---

*Stack research for: SentinelX v1.2 Modern Dark UI Redesign*
*Researched: 2026-02-25*
