# Phase 7: Filtering & Search — Research

**Researched:** 2026-02-25
**Domain:** Alpine.js reactive filtering, CSS visibility toggling, sticky positioning
**Confidence:** HIGH

---

## Summary

Phase 7 wires the dormant Alpine.js CSP build (already loaded in `base.html`) into a reactive filter system. The filter bar needs three interactive axes: verdict buttons (All/Malicious/Suspicious/Clean/No Data), IOC type pills (only for types present in results), and a real-time text search box. All filtering must operate exclusively on the client-side DOM using data attributes that Phase 6 already established.

The key architectural insight is that `data-verdict` and `data-ioc-type` attributes on `.ioc-card` elements are already the single source of truth for all styling and counts. Phase 7 builds on this by adding a single Alpine.js component (`x-data`) on the cards container or a wrapper div that maintains filter state and computes card visibility reactively. The filter bar sticks to the viewport via CSS `position: sticky`, and dashboard verdict badges become filter triggers by listening for clicks and setting the active verdict filter.

There is a critical interaction with the existing vanilla JS enrichment polling loop: as enrichment arrives, `data-verdict` attributes update and cards re-sort. The Alpine reactive state must not fight with this — the simplest solution is to keep Alpine for reading filter state and hiding/showing cards, while vanilla JS continues owning `data-verdict` mutations and DOM sort operations. Alpine's `x-show` or CSS class toggling reads the current `data-verdict` on each evaluation cycle, so it naturally picks up changes made by the polling loop.

**Primary recommendation:** Use a single Alpine.js `x-data` component wrapping the filter bar and cards grid. Use `x-show` on each card to reactively show/hide based on current filter state, combined with a CSS `display:none` fallback for zero-JS environments. Keep vanilla JS untouched; Alpine only reads `data-*` attributes, never writes them.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FILTER-01 | Verdict filter bar: All \| Malicious \| Suspicious \| Clean \| No Data — clicking shows only matching cards | Alpine `x-data` state variable `activeVerdict`, `x-show` on cards evaluates `data-verdict` match, active button styled with `:class` binding |
| FILTER-02 | IOC type pills shown only for types present in current results (no phantom pills) | Jinja2 computes unique types server-side at render time; renders only pills that have data. No client-side type detection needed unless dynamic card addition occurs (not the case here — offline mode is static, online mode adds enrichment not new cards) |
| FILTER-03 | Text search input filters cards in real-time by IOC value substring match | Alpine `x-data` `searchQuery` variable, `x-model` on input, `x-show` evaluates `data-ioc-value` `.includes(searchQuery.toLowerCase())` |
| FILTER-04 | Filter bar sticky when scrolling, dashboard badges act as filter shortcuts | CSS `position: sticky; top: 0; z-index: 10` on filter bar container; dashboard badge click sets `activeVerdict` Alpine state via `@click` or vanilla JS event dispatch |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Alpine.js CSP build | 3.14.9 (vendored) | Reactive filtering state, x-show, x-model, x-on | Already loaded in base.html; CSP-compatible (no eval); 45KB vendored file confirmed present |
| Tailwind CSS standalone | 3.4.17 (binary) | Utility classes for sticky bar, filter button states, ring/active styles | Already generating dist/style.css via `make css` |
| Vanilla JS (existing main.js) | ES5-compatible | Enrichment polling, clipboard, sorting — untouched by Phase 7 | Existing, working; Phase 7 adds only filter init code |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| CSS `position: sticky` | Native (no library) | Filter bar stays visible while scrolling | Always — browser support is universal (>97%) |
| CSS `transition` / `display:none` | Native | Smooth hide/show of filtered cards | Use `display:none` for hidden cards (removes from layout); `transition` for button active state |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Alpine.js x-show | Vanilla JS classList toggle | Alpine is already loaded; using it avoids writing a custom reactive system. Vanilla JS alternative would need manual event wiring for each filter dimension |
| Alpine.js x-show | CSS attribute selectors (e.g. `.ioc-cards-grid[data-filter="malicious"] .ioc-card:not([data-verdict="malicious"])`) | CSS-only filtering is possible but cannot combine verdict + type + text search simultaneously |
| Jinja2 server-side type list | Client-side JS type discovery | Server-side is simpler and more reliable — Jinja2 knows exactly which types are present; no need for client-side discovery since cards are static at render time |

**Installation:** No new packages needed. Alpine.js and Tailwind are already present.

---

## Architecture Patterns

### Recommended Structure

The filtering system requires three additions:

```
app/templates/results.html     — add filter bar HTML with Alpine directives
app/static/src/input.css       — add .filter-bar, .filter-btn, sticky styles
app/static/main.js             — add initFilterShortcuts() for dashboard → filter bridge
tailwind.config.js             — add new dynamic class names to safelist if needed
```

No new files. All changes extend existing files.

### Pattern 1: Single Alpine Component Wrapping Filter Bar + Grid

**What:** One `x-data` component object on a wrapper `<div>` that encloses both the filter bar and the cards grid. All filter state lives in this component.

**When to use:** When filter state must be shared between the filter bar (writes state) and the cards grid (reads state).

**Example:**

```html
<!-- Wrapper div owns all filter state -->
<div
  x-data="{
    activeVerdict: 'all',
    activeType: 'all',
    searchQuery: '',
    cardVisible(card) {
      var verdictOk = this.activeVerdict === 'all' || card.dataset.verdict === this.activeVerdict;
      var typeOk    = this.activeType === 'all'    || card.dataset.iocType === this.activeType;
      var searchOk  = this.searchQuery === ''      || card.dataset.iocValue.toLowerCase().includes(this.searchQuery.toLowerCase());
      return verdictOk && typeOk && searchOk;
    }
  }"
  id="filter-root"
>
  <!-- Filter bar -->
  <div class="filter-bar">
    <button @click="activeVerdict = 'all'"       :class="{ 'filter-btn--active': activeVerdict === 'all' }"       class="filter-btn">All</button>
    <button @click="activeVerdict = 'malicious'" :class="{ 'filter-btn--active': activeVerdict === 'malicious' }" class="filter-btn filter-btn--malicious">Malicious</button>
    <!-- ... etc ... -->
  </div>

  <!-- Cards grid — x-show on each card -->
  <div class="ioc-cards-grid" id="ioc-cards-grid">
    {% for ioc_type, iocs in grouped.items() %}
      {% for ioc in iocs %}
      <div class="ioc-card"
           data-ioc-value="{{ ioc.value }}"
           data-ioc-type="{{ ioc.type.value }}"
           data-verdict="no_data"
           x-show="cardVisible($el)"
      >
        <!-- card content unchanged -->
      </div>
      {% endfor %}
    {% endfor %}
  </div>
</div>
```

**Critical constraint:** `$el` inside `cardVisible()` refers to the element the directive is on — this works in Alpine v3. The function reads `dataset` attributes directly from the DOM element.

### Pattern 2: Dashboard Badge Click-to-Filter via Custom Event

**What:** Dashboard verdict badges are rendered inside the `verdict-dashboard` div, which is outside the Alpine component (it's above the filter bar in the DOM). To bridge dashboard clicks to Alpine filter state, use a custom DOM event or a shared data store.

**Options (ranked):**

1. **Move dashboard inside the Alpine wrapper** — simplest, but requires restructuring HTML
2. **Alpine.store + $store** — Alpine global store accessible anywhere on the page
3. **Custom DOM event bridge** — vanilla JS dispatches a `CustomEvent`; Alpine listens with `@filter-verdict.window`

Option 1 (move dashboard into wrapper) is the cleanest — the verdict dashboard can live inside `#filter-root` since it's also part of the results section.

Option 3 example (if restructuring isn't possible):
```javascript
// In main.js or a new filter-bridge section
document.querySelectorAll('.verdict-dashboard-badge').forEach(function(badge) {
    badge.addEventListener('click', function() {
        var verdict = badge.getAttribute('data-verdict');
        window.dispatchEvent(new CustomEvent('set-verdict-filter', { detail: verdict }));
    });
});
```
```html
<!-- In Alpine component -->
<div x-data="{ ... }" @set-verdict-filter.window="activeVerdict = $event.detail">
```

**Recommended: Move dashboard inside Alpine wrapper.** This avoids event bus complexity and keeps everything in one reactive scope.

### Pattern 3: IOC Type Pills — Server-Side Presence Detection

**What:** Jinja2 computes the set of IOC types in the current results and renders only type pills for types that exist.

**Why server-side:** The `grouped` dict passed to the template already contains only types with results. No client-side discovery needed.

```html
<!-- In filter bar, after verdict buttons -->
<div class="filter-type-pills">
  <button @click="activeType = 'all'" :class="{ 'filter-pill--active': activeType === 'all' }" class="filter-pill">All Types</button>
  {% for ioc_type in grouped.keys() %}
  <button
    @click="activeType = '{{ ioc_type }}'"
    :class="{ 'filter-pill--active': activeType === '{{ ioc_type }}' }"
    class="filter-pill filter-pill--{{ ioc_type }}"
  >{{ ioc_type | upper }}</button>
  {% endfor %}
</div>
```

### Pattern 4: Text Search — Real-Time with Alpine x-model

**What:** Input element bound to `searchQuery` via `x-model`. Cards evaluate `searchQuery` in their `x-show` expression. Alpine batches DOM updates via `queueMicrotask`, so response is effectively synchronous with user typing.

```html
<input
  type="search"
  x-model="searchQuery"
  placeholder="Search IOCs..."
  class="filter-search-input"
  autocomplete="off"
/>
```

The `cardVisible()` function already incorporates `searchQuery` in the pattern above. No debouncing is required at 50-100 cards — Alpine's microtask batching keeps updates well under 100ms.

### Pattern 5: Sticky Filter Bar

**What:** CSS `position: sticky; top: 0` on the filter bar container. Requires the filter bar's parent to have a defined scroll context (the page body in this case).

```css
.filter-bar-wrapper {
    position: sticky;
    top: 0;
    z-index: 10;
    background-color: var(--bg-primary); /* Prevent content bleed-through */
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1rem;
}
```

**Gotcha:** `position: sticky` does not work if any ancestor has `overflow: hidden` or `overflow: auto`. The current `.site-main` uses `flex: 1` with no overflow restriction — sticky will work as-is.

### Anti-Patterns to Avoid

- **x-show with CSS transitions that break layout:** `x-show` adds `display:none` when false, which removes the card from the grid layout correctly. Do not use `opacity: 0` + `pointer-events: none` for hidden cards — it leaves visual gaps in the grid.
- **Debouncing search:** At 50-100 cards, Alpine's microtask batching is sufficient. Adding a manual debounce adds complexity for no perceptible benefit.
- **Separate Alpine components for filter bar and cards grid:** Filter state must be shared. One wrapper component is the correct pattern.
- **Writing `data-verdict` from Alpine:** Never — Alpine reads `data-verdict`, only the vanilla JS polling loop writes it. Two-way conflicts would break enrichment.
- **`innerHTML` for filter pill labels:** All template strings use Jinja2 autoescaping. IOC type values are controlled enum strings (`ioc.type.value`), safe to render as Jinja2 expressions.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Reactive state binding | Custom JS event system with listeners per filter dimension | Alpine.js x-data / x-show / x-model | Already loaded; handles batching, reactivity, and DOM diffing correctly |
| Active button highlighting | Manual JS `classList.add/remove('active')` on every click | Alpine `:class` binding | Declarative, zero JS imperative code, automatically consistent |
| Search input debouncing | `setTimeout` debounce wrapper | Alpine x-model (uses microtask batching) | Sufficient performance at this scale; no extra code needed |
| Type pill discovery | JS loop to find unique `data-ioc-type` values | Jinja2 `grouped.keys()` in template | Server already has this data; no runtime DOM scanning needed |

**Key insight:** Alpine.js was loaded in Phase 6 specifically to avoid building a custom reactive filter system. Use it as designed.

---

## Common Pitfalls

### Pitfall 1: Alpine Not Initializing on Dynamic DOM Changes

**What goes wrong:** The enrichment polling loop appends and modifies DOM elements inside `.ioc-card`. Alpine only initializes directives for elements present at page load (or elements created via `x-for`/`$nextTick`). If Alpine directives are on static Jinja2-rendered cards, this is fine — they're present at load time.

**Why it happens:** Alpine v3 uses a MutationObserver to detect new elements with `x-` directives, but `x-show` evaluates at init time and re-evaluates when reactive state changes, not when the underlying `data-verdict` attribute changes via vanilla JS.

**How to avoid:** The `cardVisible()` function reads `$el.dataset.verdict` at the moment it's called. Since Alpine re-evaluates `x-show` expressions when reactive state changes (i.e., when the user clicks a filter button), the current `data-verdict` is always read fresh from the DOM. This is correct behavior — no special handling needed.

**Warning signs:** If filtering shows stale verdicts after enrichment completes, the issue is that `cardVisible()` isn't being re-invoked. Solution: call `Alpine.store()` or use a reactive counter to force re-evaluation after enrichment completes (advanced, probably not needed).

### Pitfall 2: Tailwind Safelist Gaps for Dynamic Filter Classes

**What goes wrong:** Filter button active states use dynamic class names like `filter-btn--active`, `filter-pill--active`, `filter-pill--ipv4`. If these are only present in Alpine `:class` bindings (evaluated at runtime), Tailwind's content scanner won't detect them and they'll be purged from the generated CSS.

**Why it happens:** Tailwind scans source files for class name strings. Alpine `:class="{ 'filter-btn--active': ... }"` embeds class names as JS object keys — Tailwind may or may not detect these depending on how the expression is formatted.

**How to avoid:** Add all dynamic filter class names to `tailwind.config.js` safelist, the same way Phase 6 added `ioc-type-badge--*` and `verdict-label--*` classes.

```javascript
// tailwind.config.js safelist additions for Phase 7:
"filter-btn--active",
"filter-pill--active",
"filter-pill--ipv4",
"filter-pill--ipv6",
"filter-pill--domain",
"filter-pill--url",
"filter-pill--md5",
"filter-pill--sha1",
"filter-pill--sha256",
"filter-pill--cve",
```

**Warning signs:** Filter buttons visually don't show active state after clicking, even though Alpine state is correct (verified via browser DevTools).

### Pitfall 3: x-show vs x-if — Choosing the Right Directive

**What goes wrong:** Using `x-if` instead of `x-show` removes elements from the DOM entirely when false. This breaks the enrichment polling loop, which finds cards by `querySelector('.ioc-card[data-ioc-value="..."]')`. If cards are removed by `x-if`, the polling loop can't update them.

**Why it happens:** `x-if` performs DOM removal; `x-show` adds `display: none` but leaves the element in the DOM.

**How to avoid:** Use `x-show` exclusively on `.ioc-card` elements. Never use `x-if` for card visibility.

### Pitfall 4: `position: sticky` Broken by Ancestor Overflow

**What goes wrong:** The filter bar doesn't stick — it scrolls with the content.

**Why it happens:** `position: sticky` requires no ancestor element to have `overflow: hidden`, `overflow: auto`, or `overflow: scroll`. An ancestor with any of these values creates a new scroll context, trapping the sticky element.

**How to avoid:** Inspect `.site-main` and all ancestors in the DOM. The current CSS shows `flex: 1` on `.site-main` with no overflow properties set — sticky will work. If a future change adds overflow to an ancestor, sticky breaks silently.

### Pitfall 5: Filter Bar + Verdict Dashboard Ordering Conflict

**What goes wrong:** FILTER-04 requires dashboard badges to act as filter shortcuts. The dashboard is currently rendered conditionally (`{% if mode == "online" and job_id %}`). If the filter bar wrapper (`x-data`) is placed below the dashboard, the dashboard badges cannot directly access Alpine state.

**Why it happens:** Alpine scope is hierarchical — child elements can access parent `x-data`, but sibling or parent elements cannot access a child's `x-data`.

**How to avoid:** Place the `x-data` wrapper to encompass both the verdict dashboard and the filter bar. Move the Alpine component root to wrap the entire results section below the progress bar.

---

## Code Examples

### Minimal Alpine Filter Component (verified pattern for Alpine v3)

```html
<div x-data="{
  activeVerdict: 'all',
  activeType: 'all',
  searchQuery: '',
  cardVisible(card) {
    var v = this.activeVerdict === 'all' || card.dataset.verdict === this.activeVerdict;
    var t = this.activeType === 'all' || card.dataset.iocType === this.activeType;
    var s = this.searchQuery === '' || card.dataset.iocValue.toLowerCase().includes(this.searchQuery.toLowerCase());
    return v && t && s;
  }
}">
  <!-- filter bar and cards live here -->
</div>
```

Note: `data-ioc-type` becomes `dataset.iocType` in JS (camelCase conversion is automatic).

### Sticky Filter Bar CSS

```css
.filter-bar-wrapper {
    position: sticky;
    top: 0;
    z-index: 10;
    background-color: var(--bg-primary);
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1rem;
}
```

### Verdict Dashboard Badge as Filter Shortcut

The verdict dashboard is conditionally rendered only in online mode. The simplest approach:

```html
<!-- Make the dashboard badge clickable -->
<span class="verdict-dashboard-badge"
      data-verdict="malicious"
      @click="activeVerdict = activeVerdict === 'malicious' ? 'all' : 'malicious'"
      style="cursor: pointer;"
      role="button"
      tabindex="0"
>
  <span class="verdict-dashboard-count" data-verdict-count="malicious">0</span> Malicious
</span>
```

Click once → sets `activeVerdict = 'malicious'`. Click again → resets to `'all'` (toggle behavior). This is intuitive: clicking the dashboard badge applies the filter; clicking again clears it.

### x-show on Card (integrating with existing Jinja2 template)

```html
<div class="ioc-card"
     data-ioc-value="{{ ioc.value }}"
     data-ioc-type="{{ ioc.type.value }}"
     data-verdict="no_data"
     x-show="cardVisible($el)"
>
```

### Filter Button with Active State

```html
<button
  class="filter-btn"
  :class="{ 'filter-btn--active': activeVerdict === 'malicious', 'filter-btn--malicious': true }"
  @click="activeVerdict = activeVerdict === 'malicious' ? 'all' : 'malicious'"
  type="button"
>Malicious</button>
```

Toggle behavior (click again to deselect) is more discoverable than requiring an explicit "All" click.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| jQuery `.hide()` / `.show()` | Alpine.js `x-show` | ~2020 | No jQuery dependency; declarative, CSP-compatible |
| CSS-only filtering via `:checked` + sibling selectors | Alpine reactive state | ~2021 | Cannot combine multiple filter dimensions with CSS-only; Alpine is necessary |
| `document.querySelectorAll` loop + manual style changes | Alpine `x-show` evaluation | Phase 7 | Alpine handles update batching and re-evaluation automatically |

**Deprecated/outdated:**
- jQuery filter plugins: Not appropriate here (no jQuery in project, CSP restrictions)
- Server-side filter requests (fetch/reload per filter change): Too slow; 100+ IOC list requires instant client-side filtering

---

## Open Questions

1. **Offline mode: show filter bar even when no dashboard?**
   - What we know: The verdict dashboard only renders in online mode with a job_id. In offline mode, all cards have `data-verdict="no_data"`, so verdict filtering would mostly be useless (only "All" and "No Data" would show cards).
   - What's unclear: Should the filter bar render in offline mode? Or only in online mode?
   - Recommendation: Render the filter bar in both modes. In offline mode, verdict filtering degrades gracefully — "All" shows everything, "No Data" shows all cards, other verdicts show nothing. This is correct and consistent behavior. The text search and type filtering are useful in offline mode.

2. **Filter state persistence across enrichment sort events**
   - What we know: The vanilla JS `sortCardsBySeverity()` reorders cards using `grid.appendChild()`. Alpine's `x-show` is attached to individual card elements, not their DOM position. Re-ordering via `appendChild` does not affect `x-show` state.
   - What's unclear: Does Alpine re-evaluate `x-show` after DOM re-ordering?
   - Recommendation: Alpine v3 uses a MutationObserver approach — `x-show` state is stored per-element, not position-dependent. Moving elements with `appendChild` preserves Alpine state on those elements. No issue expected, but should be verified in E2E testing.

3. **Empty filter results state**
   - What we know: If a user applies a verdict filter with no matching cards, the grid will appear empty.
   - What's unclear: Should an empty-filter state message be shown?
   - Recommendation: Add a simple "No cards match the current filter" message using Alpine `x-show` that appears when all cards are hidden. This is a nice UX touch but not in the requirements — defer if time-constrained.

---

## Sources

### Primary (HIGH confidence)

- Alpine.js v3 official documentation (alpinejs.dev) — `x-data`, `x-show`, `x-model`, `x-on`, `:class` patterns; `$el` magic property in directives
- Existing codebase inspection — Phase 6 `.continue-here.md`, `results.html`, `main.js`, `input.css`, `tailwind.config.js`
- MDN Web Docs — `position: sticky` browser support and ancestor overflow constraints
- Alpine.js CSP build v3.14.9 confirmed present at `/home/chris/projects/sentinelx/app/static/vendor/alpine.csp.min.js` (45,328 bytes)

### Secondary (MEDIUM confidence)

- Alpine.js `$el` in x-show — pattern is consistent with Alpine v3 documentation; `$el` refers to the element the directive is attached to, enabling reading of the element's `dataset` properties
- CSS `position: sticky` + flex parent compatibility — confirmed working with `flex: 1` parent (`.site-main`); no overflow restrictions in current CSS

### Tertiary (LOW confidence)

- Alpine MutationObserver behavior after `appendChild` reordering — inferred from Alpine v3 architecture; should be validated with a targeted E2E test

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Alpine.js vendored and confirmed; no new dependencies required
- Architecture: HIGH — data attributes established in Phase 6 are directly usable; Alpine x-show/x-data pattern is well-understood
- Pitfalls: HIGH — Tailwind safelist gap and x-show vs x-if are concrete, verifiable risks with clear mitigations

**Research date:** 2026-02-25
**Valid until:** 2026-08-25 (stable — Tailwind v3.x and Alpine v3.x are not moving quickly)
