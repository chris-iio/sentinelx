# SentinelX

## What This Is

A universal threat intelligence hub for SOC analysts. Paste free-form text (alerts, email headers, threat reports, raw IOCs) and the app extracts, normalizes, classifies, and enriches IOCs against 14 providers in parallel — presenting unified summary verdicts with expandable per-provider detail rows, bookmarkable per-IOC detail pages with relationship graphs, and analyst annotations (notes + tags). No opaque combined scores.

## Core Value

Safe, correct, and transparent IOC extraction and enrichment — never invent scores, never make network calls the analyst didn't ask for, never trust input or API responses.

## Current State

**M004 complete (2026-03-24).** Partial success — 5 of 8 success criteria met; 3 descoped (safe_request consolidation, registry caching, adapter LOC reduction). What landed: S01 fixed 4 orchestrator concurrency bugs + SSLError/ConnectionError handlers in all 12 adapters. S02: ?since= polling cursor (O(N) vs O(N²)), persistent requests.Session on all 12 adapters, ipinfo.io HTTPS replaces ip-api.com HTTP, CacheStore WAL + persistent connection + purge_expired(), ConfigStore cached reads. S03: dead TS code removed, dead CSS rules pruned, 5 O(N²) frontend patterns fixed (R023). S04: shared test helpers (tests/helpers.py) — 10 adapter test files migrated, CSP header expanded to 7 directives, SECRET_KEY startup warning, tsconfig incremental + tailwind email safelist. 944 tests (839 unit + 105 E2E) passing. R018–R025 all validated.

**M003 complete (2026-03-21).** S01: per-provider concurrency semaphore (VT ≤4, zero-auth unlimited) + 429-aware exponential backoff. S02: email IOC extraction and EMAIL group rendering (6 new E2E tests). S03: detail page design refresh (M002 zinc tokens, stacked provider cards, graph label truncation fixed). S04: summaryTimers debounce map in enrichment.ts (1–2 summary row rebuilds per IOC instead of 10), all M003 gates verified. Final state: 828 unit tests + 105 E2E tests passing, typecheck clean, bundle 26,783 bytes. R012, R014, R015, R016, R017 all validated.

## Architecture / Key Patterns

- **Backend:** Python 3.10 + Flask 3.1, iocextract + iocsearcher for extraction, requests + dnspython for HTTP/DNS
- **Frontend:** TypeScript 5.8 + esbuild (IIFE output), Tailwind CSS standalone CLI, Inter Variable + JetBrains Mono Variable, dark-first zinc design tokens with verdict-only color accents
- **Modules:** 13 TypeScript modules (main.ts + 10 modules/ + 2 types/ + 1 utils/)
- **Security:** CSP, CSRF, SSRF allowlist, host validation, textContent-only DOM (SEC-08)
- **Build:** Makefile targets — `css`, `js`, `js-dev`, `js-watch`, `typecheck`, `build`
- **Tests:** 944 unit/integration + 105 E2E (Playwright, route-mocking infrastructure in conftest.py)

## Capability Contract

See `.gsd/REQUIREMENTS.md` for the explicit capability contract, requirement status, and coverage mapping.

## Milestone Sequence

- [x] M001: v1.1 Results Page Redesign — Uniform IOC card architecture, verdict badge prominence, micro-bar, category labels, three-section grouping, inline context line, cache staleness badge
- [x] M002: v1.2 Results Page Rework — Information-first redesign: single-column layout, quiet precision design, at-a-glance enrichment surface, inline expand/collapse, full integration + security audit, E2E suite 91→99 tests
- [x] M003: System Efficiency & Completeness — S01 ✅ S02 ✅ S03 ✅ S04 ✅ (all complete)
- [x] M004: Hardening — S01 ✅ S02 ✅ S03 ✅ S04 ✅ (all complete, partial success — 5/8 criteria met)

---
*Last updated: 2026-03-24 — M004 closed. 944 tests passing (839 unit + 105 E2E). R018–R025 validated. Descoped: safe_request(), registry caching, routes decomposition.*
