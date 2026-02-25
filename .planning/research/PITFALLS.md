# Pitfalls Research

**Domain:** Dark-first UI redesign of existing Flask/Tailwind/Jinja2 web app (SentinelX v1.2)
**Researched:** 2026-02-25
**Confidence:** HIGH — sourced from WCAG spec, MDN, Smashing Magazine, LogRocket, and codebase audit

---

## Context: What SentinelX Is Starting From

SentinelX is NOT starting from a light theme. It already uses a GitHub-dark palette defined via
CSS custom properties in `app/static/src/input.css`. The v1.2 redesign moves to an emerald/teal
accent palette with more deliberate elevation, typography, and component polish.

This matters: pitfalls below are calibrated for **redesigning within an already-dark system**,
not converting a light app to dark. The migration risks are around color recalibration, contrast
verification, and elevation — not the typical "don't invert everything" mistake.

---

## Critical Pitfalls

### Pitfall 1: Contrast Assumed, Not Verified

**What goes wrong:**
Designers assume light-colored text on dark backgrounds automatically passes WCAG AA (4.5:1
for normal text, 3:1 for large text/UI components). This assumption fails when:
- Secondary text colors like `--text-secondary: #8b949e` are placed on mid-dark backgrounds
  rather than the darkest page background.
- Accent colors like `--accent-ipv4: #4a9eff` are used as small body text rather than decorative
  borders.
- New emerald/teal accent colors are chosen by aesthetics without measuring contrast first.

**Specific risk in SentinelX:**
The existing `--text-secondary: #8b949e` achieves approximately 4.5:1 on `--bg-primary` (#0d1117)
but drops to approximately 3.2:1 on `--bg-secondary` (#161b22) and approximately 2.8:1 on
`--bg-tertiary` (#1c2128). The `.site-tagline`, `.form-label`, `.enrichment-detail`, and
`.paste-feedback` elements all use `--text-secondary` on `--bg-secondary` card surfaces — these
fail WCAG AA for normal-sized text.

WCAG requirements (source: https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html):
- Normal text (below 18pt or below 14pt bold): minimum 4.5:1
- Large text (18pt or larger, or 14pt bold or larger): minimum 3:1
- UI components (borders, icons, focus rings): minimum 3:1

**Why it happens:**
Contrast tools are not used during design token definition. New accent colors are chosen by
appearance ("this teal feels right") rather than measuring contrast ratio against target backgrounds.

**How to avoid:**
Measure every text/background pairing with a WCAG contrast checker before committing to tokens.
The WebAIM Contrast Checker (https://webaim.org/resources/contrastchecker/) accepts hex values
and returns pass/fail for AA and AAA. Run the audit at token definition time, not after components
are built.

**Warning signs:**
- Secondary label text on card backgrounds "looks comfortable" but washes out when zoomed out
- Accent color used as label text on secondary/tertiary backgrounds
- Typography that passes on a calibrated monitor at full brightness but fails on lesser displays

**Phase to address:**
Phase 1 (Design Tokens) — define all token pairs as contrast-verified before any component work.
Run automated contrast audit as a phase completion criterion.

---

### Pitfall 2: Verdict Status Colors Lose Legibility After Palette Shift

**What goes wrong:**
Status colors — red (malicious), amber (suspicious), green (clean) — were calibrated for the
current GitHub-dark palette. When background tones or the accent family changes, status colors
need recalibration. Two failure modes exist:

Mode A — Oversaturation: Highly saturated status colors (pure #ff0000 red, pure #00ff00 green)
cause visual vibration and eye strain on dark surfaces. They also fail contrast when placed on
dark backgrounds with warm or cool hues because saturation distorts perceived luminance.

Mode B — Desaturation goes too far: Aggressively muted status colors become indistinguishable
from neutral gray metadata text. A pale green barely reads as "clean" alongside pale gray "no
data" text.

Specific risk in SentinelX:
- `.verdict-label--suspicious { background-color: #f59e0b; color: #000; }` — amber fill with
  black text works on current dark surfaces but becomes visually harsh after deeper palette
  changes, and #000 text on amber fails if the amber token is lightened.
- `.verdict-clean { color: #3fb950; }` — this green achieves approximately 4.9:1 on #161b22 but
  may change ratio after background token adjustments.

Research finding: colors in dark themes need less saturation than in light themes to achieve
equivalent contrast. The rule is not to remove saturation arbitrarily but to test each triple
(text color, background fill, border) against the actual card surface.

**Why it happens:**
Status colors are treated as global constants rather than theme-sensitive tokens. The red that
works on GitHub dark is not the correct red for every dark palette.

**How to avoid:**
For each semantic status color define three token variants:
1. Background fill — low opacity or dark equivalent (e.g., `rgba(248, 81, 73, 0.15)` or `#2a1a1a`)
2. Border — medium saturation, must achieve 3:1 on card surface
3. Text/badge — adjusted saturation, must achieve 4.5:1 on badge background fill

Target ranges for SentinelX emerald redesign:
- Malicious: #f87171 (rose-400 family) — avoid pure #ff0000
- Suspicious: #fbbf24 (amber-400) — maintain `color: #000` or equivalent dark text on amber fills
- Clean: #4ade80 (green-400) — slightly desaturated from pure #00ff00
- No Data: #94a3b8 (slate-400) — neutral, low emphasis

**Warning signs:**
- Status badges appear to glow or visually vibrate against the dark background
- Red appears orange in dark context due to hue shift from background undertone
- Green appears neon and causes eye strain during extended nighttime use
- Colorblindness simulation (browser greyscale) makes malicious and no-data indistinguishable

**Phase to address:**
Phase 1 (Design Tokens) — define status color triples (fill/border/text) as part of the token
system. Verify each with a contrast checker against the card surface color before implementation.

---

### Pitfall 3: Focus Ring Invisibility After Accent Color Change

**What goes wrong:**
The current focus rings use `box-shadow: 0 0 0 3px rgba(74, 158, 255, 0.25)` — a 25% opacity
blue. This is aesthetic but almost certainly fails WCAG 1.4.11 (Non-Text Contrast, 3:1 against
adjacent background). When the accent palette changes to emerald/teal, these focus rings need
recalibration and any remaining low-opacity rings must be replaced.

WCAG 2.4.7 (Focus Visible, Level A): focus indicator must be visible.
WCAG 1.4.11 (Non-Text Contrast): focus ring must achieve 3:1 against adjacent background color.
WCAG 2.4.11 (Focus Appearance, WCAG 2.2 AA): focus area must be at least 2px thick and achieve
3:1 contrast ratio between focused and unfocused states.

Specific risk in SentinelX:
- `.mode-toggle-track:focus` uses `box-shadow: 0 0 0 3px rgba(74, 158, 255, 0.25)` — 25% opacity
  blue on #161b22 background fails 3:1.
- `.ioc-textarea:focus` and `.filter-search-input:focus` use `box-shadow: 0 0 0 3px rgba(74, 158, 255, 0.1)` —
  10% opacity, definitely fails.
- The `outline: none` override on these elements must be replaced with a visible outline or a
  high-opacity shadow.

**Why it happens:**
Focus rings are made "subtle" for aesthetic reasons. The rgba opacity is dropped below the
threshold accessibility requires. Low-opacity focus rings pass visual inspection at high screen
brightness but fail for users with low-vision or in low-light conditions.

**How to avoid:**
Use `outline` (not just `box-shadow`) for focus indicators. Recommended pattern:

```css
:focus-visible {
    outline: 2px solid var(--accent-primary);
    outline-offset: 2px;
}
```

If using `box-shadow` to avoid layout shift, use fully opaque or high-opacity color (at least
70% opacity on the specific background it appears on) and verify the resulting contrast reaches
3:1. Test by tab-navigating the form with no mouse.

**Warning signs:**
- Tab-navigating the form makes the focused element difficult to locate
- Focus indicator uses rgba opacity below 0.5
- `outline: none` without a verified-contrast `box-shadow` replacement
- Focus style exists only on `:focus` not `:focus-visible` (causes visible ring on mouse clicks)

**Phase to address:**
Phase 2 (Component Redesign) — audit and replace all focus ring implementations during component
refactor. Keyboard-only navigation test required before marking phase complete.

---

### Pitfall 4: Browser Autofill Overrides Dark Input Backgrounds

**What goes wrong:**
Chrome and Safari apply a bright yellow/white autofill background (approximately #FAFFBD in
Chrome) that overrides custom dark input backgrounds via high-specificity UA pseudo-elements.
The `<input type="password" id="api-key">` on the settings page is at high risk because browsers
remember and autofill credential fields. The result is a jarring yellow/white input surrounded
by dark UI.

Additionally, without `<meta name="color-scheme" content="dark">` in the `<head>`, browsers
render native form controls (select dropdowns, scrollbars, date pickers) using light OS theme
styling even inside a dark-styled page. The results HTML page scrollbar is visible for large
result sets and will appear white on Windows with light OS theme.

**Why it happens:**
Developers style inputs with `background-color` but browsers override this for autofill states
via the UA stylesheet at a specificity level that cannot be overridden by normal CSS selectors.
The `color-scheme` meta tag is rarely documented alongside dark mode tutorials.

**How to avoid:**
Step 1 — Add `<meta name="color-scheme" content="dark">` to `base.html` `<head>`. This signals
the browser to render all UA-controlled elements in dark mode by default.

Step 2 — Add `:root { color-scheme: dark; }` in `input.css` to reinforce the meta tag.

Step 3 — Override the autofill background using the box-shadow trick (the only cross-browser
method that actually works):

```css
input:-webkit-autofill,
input:-webkit-autofill:hover,
input:-webkit-autofill:focus {
    -webkit-box-shadow: 0 0 0 100px var(--bg-secondary) inset;
    -webkit-text-fill-color: var(--text-primary);
    transition: background-color 5000s ease-in-out 0s;
}
```

The 5000s transition delay effectively prevents the yellow flash from ever completing.

**Warning signs:**
- Yellow or white flash on input fields when browser fills credentials
- Native `<select>` elements or date pickers appear with white/light backgrounds
- Page scrollbar appears white/light-gray inside a dark page (Chrome on Windows)
- `<input type="search">` (the filter search input) renders with a light browser chrome on Safari

**Phase to address:**
Phase 1 (Foundation/Base CSS) — add `color-scheme` meta tag and autofill override CSS as the
first foundation step. This has zero interaction risk and affects no component logic.

---

### Pitfall 5: Box Shadows Are Invisible on Dark Surfaces

**What goes wrong:**
Box shadows are dark semi-transparent overlays — they represent shadow cast by light sources.
On a light background, a dark shadow creates visible depth. On a dark background, a dark shadow
is imperceptible because there is minimal contrast between shadow and surface.

If the v1.2 redesign adds elevated components (modal overlays, tooltip popups, dropdown menus,
sticky filter bar separation) using standard CSS shadows (`box-shadow: 0 4px 6px rgba(0,0,0,0.1)`),
the shadows will be invisible on dark surfaces, making elevated components appear flat.

Source: Parker.mov on dark mode shadows explains this clearly — "Shadows are dark values — a
representation of the inverse of light cast on an interface. On a dark surface there is no
contrast between shadow and surface" (https://www.parker.mov/notes/good-dark-mode-shadows).

**Why it happens:**
Elevation systems are designed for light UIs. Developers copy shadow utility values from Tailwind
documentation (`shadow-md`, `shadow-lg`) without adapting them for dark surfaces.

**How to avoid:**
In dark UIs, elevation is conveyed through **surface color lightening**, not shadow darkening.
Lighter surface equals higher elevation. Shadow can supplement but not replace surface lightness.

Recommended elevation scale for SentinelX:
- Level 0 (page background): `--bg-primary: #0d1117`
- Level 1 (card surfaces): `--bg-secondary: #161b22`
- Level 2 (dropdowns, modals): `--bg-tertiary: #1c2128`
- Level 3 (tooltips): approximately `#21262d`

When shadows ARE used (for floating elements), combine a subtle inner highlight with a strong
outer shadow:

```css
/* Dark-mode elevation — inner highlight ring + strong outer shadow */
box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.06),
    0 4px 12px rgba(0, 0, 0, 0.5);
```

**Warning signs:**
- Cards look identical in depth to the page regardless of `box-shadow` values
- Dropdown menus do not appear to float above their context
- UI appears to have only one depth level regardless of component nesting

**Phase to address:**
Phase 1 (Design Tokens) — define elevation via surface color tokens, not shadow-only. Phase 2
(Components) — add inner-highlight shadows when floating elements are introduced.

---

### Pitfall 6: Scrollbar Remains Light-Themed on Windows

**What goes wrong:**
Without explicit scrollbar styling, the browser renders scrollbars using the OS default. On macOS
with dark system preference this is usually acceptable. On Windows with light OS theme (common
on analyst workstations in enterprise environments), the page scrollbar and any overflow scrollbar
inside the textarea will render as white or light-gray, creating a bright element in the dark UI.

The textarea (`ioc-textarea`) overflows vertically with long pastes. The results page scrolls
for large IOC sets. Both produce visible scrollbars that will clash with the dark design on
Windows.

**Why it happens:**
Scrollbar styling is treated as an afterthought. The `color-scheme: dark` meta tag handles some
browsers but is insufficient for explicit cross-browser scrollbar color control.

**How to avoid:**
Use the modern dual-property approach that covers both modern and legacy browsers:

```css
/* Modern standard — Firefox and Chrome 121+, Edge */
* {
    scrollbar-width: thin;
    scrollbar-color: var(--border-hover) var(--bg-secondary);
}

/* Legacy WebKit — Chrome < 121, Safari */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--bg-secondary); }
::-webkit-scrollbar-thumb {
    background-color: var(--border-hover);
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover { background-color: var(--text-secondary); }
```

Note: `scrollbar-color` takes two values in order: thumb color, then track color.

Source: Chrome for Developers scrollbar styling guide (https://developer.chrome.com/docs/css-ui/scrollbar-styling).

**Warning signs:**
- White scrollbar visible inside textarea when text overflows vertically
- Page scrollbar is bright against dark page on Windows Chrome
- Scrollbar thumb has low contrast against scrollbar track

**Phase to address:**
Phase 1 (Foundation/Base CSS) — add scrollbar styles alongside the body reset. No component
interaction, zero risk.

---

### Pitfall 7: Pure Black Backgrounds Cause Halation and Break Elevation

**What goes wrong:**
Pure black (`#000000`) as a page background causes two problems:

Problem A — Halation: Approximately 47% of people have astigmatism. Light text on pure black
backgrounds creates the "halation effect" — bright text bleeds optically onto the dark field,
making character edges appear blurry. The high contrast amplifies this optical phenomenon.
SOC analysts using the tool for extended triage sessions are particularly affected.

Problem B — Elevation floor loss: When the base is pure black, there is nowhere darker to go
for shadows, and surface color variation (the primary dark-mode elevation mechanism) becomes
nearly imperceptible. The difference between `#0a0a0a` and `#111111` cannot be perceived by
most users.

SentinelX currently uses `--bg-primary: #0d1117` (correct — a dark blue-gray, not pure black).
The v1.2 redesign must preserve this principle. If the emerald accent palette pushes toward
cooler or deeper darks, verify the base background stays in the `#0d1117` to `#131820` range.

Reference backgrounds used by major products:
- Google Material Design 3 recommends: `#121212`
- GitHub dark: `#0d1117`
- VS Code: `#1e1e1e`
- Discord: `#313338`

**Why it happens:**
Developers reach for `#000` as "the darkest possible = best dark mode" or follow OLED
optimization advice (true black = pixels off = power saving) that applies to mobile apps but
not to desktop web.

**How to avoid:**
Define a minimum background lightness as a design constraint: `--bg-primary` must be lighter
than `#0a0a0a`. Express this as an explicit token documentation comment, not just a value.

**Warning signs:**
- Text appears to glow or bleed at edges during extended reading
- All surface tiers appear identical in darkness (no perceived depth)
- Background value is `#000`, `#000000`, `#010101`, or any value with all channels below 10

**Phase to address:**
Phase 1 (Design Tokens) — enforce minimum background lightness when defining the new palette.

---

### Pitfall 8: CSS Specificity Collisions During Component Class Refactoring

**What goes wrong:**
SentinelX uses semantic component classes (`.ioc-card`, `.verdict-label`, `.filter-btn`) defined
in `@layer components {}`. Three specific collision risks exist during v1.2:

Risk A — Tailwind utility override: If new Tailwind utility classes are added directly in HTML
templates alongside existing component classes, the utility layer (`@layer utilities`) has higher
specificity than the component layer (`@layer components`), causing unexpected overrides.

Risk B — Token split-brain: If CSS tokens are partially renamed (e.g., `--text-secondary` renamed
to `--color-neutral-muted` in some places but not others), both names coexist and produce
inconsistent results as components inherit from different sources.

Risk C — Jinja2 dynamic class purge: Tailwind's CSS purge operates on static analysis of template
files. Dynamic classes generated via `{{ ioc.type.value }}` interpolation (e.g.,
`ioc-type-badge--ipv4`) are safelisted in `tailwind.config.js`. If any component class is
renamed during redesign, the safelist must be updated or Tailwind will purge the class and the
badge will disappear in production builds.

**Why it happens:**
Incremental refactoring leaves orphaned CSS. Token renames are tracked locally but not
propagated to all sites (template, JS, CSS, safelist). The Tailwind safelist is rarely reviewed
during redesign work.

**How to avoid:**
Before beginning any component work:
1. Create a token rename table mapping every old custom property name to its new name.
2. Grep all template files and `main.js` for every class name that will change before renaming.
3. When renaming a dynamic Jinja2 class: update (a) the template interpolation, (b) the JS that
   adds/removes the class dynamically, (c) the safelist in `tailwind.config.js`, (d) the CSS rule.
4. Run `make css` and visually verify the results page after every template change.

**Warning signs:**
- An IOC type badge disappears on the results page (class was purged from Tailwind output)
- Verdict colors stop updating during enrichment (class name mismatch between JS and CSS)
- Some buttons render with new design colors while others use stale inherited colors

**Phase to address:**
Phase 1 (Foundation) — complete the token and class rename audit before any component work.
Lock the naming convention. Treat class name changes as a tracked migration, not an ad-hoc edit.

---

### Pitfall 9: JavaScript Color Literals Bypass the CSS Token System

**What goes wrong:**
`main.js` currently drives all visual state through data-attribute selectors and class toggles:

```javascript
card.setAttribute("data-verdict", worstVerdict);       // correct — CSS handles color
badge.className = "verdict-badge verdict-malicious";   // correct — CSS handles color
```

This is the correct pattern and it is CSP-safe. The risk for v1.2 is that any new JS code added
during redesign might introduce direct style manipulation with hardcoded hex values:

```javascript
// Wrong pattern — do not introduce:
card.style.borderLeftColor = "#f85149";
element.style.color = "#4ade80";
```

Hardcoded hex values in JS bypass the CSS token system and break when tokens change during
future iterations. They can also introduce CSP issues if the CSP header includes `style-src 'self'`
without `unsafe-inline`.

The existing `showEnrichWarning()` and `showPasteFeedback()` use `element.style.display` — this
is layout control (not color) and is acceptable.

**Why it happens:**
"Quick fix" additions during implementation set colors directly on elements for visual states
that seem too transient to warrant a CSS class. The developer reaches for `element.style` as
the fastest path.

**How to avoid:**
- Never set `element.style.color` or `element.style.backgroundColor` to a hex literal in JS.
- Use data-attribute selectors or class toggles to drive all color-producing CSS rules.
- Treat any `element.style.*` assignment (except `display`, `visibility`, `width`) as a red flag
  in code review.

**Warning signs:**
- `element.style.color = "#..."` in any new JS code
- Colors that work on first render but do not respond to theme token updates
- Visual color differences between identical states in different flows

**Phase to address:**
All phases — treat as a code review gate. The existing JS architecture is correct; the risk is
introduced by new code added during redesign.

---

### Pitfall 10: Typography Weight and Size Too Light for Dark Backgrounds

**What goes wrong:**
Light text on dark backgrounds is rendered differently than dark text on light backgrounds.
Thin font weights (300, 400 for small text) appear visually lighter and thinner than on light
backgrounds because anti-aliasing blends the character edges with the dark surface differently.
Fine strokes in thin-weight glyphs can appear to dissolve at small sizes.

In SentinelX, `.ioc-type-badge` uses `font-size: 0.65rem` — very small text that is borderline
readable. Long SHA256 hashes render in monospace at 0.83rem on cards. If the redesign introduces
thin-weight decorative typography (font-weight 300 or 200), these elements will be harder to
read than anticipated.

Research finding: increasing font weight by one step for body text in dark themes is a standard
recommendation. Line height of 1.5–1.6 and a slight letter-spacing increase of +0.01 to +0.02em
improve readability in low-light contexts where halation causes characters to spread.

Source: Design Shack typography in dark mode guide (https://designshack.net/articles/typography/dark-mode-typography/).

**Why it happens:**
Typography is designed on calibrated monitors at comfortable brightness (70–80%). The design
looks fine in those conditions but fails for analysts using the tool late at night, in dim
environments, or on lower-quality displays.

**How to avoid:**
- Set a minimum font weight constraint: no visible text below `font-weight: 400`.
- Avoid `font-weight: 300` or `font-weight: 200` for any readable text.
- Set `line-height: 1.5` minimum for body text; `1.6` for monospace code content.
- Add `-webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility;` to `body`.
- Keep minimum `font-size` at 0.75rem for any legibility-critical content; 0.65rem badges are
  acceptable only if they use `font-weight: 700` and meet 4.5:1 contrast.

**Warning signs:**
- Monospace hash text in cards looks grainy or unevenly weighted at actual card widths
- Secondary labels feel more "invisible" than "secondary" in emphasis
- Long SHA256 hashes are difficult to visually scan

**Phase to address:**
Phase 1 (Typography Tokens) — define minimum font weight as a constraint. Phase 2 (Components) —
verify hash readability at actual card widths on a standard monitor at 50% brightness.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keep all existing component class names unchanged | Faster redesign, no template edits needed | Old class names do not reflect the new design language; confusing for future work | Acceptable for v1.2 if tokens are updated; consider renaming in v1.3 |
| Use `opacity: 0.6` on secondary text instead of a lighter token | Avoids defining a second text-color token | Contrast ratio changes with every background it appears on — unpredictable failures | Never — always use explicit color tokens |
| Use `filter: invert(1)` globally on icons | Instantly flips light assets to dark | Distorts colorful or multi-color icons; hue shifts make branded icons unrecognizable | Only for single-color black SVG icons confirmed to be single-path; never globally |
| Set `color-scheme: dark` without verifying each browser | Fixes most autofill and scrollbar issues | Firefox and Safari behavior differs; test needed | Acceptable as Phase 1 step; verify cross-browser in Phase 2 |
| Skip contrast audit until design is "finalized" | Faster early iteration | Colors get locked in during implementation before failing contrast is caught | Never — audit tokens at definition time |
| Hard-code new accent color values in templates | Fast to see the result | When the token changes, templates do not update; creates split-brain | Never — all colors must go through CSS custom properties |

---

## Integration Gotchas

Common mistakes when working with the SentinelX-specific stack during the v1.2 redesign.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Tailwind safelist | Adding new dynamic class names to templates without updating the safelist | Update `safelist` in `tailwind.config.js` and run `make css` immediately; verify the class appears in `dist/style.css` |
| Jinja2 dynamic classes | Renaming a class in CSS but forgetting the `{{ ioc.type.value }}` or `{{ verdict }}` interpolation in templates | Grep all templates for every affected class before renaming; update template, JS, safelist, and CSS atomically |
| Alpine.js CSP build | Using `x-bind:style` with dynamic color values | `style-src 'self'` CSP blocks inline style values set by Alpine; use data-attribute and class bindings instead |
| Tailwind layer ordering | Defining component overrides in `@layer utilities` | Utilities have higher specificity and will override intended component styles; component overrides belong in `@layer components` |
| Flask flash messages | `.alert-{{ category }}` class can be `success`, `error`, or `warning` but only `alert-error` is currently styled | Ensure all alert variants are styled for the dark palette |
| `make css` rebuild | Editing `tailwind.config.js` safelist but forgetting to rebuild | Always run `make css` after any config or template change; verify output file timestamp updated |
| Settings form input | `<input type="password" id="api-key">` triggers browser autofill and credential memory | Apply autofill override CSS from Pitfall 4 before testing settings page |

---

## Performance Traps

Patterns that are not relevant at SentinelX's local scale but should be avoided for correctness.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Deep CSS custom property chains | `var(--a)` references `var(--b)` references `var(--c)` — computed style resolution slows | Keep token chains to 2 levels: primitive token to semantic token | Negligible at SentinelX scale; keep for correctness |
| Tailwind purge misses safelist classes | IOC type badges or verdict labels disappear in production-like builds | Test with `NODE_ENV=production`-equivalent build; verify all dynamic classes in `dist/style.css` | Any time `make css` runs after a template change with renamed/new dynamic classes |
| CSS transitions on all card properties | 50+ cards each animating `border-color`, `background-color`, and `border-left-color` on scroll causes jank | Limit transitions to only the properties that change on user action; remove transitions from static non-interactive properties | At 30+ visible cards simultaneously during scroll |

---

## Security Mistakes

Dark mode redesign-specific security issues for SentinelX (beyond general web security
documented in the original PITFALLS.md).

| Mistake | Risk | Prevention |
|---------|------|------------|
| Adding `element.style.color` assignments in JS with color derived from data | If a color value ever derives from API response data — even indirectly — it creates an injection vector | Color must always come from CSS class or token; never from user or API data |
| Using `innerHTML` to inject styled status spans for design richness | XSS if any API response content reaches innerHTML | SentinelX already uses textContent correctly; maintain this during redesign; change CSS class definitions only |
| Adding `style="color: ..."` inline attributes to Jinja2 templates | Violates CSP `style-src 'self'` if Flask headers block inline styles | Use external CSS classes exclusively; verify no new `style="..."` attributes are introduced in templates |

---

## UX Pitfalls

Dark-theme-specific user experience mistakes relevant to a security triage tool.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Verdict colors that rely only on hue (red/amber/green) | Colorblind analysts (approximately 8% of males) cannot distinguish malicious from suspicious | Text labels are always present (already in design); verify they are never hidden or truncated |
| Enrichment spinner invisible on dark card surface | Analyst cannot tell if enrichment is loading or stalled | Spinner border must achieve 3:1 against the card background (`--bg-secondary`); verify spinner contrast |
| Filter bar sticky background identical to page (no separation) | Filter bar blends into scrolling content when content scrolls beneath it | Distinct background with bottom border is already present; ensure new palette tokens maintain the separation |
| Text search placeholder too dim | Analyst does not know what the field accepts | Placeholder text must achieve at least 3:1 against the input background — softer than body text but not invisible |
| Card hover states that change only background | Background changes are subtle on dark; analysts miss the hover affordance | Combine background change with border-color change on hover for reliable hover indication |
| No `prefers-reduced-motion` handling on new animations | Analysts sensitive to motion experience discomfort from card sort animations | Wrap card sort animations and transitions in `@media (prefers-reduced-motion: no-preference)` |

---

## "Looks Done But Isn't" Checklist

Things that appear complete in development but are missing critical pieces.

- [ ] **Color tokens:** Token is defined — but verify contrast ratio for every text/background pair that uses it before implementing components
- [ ] **Verdict colors:** Badge looks correct in isolation — but verify on actual card background (`--bg-secondary`), not the page background (`--bg-primary`)
- [ ] **Focus rings:** Interactive element has focus style — but verify it works on BOTH dark card surface AND dark page background (same component may appear in both contexts)
- [ ] **Autofill:** Input field has dark styling — but test by triggering actual browser autofill on the settings API key field with a saved credential
- [ ] **Scrollbar:** Scrollbar looks dark in macOS Chrome — but test in Windows Chrome with light OS theme active
- [ ] **Safelist:** Dynamic classes render correctly in development — but run `make css` and verify the result page renders correctly with the production-optimized CSS
- [ ] **Status colors:** Verdict badge looks clear in the browser — but test with the browser's greyscale filter (DevTools accessibility simulation) to verify colorblind legibility
- [ ] **Font weight:** Heading looks good at 70% brightness — but test at 50% brightness (analysts using the tool in dim environments at night)
- [ ] **Inline style check:** New JS code passes code review — but grep for `element.style.color` and `element.style.background` to catch any hardcoded color literals

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Contrast failures discovered post-implementation | MEDIUM | Update CSS token values only — no template changes needed if tokens drive all colors |
| Autofill yellow flash not fixed in foundation phase | LOW | Add `color-scheme` meta and autofill override CSS in `input.css` — zero component changes |
| Tailwind purges a dynamic class | LOW | Add class to safelist in `tailwind.config.js`, run `make css` — five minutes |
| Verdict color too saturated or harsh | MEDIUM | Adjust `--verdict-*` hex values in `:root` and re-test all affected badges, borders, and dashboard indicators |
| Focus rings invisible — caught in accessibility audit | MEDIUM | Replace all low-opacity `box-shadow` focus rings with `outline` or higher-opacity equivalents — systematic find-and-replace in `input.css` |
| JS hardcodes a color literal — caught in review | LOW | Refactor to use class toggle or data-attribute — localized change in `main.js` |
| Pure black introduced by a new background token | LOW | Update the single CSS custom property value and rebuild |
| Scrollbar remains light on Windows | LOW | Add scrollbar CSS to base layer if not already added — zero component interaction |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification Method |
|---------|------------------|---------------------|
| Contrast failures (Pitfall 1) | Phase 1 — Token definition | Run WCAG contrast audit on all text/background token pairs before phase closes |
| Verdict color saturation (Pitfall 2) | Phase 1 — Token definition | Test all 5 verdict states on `--bg-secondary` card surface; greyscale simulation |
| Focus ring invisibility (Pitfall 3) | Phase 2 — Component redesign | Keyboard-only tab navigation through all interactive elements |
| Form autofill override (Pitfall 4) | Phase 1 — Foundation/base CSS | Trigger browser autofill on settings API key field; verify no yellow flash |
| Invisible box shadows (Pitfall 5) | Phase 1 — Elevation tokens | Render elevated components and verify surface lightness creates visible depth |
| Light scrollbar on Windows (Pitfall 6) | Phase 1 — Base CSS | Test in Chrome on Windows with light OS theme |
| Pure black background (Pitfall 7) | Phase 1 — Token definition | Verify `--bg-primary` hex value is in `#0d1117` to `#181818` range |
| CSS specificity collisions (Pitfall 8) | Phase 1 — Token rename audit | Grep all templates and `main.js` for any stale class names; run `make css` and inspect output |
| JS hardcoded color literals (Pitfall 9) | All phases — code review gate | Grep `main.js` changes for `style.color` or `style.background` before every commit |
| Font weight / anti-aliasing (Pitfall 10) | Phase 1 — Typography tokens | Test with browser at 50% brightness; verify small text and SHA256 hash readability |

---

## Sources

- WCAG 2.1 SC 1.4.3 (Contrast Minimum): https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html
- WCAG 2.1 SC 1.4.11 (Non-Text Contrast): https://www.w3.org/WAI/WCAG21/Understanding/non-text-contrast.html
- WCAG 2.4.7 (Focus Visible): https://www.w3.org/WAI/WCAG21/Understanding/focus-visible.html
- WCAG 2.2 SC 2.4.11 (Focus Appearance): https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance.html
- Dark mode UI design anti-patterns (LogRocket): https://blog.logrocket.com/ux-design/dark-mode-ui-design-best-practices-and-examples/
- Inclusive dark mode design, Smashing Magazine 2025: https://www.smashingmagazine.com/2025/04/inclusive-dark-mode-designing-accessible-dark-themes/
- Good dark mode shadows: https://www.parker.mov/notes/good-dark-mode-shadows
- Tailwind dark mode class strategy: https://tailwindcss.com/docs/dark-mode
- color-scheme meta tag, web.dev: https://web.dev/articles/color-scheme
- MDN color-scheme property: https://developer.mozilla.org/en-US/docs/Web/CSS/color-scheme
- Scrollbar styling, Chrome for Developers: https://developer.chrome.com/docs/css-ui/scrollbar-styling
- Dark mode typography, Design Shack: https://designshack.net/articles/typography/dark-mode-typography/
- Scalable accessible dark mode (semantic color saturation): https://www.fourzerothree.in/p/scalable-accessible-dark-mode
- Complete accessibility guide for dark mode (2026): https://blog.greeden.me/en/2026/02/23/complete-accessibility-guide-for-dark-mode-and-high-contrast-color-design-contrast-validation-respecting-os-settings-icons-images-and-focus-visibility-wcag-2-1-aa/
- SentinelX codebase audit: `app/static/src/input.css`, `app/static/main.js`, `app/templates/*.html`

---
*Pitfalls research for: dark-first UI redesign of Flask/Tailwind/Jinja2 security tool (SentinelX v1.2)*
*Researched: 2026-02-25*
