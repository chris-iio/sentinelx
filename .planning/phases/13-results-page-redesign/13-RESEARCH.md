# Phase 13: Results Page Redesign - Research

**Researched:** 2026-02-28
**Domain:** Jinja2 template partials, CSS animations (shimmer/hover lift), KPI dashboard layout, empty-state UI, SVG icon integration
**Confidence:** HIGH

## Summary

Phase 13 is a frontend-only redesign of `results.html`. The codebase is already well-structured with a proven design token system (Phase 11) and shared component library (Phase 12). The main task splits into two sequenced concerns: (1) structural refactoring — extract the monolithic `results.html` into Jinja2 `include` partials without breaking any E2E tests, and (2) visual elevation — add the KPI dashboard redesign, card hover lift, dot indicators, shimmer loader, empty-state icon treatment, and search icon prefix.

The most technically novel element is the shimmer skeleton loader. The existing JS (`main.js`) removes `.spinner-wrapper` on first enrichment result — this is the insertion point. Shimmer requires a CSS `@keyframes` background-position animation on a pseudo-element or gradient overlay. The pattern is well-established in the industry and maps directly onto the existing `.enrichment-slot` structure. The critical constraint is that the shimmer must not be applied to elements that scroll (would cause jank with `background-attachment`) — a `transform` + gradient approach on a child element is the correct pattern.

The KPI dashboard upgrade (RESULTS-06) replaces the current inline-pill `.verdict-dashboard-badge` pattern with four standalone card elements. The JS polling logic updates `[data-verdict-count="malicious"]` spans — this data attribute contract must be preserved exactly through the redesign.

**Primary recommendation:** Execute in two sequential waves: Wave 1 = partial extraction (RESULTS-01, verify E2E green), Wave 2 = visual features (RESULTS-02 through RESULTS-08). Never mix structural and visual changes in the same task.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RESULTS-01 | Jinja2 template partials extracted — `_ioc_card.html`, `_verdict_dashboard.html`, `_filter_bar.html`, `_enrichment_slot.html` — with E2E tests passing after extraction before any visual changes | Jinja2 `{% include %}` mechanics, existing E2E test inventory, data-attribute contracts in main.js |
| RESULTS-02 | IOC card hover elevation — `translateY(-1px)` + subtle shadow + border-color shift on hover with 150ms ease transition | CSS transform hover pattern, existing `.ioc-card` CSS, 150ms timing already used in codebase |
| RESULTS-03 | IOC type badge dot indicator — `::before` 6px colored circle on each type badge for quick visual scanning | CSS `::before` pseudo-element, existing `--accent-ipv4/domain/etc` token system |
| RESULTS-04 | Search input has inline SVG magnifying glass icon prefix | Icon prefix pattern with `position: relative` wrapper + `padding-left` on input, existing icons macro |
| RESULTS-05 | Empty state displays shield/search icon with "No IOCs detected" headline and body text listing supported IOC types | Existing `.no-results` HTML in `results.html`, Heroicons macro already has `shield-check` |
| RESULTS-06 | Verdict stat dashboard upgraded to KPI-style cards — large monospace number, colored top border, small-caps label | Existing `[data-verdict-count]` JS contracts, KPI card CSS pattern, verdict token system |
| RESULTS-07 | Shimmer skeleton loader replaces spinner during enrichment-pending state — 2-3 animated skeleton rectangles per card | CSS `@keyframes` shimmer pattern, `.enrichment-slot` structure, `.spinner-wrapper` JS removal point |
| RESULTS-08 | 3px left-border accent on IOC cards in verdict color for instant visual scanning | Already partially implemented — `.ioc-card` has `border-left: 3px solid var(--border)` with verdict overrides. Verify it's correct. |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | bundled with Flask 3.1 | Template partials via `{% include %}` | Zero new deps — already in use |
| Tailwind CSS standalone CLI | v3.4.17 | CSS compilation | Existing pipeline (`make css`) |
| Vanilla JS | N/A | Enrichment polling, DOM updates | Already implemented in `main.js` |
| Heroicons v2 | inline SVG | Icons (shield, magnifying glass) | Already embedded in `macros/icons.html` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| CSS custom properties | native | Design tokens | All color/spacing references — use `var()` not hardcoded values |
| CSS `@keyframes` | native | Shimmer animation | Shimmer loader for `.enrichment-slot` pending state |
| CSS `::before` pseudo-element | native | Dot indicators on type badges | RESULTS-03 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `{% include %}` partials | Jinja2 macros | Macros better for repeated parametric components; `include` better for page sections |
| CSS `@keyframes` shimmer | SVG animate | CSS approach is simpler and already consistent with `@keyframes spin` in codebase |
| CSS `::before` dot | Actual HTML `<span>` dot | CSS pseudo-element is less markup, no template change needed per badge |

**Installation:** None required. All tools already present.

## Architecture Patterns

### Recommended Project Structure

After Phase 13, template structure becomes:

```
app/templates/
├── base.html                      # unchanged
├── results.html                   # slim orchestrator: imports partials
├── index.html                     # unchanged
├── settings.html                  # unchanged
├── macros/
│   └── icons.html                 # existing — add magnifying-glass icon
└── partials/
    ├── _ioc_card.html             # NEW — single IOC card (loop body)
    ├── _verdict_dashboard.html    # NEW — KPI dashboard (online mode only)
    ├── _filter_bar.html           # NEW — sticky filter + search
    └── _enrichment_slot.html      # NEW — pending/shimmer slot (online mode)
```

### Pattern 1: Jinja2 `{% include %}` for Template Partials

**What:** Extract sections of `results.html` into separate files and pull them back in with `{% include %}`. Jinja2 includes inherit the full template context — all variables passed to `render_template("results.html", ...)` are available in included files without passing arguments.

**When to use:** Large template sections that benefit from independent editing without needing parametric reuse.

**Example:**
```jinja2
{# In results.html #}
{% if mode == "online" and job_id %}
    {% include "partials/_verdict_dashboard.html" %}
{% endif %}

{% include "partials/_filter_bar.html" %}

{# In the card loop #}
{% for ioc_type, iocs in grouped.items() %}
    {% for ioc in iocs %}
        {% include "partials/_ioc_card.html" %}
    {% endfor %}
{% endfor %}
```

**Variable access in partials:** Variables `ioc`, `ioc_type`, `mode`, `job_id`, `grouped`, `total_count`, `enrichable_count` are all available in partials without any extra wiring. This is a Jinja2 native behavior — includes share the parent render context.

**Confidence:** HIGH — verified against Jinja2 documentation behavior.

### Pattern 2: Card Hover Lift (RESULTS-02)

**What:** `transform: translateY(-1px)` + `box-shadow` on `.ioc-card:hover`. Already uses `transition: border-left-color 0.2s ease` — extend to include `transform` and `box-shadow`.

**Example:**
```css
.ioc-card {
    /* existing: */
    background-color: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.75rem 1rem;
    border-left: 3px solid var(--border);
    transition: border-left-color 0.2s ease, transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}

.ioc-card:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    border-color: var(--border-hover);
}
```

**Timing:** 150ms matches the established codebase convention (`.btn`, `.filter-btn`, `.nav-link` all use `0.15s ease`). Use `0.15s` here.

**Confidence:** HIGH — pure CSS, no dependencies.

### Pattern 3: CSS `::before` Dot Indicator (RESULTS-03)

**What:** Add a `::before` pseudo-element to `.ioc-type-badge` variants. Each type uses its `--accent-{type}` color token.

**Example:**
```css
.ioc-type-badge::before {
    content: "";
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background-color: currentColor;
    margin-right: 4px;
    vertical-align: 1px;   /* optical alignment with uppercase badge text */
    flex-shrink: 0;
}
```

Since the `.ioc-type-badge--{type}` variants already set `color` to the type accent color, `background-color: currentColor` automatically picks up the right color without per-type overrides. No JavaScript changes required.

**Confidence:** HIGH — standard CSS pattern.

### Pattern 4: Shimmer Skeleton Loader (RESULTS-07)

**What:** Replace `.spinner-wrapper` HTML with shimmer rectangles in the initial enrichment-pending state. Shimmer uses `@keyframes` on a `linear-gradient` `background-position`.

**The shimmer approach (GPU-safe):**
```css
@keyframes shimmer {
    0%   { background-position: -468px 0; }
    100% { background-position: 468px 0; }
}

.shimmer-line {
    background: linear-gradient(
        to right,
        var(--bg-tertiary) 8%,
        var(--bg-hover)    18%,
        var(--bg-tertiary) 33%
    );
    background-size: 936px 100%;
    animation: shimmer 1.4s linear infinite;
    border-radius: var(--radius-sm);
    height: 12px;
}
```

**HTML structure in `_enrichment_slot.html` initial state:**
```html
<div class="enrichment-slot">
    <div class="shimmer-wrapper">
        <div class="shimmer-line shimmer-line--wide"></div>
        <div class="shimmer-line shimmer-line--narrow"></div>
        <div class="shimmer-line shimmer-line--medium"></div>
    </div>
</div>
```

**JS integration point:** `main.js` at line ~422 removes `.spinner-wrapper` on first enrichment result:
```javascript
var spinnerWrapper = slot.querySelector(".spinner-wrapper");
if (spinnerWrapper) {
    slot.removeChild(spinnerWrapper);
}
```

This selector must be updated to `.shimmer-wrapper` OR the shimmer wrapper must retain the class `.spinner-wrapper` (simpler, no JS change). **Recommended: keep class name `.spinner-wrapper`** — zero JS changes, only HTML/CSS changes.

**No-jank guarantee:** Using `background-position` animation does not cause layout reflows. `will-change: background-position` can be added if profiling shows issues, but unlikely at 50+ cards since each animation is independent and CSS-driven.

**Confidence:** HIGH — established pattern, verified against codebase JS.

### Pattern 5: KPI Dashboard Cards (RESULTS-06)

**What:** Replace `.verdict-dashboard-badge` pill pattern with four standalone `.verdict-kpi-card` elements. The JS contracts (`[data-verdict-count="malicious"]`, `[data-verdict]` attributes) must be preserved.

**New HTML structure for `_verdict_dashboard.html`:**
```html
<div class="verdict-dashboard" id="verdict-dashboard">
    <div class="verdict-kpi-card verdict-kpi-card--malicious" data-verdict="malicious"
         role="button" tabindex="0">
        <span class="verdict-kpi-count" data-verdict-count="malicious">0</span>
        <span class="verdict-kpi-label">Malicious</span>
    </div>
    <!-- repeat for suspicious, clean, no_data -->
</div>
```

**CSS pattern:**
```css
.verdict-dashboard {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.75rem;
    margin-bottom: 1.25rem;
}

.verdict-kpi-card {
    background-color: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    border-top: 3px solid;   /* colored accent — override per verdict */
    padding: 0.75rem 1rem;
    cursor: pointer;
    transition: background-color 0.15s ease;
    text-align: left;
}

.verdict-kpi-card--malicious {
    border-top-color: var(--verdict-malicious-border);
}

.verdict-kpi-count {
    font-family: var(--font-mono);
    font-size: 1.75rem;
    font-weight: 700;
    line-height: 1;
    display: block;
    color: var(--text-primary);
}

.verdict-kpi-label {
    font-size: 0.72rem;
    font-variant: small-caps;
    letter-spacing: 0.06em;
    color: var(--text-secondary);
    margin-top: 0.25rem;
    display: block;
}
```

**JS contract preserved:** `[data-verdict="malicious"]` and `[data-verdict-count="malicious"]` are kept on the new elements. The JS click-to-filter logic in `main.js` (lines 630–660 area) reads `data-verdict` on click — this still works.

**Confidence:** HIGH — data attribute contracts verified in main.js source.

### Pattern 6: Empty State (RESULTS-05)

**What:** Replace the minimal `.no-results` div with a centered icon + headline + body treatment.

**Existing HTML to replace:**
```html
<div class="no-results">
    <p>No IOCs detected in the pasted text.</p>
    <p class="no-results-hint">Supported types: IPv4, IPv6, domain, URL, MD5, SHA1, SHA256, CVE.</p>
</div>
```

**New HTML:**
```html
<div class="empty-state">
    <div class="empty-state-icon">
        {{ icon("shield-check", class="empty-state-svg", aria_label="No IOCs detected") }}
    </div>
    <h2 class="empty-state-headline">No IOCs detected</h2>
    <p class="empty-state-body">
        Supported types: IPv4, IPv6, domain, URL, MD5, SHA1, SHA256, CVE
    </p>
</div>
```

**The `shield-check` icon is already in the macro** (`macros/icons.html`). A magnifying-glass icon (`magnifying-glass`) needs to be added to the macro for RESULTS-04. The empty-state can use `shield-check` per the success criteria.

**CSS:**
```css
.empty-state {
    text-align: center;
    padding: 4rem 2rem;
    color: var(--text-secondary);
}

.empty-state-icon {
    display: flex;
    justify-content: center;
    margin-bottom: 1.5rem;
}

.empty-state-svg {
    width: 48px;
    height: 48px;
    color: var(--text-muted);
    opacity: 0.6;
}

.empty-state-headline {
    font-size: 1.125rem;
    font-weight: var(--weight-heading);
    color: var(--text-primary);
    margin-bottom: 0.5rem;
}

.empty-state-body {
    font-size: 0.85rem;
    color: var(--text-secondary);
}
```

**Confidence:** HIGH — icon already in macro, pattern is straightforward.

### Pattern 7: Search Input Icon Prefix (RESULTS-04)

**What:** The `.filter-search-input` needs an SVG magnifying-glass icon as a visual prefix. Implemented as `position: relative` wrapper with SVG positioned absolutely inside, and `padding-left` on input to clear icon space.

**New HTML structure in `_filter_bar.html`:**
```html
<div class="filter-search">
    <div class="filter-search-wrapper">
        {{ icon("magnifying-glass", class="filter-search-icon") }}
        <input type="search" id="filter-search-input"
               placeholder="Search IOCs..."
               class="filter-search-input"
               autocomplete="off" />
    </div>
</div>
```

**CSS:**
```css
.filter-search-wrapper {
    position: relative;
    display: inline-flex;
    align-items: center;
}

.filter-search-icon {
    position: absolute;
    left: 0.6rem;
    width: 14px;
    height: 14px;
    color: var(--text-muted);
    pointer-events: none;
    flex-shrink: 0;
}

.filter-search-input {
    /* existing properties retained, add: */
    padding-left: 2.2rem;
}
```

**The `magnifying-glass` icon must be added to `macros/icons.html`.** Currently only `shield-check` and `cog-6-tooth` are defined. Heroicons v2 magnifying-glass path:
```html
{# Source: https://heroicons.com — magnifying-glass (24x24 solid) #}
<path stroke-linecap="round" stroke-linejoin="round"
      d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"/>
```
Note: magnifying-glass in Heroicons v2 uses `stroke` not `fill`. The macro uses `fill="currentColor"` — this must be addressed. Use the outline variant with `fill="none" stroke="currentColor" stroke-width="1.5"` OR find a solid fill path. The outline variant is the correct Heroicons v2 magnifying-glass.

**Confidence:** MEDIUM — icon path needs verification from heroicons.com. The CSS pattern is HIGH confidence.

### Anti-Patterns to Avoid

- **Don't pass variables explicitly to `{% include %}`** — Jinja2 includes inherit context automatically. Avoid `{% include "x.html" with foo=bar %}` unless scoping is actually needed (it's not here).
- **Don't use `backdrop-filter` on `.ioc-card` hover** — already blacklisted in v1.2 (GPU jank at 50+ cards).
- **Don't use `background-attachment: fixed` in shimmer** — causes jank during scroll. Use `background-position` animation instead.
- **Don't rename `.spinner-wrapper` class** — JS in `main.js` removes it by class name (`slot.querySelector(".spinner-wrapper")`). Renaming requires JS changes.
- **Don't break `[data-verdict-count]` attribute contracts** — JS polling loop updates these spans. Keep attribute names identical in new KPI card structure.
- **Don't render `_verdict_dashboard.html` unconditionally** — existing template wraps it in `{% if mode == "online" and job_id %}`. Preserve this condition.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Icon SVG paths | Custom SVG | Heroicons v2 paths embedded in existing macro | Paths already validated, consistent 24x24 viewBox |
| Shimmer timing | Custom JS timer | CSS `@keyframes` | CSS GPU-composited, no JS overhead |
| KPI card layout | Flexbox guesswork | CSS Grid `repeat(4, 1fr)` | Evenly distributes 4 cards, responsive collapse straightforward |
| Partial inheritance | Macro arguments | Jinja2 `{% include %}` context sharing | Simpler, no argument wiring needed |

**Key insight:** Every visual feature in this phase is achievable with CSS alone (no new JS). The hardest implementation constraint is preserving the JS data-attribute contracts (`[data-verdict-count]`, `.spinner-wrapper`, `.enrichment-slot`) exactly.

## Common Pitfalls

### Pitfall 1: Breaking E2E Tests During Partial Extraction

**What goes wrong:** Moving template sections into partials breaks E2E tests because element selectors change or context variables are not available in partial scope.

**Why it happens:** Developer assumes `{% include %}` needs explicit variable passing (like macros do).

**How to avoid:** Test after extraction before any visual changes (this is the RESULTS-01 success criterion). Jinja2 `{% include %}` shares full render context — no variable passing needed. Run `python3 -m pytest tests/e2e/ -q` after each partial extraction.

**Warning signs:** `KeyError` in Jinja2 rendering, missing template variables in partial.

### Pitfall 2: Shimmer Class Name Collision with JS

**What goes wrong:** Renaming `.spinner-wrapper` to `.shimmer-wrapper` in the HTML partial without updating `main.js` — the JS never removes the shimmer, cards appear frozen in loading state.

**Why it happens:** JS and template are edited separately; easy to miss the dependency.

**How to avoid:** Either (a) keep the class `.spinner-wrapper` on the shimmer wrapper (zero JS change required), or (b) update `main.js` to remove `.shimmer-wrapper` instead. Option (a) is strongly preferred.

**Warning signs:** Enrichment results arrive via polling but shimmer persists on screen.

### Pitfall 3: KPI Dashboard Breaking Click-to-Filter

**What goes wrong:** The KPI dashboard click-to-filter behavior (clicking a verdict stat filters the card grid) breaks because `[data-verdict]` attribute is missing or has wrong value on new card elements.

**Why it happens:** New card HTML structure does not include `data-verdict` attribute.

**How to avoid:** Inspect `main.js` around line 630 for the dashboard badge click listener. The listener reads `badge.getAttribute("data-verdict")` and applies it as a filter. Ensure new `.verdict-kpi-card` elements have `data-verdict="malicious"` etc.

**Warning signs:** Clicking KPI card does nothing; filter state does not change.

### Pitfall 4: Shimmer Jank During Scroll

**What goes wrong:** Shimmer animation causes scrolling jank because the browser repaints shimmering elements on every scroll frame.

**Why it happens:** `background-attachment: fixed` or `transform` on parent elements create stacking context issues.

**How to avoid:** Use `background-position` animation on the shimmer element itself (not the parent). Do NOT use `will-change: transform` on `.ioc-card` — this promotes cards to compositing layers which can increase memory use at 50+ cards.

**Warning signs:** DevTools "Rendering" panel shows frequent repaints; scrolling is visually choppy.

### Pitfall 5: Tagline Test Failure (Pre-existing, not new)

**What goes wrong:** `test_header_branding` fails because it expects "Offline IOC Extractor" but the Phase 12 implementation changed it to "IOC Triage Tool".

**Why it happens:** Phase 12 completed this intentional change but the test was not updated.

**How to avoid:** This test must be fixed in Phase 13 Wave 1 (or before). Update the test to expect "IOC Triage Tool". This is not a regression — it's a known pre-existing failure from Phase 12.

**Warning signs:** `test_header_branding` fails in E2E suite with "Actual value: IOC Triage Tool".

## Code Examples

### Jinja2 Partial Include

```jinja2
{# results.html — after extraction #}
{% extends "base.html" %}

{% block content %}
<div class="page-results" ...>
    <div class="results-header">
        {# ... mode indicator, count, export button, back link ... #}
    </div>

    <div class="enrich-warning" id="enrich-warning" style="display:none;"></div>

    {% if mode == "online" and job_id %}
    <div class="enrich-progress" id="enrich-progress">
        {# ... progress bar ... #}
    </div>
    {% endif %}

    {% if no_results or total_count == 0 %}
        {% include "partials/_empty_state.html" %}
    {% else %}
    <div id="filter-root">
        {% if mode == "online" and job_id %}
            {% include "partials/_verdict_dashboard.html" %}
        {% endif %}
        {% include "partials/_filter_bar.html" %}
        <div class="ioc-cards-grid" id="ioc-cards-grid">
            {% for ioc_type, iocs in grouped.items() %}
                {% for ioc in iocs %}
                    {% include "partials/_ioc_card.html" %}
                {% endfor %}
            {% endfor %}
        </div>
    </div>
    {% endif %}
</div>
{% endblock %}
```

### Shimmer CSS (GPU-safe)

```css
/* Source: established CSS shimmer pattern */
@keyframes shimmer {
    0%   { background-position: -468px 0; }
    100% { background-position: 468px 0; }
}

.shimmer-line {
    background: linear-gradient(
        to right,
        var(--bg-tertiary) 8%,
        var(--bg-hover)    18%,
        var(--bg-tertiary) 33%
    );
    background-size: 936px 100%;
    animation: shimmer 1.4s linear infinite;
    border-radius: var(--radius-sm);
    height: 12px;
    margin-bottom: 6px;
}

.shimmer-line--wide   { width: 85%; }
.shimmer-line--medium { width: 65%; }
.shimmer-line--narrow { width: 45%; }
```

### KPI Dashboard Grid

```css
.verdict-dashboard {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.75rem;
    margin-bottom: 1.25rem;
}

@media (max-width: 640px) {
    .verdict-dashboard {
        grid-template-columns: repeat(2, 1fr);
    }
}
```

### Magnifying Glass Icon (Heroicons v2 Outline — to add to macro)

```jinja2
{# In macros/icons.html, add this elif branch: #}
{% elif name == "magnifying-glass" %}
<path stroke-linecap="round" stroke-linejoin="round"
      d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"/>
```

Note: The macro uses `fill="currentColor"` globally. For the magnifying-glass outline variant, the macro SVG element needs `fill="none" stroke="currentColor" stroke-width="1.5"` attributes. The cleanest fix: add a conditional `stroke` mode to the macro, OR add a dedicated outline SVG wrapper. Simplest approach: add a new `icon_outline` macro or override attributes with a `variant` parameter.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Spinner via CSS border rotation | Shimmer skeleton via `@keyframes background-position` | Phase 13 | Better perceived performance; matches Linear/Vercel aesthetic |
| Inline verdict pills in dashboard | KPI cards with monospace counts | Phase 13 | More visual hierarchy; easier to scan at a glance |
| Minimal text-only empty state | Icon + headline + body empty state | Phase 13 | Consistent with modern SaaS empty-state pattern |

**Deprecated in this phase:**
- `.enrichment-spinner` + `.enrichment-pending-text` pattern — replaced by shimmer
- `.verdict-dashboard-badge` pills — replaced by `.verdict-kpi-card` grid
- `.no-results` minimal text — replaced by `.empty-state` icon treatment

## Open Questions

1. **Heroicons macro: fill vs stroke for magnifying-glass**
   - What we know: Current macro uses `fill="currentColor"` globally (works for solid icons like shield-check, cog-6-tooth)
   - What's unclear: magnifying-glass in Heroicons v2 is an outline/stroke icon — it requires `fill="none" stroke="currentColor"`
   - Recommendation: Add a `variant` parameter to the `icon` macro (`variant="solid"` default, `variant="outline"` for magnifying-glass). Alternatively: find a solid magnifying glass path. The Phase 12 plan noted this infrastructure was needed "for search icon prefix" — this is the moment to resolve it.

2. **`test_header_branding` failure**
   - What we know: Test expects "Offline IOC Extractor" but Phase 12 changed tagline to "IOC Triage Tool". This is a known pre-existing failure.
   - What's unclear: Whether to fix the test in Wave 1 of this phase or treat it as a pre-condition issue.
   - Recommendation: Fix the test in Wave 1 as part of RESULTS-01 (partial extraction wave). It's a one-line change: `expect(idx.site_tagline).to_have_text("IOC Triage Tool")`.

3. **RESULTS-08 left-border — already partially implemented?**
   - What we know: The current `.ioc-card` CSS already has `border-left: 3px solid var(--border)` with verdict-color overrides (`.ioc-card[data-verdict="malicious"]` etc.). This looks like RESULTS-08 is already ~90% done.
   - What's unclear: Whether the 3px left border needs any additional styling refinement.
   - Recommendation: Verify the existing implementation satisfies the success criterion. If it does, RESULTS-08 is free (just confirm + document). If the border is visually too subtle, adjust in the visual wave.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + Playwright (pytest-playwright) |
| Config file | `pytest.ini` or inline conftest.py |
| Quick run command | `python3 -m pytest tests/e2e/ -q -x` |
| Full suite command | `python3 -m pytest tests/e2e/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RESULTS-01 | Partials extracted, all E2E pass | E2E regression | `python3 -m pytest tests/e2e/ -q` | ✅ existing suite |
| RESULTS-02 | Card hover lift visible (translateY + shadow) | Visual/manual | `python3 -m pytest tests/e2e/test_results_page.py -q` | ✅ (manual visual check) |
| RESULTS-03 | Dot before type badge (::before pseudo-element) | Visual/manual | CSS inspect | manual-only |
| RESULTS-04 | Magnifying glass prefix in search input | E2E element check | Wave 0 gap — new test needed | ❌ Wave 0 |
| RESULTS-05 | Empty state: icon + headline + body text | E2E | `python3 -m pytest tests/e2e/test_extraction.py -k "no_iocs" -q` | ✅ `test_no_iocs_found` exists |
| RESULTS-06 | KPI dashboard: 4 cards with monospace counts | E2E element check | Existing dashboard badge tests | ✅ ResultsPage.verdict_dashboard |
| RESULTS-07 | Shimmer replaces spinner (no spinner visible) | E2E element check | Wave 0 gap — new test needed | ❌ Wave 0 |
| RESULTS-08 | 3px left border in verdict color | Visual/manual | CSS inspect | manual-only |

### Sampling Rate

- **Per task commit:** `python3 -m pytest tests/e2e/ -q`
- **Per wave merge:** `python3 -m pytest tests/ -q` (full suite including unit tests)
- **Phase gate:** Full suite green before verify (3 known pre-existing failures are exempt: `test_online_mode_indicator`, `test_online_mode_shows_verdict_dashboard`, `test_header_branding` — the last must be fixed in Wave 1)

### Wave 0 Gaps

- [ ] `tests/e2e/test_results_page.py` — add `test_search_icon_present` covering RESULTS-04 (checks `.filter-search-icon` element exists and `.filter-search-input` has `padding-left` > 30px)
- [ ] `tests/e2e/test_results_page.py` — add `test_shimmer_shown_during_pending` or document as manual-only (shimmer requires online mode + live enrichment loop; hard to test without VT API key)
- [ ] `tests/e2e/test_homepage.py::test_header_branding` — update expected tagline from "Offline IOC Extractor" to "IOC Triage Tool" (pre-existing failure from Phase 12)

*(Note: RESULTS-07 shimmer test is flagged as Wave 0 gap, but may be practical only as manual-only due to requiring online enrichment mode.)*

## Sources

### Primary (HIGH confidence)

- Jinja2 official docs — `{% include %}` context inheritance: https://jinja.palletsprojects.com/en/3.1.x/templates/#include — verified that includes share full render context without explicit variable passing
- Project source: `app/static/main.js` lines 418-424 — `.spinner-wrapper` removal logic verified by direct code read
- Project source: `app/static/src/input.css` — `.ioc-card` existing `border-left: 3px solid` implementation verified (RESULTS-08 partially done)
- Project source: `app/templates/macros/icons.html` — `shield-check` already present, `magnifying-glass` absent (verified by read)
- Project source: `tests/e2e/` — full E2E test inventory verified; 3 pre-existing failures identified

### Secondary (MEDIUM confidence)

- CSS shimmer pattern: Established `@keyframes background-position` approach (multiple credible sources agree on this as the correct GPU-composited shimmer technique)
- Heroicons v2 magnifying-glass: Outline icon requires `stroke` not `fill` — verified by knowledge of Heroicons API design (solid icons use fill, outline icons use stroke)

### Tertiary (LOW confidence)

- Performance claim that `background-position` animation avoids layout reflow — technically correct but not profiled in this specific codebase at 50+ card scale

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools already present and verified
- Architecture: HIGH — Jinja2 partials and CSS patterns are stable and well-understood
- JS contracts: HIGH — verified by direct code read of main.js
- Shimmer technique: HIGH — established industry pattern
- Icon stroke/fill issue: MEDIUM — requires resolution during implementation
- Pitfalls: HIGH — derived from direct codebase analysis

**Research date:** 2026-02-28
**Valid until:** 2026-03-28 (stable CSS/Jinja2 domain — 30 days)
