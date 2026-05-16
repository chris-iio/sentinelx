# Project

## What This Is

SentinelX is a local, security-focused web application for analyst IOC triage. Its core loop is: paste investigation text or SSH/security artifacts, extract indicators of compromise, optionally enrich those indicators through threat-intelligence providers, and review analyst-friendly results with history, detail pages, filtering, copy/export, and diagnostics.

## Core Value

SentinelX must remain a fast local analyst workbench that turns raw security text into prioritized IOC understanding without hiding failures or leaking secrets.

## Project Shape

- **Complexity:** complex
- **Why:** The project spans Flask routes, Python extraction/enrichment/cache/history subsystems, TypeScript browser behavior, templates, diagnostics, security boundaries, and established fast/deep verification lanes.

## Current State

Milestones are complete through M020. M020 broadened the optimization audit, generated `.gsd/milestones/M020/M020-AUDIT.md` from `tools/optimization_audit.py`, shipped or preserved high-confidence refactor outcomes with strict proof, explicitly deferred risky broad rewrites, and reran final `make verify` successfully. `docs/project-map.md` remains the current product and seam inventory, and `tools/optimization_audit.py` plus Makefile audit/verification targets form the optimization proof loop.

## Architecture / Key Patterns

- Flask routes own request handling, intake/results/history/detail/settings/diagnostics surfaces, and enrichment status endpoints.
- `app.routes._helpers` owns shared route IOC grouping/template/API payload helpers while route modules preserve compatibility seams and route-specific response behavior.
- `app.pipeline` extracts, normalizes, and classifies IOCs.
- `app.enrichment` owns provider registry, adapter contracts, orchestration, rate limits, retry/backoff, cache hits, and diagnostics.
- SQLite-backed cache and history stores preserve enrichment responses and prior analyses locally; major storage redesign remains deferred until measurements justify it.
- Diagnostics sanitization caps are centralized in `app/diagnostics/policy.py` and consumed by assembler, source, and redaction modules.
- TypeScript modules own browser-side polling, result application, filtering, sorting, expansion, copy/export, and DOM-safe rendering; large-result virtualization remains deferred behind measured severity-change-gate proof.
- Make targets provide supported verification lanes: `make audit-m020`, `make verify-fast`, `make verify-deep`, and `make verify`.
- Optimization work follows an audit-led proof bar: measurement when practical, explicit code-path reasoning when measurement is awkward, generated audit documentation, and regression proof before completion claims.

## Capability Contract

See `.gsd/REQUIREMENTS.md` for the explicit capability contract, requirement status, and coverage mapping.

## Milestone Sequence

- [x] M017: Project Clarity & Aggressive Optimization — refreshed project identity, generated audit proof, and shipped focused optimization wins.
- [x] M020: Audit-Led Aggressive Refactor and Deep Optimization — generated the M020 audit, ranked aggressive rewrite candidates, shipped/preserved route and diagnostics centralization outcomes, deferred frontend virtualization and broad scope expansions with evidence, and preserved the analyst IOC triage loop with final `make verify` proof.
