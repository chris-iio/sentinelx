# T01: 01-contracts-and-foundation 01

**Slice:** S01 — **Milestone:** M001

## Description

Create the CSS contract catalog, inline source-file annotations, and CSS layer ownership rule that protect all subsequent v1.1 phases from accidentally breaking E2E tests.

Purpose: Phase 1 is the safety net. Every class rename, attribute move, or Tailwind utility addition in Phases 2-5 must check against these contracts first. Without this documentation, silent E2E breakage is inevitable (the research identified 24 template selectors, 18 JS-created runtime classes, and 3 data-attribute contracts across 4 independent consumers).

Output: CSS-CONTRACTS.md (planning artifact), inline contract comment in _ioc_card.html, CSS layer ownership comment in input.css, confirmed E2E baseline at 91/91.

## Must-Haves

- [ ] "Every CSS class used by E2E selectors is catalogued with a do-not-rename rule"
- [ ] "The data-ioc-value, data-ioc-type, and data-verdict triple-consumer contract is documented inline in the template"
- [ ] "Information density acceptance criteria exist as a written, checkable table"
- [ ] "A CSS layer ownership rule comment exists at the top of input.css"
- [ ] "91 E2E tests pass at baseline confirming no regressions from documentation commits"

## Files

- `.planning/phases/01-contracts-and-foundation/CSS-CONTRACTS.md`
- `app/templates/partials/_ioc_card.html`
- `app/static/src/input.css`
