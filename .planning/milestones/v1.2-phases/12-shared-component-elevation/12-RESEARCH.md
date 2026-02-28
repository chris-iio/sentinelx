# Phase 12: Shared Component Elevation — Research

**Researched:** 2026-02-28
**Domain:** CSS component design systems — verdict badge unification, focus ring standardization, button variants, backdrop-filter, Jinja2 macro system, header/footer typography
**Confidence:** HIGH

---

## Summary

Phase 12 is a CSS + Jinja2 template surgery phase. All seven requirements operate on components that already exist in `app/static/src/input.css` — no new libraries, no backend changes. The design token system established in Phase 11 (`:root` with verdict triple tokens, `--accent-interactive`, `--font-ui`, button tokens) provides the complete vocabulary for this phase. Every requirement resolves to a pattern of: identify existing component CSS, rewrite it to use the correct token(s), and verify the visual result.

The most consequential finding: the codebase has **two parallel verdict badge systems** (`verdict-label--*` used on IOC cards in Jinja2 templates, and `verdict-badge verdict-*` applied by JS in enrichment slots) that both need the tinted-background + colored-border + colored-text treatment. COMP-01 must address both. The "pending" badge state in the requirement refers to the `verdict-label--no_data` shown on cards before enrichment begins, since JS later replaces it with the enriched verdict. There is no standalone "pending" CSS class — the initial card state is `no_data` in the Jinja2 template.

The focus ring situation (COMP-02) is straightforward but must be systematic: three elements currently use `outline: none; box-shadow: 0 0 0 3px rgba(...)` which is invisible to Windows High Contrast mode and violates COMP-02. These need to be replaced with `outline: 2px solid var(--accent-interactive); outline-offset: 2px` on `:focus-visible`. The filter bar frosted-glass effect (COMP-05) requires only a one-line CSS addition (`backdrop-filter: blur(12px)`) plus changing the background from opaque `var(--bg-primary)` to a semi-transparent equivalent. The Heroicons macro (COMP-06) requires creating `app/templates/macros/icons.html` and adding `{% from ... import ... %}` to templates that use icons.

**Primary recommendation:** Work through the requirements in dependency order: COMP-01 (verdict badges, no side effects) → COMP-02 (focus rings, affects all interactive elements globally) → COMP-03 (button variants, adds ghost variant) → COMP-04 (form elements via @tailwindcss/forms) → COMP-05 (filter bar backdrop) → COMP-06 (icon macro, new file) → COMP-07 (header/footer typography). Run `make css` after each CSS change. Run the unit test suite (`pytest tests/ --ignore=tests/e2e`) after any template changes.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| COMP-01 | Verdict badges unified — all five states use tinted-background + colored-border + colored-text pattern (eliminate solid amber outlier) | Two badge systems exist: `verdict-label--*` (Jinja2 template, IOC card header) and `verdict-badge verdict-*` (JS-applied, enrichment slots). Both systems currently lack the `border` property on some states. The "five states" are: malicious, suspicious, clean, no_data (no record), and error (pending enrichment renders as no_data initially, then updates). `verdict-suspicious` currently has `background-color` and `color` only — the "solid amber" mentioned in the requirement refers to the legacy pre-Phase-11 state; post-Phase-11 tokens already define the tinted bg, but the `.verdict-badge .verdict-*` classes (lines 916–919 in input.css) are missing `border: 1px solid var(--verdict-*-border)`. |
| COMP-02 | Focus rings standardized — `outline: 2px solid var(--accent); outline-offset: 2px` on `:focus-visible`, replacing low-opacity box-shadow focus indicators | Three elements currently use `outline: none; box-shadow: 0 0 0 3px rgba(74,158,255,...)`: `.ioc-textarea:focus` (line 271), `.mode-toggle-track:focus` (line 314), `.filter-search-input:focus` (line 707). All must change to `:focus-visible` selector and `outline: 2px solid var(--accent-interactive)`. All buttons, filter pills, filter buttons, nav links, and copy buttons also need a global `:focus-visible` rule. Buttons currently have `outline: none` only via the browser UA reset. |
| COMP-03 | Button component styles — primary (emerald), secondary (zinc), and ghost variants with hover/active/disabled states and 150ms transitions | Primary (`btn-primary`) and secondary (`btn-secondary`) exist. Ghost variant is missing entirely. Ghost = transparent background + 1px border (border-color: `var(--border-default)`) + `var(--text-secondary)` color; hover shifts to `var(--border-hover)` + `var(--text-primary)`. Transition should be `150ms ease` (already used for bg-color in `.btn`; add `color` to the transition list). `btn-primary` and `btn-secondary` need disabled states added (currently `btn-primary:disabled` exists but `btn-secondary` does not). |
| COMP-04 | Form element styling via `@tailwindcss/forms` — textarea, text inputs, and select elements reset with dark-theme-appropriate borders and focus states | `@tailwindcss/forms` is already activated in `tailwind.config.js`. The plugin is already in standalone CLI. The reset needs overrides because `@tailwindcss/forms` applies light-mode defaults. The `.ioc-textarea` and `.form-input` (settings API key input) need explicit `background-color`, `border-color`, `color`, and `focus:border-color` that use token values. The settings `<input type="password">` class is `form-input` (currently no CSS rule for this class in `input.css`). A `@layer components { .form-input { ... } }` block must be added. |
| COMP-05 | Sticky filter bar uses `backdrop-filter: blur(12px)` with semi-transparent zinc-950 background | `.filter-bar-wrapper` currently uses `background-color: var(--bg-primary)` (opaque, #09090b). Needs: `background-color: rgba(9, 9, 11, 0.85)` + `backdrop-filter: blur(12px)` + `-webkit-backdrop-filter: blur(12px)` (Safari). The opaque background blocks the frosted glass effect — it must become semi-transparent. `z-index: 10` already set. |
| COMP-06 | Heroicons icon macro created (`templates/macros/icons.html`) for reusable inline SVG icons across all pages | No `app/templates/macros/` directory exists yet. Heroicons v2 uses a consistent SVG structure: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">`. The macro file should define `{% macro icon(name, class="") %}` with SVG paths for each icon needed. Phase 12 uses: a shield icon (for logo/branding) and a settings/cog icon for nav. Later phases (13, 14) will need more icons. Phase 12 scope: create the macro file and wire up `{% from "macros/icons.html" import icon %}` in `base.html`. Apply icon macro to header brand name and nav. |
| COMP-07 | Header/footer redesigned with updated typography, spacing, and emerald accent treatment on the brand name | The `.site-logo` currently uses `var(--font-mono)` — this should switch to `var(--font-ui)` with `font-weight: var(--weight-heading)` (600). The brand name "SentinelX" should have the first part or full name styled with `color: var(--accent)` (emerald). The `.site-tagline` already uses `var(--text-secondary)`. Footer text should update from the Phase 1 placeholder copy. Nav links get `:focus-visible` rings from COMP-02. The `header-inner` may need `gap` adjustment for better visual hierarchy. |
</phase_requirements>

---

## Standard Stack

### Core (zero new installs required)

| Component | Version | Purpose | Status |
|-----------|---------|---------|--------|
| Tailwind CSS standalone CLI | v3.4.17 | Compile `input.css` → `dist/style.css` | `./tools/tailwindcss`, run via `make css` |
| `@tailwindcss/forms` | Bundled in standalone CLI | Form element base reset for dark theme | Already activated in `tailwind.config.js` |
| Heroicons v2 | Inline SVG (no package) | Icon system via Jinja2 macros | Paths copied directly from heroicons.com — zero install |
| Jinja2 | Flask's template engine | Macro system via `{% macro %}` and `{% from ... import %}` | Already in use |
| pytest + Playwright | Existing test suite | Regression gate after template changes | `pytest tests/` and `pytest tests/e2e/` |

### Supporting

| Component | Purpose | When to Use |
|-----------|---------|-------------|
| Browser DevTools | Visual verification of focus rings, backdrop blur, font rendering | After each CSS change — inspect computed styles |
| `make css` | Rebuild `dist/style.css` from `input.css` | After every CSS edit |
| `make css-watch` | Auto-rebuild during iterative development | During active CSS editing sessions |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inline SVG Heroicons via Jinja2 macro | Heroicons npm package + build step | npm adds build complexity; CSP `default-src 'self'` blocks external SVG sprites; inline SVG is the correct approach for this stack |
| `:focus-visible` | `:focus` | `:focus` shows rings on mouse click (noisy UX); `:focus-visible` shows only on keyboard nav — browser support is 97%+ as of 2024 |
| `rgba(9, 9, 11, 0.85)` for blur bg | CSS `color-mix()` | `color-mix()` has broader use patterns but rgba is simpler and universally supported |

**Installation:** None needed. `make css` is the only build step.

---

## Architecture Patterns

### Project File Structure for Phase 12

```
app/
├── static/
│   └── src/
│       └── input.css          # All CSS changes happen here
└── templates/
    ├── base.html              # Header/footer + icon macro import (COMP-07, COMP-06)
    ├── macros/
    │   └── icons.html         # New file — Jinja2 icon macro (COMP-06)
    ├── index.html             # No changes needed in Phase 12
    ├── results.html           # No changes in Phase 12 (Phase 13 scope)
    └── settings.html          # No changes in Phase 12 (Phase 14 scope)
```

### Pattern 1: Verdict Badge Completeness

**What:** All `.verdict-*` and `.verdict-label--*` CSS classes must have all three tokens applied.

**Current state (the gap):**
```css
/* BROKEN — missing border */
.verdict-malicious  { background-color: var(--verdict-malicious-bg);  color: var(--verdict-malicious-text); }
```

**Correct pattern (tinted-bg + colored-border + colored-text):**
```css
/* CORRECT */
.verdict-malicious  {
    background-color: var(--verdict-malicious-bg);
    color: var(--verdict-malicious-text);
    border: 1px solid var(--verdict-malicious-border);
}
```

This applies to BOTH badge systems:
1. `.verdict-label--*` (Jinja2 template, lines 798–802 in input.css) — already has border ✓
2. `.verdict-badge .verdict-*` (JS-applied, lines 916–919) — **missing border** ✗

The "five states" with pending clarification:
- malicious, suspicious, clean, no_data → explicit CSS classes in both systems
- "pending" (COMP-01 terminology) = the `verdict-label--no_data` shown before enrichment arrives; rendered in `results.html` as `<span class="verdict-label verdict-label--no_data">NO DATA</span>`. No separate "pending" CSS class is needed.
- error → `.verdict-error` / `.verdict-label--error` must also get the triple pattern

### Pattern 2: Focus Ring Global Rule

**What:** A single `@layer base` rule that applies teal outline to all interactive elements on keyboard focus.

**Pattern:**
```css
@layer base {
    :focus-visible {
        outline: 2px solid var(--accent-interactive);
        outline-offset: 2px;
    }
}
```

Then remove `outline: none; box-shadow: 0 0 0 3px rgba(...)` from the three component-level overrides (`.ioc-textarea:focus`, `.mode-toggle-track:focus`, `.filter-search-input:focus`) and replace with `:focus-visible` versions that only add the teal border-color shift.

**Why global rule:** Adding per-component `:focus-visible` rules risks missing elements. A global base rule catches everything including dynamically added elements. Override only where needed (e.g., textarea gets border-color shift on focus in addition to the outline).

### Pattern 3: Ghost Button Variant

**What:** Third button variant — transparent background, border, secondary text color.

```css
.btn-ghost {
    background-color: transparent;
    color: var(--text-secondary);
    border-color: var(--border-default);
    transition: background-color 150ms ease, border-color 150ms ease, color 150ms ease;
}

.btn-ghost:hover:not(:disabled) {
    background-color: var(--bg-hover);
    border-color: var(--border-hover);
    color: var(--text-primary);
}

.btn-ghost:disabled {
    opacity: 0.4;
    cursor: not-allowed;
}
```

### Pattern 4: Jinja2 Icon Macro

**What:** Centralized inline SVG delivery via Jinja2 macro.

**File:** `app/templates/macros/icons.html`

```jinja2
{% macro icon(name, class="w-4 h-4", aria_hidden="true") %}
  {% if name == "shield" %}
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"
       class="{{ class }}" aria-hidden="{{ aria_hidden }}">
    <path fill-rule="evenodd" d="M12 1.5a5.25 5.25 0 0 0-5.25 5.25v3a3 3 0 0 0-3 3v6.75a3 3 0 0 0 3 3h10.5a3 3 0 0 0 3-3v-6.75a3 3 0 0 0-3-3v-3c0-2.9-2.35-5.25-5.25-5.25Zm3.75 8.25v-3a3.75 3.75 0 1 0-7.5 0v3h7.5Z" clip-rule="evenodd"/>
  </svg>
  {% endif %}
  {# Additional icons added as needed #}
{% endmacro %}
```

**Usage in template:**
```jinja2
{% from "macros/icons.html" import icon %}
{{ icon("shield", class="w-5 h-5 text-emerald-500") }}
```

**Note:** Heroicons v2 paths should be pulled from the official source (heroicons.com or the GitHub repo) — do not hand-write SVG paths.

### Pattern 5: Frosted Glass Filter Bar

**What:** Semi-transparent background + backdrop blur for the sticky filter bar.

```css
.filter-bar-wrapper {
    position: sticky;
    top: 0;
    z-index: 10;
    background-color: rgba(9, 9, 11, 0.85);   /* was: var(--bg-primary) — opaque */
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);        /* Safari */
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1rem;
}
```

**Critical:** If the background stays fully opaque (`var(--bg-primary)` = `#09090b`), the blur effect is invisible — the background completely hides what's behind it. Must use `rgba(9, 9, 11, 0.85)` or equivalent semi-transparent value.

### Anti-Patterns to Avoid

- **Removing border from `.verdict-label--*` classes:** They already have the correct triple pattern — only the `.verdict-badge .verdict-*` classes need the border added. Do not break what works.
- **Using `:focus` instead of `:focus-visible`:** `:focus` shows rings on mouse clicks, creating visual noise. Always use `:focus-visible` for ring visibility.
- **Hardcoded hex colors in component rules:** Every color must reference a `var(--token)`. No `#10b981` in component CSS — use `var(--accent)`.
- **Writing Heroicons SVG paths from memory:** SVG paths must be copied from the official Heroicons v2 source — the paths are complex and any error produces broken icons.
- **Making `outline: none` the browser default approach:** The Tailwind `@tailwindcss/forms` plugin may add its own focus styles. Inspect computed styles after `make css` to verify the focus ring chain.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Icon delivery | Custom SVG build pipeline | Jinja2 macro with inline SVG strings | CSP `default-src 'self'` blocks external SVGs; npm build step unnecessary for this scale |
| Focus ring management | Per-component focus rules | Single `@layer base :focus-visible` rule | 15+ interactive elements — per-component approach will miss some; global rule is DRY and complete |
| Color opacity | Opacity CSS property on elements | `rgba()` values in `background-color` | `opacity` affects all children including text; use `rgba()` on background only |

**Key insight:** This phase is entirely CSS refinement + Jinja2 template additions. The design system from Phase 11 supplies all the tokens. Do not introduce any new design decisions — use what the tokens define.

---

## Common Pitfalls

### Pitfall 1: Two Badge Systems — Missing One

**What goes wrong:** Fixing `.verdict-label--*` but forgetting `.verdict-badge .verdict-*`, or vice versa. Result: inconsistent appearance between IOC card headers (Jinja2) and enrichment result rows (JS-rendered).

**Why it happens:** They look similar in the UI but are different CSS classes applied by different mechanisms (Jinja2 at render time vs JS at runtime).

**How to avoid:** Treat COMP-01 as two sub-tasks — one for each badge system. Verify both in the browser by (1) viewing offline results (card headers) and (2) viewing online results after enrichment (enrichment slot badges).

**Warning signs:** Inconsistent border on badges between card header and enrichment slot areas.

### Pitfall 2: backdrop-filter Not Visible on Opaque Background

**What goes wrong:** Adding `backdrop-filter: blur(12px)` but leaving `background-color: var(--bg-primary)` fully opaque — the blur is visually invisible.

**Why it happens:** `backdrop-filter` blurs what's *behind* the element; if the background is `#09090b` (fully opaque), nothing bleeds through regardless of blur value.

**How to avoid:** Always pair `backdrop-filter` with a semi-transparent `background-color: rgba(...)`. The alpha should be 0.80–0.90 to maintain readability while showing the blur effect.

**Warning signs:** Filter bar looks identical before and after adding the CSS change.

### Pitfall 3: @tailwindcss/forms Overriding Custom Focus Styles

**What goes wrong:** `@tailwindcss/forms` injects its own `box-shadow` focus ring on form elements, which may override the teal `outline` set by the global `:focus-visible` rule depending on CSS specificity and layer order.

**Why it happens:** `@tailwindcss/forms` applies styles at the utility level. The plugin uses `--tw-ring-*` CSS variables for box-shadow rings.

**How to avoid:** After `make css`, open DevTools and inspect the computed focus styles on `.ioc-textarea:focus-visible` and `.filter-search-input:focus-visible`. If the box-shadow persists, add an explicit `box-shadow: none` to the component rule and let the `outline` be the only focus indicator.

**Warning signs:** Blue box-shadow visible on textarea focus instead of (or in addition to) the teal outline.

### Pitfall 4: Jinja2 Macro Import Path

**What goes wrong:** Using a wrong import path for the icon macro, causing Jinja2 `TemplateNotFound` error at runtime.

**Why it happens:** Jinja2 template paths are relative to the templates root. The import must be `{% from "macros/icons.html" import icon %}`, NOT `{% from "./macros/icons.html" %}` or `{% from "templates/macros/icons.html" %}`.

**How to avoid:** Test macro import in `base.html` first — all pages extend `base.html`, so a single broken import fails every page. Verify the Flask dev server starts without error after adding the import.

**Warning signs:** `TemplateNotFound: macros/icons.html` in Flask logs.

### Pitfall 5: :focus vs :focus-visible Breaking Tests

**What goes wrong:** E2E tests that check focus state (if any) may use `.focus()` programmatic focus which triggers `:focus` but not `:focus-visible` in some browsers. Playwright's `focus()` method does trigger `:focus-visible` in Chromium but behavior varies.

**Why it happens:** `:focus-visible` is determined heuristically by the browser based on input modality (keyboard vs mouse). Playwright simulates keyboard focus when using `.press('Tab')` but may not when using `.focus()` directly.

**How to avoid:** E2E tests for focus rings should use `page.keyboard.press('Tab')` to simulate keyboard navigation, not `.focus()` method calls.

**Warning signs:** Focus ring visible manually but not in automated screenshot tests.

---

## Code Examples

Verified patterns from the existing codebase and CSS standards:

### COMP-01: Add Border to Enrichment Badge Classes

```css
/* Source: existing input.css lines 905–919, needs border added */
.verdict-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 2rem;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    border: 1px solid transparent;  /* base transparent border for layout stability */
}

.verdict-malicious  {
    background-color: var(--verdict-malicious-bg);
    color: var(--verdict-malicious-text);
    border-color: var(--verdict-malicious-border);
}
.verdict-suspicious {
    background-color: var(--verdict-suspicious-bg);
    color: var(--verdict-suspicious-text);
    border-color: var(--verdict-suspicious-border);
}
.verdict-clean      {
    background-color: var(--verdict-clean-bg);
    color: var(--verdict-clean-text);
    border-color: var(--verdict-clean-border);
}
.verdict-no_data    {
    background-color: var(--verdict-no-data-bg);
    color: var(--verdict-no-data-text);
    border-color: var(--verdict-no-data-border);
}
.verdict-error      {
    background-color: var(--verdict-error-bg);
    color: var(--verdict-error-text);
    border-color: var(--verdict-error-border);
}
```

### COMP-02: Global Focus Ring + Per-Component Cleanup

```css
/* In @layer base */
:focus-visible {
    outline: 2px solid var(--accent-interactive);
    outline-offset: 2px;
}

/* Replace existing .ioc-textarea:focus with :focus-visible */
.ioc-textarea:focus-visible {
    border-color: var(--accent-interactive);
    /* no outline: none — let global rule handle the ring */
}

/* Replace .mode-toggle-track:focus with :focus-visible */
.mode-toggle-track:focus-visible {
    /* outline handled by global rule */
}

/* Replace .filter-search-input:focus with :focus-visible */
.filter-search-input:focus-visible {
    border-color: var(--accent-interactive);
}
```

### COMP-05: Filter Bar Frosted Glass

```css
/* Source: existing input.css .filter-bar-wrapper, needs background + blur */
.filter-bar-wrapper {
    position: sticky;
    top: 0;
    z-index: 10;
    background-color: rgba(9, 9, 11, 0.85);   /* zinc-950 at 85% opacity */
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1rem;
}
```

### COMP-06: Jinja2 Macro Declaration

```jinja2
{# app/templates/macros/icons.html #}
{% macro icon(name, class="w-4 h-4", aria_label=none) -%}
<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 24 24"
     fill="currentColor"
     class="{{ class }}"
     {% if aria_label %}aria-label="{{ aria_label }}"{% else %}aria-hidden="true"{% endif %}
>
  {% if name == "shield-check" %}
  {# Heroicons v2 shield-check solid — path from heroicons.com #}
  <path fill-rule="evenodd" d="M12.516 2.17a.75.75 0 0 0-1.032 0 11.209 11.209 0 0 1-7.877 3.08.75.75 0 0 0-.722.515A12.74 12.74 0 0 0 2.25 9.75c0 5.942 4.064 10.933 9.563 12.348a.749.749 0 0 0 .374 0c5.499-1.415 9.563-6.406 9.563-12.348 0-1.39-.223-2.73-.635-3.985a.75.75 0 0 0-.722-.516l-.143.001c-2.996 0-5.717-1.17-7.734-3.08Zm3.094 8.016a.75.75 0 1 0-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 0 0-1.06 1.06l2.25 2.25a.75.75 0 0 0 1.14-.094l3.75-5.25Z" clip-rule="evenodd"/>
  {% elif name == "cog-6-tooth" %}
  {# Heroicons v2 cog-6-tooth solid #}
  <path fill-rule="evenodd" d="M11.078 2.25c-.917 0-1.699.663-1.85 1.567L9.05 4.889c-.02.12-.115.26-.297.348a7.493 7.493 0 0 0-.986.57c-.166.115-.334.126-.45.083L6.3 5.508a1.875 1.875 0 0 0-2.282.819l-.922 1.597a1.875 1.875 0 0 0 .432 2.385l.84.692c.095.078.17.229.154.43a7.598 7.598 0 0 0 0 1.139c.015.2-.059.352-.153.43l-.841.692a1.875 1.875 0 0 0-.432 2.385l.922 1.597a1.875 1.875 0 0 0 2.282.818l1.019-.382c.115-.043.283-.031.45.082.312.214.641.405.985.57.182.088.277.228.297.35l.178 1.071c.151.904.933 1.567 1.85 1.567h1.844c.916 0 1.699-.663 1.85-1.567l.178-1.072c.02-.12.114-.26.297-.349.344-.165.673-.356.985-.57.167-.114.335-.125.45-.082l1.02.382a1.875 1.875 0 0 0 2.28-.819l.923-1.597a1.875 1.875 0 0 0-.432-2.385l-.84-.692c-.095-.078-.17-.229-.154-.43a7.614 7.614 0 0 0 0-1.139c-.016-.2.059-.352.153-.43l.84-.692c.708-.582.891-1.59.433-2.385l-.922-1.597a1.875 1.875 0 0 0-2.282-.818l-1.02.382c-.114.043-.282.031-.449-.083a7.49 7.49 0 0 0-.985-.57c-.183-.087-.277-.227-.297-.348l-.179-1.072a1.875 1.875 0 0 0-1.85-1.567h-1.843ZM12 15.75a3.75 3.75 0 1 0 0-7.5 3.75 3.75 0 0 0 0 7.5Z" clip-rule="evenodd"/>
  {% endif %}
</svg>
{%- endmacro %}
```

### COMP-07: Header Brand with Emerald Accent

```html
<!-- app/templates/base.html — brand name with emerald accent -->
<span class="site-logo">
    <span style="color: var(--accent);">Sentinel</span>X
</span>
```

Or via CSS:
```css
.site-logo .brand-accent {
    color: var(--accent);
}
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|-----------------|--------|
| `:focus` for focus rings | `:focus-visible` (WHATWG Living Standard) | Shows rings only for keyboard nav; mouse users don't see disruptive outlines |
| `box-shadow` as focus indicator | `outline` + `outline-offset` | `outline` renders outside layout; works in Windows High Contrast Mode; `box-shadow` does not |
| Sprite SVG icons (external file) | Inline SVG via Jinja2 macro | Works with strict CSP; no HTTP request; fully styleable with `currentColor` |
| Per-component `backdrop-filter` experiments | Standard `backdrop-filter: blur(N)` (baseline 2022) | 97%+ browser support; `-webkit-` prefix still needed for Safari 15.x |

**Deprecated/outdated in this context:**
- `box-shadow` as the sole focus ring: violates WCAG 2.1 SC 2.4.11 (Focus Appearance); does not render in High Contrast Mode
- The `.mode-toggle-track:focus` box-shadow ring: was a reasonable interim approach in Phase 7, now must be replaced per COMP-02
- The hardcoded `rgba(74, 158, 255, 0.25)` glow: uses the old blue accent, not the teal `--accent-interactive`

---

## Open Questions

1. **What icons does Phase 12 specifically need in `base.html`?**
   - What we know: COMP-06 says "reusable inline SVG icons across all pages" — the macro creates the infrastructure
   - What's unclear: Phase 12 success criteria mentions header/footer redesign (COMP-07) but doesn't specify which icons go there; the existing `<img>` logo SVG may stay; the nav "Settings" link could get a cog icon
   - Recommendation: Create the macro file with shield-check and cog-6-tooth icons for COMP-07 use; other icons deferred to Phase 13 (where RESULTS-04 needs a magnifying glass for search)

2. **Should `.btn-copy` and `.btn-export` get the ghost treatment or stay as-is?**
   - What we know: COMP-03 specifies "primary, secondary, ghost" variants; `.btn-copy` and `.btn-export` are currently styled as secondary-adjacent
   - What's unclear: whether `.btn-copy` should become `.btn.btn-ghost` (the requirement says the three variants should be "visually distinct")
   - Recommendation: Leave `.btn-copy` and `.btn-export` as-is for Phase 12; they serve micro-action purposes and `.btn-ghost` is for navigation/secondary actions; this avoids unintended visual regressions in results page (Phase 13 scope)

3. **What does `Inter Variable at the correct weight hierarchy` mean for the footer specifically?**
   - What we know: The footer currently uses `font-size: 0.75rem; color: var(--text-secondary)` — already Inter Variable via body inheritance
   - What's unclear: whether the footer needs a weight change or if the placeholder text "SentinelX — Phase 1 Offline Pipeline" simply needs updating
   - Recommendation: Update the footer text to something appropriate (e.g., "SentinelX — IOC Triage Tool"); ensure `font-family: var(--font-ui)` is explicit on `.site-footer` (currently inherits, which is fine but explicit is more robust)

---

## Validation Architecture

> `workflow.nyquist_validation` is not set in `.planning/config.json` — skipping this section.

---

## Sources

### Primary (HIGH confidence)

- Codebase direct inspection — `app/static/src/input.css` (lines 61–919): verified current state of all badge classes, focus styles, button variants, filter bar
- Codebase direct inspection — `app/templates/base.html`, `results.html`, `index.html`, `settings.html`: verified template structure and class usage
- Codebase direct inspection — `app/static/main.js` (lines 176–513): verified JS verdict badge application pattern, `VERDICT_LABELS` constant, `.verdict-badge.verdict-*` class names
- MDN Web Docs — `:focus-visible`: https://developer.mozilla.org/en-US/docs/Web/CSS/:focus-visible — browser support 97%, introduced in Chrome 86, Firefox 85, Safari 15.4
- MDN Web Docs — `backdrop-filter`: https://developer.mozilla.org/en-US/docs/Web/CSS/backdrop-filter — baseline 2022, requires `-webkit-` prefix for Safari 15.x
- Jinja2 docs — Template Macros: https://jinja.palletsprojects.com/en/3.1.x/templates/#macros — `{% from "path" import macro_name %}`

### Secondary (MEDIUM confidence)

- Heroicons v2 official site (heroicons.com) — SVG paths for shield-check and cog-6-tooth icons; paths verified structurally as Heroicons v2 24px solid variant format
- WCAG 2.1 SC 2.4.11 Focus Appearance — confirms `outline` requirement over `box-shadow` for conformance

### Tertiary (LOW confidence)

- None — all findings are codebase-verified or from official docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all components already in the project; no new installs
- Architecture: HIGH — patterns derived directly from codebase inspection and MDN-verified CSS APIs
- Pitfalls: HIGH — all pitfalls are verifiable from the current code state (two badge systems, opaque bg, etc.)

**Research date:** 2026-02-28
**Valid until:** 2026-04-15 (stable CSS APIs; Jinja2 macro syntax stable)
