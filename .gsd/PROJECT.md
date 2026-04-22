# SentinelX

## What This Is

A universal threat intelligence hub for SOC analysts. Paste free-form text (alerts, email headers, threat reports, raw IOCs) and the app extracts, normalizes, classifies, and enriches IOCs against 15 providers in parallel — presenting unified summary verdicts with expandable per-provider detail rows, bookmarkable per-IOC detail pages with relationship graphs, and analyst annotations (notes + tags). Analyses are persisted to SQLite and reloadable from the home page. No opaque combined scores.

## Core Value

Safe, correct, and transparent IOC extraction and enrichment — never invent scores, never make network calls the analyst didn't ask for, never trust input or API responses.

## Current State

**M012 in progress; S01, S02, and S03 complete (2026-04-22).** The live enrichment status path now exposes explicit terminal outcomes for unknown, evicted, and failed jobs while preserving the existing cursor-polling success contract. The results surface now also uses one shared live/history result-application path plus explicit `.page-results[data-results-owner]` dispatch, so history replay renders the same enrichment cards, detail rows, progress state, verdicts, detail links, export readiness, and copy-button summaries as live polling without ever leaking `/enrichment/status/history` fetches or duplicate listener wiring. The repo’s proof surface is now split into an explicit fast lane (`make verify-fast`) and deeper browser lane (`make verify-deep`), and mocked-online E2E flows use deterministic fake job IDs so browser failures point at the actual seam under test instead of background-thread shutdown noise. Fresh slice verification passed: `make verify-fast` (952 non-E2E backend tests, 78 Vitest tests, TypeScript, production build) and `make verify-deep` (113 E2E tests).

## Architecture / Key Patterns

- **Backend:** Python 3.10 + Flask 3.1, iocextract + iocsearcher for extraction, requests + dnspython for HTTP/DNS
- **Frontend:** TypeScript 5.8 + esbuild (IIFE output), Tailwind CSS standalone CLI, Inter Variable + JetBrains Mono Variable, dark-first zinc design tokens with verdict-only color accents
- **Enrichment:** 15 providers (12 HTTP via requests.Session, 2 DNS via dnspython, 1 WHOIS via python-whois), per-provider semaphore concurrency, 429-aware backoff, cursor polling, additive terminal status metadata
- **Persistence:** SQLite WAL-mode stores (CacheStore for enrichment cache, HistoryStore for analysis history) at ~/.sentinelx/
- **Results rendering:** `result-application.ts` is the shared stateful apply/flush/finalize coordinator; `enrichment.ts` keeps live-only polling/cursor/terminal/debounce behavior; `history.ts` keeps history JSON parsing and synchronous replay timing
- **Verification surface:** `make verify-fast` is the default routine proof lane, `make verify-deep` is the browser/live-results lane, and `make verify` composes both. Mocked-online E2E coverage stays deterministic by patching orchestration only inside the E2E live-server fixture and asserting rendered `data-results-owner` / `data-job-id` signals in shared helpers.
- **Security:** CSP (7 directives), CSRF, SSRF allowlist, host validation, textContent-only DOM (SEC-08)
- **Build:** Makefile targets — `css`, `js`, `js-dev`, `js-watch`, `typecheck`, `build`, `verify-fast`, `verify-deep`, `verify`
- **Routes:** `app/routes/` package with shared `main` Blueprint, separate `api` Blueprint (CSRF-exempt)

## Capability Contract

See `.gsd/REQUIREMENTS.md` for the explicit capability contract, requirement status, and coverage mapping.

## Milestone Sequence

- [x] M001: v1.1 Results Page Redesign — Uniform IOC card architecture, verdict badge prominence, micro-bar, category labels, three-section grouping, inline context line, cache staleness badge
- [x] M002: v1.2 Results Page Rework — Information-first redesign: single-column layout, quiet precision design, at-a-glance enrichment surface, inline expand/collapse, full integration + security audit, E2E suite 91→99 tests
- [x] M003: System Efficiency & Completeness — Per-provider concurrency, 429 backoff, email IOC extraction, detail page redesign, debounced summary rows
- [x] M004: Refactor & Optimize — Concurrency fixes, polling cursor, persistent Sessions, ipinfo.io HTTPS, CacheStore WAL, frontend O(N²) fixes, shared test helpers, CSP expansion
- [x] M005: Codebase Hygiene — safe_request() consolidation across 12 adapters, registry caching at startup, analyze() decomposition into 3 helpers. Net -134 LOC, 960 tests, 0 failures.
- [x] M006: Analyst Workflow & Coverage — Analysis history persistence, WHOIS domain enrichment (15th provider), URL IOC end-to-end polish, input page redesign. 1043 tests, 0 failures.
- [x] M007: Dead Code & Boilerplate Reduction — safe_request() consolidation across 12 adapters, adapter docstring trimming & dead CSS, test DRY-up with shared helpers. Net -418 LOC, 1057 tests, 0 failures.
- [x] M008: Routes Decomposition & REST API — routes.py decomposed into app/routes/ package, REST API blueprint added (POST /api/analyze, GET /api/status). 1075 tests, 0 failures.
- [x] M009: Codebase Reduction — BaseHTTPAdapter consolidation (12 adapters), parametrized contract tests (172 replacing 208), CSS audit (clean), frontend TS dedup (4 functions shared). Net -1,143 LOC, 947 tests, 0 failures.
- [x] M010: Cleanup & History Page — Route duplication cleanup (_setup_orchestrator, _get_enrichment_status shared helpers), dead import/export removal, Recent Analyses relocated from home page to dedicated /history page. 1061 tests, 0 failures.
- [x] M011: Lean & Fast — Adapter docstring trim (1,062 lines), per-adapter test consolidation (49 tests, -431 lines), dead CSS audit (207 classes verified), orchestrator test speedup (6.2s → 0.09s). Net -1,601 LOC, 1,012 tests, 0 failures.
- [ ] M012: Optimization Audit & Next-Work Decision — S01 complete: explicit terminal enrichment states surface through backend + analyst UI with preserved cursor polling and a stable verification surface. S02 complete: live polling and history replay now share one result-application path with exclusive owner dispatch and parity-backed proof. S03 complete: the repo now has an explicit fast/default verification lane plus a deterministic mocked-online browser lane that avoids launching real enrichment work.

---
*Last updated: 2026-04-22 — M012/S03 complete.*
