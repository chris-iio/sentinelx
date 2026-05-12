# SentinelX Project Map

## What SentinelX Is Now

SentinelX is a local, security-focused web application for analyst IOC triage. Its core loop is: paste investigation text or SSH/security artifacts, extract indicators of compromise, optionally enrich those indicators through threat-intelligence providers, and review analyst-friendly results with history, detail pages, filtering, copy/export, and diagnostics.

The project should feel like a fast local workbench, not a heavy enterprise dashboard. The important product surface is the analyst's path from raw text to prioritized IOC understanding.

## Who It Serves

- SOC analysts and security investigators who need fast local triage of pasted reports, headers, logs, or command output.
- Maintainers and future agents who need clear code boundaries, reliable verification lanes, and enough diagnostics to debug provider, polling, rendering, and persistence failures.

## Primary Analyst Loop

1. Open the local web UI.
2. Paste IOC-rich text into the intake workbench.
3. Choose Offline or Online mode.
4. Extract IOCs and land on the results page.
5. Scan verdict-first cards with compact context.
6. Expand rows for provider details or use detail/history pages for deeper review.
7. Export, copy, filter, or revisit prior analyses without re-querying providers unnecessarily.

## Core Runtime Shape

- Flask routes own request handling, intake/results/history/detail/settings/diagnostics surfaces, and status endpoints.
- `app.pipeline` extracts, normalizes, and classifies IOCs.
- `app.enrichment` owns provider registry, adapter contracts, orchestration, rate limits, retry/backoff, cache hits, and diagnostics.
- SQLite-backed cache and history stores preserve enrichment responses and prior analyses locally.
- TypeScript modules own browser-side polling, result application, filtering, sorting, expansion, copy/export, and DOM-safe rendering.
- Make targets provide the supported verification lanes and local server workflow.

## Optimization Seams

### Product clarity

The project identity itself is an optimization seam. Future agents should not need to reverse-engineer what SentinelX is before deciding what matters.

### Intake and results flow

The highest-value user-facing optimization work should preserve and improve the analyst path through intake, enrichment, results scanning, expansion, filtering, and history/detail review.

### Runtime/provider orchestration

Provider fan-out, per-provider caps, cache interaction, retry/backoff, status snapshots, and diagnostics affect perceived speed and correctness. Changes here need strong continuity proof.

### Request/status and persistence

Status endpoints, terminal tombstones, history-save diagnostics, and SQLite WAL stores are central but should only be changed when evidence shows a hot path or meaningful simplification.

### Frontend rendering

Result application, dashboard recounting, card sorting, summary-row rebuilds, section injection, and live/history parity are the most likely browser-side optimization targets.

### Audit and proof loop

`tools/optimization_audit.py`, `make verify-fast`, and `make verify-deep` are part of the optimization system. The audit artifact should explain what changed, what stayed alone, and why.

## Current Optimization Posture

M012 and M013 established a measurement-or-reasoning proof bar and shipped targeted polling/status and frontend handle-cache improvements. M017 should not blindly repeat those decisions. It should refresh the current-state understanding, update the audit for M017, and aggressively ship the best optimization that serves SentinelX's real identity.

## Non-Negotiable Guardrails

- Do not hide failures to make the app feel faster.
- Do not leak secrets in diagnostics, logs, browser output, or artifacts.
- Preserve IOC intake, enrichment polling, filtering, sorting, copy/export, history reload, detail links, provider settings, and security boundaries unless a slice explicitly improves them.
- Browser-visible behavior changes require browser proof.
- Every shipped optimization needs measurement when practical or explicit code-path reasoning plus regression proof.
