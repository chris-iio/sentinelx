# Project

## What This Is

SentinelX is a local, security-focused web application for analyst IOC triage. It lets an analyst paste investigation text or SSH/security artifacts, extract indicators of compromise, optionally enrich those indicators through threat-intelligence providers, and review prioritized results with history, detail pages, filtering, copy/export, and diagnostics.

## Core Value

The one thing that must work even if everything else is cut: an analyst can move from raw IOC-rich text to a clear, trustworthy, locally reviewable IOC triage result without losing context or hiding failures.

## Project Shape

- **Complexity:** complex
- **Why:** SentinelX crosses Flask request handling, provider orchestration, SQLite persistence, TypeScript browser rendering, security boundaries, and browser-heavy verification.

## Current State

The project already has a broad local triage workflow: intake workbench, offline/online extraction, multiple enrichment adapters, provider settings, result cards, expandable details, history reload, diagnostic export surfaces, a managed local dev-server path, and explicit verification lanes. Prior optimization milestones shipped per-provider runtime guardrails, cursor-based/incremental status behavior, persistent HTTP sessions, WAL-backed local stores, shared live/history result application, and frontend handle caching.

M017 reframes optimization around a fresh current-state project map. The project now also has `docs/project-map.md` as a durable guide to what SentinelX is, who it serves, its primary analyst loop, its runtime seams, and its optimization guardrails.

## Architecture / Key Patterns

- Flask routes under `app/routes` own intake, analysis, status, history, detail, settings, diagnostics, and API surfaces.
- `app.pipeline` extracts, normalizes, and classifies IOCs.
- `app.enrichment` owns provider registry setup, provider adapter contracts, orchestration, retry/backoff, rate limits, cache hits, and diagnostics.
- SQLite-backed `CacheStore` and `HistoryStore` preserve local enrichment and analysis state with WAL-mode persistence.
- TypeScript modules under `app/static/src/ts/modules` own browser polling, result application, filtering, sorting, row expansion, copy/export, and DOM-safe rendering.
- `tools/optimization_audit.py` and `docs/optimization-audit.md` define the evidence-backed optimization workflow: measurement when practical, explicit code-path reasoning when measurement is impractical, ranked do-now/do-next/later/leave-alone outcomes, and verification lane mapping.
- `make verify-fast` is the default non-E2E proof lane; `make verify-deep` is the browser-heavy mocked-online lane; `make verify` runs both.

## Capability Contract

See `.gsd/REQUIREMENTS.md` for the explicit capability contract, requirement status, and coverage mapping.

## Milestone Sequence

- [x] M012: Optimization Audit & Next-Work Decision — Established evidence-backed optimization discipline and live enrichment/status proof.
- [x] M013: SentinelX optimization-audit workflow and shipped full-stack pass — Shipped the reusable audit runner plus targeted request/status and frontend/render optimizations.
- [x] M014: Local workflow hardening and recovery loop — Hardened repo-local runtime workflow and recovery behavior.
- [x] M015: Intake Workbench — Refined the home/intake experience while preserving extraction flow.
- [x] M016: Email Reputation Depth — Added key-gated EmailRep enrichment for email IOCs with deterministic proof.
- [ ] M017: Project Clarity & Aggressive Optimization — Define what SentinelX is now, then aggressively ship the best project-grounded optimization with full proof.
