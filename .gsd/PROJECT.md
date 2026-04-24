# SentinelX

## What This Is

A universal threat intelligence hub for SOC analysts. Paste free-form text (alerts, email headers, threat reports, raw IOCs) and the app extracts, normalizes, classifies, and enriches IOCs against 15 providers in parallel — presenting unified summary verdicts with expandable per-provider detail rows, bookmarkable per-IOC detail pages with relationship graphs, and analyst annotations (notes + tags). Analyses are persisted to SQLite and reloadable from the home page. No opaque combined scores.

## Core Value

Safe, correct, and transparent IOC extraction and enrichment — never invent scores, never make network calls the analyst didn't ask for, never trust input or API responses.

## Current State

**M013 active; S01 complete (2026-04-24).** SentinelX now has a checked-in optimization-audit workflow that can be rerun locally and emits a durable ranked artifact instead of ad hoc tuning notes.

`tools/optimization_audit.py`, `Makefile`, `README.md`, and `docs/optimization-audit.md` now define the command surface for M013. The workflow supports template and baseline modes, keeps Make targets as thin wrappers around the Python runner, and enforces the audit contract that every finding must use measurement when practical or explicit code-path reasoning otherwise.

The milestone-local artifact `.gsd/milestones/M013/M013-AUDIT.md` is now the shared baseline for later optimization slices. It records four fixed ranked buckets (`do now`, `do next`, `later`, `leave alone`), lightweight measurement captures, per-seam notes across runtime/provider, request/status, persistence, and frontend/render, and explicit continuity guardrails for R008, R009, R010, R014, R015, R018, R019, R020, R022, and R040.

The current baseline ranking is explicit. The first ship target is the request/status cursor path because `/enrichment/status` still pays a full results snapshot before `since` slicing. The next likely optimization is caching card/slot handles in the shared frontend result-application coordinator. WAL-backed cache/history persistence and provider backoff/session behavior remain deliberate keep-decisions until later slices produce stronger evidence.

The verification contract is now durable instead of tribal knowledge. The audit artifact carries a verified rerun checklist that tells downstream slices when to rerun `make verify-fast`, when deterministic mocked-online `make verify-deep` is mandatory, and when the refreshed audit artifact itself must be updated before handoff. Fresh slice-close verification re-ran the workflow, `make verify-fast`, and `make verify-deep`, and the regenerated artifact records those passing captures.

## Architecture / Key Patterns

- **Backend:** Python 3.10 + Flask 3.1, iocextract + iocsearcher for extraction, requests + dnspython for HTTP/DNS
- **Frontend:** TypeScript 5.8 + esbuild (IIFE output), Tailwind CSS standalone CLI, Inter Variable + JetBrains Mono Variable, dark-first zinc design tokens with verdict-only color accents
- **Enrichment:** 15 providers (12 HTTP via requests.Session, 2 DNS via dnspython, 1 WHOIS via python-whois), per-provider semaphore concurrency, 429-aware backoff, cursor polling, additive terminal status metadata
- **Persistence:** SQLite WAL-mode stores (CacheStore for enrichment cache, HistoryStore for analysis history) at ~/.sentinelx/
- **Results rendering:** `result-application.ts` is the shared stateful apply/flush/finalize coordinator; `enrichment.ts` keeps live-only polling/cursor/terminal/debounce behavior; `history.ts` keeps history JSON parsing and synchronous replay timing
- **Optimization audit:** `tools/optimization_audit.py` is the canonical audit runner; Make targets stay thin; each finding must fit one ranked bucket and cite measurement or code-path reasoning
- **Verification surface:** `make verify-fast` is the default routine proof lane, `make verify-deep` is the browser/live-results lane, and `make verify` composes both. M013 adds a verified rerun checklist directly inside the audit artifact so later slices refresh proof instead of reconstructing it from memory.
- **Helper observability:** `app/routes/_helpers.py` owns bounded history-save diagnostics; `/settings` is the aggregate inspection surface for helper persistence health
- **Security:** CSP (7 directives), CSRF, SSRF allowlist, host validation, textContent-only DOM (SEC-08)
- **Build:** Makefile targets — `css`, `js`, `js-dev`, `js-watch`, `typecheck`, `build`, `verify-fast`, `verify-deep`, `verify`, `audit-m013-template`, `audit-m013`
- **Routes:** `app/routes/` package with shared `main` Blueprint, separate `api` Blueprint (CSRF-exempt)
- **Closeout discipline:** milestone/slice validation artifacts must be written through the DB-backed GSD toolchain (`gsd_summary_save`, `gsd_validate_milestone`, `gsd_complete_slice`, `gsd_complete_milestone`) so the ledger, projections, and disk artifacts stay aligned

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
- [x] M012: Optimization Audit & Next-Work Decision — Hardened live terminal status semantics, unified live/history result application, formalized fast/deep verification lanes with deterministic mocked-online browser proof, added bounded `/settings` history-save diagnostics, and closed with a validated keep/change decision preserving WAL-backed persistence and cursor/history continuity until future measurement proves otherwise.
- [ ] M013: SentinelX optimization-audit workflow and shipped full-stack pass — S01 completed the reusable audit runner, ranked baseline artifact, and downstream verification/rerun contract; later slices will use that artifact to justify shipped runtime, persistence, and frontend fixes.

---
*Last updated: 2026-04-24 — M013/S01 complete; reusable optimization-audit workflow and baseline ranking established.*
