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

## Architecture Seams

- **HTTP and page surfaces** — `app/routes/analysis.py`, `app/routes/api.py`, `app/routes/enrichment.py`: accept analyst input, expose programmatic analysis, and serve enrichment status polling.
- **History/detail/settings/diagnostics surfaces** — `app/routes/history.py`, `app/routes/detail.py`, `app/routes/settings.py`, `app/routes/diagnostics.py`: support replay, drill-down, provider keys/cache controls, and analyst support bundles.
- **IOC extraction pipeline** — `app/pipeline/extractor.py`, `app/pipeline/normalizer.py`, `app/pipeline/classifier.py`: turn raw pasted text into canonical typed IOC models.
- **Provider registration seam** — `app/enrichment/setup.py`, `app/enrichment/registry.py`: import/register the 16 enrichment providers and expose configured/provider-for-type lookups.
- **Enrichment fan-out and status seam** — `app/enrichment/orchestrator.py`: runs provider lookups with `ThreadPoolExecutor`, per-provider semaphores, cache checks, retry/backoff, progress snapshots, and terminal job state.
- **Local cache seam** — `app/cache/store.py`: stores enrichment results in SQLite with TTL lookup, provider-specific rows, stats, clear, and expiry purge operations.
- **Browser polling and result application seam** — `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/modules/result-application.ts`, `app/static/src/ts/modules/row-factory.ts`: poll online jobs, compute/render verdict-first rows, and keep live/history DOM behavior aligned.
- **Browser utility surfaces** — `app/static/src/ts/modules/filter.ts`, `app/static/src/ts/modules/export.ts`, `app/static/src/ts/modules/history.ts`, `app/static/src/ts/modules/settings.ts`: provide analyst filtering, export/copy/history/settings interactions after results exist.
- **Optimization proof loop** — `tools/optimization_audit.py`, `Makefile`: collect seam notes, runtime/provider diagnostics, cache/history probes, ranked findings, and supported verification lanes.

## Ranked Optimization Priorities

1. **Enrichment fan-out/status snapshot cost** — Seam: enrichment fan-out and status. Files: `app/enrichment/orchestrator.py`, `tools/optimization_audit.py`. Opportunity type: redundant status aggregation or lock-protected work during large IOC/provider fan-out. Proof needed: audit/runtime capture showing snapshot or fan-out scaling before/after, plus online enrichment regression proof.
2. **Browser result rendering churn** — Seam: browser polling and result application. Files: `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/modules/result-application.ts`, `app/static/src/ts/modules/row-factory.ts`. Opportunity type: unnecessary DOM rebuilds, recounts, sorting, or repeated per-row computations during polling/history replay. Proof needed: browser-visible parity plus a targeted fixture or timing/count comparison demonstrating less work without hiding failures.
3. **SQLite cache/history access shape** — Seam: local cache and persistence. Files: `app/cache/store.py`, route callers under `app/routes/`, audit probes in `tools/optimization_audit.py`. Opportunity type: repeated SQLite reads/writes, TTL purges, or missing indexed access on analyst reload/enrichment paths. Proof needed: tempdb/cache audit measurement or query-count reasoning, with continuity proof for cache hit, expiry, clear, and history reload behavior.
4. **IOC pipeline duplicate candidate handling** — Seam: IOC extraction pipeline. Files: `app/pipeline/extractor.py`, `app/pipeline/normalizer.py`, `app/pipeline/classifier.py`. Opportunity type: redundant normalization/classification for duplicate raw matches in pasted reports. Proof needed: representative text fixture showing same IOC output with fewer normalization/classification passes or lower elapsed time.
5. **Provider registration/config diagnostics clarity** — Seam: provider registration. Files: `app/enrichment/setup.py`, `app/enrichment/registry.py`, `app/routes/settings.py`. Opportunity type: repeated configured-provider filtering or unclear provider readiness diagnostics. Proof needed: provider-count/configured-provider tests plus diagnostics/settings behavior that preserves secret-redaction boundaries.

## Current Optimization Posture

M012 and M013 established a measurement-or-reasoning proof bar and shipped targeted polling/status and frontend handle-cache improvements. M017 should not blindly repeat those decisions. It should refresh the current-state understanding, update the audit for M017, and aggressively ship the best optimization that serves SentinelX's real identity.

## Non-Negotiable Guardrails

- Do not hide failures to make the app feel faster.
- Do not leak secrets in diagnostics, logs, browser output, or artifacts.
- Preserve IOC intake, enrichment polling, filtering, sorting, copy/export, history reload, detail links, provider settings, and security boundaries unless a slice explicitly improves them.
- Browser-visible behavior changes require browser proof.
- Every shipped optimization needs measurement when practical or explicit code-path reasoning plus regression proof.
