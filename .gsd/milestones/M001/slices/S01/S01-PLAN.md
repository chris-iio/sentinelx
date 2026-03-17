# S01: Contracts And Foundation

**Goal:** All preservation contracts are documented and enforced before a single line of visual code changes — CSS contract catalog, inline source annotations, layer ownership rule, and E2E baseline confirmation.
**Demo:** CSS-CONTRACTS.md committed with 24 E2E-locked selectors, 18 JS-created runtime classes, and 3 data-attribute contracts catalogued; inline annotations in source files; E2E baseline confirmed at 89/91.

## Must-Haves


## Tasks

- [x] **T01: 01-contracts-and-foundation 01** `est:3min`
  - Create the CSS contract catalog, inline source-file annotations, and CSS layer ownership rule that protect all subsequent v1.1 phases from accidentally breaking E2E tests.

Purpose: Phase 1 is the safety net. Every class rename, attribute move, or Tailwind utility addition in Phases 2-5 must check against these contracts first. Without this documentation, silent E2E breakage is inevitable (the research identified 24 template selectors, 18 JS-created runtime classes, and 3 data-attribute contracts across 4 independent consumers).

Output: CSS-CONTRACTS.md (planning artifact), inline contract comment in _ioc_card.html, CSS layer ownership comment in input.css, confirmed E2E baseline at 91/91.

## Files Likely Touched

- `.planning/phases/01-contracts-and-foundation/CSS-CONTRACTS.md`
- `app/templates/partials/_ioc_card.html`
- `app/static/src/input.css`
