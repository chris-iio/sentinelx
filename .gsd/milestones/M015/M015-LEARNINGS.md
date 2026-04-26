---
phase: complete
phase_name: learnings-extraction
project: SentinelX
generated: 2026-04-26T12:06:25Z
counts:
  decisions: 4
  lessons: 4
  patterns: 5
  surprises: 2
missing_artifacts:
  - Slice ASSESSMENT.md files were not present under M015 slices; M015-VALIDATION.md records that passing SUMMARY.md evidence and DB status were used instead.
---

# M015 Learnings — Intake Workbench

### Decisions

- Chose server-rendered compact Recent Analyses on `/` using bounded `HistoryStore.list_recent(limit=4)` and existing `/history/<id>` links instead of introducing a new client fetch/polling API.
  Source: DECISIONS.md/D070

- Chose a dominant command card with a compact secondary recent rail on desktop and a stacked recent list on mobile so paste → mode → Extract remains the primary action.
  Source: DECISIONS.md/D071

- Chose to clarify the existing Offline/Online toggle while preserving `#mode-input`, `#mode-toggle-widget`, `#mode-toggle-btn`, native button behavior, and current form submission semantics.
  Source: DECISIONS.md/D072

- Chose to exclude pre-submit IOC preview, provider/enrichment changes, heavy dashboarding, and results/detail redesign from M015 to protect the fast-intake scope.
  Source: DECISIONS.md/D073

### Lessons

- Contract tests should pin stable form selectors and route behavior before UI restructuring; this let S01 layer the command-card redesign without breaking CSRF, submit enablement, hidden mode input, or the Offline paste-to-results path.
  Source: S01-SUMMARY.md/What Happened

- Mode UI can drift unless all visible and hidden state renders from one normalized path; centralizing state in `form.ts` kept the hidden input, widget data, ARIA state, visible status, and submit-button styling synchronized.
  Source: S02-SUMMARY.md/What Happened

- Secondary history storage must be treated as non-critical on `/`; fail-open exception handling plus a quiet unavailable state preserved intake when history listing was unhealthy.
  Source: S03-SUMMARY.md/What Happened

- Mobile responsive assertions can reveal composition regressions that isolated slices miss; the final S04 browser check exposed horizontal overflow only after command card, mode UI, recent rail, and shell constraints were assembled.
  Source: S04-SUMMARY.md/What Happened

### Patterns

- Use `.page-index`, `.intake-workbench`, and `.command-card` as the stable intake-page shell, and preserve existing form-control selectors when changing visual hierarchy.
  Source: S01-SUMMARY.md/Patterns Established

- Keep Offline/Online mode improvements additive around the hidden-input form contract, with focused Flask, Vitest, and Playwright checks covering server-rendered IDs, DOM synchronization, and live submit behavior.
  Source: S02-SUMMARY.md/Patterns Established

- Add secondary data surfaces to `/` as bounded, fail-open, server-rendered surfaces that cannot block the primary paste form.
  Source: S03-SUMMARY.md/Patterns Established

- Seed Playwright Recent Analyses through the isolated live `HistoryStore` fixture and click real `/history/<id>` links rather than relying on developer-local SQLite state or DOM-only mocks.
  Source: S03-SUMMARY.md/Patterns Established

- Final intake workbench proof should combine route/security assertions and browser assertions so command card, mode state, recent history, fail-open behavior, no-preview exclusions, and fast Offline extraction are verified as one assembled flow.
  Source: S04-SUMMARY.md/Patterns Established

### Surprises

- The integrated mobile layout had horizontal overflow even though the individual pieces were straightforward; the fix was to widen only the index page shell and constrain the decorative pseudo-element, not clip the page shell.
  Source: S04-SUMMARY.md/Deviations

- A pre-existing CSP warning about inline style application appeared during early browser diagnostics, but it was not introduced by M015 and did not block the conservative intake redesign.
  Source: S01-SUMMARY.md/Known Limitations
