# Project

## What This Is

SentinelX is a local, security-focused web application for analyst IOC triage. Its core loop is: paste investigation text or SSH/security artifacts, extract indicators of compromise, optionally enrich those indicators through threat-intelligence providers, and review analyst-friendly results with history, detail pages, filtering, copy/export, and diagnostics.

## Core Value

SentinelX must remain a fast local analyst workbench that turns raw security text into prioritized IOC understanding without hiding failures or leaking secrets.

## Project Shape

- **Complexity:** complex
- **Why:** The project spans Flask routes, Python extraction/enrichment/cache/history subsystems, TypeScript browser behavior, templates, diagnostics, security boundaries, and established fast/deep verification lanes.

## Current State

Prior milestones have delivered the analyst results workflow, enrichment depth, diagnostic export surfaces, project clarity artifacts, and multiple evidence-backed optimization passes. `.gsd/STATE.md` reports all prior milestones complete through M017. `docs/project-map.md` is the current product and seam inventory, and `tools/optimization_audit.py` plus Makefile audit/verification targets form the existing optimization proof loop.

## Architecture / Key Patterns

- Flask routes own request handling, intake/results/history/detail/settings/diagnostics surfaces, and enrichment status endpoints.
- `app.pipeline` extracts, normalizes, and classifies IOCs.
- `app.enrichment` owns provider registry, adapter contracts, orchestration, rate limits, retry/backoff, cache hits, and diagnostics.
- SQLite-backed cache and history stores preserve enrichment responses and prior analyses locally.
- TypeScript modules own browser-side polling, result application, filtering, sorting, expansion, copy/export, and DOM-safe rendering.
- Make targets provide supported verification lanes: `make verify-fast`, `make verify-deep`, and `make verify`.
- Optimization work follows an audit-led proof bar: measurement when practical, explicit code-path reasoning when measurement is awkward, and regression proof before completion claims.

## Capability Contract

See `.gsd/REQUIREMENTS.md` for the explicit capability contract, requirement status, and coverage mapping.

## Milestone Sequence

- [x] M017: Project Clarity & Aggressive Optimization — refreshed project identity, generated audit proof, and shipped focused optimization wins.
- [ ] M020: Audit-Led Aggressive Refactor and Deep Optimization — broaden the audit, rank rewrite targets, ship or reject the highest-confidence aggressive optimizations with strict proof, and preserve the analyst IOC triage loop.
