---
estimated_steps: 7
estimated_files: 5
---

# T02: Add staleness badge to summary row and run full E2E verification

**Slice:** S05 — Context And Staleness
**Milestone:** M001

## Description

Deliver CTX-02: cached results show a staleness indicator ("cached 4h ago") in the summary row. When any verdict result for an IOC was served from cache, the `cached_at` timestamp is propagated through `VerdictEntry` and rendered as a `.staleness-badge` in the summary row next to the micro-bar. This uses the existing `formatRelativeTime()` function already in `row-factory.ts`.

After implementing CTX-02, this task also performs the final full E2E verification for the entire S05 slice (both CTX-01 and CTX-02).

## Steps

1. **Extend `VerdictEntry` interface** — In `app/static/src/ts/modules/verdict-compute.ts`, add an optional field to the `VerdictEntry` interface:
   ```typescript
   cachedAt?: string;  // ISO timestamp from result.cached_at when served from cache
   ```
   Add it after the existing fields (after `statText`). This is the only change to this file.

2. **Populate `cachedAt` in enrichment.ts** — In `app/static/src/ts/modules/enrichment.ts`, find where `VerdictEntry` objects are constructed (in the verdict/non-context branch, after line ~235). When building the entry object, add:
   ```typescript
   cachedAt: result.cached_at ?? undefined,
   ```
   The `result.cached_at` field is already typed as `cached_at?: string` on `EnrichmentResultItem` in `api.ts`. This propagates the cache timestamp from the API response into the verdict tracking system.

3. **Render staleness badge in `updateSummaryRow()`** — In `app/static/src/ts/modules/row-factory.ts`, modify the `updateSummaryRow()` function. After the micro-bar is appended to `summaryRow` (around line 305, after `summaryRow.appendChild(microBar)`), add:

   ```typescript
   // d. Staleness badge — show oldest cached_at if any entries were cached (CTX-02)
   const cachedEntries = entries.filter(e => e.cachedAt);
   if (cachedEntries.length > 0) {
     // Find the oldest (minimum) cached_at timestamp
     const oldestCachedAt = cachedEntries
       .map(e => e.cachedAt!)
       .sort()[0];
     const staleBadge = document.createElement("span");
     staleBadge.className = "staleness-badge";
     staleBadge.textContent = "cached " + formatRelativeTime(oldestCachedAt);
     summaryRow.appendChild(staleBadge);
   }
   ```

   The `formatRelativeTime()` function already exists in this file (defined around line 56) and converts ISO strings to relative time like "4h ago".

4. **CSS for staleness badge** — Add to `app/static/src/input.css` in the `@layer components` section, near the existing `.ioc-summary-row` or `.cache-badge` rules:
   ```css
   .staleness-badge {
       font-size: 0.675rem;
       color: var(--text-muted, #6b7280);
       margin-left: auto;
       white-space: nowrap;
   }
   ```
   The `margin-left: auto` pushes the badge to the right end of the summary row (which is a flex container). This matches the visual pattern of the per-row `.cache-badge`.

5. **Rebuild bundles** — Run `make typecheck`, `make js-dev`, `make css`. All must pass.

6. **Full E2E test suite** — Run `pytest tests/ -m e2e --tb=short -q`. Expected: 89 passed, 2 failed (pre-existing title-case failures in `test_page_title` and `test_settings_page_title_tag`). Any additional failures indicate a regression from S05 changes.

7. **SEC-08 compliance check** — Run `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/`. Only a comment in `graph.ts` should match. No functional innerHTML usage anywhere.

## Must-Haves

- [ ] `VerdictEntry` interface in `verdict-compute.ts` has `cachedAt?: string` field
- [ ] `enrichment.ts` populates `cachedAt` from `result.cached_at` when constructing VerdictEntry objects
- [ ] `updateSummaryRow()` renders `.staleness-badge` span when any entry has `cachedAt`
- [ ] Staleness badge shows the oldest `cachedAt` value formatted as relative time
- [ ] No staleness badge appears when no entries have `cachedAt` (all fresh results)
- [ ] `.staleness-badge` CSS provides muted, right-aligned styling
- [ ] All DOM construction uses `createElement + textContent` (SEC-08)
- [ ] `make typecheck` passes with zero errors
- [ ] `make js-dev` bundle compiles
- [ ] `make css` rebuilds
- [ ] E2E baseline maintained: 89 pass, 2 pre-existing failures only

## Verification

- `make typecheck` — zero errors
- `make js-dev` — bundle compiles successfully
- `make css` — Tailwind rebuild succeeds
- `pytest tests/ -m e2e --tb=short -q` — 89 passed, 2 failed (pre-existing title-case only)
- `grep -rn "innerHTML\|insertAdjacentHTML" app/static/src/ts/` — only comment in graph.ts
- `grep -n "cachedAt" app/static/src/ts/modules/verdict-compute.ts` — shows the field in VerdictEntry
- `grep -n "cachedAt" app/static/src/ts/modules/enrichment.ts` — shows population from result.cached_at
- `grep -n "staleness-badge" app/static/src/ts/modules/row-factory.ts` — shows badge creation in updateSummaryRow
- `grep -n "staleness-badge" app/static/src/input.css` — shows CSS rule

## Inputs

- `app/static/src/ts/modules/verdict-compute.ts` — `VerdictEntry` interface (around line 17) with existing fields: provider, verdict, summaryText, detectionCount, totalEngines, statText
- `app/static/src/ts/modules/enrichment.ts` — Verdict branch constructs `VerdictEntry` objects and pushes them into `iocVerdicts`. T01 already added `updateContextLine` call in the context branch — this task modifies the *verdict* branch only.
- `app/static/src/ts/modules/row-factory.ts` — `updateSummaryRow()` function (line ~254) rebuilds the summary row with verdict badge, attribution, and micro-bar. `formatRelativeTime()` (line ~56) already converts ISO strings to "Xh ago" format. T01 already added `updateContextLine()` to this file.
- `app/static/src/input.css` — T01 already added `.ioc-context-line` rules. Add `.staleness-badge` nearby.
- T01 summary — Prior task added context line feature. This task must not disturb T01's additions.

## Expected Output

- `app/static/src/ts/modules/verdict-compute.ts` — `VerdictEntry` interface has `cachedAt?: string`
- `app/static/src/ts/modules/enrichment.ts` — `cachedAt: result.cached_at ?? undefined` in VerdictEntry construction
- `app/static/src/ts/modules/row-factory.ts` — `updateSummaryRow()` renders `.staleness-badge` after micro-bar when cached entries exist
- `app/static/src/input.css` — `.staleness-badge` CSS rule
- `app/static/dist/main.js` — Rebuilt JS bundle
- `app/static/dist/style.css` — Rebuilt CSS
- Full E2E suite passing at baseline (89 pass, 2 pre-existing fail)

## Observability Impact

- **New DOM signal:** `document.querySelectorAll('.staleness-badge').length` — count of IOCs whose summary row shows a cache-staleness indicator. Non-zero means at least one verdict result was served from cache.
- **Inspection:** Each `.staleness-badge` element's `textContent` shows the relative age of the oldest cached result for that IOC (e.g., "cached 4h ago").
- **Failure visibility:** If `.staleness-badge` is absent when expected, inspect `VerdictEntry` objects in `iocVerdicts` for `cachedAt` field presence — if missing, `result.cached_at` was not populated by the API response or the enrichment.ts propagation line was not reached. If the badge text shows raw ISO instead of relative time, `formatRelativeTime()` threw during parsing.
- **No staleness when fresh:** When all results are fresh (no `cached_at` on any API response), zero `.staleness-badge` elements should exist — verify via `document.querySelectorAll('.staleness-badge').length === 0`.
