---
estimated_steps: 7
estimated_files: 4
skills_used: []
---

# T02: Audit the current browser loop on desktop/mobile

Why: The redesign target must come from the actual product loop, not a generic preference for minimal UI.

Do:
1. Start or use the supported local dev-server path.
2. Exercise `/` on desktop and mobile viewport sizes.
3. Submit a representative Offline sample containing multiple IOC types.
4. Inspect results page hierarchy: header, progress/status, filters, dashboard chrome, result cards, details/context affordances.
5. Load a prior analysis from history and confirm where history feels helpful vs distracting.
6. Record friction points with file/template/selector references and separate must-fix from nice-to-have.
7. Identify which elements should be removed, collapsed, quieted, or preserved for S02/S03.

Done when: A concise audit artifact exists with concrete UI observations tied to code locations and product-loop steps.

## Inputs

- `.gsd/milestones/M016/M016-RESEARCH.md`
- `app/templates/index.html`
- `app/templates/results.html`
- `app/templates/partials/_verdict_dashboard.html`
- `app/templates/partials/_filter_bar.html`
- Existing dev-server/browser verification conventions.

## Expected Output

- Audit notes in an appropriate M016 artifact or slice note.
- Prioritized target list for S02/S03.

## Verification

Audit notes must include:

- Desktop observation for intake.
- Mobile observation for intake.
- Offline results observation.
- Online/progress or mocked-online observation if feasible.
- History resume observation.
- Specific file/selector references for each recommended change.

## Observability Impact

No runtime code changes. The output should make future UI changes easier to verify because it names the exact workflow states that matter.
