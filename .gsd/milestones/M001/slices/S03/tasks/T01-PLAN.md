---
estimated_steps: 6
estimated_files: 2
---

# T01: Enlarge verdict badge and replace consensus badge with micro-bar

**Slice:** S03 — Visual Redesign
**Milestone:** M001

## Description

Deliver VIS-01 (verdict badge prominence) and VIS-02 (micro-bar replacing consensus badge). These are the header/summary row visual changes that create a clear hierarchy: the IOC card header verdict badge becomes the dominant scan target, and the text consensus badge `[2/5]` is replaced by a proportional micro-bar encoding the verdict distribution.

VIS-01 is CSS-only — increase `.verdict-label` size. VIS-02 touches both CSS (new micro-bar classes) and TypeScript (rewrite the consensus badge block in `updateSummaryRow()`).

**Critical constraint:** `.verdict-label` is E2E-locked — do NOT rename the class. Only modify its CSS properties. The `.consensus-badge` class is in the "JS-Created Runtime Classes" table but NO E2E Playwright test queries it (confirmed via grep). It is safe to stop creating it in `updateSummaryRow()`.

**Relevant skill:** `frontend-design` — load for CSS/DOM builder guidance.

## Steps

1. **Verify `.consensus-badge` is safe to remove from DOM construction.** Run `grep -r "consensus.badge\|consensus-badge" tests/e2e/` — must return zero results. If any test references it, abort and escalate.

2. **CSS — VIS-01: Enlarge `.verdict-label`.** In `app/static/src/input.css`, find the `.verdict-label` block (around line 1030). Change:
   - `font-size: 0.7rem` → `font-size: 0.875rem`
   - `font-weight: 600` → `font-weight: 700`
   - `padding: 0.1rem 0.4rem` → `padding: 0.25rem 0.75rem`
   
   Leave all other properties unchanged (font-family, letter-spacing, text-transform, border-radius, flex-shrink). The `.verdict-badge` in provider rows (around line 1145) stays at `0.72rem` / `2px 8px` — do NOT change it. This size gap creates the visual hierarchy.

3. **CSS — VIS-02: Add micro-bar classes.** In `app/static/src/input.css`, after the `.consensus-badge` block (around lines 1185-1210), add new classes:
   ```css
   .verdict-micro-bar {
       display: flex;
       height: 6px;
       border-radius: 3px;
       overflow: hidden;
       min-width: 4rem;
       flex-shrink: 0;
       background-color: var(--bg-tertiary);
   }
   .micro-bar-segment {
       height: 100%;
       transition: width var(--duration-fast) ease;
       min-width: 0;
   }
   .micro-bar-segment--malicious  { background-color: var(--verdict-malicious-border); }
   .micro-bar-segment--suspicious { background-color: var(--verdict-suspicious-border); }
   .micro-bar-segment--clean      { background-color: var(--verdict-clean-border); }
   .micro-bar-segment--no_data    { background-color: var(--bg-hover); }
   ```
   Do NOT remove the existing `.consensus-badge` CSS — leave it as dead CSS for now. It can be cleaned up later.

4. **TypeScript — Add `computeVerdictCounts()` helper.** In `app/static/src/ts/modules/row-factory.ts`, add a private helper function (near other private helpers at top of file):
   ```typescript
   function computeVerdictCounts(entries: VerdictEntry[]): {
     malicious: number; suspicious: number; clean: number; noData: number; total: number;
   } {
     let malicious = 0, suspicious = 0, clean = 0, noData = 0;
     for (const e of entries) {
       if (e.verdict === "malicious") malicious++;
       else if (e.verdict === "suspicious") suspicious++;
       else if (e.verdict === "clean") clean++;
       else noData++;
     }
     return { malicious, suspicious, clean, noData, total: entries.length };
   }
   ```

5. **TypeScript — Replace consensus badge with micro-bar in `updateSummaryRow()`.** Find the block in `updateSummaryRow()` (around line 269-272) that creates `consensusBadge`:
   ```typescript
   const consensusBadge = document.createElement("span");
   consensusBadge.className = "consensus-badge " + consensusBadgeClass(flagged);
   consensusBadge.textContent = "[" + flagged + "/" + responded + "]";
   summaryRow.appendChild(consensusBadge);
   ```
   Replace it with:
   ```typescript
   const counts = computeVerdictCounts(entries);
   const total = Math.max(1, counts.total);
   const microBar = document.createElement("div");
   microBar.className = "verdict-micro-bar";
   microBar.setAttribute("title",
     `${counts.malicious} malicious, ${counts.suspicious} suspicious, ${counts.clean} clean, ${counts.noData} no data`
   );
   const segments: Array<[number, string]> = [
     [counts.malicious, "malicious"],
     [counts.suspicious, "suspicious"],
     [counts.clean, "clean"],
     [counts.noData, "no_data"],
   ];
   for (const [count, verdict] of segments) {
     if (count === 0) continue;
     const seg = document.createElement("div");
     seg.className = "micro-bar-segment micro-bar-segment--" + verdict;
     seg.style.width = Math.round((count / total) * 100) + "%";
     microBar.appendChild(seg);
   }
   summaryRow.appendChild(microBar);
   ```
   This requires `entries` (the `VerdictEntry[]` array) to be available in `updateSummaryRow()`. Check the function signature — it receives `entries: VerdictEntry[]` among its parameters. If not, it receives `iocVerdicts` and the ioc value to look up entries.

6. **Clean up unused import.** If `consensusBadgeClass` is no longer used anywhere in `row-factory.ts`, remove it from the import statement at the top of the file (line ~19). Run `grep -n "consensusBadgeClass" app/static/src/ts/modules/row-factory.ts` to confirm. Also check if `verdict-compute.ts` still needs to export it — if `row-factory.ts` was the only consumer, add a `// Phase 3: no longer used, kept for API stability` comment in verdict-compute.ts rather than removing the export.

## Must-Haves

- [ ] `.verdict-label` CSS: font-size 0.875rem, font-weight 700, padding 0.25rem 0.75rem
- [ ] `.verdict-badge` CSS: UNCHANGED at 0.72rem / 2px 8px
- [ ] New CSS classes: `.verdict-micro-bar`, `.micro-bar-segment`, `.micro-bar-segment--{malicious,suspicious,clean,no_data}`
- [ ] `computeVerdictCounts()` private helper in row-factory.ts
- [ ] `updateSummaryRow()` creates `.verdict-micro-bar` div with percentage-width segments
- [ ] Micro-bar `title` attribute encodes exact counts for accessibility
- [ ] Zero-count segments are skipped (no empty divs in the micro-bar)
- [ ] `total === 0` case guarded — no NaN widths
- [ ] No E2E-locked class renamed or removed
- [ ] `make typecheck && make js-dev && make css` all pass

## Verification

- `grep -r "consensus.badge\|consensus-badge" tests/e2e/` — zero results (pre-step safety)
- `make css` — CSS builds successfully
- `make typecheck` — zero TypeScript errors
- `make js-dev` — esbuild bundles successfully
- `pytest tests/ -m e2e --tb=short -q` — 89/91 baseline maintained
- `grep -n "consensusBadge" app/static/src/ts/modules/row-factory.ts` — no remaining references to old consensus badge creation

## Inputs

- `app/static/src/input.css` — current CSS with `.verdict-label` (line ~1030), `.verdict-badge` (line ~1145), `.consensus-badge` (line ~1185)
- `app/static/src/ts/modules/row-factory.ts` — current DOM builders with `updateSummaryRow()` (line ~239) creating consensus badge (line ~269)
- `app/static/src/ts/modules/verdict-compute.ts` — exports `VerdictEntry` type and `consensusBadgeClass`

## Expected Output

- `app/static/src/input.css` — `.verdict-label` enlarged; new `.verdict-micro-bar` and `.micro-bar-segment` classes added
- `app/static/src/ts/modules/row-factory.ts` — `computeVerdictCounts()` helper added; `updateSummaryRow()` creates micro-bar instead of consensus badge; `consensusBadgeClass` import removed if unused
