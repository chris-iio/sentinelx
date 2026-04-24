# S02 Research — Runtime/provider seam shipped fixes

## Slice / requirement focus

Primary requirements for this slice are **R014, R015, R018, and R020**: preserve the current per-provider concurrency behavior, 429/backoff semantics, semaphore/snapshot correctness, and adapter-owned session reuse while investigating runtime/provider hot paths. **R040** is a required supporting guardrail because any shipped runtime change has to refresh the audit artifact and carry fresh verification evidence. If this slice surfaces anything through polling/status payloads or analyst-visible UI, it also starts touching **R008/R010/R019** and drifts toward S03, so keep that boundary explicit.

## Summary

This is **targeted research**, not deep greenfield exploration. The runtime/provider seam is already intentionally shaped, and the main risk is changing validated concurrency/backoff/session behavior without enough evidence. The strongest S02 path is:

1. add bounded runtime visibility at the orchestrator layer,
2. use that visibility to decide whether a narrow runtime fix is justified,
3. otherwise update the audit with an explicit keep-decision rather than forcing a rewrite.

The big architectural surprise is that **provider semaphores are per-orchestrator/job, not app-global**. `_setup_orchestrator()` creates a fresh `EnrichmentOrchestrator` per submitted job in `app/routes/_helpers.py`, but the adapter instances come from the app-cached registry built in `app/__init__.py` / `app/enrichment/setup.py`. That means adapter sessions are shared across jobs, while semaphore caps are recreated per job. With the helper-level `_enrichment_pool` capped at 4 jobs, live global provider concurrency can still exceed the nominal per-provider cap under concurrent jobs. That is current behavior and therefore a guardrail, not something to “fix” casually in S02.

## Recommendation

Follow the `observability` skill’s rule here: **add bounded, agent-useful diagnostics instead of speculative concurrency rewrites**. The natural first task is to add per-job runtime/provider diagnostics inside `app/enrichment/orchestrator.py` so S02 can measure what actually happens during enrichment:

- dispatch counts by provider
- cache hits vs misses
- retry counts
- rate-limit retry counts
- provider latency aggregates (count / total / maybe max)
- possibly terminal summary fields that can be consumed by the audit runner or tests

Keep those diagnostics **owned by the orchestrator/job**, not by adapter instances. Adapters are shared registry singletons, so adapter-owned mutable metrics would smear data across concurrent jobs and across registry rebuilds from `app/routes/settings.py`.

Only after that visibility exists should the slice decide whether a narrow optimization is warranted. The most plausible low-risk runtime fix is **reducing wasted work on cache-hit-heavy flows**, because cache hits currently still travel through the normal per-dispatch future/semaphore/attempt path before short-circuiting in `_single_attempt()`. But that should stay measurement-gated. If the new measurements do not show meaningful runtime waste, S02 can truthfully ship diagnostics plus an updated **leave-alone / still-later** audit decision.

Also follow the `verify-before-complete` skill rule: no slice-close claim without a fresh audit refresh and fresh `make verify-fast` / `make verify-deep` evidence in the same execution pass.

## Implementation landscape

### Core runtime files

- `app/enrichment/orchestrator.py`
  - Main S02 seam.
  - Owns per-job dispatch fan-out, per-provider semaphores, retry/backoff, cache short-circuiting, cached markers, and status snapshots.
  - Current logging is sparse: mainly 429 warnings and job-failure logging. There is no bounded runtime summary proving provider mix, cache-hit ratio, or retry cost.

- `app/enrichment/adapters/base.py`
  - Shared template for most HTTP adapters: persistent `requests.Session`, auth-header setup, `safe_request()` dispatch, optional hooks/request body.
  - Useful constraint: this file is *not* a complete seam for instrumentation because several adapters override `lookup()`.

- `app/enrichment/http_safety.py`
  - Canonical HTTP security path for timeout, SSRF allowlist, no redirects, streaming, and response-size cap.
  - Good place to preserve security invariants, but a poor place for primary runtime metrics because it cannot see cache hits, job IDs, retries, or non-HTTP adapters.

- `app/enrichment/setup.py`
  - Registry builder for all 15 providers.
  - Important for S02 because it proves adapters are long-lived app-owned instances; changing session ownership here would directly hit R020.

- `app/__init__.py`
  - Creates the shared cache/history stores and shared provider registry once at app startup.
  - Confirms current architecture wants adapter/session reuse and store reuse, not per-request reconstruction.

- `app/routes/_helpers.py`
  - Boundary file, not the primary S02 seam.
  - `_setup_orchestrator()` creates one orchestrator per job and submits it through `_enrichment_pool` (`max_workers=4`), so there is already a second concurrency layer outside provider semaphores.
  - If S02 decides to expose diagnostics through status payloads, this file changes — but every extra poll payload byte competes with S03’s cursor-native status work, so keep additions bounded.

- `tools/optimization_audit.py`
  - S01 baseline contract file.
  - It already captures request/status and persistence internal benchmarks, but **does not yet capture a runtime/provider-specific measurement**. S02 likely needs to add one here if the slice wants the audit artifact itself to carry the new evidence.

### Existing provider shape that constrains the approach

- `build_registry()` registers **15 providers**, but only **8 are configured with no API keys** in a default local run.
- `BaseHTTPAdapter` covers **12 adapters**, but `rg "def lookup\(" app/enrichment/adapters` shows **custom lookup implementations** in:
  - `virustotal.py`
  - `crtsh.py`
  - `threatminer.py`
  - `dns_lookup.py`
  - `whois_lookup.py`
  - `asn_cymru.py`
- Because of that mix, **orchestrator-level instrumentation is the only seam that automatically covers all providers** without adapter-by-adapter work.

### Current guardrail-heavy behavior already proven by tests

`tests/test_orchestrator.py` is the main protection net (29 collected tests) and already locks down:

- multi-adapter dispatch
- per-provider semaphore caps
- 429 exponential backoff
- semaphore release before backoff sleep
- snapshot safety for `get_status()`
- cached-marker locking
- LRU/terminal tombstone behavior

`tests/test_http_safety.py` (14 collected tests) and `tests/test_base_adapter.py` (35 collected tests) protect the shared adapter/session/security contract. This makes `safe_request()` and session ownership expensive places to churn unless a change is truly necessary.

## Key constraints / surprises

- **Per-job semaphores, shared adapters:** current provider caps are enforced per orchestrator instance, while adapter sessions are shared app-wide. Any attempt to make caps global would be a behavioral change, not a refactor.
- **Helper pool vs provider pool:** `_enrichment_pool` limits concurrent jobs to 4, while each orchestrator creates its own `ThreadPoolExecutor(max_workers=20)`. Do not mix “provider seam” work with helper/job-pool tuning unless measurements clearly show cross-job contention.
- **`provider_concurrency` is not wired through app config:** it exists only in `app/enrichment/orchestrator.py` and tests. Surfacing or tuning it in S02 would expand scope and alter runtime behavior without baseline evidence.
- **Status payload changes are risky scope creep:** if diagnostics are exposed in `/enrichment/status`, keep them tiny and stable. S01’s audit explicitly ranked the request/status seam ahead of frontend/render; S02 should not accidentally worsen the poll path while adding provider metrics.
- **Security posture is centralized and already good:** CSP is locked down in `app/__init__.py`, and all outbound HTTP safety goes through `safe_request()`. Runtime improvements should preserve that rather than bypass it.

## Natural task seams for the planner

1. **Orchestrator diagnostics task**
   - Files: `app/enrichment/orchestrator.py`, `tests/test_orchestrator.py`
   - Goal: add thread-safe per-job runtime/provider diagnostics without changing provider semantics.
   - Scope boundary: avoid adapter/session rewrites and avoid global semaphore changes.

2. **Audit capture / reporting task**
   - Files: `tools/optimization_audit.py`, `tests/test_optimization_audit.py`, `.gsd/milestones/M013/M013-AUDIT.md`
   - Goal: make S02 evidence durable by adding a runtime/provider capture and refreshing the ranked findings.
   - Scope boundary: keep the audit runner the single source of truth; do not scatter runtime findings across task prose only.

3. **Optional narrow runtime fix task (only if the new evidence justifies it)**
   - Likely files: `app/enrichment/orchestrator.py`, maybe `app/routes/_helpers.py` only if a bounded summary must be surfaced
   - Best candidate: reduce avoidable work on cache-hit-heavy flows while preserving cached markers, retry semantics, and provider/session behavior.
   - Fallback outcome: explicit leave-alone / still-later audit update if the new diagnostics show no worthwhile runtime win.

## What to prove first

Prove the measurement surface before changing behavior:

- Can S02 show provider mix, cache-hit ratio, retry cost, and rate-limit behavior for a real enrichment run?
- Can that proof be captured in the durable audit artifact, not just logs?
- Does any measured runtime waste survive once the current per-provider/backoff/session guardrails are honored?

If those answers are weak, S02 should close with stronger observability and a justified keep-decision rather than an invented optimization.

## Verification

### Fast inner-loop checks

- `pytest tests/test_orchestrator.py -q`
- `pytest tests/test_http_safety.py tests/test_base_adapter.py -q`
- `pytest tests/test_optimization_audit.py -q` if the audit runner changes
- `pytest tests/test_analysis_page.py tests/test_routes.py -q` only if S02 exposes diagnostics through Flask routes/status payloads

### Slice-close proof

Per the S01 audit contract and the `verify-before-complete` skill:

1. Refresh the audit artifact:
   - `python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md`
2. Run the fast regression lane:
   - `make verify-fast`
3. Because this slice touches live enrichment orchestration, rerun the mocked-online browser lane:
   - `make verify-deep`
4. Refresh the artifact again with captures if needed so the S02 row records whether the runtime/provider seam shipped a fix or stayed a keep-decision.

Relevant live-stack tests that make `verify-deep` matter here include the online enrichment/browser seams collected from:

- `tests/e2e/test_extraction.py::test_online_mode_indicator[chromium]`
- `tests/e2e/test_extraction.py::test_online_mode_shows_verdict_dashboard[chromium]`
- `tests/e2e/test_url_e2e.py::test_url_enrichment_summary_row_created[chromium]`
- `tests/e2e/test_url_e2e.py::test_url_detail_link_href_correct[chromium]`

## Skill guidance

Installed skills that directly apply:

- `observability` — use its “bounded, agent-first observability” rule for runtime diagnostics instead of ad hoc logging.
- `verify-before-complete` — requires fresh evidence in the same execution pass before any done/works claim.
- `debug-like-expert` — useful mindset if the new runtime measurements disagree with baseline expectations.

Promising external skill if this slice ends up surfacing runtime diagnostics through Flask endpoints or settings UI:

- `npx skills add aj-geddes/useful-ai-prompts@flask-api-development`

I would **not** pull in a SQLite-focused skill for S02 unless the work unexpectedly drifts into cache/history internals; that belongs more naturally to S03.
