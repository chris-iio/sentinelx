# Architecture Research

**Domain:** Dark-first design system for Flask/Jinja2 security tool (SentinelX v1.2)
**Researched:** 2026-02-25
**Confidence:** HIGH — patterns verified against Tailwind CSS official docs, Jinja2 templating docs, and production design system references (Vercel Geist, Linear, GitHub Primer)

---

## System Overview

The v1.2 design system sits entirely in the frontend layer. No backend changes. The architecture has three sub-layers:

```
┌─────────────────────────────────────────────────────────────┐
│                     Design Token Layer                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  CSS Custom Properties in :root (input.css)          │   │
│  │  Semantic tokens: --color-surface, --color-accent,   │   │
│  │  --color-text-primary, --color-border, etc.          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Tailwind Config (tailwind.config.js)                │   │
│  │  theme.extend.colors references CSS vars → generates │   │
│  │  utility classes: bg-surface, text-muted, etc.       │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                     Component Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  @layer base │  │ @layer comp. │  │ @layer util  │      │
│  │  (reset/html)│  │ (BEM classes)│  │ (Tailwind)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
├─────────────────────────────────────────────────────────────┤
│                     Template Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  base.html   │  │  partials/   │  │  macros/     │      │
│  │  (shell)     │  │  (include)   │  │  (reusable)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
├─────────────────────────────────────────────────────────────┤
│                     Build Layer                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Tailwind CLI: input.css → dist/style.css            │   │
│  │  (standalone binary, no Node.js required)            │   │
│  │  Font files: app/static/fonts/ → @font-face in CSS   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Design Token Architecture

### Decision: CSS Custom Properties at :root, Referenced in Tailwind Config

The existing codebase already uses CSS custom properties (CSS vars) in `:root` for design tokens. This is the correct pattern and should be extended, not replaced.

**The two-layer pattern (verified against Tailwind v3 docs and production systems):**

**Layer 1 — CSS custom properties in `input.css`:** Define the raw semantic values. These are the ground truth. They can be overridden at any selector scope without touching component markup.

**Layer 2 — Tailwind config maps names to CSS vars:** This generates utility classes (`bg-surface`, `text-muted`) that resolve at runtime via the CSS var. Components written with `bg-surface` automatically adopt theme changes.

**Why this over Tailwind `dark:` variants:** The `dark:` variant pattern doubles every color utility in the markup and requires toggling a `dark` class on `<html>`. For a tool that is always dark — no light mode — this adds zero value and creates double the markup. CSS vars at `:root` are simpler: define once, everything inherits.

**Confidence: HIGH** — verified against official Tailwind v3 docs, Vercel Geist system, and the nareshbhatia/tailwindcss-dark-mode-semantic-colors reference implementation.

### Semantic Color Token Vocabulary

The existing tokens in `input.css` are GitHub-flavored dark theme (good foundation). The v1.2 redesign refines the naming toward a more systematic semantic vocabulary aligned with Linear/Vercel quality:

```
Surface hierarchy (background layers):
  --color-bg-base         — body background (deepest, darkest)
  --color-bg-surface      — card/panel surfaces (one level up from base)
  --color-bg-raised       — elevated elements (dropdowns, tooltips, modals)
  --color-bg-overlay      — overlay/scrim backgrounds

Text:
  --color-text-primary    — body text, headings (high contrast)
  --color-text-secondary  — labels, captions, supporting text (muted)
  --color-text-disabled   — placeholder, explicitly disabled content
  --color-text-inverse    — text on colored/accent backgrounds

Borders:
  --color-border-default  — default borders, dividers
  --color-border-strong   — hover/focus borders, emphasized separators
  --color-border-subtle   — extremely subtle separators

Accent (emerald/teal brand color):
  --color-accent          — primary accent (emerald-500 range)
  --color-accent-muted    — accent at low opacity for backgrounds
  --color-accent-strong   — accent hover state

Status colors (security-specific, high importance):
  --color-danger          — malicious verdicts
  --color-danger-muted    — malicious backgrounds (low opacity)
  --color-warning         — suspicious verdicts
  --color-warning-muted   — suspicious backgrounds
  --color-success         — clean verdicts
  --color-success-muted   — clean backgrounds
  --color-neutral         — no-data / unknown verdicts
  --color-neutral-muted   — no-data backgrounds

IOC type accents (existing — keep, just rename for consistency):
  --color-ioc-ip          — IPv4/IPv6 type accent
  --color-ioc-domain      — domain type accent
  --color-ioc-url         — URL type accent
  --color-ioc-hash        — hash type accent (MD5/SHA1/SHA256)
  --color-ioc-cve         — CVE type accent

Interactive:
  --color-interactive-bg         — button/interactive element background
  --color-interactive-bg-hover   — hover state
  --color-interactive-fg         — text on interactive elements
```

### Tailwind Config Pattern for Semantic Tokens

```javascript
// tailwind.config.js
module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/static/**/*.js",
  ],
  safelist: [
    // ... (existing dynamic class safelist — keep unchanged)
  ],
  theme: {
    extend: {
      colors: {
        // Surface hierarchy
        "bg-base":     "var(--color-bg-base)",
        "bg-surface":  "var(--color-bg-surface)",
        "bg-raised":   "var(--color-bg-raised)",
        "bg-overlay":  "var(--color-bg-overlay)",

        // Text
        "text-primary":   "var(--color-text-primary)",
        "text-secondary": "var(--color-text-secondary)",
        "text-disabled":  "var(--color-text-disabled)",
        "text-inverse":   "var(--color-text-inverse)",

        // Borders
        "border-default": "var(--color-border-default)",
        "border-strong":  "var(--color-border-strong)",
        "border-subtle":  "var(--color-border-subtle)",

        // Accent
        "accent":         "var(--color-accent)",
        "accent-muted":   "var(--color-accent-muted)",
        "accent-strong":  "var(--color-accent-strong)",

        // Status
        "danger":          "var(--color-danger)",
        "danger-muted":    "var(--color-danger-muted)",
        "warning":         "var(--color-warning)",
        "warning-muted":   "var(--color-warning-muted)",
        "success":         "var(--color-success)",
        "success-muted":   "var(--color-success-muted)",
        "neutral-verdict": "var(--color-neutral)",
        "neutral-muted":   "var(--color-neutral-muted)",
      },
      fontFamily: {
        "ui":   ["Inter", "system-ui", "-apple-system", "sans-serif"],
        "mono": ["'JetBrains Mono'", "'Fira Code'", "Consolas", "monospace"],
      },
      borderRadius: {
        "sm":  "4px",
        "md":  "6px",
        "lg":  "8px",
        "xl":  "12px",
        "pill": "9999px",
      },
    },
  },
  plugins: [],
};
```

This gives utility classes like `bg-bg-surface`, `text-text-primary`, `border-border-default`. These are intentionally explicit — `bg-surface` would conflict with Tailwind's default `surface` if it existed, but the `bg-bg-*` and `text-text-*` pattern is unambiguous. Alternatively, use the existing pattern of referencing CSS vars directly in component classes.

**Simpler alternative (matches existing codebase pattern better):** Keep CSS vars referenced only in `@layer components` via `@apply` or direct `var()` references, and only extend Tailwind config for colors that need utility-class access in Jinja2 templates. This avoids the `bg-bg-surface` naming awkwardness and preserves the existing architecture.

**Recommendation:** Keep semantic tokens as CSS custom properties, used directly in `@layer components`. Only register colors in `tailwind.config.js` when a utility class needs to be applied in Jinja2 HTML markup (as opposed to CSS component classes). This matches the existing pattern and avoids verbose naming.

## Component Organization

### Decision: @apply-Based Component Classes in @layer components

The existing codebase already uses `@layer components` with BEM-style class names (`.ioc-card`, `.filter-btn`, `.btn-primary`). This is the correct approach for a Jinja2 app.

**Why `@apply` component classes instead of utility-first in templates:**

1. **Jinja2 templates are not components.** There is no component encapsulation in Jinja2 — the same `.ioc-card` markup appears in a loop, potentially 50+ times per page. Putting 15 utility classes inline on each card iteration makes templates illegible and creates a diff nightmare for every style change.

2. **Tailwind's own guidance:** Tailwind recommends extracting repeated patterns to `@apply` classes when using a templating language (as opposed to a JS component framework where the component file is the encapsulation boundary). This is directly the Jinja2 case.

3. **Existing test coverage assumes class names.** The Playwright E2E tests target CSS class names like `.ioc-card`, `.filter-btn`, `.verdict-label`. Utility-first would break these selectors or require `data-testid` sprawl.

**The mixed approach (what the codebase already does, which is correct):**

- `@layer components` — Named BEM classes for repeating structural patterns (cards, buttons, badges, filter pills, form elements)
- Tailwind utilities — Used directly in templates for one-off layout, spacing, and display helpers where a named class would be overkill

**Confidence: HIGH** — Tailwind's official docs on "Reusing Styles" explicitly recommend template partials and `@apply` for templating languages.

### Component Class Organization in input.css

Group component classes by page/feature, not by element type. The current organization is already correct. For v1.2:

```
@layer base {
  /* Reset, html, body, @font-face declarations */
}

@layer components {
  /* 1. Layout shells */
  .site-header, .site-main, .site-footer
  .header-inner, .site-nav

  /* 2. Shared UI primitives */
  .btn (base), .btn-primary, .btn-secondary, .btn-ghost
  .badge (base)
  .alert, .alert-error, .alert-warning, .alert-success

  /* 3. Form elements */
  .form-field, .form-label, .form-input
  .ioc-textarea
  .mode-toggle-* family

  /* 4. Input page */
  .page-index, .input-card
  .input-title, .input-subtitle

  /* 5. Results page */
  .page-results
  .results-header, .results-summary
  .verdict-dashboard, .verdict-dashboard-badge
  .filter-bar-*, .filter-btn, .filter-pill
  .ioc-cards-grid, .ioc-card, .ioc-card-header
  .ioc-value, .ioc-type-badge, .verdict-label
  .enrichment-* family

  /* 6. Settings page */
  .page-settings, .settings-card, .settings-section
  .input-group (for side-by-side input + button)

  /* 7. IOC type variants */
  .ioc-type-badge--{type} family
  .filter-pill--{type} family

  /* 8. Verdict variants */
  .verdict-label--{verdict} family
  .verdict-{verdict} family (enrichment badges)
  .filter-btn--{verdict}.filter-btn--active family
}
```

## Template Structure

### Current Structure (4 files, flat)

```
app/templates/
├── base.html      — shell (head, header, main, footer)
├── index.html     — input page
├── results.html   — results page (756 lines, complex)
└── settings.html  — settings page
```

### Recommended v1.2 Structure (partials for complex pages)

```
app/templates/
├── base.html                      — shell (MODIFIED: font preload, new header structure)
├── index.html                     — input page (MODIFIED: redesigned card layout)
├── results.html                   — results page (MODIFIED: new visual design)
├── settings.html                  — settings page (MODIFIED: new card design)
└── partials/
    ├── _ioc_card.html             — single IOC card (extracted from results.html loop)
    ├── _verdict_dashboard.html    — the malicious/suspicious/clean/no-data badges row
    ├── _filter_bar.html           — filter verdict + type pills + search input
    └── _enrichment_slot.html      — spinner + provider results (inside card)
```

**Rationale for partials:**

The results page is already 156 lines and growing. The `{% for ioc_type, iocs in grouped.items() %}{% for ioc in iocs %}` loop currently contains 30+ lines of HTML per card. Extracting `_ioc_card.html` as a partial via `{% include %}` does three things:

1. Makes `results.html` readable (the loop body is a single include line)
2. Gives the card a single source of truth for future style changes
3. Enables independent testing of the card structure

**Jinja2 include syntax (CSP-safe, no changes to backend):**

```jinja
{# In results.html — replace the inner loop body #}
{% for ioc in iocs %}
  {% include "partials/_ioc_card.html" %}
{% endfor %}
```

The included template has access to the same context as the parent (including `ioc`, `mode`, `job_id`).

**When not to use Jinja2 macros:** Macros add import boilerplate and are harder to read for simple includes. Use `{% include %}` for structural partials. Use macros only when the same pattern needs to render with different parameters passed explicitly (not from context) — which is rare in this codebase.

### base.html Changes for v1.2

The `base.html` shell needs these modifications:

1. **Font preload:** Add `<link rel="preload">` for Inter WOFF2 before the stylesheet link
2. **Class on `<html>`:** Consider adding `class="dark"` for future compatibility — not needed now since the tool is always dark, but harmless
3. **Block structure:** Add `{% block head_extra %}{% endblock %}` after the stylesheet link for page-specific meta/preload needs
4. **Header redesign:** The header will change structure significantly (logo, nav, possibly tagline position) — keep `{% block content %}` stable

```html
<!-- base.html sketch -->
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}SentinelX{% endblock %}</title>

    <!-- Font preload: must precede stylesheet to avoid FOUC -->
    <link rel="preload"
          href="{{ url_for('static', filename='fonts/inter-variable.woff2') }}"
          as="font" type="font/woff2" crossorigin>

    <link rel="stylesheet" href="{{ url_for('static', filename='dist/style.css') }}">
    {% block head_extra %}{% endblock %}
</head>
<body>
    <header class="site-header">
        <div class="header-inner">
            <!-- header content — redesigned in v1.2 -->
        </div>
    </header>

    <main class="site-main">
        {% block content %}{% endblock %}
    </main>

    <footer class="site-footer">
        <!-- footer content -->
    </footer>

    <script src="{{ url_for('static', filename='vendor/alpine.csp.min.js') }}" defer></script>
    <script src="{{ url_for('static', filename='main.js') }}" defer></script>
    {% block scripts_extra %}{% endblock %}
</body>
</html>
```

**CSP compatibility:** The `crossorigin` attribute on the font preload is mandatory for CORS compliance (browsers treat font requests as CORS). Flask serves from `'self'`, so no CSP changes are needed for self-hosted fonts — `font-src 'self'` is implied by `default-src 'self'`.

## Font Loading Strategy

### Decision: Self-Host Inter Variable Font

Inter is the standard choice for Linear/Vercel-quality SaaS UI. Inter Variable provides the full weight range (100-900) in a single ~260KB WOFF2 file, avoiding multiple font requests.

**File placement:**

```
app/static/
├── fonts/
│   ├── inter-variable.woff2       — UI font (full variable weight range)
│   └── jetbrains-mono-variable.woff2  — monospace font for IOC values
├── vendor/
│   └── alpine.csp.min.js
├── dist/
│   └── style.css
└── main.js
```

**@font-face declaration in input.css:**

```css
@layer base {
    @font-face {
        font-family: 'Inter';
        src: url('/static/fonts/inter-variable.woff2') format('woff2-variations');
        font-weight: 100 900;
        font-style: normal;
        font-display: swap;
    }

    @font-face {
        font-family: 'JetBrains Mono';
        src: url('/static/fonts/jetbrains-mono-variable.woff2') format('woff2-variations');
        font-weight: 100 800;
        font-style: normal;
        font-display: swap;
    }
}
```

**Why `font-display: swap`:** Prevents render-blocking. The browser shows system font immediately, then swaps to Inter when loaded. For a local tool, the font is cached after the first load — no meaningful flash.

**Why not Google Fonts CDN:** CSP `default-src 'self'` blocks external font URLs. Even if the CSP were relaxed, loading from an external CDN violates the security posture for a tool that intentionally makes no external calls in offline mode. Self-hosted fonts are consistent with the existing vendor/ pattern for Alpine.js.

**Font sources (download once, commit to repo):**

- Inter Variable: https://github.com/rsms/inter/releases (SIL OFL license, free)
- JetBrains Mono Variable: https://www.jetbrains.com/legalnotice/fonts/ (SIL OFL license, free)

**Confidence: HIGH** — WOFF2 variable fonts + `font-display: swap` is established best practice; CSP font-src behavior verified against MDN.

## Responsive Design Approach

### Decision: Desktop-First, Minimal Mobile Accommodations

PROJECT.md explicitly states: "Mobile or responsive design — desktop browser on analyst workstation" is out of scope. The tool runs on a local machine. However, the existing CSS already includes a `@media (max-width: 640px)` block with minor adjustments (padding reduction, stack form options vertically).

**v1.2 approach:**

- Design at 1280px minimum viewport width
- Keep the existing `@media (max-width: 640px)` fallbacks for stack form elements — they prevent horizontal scroll at smaller sizes without adding complexity
- Do not add new breakpoints or mobile-specific layouts
- The `max-width: 960px` layout container can expand to `max-width: 1200px` for v1.2 to make better use of analyst desktop screens

**Why not mobile-first:** The tool's use case (analyst workstation, jump box) means the design decisions should optimize for a wide desktop viewport. Mobile-first would mean designing the worst-case viewport first and scaling up — the opposite of what this tool needs.

## Migration Strategy: Light to Dark Transition

### The Existing Situation

The existing code is already dark theme. Every color value in `:root` is a dark palette value. The CSS vars infrastructure is in place. The v1.2 migration is a **refinement and elevation** of the existing dark theme, not a light-to-dark conversion.

**What actually needs to change:**

1. **Color palette update:** Replace GitHub-dark inspired values with Linear/Vercel-quality emerald/teal-accented palette. The variable names stay similar, the hex values change.

2. **Tailwind config extension:** Add semantic color names to `theme.extend.colors` so Jinja2 templates can use `bg-surface` utilities where needed (currently the CSS vars are only used in `@layer components`, not directly in templates).

3. **Typography upgrade:** Replace the system font stack with self-hosted Inter. Swap `Fira Code` / `JetBrains Mono` priority.

4. **Visual refinements:** Spacing, border radius, shadow depth, glassmorphism/blur effects where appropriate (CSS only, no JS).

5. **Template restructuring:** Extraction of partials, header/footer redesign, card component elevation.

### Migration Build Order

This order respects dependencies and allows validation at each step:

**Step 1 — Font infrastructure (no visible change yet)**
- Download Inter + JetBrains Mono WOFF2 variable fonts
- Add to `app/static/fonts/`
- Add `@font-face` to `@layer base` in `input.css`
- Add preload links to `base.html`
- Verify: fonts load, no CSP errors in browser console
- Files: `input.css`, `base.html`, `app/static/fonts/`

**Step 2 — Color token redesign (visible change, no structural changes)**
- Update CSS custom property values in `:root` (change hex values, rename for consistency)
- Update `tailwind.config.js` to extend colors with semantic token names
- Run `make css` to regenerate `dist/style.css`
- Verify: existing component classes still apply (they now reference updated vars), all pages render correctly
- Files: `input.css`, `tailwind.config.js`

**Step 3 — Base component style elevation (visible refinements)**
- Update `@layer components` classes to use refined spacing, radius, shadows
- Update the existing component styles to reference new token names
- No template changes yet — class names stay the same
- Run `make css` → verify
- Files: `input.css`

**Step 4 — Template partials extraction (structural, no visual change)**
- Extract `_ioc_card.html`, `_verdict_dashboard.html`, `_filter_bar.html`, `_enrichment_slot.html`
- Update `results.html` to use `{% include %}` for extracted partials
- Verify: results page renders identically to before (E2E tests should pass)
- Files: new `app/templates/partials/` directory + updated `results.html`

**Step 5 — Header/footer redesign**
- Redesign `base.html` header (new logo treatment, nav positioning)
- Update `.site-header`, `.header-inner`, `.site-nav` component styles
- Files: `base.html`, `input.css`

**Step 6 — Input page redesign**
- Redesign input card to Linear/Vercel quality (refined spacing, typography, improved mode toggle)
- Update `index.html` and relevant component classes
- Files: `index.html`, `input.css`

**Step 7 — Results page redesign**
- Redesign IOC cards, filter bar, verdict dashboard
- Work with partials extracted in Step 4
- Files: `results.html`, partials, `input.css`

**Step 8 — Settings page redesign**
- Redesign settings card, form input, save button
- Files: `settings.html`, `input.css`

**Step 9 — Tailwind config safelist validation**
- Verify all dynamically-applied classes (verdict colors, IOC type badges) remain in the safelist
- Run full E2E test suite
- Files: `tailwind.config.js`

## Build Pipeline

### Current Pipeline (no changes required)

```makefile
# Current Makefile — no changes needed for v1.2
css:
    $(TAILWIND) -i app/static/src/input.css -o app/static/dist/style.css --minify

css-watch:
    $(TAILWIND) -i app/static/src/input.css -o app/static/dist/style.css --watch

build: css
```

The Tailwind standalone CLI v3.4.17 handles everything needed:

- CSS custom properties: pass through as-is (no processing required)
- `@font-face` in `@layer base`: supported
- `@apply` in `@layer components`: supported
- Content scanning of templates and JS for utility class extraction: configured via `content` in `tailwind.config.js`

**Tailwind v3 vs v4 consideration:** The project uses Tailwind v3 (standalone CLI v3.4.17). The semantic token approach described here works in v3. Tailwind v4 (released January 2025) uses `@theme` in CSS instead of `tailwind.config.js` — but migrating to v4 is out of scope for this milestone. The v3 approach is stable and compatible.

**One optional addition for development:** Add a `fonts` Makefile target documenting the font download process:

```makefile
## Document font source (run once, files committed to repo)
fonts-info:
    @echo "Download Inter Variable from: https://github.com/rsms/inter/releases"
    @echo "Download JetBrains Mono from: https://www.jetbrains.com/legalnotice/fonts/"
    @echo "Place .woff2 files in: app/static/fonts/"
```

## Integration Points

### New Files Required

| File | Purpose | Notes |
|------|---------|-------|
| `app/static/fonts/inter-variable.woff2` | Inter variable font | Download from rsms/inter GitHub |
| `app/static/fonts/jetbrains-mono-variable.woff2` | JetBrains Mono | Download from JetBrains |
| `app/templates/partials/_ioc_card.html` | IOC card partial | Extracted from results.html loop |
| `app/templates/partials/_verdict_dashboard.html` | Verdict dashboard partial | Extracted from results.html |
| `app/templates/partials/_filter_bar.html` | Filter bar partial | Extracted from results.html |
| `app/templates/partials/_enrichment_slot.html` | Enrichment slot partial | Extracted from results.html |

### Modified Files

| File | Change Type | Notes |
|------|------------|-------|
| `app/static/src/input.css` | Major update | New color tokens, @font-face, component style elevation |
| `tailwind.config.js` | Extend | Add semantic colors to theme.extend.colors |
| `app/templates/base.html` | Significant | Font preload, head_extra block, header redesign |
| `app/templates/index.html` | Major redesign | Input card elevation |
| `app/templates/results.html` | Partial extraction + redesign | Card loop replaced with include |
| `app/templates/settings.html` | Moderate redesign | Card, form, input-group |
| `Makefile` | Optional | fonts-info target (documentation only) |
| `app/static/dist/style.css` | Regenerated | Build artifact, committed after each css build |

### CSP Compatibility Matrix

| Resource | CSP Directive | Status |
|----------|--------------|--------|
| `dist/style.css` | `style-src 'self'` | OK — same-origin |
| `fonts/*.woff2` | `font-src 'self'` | OK — same-origin (font-src falls back to default-src) |
| `main.js` | `script-src 'self'` | OK — unchanged |
| `vendor/alpine.csp.min.js` | `script-src 'self'` | OK — unchanged |
| Inline `font-display` CSS | n/a | In external stylesheet, not inline |
| No external CDN fonts | — | Required: CSP blocks external font URLs |

**No CSP header changes are needed.** The existing `default-src 'self'` policy covers self-hosted fonts because `font-src` defaults to `default-src` when not explicitly set.

### Existing Test Compatibility

The Playwright E2E tests target:

- CSS class names (`.ioc-card`, `.filter-btn`, `.verdict-label`, etc.)
- `data-*` attributes (`data-verdict`, `data-ioc-type`, `data-filter-verdict`)
- Element IDs (`#filter-root`, `#ioc-cards-grid`, `#mode-toggle-widget`)

**Migration rule:** Class names, IDs, and data attributes must not change during v1.2. Only CSS _styles_ change. All existing Playwright selectors will continue to work without modification. New or renamed classes should have their selectors updated in `tests/e2e/` if any are added.

## Anti-Patterns

### Anti-Pattern 1: Utility-First in Jinja2 Loops

**What people do:** Apply 12+ Tailwind utility classes directly in Jinja2 template markup for repeating elements.

```jinja
{# BAD: utility classes on a component repeated 50 times #}
<div class="bg-gray-800 border border-gray-700 rounded-lg p-3 border-l-4 transition-all">
```

**Why it's wrong:** When the design needs to change (border radius, padding, background shade), every template file must be edited. The Tailwind JIT scanner must index 50 copies of the same class string. Template diffs are huge and noisy.

**Do this instead:** Define `.ioc-card` in `@layer components` with `@apply` or CSS var references. Use one meaningful class name in the template:

```jinja
{# GOOD: single semantic class name #}
<div class="ioc-card" data-verdict="{{ ioc.verdict }}">
```

### Anti-Pattern 2: Hardcoded Hex Values in Component Classes

**What people do:** Write `color: #f85149` directly in component class definitions instead of using the design token.

**Why it's wrong:** When the palette changes (e.g., shifting from GitHub-red to a slightly different red), every hardcoded hex must be found and updated. Two hex values that look similar may diverge.

**Do this instead:** Always reference CSS custom properties:

```css
/* BAD */
.verdict-label--malicious { color: #f85149; }

/* GOOD */
.verdict-label--malicious { color: var(--color-danger); }
```

### Anti-Pattern 3: Duplicating Verdict Color Logic

**What people do:** Define verdict colors in CSS, then redefine equivalent values in JavaScript for dynamic DOM updates (enrichment rendering in `main.js`).

**Why it's wrong:** The two definitions will inevitably drift. CSS shows one shade of red, JS renders a slightly different shade.

**Do this instead:** In `main.js`, when building verdict badge elements dynamically, apply the same CSS class names used in Jinja2 templates (`.verdict-malicious`, `.verdict-label--malicious`). The CSS vars do the color work. JS only adds the class, never sets colors directly via `element.style.color`.

### Anti-Pattern 4: Loading Fonts from Google Fonts CDN

**What people do:** Add `<link href="https://fonts.googleapis.com/css2?family=Inter">` to the template head.

**Why it's wrong:**
1. CSP `default-src 'self'` blocks the external stylesheet request entirely — no font loads
2. Fixes require relaxing CSP with `style-src` and `font-src` additions, weakening the security posture
3. In offline mode, the tool should have zero dependency on external network

**Do this instead:** Self-host font files in `app/static/fonts/`. This is the only CSP-compatible approach.

### Anti-Pattern 5: Omitting `crossorigin` on Font Preload

**What people do:** Add a `<link rel="preload">` for the font file without the `crossorigin` attribute.

**Why it's wrong:** Browsers treat font requests as CORS even for same-origin fonts. Without `crossorigin` on the preload, the browser makes two requests: the preload (discarded) and the actual fetch triggered by `@font-face`. The preload provides no benefit.

**Do this instead:**

```html
<!-- WRONG: crossorigin missing, preload is wasted -->
<link rel="preload" href="/static/fonts/inter-variable.woff2" as="font" type="font/woff2">

<!-- CORRECT: crossorigin required for font preloads -->
<link rel="preload" href="..." as="font" type="font/woff2" crossorigin>
```

### Anti-Pattern 6: Upgrading to Tailwind v4 Mid-Milestone

**What people do:** See that Tailwind v4 exists and decide to upgrade as part of the design refresh.

**Why it's wrong:** Tailwind v4 has a completely different configuration model (`@theme` CSS directive replaces `tailwind.config.js`), a new CLI binary, and breaking changes to how utilities are generated. This upgrade is a separate project, not a v1.2 task.

**Do this instead:** Complete v1.2 on Tailwind v3 (the existing, stable CLI). The v3 configuration approach described in this document produces full-quality output. Migrate to v4 in a dedicated milestone after v1.2 is stable.

## Sources

- Tailwind CSS v3 — Dark Mode configuration: https://v3.tailwindcss.com/docs/dark-mode (HIGH confidence — official v3 docs)
- Tailwind CSS — Reusing Styles (when to use @apply): https://tailwindcss.com/docs/reusing-styles (HIGH confidence — official docs)
- Tailwind CSS — Adding Custom Styles: https://tailwindcss.com/docs/adding-custom-styles (HIGH confidence — official docs)
- Tailwind CSS — Theme configuration: https://tailwindcss.com/docs/theme (HIGH confidence — official docs)
- Dark Mode with Design Tokens in Tailwind CSS: https://www.richinfante.com/2024/10/21/tailwind-dark-mode-design-tokens-themes-css (MEDIUM confidence — verified against official Tailwind docs)
- Semantic color tokens (nareshbhatia demo): https://github.com/nareshbhatia/tailwindcss-dark-mode-semantic-colors (MEDIUM confidence — reference implementation, community-sourced)
- Vercel Geist color token naming: https://vercel.com/geist/colors (HIGH confidence — official Vercel design system)
- Flask Templates (Jinja2 includes and macros): https://flask.palletsprojects.com/en/stable/templating/ (HIGH confidence — official Flask 3.1 docs)
- Jinja2 Template Inheritance and Includes: https://jinja.palletsprojects.com/en/stable/templates/ (HIGH confidence — official Jinja2 docs)
- Self-hosting web fonts guide: https://tristanguest.hashnode.dev/a-practical-guide-to-self-hosting-web-fonts (MEDIUM confidence — practical guide, verified against MDN font-display)
- Inter Variable font: https://github.com/rsms/inter/releases (HIGH confidence — official Inter font repo)
- JetBrains Mono: https://www.jetbrains.com/legalnotice/fonts/ (HIGH confidence — official JetBrains page)
- Font preload crossorigin requirement: https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes/rel/preload#cors-enabled_fetches (HIGH confidence — MDN official)
- How we redesigned the Linear UI: https://linear.app/now/how-we-redesigned-the-linear-ui (MEDIUM confidence — product blog, design reference)
- Tailwind CSS v4.0 release (context only, not adopting): https://tailwindcss.com/blog/tailwindcss-v4 (HIGH confidence — official Tailwind blog)
- Semantic Tailwind color setup: https://www.subframe.com/blog/how-to-setup-semantic-tailwind-colors (MEDIUM confidence — community blog, pattern verified against Tailwind docs)

---
*Architecture research for: Dark-first design system — SentinelX v1.2 Modern UI Redesign*
*Researched: 2026-02-25*
