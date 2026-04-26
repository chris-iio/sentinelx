# SentinelX

## What This Is

A universal threat intelligence hub for SOC analysts. Paste free-form text (alerts, email headers, threat reports, raw IOCs) and the app extracts, normalizes, classifies, and enriches IOCs against 15 providers in parallel — presenting unified summary verdicts with expandable per-provider detail rows, bookmarkable per-IOC detail pages with relationship graphs, and analyst annotations (notes + tags). Analyses are persisted to SQLite and reloadable from the browser. No opaque combined scores.

## Core Value

Safe, correct, and transparent IOC extraction and enrichment — never invent scores, never make network calls the analyst didn't ask for, never trust input or API responses. For M015 specifically, the front door should support a fast analyst motion: paste → choose mode → Extract.

## Current State

**M015 is planned as the active next milestone: Intake Workbench.** All prior milestones through M014 are complete. The product-facing SentinelX stack is stable: extraction/enrichment, result rendering, detail pages, history reload, REST API, optimization-audit workflow, fast/deep verification lanes, and local workflow recovery are in place and verified.

M014 closed the local workflow hardening pass around the repo/operator seam. SentinelX now has `tools/runtime_state_boundary.py` as the authoritative durable/transient/manual-review classifier, `tools/runtime_state_repair.py` plus `make repair-runtime-state` as the supported repair entrypoint, and `tools/dev_server.py` plus `make dev-server-start|status|restart|stop` as the supported local dev-server lifecycle. The `/api/health` contract is single-sourced in `app/health_contract.py`, and final M014 proof passed the focused seam suite, repair/boundary commands, live crash/restart proof, and full `make verify`.

The remaining product-facing gap is the first screen. The results/detail/history surfaces have become mature, but `/` is still a thin paste form: brand, textarea, Offline/Online toggle, Clear, Extract, and paste feedback. M015 redesigns that front door into a fast analyst **Intake Workbench** without changing extraction/enrichment semantics. The user explicitly chose **go fast**, no pre-submit extraction preview, and a **compact list** of Recent Analyses on the intake page.

## Architecture / Key Patterns

- **Backend:** Python 3.10 + Flask 3.1, iocextract + iocsearcher for extraction, requests + dnspython for HTTP/DNS
- **Frontend:** TypeScript 5.8 + esbuild (IIFE output), Tailwind CSS standalone CLI, Inter Variable + JetBrains Mono Variable, dark-first zinc design tokens with verdict-only color accents
- **Enrichment:** 15 providers (12 HTTP via requests.Session, 2 DNS via dnspython, 1 WHOIS via python-whois), per-provider semaphore concurrency, 429-aware backoff, cursor polling, additive terminal status metadata
- **Status path split:** `EnrichmentOrchestrator.get_status()` remains the mutation-safe full snapshot for history/full-state callers; `get_incremental_status()` is the live polling hot path that returns scalar fields, the requested result tail, aligned cached markers, and `next_since`
- **Persistence:** SQLite WAL-mode stores (CacheStore for enrichment cache, HistoryStore for analysis history) at `~/.sentinelx/`; WAL and `busy_timeout` remain explicitly re-proved keep-decisions rather than assumed behavior
- **History:** `HistoryStore.list_recent(limit)` returns lightweight summaries; `/history` renders the full recent list; `/history/<id>` reloads a past analysis without re-querying providers
- **Intake form:** `app/templates/index.html` posts to `main.analyze` with CSRF, `#ioc-text`, hidden `#mode-input`, `#mode-toggle-widget`, `#mode-toggle-btn`, `#clear-btn`, and `#submit-btn`; `app/static/src/ts/modules/form.ts` owns submit enablement, auto-grow, paste feedback, and mode toggle behavior
- **Results rendering:** `result-application.ts` is the shared stateful apply/flush/finalize coordinator; it caches stable per-IOC DOM handles and one-time provider-count metadata for both live polling and history replay while keeping dynamic summary/detail rows lazy and text-only
- **Verification surface:** `make verify-fast` is the default routine proof lane, `make verify-deep` is the mocked-online browser/live-results lane, and `make verify` composes both
- **Security:** CSP, CSRF, SSRF allowlist, localhost host validation, textContent-only DOM construction
- **Runtime-boundary seam:** `tools/runtime_state_boundary.py` is the authoritative classifier/audit seam for durable vs transient repo-local workflow state, and `tools/runtime_state_repair.py` is the only supported mutating companion
- **Local dev-server contract:** `tools/dev_server.py` is the single lifecycle implementation, `/api/health` is the exact secret-free readiness probe, status derives from live probe truth rather than PID files alone, and manager-owned runtime metadata remains under `.gsd/runtime/dev-server/**`
- **Closeout discipline:** milestone/slice validation artifacts must be written through the DB-backed GSD toolchain so the ledger, projections, and disk artifacts stay aligned

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
- [x] M013: SentinelX optimization-audit workflow and shipped full-stack pass — S01 established the reusable audit runner and ranked baseline, S02 closed the runtime/provider seam with measured keep-decisions, S03 shipped the request/status cursor hot-path improvement and re-proved WAL persistence as a keep-decision, and S04 shipped coordinator-local frontend/render caching plus the final audit rerun with embedded `verify-fast` / `verify-deep` proof.
- [x] M014: Local workflow hardening and recovery loop — S01 established the explicit runtime-state boundary, S02 shipped the supported classifier-backed repair entrypoint, S03 shipped the supported local dev-server lifecycle with crash recovery, and S04 closed the milestone with the explicit seam review, shared health-contract single-sourcing, and fresh final-assembly proof.
- [ ] M015: Intake Workbench — Redesign the home/input page into a fast analyst command surface with clarified mode choice, compact Recent Analyses, graceful history degradation, and final browser/full-repo proof.

---
*Last updated: 2026-04-26 — M015 planned as the next active milestone.*
