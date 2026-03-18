---
estimated_steps: 7
estimated_files: 3
---

# T03: Visual polish pass, --bg-hover verification, production build gate

**Slice:** S04 — Functionality integration + polish
**Milestone:** M002

## Description

R010 requires performance doesn't regress and the build stays lean. S03 forward intelligence flagged `--bg-hover` as fragile — "used in `.ioc-summary-row:hover` but not confirmed to be defined in the design system. If undefined, hover state will silently fail." This task verifies the token, applies any CSS polish needed for spacing/transitions, runs the production build, and performs the final E2E gate.

This is the only S04 task that may produce code changes (CSS only). All changes are in `input.css` — no TypeScript modifications.

**Skill note:** Load the `lint` skill if formatting issues arise during CSS edits.

## Steps

1. Verify `--bg-hover` token is defined in `input.css`:
   ```
   grep -n 'bg-hover' app/static/src/input.css
   ```
   Must find a definition in the `:root`, `@theme`, or Tailwind config block. If undefined, add it with a muted value consistent with the quiet precision design system (e.g., a subtle gray like `oklch(0.25 0 0)` or similar — match the existing token pattern). Also verify it compiles into `dist/style.css`.

2. Review S03 forward intelligence CSS items:
   - Confirm `.ioc-summary-row:hover` uses `var(--bg-hover)` and the compiled CSS contains it
   - Confirm chevron rotation CSS (`.ioc-summary-row.is-open .chevron-icon`) is present in dist
   - Confirm `.detail-link-footer` and `.detail-link` styles are in dist

3. Check spacing consistency in `input.css`:
   - Expanded panel padding (`.enrichment-details.is-open`) — consistent with row padding
   - Filter bar alignment — `._filter_bar` section consistent with dashboard and results spacing
   - Dashboard-to-results gap — verify no excessive whitespace between verdict summary and IOC rows

4. If any CSS adjustments are needed, edit `app/static/src/input.css` only. Keep changes minimal — this is polish, not redesign. Follow the existing design token pattern.

5. Rebuild all assets:
   ```
   make css && make js-dev
   ```

6. Production build and size check:
   ```
   make js
   wc -c app/static/dist/main.js
   ```
   Must be ≤ 30KB (30,000 bytes). Current baseline: 26.6KB.

7. Final E2E gate:
   ```
   pytest tests/e2e/ -q
   ```
   Must pass 36/36. Any failure after CSS-only changes indicates a CSS change broke a visual assertion or element visibility — investigate immediately.

## Must-Haves

- [ ] `--bg-hover` token defined in `input.css` and compiled into `dist/style.css`
- [ ] S03 CSS artifacts confirmed in dist: `.ioc-summary-row:hover`, chevron rotation, detail link styles
- [ ] Production build size ≤ 30KB
- [ ] `make css && make js-dev` succeeds
- [ ] `make js` succeeds
- [ ] `pytest tests/e2e/ -q` passes 36/36
- [ ] Any CSS polish edits are minimal and follow existing design token patterns

## Verification

- `grep -n 'bg-hover' app/static/src/input.css` — definition found
- `grep 'bg-hover' app/static/dist/style.css` — compiled into output
- `wc -c app/static/dist/main.js` — ≤ 30,000 bytes
- `pytest tests/e2e/ -q` — 36/36 pass

## Observability Impact

**Signals produced by this task:**
- `app/static/dist/style.css` — rebuilt; `grep 'bg-hover' dist/style.css` confirms the token compiled through
- `app/static/dist/main.js` — rebuilt production bundle; `wc -c` reads bundle size directly as a byte count
- E2E test suite — `pytest tests/e2e/ -q` produces a pass/fail count; failures after CSS-only changes indicate element visibility regressions

**How a future agent inspects this task:**
- Token presence: `grep 'bg-hover' app/static/src/input.css` (source) + `grep 'bg-hover' app/static/dist/style.css` (compiled)
- S03 CSS artifacts: `grep 'ioc-summary-row\|chevron-icon\|detail-link' app/static/dist/style.css`
- Bundle size gate: `wc -c app/static/dist/main.js` — value must be ≤ 30000
- Build health: `make css && make js` — exit code 0 means all assets compiled cleanly

**Failure state visibility:**
- `--bg-hover` undefined in dist → hover state on `.ioc-summary-row` silently does nothing (no JS error, purely visual)
- Bundle size > 30KB → tree-shaking regression; check for new large imports in TS modules
- CSS build failure → `make css` exits non-zero with postcss/tailwind error on stderr
- E2E failure after CSS change → a visual assertion or `display:none` style gate broke; check `pytest -v` output for specific test name

## Inputs

- T01 completed: integration pipeline verified, builds green
- T02 completed: security audit clean
- S03 forward intelligence: `--bg-hover` flagged as fragile; `.ioc-summary-row:hover` depends on it

## Expected Output

- `app/static/src/input.css` — possibly modified with `--bg-hover` definition or minor spacing polish
- `app/static/dist/style.css` — rebuilt with any CSS changes
- `app/static/dist/main.js` — rebuilt, ≤ 30KB production
- Final E2E pass evidence: 36/36
