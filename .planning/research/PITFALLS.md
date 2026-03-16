# Pitfalls Research

**Domain:** UI redesign of an existing multi-provider threat intelligence results page
**Researched:** 2026-03-16
**Confidence:** HIGH — based on direct codebase inspection of all E2E tests, page object selectors, TypeScript modules, Jinja templates, and CSS. No external verification needed; pitfalls are structural facts about this specific codebase.

---

## Context: What This Research Covers

SentinelX v1.1 redesigns the results page of a working, tested SOC tool. The goal is cohesive visual
presentation — not new features. The existing system has:

- **91 E2E tests** using Playwright Page Object Model with hard-coded CSS class selectors
- **757+ unit/integration tests** covering enrichment logic, routes, and rendering
- **13 TypeScript modules** compiled by esbuild into a single IIFE bundle
- **Security constraint SEC-08**: all DOM construction uses `createElement + textContent`, never `innerHTML`
- **Tailwind CSS standalone** (no PostCSS, no npm) generating from `app/static/src/input.css`
- A **detail page URL contract** (`/ioc/<type>/<path:value>`) used in the card template

The pitfalls below are calibrated for redesign-without-new-features on this exact system.

---

## Critical Pitfalls

### Pitfall 1: CSS Class Rename Breaks E2E Tests Silently

**What goes wrong:**
The E2E page object (`tests/e2e/pages/results_page.py`) contains 20+ hard-coded CSS class selectors.
If any of these classes are renamed, removed, or restructured as part of the visual redesign, the
corresponding Playwright locator returns zero elements — and the test fails with a timeout rather
than a clear "class not found" error. The failure mode looks like a network or timing problem, not
a selector mismatch, which wastes debugging time.

The locked selectors are:
- `.ioc-card`, `.ioc-card[data-ioc-type]`, `.ioc-card[data-verdict]`, `.ioc-card:visible`
- `.ioc-value`, `.ioc-type-badge`, `.ioc-original`, `.verdict-label`, `.copy-btn`
- `.filter-bar-wrapper`, `.filter-verdict-buttons .filter-btn`, `.filter-type-pills .filter-pill`
- `.filter-search-input`, `.filter-btn--active`, `.filter-pill--active`
- `.ioc-cards-grid` (via `#ioc-cards-grid` locator in `test_extraction.py`)
- `.results-summary .ioc-count`, `.mode-indicator`, `.back-link`, `.empty-state`, `.empty-state-body`
- `#verdict-dashboard`, `.verdict-kpi-card[data-verdict]`, `.provider-coverage-row`
- `.enrichment-slot`, `.enrichment-slot--loaded`, `.chevron-toggle`, `.enrichment-details`

The E2E test for sticky positioning reads computed style directly:
```python
page.evaluate("() => window.getComputedStyle(document.querySelector('.filter-bar-wrapper')).position")
```
This fails if `.filter-bar-wrapper` is renamed or if the sticky class is moved to a child element.

**Why it happens:**
Visual redesigns naturally want to rename classes to reflect new semantic intent (e.g., rename
`.ioc-card` to `.result-card`, rename `.ioc-value` to `.indicator-value`). The developer changes the
template and CSS simultaneously and everything looks correct visually — but E2E tests fail because
the page object still uses the old class names.

**How to avoid:**
Establish a two-class strategy: keep the existing semantic class as a "test anchor" that carries
no visual styles, and add a new class for the visual redesign. Example:
```html
<div class="ioc-card result-card-v2" data-ioc-value="...">
```
The test selects `.ioc-card`; the CSS styles `.result-card-v2`. Alternatively, use `data-testid`
attributes as dedicated test hooks that are immune to CSS renaming. Update the page object to use
`data-testid` selectors before renaming any CSS classes.

**Warning signs:**
- E2E tests suddenly fail with timeout errors after template changes
- `test_filter_bar_has_sticky_position` fails without a Flask error
- `test_cards_have_verdict_labels` reports 0 elements found

**Phase to address:**
Phase 1 of redesign — establish the CSS class preservation contract before touching any template.
Run the full E2E suite after every template change, not just at the end.

---

### Pitfall 2: `data-*` Attribute Contract Broken by Template Restructuring

**What goes wrong:**
The filter logic in `filter.ts` reads `data-verdict`, `data-ioc-type`, and `data-ioc-value` from
`.ioc-card` elements. The enrichment polling in `enrichment.ts` and `cards.ts` reads and writes
`data-verdict`. The E2E tests assert on the values of these attributes directly:

```python
assert visible.get_attribute("data-ioc-value") == "8.8.8.8"
card.get_attribute("data-verdict")  # asserted == "no_data"
```

If the redesign moves these attributes to a wrapper or child element (even while keeping the classes),
the JavaScript breaks silently — filter still runs but matches against empty strings, so all cards
show/hide incorrectly — and E2E tests assert on None instead of the value.

`cards.ts:findCardForIoc()` uses `document.querySelector('.ioc-card[data-ioc-value="..."]')`.
Moving `data-ioc-value` off the `.ioc-card` root element breaks verdict updates and card sorting.

**Why it happens:**
Template restructuring for visual purposes (adding wrapper divs, moving elements into a new grid
layout) does not obviously affect JavaScript behavior. The developer tests visually, sees the card
render correctly, and ships — but the JavaScript was silently reading from elements that no longer
have the expected attributes.

**How to avoid:**
Treat `data-ioc-value`, `data-ioc-type`, and `data-verdict` on `.ioc-card` as an interface contract,
not implementation details. Document them explicitly:
```
CONTRACT: .ioc-card root element MUST carry:
  data-ioc-value="{normalized_ioc_value}"
  data-ioc-type="{ioc_type}"
  data-verdict="{verdict_key}"
These attributes are read by filter.ts, cards.ts, and enrichment.ts.
Moving them to a child element will silently break filtering and verdict updates.
```
Add a unit test that asserts these attributes exist on the root `.ioc-card` element.

**Warning signs:**
- Filter bar buttons have no visual effect after template changes
- Verdict badges never update during enrichment
- Cards always appear/disappear in groups rather than individually

**Phase to address:**
Phase 1 — document the data attribute contract before any template restructuring.

---

### Pitfall 3: Detail Page Link Contract Broken by IOC Value Encoding Change

**What goes wrong:**
Every IOC card contains a "Detail" link generated by Jinja:
```jinja
href="{{ url_for('main.ioc_detail', ioc_type=ioc.type.value, ioc_value=ioc.value) }}"
```
The route uses `<path:ioc_value>` to handle URL IOCs containing slashes. This is a load-bearing
design decision. If the redesign changes how IOC values are displayed or encoded in the template
(e.g., wrapping values in a different element, applying URL encoding in the template rather than
letting Flask handle it, or changing how `ioc.value` is passed), the generated URL may no longer
match the route pattern.

Additionally, `enrichment.ts:findCopyButtonForIoc()` iterates `.copy-btn` elements and matches
`data-value` attributes against the IOC value string. If the copy button is restructured or its
`data-value` attribute is removed during visual cleanup, clipboard copy silently stops working.

**Why it happens:**
`url_for()` looks simple — it just generates a URL. Developers may not realize that the `<path:>`
converter is doing special work for URL-type IOCs (`https://evil.com/path/here`), or that changing
how `ioc.value` flows through the template can break URL generation for edge cases.

**How to avoid:**
Never modify the Jinja expression generating the detail link. The exact form:
```jinja
url_for('main.ioc_detail', ioc_type=ioc.type.value, ioc_value=ioc.value)
```
must be preserved verbatim. Run the URL IOC test from `test_ioc_detail_routes.py` (the
`/ioc/url/https://evil.com/beacon` case) as a smoke test after any template change.

**Warning signs:**
- Detail links for URL-type IOCs return 404
- `test_ioc_detail_routes.py::test_path_converter_handles_url_ioc` fails
- Copy button no longer copies anything after enrichment

**Phase to address:**
Before any template work — preserve the link generation expression and add it to the pre-merge
checklist.

---

### Pitfall 4: Scope Creep Converts a Refinement Milestone into a Feature Milestone

**What goes wrong:**
While redesigning the visual presentation, it becomes tempting to "while I'm here" add new features:
provider grouping by category, collapsible IOC type sections, a summary stats panel, dark/light
mode toggle, annotation-style inline notes, or animated transitions. Each individual addition looks
small, but collectively they add features that:
1. Need new tests written (which requires understanding the feature, not just visual tweaks)
2. Change the data model or routing (which requires backend work)
3. Extend the timeline beyond the stated scope
4. Risk introducing new bugs into a previously stable system

The v1.1 milestone explicitly states: "New features — v1.1 is refinement only." This constraint
exists because the test suite is calibrated to the current behavior. Adding features while redesigning
means updating tests at the same time as changing visual structure — two moving targets simultaneously.

**Why it happens:**
Redesigns offer high creative leverage. Every element is already being touched, so "just add X while
I'm here" feels efficient. The cognitive load of working in a file makes each incremental addition
feel free. It isn't — each addition has a tail cost in testing, documentation, and future maintenance.

**How to avoid:**
Maintain a "deferred features" list. Every idea that goes beyond visual restructuring gets added to
the list, not implemented. The definition of "visual restructuring" is: change that does not require
new Python routes, new TypeScript functions, new template variables, or new test cases. Review the
deferred list at the end of the milestone for a future roadmap item.

**Warning signs:**
- Template starts receiving new Jinja context variables not in the current route
- New TypeScript functions are being written (not modified) during the redesign
- The unit test count is growing, not just the E2E count being updated

**Phase to address:**
Every phase — carry the deferred features list at all times.

---

### Pitfall 5: Information Density Regression in Pursuit of "Cleaner" Design

**What goes wrong:**
SOC analysts use information density deliberately. The current card shows, in one visible state:
IOC value, type badge, verdict label, copy button, detail link, and (when present) the defanged
original. The enrichment slot shows the worst verdict badge, attribution text, and consensus badge
simultaneously before the analyst expands it. Redesigns that reduce visible information to achieve
a "cleaner" aesthetic force analysts to click to see what was previously scannable. Each additional
click per IOC multiplies across a 50-IOC triage session.

Specific information density losses to avoid:
- Removing the verdict label from the card header (visible before enrichment completes)
- Hiding the consensus badge `[3/5]` behind a hover state
- Moving the IOC type badge to a collapsed section
- Replacing the provider-count "3 providers still loading..." with a generic spinner
- Abbreviating or truncating the IOC value in the card header

**Why it happens:**
Designer instinct and general web design patterns optimize for whitespace and minimal visible
information. These patterns apply to consumer apps where users browse. This app is a professional
tool where analysts scan. The aesthetic goal ("cleaner") conflicts with the functional goal ("faster
triage"). Without SOC analyst user testing, the designer defaults to general web aesthetics.

**How to avoid:**
Define information density requirements before redesigning:
1. The IOC value must be fully visible without expansion (no truncation for typical lengths)
2. The verdict label must be visible on the card header before enrichment completes
3. The consensus badge must be visible without hover in the summary row
4. The provider count / "still loading" text must be visible per-card

Treat these as acceptance criteria. Verify each after every visual iteration.

**Warning signs:**
- Card header has fewer visible elements than before the redesign
- Analyst workflow requires more clicks to triage the same set of IOCs
- Information moved to "hover" or "expanded" states was previously always-visible

**Phase to address:**
Phase 1 — write the information density requirements before touching the CSS. Treat them as
non-negotiable acceptance criteria.

---

### Pitfall 6: CSS Specificity Wars Between Tailwind Utilities and BEM Component Classes

**What goes wrong:**
The project uses both Tailwind utility classes (from `input.css` via `@layer utilities`) and
hand-written BEM-style component classes (`.ioc-card`, `.verdict-label`, `.filter-btn`). During
a redesign, adding Tailwind utilities directly to the same elements as the existing component
classes creates specificity conflicts:

1. `@layer components` vs `@layer utilities` — utilities win by default in Tailwind's cascade
2. Adding `!important` to override component styles with utilities propagates everywhere
3. Mixing concerns: the component class handles layout/color/transition while utilities handle
   spacing/typography, with no clear boundary

The existing CSS uses `@layer` blocks in `input.css`. Adding utilities inline in the template
means the compiled `dist/style.css` may not include them if the Tailwind standalone scanner
doesn't find them in the scanned files.

**Why it happens:**
Tailwind's utility-first approach makes quick visual changes easy. Adding `px-4 py-2 rounded-lg`
to a card element works instantly. But when the component class already defines padding and
border-radius, the interaction between the two is unpredictable. Developers add `!important` to
utilities to "fix" overrides, creating a specificity debt that compounds with each iteration.

**How to avoid:**
Follow a single-layer rule for each component: either the component class owns all visual properties,
or Tailwind utilities own them — never both on the same element for the same properties. For this
redesign, the cleanest approach is to update the hand-written component classes in `input.css` and
reserve Tailwind utilities for new layout structures only. Avoid adding Tailwind utilities to
existing elements that already have component classes controlling the same property.

**Warning signs:**
- Adding `!important` to Tailwind utilities to override component class styles
- Same property (e.g., `padding`) defined in both the component class and a Tailwind utility on
  the same element
- `dist/style.css` does not reflect changes made in inline utility classes in templates

**Phase to address:**
CSS architecture decision in Phase 1 — establish which layer owns what before modifying any styles.

---

### Pitfall 7: Accessibility Regressions From Visual Restructuring

**What goes wrong:**
The existing templates have specific accessibility attributes that tests verify:
- Copy buttons: `aria-label="Copy {ioc.value}"` — verified by `test_copy_button_has_aria_label`
- Mode toggle: `aria-pressed` — verified by E2E tests
- Chevron toggle: `aria-expanded="false"` — in `_enrichment_slot.html`, wired by `enrichment.ts`
- Verdict KPI cards: `role="button" tabindex="0"` — keyboard clickable for filter-by-verdict
- Filter search input: `id="filter-search-input"` — referenced by `filter.ts` via `getElementById`

If visual restructuring moves elements, changes element types (e.g., `<div>` to `<span>`), removes
landmark roles, or strips `aria-*` attributes during cleanup, the result is:
1. Screen readers lose context
2. JavaScript wiring breaks (`filter.ts` searches `getElementById("filter-search-input")`)
3. Keyboard navigation fails for the verdict dashboard

The filter search input is doubly coupled: the `id="filter-search-input"` is used by `filter.ts`
(JavaScript) AND the class `.filter-search-input` is used by the E2E page object. Both must be
preserved.

**Why it happens:**
Visual redesigns focus on what's visible. Accessibility attributes are invisible and frequently
stripped during template cleanup as "extra noise." Developers who don't use screen readers or
keyboard navigation do not notice the regression.

**How to avoid:**
Before any template change, catalog every `aria-*`, `role=`, `tabindex`, and `id` attribute in the
results-page templates. Mark each as "JavaScript-coupled", "test-coupled", or "accessibility-only".
Never remove an attribute without checking all three categories. Run the E2E aria label tests
after every template iteration.

**Warning signs:**
- `test_copy_button_has_aria_label` fails
- Filter search input stops responding to typing (JavaScript can't find the element by ID)
- Verdict dashboard KPI cards are not keyboard-focusable

**Phase to address:**
Before template restructuring — audit and catalog all semantic attributes. Include accessibility
verification in the phase acceptance criteria.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Rename CSS classes without updating E2E page objects | Visual redesign feels clean | All filter/copy/navigation E2E tests fail; silent timeout errors | Never — update page object alongside template |
| Move `data-verdict` to a child element for layout reasons | Cleaner card structure | `filter.ts` and `cards.ts` break silently; verdict updates stop working | Never — data attributes on `.ioc-card` root are a contract |
| Add Tailwind utilities on top of existing component classes | Quick visual iteration | Specificity conflicts; `!important` debt; unclear ownership | Only for new elements with no existing component class |
| Copy visual design patterns from consumer apps | Aesthetically polished | Reduced information density; analysts need more clicks per IOC | Only when analyst-facing density requirements are met first |
| Defer E2E test runs to end of redesign phase | Faster iteration | Accumulate multiple breaking changes; harder to isolate regression source | Never — run E2E after each template change |
| Strip "redundant" `id=` or `aria-` attributes during cleanup | Cleaner HTML | JavaScript wiring breaks (`getElementById` fails); accessibility regressions | Never — audit before removing any `id` or `aria-*` |

---

## Integration Gotchas

Common mistakes when modifying the results page in this specific architecture.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Jinja + TypeScript coupling | Renaming a Jinja template variable breaks the JS data attribute read | Treat `data-job-id`, `data-mode`, `data-provider-counts` on `.page-results` as a contract between Flask route and `enrichment.ts:init()` |
| esbuild IIFE bundle | Adding a new TypeScript module without updating `main.ts` init call | `main.ts` calls `init()` for each module; new modules must be registered there or they never execute |
| Tailwind standalone CLI | Adding utility classes in templates that are not scanned | Tailwind standalone scans files listed in its config; ensure templates are included in the content glob |
| `filter.ts` querySelector scope | Moving `.ioc-card` elements outside `#filter-root` | `filter.ts` queries `filterRoot.querySelectorAll(".ioc-card")` — cards outside `#filter-root` are invisible to the filter |
| `enrichment.ts` chevron wiring | Adding new `.enrichment-details` containers with different structure | `wireExpandToggles()` expects `.chevron-toggle` followed by `.enrichment-details` as `nextElementSibling` — structural adjacency is required |
| `cards.ts` CSS.escape selector | IOC values with special characters in `data-ioc-value` | `findCardForIoc()` uses `CSS.escape()` correctly — preserve this pattern; do not change the attribute to an encoded form |

---

## Performance Traps

Patterns that work at small scale but become visible problems with 14 providers across multiple IOCs.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Expensive CSS transitions on cards | Page feels sluggish when 14 providers update 10+ cards simultaneously | Use `will-change: transform` sparingly; avoid transitions on frequently-mutated properties like `border-color` | With 10+ IOCs in online mode; each provider result triggers a card update |
| CSS animations triggered on every verdict update | Cards "flash" as each provider result arrives; visual noise | Gate animation to initial card appearance only (the existing `animation-delay` pattern does this correctly) | From first online enrichment run |
| `sortCardsBySeverity()` triggers a layout reflow | Cards re-order visually mid-enrichment; disorienting | Debounce is already implemented (100ms); do not remove it during cleanup | If debounce is removed, every provider result triggers a DOM reorder |
| Filter reapplication not triggered after DOM changes | Cards added after page load (new IOC types) may not be subject to active filters | `applyFilter()` must be called after any dynamic DOM change that adds `.ioc-card` elements | If redesign adds lazy-loaded card groups |
| Heavy CSS selectors on card grid | Painting performance degrades with many cards | Avoid attribute selectors on inner elements (`.ioc-card .enrichment-slot[data-state="loaded"]`); prefer class selectors | Visible at 20+ IOCs with active enrichment |

---

## Security Mistakes

Domain-specific security issues in the context of this redesign.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Introducing `innerHTML` during visual restructuring | XSS — API responses (IOC values, provider names, stat text) reach the DOM unsanitized | The entire `enrichment.ts` uses `createElement + textContent` (SEC-08). Never replace this with template literals or `innerHTML` for "convenience" during refactoring |
| Using `insertAdjacentHTML` as "safe innerHTML" | Same XSS risk as `innerHTML` | `insertAdjacentHTML` parses HTML; it is not safe for untrusted content. Only `createElement + textContent` is permitted |
| Exposing IOC values in URL fragments for visual effects | Fragment state visible in browser history | Existing architecture does not use fragments for state; do not introduce them during redesign |
| Weakening CSP to allow inline styles added during redesign | Inline `style=` attributes could allow style injection | If a visual effect requires inline `style=`, ensure it uses JavaScript to set `element.style.property = value` (not `innerHTML`), which is CSP-safe |

---

## UX Pitfalls

Common user experience mistakes when redesigning a professional triage tool.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Making verdict colors "softer" for aesthetics | Malicious and suspicious verdicts become hard to distinguish at a glance | Verdict colors are functional, not decorative — keep high-contrast for malicious (red) and suspicious (amber) |
| Removing the "NO DATA" default verdict label before enrichment | Analyst cannot tell if a card failed to load or simply has no data | The `no_data` verdict label serves as a loading state placeholder — preserve it |
| Collapsing the filter bar into a hamburger/dropdown | Filter-by-type and search require more clicks per triage session | The filter bar is used on every session; it must be always-visible (the existing sticky pattern is correct) |
| Adding hover-only tooltips for IOC type badges | Badge meaning is not discoverable for keyboard users or during fast scanning | Abbreviations (IPV4, SHA256) are already standard; if tooltip added, use `<title>` or `aria-label` not CSS-only hover |
| Reordering card elements so Copy precedes the IOC value | Breaks analyst scanning pattern (value first, actions second) | The existing order — value, type, verdict, copy, detail — follows triage priority; preserve it |
| Making the verdict dashboard KPI cards into a collapsed accordion | Removes the at-a-glance summary that makes online mode valuable | The verdict dashboard is always-visible for a reason; collapsing it removes its primary value |

---

## "Looks Done But Isn't" Checklist

Things that appear complete visually but are missing critical pieces.

- [ ] **CSS classes preserved:** Run E2E suite; all 91 tests pass. Zero selector timeouts.
- [ ] **`data-*` contracts:** `.ioc-card` root element carries `data-ioc-value`, `data-ioc-type`, `data-verdict`. Verified by `test_cards_have_data_verdict_attribute` passing.
- [ ] **Filter bar sticky:** `window.getComputedStyle(document.querySelector('.filter-bar-wrapper')).position === 'sticky'`. Verified by `test_filter_bar_has_sticky_position`.
- [ ] **Detail links:** URL IOCs (`https://evil.com/path`) produce working detail page links. Verified by navigating a URL-type IOC's detail link.
- [ ] **Copy button aria-label:** `aria-label="Copy {ioc.value}"` present on every copy button. Verified by `test_copy_button_has_aria_label`.
- [ ] **Filter search ID:** `id="filter-search-input"` on the search input — both test-coupled and JavaScript-coupled. Verify by typing in search and confirming filter applies.
- [ ] **Verdict dashboard:** `#verdict-dashboard` present in online mode, absent in offline mode. Verified by `test_online_mode_shows_verdict_dashboard` and `test_offline_mode_hides_verdict_dashboard`.
- [ ] **`#filter-root` contains all cards:** All `.ioc-card` elements are descendants of `#filter-root`. Verify filtering still works for all card types.
- [ ] **Accessibility:** Verdict KPI cards have `role="button" tabindex="0"`. Chevron toggles have `aria-expanded`. Verify by keyboard-tabbing through the page.
- [ ] **SEC-08 preserved:** No `innerHTML` or `insertAdjacentHTML` introduced. Run `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` — should return zero results.
- [ ] **Information density:** Verdict label, IOC value (full), and type badge visible without any click or hover on every card in offline mode. Verify by visual inspection with 5 IOCs.
- [ ] **No new features:** Template variable list in the route matches the redesigned template's variable usage. No new Python context variables added. Run `grep -n "{{ " app/templates/results.html app/templates/partials/*.html` and compare to route context.

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| E2E tests fail after CSS class rename | MEDIUM | Identify renamed class; either revert rename or add old class as secondary class on element; rerun E2E |
| Data attribute moved off `.ioc-card` root; filter broken | MEDIUM | Move attribute back to root; check `data-ioc-value`, `data-ioc-type`, `data-verdict` are all on the `.ioc-card` element; rerun unit tests for filter |
| Detail link broken for URL-type IOCs | LOW | Restore verbatim `url_for('main.ioc_detail', ioc_type=ioc.type.value, ioc_value=ioc.value)` in `_ioc_card.html`; test with URL IOC |
| Scope crept into new feature | MEDIUM | Extract the feature addition into a separate commit, revert from current branch, add to deferred features list; redesign branch should contain only visual changes |
| Information density regression found in UAT | MEDIUM | Identify which elements moved to collapsed/hover state; restore to always-visible; this is a design revision, not a code bug |
| CSS specificity conflict causes visual breakage | LOW | Remove utility classes from conflicted element; update the component class in `input.css` instead; rebuild CSS |
| `innerHTML` introduced during refactoring | HIGH — security | Revert the change immediately; re-implement using `createElement + textContent` pattern; run `grep -rn "innerHTML" app/static/src/ts/` to confirm no other occurrences |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| CSS class rename breaks E2E tests (Pitfall 1) | Phase 1 — establish class preservation contract before any template edits | Run full 91-test E2E suite; zero failures |
| `data-*` contract broken (Pitfall 2) | Phase 1 — document data attribute contract in a code comment; add unit test | `test_cards_have_data_verdict_attribute` and `test_cards_have_data_ioc_value_attribute` pass |
| Detail page link contract broken (Pitfall 3) | Phase 1 — add URL IOC smoke test to pre-merge checklist | `/ioc/url/https://evil.com/beacon` returns 200; `test_path_converter_handles_url_ioc` passes |
| Scope creep (Pitfall 4) | Every phase — maintain deferred features list; PR description must state "no new features" | Route context variables unchanged; no new TypeScript functions; test count does not grow |
| Information density regression (Pitfall 5) | Phase 1 — write density requirements as acceptance criteria before CSS changes | Visual checklist: verdict label visible, IOC value untruncated, consensus badge visible, all on card without expansion |
| Tailwind/BEM specificity war (Pitfall 6) | Phase 1 CSS architecture decision — single-layer ownership rule established before styling | No `!important` in redesigned CSS; `dist/style.css` reflects all intended visual changes |
| Accessibility regressions (Pitfall 7) | Before template restructuring — catalog all `aria-*`/`role`/`id` attributes | `test_copy_button_has_aria_label`, `aria-expanded` on chevron, `role="button"` on KPI cards all verified |

---

## Sources

- Direct inspection: `tests/e2e/pages/results_page.py` (all CSS selectors the redesign must preserve)
- Direct inspection: `tests/e2e/test_results_page.py` (FILTER-01 through FILTER-04 tests with exact selector dependencies)
- Direct inspection: `tests/e2e/test_extraction.py` (structural attribute tests)
- Direct inspection: `tests/e2e/test_copy_buttons.py` (aria-label contract)
- Direct inspection: `app/templates/partials/_ioc_card.html` (data attribute layout and link generation)
- Direct inspection: `app/templates/partials/_filter_bar.html` (filter bar structure and IDs)
- Direct inspection: `app/templates/partials/_verdict_dashboard.html` (KPI card structure)
- Direct inspection: `app/static/src/ts/modules/filter.ts` (querySelector dependencies on `#filter-root`)
- Direct inspection: `app/static/src/ts/modules/cards.ts` (`findCardForIoc` data attribute contract)
- Direct inspection: `app/static/src/ts/modules/enrichment.ts` (chevron adjacency requirement, SEC-08 pattern)
- Direct inspection: `app/static/src/input.css` (existing CSS layers and component class ownership)
- Direct inspection: `app/templates/ioc_detail.html` (CSS-only tab pattern, `<path:>` URL contract)
- Project constraints: `PROJECT.md` — "New features — v1.1 is refinement only"

---

*Pitfalls research for: SentinelX v1.1 Results Page Redesign — redesigning existing multi-provider threat intel UI*
*Researched: 2026-03-16*
