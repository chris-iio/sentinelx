# M015: Intake Workbench

**Vision:** Redesign SentinelX’s home/input page into a fast analyst Intake Workbench: paste stays dominant, Offline/Online mode becomes clearer, compact Recent Analyses help resume work, and the existing extraction/enrichment/history behavior remains unchanged.

## Success Criteria

- The `/` page functions as a fast analyst intake workbench with the paste form as the dominant action.
- The primary user flow remains paste → choose Offline/Online → Extract → results, with no pre-submit preview.
- Offline/Online mode is clearer but preserves the existing hidden `mode` form contract and accessibility behavior.
- Compact Recent Analyses appears on the intake page when history exists and links to saved analysis reloads.
- History listing failures never block the paste form or extraction path.
- Desktop and mobile layouts preserve the command-card priority and keep history visually secondary.
- Existing extraction, enrichment, history reload, CSRF/security, TypeScript/build, and E2E behavior remain intact.

## Slices

- [x] **S01: S01** `risk:Medium — visual restructuring can break existing homepage selectors, form semantics, or the fast path if not grounded in current DOM contracts.` `depends:[]`
  > After this: The home page has a redesigned command-card layout where the analyst can paste IOC text, see Extract enable, and submit offline exactly as before.

- [x] **S02: S02** `risk:Medium — mode UI changes are small but can silently break form submission, accessibility, or existing tests.` `depends:[]`
  > After this: Offline/Online mode is visually clearer and keyboard-accessible while preserving the existing hidden `mode` form contract and current submit behavior.

- [x] **S03: S03** `risk:High — this is the only slice that adds a data dependency to `/`, and it must not make history availability a prerequisite for intake.` `depends:[]`
  > After this: The intake page shows a compact recent-analysis rail/list when history exists, links into `/history/<id>`, and still renders the paste form if history listing fails.

- [ ] **S04: S04** `risk:Medium — individual pieces are straightforward, but composition can still regress responsive layout, accessibility, or existing E2E coverage.` `depends:[]`
  > After this: The assembled intake workbench is verified on desktop/mobile, fast paste-to-results still works, history resume works, and existing SentinelX verification remains green.

## Boundary Map

### S01 → S02

Produces:
- `index.html` command-card structure with stable form controls: `#ioc-text`, `#submit-btn`, `#clear-btn`, `#mode-input`, `#mode-toggle-widget`, `#mode-toggle-btn`
- CSS layout foundation for `.page-index`, command card, responsive workbench container, and primary action hierarchy
- Browser proof that paste → Extract offline still reaches results

Consumes:
- nothing (first slice)

### S01 → S03

Produces:
- Stable intake page layout with a defined secondary rail/list area for Recent Analyses
- Visual hierarchy constraints: paste command card remains dominant; secondary surfaces cannot block or crowd the form
- Existing form submit behavior preserved so history additions can stay orthogonal

Consumes:
- nothing (first slice)

### S02 → S04

Produces:
- Clarified Offline/Online mode UI while preserving hidden `mode` input semantics
- Keyboard/aria behavior for the mode control
- Tests proving current offline/online form behavior survives visual clarification

Consumes from S01:
- command-card form structure and baseline intake layout

### S03 → S04

Produces:
- Index route recent-analysis summary contract: bounded list from `HistoryStore.list_recent(limit)` passed to `index.html`
- Jinja markup and CSS classes for compact recent rows, empty state, and history-unavailable state
- Tests proving recent rows link to `/history/<id>` and history failure does not block the form

Consumes from S01:
- secondary rail/list region and responsive hierarchy

### S01 + S02 + S03 → S04

Produces:
- Complete intake workbench pieces: command card, clarified mode, compact history, failure states, responsive styling

Consumes:
- all prior slice outputs and verifies them together through browser and full repository proof
