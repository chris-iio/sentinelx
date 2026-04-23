# SentinelX

## What This Is

A universal threat intelligence hub for SOC analysts. Paste free-form text (alerts, email headers, threat reports, raw IOCs) and the app extracts, normalizes, classifies, and enriches IOCs against 15 providers in parallel — presenting unified summary verdicts with expandable per-provider detail rows, bookmarkable per-IOC detail pages with relationship graphs, and analyst annotations (notes + tags). Analyses are persisted to SQLite and reloadable from the home page. No opaque combined scores.

## Core Value

Safe, correct, and transparent IOC extraction and enrichment — never invent scores, never make network calls the analyst didn't ask for, never trust input or API responses.

## Current State

**M012 complete (2026-04-23).** The optimization-audit milestone shipped four concrete product/runtime improvements and closed with a ranked next-work decision backed by fresh verification instead of speculative cleanup.

The live enrichment status seam is now truthful end to end. `app/routes/_helpers.py` and `app/enrichment/orchestrator.py` expose additive terminal metadata for unknown, evicted, and failed jobs while preserving the existing success-path contract (`results`, `complete`, `next_since`, progress fields). `app/static/src/ts/modules/enrichment.ts` now parses terminal JSON payloads before branching on `resp.ok`, stops polling on terminal states, and surfaces analyst-visible failure messaging without regressing incremental success-path rendering.

The results surface now has one shared live/history application seam. `app/static/src/ts/modules/result-application.ts` owns shared stateful apply/flush/finalize behavior, while `enrichment.ts` retains live-only polling/cursor/terminal/debounce concerns and `history.ts` retains stored-history replay timing. `.page-results[data-results-owner]` is now the authoritative dispatch contract in `app/static/src/ts/main.ts`, preventing live/history double initialization and protecting parity for enrichment cards, detail rows, progress, export readiness, copy-button summaries, and detail links.

The verification floor is now explicit and trusted for future optimization work. `Makefile` and `README.md` define `make verify-fast` as the routine proof lane (non-E2E pytest, Vitest, TypeScript, production build), `make verify-deep` as the browser-sensitive escalation lane, and `make verify` as the composite command. `tests/e2e/conftest.py` keeps mocked-online browser flows deterministic by patching orchestration only inside the E2E fixture and asserting rendered `data-results-owner` / `data-job-id` seams in shared helpers.

The persistence/helper follow-through closed with a low-regret keep decision instead of a rewrite. `/settings` now exposes bounded History Save Diagnostics sourced from helper-local aggregate bookkeeping in `app/routes/_helpers.py`, `app/routes/settings.py`, and `app/templates/settings.html`. M012’s ranked assessment concluded that the WAL-backed persistent-connection design in `app/cache/store.py` and `app/enrichment/history_store.py`, the full-results history replay path, and `_get_enrichment_status()` cursor semantics should remain in place unless future diagnostics or measurement show real contention or write-path pain.

Fresh milestone-closeout verification passed in the completion turn: `python3 -m pytest tests/test_orchestrator.py tests/test_api.py tests/test_routes.py tests/test_http_safety.py tests/test_adapter_contract.py -q` (`266 passed in 0.96s`), `python3 -m pytest tests/test_cache_store.py tests/test_history_store.py tests/test_history_routes.py tests/test_settings.py -q` (`73 passed in 1.75s`), and `make verify-fast` (`955 passed, 113 deselected`, Vitest `78 passed`, clean `npx tsc --noEmit`, successful production build with only the pre-existing non-blocking Browserslist warning). `R040` is now present and validated in the canonical requirements ledger, so M012 validation passed and the milestone is formally complete.

## Architecture / Key Patterns

- **Backend:** Python 3.10 + Flask 3.1, iocextract + iocsearcher for extraction, requests + dnspython for HTTP/DNS
- **Frontend:** TypeScript 5.8 + esbuild (IIFE output), Tailwind CSS standalone CLI, Inter Variable + JetBrains Mono Variable, dark-first zinc design tokens with verdict-only color accents
- **Enrichment:** 15 providers (12 HTTP via requests.Session, 2 DNS via dnspython, 1 WHOIS via python-whois), per-provider semaphore concurrency, 429-aware backoff, cursor polling, additive terminal status metadata
- **Persistence:** SQLite WAL-mode stores (CacheStore for enrichment cache, HistoryStore for analysis history) at ~/.sentinelx/
- **Results rendering:** `result-application.ts` is the shared stateful apply/flush/finalize coordinator; `enrichment.ts` keeps live-only polling/cursor/terminal/debounce behavior; `history.ts` keeps history JSON parsing and synchronous replay timing
- **Helper observability:** `app/routes/_helpers.py` owns bounded history-save diagnostics; `/settings` is the aggregate inspection surface for helper persistence health
- **Verification surface:** `make verify-fast` is the default routine proof lane, `make verify-deep` is the browser/live-results lane, and `make verify` composes both. Mocked-online E2E coverage stays deterministic by patching orchestration only inside the E2E live-server fixture and asserting rendered `data-results-owner` / `data-job-id` signals in shared helpers.
- **Security:** CSP (7 directives), CSRF, SSRF allowlist, host validation, textContent-only DOM (SEC-08)
- **Build:** Makefile targets — `css`, `js`, `js-dev`, `js-watch`, `typecheck`, `build`, `verify-fast`, `verify-deep`, `verify`
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

---
*Last updated: 2026-04-23 — M012 complete and validated.*
