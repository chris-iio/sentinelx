# SentinelX

## What This Is

A universal threat intelligence hub for SOC analysts. Paste free-form text (alerts, email headers, threat reports, raw IOCs) and the app extracts, normalizes, classifies, and enriches IOCs against 15 providers in parallel — presenting unified summary verdicts with expandable per-provider detail rows, bookmarkable per-IOC detail pages with relationship graphs, and analyst annotations (notes + tags). Analyses are persisted to SQLite and reloadable from the home page. No opaque combined scores.

## Core Value

Safe, correct, and transparent IOC extraction and enrichment — never invent scores, never make network calls the analyst didn't ask for, never trust input or API responses.

## Current State

**M013 is complete and M014 is active (S01-S02 complete).** The product-facing SentinelX stack remains stable: the repo still has the checked-in optimization-audit workflow from M013, explicit evidence-backed keep-decisions for the runtime/provider and WAL persistence seams, a shipped request/status hot-path improvement, and a shipped frontend/render coordinator optimization backed by fresh final-state `verify-fast` and `verify-deep` proof.

M014 is a local workflow hardening pass aimed at the repo/operator seam rather than an analyst-facing feature. S01 established the authoritative runtime-state boundary: `tools/runtime_state_boundary.py` classifies durable `.gsd` artifacts, transient `.gsd`/`.bg-shell` runtime state, and fail-closed legacy `.planning/**` paths; `.gitignore` and the repo-native verifier were aligned to that contract; and temp-repo Git regression fixtures prove the stash/pop blocker class is either prevented or surfaced explicitly. S02 is now complete and adds the supported recovery loop: `tools/runtime_state_repair.py` is the only mutating repair CLI, `make repair-runtime-state` is the one supported repo-native recovery entrypoint, `tracked-transient` findings are deindexed, `unignored-transient` findings are quarantined under `.gsd/runtime/repair-quarantine/<timestamp>/...`, and live-repo repair/audit runs stay green while `.planning/**` remains visible manual-review backlog instead of being auto-cleaned. The remaining slices still need to standardize the supported local dev-process loop (S03) and close with final review/refactor plus full assembled verification (S04).

`tools/optimization_audit.py`, `Makefile`, `README.md`, and `docs/optimization-audit.md` remain the command surface and proof vocabulary for performance-related work. M014 hardens the local developer/operator loop around them so repo-local state and crashed local processes are easier to classify, repair, and restart without risking milestone/context artifacts.

## Architecture / Key Patterns

- **Backend:** Python 3.10 + Flask 3.1, iocextract + iocsearcher for extraction, requests + dnspython for HTTP/DNS
- **Frontend:** TypeScript 5.8 + esbuild (IIFE output), Tailwind CSS standalone CLI, Inter Variable + JetBrains Mono Variable, dark-first zinc design tokens with verdict-only color accents
- **Enrichment:** 15 providers (12 HTTP via requests.Session, 2 DNS via dnspython, 1 WHOIS via python-whois), per-provider semaphore concurrency, 429-aware backoff, cursor polling, additive terminal status metadata
- **Status path split:** `EnrichmentOrchestrator.get_status()` remains the mutation-safe full snapshot for history/full-state callers; `get_incremental_status()` is the live polling hot path that returns scalar fields, the requested result tail, aligned cached markers, and `next_since`
- **Persistence:** SQLite WAL-mode stores (CacheStore for enrichment cache, HistoryStore for analysis history) at `~/.sentinelx/`; WAL and `busy_timeout` remain explicitly re-proved keep-decisions rather than assumed behavior
- **Results rendering:** `result-application.ts` is the shared stateful apply/flush/finalize coordinator; it caches stable per-IOC DOM handles and one-time provider-count metadata for both live polling and history replay while keeping dynamic summary/detail rows lazy and text-only
- **Verification surface:** `make verify-fast` is the default routine proof lane, `make verify-deep` is the mocked-online browser/live-results lane, and `make verify` composes both
- **Optimization audit:** `tools/optimization_audit.py` is the canonical audit runner; Make targets stay thin; each finding fits one ranked bucket and cites measurement or code-path reasoning
- **Helper observability:** `app/routes/_helpers.py` owns bounded history-save diagnostics; `/settings` is the aggregate inspection surface for helper persistence health; terminal tombstones stay helper-owned even though live polling reads incremental orchestrator snapshots
- **Security:** CSP (7 directives), CSRF, SSRF allowlist, host validation, textContent-only DOM (SEC-08)
- **Build/dev entrypoints:** Makefile targets include `css`, `js`, `js-dev`, `js-watch`, `typecheck`, `build`, `repair-runtime-state`, `verify-runtime-boundary`, `verify-fast`, `verify-deep`, `verify`, `audit-m013-template`, and `audit-m013`
- **Runtime-boundary seam:** `tools/runtime_state_boundary.py` is the authoritative classifier/audit seam for durable vs transient repo-local workflow state, and `tools/runtime_state_repair.py` is the only supported mutating companion. `make verify-runtime-boundary` proves the classifier and blocker classes, while `make repair-runtime-state` performs supported deindex/quarantine repair and then re-runs the inspection-only audit.
- **Repair safety contract:** `.planning/**` remains `manual-review-path` and never auto-mutates; only `tracked-transient` and `unignored-transient` findings are actionable; quarantine destinations must already be ignored and preserve original path context under `.gsd/runtime/repair-quarantine/<timestamp>/...`
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
- [x] M013: SentinelX optimization-audit workflow and shipped full-stack pass — S01 established the reusable audit runner and ranked baseline, S02 closed the runtime/provider seam with measured keep-decisions, S03 shipped the request/status cursor hot-path improvement and re-proved WAL persistence as a keep-decision, and S04 shipped coordinator-local frontend/render caching plus the final audit rerun with embedded `verify-fast` / `verify-deep` proof.
- [ ] M014: Local workflow hardening and recovery loop — S01-S02 complete: the runtime boundary is explicit and verified, and the repo now has a supported repair entrypoint with safe deindex/quarantine behavior; S03-S04 remain to add the supported local dev loop and final closure.

---
*Last updated: 2026-04-25 — M014 active with S01-S02 complete; runtime-state repair is shipped and verified, with dev-loop and final closure work remaining.*
