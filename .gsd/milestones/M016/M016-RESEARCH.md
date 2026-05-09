# M016 — Research: Minimal Useful Product Hardening

**Date:** 2026-05-09
**Status:** Supersedes the earlier EmailRep-centered research

## Executive Summary

M016 should not add another provider by default. The better product move is to harden SentinelX as a minimal local-first threat-intel evidence workbench: paste messy security text, extract observables quickly, optionally enrich them, and show transparent evidence without dashboard clutter.

The current local code already supports the right core loop (`/` paste form, Offline/Online mode, extraction, enrichment, results cards, details, history resume). The problem is focus: the UI and execution plan still lean toward provider expansion and dashboard-style status surfaces. Research of comparable IOC/enrichment workflows supports a narrower product: fast extraction, explicit enrichment, source-level evidence, and progressive depth only when needed.

## Product Definition

SentinelX is best treated as:

> A local-first IOC evidence workbench for quickly turning raw security text into normalized observables and transparent enrichment context.

It is **not** a SIEM, SOAR, SOC dashboard, raw-email phishing triage suite, or opaque AI verdict engine.

## External Research Takeaways

### 1. IOC tools are valuable when they turn raw observables into reports with evidence

Google Threat Intelligence describes IOC investigation as checking files, URLs, IPs, or domains and producing reports that gather metadata, relationships, and vendor verdicts so users can assess and act. This maps directly to SentinelX's existing strength: extract observables, enrich when requested, and preserve source-level evidence.

**Implication for M016:** keep evidence visible. Do not hide all provider facts behind a single magic score.

### 2. Enrichment should reduce grunt work, not become the product surface

Palo Alto's IOC enrichment workflow frames enrichment as an early repetitive incident-response task: extract IOCs, query threat-intel tools, collect context, then let analysts review/act. ANY.RUN similarly emphasizes swift lookup and context for fatigue-free investigations.

**Implication for M016:** the primary interface should be a fast paste-and-review path, not a provider-management dashboard. Provider state is supporting information.

### 3. Context beats raw data dumps

Threat-intel enrichment guidance consistently frames enrichment as adding context, metadata, relationships, reputation, and temporal information to raw indicators. The useful output is not every raw field; it is the few facts that help an analyst decide whether to pivot, ignore, block, or investigate.

**Implication for M016:** result cards should show compact evidence summaries with details available on demand. Avoid dumping nested provider payloads or showing too many counters by default.

### 4. Progressive enrichment is a good model for speed

Modern enrichment guidance recommends lightweight initial context and deeper enrichment only when needed. This aligns with SentinelX's Offline-first design and explicit Online mode.

**Implication for M016:** Offline should feel instant and local. Online should be explicit, progressive, and honest about pending/provider failures without blocking the useful extracted IOC list.

## Local Codebase Audit Findings

### Current strengths

- `app/templates/index.html` already centers the product around a paste form and Offline-first extraction.
- `app/routes/analysis.py` keeps Offline simple: read text, run `run_pipeline`, group IOCs, render results.
- Online mode is explicit and key-gated through the registry; it does not accidentally contact providers in Offline mode.
- `app/static/src/ts/modules/result-application.ts` has a shared live/history rendering path, which is the right seam for preserving parity while simplifying UI.
- History is already fail-open on the index route via `_recent_analyses_context()`, so history does not block the primary paste flow.

### Current friction / product issues

- The milestone execution state still points at `EmailRepAdapter`, which conflicts with the product direction in `M016-CONTEXT.md`.
- `index.html` has clearer structure than earlier dashboard surfaces, but it still spends significant space explaining mode mechanics before the analyst sees results.
- Recent analyses are presented as a full rail next to the primary task; for a minimal first-use experience this should be visually secondary or collapsible.
- `results.html` renders multiple controls at top-level: mode indicator, count summary, export group, back link, warning, progress, verdict dashboard, provider coverage, filter bar, search, and cards. This is useful but visually dashboard-like.
- `_verdict_dashboard.html` duplicates filter affordances and provider-coverage counters. It is likely the main dashboard chrome to remove, collapse, or visually quiet.
- `_filter_bar.html` shows all verdict filters even when counts are zero or Online enrichment has not completed. That can make the surface feel heavier than the evidence.
- Runtime speed is not yet measured. We need baseline timing before claiming fast.

## Recommended Direction

### Stop: EmailRep as the default next action

EmailRep can remain a future provider idea, but it should not drive M016. Adding EmailRep would expand settings, registry, provider-count, UI-context, and test surface without answering whether the current tool is useful and fast.

### Start: product-loop hardening

M016 should implement and verify a minimal useful product loop:

1. Open `/`.
2. Paste suspicious text.
3. Keep Offline by default or intentionally switch Online.
4. Submit.
5. See extracted IOCs quickly.
6. Review compact evidence and provider status.
7. Open details only when needed.
8. Resume a past analysis without re-enrichment.

### Runtime target

Measure first, then optimize. Candidate paths:

- Offline `POST /analyze` route timing around `run_pipeline()` and template render.
- Initial browser render time for results with many IOCs.
- Online enrichment status polling and DOM update behavior.
- History detail replay time and DOM update behavior.

The first likely target should be Offline paste-to-results, because it is the product's safest default and easiest to benchmark deterministically.

## UI Simplification Hypotheses

These are hypotheses to test/implement during M016, not final design mandates:

- Make the input card feel like one obvious command surface: shorter copy, larger textarea, fewer explanatory paragraphs.
- Keep Offline/Online choice, but reduce mode explanation to one line plus accessible status.
- Move recent analyses into a quieter secondary strip/details disclosure rather than a competing rail.
- Replace the Online verdict KPI dashboard with a compact status line and let result-card labels carry verdict information.
- Keep filters, but make them conditional or compact so they do not dominate small result sets.
- Preserve detail/context links so provider evidence remains available.
- Prefer progressive disclosure over removing evidence.

## Verification Strategy

M016 completion requires evidence, not aesthetics alone:

- Focused route/unit tests for touched analysis/history/enrichment behavior.
- Frontend tests for touched form/filter/result modules.
- Browser proof for Offline paste-to-results on desktop and mobile.
- Browser proof for mocked Online enrichment with progress/failure/provider evidence.
- Browser proof for history resume with no re-query/polling.
- Fresh runtime evidence for at least one path, preferably Offline paste-to-results before and after simplification or optimization.
- `make verify-fast` as the final routine lane after implementation.

## Sources / Artifacts

Research artifacts saved locally:

- `.firecrawl/m016-product-research.json`
- `.firecrawl/m016-workflow-research.json`
- `.firecrawl/m016-ui-research.json`

External sources consulted:

- Google Threat Intelligence, "Get started with IOC Investigation" — IOC reports gather metadata, relationships, and vendor verdicts for analyst assessment.
- Palo Alto Networks, "Security Orchestration Use Case: Automating IOC Enrichment" — enrichment extracts IOCs, queries sources, and makes context available quickly during incident response.
- ANY.RUN, "How to Enrich IOCs with Actionable Threat Context" — quick checks and context reduce investigation fatigue.
- Wiz, "What Is Enrichment In Threat Intelligence?" — enrichment turns raw observables into actionable context and recommends progressive enrichment strategies.

## Superseded Prior Research

The earlier M016 EmailRep research is intentionally superseded. Its useful takeaway is limited to a future provider backlog item: email IOCs currently have no Online provider coverage. That is not the highest-value M016 problem.
