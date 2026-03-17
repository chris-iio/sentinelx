---
estimated_steps: 6
estimated_files: 5
---

# T01: Add inline context line to IOC card header for IP and domain IOCs

**Slice:** S05 — Context And Staleness
**Milestone:** M001

## Description

Deliver CTX-01: key context fields visible in the IOC card header without expanding the enrichment details. For IP IOCs, this means showing the GeoIP location string (country, city, ASN) from the "IP Context" provider. For domain IOCs, show resolved A record IPs from the "DNS Records" provider. Hash, URL, and CVE IOC types have no context providers, so their context line stays empty and hides via CSS `:empty`.

This task adds a template placeholder, a new `updateContextLine()` function in `row-factory.ts`, wires it into the context provider branch of `enrichment.ts`, and adds CSS styling.

**Relevant skill:** `frontend-design` (CSS styling)

## Steps

1. **Template placeholder** — In `app/templates/partials/_ioc_card.html`, add an empty `<div class="ioc-context-line"></div>` after the `{% endif %}` that closes the `.ioc-original` conditional block and before the `{% if mode == "online" and job_id %}` enrichment slot include. The exact insertion point is between line `{% endif %}` (for `ioc.raw_match != ioc.value`) and `{% if mode == "online" and job_id %}`.

2. **Create `updateContextLine()` in `row-factory.ts`** — Add a new exported function `updateContextLine(card: HTMLElement, result: EnrichmentResultItem): void` that:
   - Finds `.ioc-context-line` inside `card`
   - Based on `result.provider`:
     - `"IP Context"` → Extract `result.raw_stats.geo` (a pre-formatted string like "US · San Francisco · AS24940 (Hetzner Online GmbH)"). Create a `<span>` with class `context-field` and `data-context-provider="IP Context"`, set its `textContent` to the geo string. **Before appending, check if a span with `data-context-provider="IP Context"` already exists — if so, replace its textContent.** Append to `.ioc-context-line`.
     - `"ASN Intel"` → **Only if no child span with `data-context-provider="IP Context"` exists yet** (IP Context is more comprehensive). Extract `result.raw_stats.asn` and `result.raw_stats.prefix`. Create a span with `data-context-provider="ASN Intel"` and textContent like "AS24940 · 5.9.0.0/16". Append to `.ioc-context-line`.
     - `"DNS Records"` → Extract `result.raw_stats.a` (an array of IP strings). If the array is non-empty, take the first 3 entries, join with ", ", and create a span with `data-context-provider="DNS Records"` and textContent like "A: 93.184.216.34, 93.184.216.35". Append to `.ioc-context-line`.
     - All other providers → do nothing (return early).
   - If the extracted value is falsy/empty, return without appending anything (keeps the container `:empty`).
   - All DOM construction uses `createElement` + `textContent` (SEC-08). No `innerHTML`.

3. **Import and use the `EnrichmentResultItem` type** — The function parameter type `EnrichmentResultItem` is from `../types/api.ts`. Ensure it's imported in `row-factory.ts` (check if it's already imported; if not, add the import).

4. **Wire `updateContextLine` call into `enrichment.ts`** — In the context provider branch (around line 215-235, inside the `if (CONTEXT_PROVIDERS.has(result.provider))` block), after the context row is appended to the context section and before the `return` statement, add:
   ```typescript
   // Populate inline context line in card header (CTX-01)
   updateContextLine(card, result);
   ```
   The `card` variable is already available (line ~207: `const card = findCardForIoc(result.ioc_value)`). Import `updateContextLine` from `./row-factory` in the existing import statement at the top of `enrichment.ts` (line ~24).

5. **CSS styling** — Add to `app/static/src/input.css` in the `@layer components` section (near the other `.ioc-*` rules):
   ```css
   .ioc-context-line:empty {
       display: none;
   }
   .ioc-context-line {
       font-size: 0.75rem;
       color: var(--text-muted, #6b7280);
       padding: 0.125rem 1rem 0.25rem;
       line-height: 1.4;
   }
   .ioc-context-line .context-field {
       margin-right: 0.75rem;
   }
   ```
   Place the `:empty` rule before the main rule so it takes precedence when the element has no children.

6. **Build and verify** — Run `make typecheck`, `make js-dev`, `make css`. All must pass with zero errors.

## Must-Haves

- [ ] `.ioc-context-line` div exists in `_ioc_card.html` between card header/original and enrichment slot
- [ ] `.ioc-context-line:empty { display: none }` CSS rule present
- [ ] `updateContextLine()` exported from `row-factory.ts` with provider-specific extraction logic
- [ ] IP Context provider populates context line with `raw_stats.geo`
- [ ] ASN Intel skips if IP Context already populated (dedup via `data-context-provider` attribute check)
- [ ] DNS Records populates context line with first 3 A record IPs
- [ ] `updateContextLine` called in enrichment.ts context provider branch
- [ ] All DOM construction uses `createElement + textContent` only (SEC-08)
- [ ] `make typecheck` passes with zero errors
- [ ] `make js-dev` bundle compiles
- [ ] `make css` rebuilds successfully

## Verification

- `make typecheck` — zero errors
- `make js-dev` — bundle compiles successfully
- `make css` — Tailwind rebuild succeeds
- `grep -n "ioc-context-line" app/templates/partials/_ioc_card.html` — shows the placeholder div
- `grep -n "updateContextLine" app/static/src/ts/modules/enrichment.ts` — shows the call in context branch
- `grep -n "updateContextLine" app/static/src/ts/modules/row-factory.ts` — shows the function definition and export
- `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` — only comment in graph.ts (SEC-08 compliance)

## Inputs

- `app/templates/partials/_ioc_card.html` — Current template with `.ioc-card-header`, optional `.ioc-original`, and `_enrichment_slot.html` include
- `app/static/src/ts/modules/enrichment.ts` — Context provider branch at line ~215 routes results to `.enrichment-section--context`. `card` variable available. Already imports from `./row-factory`.
- `app/static/src/ts/modules/row-factory.ts` — Contains `createContextRow`, `updateSummaryRow`, `formatRelativeTime`. Import `EnrichmentResultItem` type if not already present.
- `app/static/src/input.css` — Component layer with `.ioc-card`, `.ioc-card-header`, `.ioc-original` rules

## Expected Output

- `app/templates/partials/_ioc_card.html` — Has `.ioc-context-line` div positioned between header/original and enrichment slot
- `app/static/src/ts/modules/row-factory.ts` — New exported `updateContextLine(card, result)` function with IP Context / ASN Intel / DNS Records logic
- `app/static/src/ts/modules/enrichment.ts` — `updateContextLine(card, result)` called in context provider branch; `updateContextLine` added to import
- `app/static/src/input.css` — `.ioc-context-line` and `.context-field` CSS rules
- `app/static/dist/main.js` — Rebuilt JS bundle
- `app/static/dist/style.css` — Rebuilt CSS

## Observability Impact

- **New DOM surface:** `.ioc-context-line` div present on every `.ioc-card`. When empty (no context providers for IOC type), `:empty` CSS rule hides it. When populated, child `<span>` elements carry `data-context-provider` attributes identifying which provider sourced the data.
- **Inspection commands:**
  - `document.querySelectorAll('.ioc-context-line:not(:empty)').length` — count of IOCs with inline context rendered
  - `document.querySelectorAll('.ioc-context-line').length` — should equal `.ioc-card` count (placeholder always present)
  - `document.querySelector('.ioc-context-line span')?.getAttribute('data-context-provider')` — identifies which provider populated a context line
- **Failure signal:** If an IP IOC's `.ioc-context-line` stays empty while `.enrichment-section--context .provider-detail-row` has children, then `updateContextLine()` was not called or `raw_stats.geo` was absent.
- **No backend changes.** All data already flows from Flask to browser via the enrichment status endpoint.
