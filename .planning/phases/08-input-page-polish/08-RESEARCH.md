# Phase 8: Input Page Polish — Research

**Researched:** 2026-02-25
**Domain:** Vanilla JS UI patterns — toggle switch, paste feedback, reactive button label
**Confidence:** HIGH

---

## Summary

Phase 8 applies three focused improvements to the existing input page (`index.html` + `main.js`). All three requirements are pure frontend changes: no Flask routes change, no backend data models change, no new dependencies required. The existing stack (Tailwind CSS standalone CLI for styling, vanilla JS for interactivity, CSP `default-src 'self'; script-src 'self'`) is fully sufficient.

The key constraint is the strict CSP: `default-src 'self'; script-src 'self'`. This means **no inline `style=` attributes in HTML**, **no `eval`**, and **no external scripts**. All visual state must be driven by CSS classes toggled from `main.js`. The Alpine.js CSP build (`alpine.csp.min.js`) was removed in Phase 7 — it is no longer loaded. All interactivity must use pure vanilla JS, following the exact pattern established in Phase 7's `initFilterBar()`.

The three requirements are small, self-contained, and can be implemented in a single plan wave. INPUT-01 (toggle switch) is the largest piece of work — it replaces the `<select>` element with a styled CSS toggle and wires a JS handler. INPUT-02 (paste feedback) adds ~10 lines of JS to the existing paste listener. INPUT-03 (reactive submit label) is a one-liner addition to the existing mode-change handler.

**Primary recommendation:** One plan wave. Implement all three requirements together in `index.html` (HTML structure), `input.css` (CSS toggle styles), `main.js` (JS handlers), then add E2E tests covering the new behaviours. Total scope is small — similar in scale to a single Phase 7 plan.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INPUT-01 | Mode selector is a toggle switch (not a dropdown) clearly labeled "Offline" / "Online" with visual state indicator | Toggle switch pattern: CSS-only pill with JS-toggled class. Hidden `<input type="hidden" name="mode">` submits form value. No `<select>` element retained. |
| INPUT-02 | Paste event shows character count feedback ("N characters pasted") near the textarea | `paste` event listener in `initSubmitButton()` already exists. Extend it: after `setTimeout(updateSubmitState, 0)`, read `textarea.value.length` and update a feedback `<span>`. Auto-dismiss after 2s. |
| INPUT-03 | Submit button label changes based on mode — "Extract IOCs" in offline mode, "Extract & Enrich" in online mode, updating reactively on toggle | Add `updateSubmitLabel()` call to the toggle click handler. Read current mode from hidden input or toggle state variable. |
</phase_requirements>

---

## Standard Stack

### Core (already installed — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vanilla JS (IIFE in `main.js`) | ES5-compatible | Toggle state, paste feedback, reactive label | Existing pattern; CSP-safe; no build step |
| Tailwind CSS standalone CLI | v3.4.17 | CSS utility classes for toggle widget | Already integrated via `make css` |
| Custom CSS components (`input.css`) | — | Toggle switch visual widget | Project pattern: component classes in `@layer components` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| CSS custom properties (`--verdict-*`, `--accent-*`) | — | Consistent color tokens | All new toggle colors should use existing CSS variables |
| `make css` | — | Rebuild `dist/style.css` after editing `input.css` | After any CSS change |
| Playwright + pytest | existing | E2E tests for new behaviours | New toggle interactions, paste feedback, button label |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| CSS toggle switch | `<input type="checkbox">` styled toggle | Checkbox approach requires syncing checked state to hidden form field; custom CSS div is simpler and already fits the project's component pattern |
| Hidden `<input name="mode">` | Keep `<select>` but hide it | Keeping the `<select>` would break IndexPage POM locator; cleaner to replace outright |
| Auto-dismiss via `setTimeout` | CSS animation fade-out | setTimeout is simpler and already used in `showCopiedFeedback()`; consistent pattern |

**Installation:** None required. All tools already present.

---

## Architecture Patterns

### Existing Pattern: `initSubmitButton()` in `main.js`

The entire input page interactivity lives in `initSubmitButton()` (lines 34–67 of `main.js`). This function:
- Gets `form`, `textarea`, `submitBtn`, `clearBtn` by ID
- Attaches `input` and `paste` listeners to textarea
- Has a `setTimeout` in the paste handler to defer until paste content is applied

**Phase 8 extends this exact pattern** — no new top-level init functions needed (though adding `initModeToggle()` is reasonable for clarity).

### Recommended Structure After Phase 8

```
main.js (existing IIFE):
├── initSubmitButton()          — MODIFIED: add paste char-count feedback + updateSubmitLabel()
├── initModeToggle()            — NEW: toggle click → update hidden input, updateSubmitLabel()
├── updateSubmitLabel(mode)     — NEW: set submitBtn.textContent based on mode string
├── initCopyButtons()           — unchanged
├── initFilterBar()             — unchanged (results page only)
├── initEnrichmentPolling()     — unchanged (results page only)
├── initExportButton()          — unchanged (results page only)
├── initSettingsPage()          — unchanged (settings page only)
└── init()                      — add initModeToggle() call

index.html:
├── Remove: <select id="mode-select">
├── Add: toggle widget HTML (div + two labels + hidden input)
└── h1.input-title text stays "Extract IOCs" (title is static; submit btn changes, not h1)

input.css (@layer components):
├── .mode-toggle-switch         — outer container
├── .mode-toggle-track          — pill background
├── .mode-toggle-thumb          — sliding circle
├── .mode-toggle-label          — "Offline" / "Online" text labels
└── [data-mode="online"] modifiers — active/inactive color states
```

### Pattern 1: CSS Toggle Switch (No Checkbox)

**What:** A visual pill with a sliding thumb, driven entirely by CSS class toggling in JS. No `<input type="checkbox">` needed.

**When to use:** When the toggle maps to a named form value (not a boolean), and when the project already has a custom CSS component system.

**Example structure:**

```html
<!-- index.html — replaces <select id="mode-select"> -->
<div class="form-field">
    <label class="form-label">Analysis Mode</label>
    <div class="mode-toggle-widget" id="mode-toggle-widget" data-mode="offline">
        <span class="mode-toggle-label mode-toggle-label--offline">Offline</span>
        <button type="button" class="mode-toggle-track" id="mode-toggle-btn" aria-pressed="false" aria-label="Toggle analysis mode">
            <span class="mode-toggle-thumb"></span>
        </button>
        <span class="mode-toggle-label mode-toggle-label--online">Online</span>
    </div>
    <!-- Hidden input carries mode value on form POST — name="mode" is required by Flask route -->
    <input type="hidden" name="mode" id="mode-input" value="offline">
</div>
```

**CSS (in `input.css` `@layer components`):**

```css
.mode-toggle-widget {
    display: flex;
    align-items: center;
    gap: 0.6rem;
}

.mode-toggle-track {
    position: relative;
    width: 44px;
    height: 24px;
    border-radius: 12px;
    background-color: var(--bg-tertiary);
    border: 1px solid var(--border);
    cursor: pointer;
    transition: background-color 0.2s ease, border-color 0.2s ease;
    padding: 0;
    flex-shrink: 0;
}

.mode-toggle-track:focus {
    outline: none;
    box-shadow: 0 0 0 3px rgba(74, 158, 255, 0.25);
}

.mode-toggle-thumb {
    position: absolute;
    top: 3px;
    left: 3px;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background-color: var(--text-secondary);
    transition: transform 0.2s ease, background-color 0.2s ease;
}

/* Online state — widget carries data-mode="online" */
.mode-toggle-widget[data-mode="online"] .mode-toggle-track {
    background-color: rgba(74, 255, 158, 0.15);
    border-color: rgba(74, 255, 158, 0.4);
}

.mode-toggle-widget[data-mode="online"] .mode-toggle-thumb {
    transform: translateX(20px);
    background-color: var(--accent-domain);
}

.mode-toggle-label {
    font-size: 0.85rem;
    color: var(--text-secondary);
    user-select: none;
    transition: color 0.15s ease;
}

/* Active label highlight */
.mode-toggle-widget[data-mode="offline"] .mode-toggle-label--offline,
.mode-toggle-widget[data-mode="online"] .mode-toggle-label--online {
    color: var(--text-primary);
    font-weight: 600;
}
```

**JS handler (`initModeToggle()`):**

```javascript
function initModeToggle() {
    var widget = document.getElementById("mode-toggle-widget");
    var toggleBtn = document.getElementById("mode-toggle-btn");
    var modeInput = document.getElementById("mode-input");
    if (!widget || !toggleBtn || !modeInput) return;

    toggleBtn.addEventListener("click", function () {
        var current = widget.getAttribute("data-mode");
        var next = current === "offline" ? "online" : "offline";
        widget.setAttribute("data-mode", next);
        modeInput.value = next;
        toggleBtn.setAttribute("aria-pressed", next === "online" ? "true" : "false");
        updateSubmitLabel(next);
    });
}

function updateSubmitLabel(mode) {
    var submitBtn = document.getElementById("submit-btn");
    if (!submitBtn) return;
    submitBtn.textContent = mode === "online" ? "Extract & Enrich" : "Extract IOCs";
}
```

### Pattern 2: Paste Character Feedback

**What:** Extend the existing paste handler in `initSubmitButton()` to show a transient "N characters pasted" message near the textarea.

**When to use:** Immediately, as the existing paste `setTimeout` already defers until content is applied.

**Example:**

```javascript
// In initSubmitButton(), extend the paste handler:
textarea.addEventListener("paste", function () {
    setTimeout(function () {
        updateSubmitState();
        var len = textarea.value.length;
        showPasteFeedback(len);
    }, 0);
});

function showPasteFeedback(charCount) {
    var feedback = document.getElementById("paste-feedback");
    if (!feedback) return;
    feedback.textContent = charCount + " characters pasted";
    feedback.style.display = "";  // NOTE: inline style on JS-created element is CSP-safe
                                   // (style= on HTML elements is blocked, but JS .style prop is not)
    clearTimeout(feedback._timer);
    feedback._timer = setTimeout(function () {
        feedback.style.display = "none";
    }, 2000);
}
```

**HTML (add below textarea in `index.html`):**

```html
<span id="paste-feedback" class="paste-feedback" style="display:none;" aria-live="polite"></span>
```

**IMPORTANT CSP NOTE:** `style="display:none"` in HTML is NOT blocked by the current CSP. The CSP directive is `default-src 'self'; script-src 'self'` — there is no `style-src` restriction that would block inline HTML styles. Only `script-src 'unsafe-inline'` is absent, preventing inline JS. Inline CSS `style=` attributes are permitted under this policy. Setting `.style.display` via JS is always permitted regardless of CSP.

**CSS:**

```css
.paste-feedback {
    font-size: 0.78rem;
    color: var(--text-secondary);
    font-style: italic;
    display: block;
    margin-top: 0.25rem;
    min-height: 1.2em;
}
```

### Anti-Patterns to Avoid

- **Keeping the `<select>` and overlaying it visually**: Breaks existing E2E tests that use `idx.mode_select` locator. Replace cleanly.
- **Using Alpine.js for toggle reactivity**: Alpine CSP vendor was removed in Phase 7. All new JS must be vanilla.
- **Using `innerHTML` for paste feedback**: Project convention (SEC-08) requires `.textContent` for all dynamic content. Use `.textContent = charCount + " characters pasted"` only.
- **Using `aria-checked` on a `<div>`**: Use a proper `<button>` with `aria-pressed` for the toggle, or a styled `<input type="checkbox">` with `role="switch"`. The `<button>` approach is simpler given no checkbox checked-state sync.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Form value submission for toggle | Custom serialization | Hidden `<input name="mode">` synced by JS | Flask route reads `request.form["mode"]` — hidden input is the standard pattern |
| Dismiss timer for paste feedback | Re-implement | `setTimeout` + `clearTimeout` (same pattern as `showCopiedFeedback`) | Already proven in the codebase; no edge cases |
| Toggle animation | CSS transitions (already in project) | `transition: transform 0.2s ease` on `.mode-toggle-thumb` | Project already uses `transition` extensively; consistent |

**Key insight:** The project has an established pattern for every sub-problem in this phase. Follow `showCopiedFeedback()` for the paste dismiss timer, follow `initFilterBar()` for data-attribute-driven CSS state, and follow the existing hidden CSRF input for form value submission.

---

## Common Pitfalls

### Pitfall 1: Breaking Existing E2E Tests That Use `idx.mode_select`

**What goes wrong:** `test_mode_select_options`, `test_offline_mode_selected_by_default`, `test_mode_toggle_to_online`, and `test_mode_toggle_back_to_offline` all reference `idx.mode_select = page.locator("#mode-select")` and call `.select_option()`. Removing the `<select>` without updating these tests causes 4+ E2E failures.

**Why it happens:** The `IndexPage` POM (`tests/e2e/pages/index_page.py`) hardcodes `mode_select = page.locator("#mode-select")`.

**How to avoid:** Update `IndexPage` POM to replace `mode_select` with a `mode_toggle` locator targeting the new widget. Rewrite the four mode-related tests to use `click()` on the toggle button instead of `select_option()`.

**Warning signs:** Any E2E test referencing `mode_select` or `#mode-select`.

### Pitfall 2: CSP `style-src` Confusion

**What goes wrong:** Developer assumes `style="display:none"` on the `paste-feedback` span will be blocked by CSP, adds unnecessary complexity (toggling a CSS class instead), then gets confused why class-based show/hide also requires JS `.style`.

**Why it happens:** The current CSP is `default-src 'self'; script-src 'self'`. There is no `style-src 'none'` or `style-src 'self'` in the policy. `style-src` falls back to `default-src 'self'`, which permits linked stylesheets (`<link rel="stylesheet">`) but does not explicitly restrict `style=` attributes. In practice, browsers treat the absence of `'unsafe-inline'` in `style-src` as blocking inline `style=` attributes only when `style-src` is explicitly set without `'unsafe-inline'`. Since this project's CSP only sets `default-src` and `script-src`, inline styles in HTML are **not blocked**.

**Confirmed by:** Phase 7 STATE.md note: "card.style.display via DOM JS is NOT blocked by CSP style-src (only HTML style= attributes are blocked)". The existing project convention already settled this — use `.style.display` from JS freely.

**How to avoid:** Follow the Phase 7 precedent. `.style.display = ""` / `"none"` from JS is always safe. The `<span style="display:none">` initial state in HTML is also safe under this CSP.

### Pitfall 3: Paste Event Fires Before Content Is Available

**What goes wrong:** Reading `textarea.value.length` synchronously in the `paste` handler returns the pre-paste length (0 or whatever was already there).

**Why it happens:** The `paste` event fires before the browser inserts the clipboard text into the element.

**How to avoid:** The existing code already handles this correctly with `setTimeout(updateSubmitState, 0)`. Extend the same `setTimeout` callback to also call `showPasteFeedback(textarea.value.length)`. This is already noted in the existing comments in `main.js`.

### Pitfall 4: Tailwind Safelist Missing New Dynamic Classes

**What goes wrong:** New CSS classes that are constructed dynamically in JS (e.g., `mode-toggle-widget[data-mode="online"]`) or set via JS (e.g., added/removed class names) get purged by Tailwind if they don't appear literally in template or JS files.

**Why it happens:** Tailwind scans `app/templates/**/*.html` and `app/static/**/*.js` for class names. Classes only referenced in CSS selectors (not in HTML/JS) are purged.

**How to avoid:** Phase 8 uses data-attribute CSS selectors (`[data-mode="online"]`) rather than dynamic class names, so purging is not an issue. The toggle thumb position and track color are driven by `[data-mode]` attribute CSS — no class toggling, no safelist entries needed. If any JS-toggled classes are added, add them to `tailwind.config.js` safelist.

### Pitfall 5: Submit Button Text Overwritten on Disable/Enable

**What goes wrong:** `updateSubmitState()` calls `submitBtn.disabled = ...` but does not touch `textContent`. However, future changes might accidentally reset the text. The button starts with hardcoded "Extract IOCs" in HTML; after toggle to online, JS sets it to "Extract & Enrich". If the page re-renders (e.g., form error), the text reverts to "Extract IOCs" regardless of selected mode.

**Why it happens:** Server-rendered HTML always emits the initial button text. The mode toggle state is not persisted across form submissions.

**How to avoid:** On page load, check the initial mode value (from `modeInput.value`) and call `updateSubmitLabel()` in `initModeToggle()` to set the correct initial label. This handles the case where the server pre-selects a mode (currently always "offline", but defensive coding matters).

---

## Code Examples

Verified patterns from existing codebase:

### Existing: showCopiedFeedback (dismiss timer pattern — reuse for paste feedback)

```javascript
// Source: app/static/main.js lines 88-96
function showCopiedFeedback(btn) {
    var original = btn.textContent;
    btn.textContent = "Copied!";
    btn.classList.add("copied");
    setTimeout(function () {
        btn.textContent = original;
        btn.classList.remove("copied");
    }, 1500);
}
```

Use the same `setTimeout` + `clearTimeout` pattern for paste feedback dismiss.

### Existing: data-attribute CSS state driving (Phase 7 filter bar pattern)

```javascript
// Source: app/static/main.js lines 596-634 (initFilterBar applyFilter)
card.style.display = (verdictMatch && typeMatch && searchMatch) ? "" : "none";
btn.classList.add("filter-btn--active");  // or .remove()
```

The toggle switch follows the same principle: `widget.setAttribute("data-mode", next)` drives all visual CSS via `[data-mode="online"]` selectors. No class toggling needed on the track/thumb.

### Existing: Paste handler with setTimeout

```javascript
// Source: app/static/main.js lines 51-54
textarea.addEventListener("paste", function () {
    // Defer until after paste content is applied
    setTimeout(updateSubmitState, 0);
});
```

Extend this to also call `showPasteFeedback(textarea.value.length)` inside the same `setTimeout` callback.

### Flask route: reads `request.form["mode"]`

```python
# app/routes.py — the route that processes the form POST
# mode = request.form.get("mode", "offline")
# This means the hidden input <input type="hidden" name="mode" value="offline">
# is the correct approach. The <select> was previously supplying this value.
```

Verify in `app/routes.py` that `mode` is read from `request.form`. The hidden input replacement must carry `name="mode"`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `<select>` for binary toggle | CSS toggle switch + hidden input | Phase 8 (this phase) | Better UX — affordance is immediately clear |
| Paste event ignored (no feedback) | Character count feedback | Phase 8 (this phase) | Analyst knows content was captured |
| Static "Extract IOCs" button | Dynamic label based on mode | Phase 8 (this phase) | Reduces submit anxiety — clear intent |

**Deprecated/outdated:**
- `<select id="mode-select">` and `.mode-select` CSS class: removed in this phase, replaced by toggle widget
- `IndexPage.mode_select` Playwright locator: must be replaced in `tests/e2e/pages/index_page.py`

---

## Open Questions

1. **Should paste feedback show "N characters pasted" or "N characters" (shorter)?**
   - What we know: Requirement says "N characters pasted"
   - What's unclear: Nothing — the wording is specified in INPUT-02
   - Recommendation: Use exact wording "N characters pasted"

2. **Should paste feedback persist if user types more after pasting?**
   - What we know: The `input` event fires on every keystroke
   - What's unclear: Whether to dismiss on next input or only via setTimeout
   - Recommendation: Dismiss only via 2s timeout (simpler, less distracting); `input` event does not reset the timer

3. **Does `app/routes.py` read `request.form.get("mode")` or does it have a default?**
   - What we know: The `<select>` previously submitted `name="mode"` with values `"offline"`/`"online"`
   - What's unclear: What happens if the field is missing (e.g., form submitted with JS disabled)
   - Recommendation: Verify in `app/routes.py` and ensure the hidden input always submits a value; the existing server behavior is unchanged by this phase

---

## Implementation Scope

All changes are confined to three files:

| File | Change Type | Size Estimate |
|------|-------------|---------------|
| `app/templates/index.html` | Replace `<select>` block with toggle widget HTML, add paste-feedback span | ~15 lines net change |
| `app/static/src/input.css` | Add toggle switch component styles, paste feedback style | ~50 lines new CSS |
| `app/static/main.js` | Add `initModeToggle()`, `updateSubmitLabel()`, extend paste handler | ~30 lines new JS |
| `app/static/dist/style.css` | Regenerated via `make css` | Generated — not hand-edited |
| `tests/e2e/pages/index_page.py` | Replace `mode_select` locator, add toggle locators | ~5 lines |
| `tests/e2e/test_ui_controls.py` | Update 4 mode-related tests to use toggle | ~20 lines |
| `tests/e2e/test_homepage.py` | Update `test_form_elements_present`, remove `test_mode_select_options`, `test_offline_mode_selected_by_default` | ~15 lines |

**Estimated plan count:** 1 plan (all requirements small enough to implement together).

---

## Sources

### Primary (HIGH confidence)
- Codebase direct read — `app/templates/index.html`, `app/static/main.js`, `app/static/src/input.css`, `app/__init__.py` (CSP header), `tailwind.config.js`
- `.planning/STATE.md` — Phase 7 decisions, CSP behaviour confirmed in project
- `tests/e2e/pages/index_page.py`, `tests/e2e/test_homepage.py`, `tests/e2e/test_ui_controls.py` — existing test coverage that must be maintained

### Secondary (MEDIUM confidence)
- MDN Web Docs patterns (training data, cross-referenced with codebase): `paste` event timing, `setTimeout` deference pattern, `aria-pressed` for toggle buttons

### Tertiary (LOW confidence)
- None — all findings are grounded in codebase inspection or well-established Web API behaviour

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — No new dependencies; existing stack verified by direct codebase read
- Architecture patterns: HIGH — All patterns extracted from existing working code
- Pitfalls: HIGH — Pitfalls identified from reading actual test files and CSP config; not hypothetical

**Research date:** 2026-02-25
**Valid until:** Stable (no external dependencies; only project-internal files)
