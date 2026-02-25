# Phase 11: Foundation — Design Tokens & Base CSS — Research

**Researched:** 2026-02-25
**Domain:** CSS custom property token systems, self-hosted variable fonts, dark-mode browser signals, WCAG AA contrast verification
**Confidence:** HIGH

---

## Summary

Phase 11 replaces SentinelX's current GitHub-flavored dark theme (midnight blue-grays, `#0d1117` base) with a zinc/emerald/teal design system that mirrors the Linear/Vercel premium SaaS aesthetic. The work is entirely contained within three files — `app/static/src/input.css`, `app/templates/base.html`, and `tailwind.config.js` — plus the new `app/static/fonts/` directory. No templates other than `base.html` are touched. No backend changes. No JS changes.

The eight requirements divide into four distinct workstreams: (1) rewrite the `:root` token block with the new zinc-emerald-teal palette and typography scale; (2) download Inter Variable and JetBrains Mono Variable woff2 files into `app/static/fonts/` and wire up `@font-face` declarations plus `<link rel="preload">` in `base.html`; (3) add `<meta name="color-scheme" content="dark">` to `base.html` and `:root { color-scheme: dark; }` in CSS to fix native controls and scrollbars; (4) add a `-webkit-autofill` override block for the settings API key input. After all four workstreams are complete, a manual WCAG AA contrast audit must pass before the phase closes.

The only gate criterion that blocks Phase 12 is the contrast audit. Everything else is verifiable immediately via browser DevTools font inspection. The existing Playwright E2E tests require no changes — Phase 11 makes no structural HTML changes and no class name changes, so all existing selectors remain valid.

**Primary recommendation:** Rewrite the `:root` token block atomically (replacing all old tokens in one pass), add fonts, add browser dark-mode signals, run `make css`, and then verify every token pair with the WebAIM Contrast Checker before marking the phase done.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FOUND-01 | Design token system defined as CSS custom properties at `:root` — zinc-based surface hierarchy (950/900/800/700), emerald/teal accent system, four-state verdict color triples (text/bg/border per verdict) | Target hex values fully specified in SUMMARY.md; pattern: rewrite existing `:root` block replacing GitHub palette with zinc/emerald/teal values |
| FOUND-02 | Inter Variable font self-hosted in `app/static/fonts/` with `@font-face` declaration and `crossorigin` preload link in `base.html` | Self-hosting mandatory (CSP `default-src 'self'`, airgapped environments); Inter Variable Latin woff2 ~70KB from rsms/inter GitHub releases; `@font-face` with `font-display: swap` |
| FOUND-03 | JetBrains Mono Variable font self-hosted in `app/static/fonts/` with `@font-face` declaration, applied to all IOC value displays | JetBrains Mono Variable woff2 ~60KB from JetBrains/JetBrainsMono GitHub releases; `--font-mono` token already used for all `.ioc-value` and textarea font-family |
| FOUND-04 | `<meta name="color-scheme" content="dark">` added to `base.html` and `:root { color-scheme: dark; }` in CSS, fixing native form controls and scrollbar rendering | MDN-verified: `color-scheme: dark` on `:root` tells browsers to render native UI (scrollbars, selects, date pickers) in dark mode; `<meta>` tag ensures early signal before CSS loads |
| FOUND-05 | All text/background token pairs pass WCAG AA contrast — 4.5:1 for normal text, 3:1 for UI components — verified before any component work begins | Specific token pairs to audit documented below; existing secondary text (`#8b949e` on `#161b22`) fails at ~3.2:1 — new zinc-400 (`#a1a1aa`) on zinc-950 (`#09090b`) achieves ~7:1 |
| FOUND-06 | Browser autofill override CSS prevents yellow flash on dark input fields (settings page API key field) | Chrome for Developers documented technique: `box-shadow: 0 0 0 100px var(--surface-input) inset; -webkit-text-fill-color: var(--text-primary); transition: background-color 5000s` on `input:-webkit-autofill` |
| FOUND-07 | `tailwind.config.js` updated with `darkMode: 'selector'`, extended theme colors mapping to CSS tokens, and `@tailwindcss/forms` plugin activated | Tailwind v3 `darkMode: 'selector'` (not `'class'` — selector is the v3.3+ recommended name); `@tailwindcss/forms` is bundled in the standalone CLI, activated via `require('@tailwindcss/forms')` in plugins array |
| FOUND-08 | Typography scale defined — 3-tier weight system (headings, body, captions) with -0.02em tracking on headings, consistent line-height ratios | Token-level changes: `--font-ui` → Inter Variable, `--font-mono` → JetBrains Mono Variable; weight tokens for headings (600), body (400), captions (500); tracking token -0.02em for headings |
</phase_requirements>

---

## Standard Stack

### Core (already in the project — no new installs needed)

| Component | Version | Purpose | Status |
|-----------|---------|---------|--------|
| Tailwind CSS standalone CLI | v3.4.17 (per Makefile) | CSS compilation from `input.css` → `dist/style.css` | Installed at `./tools/tailwindcss` |
| `@tailwindcss/forms` | Bundled in standalone CLI | CSS reset for textarea, inputs, select | Needs activation in `plugins:[]` |
| Inter Variable | ~70KB woff2 | UI typeface — all chrome text | Not yet downloaded |
| JetBrains Mono Variable | ~60KB woff2 | Monospace — IOC values, textarea | Not yet downloaded |

### New (to be added in this phase)

| Component | Source | Notes |
|-----------|--------|-------|
| Inter Variable woff2 | `github.com/rsms/inter/releases` — `Inter.var.woff2` (Latin subset) | SIL OFL license; download directly, no npm |
| JetBrains Mono Variable woff2 | `github.com/JetBrains/JetBrainsMono/releases` — `JetBrainsMono[wght].woff2` | SIL OFL license; download directly, no npm |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Self-hosted fonts | Google Fonts CDN | Blocked by CSP `default-src 'self'`; airgapped environments have no internet access |
| `font-display: swap` | `font-display: block` | `swap` = content visible immediately, font swaps in; `block` = FOIT; `swap` is correct for a tool used heavily on repeat visits |
| `darkMode: 'selector'` | `darkMode: 'class'` | `'selector'` is the v3.3+ replacement for `'class'`; functionally identical but is the current documented API |

**Installation:** No package installs needed. Font files downloaded manually via `curl`. `@tailwindcss/forms` is bundled.

---

## Architecture Patterns

### Token Naming Convention (CONFIRMED for this project)

Based on the research synthesis decision: keep CSS custom properties as semantic tokens in `input.css`, referenced directly in `@layer components` rules via `var()`. Only extend `tailwind.config.js` theme for tokens that must appear in Jinja2 HTML as utility classes.

For Phase 11, **no Tailwind theme extension for color tokens is needed** — all color usage is in component classes, not in Jinja2 utility strings. The `tailwind.config.js` changes in this phase are only:
1. Add `darkMode: 'selector'`
2. Add `@tailwindcss/forms` to `plugins:`

### Pattern 1: CSS Custom Property Token Block Rewrite

**What:** Replace the existing `:root` block entirely with the new zinc/emerald/teal token set. Keep all existing token names that are referenced in component styles (surface, text, border, verdict, accent tokens). Rename values but preserve variable names where possible to avoid touching component rules.

**Token rename table (old name → new name → new value):**

```css
/* BEFORE (GitHub palette) */
:root {
    --bg-primary:    #0d1117;   /* midnight navy */
    --bg-secondary:  #161b22;   /* dark blue-gray card */
    --bg-tertiary:   #1c2128;   /* slightly lighter */
    --text-primary:  #e6edf3;   /* cool white */
    --text-secondary: #8b949e;  /* muted blue-gray — FAILS WCAG AA on bg-secondary */
    --border:        #30363d;
    --border-hover:  #484f58;
    --verdict-malicious:  #f85149;
    --verdict-suspicious: #f59e0b;
    --verdict-clean:      #3fb950;
    --verdict-no-data:    #8b949e;
    --verdict-error:      #d29922;
    --font-mono: 'Fira Code', 'Cascadia Code', 'JetBrains Mono', ...;
    --font-ui:   -apple-system, BlinkMacSystemFont, ...;
}

/* AFTER (zinc/emerald/teal palette) */
:root {
    /* Surfaces — zinc hierarchy */
    --bg-primary:    #09090b;   /* zinc-950 — page base */
    --bg-secondary:  #18181b;   /* zinc-900 — card surface */
    --bg-tertiary:   #27272a;   /* zinc-800 — inputs, nested */
    --bg-hover:      #3f3f46;   /* zinc-700 — hover state */

    /* Borders — opacity-based (no color shift) */
    --border:        rgba(255, 255, 255, 0.06);   /* subtle */
    --border-default: rgba(255, 255, 255, 0.10);  /* default */
    --border-hover:  rgba(255, 255, 255, 0.18);   /* emphasis */

    /* Text — zinc scale */
    --text-primary:   #f4f4f5;  /* zinc-100 — headings */
    --text-secondary: #a1a1aa;  /* zinc-400 — labels, metadata — ~7:1 on zinc-950 */
    --text-muted:     #71717a;  /* zinc-500 — placeholder, footnotes */

    /* Accent */
    --accent:         #10b981;  /* emerald-500 — primary actions */
    --accent-hover:   #34d399;  /* emerald-400 — hover */
    --accent-subtle:  #022c22;  /* emerald-950 — tinted bg */
    --accent-interactive: #14b8a6; /* teal-500 — focus rings, secondary interactive */

    /* Verdict color triples */
    --verdict-malicious-text:   #f87171;   /* red-400 */
    --verdict-malicious-bg:     #450a0a;   /* red-950 */
    --verdict-malicious-border: #ef4444;   /* red-500 */

    --verdict-suspicious-text:   #fbbf24;  /* amber-400 */
    --verdict-suspicious-bg:     #451a03;  /* amber-950 */
    --verdict-suspicious-border: #f59e0b;  /* amber-500 */

    --verdict-clean-text:   #34d399;   /* emerald-400 */
    --verdict-clean-bg:     #022c22;   /* emerald-950 */
    --verdict-clean-border: #10b981;   /* emerald-500 */

    --verdict-no-data-text:   #a1a1aa;  /* zinc-400 */
    --verdict-no-data-bg:     #27272a;  /* zinc-800 */
    --verdict-no-data-border: #3f3f46;  /* zinc-700 */

    --verdict-error-text:   #fbbf24;   /* reuse amber — error is rare */
    --verdict-error-bg:     #451a03;
    --verdict-error-border: #f59e0b;

    /* Typography tokens */
    --font-ui:   'Inter Variable', system-ui, sans-serif;
    --font-mono: 'JetBrains Mono Variable', 'JetBrains Mono', monospace;

    /* Typography scale */
    --weight-heading: 600;
    --weight-body:    400;
    --weight-caption: 500;
    --tracking-heading: -0.02em;
    --line-height-body: 1.6;

    /* Shape */
    --radius:    6px;
    --radius-sm: 4px;

    /* Dark mode signal */
    color-scheme: dark;
}
```

**Important note on token naming:** The component rules throughout `input.css` reference `--verdict-malicious`, `--verdict-suspicious`, etc. (single token per verdict). Moving to verdict triples (text/bg/border) means updating component rules that use these tokens. The component rules that will need updating:
- `.verdict-label--*` styles (currently use `--verdict-{name}` for color)
- `.verdict-dashboard-badge[data-verdict="*"]` styles (currently use hardcoded rgba for bg/border)
- `.ioc-card[data-verdict="*"]` border-left colors
- `.verdict-badge` classes (`.verdict-malicious`, `.verdict-suspicious`, etc.)
- Filter button active states

**Strategy:** Introduce both the old single-name tokens AND the new triple tokens in Phase 11, then update the component rules that use them. This is all within `input.css` — no template changes needed.

### Pattern 2: Self-Hosted Variable Font with @font-face

```css
/* In input.css, inside @layer base or before @tailwind directives */

@font-face {
    font-family: 'Inter Variable';
    font-style: normal;
    font-weight: 100 900;
    font-display: swap;
    src: url('/static/fonts/InterVariable.woff2') format('woff2');
}

@font-face {
    font-family: 'JetBrains Mono Variable';
    font-style: normal;
    font-weight: 100 800;
    font-display: swap;
    src: url('/static/fonts/JetBrainsMonoVariable.woff2') format('woff2');
}
```

**Note:** Flask serves static files at `/static/` by default, not `/app/static/`. The `src` URL in `@font-face` must match the browser-visible URL, not the filesystem path. Use `url('/static/fonts/...')` — or better, use Jinja2's `url_for` syntax if the CSS is ever processed by Flask (it is NOT in this stack — Tailwind CLI compiles the CSS without Flask context). Therefore use the literal path `/static/fonts/InterVariable.woff2`.

**Verification:** After `make css`, open DevTools → Network tab → reload → filter by "Font" — confirm `InterVariable.woff2` and `JetBrainsMonoVariable.woff2` appear with status 200.

### Pattern 3: Preload Links in base.html

```html
<!-- In <head>, before <link rel="stylesheet"> -->
<link rel="preload"
      href="{{ url_for('static', filename='fonts/InterVariable.woff2') }}"
      as="font"
      type="font/woff2"
      crossorigin>
<link rel="preload"
      href="{{ url_for('static', filename='fonts/JetBrainsMonoVariable.woff2') }}"
      as="font"
      type="font/woff2"
      crossorigin>
```

**Why `crossorigin`:** Even for same-origin fonts, the `crossorigin` attribute is required on preload links for fonts. Without it, the browser fetches the font twice: once from the preload hint and once from the actual CSS `@font-face` declaration. This is a well-known browser behavior documented by MDN. The attribute value can be omitted (bare `crossorigin`) or set to `crossorigin="anonymous"` — both work identically for same-origin resources.

### Pattern 4: color-scheme dark Signal

Two-part fix — both parts needed:

**Part 1: HTML meta tag (in base.html `<head>`):**
```html
<meta name="color-scheme" content="dark">
```

**Part 2: CSS property (in input.css `:root`):**
```css
:root {
    color-scheme: dark;
}
```

**Why both?** The `<meta>` tag signals the browser's rendering engine before CSS is parsed, preventing a flash of light-themed native controls. The CSS `color-scheme` property applies to the cascade and affects inherited computations. MDN and Chrome developer docs both recommend both for complete coverage.

**Effect:** Scrollbars, native `<select>` dropdowns, date inputs, checkbox/radio, focus indicators — all render in the OS dark mode appearance without any additional CSS needed.

### Pattern 5: Autofill Override

The browser autofill yellow (#ffeaa7 or similar) overrides `background-color` on inputs. The standard workaround uses `box-shadow` to paint over the autofill background (browsers do not override `box-shadow`):

```css
/* In @layer components or after :root */

input:-webkit-autofill,
input:-webkit-autofill:hover,
input:-webkit-autofill:focus,
input:-webkit-autofill:active {
    -webkit-box-shadow: 0 0 0 100px var(--bg-tertiary) inset !important;
    box-shadow:         0 0 0 100px var(--bg-tertiary) inset !important;
    -webkit-text-fill-color: var(--text-primary) !important;
    transition: background-color 5000s ease-in-out 0s;
}
```

**Why `transition: background-color 5000s`:** This prevents the autofill background from flashing by delaying any background-color transition for ~83 minutes, effectively locking it. The `box-shadow` approach is the canonical Chrome workaround documented by Chrome for Developers.

**Scope:** The settings page has an API key `<input type="password">` that browsers offer to autofill. This is the primary affected element.

### Pattern 6: @tailwindcss/forms Activation

In `tailwind.config.js`:
```js
plugins: [
    require('@tailwindcss/forms'),
],
```

The `@tailwindcss/forms` plugin is bundled in the Tailwind standalone CLI binary — no `npm install` or `node_modules` needed. The `require()` call works because the standalone CLI bundles all official plugins. Verify by running `make css` — if the plugin is not bundled, Tailwind will throw a module resolution error.

**What it does:** Resets browser-default styling on `input`, `textarea`, `select`, `checkbox`, `radio`, and `file` elements to a consistent baseline that dark-theme CSS can build on. Without this reset, `<select>` elements in particular render with OS-native light backgrounds even with `color-scheme: dark`.

### Pattern 7: darkMode: 'selector' Config

```js
module.exports = {
    darkMode: 'selector',
    // ...
};
```

This adds support for `.dark` selector-based dark mode utilities (`dark:bg-zinc-900` etc.) without requiring `prefers-color-scheme`. Since v1.2 is dark-first with no light mode toggle, this is primarily future-proofing. The `'selector'` value was introduced in Tailwind CSS v3.3.0. The previously common `'class'` value still works but `'selector'` is the current documented API.

### Anti-Patterns to Avoid

- **Hardcoding hex values in component rules:** All color values in `@layer components` must reference `var(--token-name)`. No `#10b981` literals allowed in component rules.
- **Using `darkMode: 'media'`:** This would tie dark mode to OS preference. For a security tool, dark-always is correct. Use `'selector'` for explicit control.
- **Linking fonts from a CDN:** CSP blocks it. Flask serves only from `'self'`. All fonts must be in `app/static/fonts/`.
- **Putting `@font-face` inside `@layer`:** Tailwind's `@layer` directive maps to CSS cascade layers. `@font-face` declarations should be outside any `@layer` block — place them at the top of `input.css` before `@tailwind base`.
- **Using `font-display: block`:** Creates flash of invisible text (FOIT). `font-display: swap` shows system fallback until Inter loads — correct for a tool used on repeat visits.
- **Forgetting `crossorigin` on preload links:** Without it, the browser fetches the font twice. Always include `crossorigin` on font preload `<link>` elements.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Autofill background override | Custom `<input>` wrapper or JS | `-webkit-autofill` box-shadow trick | Browsers won't respect `background-color` on autofill — only `box-shadow` works reliably |
| Form element reset | Manual reset for each input/textarea/select | `@tailwindcss/forms` | Handles cross-browser edge cases including `<select>` appearance on Safari/Firefox |
| Dark native controls | CSS targeting `scrollbar-color`, `::-webkit-scrollbar` | `color-scheme: dark` | OS-aware — correct dark mode signal without browser-specific hacks (which have limited support) |
| WCAG contrast calculation | Manual formula implementation | WebAIM Contrast Checker (webmaster.soe.ucsc.edu/contrast) or browser DevTools Accessibility panel | Luminance math is error-prone; existing tools are verified |

**Key insight:** The browser dark-mode ecosystem (`color-scheme`, autofill overrides, native form resets) is filled with browser-specific quirks. Using the platform-native signals (`color-scheme: dark`) and established workarounds (autofill box-shadow trick) is far more reliable than trying to CSS-override each native control individually.

---

## Common Pitfalls

### Pitfall 1: Secondary Text Fails WCAG AA on New Surfaces

**What goes wrong:** The old `--text-secondary: #8b949e` on `--bg-secondary: #161b22` achieves ~3.2:1 — it passes 3:1 (UI components) but fails 4.5:1 (normal text). On the new zinc-900 card surface (`#18181b`), `#8b949e` would achieve ~3.0:1 — below even the UI component threshold.

**Why it happens:** The existing design was calibrated for GitHub's blue-gray palette. The zinc palette has different relative luminance values.

**How to avoid:** Use `--text-secondary: #a1a1aa` (zinc-400) throughout. Zinc-400 on zinc-950 achieves ~7:1. Zinc-400 on zinc-900 achieves ~6.5:1. Both pass normal text at 4.5:1 comfortably.

**Warning signs:** If anything labeled as secondary text is more muted than zinc-400 in the new palette, re-check its contrast.

### Pitfall 2: Font URL Path in @font-face vs Filesystem Path

**What goes wrong:** The `@font-face` `src: url()` path must match the browser-visible URL, not the filesystem path. The file lives at `app/static/fonts/InterVariable.woff2` on disk, but the browser fetches it from `/static/fonts/InterVariable.woff2`.

**Why it happens:** Tailwind CLI compiles `input.css` without any Flask context, so Jinja2 `url_for()` cannot be used in CSS. The path in CSS must be the literal URL path.

**How to avoid:** Use `url('/static/fonts/InterVariable.woff2')` in `@font-face`. Verify by running the Flask dev server and inspecting the Network tab — the font request should show status 200.

### Pitfall 3: @tailwindcss/forms Require Fails if Tailwind Version Doesn't Bundle It

**What goes wrong:** `require('@tailwindcss/forms')` in `tailwind.config.js` resolves through the standalone CLI's bundled module system. If the CLI version is older, the plugin may not be bundled.

**Why it happens:** The Makefile shows `v3.4.17` — this version DOES bundle `@tailwindcss/forms`. But if the binary is ever updated independently, this could change.

**How to avoid:** Run `make css` immediately after adding the plugin. If Tailwind throws `Cannot find module '@tailwindcss/forms'`, the plugin needs to be installed separately (or the binary updated). This is unlikely at v3.4.x but worth verifying.

### Pitfall 4: Verdict Token Name Split-Brain

**What goes wrong:** The existing code uses `--verdict-malicious`, `--verdict-suspicious`, etc. as single-value tokens (just the text color). Phase 11 introduces verdict triples (`--verdict-malicious-text`, `--verdict-malicious-bg`, `--verdict-malicious-border`). If the old single-name tokens are not also updated (or removed), component rules that reference them will use stale values.

**Why it happens:** `@layer components` rules use `var(--verdict-malicious)` for border-left colors on `.ioc-card[data-verdict="malicious"]`. If `--verdict-malicious` keeps its old value (`#f85149`) while the new `-text` variant (`#f87171`) is added, the old border-left colors will not match the new badge colors.

**How to avoid:** Two options:
1. **Keep the single-name tokens** but update their values to be aliases (`--verdict-malicious: var(--verdict-malicious-text)`), OR
2. **Remove single-name tokens** and update all component rules that referenced them in the same PR.

**Recommendation:** Option 2 — remove single-name tokens and update all component rules atomically. This is cleaner and the search scope is contained entirely within `input.css`.

### Pitfall 5: IOC Type Accent Colors Need Re-evaluation

**What goes wrong:** The existing `--accent-*` tokens for IOC types use colors from the GitHub palette (`#4a9eff` for IPv4, `#4aff9e` for domain, etc.). These are not the zinc/emerald/teal target palette colors. They may or may not pass WCAG AA on the new zinc-900 card surface.

**Why it happens:** IOC type badge colors were never aligned to a design system — they were picked for visual distinctiveness on the old dark blue-gray background.

**How to avoid:** Audit each `--accent-*` color against the new `--bg-secondary: #18181b` surface. The current values (blue `#4a9eff`, green `#4aff9e`, teal `#4aeeee`, orange `#ff9e4a`, red `#ff4a4a`) should mostly pass — they are all high-luminance colors — but verify with contrast checker before closing the phase. If any fail, bump to the next brighter variant in the Tailwind palette.

### Pitfall 6: Existing .verdict-suspicious is Hardcoded Solid Amber

**What goes wrong:** `input.css` line 753 has `.verdict-label--suspicious { background-color: #f59e0b; color: #000; }` — a solid amber badge with black text. This is NOT the target tinted-background pattern.

**Why it happens:** This was a quick-ship outlier from v1.1. It's explicitly called out in the project research as the single biggest design inconsistency.

**How to avoid:** Phase 11 does NOT fix the suspicious badge visual (that's Phase 12, COMP-01). But Phase 11 DOES need to define the `--verdict-suspicious-text`, `--verdict-suspicious-bg`, and `--verdict-suspicious-border` tokens that Phase 12 will use. Ensure these tokens exist in the `:root` block even if the component rules that use them aren't updated until Phase 12.

### Pitfall 7: Preload crossorigin Must Match @font-face CORS Mode

**What goes wrong:** The preload hint and the `@font-face` declaration must use the same CORS mode. If the preload has `crossorigin` but the `@font-face` does not explicitly set CORS (which is the default for same-origin), browsers still double-fetch.

**Why it happens:** Browser font fetching uses CORS anonymous mode by default. Preload with `crossorigin` also uses CORS anonymous. For same-origin fonts, both work — but the `crossorigin` attribute on the preload link is still required to prevent double-fetch. This is a browser behavior, not an error state.

**How to avoid:** Always include `crossorigin` (or `crossorigin="anonymous"`) on font preload links. The `@font-face` CSS does not need a CORS attribute — the browser handles this automatically for same-origin requests.

---

## Code Examples

### Complete @font-face declarations

```css
/* Place BEFORE @tailwind directives in input.css */

@font-face {
    font-family: 'Inter Variable';
    font-style: normal;
    font-weight: 100 900;
    font-display: swap;
    src: url('/static/fonts/InterVariable.woff2') format('woff2');
}

@font-face {
    font-family: 'JetBrains Mono Variable';
    font-style: normal;
    font-weight: 100 800;
    font-display: swap;
    src: url('/static/fonts/JetBrainsMonoVariable.woff2') format('woff2');
}
```

### base.html head section after changes

```html
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="dark">
    <title>SentinelX — IOC Extractor</title>
    <link rel="icon" type="image/svg+xml" href="{{ url_for('static', filename='images/logo.svg') }}">
    <link rel="preload"
          href="{{ url_for('static', filename='fonts/InterVariable.woff2') }}"
          as="font"
          type="font/woff2"
          crossorigin>
    <link rel="preload"
          href="{{ url_for('static', filename='fonts/JetBrainsMonoVariable.woff2') }}"
          as="font"
          type="font/woff2"
          crossorigin>
    <link rel="stylesheet" href="{{ url_for('static', filename='dist/style.css') }}">
</head>
```

### tailwind.config.js after changes

```js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/static/**/*.js",
  ],
  darkMode: 'selector',
  safelist: [
    // (existing safelist unchanged)
    "ioc-type-badge--ipv4",
    "ioc-type-badge--ipv6",
    // ... etc
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
};
```

### Autofill override CSS

```css
/* In @layer components after all other input rules */

input:-webkit-autofill,
input:-webkit-autofill:hover,
input:-webkit-autofill:focus,
input:-webkit-autofill:active {
    -webkit-box-shadow: 0 0 0 100px var(--bg-tertiary) inset !important;
    box-shadow:         0 0 0 100px var(--bg-tertiary) inset !important;
    -webkit-text-fill-color: var(--text-primary) !important;
    transition: background-color 5000s ease-in-out 0s;
}
```

---

## WCAG AA Contrast Audit Requirements

### Token Pairs to Verify (manual, pre-Phase 12 gate)

| Foreground Token | Background Token | Hex Values | Min Ratio | Category |
|-----------------|-----------------|------------|-----------|----------|
| `--text-primary` (`#f4f4f5`) | `--bg-primary` (`#09090b`) | zinc-100 on zinc-950 | 4.5:1 | Normal text |
| `--text-primary` (`#f4f4f5`) | `--bg-secondary` (`#18181b`) | zinc-100 on zinc-900 | 4.5:1 | Normal text (card) |
| `--text-secondary` (`#a1a1aa`) | `--bg-primary` (`#09090b`) | zinc-400 on zinc-950 | 4.5:1 | Normal text (labels) |
| `--text-secondary` (`#a1a1aa`) | `--bg-secondary` (`#18181b`) | zinc-400 on zinc-900 | 4.5:1 | Normal text (card labels) |
| `--text-muted` (`#71717a`) | `--bg-primary` (`#09090b`) | zinc-500 on zinc-950 | 3:1 | UI components (placeholders) |
| `--accent` (`#10b981`) | `--bg-primary` (`#09090b`) | emerald-500 on zinc-950 | 3:1 | UI components (buttons) |
| `--verdict-malicious-text` (`#f87171`) | `--verdict-malicious-bg` (`#450a0a`) | red-400 on red-950 | 4.5:1 | Normal text (badge) |
| `--verdict-suspicious-text` (`#fbbf24`) | `--verdict-suspicious-bg` (`#451a03`) | amber-400 on amber-950 | 4.5:1 | Normal text (badge) |
| `--verdict-clean-text` (`#34d399`) | `--verdict-clean-bg` (`#022c22`) | emerald-400 on emerald-950 | 4.5:1 | Normal text (badge) |
| `--verdict-no-data-text` (`#a1a1aa`) | `--verdict-no-data-bg` (`#27272a`) | zinc-400 on zinc-800 | 4.5:1 | Normal text (badge) |

**Tool:** WebAIM Contrast Checker (https://webaim.org/resources/contrastchecker/) or browser DevTools Accessibility panel.

**Known pass cases (pre-verified in project research):** The target zinc/emerald palette values were pre-selected to pass — but the research emphasizes that "contrast assumed, not verified" is pitfall #1. Verify every pair regardless.

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|-----------------|-------|
| `darkMode: 'class'` in tailwind.config | `darkMode: 'selector'` | v3.3+ nomenclature; functionally identical |
| `@font-face` format('woff2') without variable range | `font-weight: 100 900` range for variable fonts | Required to activate variable font interpolation |
| Single verdict color token | Verdict color triples (text/bg/border) | Enables tinted-background badge pattern without hardcoded rgba values |
| System font stack | Self-hosted Inter Variable | Consistent rendering across OS; required for airgapped deployment |

**Deprecated/outdated:**
- Fira Code as primary monospace: The current CSS has `--font-mono: 'Fira Code', 'Cascadia Code', 'JetBrains Mono', ...`. Phase 11 replaces this with JetBrains Mono Variable as the primary, with system monospace as fallback.
- GitHub blue-gray palette (`#0d1117` base): Replaced entirely with zinc hierarchy.

---

## Open Questions

1. **Font file exact names from releases**
   - What we know: Inter Variable is distributed as `InterVariable.woff2` (Latin subset) in rsms/inter releases. JetBrains Mono Variable is distributed as `JetBrainsMono[wght].woff2` in JetBrains/JetBrainsMono releases.
   - What's unclear: Exact filename in the latest release may vary slightly (e.g., `JetBrainsMono-VF.woff2`). Need to check the actual release page at download time.
   - Recommendation: Check the GitHub releases page at download time. Rename to `InterVariable.woff2` and `JetBrainsMonoVariable.woff2` after download for consistent local filenames.

2. **@tailwindcss/forms compatibility with existing custom form styles**
   - What we know: The `forms` plugin resets native browser appearance on inputs/selects/textareas. The existing `input.css` has custom form styles (`.ioc-textarea`, `.filter-search-input`, etc.).
   - What's unclear: Whether `@tailwindcss/forms` reset will conflict with any existing component rules.
   - Recommendation: The plugin uses lower specificity than `@layer components` rules, so conflicts are unlikely. If visual regressions appear after activating the plugin, inspect with DevTools to see which rule wins.

3. **IOC type accent colors re-evaluation**
   - What we know: Current accent colors were calibrated for the GitHub palette. They are all high-luminance saturated colors.
   - What's unclear: Whether to align them to the Tailwind palette (e.g., `--accent-ipv4: #60a5fa` sky-400 instead of the ad-hoc `#4a9eff`) or leave as-is if they pass contrast.
   - Recommendation: Audit contrast. If they pass, leave values as-is for Phase 11. Palette alignment can be addressed in a future cleanup.

---

## Implementation Order Within Phase

Based on dependencies, the recommended task order is:

1. **Download fonts** — `curl` the two woff2 files into `app/static/fonts/` (no dependencies)
2. **Add @font-face declarations** to `input.css` (depends on: fonts downloaded)
3. **Add preload links + color-scheme meta** to `base.html` (depends on: font filenames known)
4. **Rewrite :root token block** in `input.css` — replace all tokens with zinc/emerald/teal values (no template dependencies)
5. **Update component rules** that reference changed token names (depends on: new :root block)
6. **Add autofill override CSS** (no dependencies)
7. **Update tailwind.config.js** — add darkMode + forms plugin (no dependencies)
8. **Run `make css`** and verify build succeeds
9. **Manual WCAG AA audit** — verify every token pair in the table above (gate criterion)
10. **Manual browser verification** — confirm fonts load, scrollbar is dark, autofill stays dark

---

## Sources

### Primary (HIGH confidence)

- Project SUMMARY.md — complete zinc/emerald/teal token hex values, architecture decisions, pitfall analysis
- Project REQUIREMENTS.md — exact requirement wording for FOUND-01 through FOUND-08
- MDN Web Docs — `color-scheme` property behavior, `crossorigin` attribute on preload, `font-display` values
- Tailwind CSS v3 official docs — `darkMode: 'selector'`, standalone CLI plugin bundling, `@layer` behavior
- Chrome for Developers — autofill override technique (`-webkit-autofill` box-shadow)
- WCAG 2.1 SC 1.4.3 (contrast minimum), SC 1.4.11 (non-text contrast)

### Secondary (MEDIUM confidence)

- rsms/inter GitHub — Inter Variable font distribution format and file naming
- JetBrains/JetBrainsMono GitHub — JetBrains Mono Variable woff2 distribution

### Tertiary (LOW confidence)

- None — all key implementation decisions are covered by HIGH or MEDIUM confidence sources.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all technologies are existing project stack with additive changes only
- Architecture: HIGH — token naming, font URL paths, and browser dark-mode signals all verified against official sources
- Pitfalls: HIGH — contrast failure, font URL path, and autofill issues are all concretely documented in project research with specific hex values

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (Tailwind v3 is stable; `color-scheme` is a stable browser API; no fast-moving dependencies)
