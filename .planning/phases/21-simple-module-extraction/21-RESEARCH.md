# Phase 21: Simple Module Extraction — Research

**Researched:** 2026-03-01
**Domain:** TypeScript DOM module authoring — extracting vanilla JS into typed ES modules
**Confidence:** HIGH

---

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MOD-02 | Form controls module (submit button, clear, auto-grow textarea, mode toggle, paste feedback) | Timer types, null guards, `attr` helper, textarea event patterns |
| MOD-03 | Clipboard module (copy IOC values, copy-with-enrichment, fallback copy) | `navigator.clipboard` typing, `HTMLElement` narrowing, fallback copy pattern |
| MOD-05 | Card management module (verdict updates, dashboard counts, severity sorting) | `CSS.escape()` typing in lib.dom.d.ts, debounce timer types, `querySelectorAll` iteration |
| MOD-06 | Filter bar module (verdict/type/search filtering, dashboard badge click) | Filter state object typing, `querySelectorAll` null checks, `addEventListener` with typed events |
| MOD-07 | Settings module (API key show/hide toggle) | `HTMLInputElement` type narrowing, input.type assignment |
| MOD-08 | UI utilities module (scroll-aware filter bar, card stagger animation) | `window.scrollY`, passive event listeners, CSS custom properties |

</phase_requirements>

---

## Summary

Phase 21 extracts six of the eight planned TypeScript modules from the existing `main.js` (856-line IIFE). The six modules in scope — `form.ts`, `clipboard.ts`, `cards.ts`, `filter.ts`, `settings.ts`, and `ui.ts` — cover all behavior except the enrichment polling loop (deferred to Phase 22). The source code to be extracted is well-understood: it lives in `app/static/main.js` and has already been analyzed to produce the Phase 20 type definitions.

The core challenge is not logic extraction but TypeScript discipline: every `getElementById` / `querySelector` call returns `Element | null` (or a more specific nullable type) and TypeScript's strict mode requires explicit null handling. The project has already decided on `if (!el) return` guard patterns (no non-null assertions), `ReturnType<typeof setTimeout>` for all timer variables, and an `attr(el, name, fallback?)` helper to neutralize `getAttribute`'s `string | null` return. These decisions are locked.

Each module exports a single `init` function and has no inter-module dependencies except imports from `app/static/src/ts/types/`. The modules do not call each other — the enrichment module (Phase 22) will be the only cross-module consumer of the `cards.ts` exports. This clean isolation means all six can be written independently in any order.

**Primary recommendation:** Write each module as a straight line-for-line port of the relevant section of `main.js`, apply null guards and type annotations, then run `make typecheck` to catch any remaining issues. Do not refactor logic during extraction — behavioral fidelity is the success criterion, not code elegance.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| TypeScript | 5.8.3 (already installed) | Type checking via `tsc --noEmit` | Already in place from Phase 20 |
| esbuild | 0.27.3 (already installed) | Bundling + transpilation | Already in place from Phase 19 |
| lib.dom.d.ts | Ships with TypeScript | All browser API types | Official TypeScript DOM typings |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lib.dom.iterable.d.ts | Ships with TypeScript | `NodeList.forEach`, array spread of `querySelectorAll` results | Already enabled via `"lib": ["es2022", "dom", "dom.iterable"]` in tsconfig.json |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ReturnType<typeof setTimeout>` | `number` | `number` is technically correct in browser environments, but project decision is `ReturnType<typeof setTimeout>` for clarity and to prevent `@types/node` conflicts if ever added |
| `if (!el) return` | `el!` (non-null assertion) | Non-null assertions are banned by project requirement (success criterion 2) |
| `attr()` helper | `el.getAttribute(name) ?? fallback` | Inline is verbose and repeated; the helper is required by success criterion 4 |

**Installation:** None needed — stack is fully installed.

---

## Architecture Patterns

### Recommended Module Structure

```
app/static/src/ts/
├── types/
│   ├── ioc.ts          # Phase 20 — VerdictKey, IocType, constants
│   └── api.ts          # Phase 20 — EnrichmentItem, EnrichmentStatus
└── modules/            # Phase 21 creates this directory + 6 files
    ├── form.ts         # MOD-02: submit, clear, auto-grow, mode toggle, paste feedback
    ├── clipboard.ts    # MOD-03: copy buttons, copy-with-enrichment, fallback
    ├── cards.ts        # MOD-05: verdict updates, dashboard counts, severity sorting
    ├── filter.ts       # MOD-06: verdict/type/search filtering, dashboard badge click
    ├── settings.ts     # MOD-07: API key show/hide toggle
    └── ui.ts           # MOD-08: scroll-aware filter bar, card stagger animation
```

Also creates one shared utility:

```
app/static/src/ts/
└── utils/
    └── dom.ts          # attr() helper + any other reusable DOM utilities
```

### Pattern 1: The `attr` helper

**What:** A typed wrapper around `getAttribute` that returns `string` instead of `string | null`. The optional `fallback` parameter defaults to `""` to avoid forcing callers to handle `undefined`.

**When to use:** Every `getAttribute` call in the codebase — required by success criterion 4.

```typescript
// app/static/src/ts/utils/dom.ts

/**
 * Typed getAttribute wrapper — returns string instead of string | null.
 * Callers pass a fallback (default: "") to avoid null propagation.
 * Attribute names are not narrowed to a union type intentionally —
 * the tradeoff is flexibility over compile-time attribute typo detection.
 */
export function attr(el: Element, name: string, fallback = ""): string {
  return el.getAttribute(name) ?? fallback;
}
```

**Key design note:** Success criterion 4 says "calling it with a misspelled attribute name still compiles (strings are not typed)" — this is intentional. Do NOT type `name` as a template literal union of valid attribute names. Keep it as `string`.

### Pattern 2: Module init function signature

**What:** Every module exports exactly one function named `init`. No arguments. Returns `void`. All DOM queries happen inside `init`.

**When to use:** All six modules in Phase 21.

```typescript
// Pattern for every module
export function init(): void {
  const el = document.getElementById("some-id");
  if (!el) return;   // null guard — TypeScript narrows el to HTMLElement
  // ... rest of logic
}
```

### Pattern 3: Typed DOM element queries

**What:** TypeScript's `getElementById` returns `HTMLElement | null`. For input elements, `querySelector` returns `Element | null`. Type-narrowing requires either a guard or a type assertion with a check.

```typescript
// getElementById — returns HTMLElement | null
const btn = document.getElementById("submit-btn");
if (!btn) return;
// btn is now HTMLElement — but not HTMLButtonElement
// For disabled property, cast after guard:
const submitBtn = document.getElementById("submit-btn") as HTMLButtonElement | null;
if (!submitBtn) return;
submitBtn.disabled = true; // OK

// querySelector with generic — returns typed element or null
const textarea = document.querySelector<HTMLTextAreaElement>("#ioc-text");
if (!textarea) return;
textarea.value; // OK — typed as HTMLTextAreaElement

// querySelectorAll — returns NodeListOf<T>, always non-null
const cards = document.querySelectorAll<HTMLElement>(".ioc-card");
cards.forEach(card => {
  const verdict = attr(card, "data-verdict");
});
```

**Confidence:** HIGH — verified against TypeScript lib.dom.d.ts signatures.

### Pattern 4: Timer types

**What:** `setTimeout` returns `ReturnType<typeof setTimeout>` (which resolves to `number` in browsers, but is written in full for portability). All timer variables must be declared with this type.

**When to use:** Anywhere a timer handle is stored for later `clearTimeout`.

```typescript
// In form.ts — paste feedback timer
// The existing main.js stores _timer on a DOM element — in TypeScript
// we store it as a module-level variable instead (no property on HTMLElement)
let pasteTimer: ReturnType<typeof setTimeout> | null = null;

function showPasteFeedback(charCount: number): void {
  const feedback = document.getElementById("paste-feedback");
  if (!feedback) return;
  feedback.textContent = `${charCount} characters pasted`;
  feedback.style.display = "";
  feedback.classList.remove("is-hiding");
  feedback.classList.add("is-visible");
  if (pasteTimer !== null) clearTimeout(pasteTimer);
  pasteTimer = setTimeout(() => {
    feedback.classList.remove("is-visible");
    feedback.classList.add("is-hiding");
    setTimeout(() => {
      feedback.style.display = "none";
      feedback.classList.remove("is-hiding");
    }, 250);
  }, 2000);
}
```

**Important:** `main.js` stores `_timer` directly on a DOM element (`feedback._timer`). TypeScript will reject this because `HTMLElement` has no `_timer` property. The fix is to hoist the timer to a module-level variable — this is the correct TypeScript pattern and does not change behavior.

### Pattern 5: `HTMLInputElement` type narrowing (settings.ts)

**What:** `getElementById` returns `HTMLElement | null`. To read/write `.type` (only on `HTMLInputElement`), you must use a generic query or a type assertion after a null guard.

```typescript
// settings.ts
export function init(): void {
  const btn = document.getElementById("toggle-key-btn");
  const input = document.getElementById("api-key") as HTMLInputElement | null;
  if (!btn || !input) return;

  btn.addEventListener("click", () => {
    if (input.type === "password") {
      input.type = "text";
      btn.textContent = "Hide";
    } else {
      input.type = "password";
      btn.textContent = "Show";
    }
  });
}
```

### Pattern 6: `CSS.escape()` in TypeScript

**What:** `CSS.escape()` is present in `lib.dom.d.ts` and works without any import. The existing `main.js` uses it in `findCardForIoc`.

```typescript
// cards.ts
function findCardForIoc(iocValue: string): HTMLElement | null {
  return document.querySelector<HTMLElement>(
    `.ioc-card[data-ioc-value="${CSS.escape(iocValue)}"]`
  );
}
```

**Confidence:** HIGH — `CSS.escape` is in the DOM standard and TypeScript's lib.dom.d.ts.

### Pattern 7: Passive scroll listener (ui.ts)

**What:** The `addEventListener` overload that accepts an `AddEventListenerOptions` object is fully typed in lib.dom.d.ts.

```typescript
// ui.ts
export function init(): void {
  const filterBar = document.querySelector<HTMLElement>(".filter-bar-wrapper");
  if (!filterBar) return;

  let scrolled = false;
  window.addEventListener("scroll", () => {
    const isScrolled = window.scrollY > 40;
    if (isScrolled !== scrolled) {
      scrolled = isScrolled;
      filterBar.classList.toggle("is-scrolled", scrolled);
    }
  }, { passive: true });
}
```

### Pattern 8: `NodeList` iteration under `noUncheckedIndexedAccess`

**What:** With `noUncheckedIndexedAccess: true` in tsconfig, indexed access like `cards[i]` returns `HTMLElement | undefined`. Use `forEach` or `for...of` instead of indexed loops to avoid this.

```typescript
// WRONG with noUncheckedIndexedAccess
const cards = document.querySelectorAll<HTMLElement>(".ioc-card");
for (let i = 0; i < cards.length; i++) {
  const v = cards[i].getAttribute("data-verdict"); // ERROR: cards[i] is HTMLElement | undefined
}

// CORRECT — forEach or for...of avoids the undefined
cards.forEach(card => {
  const v = attr(card, "data-verdict");
});

// Also correct — Array.from then iterate
Array.from(cards).forEach(card => { ... });
```

**Confidence:** HIGH — this is a known `noUncheckedIndexedAccess` interaction with NodeList.

### Anti-Patterns to Avoid

- **Non-null assertions (`!`):** Banned by success criterion 2. Use `if (!el) return` instead.
- **`NodeJS.Timeout`:** Banned by success criterion 3. Use `ReturnType<typeof setTimeout>`.
- **`as any`:** Avoid entirely. If a type is genuinely unknown, use `unknown` and narrow.
- **Storing timers on DOM elements (`el._timer`):** TypeScript rejects arbitrary properties on `HTMLElement`. Use module-level variables.
- **`innerHTML` for user data:** Already avoided in main.js — keep it that way (XSS, SEC-08).
- **Indexed NodeList access with `noUncheckedIndexedAccess`:** Use `forEach` / `for...of` instead of `array[i]`.
- **Importing types with `import` (not `import type`):** For type-only imports from `./types/ioc`, use `import type { VerdictKey } from "../types/ioc"` to satisfy `isolatedModules`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Timer type annotation | Custom type alias | `ReturnType<typeof setTimeout>` | Project decision; standard TypeScript pattern |
| Null-safe attribute access | Custom `getAttr` variant | The `attr()` helper as specified | Already decided; keeps return type `string` |
| DOM type narrowing | Type cast utilities | TypeScript generics on `querySelector<T>` | Built into lib.dom.d.ts |
| `NodeList` to array conversion | Manual loops | `Array.from()` or `.forEach()` | Standard; avoids `noUncheckedIndexedAccess` pitfalls |

**Key insight:** All the "library" work is already in TypeScript's own DOM typings. No third-party packages needed.

---

## Common Pitfalls

### Pitfall 1: `_timer` Property on `HTMLElement`

**What goes wrong:** `main.js` sets `feedback._timer = setTimeout(...)` directly on a DOM element. TypeScript rejects `HTMLElement._timer` because it's not a declared property.

**Why it happens:** JavaScript allows arbitrary property assignment on objects; TypeScript requires declared properties on typed objects.

**How to avoid:** Declare timer variables at the module level (`let pasteTimer: ReturnType<typeof setTimeout> | null = null;`) rather than as DOM element properties.

**Warning signs:** TypeScript error `Property '_timer' does not exist on type 'HTMLElement'`.

### Pitfall 2: `querySelectorAll` Returns `NodeListOf<T>`, Not an Array

**What goes wrong:** `Array.prototype.slice.call(grid.querySelectorAll(...))` is used in main.js to convert NodeList to an array for `.sort()`. TypeScript handles this differently — `Array.from()` is cleaner and fully typed.

**Why it happens:** NodeList doesn't have `.sort()` — you need a real array. The IIFE used `Array.prototype.slice.call()` as an ES5-compatible conversion.

**How to avoid:** Use `Array.from(grid.querySelectorAll<HTMLElement>(".ioc-card"))` then `.sort()`.

**Warning signs:** TypeScript error `Property 'sort' does not exist on type 'NodeListOf<HTMLElement>'`.

### Pitfall 3: `noUncheckedIndexedAccess` with Array Access

**What goes wrong:** `verdicts[0]` in `computeWorstVerdict` returns `VerdictEntry | undefined` under `noUncheckedIndexedAccess`, not `VerdictEntry`. Assigning it to a `VerdictEntry` variable causes a type error.

**Why it happens:** `noUncheckedIndexedAccess` adds `| undefined` to all indexed access returns for safety.

**How to avoid:** Check existence before use: `if (verdicts.length === 0) return "no_data"; const first = verdicts[0]; if (!first) return "no_data";` — or use `.at(0)` with a nullish check.

**Warning signs:** TypeScript error `Type 'VerdictEntry | undefined' is not assignable to type 'VerdictEntry'`.

### Pitfall 4: `getAttribute` on Specific Subtypes

**What goes wrong:** `getAttribute` is defined on `Element`, not just `HTMLElement`. If you query for a generic `Element` (without the generic parameter on `querySelector`), TypeScript may infer `Element | null` — which is fine. But if you then try to access `.style` (an `HTMLElement`-only property), you get an error.

**Why it happens:** `Element` is the base interface; `.style`, `.disabled`, `.value` etc. are on subtypes like `HTMLElement`, `HTMLInputElement`, `HTMLButtonElement`.

**How to avoid:** Always use the generic form: `querySelector<HTMLButtonElement>(...)` or cast after null check: `const btn = el as HTMLButtonElement`.

**Warning signs:** TypeScript error `Property 'style' does not exist on type 'Element'`.

### Pitfall 5: `import type` vs `import` for Isolated Modules

**What goes wrong:** `tsconfig.json` has `isolatedModules: true`. Importing a type with a regular `import` statement (not `import type`) can cause errors in some edge cases when the import is only used as a type.

**Why it happens:** `isolatedModules` requires that type-only imports are erased at compile time without needing type information. Regular imports that resolve to types may trigger warnings.

**How to avoid:** Use `import type { VerdictKey } from "../types/ioc"` for type-only imports. Use `import { attr } from "../utils/dom"` for value imports.

**Warning signs:** TypeScript warning/error about `isolatedModules` and type re-exports.

### Pitfall 6: `HTMLElement.textContent` is `string | null`

**What goes wrong:** `btn.textContent = "Copied!"` works, but reading `btn.textContent` to save `original` returns `string | null`. Assigning it back after the timeout causes a type mismatch if TypeScript expects `string`.

**Why it happens:** `textContent` getter returns `string | null` per the DOM spec (elements can technically have null textContent).

**How to avoid:** Use nullish coalescing: `const original = btn.textContent ?? "Copy"` — fallback to a known default so the variable is typed as `string`.

**Warning signs:** TypeScript error `Type 'string | null' is not assignable to type 'string'`.

---

## Code Examples

Verified patterns from lib.dom.d.ts and TypeScript documentation:

### Module skeleton (every module follows this pattern)

```typescript
// app/static/src/ts/modules/form.ts
import type { } from "../types/ioc"; // only if types are needed
import { attr } from "../utils/dom";

export function init(): void {
  const form = document.getElementById("analyze-form");
  if (!form) return;

  const textarea = document.querySelector<HTMLTextAreaElement>("#ioc-text");
  const submitBtn = document.querySelector<HTMLButtonElement>("#submit-btn");
  if (!textarea || !submitBtn) return;

  // ... rest of init
}
```

### attr helper — complete implementation

```typescript
// app/static/src/ts/utils/dom.ts
export function attr(el: Element, name: string, fallback = ""): string {
  return el.getAttribute(name) ?? fallback;
}
```

### Timer module-level variable pattern

```typescript
// Module-level timer — not on DOM element
let pasteTimer: ReturnType<typeof setTimeout> | null = null;

// Usage:
if (pasteTimer !== null) clearTimeout(pasteTimer);
pasteTimer = setTimeout(() => { /* ... */ }, 2000);
```

### Sort cards by severity — typed version

```typescript
// cards.ts — typed conversion from NodeList to sortable array
function doSortCards(): void {
  const grid = document.getElementById("ioc-cards-grid");
  if (!grid) return;

  const cards = Array.from(grid.querySelectorAll<HTMLElement>(".ioc-card"));
  if (cards.length === 0) return;

  cards.sort((a, b) => {
    const va = verdictSeverityIndex(attr(a, "data-verdict", "no_data") as VerdictKey);
    const vb = verdictSeverityIndex(attr(b, "data-verdict", "no_data") as VerdictKey);
    return vb - va; // descending
  });

  cards.forEach(card => grid.appendChild(card));
}
```

### Verdict dashboard count update — typed

```typescript
// cards.ts
function updateDashboardCounts(): void {
  const dashboard = document.getElementById("verdict-dashboard");
  if (!dashboard) return;

  const counts: Record<string, number> = {
    malicious: 0, suspicious: 0, clean: 0, no_data: 0
  };

  document.querySelectorAll<HTMLElement>(".ioc-card").forEach(card => {
    const v = attr(card, "data-verdict");
    if (Object.prototype.hasOwnProperty.call(counts, v)) {
      counts[v] = (counts[v] ?? 0) + 1;
    }
  });

  (["malicious", "suspicious", "clean", "no_data"] as const).forEach(verdict => {
    const countEl = dashboard.querySelector<HTMLElement>(`[data-verdict-count="${verdict}"]`);
    if (countEl) countEl.textContent = String(counts[verdict] ?? 0);
  });
}
```

### Clipboard fallback copy — typed

```typescript
// clipboard.ts
function fallbackCopy(text: string, btn: HTMLElement): void {
  const tmp = document.createElement("textarea");
  tmp.value = text;
  tmp.style.position = "fixed";
  tmp.style.top = "-9999px";
  tmp.style.left = "-9999px";
  document.body.appendChild(tmp);
  tmp.focus();
  tmp.select();
  try {
    document.execCommand("copy");
    showCopiedFeedback(btn);
  } catch {
    // Copy failed — user can still manually select the value
  } finally {
    document.body.removeChild(tmp);
  }
}
```

### navigator.clipboard — typed

```typescript
// clipboard.ts
function writeToClipboard(text: string, btn: HTMLElement): void {
  if (!navigator.clipboard) {
    fallbackCopy(text, btn);
    return;
  }
  navigator.clipboard.writeText(text).then(() => {
    showCopiedFeedback(btn);
  }).catch(() => {
    fallbackCopy(text, btn);
  });
}
```

---

## Module Breakdown: What Goes Where

This section maps `main.js` functions to Phase 21 modules to guide planning.

### `form.ts` (MOD-02)

Extracts from main.js lines 34–162:

| Function | Source Lines | Notes |
|----------|-------------|-------|
| `initSubmitButton()` | 34–70 | Includes `updateSubmitState`, paste event, clear button setup |
| `initAutoGrow()` | 74–112 | textarea grow + cursor state |
| `initModeToggle()` | 116–133 | Reads mode widget, sets aria-pressed |
| `updateSubmitLabel(mode)` | 135–142 | Updates button text + CSS class |
| `showPasteFeedback(charCount)` | 146–162 | Paste counter with animation — timer must be module-level |

**Key issues:** `feedback._timer` in main.js must become a module-level variable. `updateSubmitLabel` is called by `initModeToggle` — both must be in the same module or `updateSubmitLabel` exported.

### `clipboard.ts` (MOD-03)

Extracts from main.js lines 166–223:

| Function | Source Lines | Notes |
|----------|-------------|-------|
| `initCopyButtons()` | 166–181 | Queries `.copy-btn`, attaches click listeners |
| `showCopiedFeedback(btn)` | 183–191 | `btn.textContent` is `string | null` — use fallback |
| `fallbackCopy(text, btn)` | 193–211 | `execCommand` deprecated but still works in all browsers |
| `writeToClipboard(text, btn)` | 213–223 | `navigator.clipboard` may be undefined |

**Key issues:** `showCopiedFeedback` saves `btn.textContent` — use `btn.textContent ?? "Copy"` for the type.

Also exports `writeToClipboard` — needed by the export button in `initExportButton()` which is in Phase 22's enrichment module. **Plan accordingly:** either export `writeToClipboard` from `clipboard.ts` for use by Phase 22, or duplicate it. Export is cleaner.

### `cards.ts` (MOD-05)

Extracts from main.js lines 258–336:

| Function | Source Lines | Notes |
|----------|-------------|-------|
| `findCardForIoc(iocValue)` | 259–262 | Uses `CSS.escape()` — in lib.dom.d.ts |
| `updateCardVerdict(iocValue, verdict)` | 263–285 | Modifies DOM classes; verdict label update |
| `updateDashboardCounts()` | 287–308 | Counts cards by verdict attribute |
| `sortCardsBySeverity()` (debounced) | 310–336 | Module-level `sortTimer` variable |
| `doSortCards()` | 318–336 | Converts NodeList to array, sorts in-place |

**Key issues:**
- `sortTimer` must be a module-level `ReturnType<typeof setTimeout> | null` variable.
- `cards[i]` indexed access in original will need `forEach` or null-checked access.
- `VERDICT_LABELS` and `VERDICT_SEVERITY` are imported from `../types/ioc`.
- `findCardForIoc` and `updateCardVerdict` will need to be exported — they are called by the enrichment module (Phase 22).
- `updateDashboardCounts` and `sortCardsBySeverity` also called by enrichment — export these too.

**Design decision for planner:** `cards.ts` exports its `init` function AND also exports `findCardForIoc`, `updateCardVerdict`, `updateDashboardCounts`, `sortCardsBySeverity`. The Phase 22 enrichment module imports and calls these directly.

### `filter.ts` (MOD-06)

Extracts from main.js lines 677–788:

| Function/Block | Source Lines | Notes |
|---------------|-------------|-------|
| `initFilterBar()` | 677–788 | Self-contained; all state in local `filterState` object |
| `applyFilter()` | (nested) 688–730 | Applies filter state to cards |
| Verdict button handlers | 733–747 | Click event setup |
| Type pill handlers | 750–763 | Click event setup |
| Search input handler | 766–772 | `input` event |
| Dashboard badge handler | 775–787 | Syncs dashboard → filter |

**Key issues:**
- `filterState` is a plain object — type it as `interface FilterState { verdict: string; type: string; search: string; }`.
- The `for (var i = ...)` loops with IIFE closures (`(function(btn) { ... })(verdictBtns[i])`) — in TypeScript/ES2022, replace with simple `forEach` (no closure needed since `const` has block scope).
- All `querySelectorAll` calls return typed `NodeListOf<T>` — use `forEach`.
- `filterState.verdict === verdict` compares `string` with `string | null` (from getAttribute) — use `attr()` helper.

### `settings.ts` (MOD-07)

Extracts from main.js lines 792–805:

| Function | Source Lines | Notes |
|----------|-------------|-------|
| `initSettingsPage()` | 792–805 | Simple toggle; 2 elements |

**Key issues:**
- `input.type` requires casting to `HTMLInputElement | null` (cannot read `.type` on `HTMLElement`).
- Simplest module — good candidate for first implementation.

### `ui.ts` (MOD-08)

Extracts from main.js lines 811–835:

| Function | Source Lines | Notes |
|----------|-------------|-------|
| `initScrollAwareFilterBar()` | 811–826 | Module-level `scrolled` boolean state |
| `initCardStagger()` | 830–835 | Sets CSS custom property `--card-index` |

**Key issues:**
- `init()` should call both `initScrollAwareFilterBar()` and `initCardStagger()` — keep as private helpers, expose only `init`.
- `cards[i].style.setProperty(...)` — use `forEach` with `(card, i)` index for cleanliness.

---

## Cross-Module Dependencies

```
utils/dom.ts          ← attr() helper; imported by all modules
types/ioc.ts          ← VerdictKey, VERDICT_LABELS, VERDICT_SEVERITY, IOC_PROVIDER_COUNTS
                        ← imported by cards.ts (and eventually enrichment.ts)
types/api.ts          ← EnrichmentItem types; NOT needed by Phase 21 modules

cards.ts exports:
  init()              ← called by main.ts (Phase 22)
  findCardForIoc()    ← called by enrichment.ts (Phase 22)
  updateCardVerdict() ← called by enrichment.ts (Phase 22)
  updateDashboardCounts() ← called by enrichment.ts (Phase 22)
  sortCardsBySeverity()   ← called by enrichment.ts (Phase 22)

clipboard.ts exports:
  init()              ← called by main.ts (Phase 22)
  writeToClipboard()  ← called by enrichment.ts (Phase 22) for export button
```

All other Phase 21 modules export ONLY `init()`.

---

## State of the Art

| Old Approach (main.js) | TypeScript Approach | Impact |
|------------------------|--------------------|----|
| `var` declarations | `const`/`let` | Block scoping; no hoisting surprises |
| IIFE closures for loop variables | `forEach` callbacks | Closure no longer needed; cleaner |
| `Array.prototype.slice.call(nodeList)` | `Array.from(nodeList)` | Native, typed |
| `feedback._timer` on DOM element | Module-level timer variable | TypeScript-compatible |
| Inline object property hasOwnProperty | Same pattern works in TS | No change |
| `for (var i = 0; i < btns.length; i++)` | `btns.forEach(btn => ...)` | Avoids noUncheckedIndexedAccess |

**Deprecated/outdated:**
- `document.execCommand("copy")` — deprecated in Web standards but still widely supported. Kept as fallback since `navigator.clipboard` requires HTTPS/secure context. The main.js already handles this correctly.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.x + Playwright (sync API) |
| Config file | `pytest.ini` or pyproject.toml (standard pytest discovery) |
| Quick run command | `pytest tests/e2e/ -x -m e2e` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MOD-02 | Submit button enable/disable, clear, mode toggle, paste feedback | E2E | `pytest tests/e2e/test_ui_controls.py -x` | Yes |
| MOD-03 | Copy buttons present, data-value attribute, Copied! feedback | E2E | `pytest tests/e2e/test_copy_buttons.py -x` | Yes |
| MOD-05 | Card verdict updates, dashboard counts, severity sorting | E2E (online mode, needs VT key) | `pytest tests/e2e/test_results_page.py -x` | Yes (partial — online tests skip without key) |
| MOD-06 | Verdict/type/search filtering, dashboard badge click | E2E | `pytest tests/e2e/test_results_page.py -x` | Yes |
| MOD-07 | API key show/hide toggle | E2E (manual verification) | No dedicated test | No — manual only |
| MOD-08 | Scroll-aware filter bar, card stagger animation | E2E (visual) | `pytest tests/e2e/ -k "sticky" -x` | Partial — sticky position tested |

**MOD-05 note:** Card verdict updates require online mode enrichment — tests for this behavior exist in `test_results_page.py` but are gated by VT API key. Severity sorting is behavioral — verifiable by checking card order in DOM after enrichment, but no dedicated test exists. For Phase 21, behavioral fidelity is verified by E2E suite green (non-VT-gated tests).

**MOD-07 note:** No E2E test exists for the settings show/hide toggle specifically. Manual verification: navigate to `/settings`, check toggle works. This is acceptable since the implementation is 10 lines.

**MOD-08 note:** Card stagger animation sets CSS custom property `--card-index` — verifiable via JS evaluate in Playwright. Scroll-aware filter bar is tested via `test_filter_bar_has_sticky_position`. No dedicated scroll-scroll-threshold test exists.

### Sampling Rate

- **Per task commit:** `make typecheck && pytest tests/e2e/test_ui_controls.py tests/e2e/test_copy_buttons.py tests/e2e/test_results_page.py -x -m e2e`
- **Per wave merge:** `pytest tests/ -x` (full suite)
- **Phase gate:** Full suite green + `make typecheck` zero errors before Phase 22

### Wave 0 Gaps

- No new test files needed — existing E2E tests cover all verifiable behaviors.
- No test framework installation needed — pytest + Playwright already installed.
- One gap: no dedicated E2E test for settings show/hide toggle (MOD-07). This is low-risk (10-line function) and can be verified manually.

---

## Open Questions

1. **Should `updateSubmitLabel` in `form.ts` be exported?**
   - What we know: It is called by `initModeToggle` and both functions live in `form.ts`.
   - What's unclear: Does Phase 22's enrichment module need to call it? Review of main.js says no — `updateSubmitLabel` is internal to the form flow.
   - Recommendation: Keep `updateSubmitLabel` private (not exported) — call it from within `form.ts` only.

2. **Export scope for `cards.ts`**
   - What we know: `findCardForIoc`, `updateCardVerdict`, `updateDashboardCounts`, `sortCardsBySeverity` are called by `renderEnrichmentResult` in the enrichment module.
   - What's unclear: Should these be part of the `cards.ts` public API, or should `enrichment.ts` duplicate the logic?
   - Recommendation: Export all four from `cards.ts`. This is cleaner than duplication and aligns with the planned module architecture.

3. **Export scope for `clipboard.ts` — `writeToClipboard`**
   - What we know: `initExportButton()` in main.js calls `writeToClipboard(exportText, exportBtn)`.
   - What's unclear: `initExportButton()` is part of the enrichment module (Phase 22) — it belongs in `enrichment.ts` because it reads `iocVerdicts` data set by the polling loop.
   - Recommendation: Export `writeToClipboard` from `clipboard.ts` so `enrichment.ts` can import it without duplicating clipboard logic.

---

## Sources

### Primary (HIGH confidence)

- TypeScript lib.dom.d.ts — verified `getElementById` returns `HTMLElement | null`, `querySelector<T>` returns `T | null`, `querySelectorAll<T>` returns `NodeListOf<T>`, `CSS.escape` exists, `navigator.clipboard` exists, `AddEventListenerOptions` interface exists.
- `app/static/main.js` (project source) — ground truth for all behavior being extracted.
- `app/static/src/ts/types/ioc.ts` and `api.ts` — Phase 20 types available for import.
- `tsconfig.json` — strict, isolatedModules, noUncheckedIndexedAccess confirmed.
- Phase 20 STATE.md decisions — `ReturnType<typeof setTimeout>`, `attr()` helper, no non-null assertions.

### Secondary (MEDIUM confidence)

- TypeScript Handbook — `noUncheckedIndexedAccess` behavior with array/NodeList indexing.
- TypeScript `isolatedModules` documentation — `import type` requirement for type-only imports.

### Tertiary (LOW confidence)

- `document.execCommand("copy")` deprecation status — confirmed deprecated in spec but widely supported in browsers as of 2026. Keeping fallback is correct.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — fully installed from Phases 19-20, no new dependencies
- Architecture: HIGH — module split directly derived from main.js function boundaries
- Pitfalls: HIGH — derived from direct analysis of main.js + tsconfig settings
- Test coverage: HIGH — existing E2E suite verified to cover all six module behaviors

**Research date:** 2026-03-01
**Valid until:** 2026-04-01 (TypeScript 5.8 stable; esbuild 0.27.3 pinned; no external dependencies)
