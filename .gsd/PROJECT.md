# SentinelX

## What This Is

A universal threat intelligence hub for SOC analysts. Paste free-form text (alerts, email headers, threat reports, raw IOCs) and the app extracts, normalizes, classifies, and enriches IOCs against 14 providers in parallel — presenting unified summary verdicts with expandable per-provider detail rows, bookmarkable per-IOC detail pages with relationship graphs, and analyst annotations (notes + tags). No opaque combined scores.

## Core Value

Safe, correct, and transparent IOC extraction and enrichment — never invent scores, never make network calls the analyst didn't ask for, never trust input or API responses.

## Current State

v1.1 shipped (2026-03-17). M002 S01 complete (2026-03-18): Results page now renders in single-column full-width rows with quiet precision design system — verdict-only loud color, muted type badges, compressed dashboard, compact filter bar. All 16 DOM contract selectors preserved, 36 E2E tests passing. M002 S02 complete (2026-03-18): At-a-glance enrichment surface (verdict badge, context line, provider stat line, micro-bar, staleness badge) renders at full opacity after enrichment. M002 S03 complete (2026-03-18): Summary row is now the expand/collapse click target — event-delegated, keyboard-accessible, animated chevron, "View full detail →" link injected on enrichment completion, expanded panel polished with design tokens only. All builds and 36 E2E tests passing. Next: S04 (functionality integration + polish).

## Architecture / Key Patterns

- **Backend:** Python 3.10 + Flask 3.1, iocextract + iocsearcher for extraction, requests + dnspython for HTTP/DNS
- **Frontend:** TypeScript 5.8 + esbuild (IIFE output), Tailwind CSS standalone CLI, Inter Variable + JetBrains Mono Variable, dark-first zinc/emerald/teal design tokens
- **Modules:** 13 TypeScript modules (main.ts + 10 modules/ + 2 types/ + 1 utils/)
- **Security:** CSP, CSRF, SSRF allowlist, host validation, textContent-only DOM (SEC-08)
- **Build:** Makefile targets — `css`, `js`, `js-dev`, `js-watch`, `typecheck`, `build`
- **Tests:** 757+ unit/integration + 91 E2E (Playwright)

## Capability Contract

See `.gsd/REQUIREMENTS.md` for the explicit capability contract, requirement status, and coverage mapping.

## Milestone Sequence

- [x] M001: v1.1 Results Page Redesign — Uniform IOC card architecture, verdict badge prominence, micro-bar, category labels, three-section grouping, inline context line, cache staleness badge
- [x] M002: Results Page Rework — Information-first redesign: single-column layout, quiet precision design, progressive disclosure, at-a-glance enrichment surface

---
*Last updated: 2026-03-18 — M002/S03 complete*
