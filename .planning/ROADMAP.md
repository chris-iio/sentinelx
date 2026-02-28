# Roadmap: oneshot-ioc

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-02-24)
- ✅ **v1.1 UX Overhaul** — Phases 6-8 (shipped 2026-02-25, reduced scope)
- ✅ **v1.2 Modern UI Redesign** — Phases 11-12 (shipped; 13-14 superseded by v1.3)
- ✅ **v1.3 Visual Experience Overhaul** — Phases 15-17 (shipped 2026-02-28)
- ✅ **v2.0 Home Page Modernization** — Phase 18 (shipped 2026-02-28)
- 🚧 **v3.0 TypeScript Migration** — Phases 19-23 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-4) — SHIPPED 2026-02-24</summary>

- [x] Phase 1: Foundation and Offline Pipeline (4/4 plans) — completed 2026-02-21
- [x] Phase 2: Core Enrichment (4/4 plans) — completed 2026-02-21
- [x] Phase 3: Additional TI Providers (3/3 plans) — completed 2026-02-21
- [x] Phase 3.1: Integration Fixes and Git Hygiene (1/1 plan) — completed 2026-02-22 *(INSERTED)*
- [x] Phase 4: UX Polish and Security Verification (2/2 plans) — completed 2026-02-24

Full details: `milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.1 UX Overhaul (Phases 6-8) — SHIPPED 2026-02-25</summary>

- [x] Phase 6: Foundation — Tailwind + Alpine + Card Layout — completed 2026-02-24
- [x] Phase 7: Filtering & Search — completed 2026-02-25
- [x] Phase 8: Input Page Polish — completed 2026-02-25

Phases 9-10 dropped: EXPORT and POLISH requirements superseded by v1.2 full redesign.

Full details: `milestones/v1.1-ROADMAP.md`

</details>

<details>
<summary>✅ v1.2 Modern UI Redesign (Phases 11-12) — SHIPPED 2026-02-28</summary>

- [x] Phase 11: Foundation — Design Tokens & Base CSS (3/3 plans) — completed 2026-02-28
- [x] Phase 12: Shared Component Elevation (3/3 plans) — completed 2026-02-27

Phases 13-14 superseded by v1.3 Visual Experience Overhaul (broader scope). Phase 13 plan 01 (Jinja2 partial extraction) was completed and partials are in place.

</details>

<details>
<summary>✅ v1.3 Visual Experience Overhaul (Phases 15-17) — SHIPPED 2026-02-28</summary>

- [x] Phase 15: Results Page Visual Overhaul — completed 2026-02-28
- [x] Phase 16: Input Page and Global Motion — completed 2026-02-28
- [x] Phase 17: Settings Page Polish — completed 2026-02-28

</details>

<details>
<summary>✅ v2.0 Home Page Modernization (Phase 18) — SHIPPED 2026-02-28</summary>

- [x] Phase 18: Home Page Modernization — completed 2026-02-28

</details>

### v3.0 TypeScript Migration (Phases 19-23)

- [ ] **Phase 19: Build Pipeline Infrastructure** - esbuild binary, tsconfig, Makefile targets, CSP verification
- [ ] **Phase 20: Type Definitions Foundation** - Domain types, API response interfaces, verdict constants
- [ ] **Phase 21: Simple Module Extraction** - Six typed modules (form, clipboard, card management, filter, settings, UI utilities)
- [ ] **Phase 22: Enrichment Module and Entry Point** - Complex enrichment module, main.ts entry point, template update, main.js deletion
- [ ] **Phase 23: Type Hardening and Verification** - Zero TypeScript errors, zero any types, full E2E suite passing

## Phase Details

### Phase 11: Foundation — Design Tokens & Base CSS
**Goal**: A verified dark-first design token system is in place — every color token passes WCAG AA contrast, Inter Variable and JetBrains Mono load from static fonts, and browser dark-mode signals are correct — with no structural template changes yet
**Depends on**: v1.1 complete (Phase 8)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05, FOUND-06, FOUND-07, FOUND-08
**Success Criteria** (what must be TRUE):
  1. All IOC value displays render in JetBrains Mono Variable (verifiable by inspecting font-family in DevTools on any results page IOC)
  2. All UI chrome text renders in Inter Variable (verifiable by inspecting font-family on the input page label or header)
  3. Every text/background token pair in the design system passes WCAG AA: 4.5:1 for normal text, 3:1 for UI components (verified via contrast checker against documented token values)
  4. Pasting into the settings API key field then refreshing does not produce a yellow autofill flash — the field stays dark zinc
  5. Browser scrollbar and native form controls render in dark mode (no light scrollbar on dark background in any OS-level dark-aware browser)
**Plans**: 3 plans

Plans:
- [x] 11-01-PLAN.md — Font infrastructure (download + @font-face + preload), base.html dark-mode meta, Tailwind config (darkMode + forms plugin)
- [x] 11-02-PLAN.md — Design token rewrite (zinc/emerald/teal :root), component rule migration to verdict triples, autofill override, typography scale
- [x] 11-03-PLAN.md — WCAG AA contrast verification (automated + human visual checkpoint)

### Phase 12: Shared Component Elevation
**Goal**: All shared UI primitives — verdict badges, buttons, focus rings, form elements, header/footer, icon macro — are elevated to the target design system so every subsequent page starts from a consistent premium baseline
**Depends on**: Phase 11
**Requirements**: COMP-01, COMP-02, COMP-03, COMP-04, COMP-05, COMP-06, COMP-07
**Success Criteria** (what must be TRUE):
  1. All five verdict badge states (malicious, suspicious, clean, no record, pending) use the tinted-background + colored-border + colored-text pattern — the solid amber suspicious badge is gone
  2. Every interactive element (buttons, filter pills, toggle, search input, links) shows a visible 2px teal outline on keyboard focus — no element has an invisible or box-shadow-only focus indicator
  3. Primary (emerald), secondary (zinc), and ghost button variants are visually distinct with hover and disabled states that are observable without DevTools
  4. The sticky filter bar has a frosted-glass blur effect visible when scrolling past cards (content visible through the blurred bar background)
  5. Header and footer use Inter Variable at the correct weight hierarchy with emerald accent treatment on the brand name
**Plans**: 3 plans

Plans:
- [x] 12-01-PLAN.md — Core CSS component elevation: verdict badge borders, global focus-visible ring, ghost button variant
- [x] 12-02-PLAN.md — Form element dark-theme styling and frosted-glass filter bar backdrop
- [x] 12-03-PLAN.md — Heroicons Jinja2 macro, header/footer redesign, visual verification checkpoint

### Phase 15: Results Page Visual Overhaul
**Goal**: The results page is a fully animated, visually rich experience — cards lift on hover, cascade in on load, shimmer during enrichment, show a KPI dashboard, handle empty state, and present type badges with dot indicators and a search field with icon prefix; the filter bar is scroll-aware
**Depends on**: Phase 12 (shared components), Jinja2 partials in place (from v1.2 Phase 13-01)
**Requirements**: RES-01, RES-02, RES-03, RES-04, RES-05, RES-06, RES-07, MOT-03
**Success Criteria** (what must be TRUE):
  1. Hovering any IOC card produces a visible upward lift (translateY + enhanced shadow) that begins within 150ms — observable without DevTools
  2. On page load, IOC cards animate in with a staggered cascade — each card visibly delayed from the previous by roughly 50ms, so the sequence is perceptible
  3. Each IOC type badge displays a small colored dot before the type label that distinguishes types without requiring the text to be read
  4. When no IOCs are found, the results area shows a centered icon with a "No IOCs detected" headline and a body line listing supported types — not an empty list or blank space
  5. During enrichment loading, pending IOC cards show animated shimmer rectangles (not a spinner) that animate smoothly without scroll jank
  6. The verdict stat area displays four KPI cards with large monospace numbers and colored top borders — inline pills are absent from this area
  7. The text search input has a magnifying glass icon visually inside the left edge of the field
  8. Scrolling the results page past the filter bar threshold gives the filter bar a visibly enhanced shadow/border treatment compared to its unscrolled state
**Plans**: TBD

Plans:

### Phase 16: Input Page and Global Motion
**Goal**: The input page is polished with focus glow, animated paste feedback, and mode-aware submit button; every interactive element site-wide has smooth CSS transitions; and the page load experience has an orchestrated stagger animation
**Depends on**: Phase 15
**Requirements**: INP-01, INP-02, INP-03, INP-04, MOT-01, MOT-02, MOT-04
**Success Criteria** (what must be TRUE):
  1. Focusing the textarea produces a visible emerald glow (box-shadow with accent color at low opacity) that is absent when the field is unfocused
  2. Pasting text into the textarea triggers a character count notification that slides in and fades out via CSS animation — the transition is visible and not an abrupt show/hide
  3. The submit button is emerald when Online mode is active and zinc/secondary when Offline mode is active, and it updates instantly (no page reload) when the toggle is switched
  4. The input card has a visible border and shadow treatment that creates depth separation from the zinc-950 page background
  5. On page load, the header, main content block, and footer animate in with a perceptible stagger sequence — each section begins its reveal after the previous one starts
  6. All interactive elements (buttons, pills, inputs, cards, links) across every page have smooth hover/focus/active transitions of at least 150ms — no element snaps abruptly between states
  7. Focused cards and inputs show a subtle border glow (box-shadow with accent color) in addition to the existing focus ring — observable as a soft colored halo around the focused element
**Plans**: TBD

Plans:

### Phase 17: Settings Page Polish
**Goal**: The settings page is elevated to match the v1.3 design quality — each section lives in a bordered card, the API key field uses monospace rendering with a show/hide toggle, and a status badge reflects actual key configuration
**Depends on**: Phase 16
**Requirements**: SET-01, SET-02, SET-03
**Success Criteria** (what must be TRUE):
  1. Each settings section (e.g. VirusTotal, MalwareBazaar) displays in a bordered card with the section name as a left-aligned header — not an unstyled group of fields
  2. The API key input renders in JetBrains Mono font — verifiable by inspecting font-family in DevTools — and has a show/hide toggle button that switches the field between password and text type
  3. A status badge next to or within the API key field shows "Configured" (with a success color) when the key is present in the environment, and "Not configured" (with a muted or warning color) when it is absent
**Plans**: TBD

Plans:

### Phase 18: Home Page Modernization
**Goal**: The home page is a clean, minimal, contemporary experience — a thinner header showing only logo, brand name, and settings icon; a compact auto-growing textarea; tighter inline controls; and a simplified footer that matches the header's stripped-down tone
**Depends on**: Phase 17
**Requirements**: LAY-01, LAY-02, LAY-03, INP-01, INP-02, INP-03
**Success Criteria** (what must be TRUE):
  1. The header displays exactly three elements — a logo icon, the "SentinelX" brand text, and a settings gear icon — with no tagline or descriptive text visible anywhere in the header
  2. The header is visibly thinner than the current implementation — reduced vertical padding creates a compact top bar that does not dominate the page
  3. The textarea defaults to approximately 5 visible rows on first load and grows taller as the user types or pastes text, stopping at a defined maximum height
  4. The form controls row (mode toggle + submit button) uses tighter horizontal and vertical spacing so the control group feels compact and modern rather than spread out
  5. The footer uses minimal text and reduced padding, visually matching the header's restrained aesthetic — no prominent section or decorative content
**Plans**: TBD

Plans:

### Phase 19: Build Pipeline Infrastructure
**Goal**: A working TypeScript build pipeline is in place — esbuild binary installed, Makefile targets operational, tsconfig configured for strict browser-only type checking, base.html updated to serve the compiled bundle, and the CSP security regression test still passing
**Depends on**: Phase 18 (v2.0 complete)
**Requirements**: BUILD-01, BUILD-02, BUILD-03, BUILD-04, BUILD-05, BUILD-06
**Success Criteria** (what must be TRUE):
  1. Running `make js` produces `app/static/dist/main.js` as a minified IIFE bundle and the app loads correctly in the browser with all existing functionality working
  2. Running `make js-dev` produces an unminified bundle with inline source maps — the Sources panel in browser DevTools shows TypeScript source files, not compiled output
  3. Running `make js-watch` stays running and recompiles the bundle within 200ms whenever a source file changes
  4. Running `make typecheck` executes `tsc --noEmit` and exits zero with no errors on a valid TypeScript file
  5. Running `make build` completes both CSS and JS compilation in a single command — the Makefile `build` target depends on both `css` and `js`
  6. The `test_csp_header_exact_match` security regression test passes against the compiled `dist/main.js` bundle — no CSP violation introduced by esbuild output
**Plans**: TBD

Plans:

### Phase 20: Type Definitions Foundation
**Goal**: All shared TypeScript types, interfaces, and typed constants are defined before any module conversion begins — the domain model is centralized, API response shapes are documented, and `tsc --noEmit` passes on the type files alone
**Depends on**: Phase 19
**Requirements**: TYPE-01, TYPE-02, TYPE-03, TYPE-04
**Success Criteria** (what must be TRUE):
  1. `app/static/src/ts/types/ioc.ts` defines `VerdictKey` and `IocType` as union types, and typed constants `VERDICT_SEVERITY`, `VERDICT_LABELS`, and `IOC_PROVIDER_COUNTS` — importing these in a scratch file and using a non-existent verdict key produces a TypeScript compile error
  2. `app/static/src/ts/types/api.ts` defines `EnrichmentResult` and `EnrichmentStatus` interfaces that match the Flask `/enrichment/status/{job_id}` response shape — a field name typo in a consuming module causes a type error at compile time
  3. Running `make typecheck` passes with zero errors on the type definition files — `tsc --noEmit` exits clean
  4. `tsconfig.json` at project root uses `strict: true`, `isolatedModules: true`, `noUncheckedIndexedAccess: true`, and `"types": []` — attempting to use a Node.js global like `process` produces a type error
**Plans**: TBD

Plans:

### Phase 21: Simple Module Extraction
**Goal**: Six TypeScript modules are extracted from `main.js` — form controls, clipboard, card management, filter bar, settings, and UI utilities — with proper null guards, typed DOM interactions, and established patterns (attr helper, timer types) that the enrichment module will reuse
**Depends on**: Phase 20
**Requirements**: MOD-02, MOD-03, MOD-05, MOD-06, MOD-07, MOD-08
**Success Criteria** (what must be TRUE):
  1. Each of the six modules (`form.ts`, `clipboard.ts`, `cards.ts`, `filter.ts`, `settings.ts`, `ui.ts`) exports a single `init` function — calling `make typecheck` passes with zero errors across all six files
  2. No module uses a non-null assertion (`!`) anywhere — all `querySelector` and `getElementById` calls are guarded with `if (!el) return` or equivalent null checks that TypeScript accepts
  3. All timer variables in form and UI modules use `ReturnType<typeof setTimeout>` as their declared type — no `NodeJS.Timeout` references appear anywhere in the codebase
  4. An `attr(el, name, fallback?)` helper utility exists and is used for all `getAttribute` calls — calling it with a misspelled attribute name still compiles (strings are not typed), but the return type is `string` rather than `string | null`
  5. Running the Playwright E2E suite against the compiled bundle produces the same pass/fail results as before the migration — no behavioral regressions in form controls, clipboard, filtering, or settings
**Plans**: TBD

Plans:

### Phase 22: Enrichment Module and Entry Point
**Goal**: The most complex module (`enrichment.ts`, ~350 lines) is typed and working, `main.ts` imports and initializes all modules, `base.html` references `dist/main.js`, and the original `main.js` is deleted — the migration is structurally complete
**Depends on**: Phase 21
**Requirements**: MOD-01, MOD-04, SAFE-03, SAFE-04
**Success Criteria** (what must be TRUE):
  1. `app/static/src/ts/modules/enrichment.ts` defines typed interfaces for `VerdictEntry` and the `iocVerdicts` accumulator map — no `any` types appear in the enrichment polling loop, result rendering, or verdict accumulation logic
  2. `app/static/src/ts/main.ts` exists as the esbuild entry point and imports init functions from all seven modules — the compiled bundle is produced from this single entry point
  3. `base.html` script tag references `dist/main.js` (not `main.js`) and the app loads correctly with all features working — enrichment polling, card rendering, verdict updates, and dashboard counts all function identically to pre-migration behavior
  4. `app/static/main.js` no longer exists in the repository — the original file has been deleted and `git status` shows it as removed
**Plans**: TBD

Plans:

### Phase 23: Type Hardening and Verification
**Goal**: The migration is complete and verified — zero TypeScript errors, zero unjustified `any` types, all E2E tests passing against the compiled bundle, and the full build pipeline confirmed working end-to-end
**Depends on**: Phase 22
**Requirements**: SAFE-01, SAFE-02
**Success Criteria** (what must be TRUE):
  1. `make typecheck` exits with zero errors and zero warnings — `tsc --noEmit` produces no output on a clean run
  2. `grep -r ": any" app/static/src/ts/` returns no results — no `any` type annotations exist anywhere in the TypeScript source (excluding explicitly documented exceptions in a comment)
  3. All Playwright E2E tests pass against the compiled `dist/main.js` — the full test suite produces the same results as the pre-migration baseline (pre-existing failures like `test_online_mode_indicator` remain unchanged, no new failures introduced)
  4. The `test_csp_header_exact_match` security regression test passes — the compiled bundle contains no `eval`, no `Function()` constructor, and no inline event handlers
  5. Running `make build` from a clean state produces both `app/static/dist/style.css` and `app/static/dist/main.js` correctly — the full build pipeline works end-to-end
**Plans**: TBD

Plans:

## Progress

**Execution Order:**
v3.0 phases execute in numeric order: 19 → 20 → 21 → 22 → 23

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation and Offline Pipeline | v1.0 | 4/4 | Complete | 2026-02-21 |
| 2. Core Enrichment | v1.0 | 4/4 | Complete | 2026-02-21 |
| 3. Additional TI Providers | v1.0 | 3/3 | Complete | 2026-02-21 |
| 3.1. Integration Fixes and Git Hygiene | v1.0 | 1/1 | Complete | 2026-02-22 |
| 4. UX Polish and Security Verification | v1.0 | 2/2 | Complete | 2026-02-24 |
| 6. Foundation — Tailwind + Alpine + Card Layout | v1.1 | 0/? | Complete | 2026-02-24 |
| 7. Filtering & Search | v1.1 | 2/2 | Complete | 2026-02-25 |
| 8. Input Page Polish | v1.1 | 2/2 | Complete | 2026-02-25 |
| 11. Foundation — Design Tokens & Base CSS | v1.2 | 3/3 | Complete | 2026-02-28 |
| 12. Shared Component Elevation | v1.2 | 3/3 | Complete | 2026-02-27 |
| 15. Results Page Visual Overhaul | v1.3 | 0/? | Complete | 2026-02-28 |
| 16. Input Page and Global Motion | v1.3 | 0/? | Complete | 2026-02-28 |
| 17. Settings Page Polish | v1.3 | 0/? | Complete | 2026-02-28 |
| 18. Home Page Modernization | v2.0 | 3/3 | Complete | 2026-02-28 |
| 19. Build Pipeline Infrastructure | v3.0 | 0/? | Not started | — |
| 20. Type Definitions Foundation | v3.0 | 0/? | Not started | — |
| 21. Simple Module Extraction | v3.0 | 0/? | Not started | — |
| 22. Enrichment Module and Entry Point | v3.0 | 0/? | Not started | — |
| 23. Type Hardening and Verification | v3.0 | 0/? | Not started | — |
