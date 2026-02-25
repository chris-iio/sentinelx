# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-25)

**Core value:** Safe, correct, and transparent IOC extraction and enrichment — never invent scores, never make network calls the analyst didn't ask for, never trust input or API responses.
**Current focus:** Phase 11 — Foundation (Design Tokens & Base CSS)

## Current Position

Phase: 11 of 14 (Foundation — Design Tokens & Base CSS)
Plan: 0 of ? in current phase
Status: Ready to plan
Last activity: 2026-02-25 — v1.2 roadmap created, phases 11-14 defined

Progress: [██████████░░░░░░░░░░] ~50% (8/14 phases complete across all milestones — counting shipped v1.0 and v1.1 work)

## Performance Metrics

**Velocity:**
- Total plans completed: 14 (v1.0) + 4 (v1.1 partial) = 18
- v1.1 avg duration: fast (frontend-only, 2 days for 3 phases)
- Total execution time: ~6 days across v1.0 + v1.1

**By Phase (v1.2 — not yet started):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 11. Foundation | TBD | — | — |
| 12. Components | TBD | — | — |
| 13. Results | TBD | — | — |
| 14. Input/Settings | TBD | — | — |

*Updated after each plan completion*

## Accumulated Context

### Decisions

- v1.1 Alpine CSP vendor removed — Phase 7 switched to pure vanilla JS `initFilterBar()`; no Alpine dependency
- data-verdict attribute is single source of truth for CSS border, JS sorting, and dashboard counts
- Toggle uses data-mode on wrapper div; hidden input name=mode carries form POST to Flask (route unchanged)
- Tailwind safelist is critical for dynamic class names (ioc-type-badge--{type}, verdict-{verdict} families)
- v1.2 architecture: CSS custom properties at :root as token layer; component styles in @layer components using BEM class names; no utility-first strings in Jinja2 loops
- v1.2 stack additions: Inter Variable + JetBrains Mono (self-hosted in app/static/fonts/), Heroicons v2 inline SVG, @tailwindcss/forms plugin, darkMode: 'selector' config

### Pending Todos

None.

### Blockers/Concerns

- Pre-existing: E2E tests test_online_mode_indicator and test_online_mode_shows_verdict_dashboard fail without VT API key (not a regression, not v1.2 scope)
- Phase 11 gate criterion: all text/background token pairs must pass WCAG AA (4.5:1 normal, 3:1 UI) before moving to Phase 12
- Phase 13 gate criterion: Playwright E2E tests must pass after partial extraction before any visual changes

## Session Continuity

Last session: 2026-02-25
Stopped at: v1.2 roadmap created — ready to plan Phase 11
Resume file: None
