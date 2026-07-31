# SentinelX Project Map

## What SentinelX Is Now

SentinelX is a local, security-focused web application for analyst IOC triage. Its core loop is: paste investigation text or SSH/security artifacts, extract indicators of compromise, optionally enrich those indicators through threat-intelligence providers, and review analyst-friendly results with history, detail pages, filtering, copy/export, and diagnostics.

SentinelX also ships a CTF workspace (`/ctf`) for events such as HackTheBox Cyber Apocalypse: analysts track events, challenges (web/crypto/pwn/rev/forensics/osint/misc/hardware/blockchain/ml), per-challenge notes, and a flag vault that auto-captures `PREFIX{...}` tokens from pasted notes. Submitting a flag marks the challenge solved.

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

- **HTTP entry surfaces** — `app/routes/analysis.py`, `app/routes/api.py`, `app/routes/enrichment.py`: keep Flask decorators and request-bound dependency wiring thin while delegating response decisions to focused route modules.
- **Analysis/API/history payload seam** — `app/routes/analysis_results.py`, `app/routes/api_analysis.py`, `app/routes/history_replay.py`, `app/routes/ioc_payloads.py`: own browser/API response decisions and shared IOC grouping, serialization, and replay template context.
- **History/detail/settings/diagnostics surfaces** — `app/routes/history.py`, `app/routes/detail.py`, `app/routes/settings.py`, `app/routes/diagnostics.py`: wire replay, drill-down, provider/cache controls, and analyst support routes to focused modules such as `detail_graph.py`, `settings_view.py`, and `diagnostic_export.py`.
- **CTF workspace seam** — `app/routes/ctf.py`, `app/ctf/store.py`, `app/ctf/flags.py`: event/challenge CRUD, per-challenge notes with automatic `PREFIX{...}` flag detection, and the SQLite-backed flag vault at `~/.sentinelx/ctf.db`. Loopback-only like history/settings.
- **CTF toolkit seam** — `app/routes/ctf_toolkit.py`, `app/ctf/toolkit.py`: offline stdlib-only helpers (decoders, Caesar/XOR brute, hash ID/digests, Vigenere, strings, file-signature sniffing, cyclic patterns, little-endian packing) behind validated POST forms.
- **CTF recon runner seam** — `app/ctf/runner.py`: the single SEC-13 exception. Preset argv profiles (nmap/gobuster/ffuf/nikto/sqlmap/whatweb), strict target and wordlist validation, no shell, bounded timeouts/output, runs recorded with auto flag capture.
- **CTF writeup seam** — `app/ctf/writeup.py`, `app/ctf/hints.py`: markdown export per challenge/event with fence-escape protection, and per-category methodology checklists.
- **Diagnostic bundle seam** — `app/diagnostics/`, `app/routes/diagnostic_export.py`: assemble deterministic bounded ZIPs, centralize sanitization policy, redact configured secrets, and apply the supported `/diagnostics/export` response and bounded failure contract.
- **IOC extraction pipeline** — `app/pipeline/extractor.py`, `app/pipeline/normalizer.py`, `app/pipeline/classifier.py`: turn raw pasted text into canonical typed IOC models while deduplicating normalized candidates before repeated classification.
- **Provider registration seam** — `app/enrichment/setup.py`, `app/enrichment/registry.py`: import/register the 16 enrichment providers and expose configured/provider-for-type lookups.
- **Enrichment fan-out and status seam** — `app/enrichment/orchestrator.py`, `app/enrichment/status_snapshots.py`, `app/routes/enrichment_jobs.py`: run provider lookups with concurrency, cache, and retry/backoff controls while serving cursor-based incremental status snapshots.
- **Local cache seam** — `app/cache/store.py`: stores enrichment results in SQLite with TTL lookup, provider-specific rows, stats, clear, and expiry purge operations.
- **Browser polling and result application seam** — `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/modules/result-application.ts`, `app/static/src/ts/modules/row-factory.ts`: poll online jobs, compute/render verdict-first rows, reuse stable per-IOC DOM handles, and keep live/history behavior aligned.
- **Browser utility surfaces** — `app/static/src/ts/modules/filter.ts`, `app/static/src/ts/modules/export.ts`, `app/static/src/ts/modules/history.ts`, `app/static/src/ts/modules/settings.ts`: provide analyst filtering, export/copy/history/settings interactions after results exist.
- **Optimization proof loop** — `tools/optimization_audit.py`, `Makefile`: generate milestone-local audits through `--milestone-id`, refresh the current M020 artifact, collect measured seam evidence, and attach supported verification lanes.

## Current Optimization Seams

1. **Enrichment fan-out/status snapshots** — `app/enrichment/orchestrator.py`, `app/enrichment/status_snapshots.py`, and `app/routes/enrichment_jobs.py` now keep polling on the cursor-based incremental snapshot path. Preserve `since`/`next_since`, terminal state, cached markers, and failure visibility; require fresh scaling evidence before changing this seam again.
2. **Browser result rendering** — `app/static/src/ts/modules/result-application.ts` reuses stable per-IOC handles and keeps whole-grid recount/sort work behind the severity-change gate. M020 measured the current gate and deferred virtualization; promote a larger rewrite only with browser-visible pressure and parity proof.
3. **SQLite cache/history access** — `app/cache/store.py` and `app/enrichment/history_store.py` retain WAL-backed persistent connections and bounded access patterns. M020 left major storage redesign deferred until contention, lock-wait, or write-amplification measurements justify it.
4. **IOC pipeline duplicate handling** — `app/pipeline/extractor.py`, `app/pipeline/normalizer.py`, and `app/pipeline/classifier.py` now deduplicate normalized candidates before repeated classification and preserve first-observed output semantics. Treat this as a regression-protected shipped path rather than an open generic cleanup target.
5. **Route and diagnostic ownership** — focused route-response modules now own analysis/API/history/detail/settings/diagnostic decisions, `app/routes/ioc_payloads.py` owns shared IOC payload shaping, and `app/diagnostics/policy.py` owns sanitization caps. Preserve these boundaries unless new duplication or measured hot-path evidence supports another move.

## Current Optimization Posture

M012 and M013 established the measurement-or-reasoning proof bar. M017 shipped focused polling/status and frontend handle-cache improvements. M020 is complete: it generated `.gsd/milestones/M020/M020-AUDIT.md`, preserved the analyst IOC triage loop, kept route IOC payload and diagnostics sanitization ownership centralized, measured and retained the frontend severity-change gate, and deferred major storage, product/UI, provider, and virtualization rewrites where evidence did not justify them. Future optimization work should begin from those recorded M020 outcomes and refresh the M020 audit surface when reproducing or extending its proof, rather than treating the old M017 plan as future work.

## Non-Negotiable Guardrails

- Do not hide failures to make the app feel faster.
- Do not leak secrets in diagnostics, logs, browser output, or artifacts.
- Preserve IOC intake, enrichment polling, filtering, sorting, copy/export, history reload, detail links, provider settings, and security boundaries unless a slice explicitly improves them.
- Browser-visible behavior changes require browser proof.
- Every shipped optimization needs measurement when practical or explicit code-path reasoning plus regression proof.
