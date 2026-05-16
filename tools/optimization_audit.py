#!/usr/bin/env python3
"""SentinelX optimization audit runner.

Creates a durable markdown artifact for milestone-local optimization passes.
The workflow is SentinelX-first, but the document shape is intentionally light
and reusable: every finding must cite either measurement or explicit code-path
reasoning, and every finding must land in a ranked bucket.

Examples:
    python3 tools/optimization_audit.py --help
    python3 tools/optimization_audit.py --mode template \
        --output .gsd/milestones/M013/M013-AUDIT-TEMPLATE.md
    python3 tools/optimization_audit.py --mode baseline \
        --output .gsd/milestones/M013/M013-AUDIT.md
    python3 tools/optimization_audit.py --mode baseline \
        --capture-command "verify-fast::make verify-fast" \
        --capture-command "smoke::python3 -c \"print('ok')\""
"""
from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from collections import deque
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from unittest.mock import patch

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.text_utils import collapse_whitespace, stripped_text_or_none  # noqa: E402
from app.time_utils import utc_display_seconds, utc_now  # noqa: E402

DEFAULT_MILESTONE_ID = "M013"
DEFAULT_OUTPUT = Path(f".gsd/milestones/{DEFAULT_MILESTONE_ID}/{DEFAULT_MILESTONE_ID}-AUDIT.md")
DEFAULT_TEMPLATE_OUTPUT = Path(
    f".gsd/milestones/{DEFAULT_MILESTONE_ID}/{DEFAULT_MILESTONE_ID}-AUDIT-TEMPLATE.md"
)
M017_MILESTONE_ID = "M017"
M017_OUTPUT = Path(f".gsd/milestones/{M017_MILESTONE_ID}/{M017_MILESTONE_ID}-AUDIT.md")
M017_TEMPLATE_OUTPUT = Path(
    f".gsd/milestones/{M017_MILESTONE_ID}/{M017_MILESTONE_ID}-AUDIT-TEMPLATE.md"
)
M020_MILESTONE_ID = "M020"
M020_OUTPUT = Path(f".gsd/milestones/{M020_MILESTONE_ID}/{M020_MILESTONE_ID}-AUDIT.md")
M020_TEMPLATE_OUTPUT = Path(
    f".gsd/milestones/{M020_MILESTONE_ID}/{M020_MILESTONE_ID}-AUDIT-TEMPLATE.md"
)
PROJECT_MAP_PATH = Path("docs/project-map.md")
FINDING_BUCKETS = ("do now", "do next", "later", "leave alone")
RUNTIME_PROVIDER_DIAGNOSTIC_FIELDS = (
    "dispatch_count",
    "attempt_count",
    "cache_hits",
    "cache_misses",
    "retry_count",
    "rate_limit_retry_count",
    "error_count",
    "latency_total_seconds",
    "latency_max_seconds",
    "providers",
)
RUNTIME_PROVIDER_PROVIDER_FIELDS = (
    "dispatch_count",
    "attempt_count",
    "cache_hits",
    "cache_misses",
    "retry_count",
    "rate_limit_retry_count",
    "error_count",
    "latency_total_seconds",
    "latency_max_seconds",
)


@dataclass(frozen=True, slots=True)
class VerificationLane:
    name: str
    command: str
    use_when: str


@dataclass(frozen=True, slots=True)
class Guardrail:
    requirement_id: str
    summary: str


@dataclass(frozen=True, slots=True)
class Seam:
    name: str
    continuity_focus: str
    prompts: tuple[str, str]


@dataclass(frozen=True, slots=True)
class CommandCapture:
    label: str
    command: str
    exit_code: int
    duration_ms: int
    summary: str


@dataclass(frozen=True, slots=True)
class BaselineFinding:
    bucket: str
    finding: str
    seam: str
    evidence_kind: str
    evidence_summary: str
    continuity_guardrails: str
    rerun_lanes: str
    continuity_notes: str


@dataclass(frozen=True, slots=True)
class SeamNote:
    seam: str
    boundary: str
    current_shape: str
    continuity_watch: str
    baseline_call: str


@dataclass(frozen=True, slots=True)
class GuardrailCoverage:
    requirement_id: str
    seam: str
    covered_by: str
    continuity_notes: str


@dataclass(slots=True)
class AuditDocument:
    milestone_id: str
    mode: str
    repo_name: str
    repo_root: Path
    output_path: Path
    generated_at: str
    captures: list[CommandCapture] = field(default_factory=list)


VERIFICATION_LANES: tuple[VerificationLane, ...] = (
    VerificationLane(
        name="verify-fast",
        command="make verify-fast",
        use_when=(
            "Default rerun lane for backend/frontend logic, build/test plumbing, "
            "and any finding that does not change mocked-online browser behavior."
        ),
    ),
    VerificationLane(
        name="verify-deep",
        command="make verify-deep",
        use_when=(
            "Required whenever a change touches live enrichment orchestration, "
            "polling/status flow, results-page DOM/state, or mocked-online browser seams."
        ),
    ),
    VerificationLane(
        name="verify",
        command="make verify",
        use_when="Full pre-handoff lane when downstream slices need the unambiguous repo-wide proof command.",
    ),
)

GUARDRAILS: tuple[Guardrail, ...] = (
    Guardrail("R008", "Preserve enrichment polling, export, filtering, detail links, copy buttons, and progress continuity."),
    Guardrail("R009", "Preserve CSP, CSRF, SSRF allowlist, host validation, and DOM-safety constraints."),
    Guardrail("R010", "Preserve or improve polling/render efficiency."),
    Guardrail("R014", "Preserve per-provider concurrency behavior unless evidence proves a better approach."),
    Guardrail("R015", "Preserve 429 backoff behavior unless evidence proves a better approach."),
    Guardrail("R018", "Preserve semaphore/backoff and snapshot correctness unless evidence proves otherwise."),
    Guardrail("R019", "Preserve cursor-based polling efficiency unless evidence proves otherwise."),
    Guardrail("R020", "Preserve persistent HTTP session behavior where still justified."),
    Guardrail("R022", "Preserve WAL-mode cache/history store behavior unless evidence supports change."),
    Guardrail("R040", "Keep strong verification continuity while refactoring and optimizing."),
)

SEAMS: tuple[Seam, ...] = (
    Seam(
        name="runtime/provider",
        continuity_focus="Orchestrator concurrency, cache interaction, retry/backoff behavior, and provider dispatch cost.",
        prompts=(
            "What work is measured here, and what hot-path reasoning is still required?",
            "Which guardrails and rerun lanes must stay attached if we change this seam?",
        ),
    ),
    Seam(
        name="request/status",
        continuity_focus="Flask route/helper status flow, next_since continuity, and history-save diagnostics.",
        prompts=(
            "What request-path work is actually hot versus only structurally central?",
            "If a finding changes analyst-visible status behavior, which proof lane catches it?",
        ),
    ),
    Seam(
        name="persistence",
        continuity_focus="SQLite WAL cache/history store access, locking, query shape, and post-enrichment durability.",
        prompts=(
            "Is there measured contention, or should this seam remain a leave-alone decision?",
            "What evidence would justify revisiting long-lived WAL-backed connections?",
        ),
    ),
    Seam(
        name="frontend/render",
        continuity_focus="Polling cadence, shared live/history result application, and DOM/render churn.",
        prompts=(
            "What analyst-visible work is actually happening per poll or per render flush?",
            "Does the finding preserve live/history parity and deterministic mocked-online proof?",
        ),
    ),
)

BASELINE_FINDINGS: tuple[BaselineFinding, ...] = (
    BaselineFinding(
        bucket="leave alone",
        finding="Keep `/enrichment/status` and `/api/status` on the orchestrator-owned incremental snapshot path; the request/status hot-path fix is shipped.",
        seam="request/status",
        evidence_kind="measurement + code-path reasoning",
        evidence_summary=(
            "Internal capture `status-snapshot-scaling` now compares the retained-list full snapshot with the shipped delta accessor: "
            "`get_status()` still scales with total retained results, while `get_incremental_status(since=4990)` returns only the tail and preserves `next_since`. "
            "`app/routes/_helpers.py::_get_enrichment_status()` now calls `orchestrator.get_incremental_status()` and serializes only the returned tail plus aligned `cached_markers`, while helper-owned terminal tombstones and history-save diagnostics stay intact."
        ),
        continuity_guardrails="R008, R010, R018, R019, R040",
        rerun_lanes="`make verify-fast`, `make verify-deep`",
        continuity_notes=(
            "Preserve `done`/`total`/`complete`, `next_since`, tail-only `cached_at` markers, terminal failure semantics, and aggregate history-save diagnostics; "
            "do not fall back to full results snapshots on the poll path without fresh evidence."
        ),
    ),
    BaselineFinding(
        bucket="do next",
        finding="Keep the shared result-application coordinator on cached per-IOC DOM handles before chasing broader flush-wide render work.",
        seam="frontend/render",
        evidence_kind="code-path reasoning",
        evidence_summary=(
            "`app/static/src/ts/modules/result-application.ts` now caches each IOC's card, context line, verdict label, enrichment slot, lazily discovered summary row, details panel, section handles, reputation-row count, no-data summary injection state, spinner wrapper, pending indicator, copy button, and provider-count total "
            "inside `createResultApplicationCoordinator()`, so `apply()`, `flush()`, and `finalize()` reuse stable DOM references instead of repeating `findCardForIoc()` "
            "and `.querySelector('.enrichment-slot')`/`.querySelector('.ioc-summary-row')`/`.querySelector('.ioc-context-line')`/`.querySelector('.verdict-label')`/`.querySelector('.enrichment-details')`/`.querySelector('.spinner-wrapper')`/`.querySelector('.enrichment-waiting-text')`/`.querySelector('.no-data-summary-row')` work. `finalize()` now walks a cached IOC-value list with indexed iteration instead of allocating a `Map.values()` iterator over the handle cache. "
            "Focused proof lives in `app/static/src/ts/modules/result-application.test.ts::caches stable IOC handles and provider counts across repeated apply, flush, and finalize calls`, which verifies repeated same-IOC results do not repeat summary-row, context-line, verdict-label, spinner, or pending-indicator lookups, finalization does not add another details-panel lookup, and finalization skips the old no-data summary guard query; `skips reputation detail-row sorting while an IOC has only one reputation row`, which makes one-row reputation sorting fail while preserving summary rendering; `app/static/src/ts/modules/row-factory.test.ts::reuses cached summary row and details handles when provided`, which makes slot summary/details lookup fail while preserving summary rendering; and `app/static/src/ts/modules/row-factory.test.ts::CTX-01: reuses a cached context line when provided`, which makes card context-line lookup fail while preserving context text insertion. "
            "`finalize walks cached IOC values without allocating a Map values iterator` patches `Map.prototype.values` to fail while preserving detail-link injection. "
            "The remaining shared render cost still sits in `updateDashboardCounts()` scanning every `.ioc-card` "
            "and `sortCardsBySeverity()` reordering the whole grid after each flush, so broader follow-up should stay explicit and measurement-led."
        ),
        continuity_guardrails="R008, R009, R010, R019, R040",
        rerun_lanes="`make verify-fast`, `make verify-deep`",
        continuity_notes=(
            "If a later pass narrows flush-wide render work, preserve live/history parity, textContent-only DOM construction, expand toggles, export/copy/detail-link wiring, "
            "and deterministic mocked-online browser proof."
        ),
    ),
    BaselineFinding(
        bucket="leave alone",
        finding="Keep the runtime/provider dispatch path unchanged until diagnostics show a materially cache-hit-heavy workload.",
        seam="runtime/provider",
        evidence_kind="measurement + code-path reasoning",
        evidence_summary=(
            "Internal capture `runtime-provider-diagnostics` reports provider mix CacheAlpha:2d/0e, RateLimitBeta:2d/1e; dispatch=4, attempts=5, cache-hit ratio 1/5 (20%), retries=1 (429=1), and latency total=2.25s max=1.00s. "
            "The orchestrator already short-circuits cache hits inside `_single_attempt()`, so moving that check ahead of thread-pool/semaphore scheduling would only shave bounded dispatch overhead and this measurement does not show a large enough cache-hit-heavy mix to justify churn."
        ),
        continuity_guardrails="R014, R015, R018, R020, R040",
        rerun_lanes="`make verify-fast`, `make verify-deep`",
        continuity_notes=(
            "Preserve per-provider caps, cache-hit markers, retry/backoff semantics, and adapter-owned session reuse; only revisit pre-dispatch short-circuiting if a future capture shows cache hits dominating enough to outweigh the regression surface."
        ),
    ),
    BaselineFinding(
        bucket="leave alone",
        finding="Keep WAL-backed cache/history stores and persistent connections unchanged until contention evidence appears.",
        seam="persistence",
        evidence_kind="measurement + code-path reasoning",
        evidence_summary=(
            "Internal temp-DB captures show low-latency cache puts/gets and history saves/loads on the current code, while `app/cache/store.py` "
            "and `app/enrichment/history_store.py` already enable WAL, `busy_timeout`, persistent connections, and simple indexed queries. "
            "No lock-pressure or write-amplification evidence justified churn in this baseline pass."
        ),
        continuity_guardrails="R022, R040",
        rerun_lanes="`make verify-fast`",
        continuity_notes=(
            "If a later slice sees real writer contention, measure concurrent load first; do not trade away WAL or persistent-connection simplicity speculatively."
        ),
    ),
    BaselineFinding(
        bucket="leave alone",
        finding="Keep per-provider backoff/session semantics as explicit measured keep-decisions.",
        seam="runtime/provider",
        evidence_kind="measurement + code-path reasoning",
        evidence_summary=(
            "The same `runtime-provider-diagnostics` capture surfaces retry/rate-limit cost and provider error tallies without widening analyst-visible status, and `tests/test_orchestrator.py` still proves semaphores exclude backoff sleep, cached markers stay locked, and diagnostics snapshots stay stable. "
            "That combination makes measurement the additive change while keeping adapter-owned sessions and backoff rules on explicit keep-decision footing until a later slice shows real provider pain."
        ),
        continuity_guardrails="R014, R015, R018, R020, R040",
        rerun_lanes="`make verify-fast`, `make verify-deep`",
        continuity_notes=(
            "Future work should consume the measured diagnostics surface first and only revisit the contract if live evidence shows meaningful provider pain beyond cache-hit-heavy dispatch overhead."
        ),
    ),
)

M020_FINDINGS: tuple[BaselineFinding, ...] = (
    BaselineFinding(
        bucket="do now",
        finding="Keep S02's duplicate route IOC grouping rewrite on the shared route helper seam.",
        seam="request/status",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/routes/analysis.py`, `app/routes/api.py`, and `app/routes/history.py` were the highest-confidence M020 rewrite target because those request surfaces rebuilt IOC template context, grouped persisted IOC rows, and serialized/grouped JSON API payloads separately after prior micro-optimizations. "
            "S02 now centralizes those builders in `app/routes/_helpers.py` through `_ioc_template_context()`, `_history_ioc_template_context()`, `_group_iocs_for_template()`, `_group_history_iocs()`, and `_serialized_ioc_response_payload()`, while the route modules keep thin imports for their response-specific behavior. Focused proof is `python3 -m pytest -q tests/test_routes.py tests/test_api.py tests/test_history_routes.py`."
        ),
        continuity_guardrails="R008, R009, R010, R040, R094, R095, R096, R097, R098, R099",
        rerun_lanes="`python3 -m pytest -q tests/test_routes.py tests/test_api.py tests/test_history_routes.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve online-admission error visibility, missing-provider redirects, grouped template IOC data, JSON API shape, empty history replay states, diagnostics proof language, CSRF/DOM safety, capture-command failure visibility, and secret redaction while keeping duplicate route-owned IOC grouping and serialization code behind the shared helper seam."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep S03's diagnostics sanitization caps behind the shared immutable policy object.",
        seam="diagnostic export/sanitization",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/diagnostics/policy.py` now owns `DiagnosticSanitizationPolicy` and `DIAGNOSTIC_SANITIZATION_POLICY`, an immutable caps object shared by `app/diagnostics/assembler.py`, `app/diagnostics/redaction.py`, and `app/diagnostics/sources.py` for the S03 diagnostics/redaction contract. "
            "Assembler archive-path and generated-filename bounds, runtime source byte/string/list/dict/depth caps, and redaction depth/label caps now derive from that policy while the existing optimized helper names remain stable. "
            "T02 inspected the production modules and left behavior alone because the shared policy extraction was already complete; the S03 outcome is therefore shipped as a centralization keep-decision, not rejected. "
            "Focused proof is `python3 -m pytest -q tests/test_diagnostic_export_assembler.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_sources.py`."
        ),
        continuity_guardrails="R009, R040, R096, R097, R098, R099",
        rerun_lanes="`python3 -m pytest -q tests/test_diagnostic_export_assembler.py tests/test_diagnostic_redaction.py tests/test_diagnostic_export_sources.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve diagnostic source status/error/omitted/truncated manifest states, archive validation errors, config read errors as secret-free metadata, failed audit capture visibility, exact-secret longest-first replacement, configured-secret inventory labels, archive path rejection, manifest collision checks, truncation caps, and secret-free diagnostic bundles with no raw provider keys, bearer tokens, secrets, or `.gsd`/`.planning`/`.audits`/`.git` contents while keeping diagnostics caps centralized."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep large-result frontend rendering on the severity-change gate and defer virtualization.",
        seam="frontend/render",
        evidence_kind="work-count measurement + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/result-application.test.ts::measures large-result render pressure at the severity-change gate` builds a 240-card results fixture for the S04 browser-visible deferment. "
            "After the initial clean verdict, a second provider result with the same severity performs zero `.ioc-card` whole-grid scans, zero dashboard recounts, and zero sort calls. A later malicious severity change performs exactly one document-level card scan for dashboard counts and one grid-level card scan for the debounced sort. Current evidence supports preserving the severity-change gate rather than promoting DOM virtualization."
        ),
        continuity_guardrails="R008, R009, R010, R019, R040, R096, R097, R098",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/result-application.test.ts`; `make verify-fast`; `make verify-deep` for browser-visible/live-enrichment-visible proof",
        continuity_notes=(
            "Preserve filtering, sorting, copy/export, detail links, expansion state, live/history parity, textContent-safe rendering, failure visibility through DOM state, mocked-online browser failures, and the severity-change gate without logging secrets or provider payloads. Reconsider virtualization only with evidence beyond this 240-card work-count fixture."
        ),
    ),
    BaselineFinding(
        bucket="do next",
        finding="Refresh S05's final closeout audit after every shipped, rejected, or deferred rewrite so downstream proof stays current.",
        seam="audit/proof handoff",
        evidence_kind="code-path reasoning + generated artifact proof",
        evidence_summary=(
            "S05 depends on the generated M020 audit being the DB-independent handoff for shipped, rejected, deferred, and leave-alone outcomes. "
            "The closeout contract records that S02 shipped route helper centralization, S03 shipped diagnostics policy centralization, and S04 rejected virtualization promotion by keeping the severity-change gate while virtualization remains deferred until measured browser-visible pressure justifies it. "
            "Final `make verify` remains the S05 closeout proof lane, paired with a refreshed generated audit, so downstream agents can see both the ranked outcome table and the full app verification lane passes instead of relying on hand-edited `.gsd` prose. "
            "The runner already records command-surface rows, measurement captures, rerun lanes, and ranked finding rows, so the next optimization step is to keep refreshing `make audit-m020` after each implementation slice rather than letting S02-S04 proof drift from the final closeout artifact."
        ),
        continuity_guardrails="R040, R094, R095, R096, R097, R098, R099, R100",
        rerun_lanes="`make audit-m020`; `python3 -m pytest -q tests/test_optimization_audit.py`; `make verify-fast`; final closeout must run `make verify`",
        continuity_notes=(
            "Preserve the generated artifact as the inspection surface for future agents: every closeout update must keep command-surface rows, failed-capture visibility, proof lanes, and ranked shipped/rejected/deferred/leave-alone outcomes synchronized. "
            "Keep failure-visibility and redaction guardrails explicit: route/API responses for missing-provider and empty-path behavior, diagnostic bundle manifest status/error/omitted/truncated metadata, redaction metadata without raw secrets, and generated audit command-capture rows, including failed-capture visibility, all remain part of the S05 proof surface."
        ),
    ),
    BaselineFinding(
        bucket="later",
        finding="Defer frontend DOM virtualization until measured result-card counts justify the browser-visible regression surface.",
        seam="frontend/render",
        evidence_kind="code-path reasoning",
        evidence_summary=(
            "M017 removed repeated coordinator-local DOM lookup work and narrowed flush-wide recount/reorder calls. A deeper virtualization rewrite would touch `app/static/src/ts/modules/result-application.ts`, `row-factory.ts`, filters, copy/export, and E2E-visible DOM contracts. Current audit captures do not show enough large-result browser pressure to justify that risk for M020 S02."
        ),
        continuity_guardrails="R008, R009, R010, R019, R040, R096, R097, R098",
        rerun_lanes="`npx vitest run`; `make verify-deep`; `make verify` when promoted",
        continuity_notes=(
            "Promote only with a fixture or browser measurement showing card-count pressure. Preserve filtering, sorting, copy/export, detail links, expansion state, textContent-safe rendering, and mocked-online browser proof."
        ),
    ),
    BaselineFinding(
        bucket="leave alone",
        finding="Leave provider concurrency/backoff semantics alone during M020 unless fresh live evidence contradicts the M017 keep-decision.",
        seam="runtime/provider",
        evidence_kind="measurement + code-path reasoning",
        evidence_summary=(
            "The M017 `runtime-provider-diagnostics` capture showed cache hits did not dominate dispatch cost, while tests protect semaphore scope, 429 backoff, cached markers, and diagnostics. M020 should not rewrite provider scheduling simply because it is complex; complexity here reflects quota and failure semantics."
        ),
        continuity_guardrails="R014, R015, R018, R020, R040, R099",
        rerun_lanes="`python3 -m pytest -q tests/test_orchestrator.py`; `make verify-deep` for live-enrichment-visible changes",
        continuity_notes=(
            "Preserve per-provider concurrency caps, retry/backoff, adapter-owned sessions, cache-hit markers, terminal failure visibility, and diagnostics unless a new measurement proves a better contract."
        ),
    ),
)

BASELINE_SEAM_NOTES: tuple[SeamNote, ...] = (
    SeamNote(
        seam="runtime/provider",
        boundary="`app/enrichment/orchestrator.py` plus `tests/test_orchestrator.py`.",
        current_shape=(
            "Dispatch fans out IOC/adaptor pairs through a thread pool, but rate-limited providers are gated by per-provider semaphores and 429 backoff sleeps happen "
            "outside the semaphore. Cache hits short-circuit lookup work inside `_single_attempt()`, and tests already prove concurrency, retry, and snapshot invariants."
        ),
        continuity_watch="R014, R015, R018, R020, R040 stay attached to any change here.",
        baseline_call=(
            "The deterministic `runtime-provider-diagnostics` capture now points to a keep-decision: current cache hits do not dominate enough to justify moving work ahead of the worker/semaphore path, so do not rewrite concurrency policy, backoff scope, or session ownership on aesthetics."
        ),
    ),
    SeamNote(
        seam="request/status",
        boundary="`app/routes/_helpers.py`, `app/routes/analysis.py`, and helper/status regression coverage.",
        current_shape=(
            "The helper owns a bounded module-level orchestrator registry, a shared enrichment thread pool, terminal tombstones, and history-save diagnostics. The frontend's `since` cursor "
            "contract is preserved on the shipped path because `_get_enrichment_status()` now asks the orchestrator for an incremental snapshot and only serializes the returned tail."
        ),
        continuity_watch="R008, R010, R018, R019, R040 are the key guardrails.",
        baseline_call=(
            "The hot-path fix is now shipped: keep polling on the orchestrator-owned incremental snapshot path and leave helper-owned terminal tombstones plus history-save diagnostics truthful."
        ),
    ),
    SeamNote(
        seam="persistence",
        boundary="`app/cache/store.py`, `app/enrichment/history_store.py`, and their focused unit suites.",
        current_shape=(
            "Both stores use persistent SQLite connections, WAL mode, `busy_timeout`, and simple indexed access patterns. Writes commit per operation, which is conservative but currently uncomplicated and "
            "well-covered by tests."
        ),
        continuity_watch="R022 and R040 must remain explicit.",
        baseline_call=(
            "Keep the current store design until a later slice captures real contention, lock waits, or write-amplification evidence under concurrent load."
        ),
    ),
    SeamNote(
        seam="frontend/render",
        boundary="`app/static/src/ts/modules/enrichment.ts`, `result-application.ts`, `row-factory.ts`, and mocked-online browser proof.",
        current_shape=(
            "The live polling loop runs every 750ms, batches DOM flushes with a 100ms timer, and routes both live and history application through one coordinator. That shared path now caches stable card/summary-row/context-line/verdict-label/slot/details/section/spinner/pending-indicator handles, reputation-row count, and no-data summary injection state per IOC, but severity-changing flushes still recount `.ioc-card`s and reorder the whole grid."
        ),
        continuity_watch="R008, R009, R010, R019, R040 remain coupled to any render optimization.",
        baseline_call=(
            "The shipped coordinator-local cache retired repeated card/summary-row/context-line/verdict-label/slot/details/spinner/pending-indicator/no-data-summary lookups; any later frontend pass should focus on measuring and narrowing flush-wide dashboard recounts/reorders without disturbing the broader proof surface."
        ),
    ),
)

BASELINE_GUARDRAIL_COVERAGE: tuple[GuardrailCoverage, ...] = (
    GuardrailCoverage("R008", "request/status + frontend/render", "Shipped request/status delta path plus do-next flush-wide render follow-up", "Keep polling continuity, export/copy/detail-link behavior, and progress visibility intact."),
    GuardrailCoverage("R009", "frontend/render", "Do-next flush-wide frontend/render work", "Preserve textContent-only DOM construction, CSP/CSRF assumptions, and host-validation-adjacent safety expectations."),
    GuardrailCoverage("R010", "request/status + frontend/render", "Shipped request/status delta path plus do-next flush-wide render follow-up", "Any shipped optimization must reduce or at least not worsen polling/render churn."),
    GuardrailCoverage("R014", "runtime/provider", "Measured runtime/provider keep-decision", "Per-provider concurrency remains part of the contract unless a future cache-hit-heavy capture proves that a narrower pre-dispatch optimization is worth the regression surface."),
    GuardrailCoverage("R015", "runtime/provider", "Measured runtime/provider keep-decision", "429 backoff stays protected; future changes must prove they do not regress quota safety."),
    GuardrailCoverage("R018", "runtime/provider + request/status", "Shipped request/status delta path plus measured runtime/provider evidence", "Snapshot correctness, semaphore scope, and cached-marker locking remain non-negotiable."),
    GuardrailCoverage("R019", "request/status + frontend/render", "Shipped request/status delta path plus do-next flush-wide render follow-up", "Keep `since`/`next_since` incremental polling semantics end-to-end."),
    GuardrailCoverage("R020", "runtime/provider", "Measured runtime/provider keep-decision", "Persistent adapter-owned sessions stay justified until measured evidence argues otherwise."),
    GuardrailCoverage("R022", "persistence", "Leave-alone WAL store decision", "WAL and persistent connection behavior stay explicit keep-decisions pending contention evidence."),
    GuardrailCoverage("R040", "all seams", "Every ranked finding", "Each future slice must rerun the listed proof lanes before claiming an optimization is safe."),
)

M017_FINDINGS: tuple[BaselineFinding, ...] = (
    BaselineFinding(
        bucket="do now",
        finding="Keep S03's shipped enrichment status polling optimization on the tail-only snapshot path for SentinelX's analyst IOC triage loop.",
        seam="enrichment fan-out/status snapshot cost",
        evidence_kind="measurement + code-path reasoning",
        evidence_summary=(
            "`docs/project-map.md` ranks enrichment fan-out/status snapshot cost as the #1 optimization priority for the local analyst IOC triage workflow. "
            "The `status-snapshot-scaling` capture measures the old retained-list snapshot against the shipped tail accessor: "
            "`get_status()` scales with retained results while `get_incremental_status(since=4990)` returns only the tail and preserves `next_since`. "
            "Code-path proof lives in `app/enrichment/orchestrator.py::get_incremental_status()` and `app/routes/_helpers.py::_get_enrichment_status()`, where the polling route calls the incremental accessor and serializes only returned tail rows plus aligned `cached_markers`. "
            "Full `get_status()` snapshots still return a caller-isolated result list, but now copy retained results with direct accumulation instead of routing through the `list()` constructor; focused proof lives in `tests/test_orchestrator.py::TestGetStatusListSnapshot::test_get_status_snapshot_copies_results_directly`. "
            "The incremental snapshot now uses `itertools.islice()` plus direct accumulation for non-negative and negative cursors to avoid creating an intermediate sliced results list or constructor-copying the returned tail while preserving Python negative-slice compatibility; focused proof lives in `tests/test_orchestrator.py::TestIncrementalStatusSnapshot::test_get_incremental_status_nonnegative_since_does_not_slice_results`, `test_get_incremental_status_copies_tail_without_list_constructor`, and `test_get_incremental_status_preserves_negative_since_behavior`. "
            "Out-of-range cursors now return an empty tail before walking retained results; focused proof lives in `tests/test_orchestrator.py::TestIncrementalStatusSnapshot::test_get_incremental_status_returns_empty_tail_beyond_retained_length`. "
            "Scalar status fields are now copied directly by known public key instead of scanning every job item and filtering internals; focused proof lives in `tests/test_orchestrator.py::TestIncrementalStatusSnapshot::test_get_incremental_status_builds_scalar_fields_without_items_scan`. "
            "The public `cached_markers` snapshot now preserves caller isolation while copying markers with direct key accumulation instead of `dict(self._cached_markers)`; focused proof lives in `tests/test_orchestrator.py::TestCachedMarkersLock::test_cached_markers_snapshot_copies_directly`. "
            "Polling serialization now reads `status.get('cached_markers')` once per payload and reuses the marker map for every tail result; focused proof lives in `tests/test_routes.py::test_enrichment_status_reads_cached_markers_once_per_payload`. "
            "That same status proof also guards `_get_enrichment_status()` against list-comprehension frames while serializing the returned tail. "
            "`_build_status_payload()` now only falls back to `len(status['results'])` when `next_since` is missing, instead of evaluating that length while an explicit cursor is already present; focused proof lives in `tests/test_routes.py::test_status_payload_uses_explicit_next_since_without_measuring_results`. "
            "`_serialize_result()` also skips per-result cache-key construction entirely when the cached-marker map is empty; focused proof lives in `tests/test_routes.py::test_serialize_result_skips_empty_cached_marker_map`. "
            "Background history-save serialization now accumulates result and IOC payloads with direct loops instead of callback-style bulk mapping; focused proof lives in `tests/test_history_routes.py::TestEnrichmentSaveWrapper::test_save_serializes_results_and_iocs_with_direct_loops`. "
            "History-save diagnostic default and live snapshots are now copied with direct helpers instead of `dict(...)`; focused proof lives in `tests/test_history_routes.py::TestEnrichmentSaveWrapper::test_history_save_diagnostics_falls_back_to_safe_defaults`, which preserves malformed-state coercion while guarding the coercion/accessor functions against constructor-copying diagnostics. "
            "History-save timestamp presence and orchestration status string coercion now reuse `has_non_whitespace()` so timestamp checks avoid stripped-string allocation and status strings strip at most once when a normalized value is kept; the fixed diagnostic/status field groups and recordable outcome sets now live as module constants instead of rebuilt tuple/set literals inside each coercion call; focused proof lives in `test_history_save_diagnostics_presence_checks_avoid_timestamp_strip`, `test_history_save_diagnostics_error_summary_strips_once`, and `tests/test_routes.py::test_orchestration_status_string_coercion_strips_once`. "
            "Polling terminal-status code selection now reuses the tuple-backed `_STATUS_NOT_FOUND_REASONS` membership table instead of allocating the `{'unknown', 'evicted'}` set on every status response; focused proof lives in `tests/test_routes.py::test_enrichment_status_not_found_reasons_use_static_membership_set`. "
            "Diagnostic terminal tombstone snapshots now copy terminal job state with direct key accumulation instead of `dict(_terminal_jobs.get(...))`; focused proof lives in `tests/test_routes.py::test_orchestration_diagnostics_evicted_job_copies_terminal_snapshot_directly`. "
            "Malformed diagnostics provider maps are also coerced by scanning provider keys directly instead of allocating an `items()` view; focused proof lives in `tests/test_orchestrator.py::TestJobDiagnostics::test_get_diagnostics_falls_back_to_safe_defaults_for_malformed_state`."
        ),
        continuity_guardrails="R085, R087, R008, R010, R018, R019, D078, D079, D080",
        rerun_lanes="`python3 tools/optimization_audit.py --milestone-id M017 --mode baseline`; `make verify-fast`; add `make verify-deep` for browser-visible polling changes",
        continuity_notes=(
            "S03 shipped this path with measurement and code-path proof; preserve `total`, `done`, `complete`, `status`, `terminal`, `terminal_reason`, `error`, full-status result isolation, cached-marker snapshot isolation, `next_since`, failure tombstones, history-save diagnostics, diagnostic provider defaults/merging, and redacted diagnostics without falling back to full result-list snapshots on polling, eagerly measuring retained results when an explicit cursor exists, constructor-copying cached markers or incremental result tails, allocating diagnostic provider items views, constructor-copying terminal tombstones, constructor-copying history-save diagnostic defaults/snapshots, repeatedly stripping diagnostic status strings, rebuilding diagnostic/status field tuples, or rebuilding terminal-not-found reason sets per response."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep S04's shipped frontend/render optimization on the shared result-application severity-change gate.",
        seam="browser polling and result application",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "S04 shipped the remaining high-confidence frontend/render follow-up by removing the duplicate broad `flush()` implementation in "
            "`app/static/src/ts/modules/result-application.ts` that always called `updateDashboardCounts()` and `sortCardsBySeverity()`. "
            "The active shared coordinator path now compares each dirty IOC's previous and computed verdict while flushing, so it only runs global dashboard recount/reorder calls when severity-affecting state changes. "
            "Focused proof lives in `app/static/src/ts/modules/result-application.test.ts`: provider-only/no-op deltas preserve summaries, provider rows, copy/detail affordances, and skip global recount/reorder, while severity-changing deltas still update counts and order. "
            "T02 verification also reran the full frontend suite plus mocked-online browser checks for results and EmailRep continuity."
        ),
        continuity_guardrails="R085, R086, R087, R088, R008, R009, R010, R019, D078, D079, D080",
        rerun_lanes="`npm test -- --run app/static/src/ts/modules/result-application.test.ts`; `npm test -- --run`; `python3 -m pytest -q tests/e2e/test_results_page.py tests/e2e/test_emailrep_online.py`; add `make verify-deep` for broader browser-visible polling changes",
        continuity_notes=(
            "S04 is no longer an unresolved target: preserve the severity-change gate, live/history shared coordinator parity, filtering/sorting/copy/export/detail links, "
            "textContent-safe DOM construction, visible enrichment progress/results state, browser-accessible history/detail pages, and deterministic mocked-online browser proof without exposing secrets."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep the shared result-application coordinator on cached per-IOC DOM handles before chasing broader flush-wide render work.",
        seam="frontend/render",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/result-application.ts` now caches each IOC's card, summary row, context line, verdict label, enrichment slot, details panel, section handles, reputation-row count, no-data summary injection state, detail-link injection state, spinner wrapper, pending indicator, copy button, and provider-count total inside `createResultApplicationCoordinator()`. "
            "That lets `apply()`, `flush()`, and `finalize()` reuse stable DOM references instead of repeating `findCardForIoc()` and `.querySelector('.ioc-summary-row')`/`.querySelector('.ioc-context-line')`/`.querySelector('.verdict-label')`/`.querySelector('.enrichment-details')`/`.querySelector('.spinner-wrapper')`/`.querySelector('.enrichment-waiting-text')`/`.querySelector('.no-data-summary-row')` work. "
            "Focused proof lives in `app/static/src/ts/modules/result-application.test.ts::caches stable IOC handles and provider counts across repeated apply, flush, and finalize calls`, which verifies repeated same-IOC results do not repeat summary-row, context-line, verdict-label, spinner, or pending-indicator lookups, finalization does not add another details-panel lookup, and finalization skips the old no-data summary guard query; `skips reputation detail-row sorting while an IOC has only one reputation row`; `app/static/src/ts/modules/row-factory.test.ts::reuses cached summary row and details handles when provided`; and `CTX-01: reuses a cached context line when provided`. "
            "`finalize walks cached IOC values without allocating a Map values iterator` also patches `Map.prototype.values` to fail while preserving detail-link injection, avoiding a `Map.values()` iterator, and proving repeated finalization does not repeat `.detail-link-footer` lookup."
        ),
        continuity_guardrails="R008, R009, R010, R019, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/result-application.test.ts app/static/src/ts/modules/row-factory.test.ts`; `make verify-fast`",
        continuity_notes=(
            "The shipped coordinator-local cache retired repeated card/summary-row/context-line/verdict-label/slot/details/spinner/pending-indicator/no-data-summary lookups. "
            "Preserve live/history parity, textContent-only DOM construction, expand toggles, export/copy/detail-link wiring, severity-change gating, and dynamic summary/no-data behavior while avoiding repeated coordinator-local DOM rediscovery."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep live polling progress updates on cached progress element handles.",
        seam="browser polling and result application",
        evidence_kind="DOM lookup proof + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/enrichment.ts::init()` now captures the progress fill/text elements once for a live results page and passes those handles into `updateProgressBar()` on each poll, instead of re-querying the same IDs for every status payload. "
            "Focused proof lives in `app/static/src/ts/modules/enrichment.test.ts`, where `document.getElementById` is spied during a running poll and the progress fill/text IDs are each read only once while the progress text still updates."
        ),
        continuity_guardrails="R008, R010, R019, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/enrichment.test.ts`; `make verify-fast`; add `make verify-deep` for broader browser-visible polling changes",
        continuity_notes=(
            "Preserve live-owner gating, polling cadence, progress text/fill behavior, retry/terminal failure handling, export enablement, and shared result application while avoiding repeated progress-node DOM lookups per poll."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep summary-row expand toggles on cached details-panel lookups.",
        seam="frontend/render",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/enrichment.ts::wireExpandToggles()` now keeps a per-wired-root `WeakMap` from `.ioc-summary-row` to its `.enrichment-details` panel, so repeated click/keyboard toggles reuse the details handle instead of rediscovering the slot and querying the panel every time. "
            "Focused proof lives in `app/static/src/ts/modules/enrichment.test.ts::caches details panel lookups across repeated summary-row toggles`, which toggles the same summary row twice and verifies the slot performs only one `.enrichment-details` lookup while preserving aria-expanded and open/closed state."
        ),
        continuity_guardrails="R008, R009, R010, R019, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/enrichment.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve delegated click/keyboard expand behavior, dynamic summary-row support for live/history rendering, aria-expanded updates, and details-panel open state while avoiding repeated per-toggle DOM rediscovery."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep live warning banners on a cached warning element handle.",
        seam="frontend/render",
        evidence_kind="DOM lookup proof + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/enrichment.ts::init()` now captures `#enrich-warning`, `#enrich-progress`, `#export-btn`, and `#export-dropdown` once for the live results page, reuses the already-cached progress text handle, and passes those handles into provider warning, terminal-warning, completion, terminal-failure, and `initExportButton()` rendering. "
            "Focused proof lives in `app/static/src/ts/modules/enrichment.test.ts::reuses the warning banner handle across repeated provider warnings`, which returns two warning-producing provider errors in one complete payload, verifies `document.getElementById('enrich-warning')` and `document.getElementById('enrich-progress')` are each called once, verifies `#export-btn` and `#export-dropdown` are each looked up once during init-time export wiring, and verifies completion does not add another `export-btn` lookup while the final warning remains visible."
        ),
        continuity_guardrails="R008, R009, R010, R019, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/enrichment.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve rate-limit/auth warning copy, terminal failure banners, live-owner polling behavior, and export/progress completion while avoiding repeated warning/progress/export DOM lookups per payload."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep summary-row cached timestamp selection on a single-pass oldest lookup.",
        seam="browser polling and result application",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/row-factory.ts::oldestCachedAt()` now finds the oldest cached timestamp in one pass instead of filtering, mapping, and sorting cached entries. "
            "Focused proof lives in `app/static/src/ts/modules/row-factory.test.ts`, where the cached timestamp helper returns the oldest value while `Array.prototype.sort` is patched to fail."
        ),
        continuity_guardrails="R008, R009, R010, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/row-factory.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve staleness badge semantics, textContent-only DOM construction, and summary-row rendering while avoiding unnecessary cached-entry array work."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep inline context snippet formatting on direct string construction.",
        seam="browser polling and result application",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/row-factory.ts::formatAsnContext()` and `formatDnsAContext()` now build ASN and DNS inline context strings directly instead of using temporary arrays with `push()`, `slice()`, `filter()`, and `join()`. "
            "`CONTEXT_PROVIDERS` now derives from one readonly context-provider name list instead of carrying the provider list inline at the exported set construction site. "
            "Focused proof lives in `app/static/src/ts/modules/row-factory.test.ts`, where context formatting still preserves ASN/prefix and first-three-string DNS behavior while `Array.prototype.slice`, `Array.prototype.filter`, and `Array.prototype.join` are patched to fail, and the context-provider set source is guarded against inline exported set construction."
        ),
        continuity_guardrails="R008, R009, R010, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/row-factory.test.ts app/static/src/ts/modules/result-application.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve inline IOC card context text, IP Context priority over ASN Intel, DNS A-record first-three-string semantics, context-provider membership, context-provider ordering, and textContent-safe DOM updates while avoiding temporary context arrays and duplicated/inline context-provider list ownership."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep no-data summary insertion on direct child scanning.",
        seam="browser polling and result application",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/row-factory.ts::injectSectionHeadersAndNoDataSummary()` now scans direct no-data section children once, counting no-data rows and remembering the first insertion anchor instead of allocating a `querySelectorAll()` NodeList. "
            "Focused proof lives in `app/static/src/ts/modules/row-factory.test.ts`, where the no-data section's `querySelectorAll()` is patched to fail while summary count text and insertion still work."
        ),
        continuity_guardrails="R008, R009, R010, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/row-factory.test.ts app/static/src/ts/modules/result-application.test.ts app/static/src/ts/modules/history.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve no-data summary text, insertion before the first no-data row, click/keyboard expansion, accessibility attributes, and live/history rendering while avoiding per-slot NodeList allocation."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep summary attribution provider selection on a single-pass best-candidate scan.",
        seam="browser polling and result application",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/verdict-compute.ts::computeAttribution()` now chooses the highest-detail provider with a single scan instead of filtering candidates and sorting a copied array. "
            "Focused proof lives in `app/static/src/ts/modules/verdict-compute.test.ts`, where attribution still honors total-engine priority and severity tie-breaks while `Array.prototype.sort` is patched to fail."
        ),
        continuity_guardrails="R008, R010, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/verdict-compute.test.ts app/static/src/ts/modules/row-factory.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve summary attribution text, no-data/error exclusion, total-engine priority, and severity tie-break behavior while avoiding candidate array allocation and sorting."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep summary worst-verdict computation on a single-pass scan.",
        seam="browser polling and result application",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/verdict-compute.ts::computeWorstVerdict()` now handles `known_good` override and severity tracking in one pass instead of doing an upfront `some()` scan before `findWorstEntry()`. "
            "Focused proof lives in `app/static/src/ts/modules/verdict-compute.test.ts`, where worst-verdict selection still preserves known-good override and malicious severity while `Array.prototype.some` is patched to fail."
        ),
        continuity_guardrails="R008, R010, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/verdict-compute.test.ts app/static/src/ts/modules/row-factory.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve known-good override, no-data fallback, and severity ordering while avoiding the extra pre-scan on every summary verdict computation."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep exported worst-entry lookup on cached severity and malicious short-circuiting.",
        seam="browser polling and result application",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/verdict-compute.ts::findWorstEntry()` now caches the current worst severity instead of recomputing it each iteration, and returns immediately once `malicious` is found. "
            "Focused proof lives in `app/static/src/ts/modules/verdict-compute.test.ts`, where a later row throws if inspected after a malicious verdict."
        ),
        continuity_guardrails="R008, R010, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/verdict-compute.test.ts app/static/src/ts/modules/row-factory.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve exported worst-entry behavior, first-entry tie behavior, and severity ordering while avoiding redundant severity lookups after the maximum verdict is known."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep result-application severity detection on per-dirty IOC comparison.",
        seam="browser polling and result application",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/result-application.ts::flush()` now accumulates a severity-changed flag from `flushIoc()` instead of building before/after arrays from whole-grid `.ioc-card` queries. "
            "Focused proof lives in `app/static/src/ts/modules/result-application.test.ts`, where a severity-changing flush still triggers dashboard recount/reorder while `Document.prototype.querySelectorAll` records no `.ioc-card` snapshot scan from the coordinator."
        ),
        continuity_guardrails="R008, R009, R010, R019, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/result-application.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve the severity-change gate, live/history shared coordinator parity, and dashboard recount/reorder behavior while avoiding two whole-grid verdict snapshots on every dirty flush."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep provider-count metadata parsing cached by raw DOM value.",
        seam="browser polling and result application",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/types/ioc.ts::getProviderCounts()` now caches parsed `data-provider-counts` metadata by raw attribute value, so repeated coordinator setup for the same results surface does not re-run `JSON.parse()`. "
            "`verdictSeverityIndex()` still uses the shared prebuilt severity map, but that map is now populated with an indexed loop instead of allocating `VERDICT_SEVERITY.map(...)` entries at module load. "
            "Focused proof lives in `app/static/src/ts/types/ioc.test.ts`, where repeated reads parse once, changed raw metadata reparses, malformed metadata fallback is cached for the same raw value, and severity ordering is guarded against array-map lookup construction."
        ),
        continuity_guardrails="R008, R010, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/types/ioc.test.ts app/static/src/ts/modules/result-application.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve provider-count fallback values, dynamic DOM metadata overrides, malformed JSON fallback behavior, result-application pending-count semantics, and verdict severity ordering while avoiding repeated provider-count JSON parsing for unchanged metadata and module-load severity entry mapping."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep provider detail-row sorting on cached severity keys.",
        seam="browser polling and result application",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/shared-rendering.ts::sortDetailRows()` now decorates each provider row with its severity once before sorting instead of reading `data-verdict` and recomputing severity inside every comparator call. "
            "The decoration pass now walks the row NodeList with an indexed loop instead of allocating through `Array.from(...).map(...)`. "
            "Focused proof lives in `app/static/src/ts/modules/shared-rendering.test.ts`, where four rows sort into severity order with exactly four `data-verdict` reads, and row sorting still works when `Array.from` is patched to fail."
        ),
        continuity_guardrails="R008, R009, R010, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/shared-rendering.test.ts app/static/src/ts/modules/result-application.test.ts app/static/src/ts/modules/history.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve provider detail-row severity order and live/history shared rendering behavior while avoiding comparator-amplified DOM attribute reads and extra row decoration array passes."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep export dropdown actions on one delegated listener.",
        seam="browser polling and result application",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/shared-rendering.ts::initExportButton()` now installs one delegated click handler on the export dropdown instead of querying `[data-export]` buttons and attaching one listener per action. "
            "Focused proof lives in `app/static/src/ts/modules/shared-rendering.test.ts`, where the dropdown's `querySelectorAll()` is patched to fail while nested JSON, CSV, and copy-all clicks still call the expected export helpers."
        ),
        continuity_guardrails="R008, R009, R010, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/shared-rendering.test.ts app/static/src/ts/modules/result-application.test.ts app/static/src/ts/modules/history.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve live/history export wiring, dropdown close behavior, nested button clicks, JSON/CSV downloads, and copy-all IOC behavior while avoiding per-action listener attachment."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep IOC card sorting on cached severity keys.",
        seam="browser polling and result application",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/cards.ts::sortCardsBySeverity()` now decorates each IOC card with its severity once before sorting instead of reading `data-verdict` and recomputing severity inside every comparator call. "
            "The decoration pass now walks the card NodeList with an indexed loop instead of allocating through `Array.from(...).map(...)`, and the final append pass also uses an indexed loop instead of array callback iteration. "
            "Focused proof lives in `app/static/src/ts/modules/cards.test.ts`, where four cards sort into severity order with exactly four `data-verdict` reads after the debounced sort fires, card sorting still works when `Array.from` is patched to fail, and the module source is guarded against `.forEach(` regressions."
        ),
        continuity_guardrails="R008, R010, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/cards.test.ts app/static/src/ts/modules/result-application.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve dashboard card ordering and the debounced sort behavior while avoiding comparator-amplified DOM attribute reads and extra card decoration array passes."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep card verdict label updates on the shared classList helper.",
        seam="browser polling and result application",
        evidence_kind="refactor proof + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/cards.ts::applyCardVerdict()` now centralizes card `data-verdict`, label class, and label text updates for both direct card updates and shared result application. "
            "The helper uses `classList.remove()`/`classList.add()` for known verdict classes instead of rebuilding `className` with `split().filter().join()`. "
            "Focused proof lives in `app/static/src/ts/modules/cards.test.ts`, where verdict-label updates preserve unrelated classes and assert the classList calls."
        ),
        continuity_guardrails="R008, R009, R010, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/cards.test.ts app/static/src/ts/modules/result-application.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve card data-verdict updates, visible verdict labels, unrelated CSS classes, and shared live/history result-application behavior while removing duplicated string-based class rebuilding."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep filter applications on cached static node lists.",
        seam="browser polling and result application",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/filter.ts::init()` now captures the static IOC cards, verdict buttons, and type pills once instead of re-querying those node lists on every verdict/type/search filter application. "
            "Filter setup and application now walk those NodeLists with indexed loops instead of `NodeList.prototype.forEach()` callbacks. "
            "Focused proof lives in `app/static/src/ts/modules/filter.test.ts`, where verdict click, type click, dashboard-badge click, and debounced search filtering preserve visible card and active-control behavior without additional `querySelectorAll` calls after init, and with `NodeList.prototype.forEach` patched to fail."
        ),
        continuity_guardrails="R008, R009, R010, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/filter.test.ts app/static/src/ts/modules/enrichment.test.ts app/static/src/ts/modules/history.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve verdict, type, search, and dashboard filter behavior while avoiding repeated static selector scans and callback iteration during every filter application."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep card stagger initialization on indexed NodeList iteration.",
        seam="browser polling and result application",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/ui.ts::initCardStagger()` now applies capped `--card-index` values with an indexed `NodeList` loop instead of allocating a `forEach()` callback during page-load UI setup. "
            "Focused proof lives in `app/static/src/ts/modules/ui.test.ts`, where stagger indexes still cap at 15 while `NodeList.prototype.forEach` is patched to fail, and scroll-aware filter bar behavior remains covered."
        ),
        continuity_guardrails="R008, R009, R010, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/ui.test.ts app/static/src/ts/modules/main.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve card stagger CSS variable values, the 15-index cap, scroll-aware filter-bar class toggling, and main page-load initialization while avoiding callback iteration for static card setup."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep copy-button handling on one delegated listener.",
        seam="browser polling and result application",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/clipboard.ts::init()` now installs one document-level delegated click handler instead of attaching a click listener to every `.copy-btn` at initialization. "
            "Focused proof lives in `app/static/src/ts/modules/clipboard.test.ts`, where one listener handles an existing nested click target plus a later-added copy button, and repeated `init()` calls do not duplicate clipboard writes."
        ),
        continuity_guardrails="R008, R009, R010, R040, R085",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/clipboard.test.ts app/static/src/ts/modules/export.test.ts app/static/src/ts/modules/result-application.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve copy text, enrichment suffixes, nested button clicks, copied feedback, export clipboard reuse, and dynamic result/history buttons while avoiding per-button listener attachment."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep form initialization on shared element lookups.",
        seam="browser polling and result application",
        evidence_kind="refactor proof + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/form.ts::init()` now gathers the index form's textarea, submit button, clear button, and mode-toggle nodes once and passes them into submit, auto-grow, and mode-toggle helpers instead of letting each helper repeat document lookups. "
            "Focused proof lives in `app/static/src/ts/modules/form.test.ts`, where form mode, submit enablement, and missing-markup behavior remain covered while `document.querySelector()` calls for `#ioc-text`, `#submit-btn`, and `#mode-input` are each asserted once."
        ),
        continuity_guardrails="R008, R009, R010, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/form.test.ts app/static/src/ts/modules/main.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve submit enablement, clear behavior, textarea auto-grow, paste feedback, mode toggle state synchronization, and missing-markup fail-fast behavior while avoiding repeated static form selector lookups."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep settings accordion updates on cached header references.",
        seam="browser polling and result application",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/settings.ts::initAccordion()` now caches each settings section's accordion header during initialization and reuses those references when expanding a section. "
            "Accordion record setup and expansion now use indexed loops instead of array `forEach()` callbacks. "
            "Focused proof lives in `app/static/src/ts/modules/settings.test.ts`, where accordion clicks preserve one-open-section behavior without any post-init `querySelector()` calls from the click path, API key visibility toggling remains covered, and the module source is guarded against `.forEach(` regressions."
        ),
        continuity_guardrails="R008, R009, R010, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/settings.test.ts app/static/src/ts/modules/main.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve settings accordion aria-expanded state, one-open-provider behavior, and API key show/hide toggles while avoiding repeated section-header selector work and callback iteration on every accordion expansion."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep settings initialization on one section query.",
        seam="browser polling and result application",
        evidence_kind="refactor proof + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/settings.ts::init()` now queries `.settings-section` once and passes that NodeList to accordion and API key toggle setup instead of querying provider sections and all sections separately. "
            "Settings section setup now walks that NodeList with indexed loops instead of iterator/callback-based passes. "
            "Focused proof lives in `app/static/src/ts/modules/settings.test.ts`, where accordion and API key toggles still work while `document.querySelectorAll()` observes exactly one `.settings-section` query, no `.settings-section[data-provider]` query, and the module source is guarded against `.forEach(` regressions."
        ),
        continuity_guardrails="R008, R009, R010, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/settings.test.ts app/static/src/ts/modules/main.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve settings accordion behavior, provider-only accordion wiring, API key show/hide toggles, and main init dispatch while avoiding duplicated settings-section selector scans and callback iteration."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep dashboard verdict-count updates on one count-element query.",
        seam="browser polling and result application",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/cards.ts::updateDashboardCounts()` now scans `[data-verdict-count]` elements once instead of issuing one dashboard `querySelector()` per verdict bucket. "
            "It also checks valid dashboard verdict names through a precomputed set instead of scanning the static verdict tuple for every count element. "
            "The card and count-element NodeLists are walked with indexed loops instead of `NodeList.prototype.forEach()` callbacks on each recount. "
            "Focused proof lives in `app/static/src/ts/modules/cards.test.ts`, where dashboard counts update correctly while the dashboard performs one count-element query, no per-verdict `querySelector()` calls, no `Array.prototype.includes()` membership scans, and `NodeList.prototype.forEach` is patched to fail."
        ),
        continuity_guardrails="R008, R010, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/cards.test.ts app/static/src/ts/modules/result-application.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve dashboard count semantics for malicious, suspicious, clean, known_good, and no_data while reducing repeated selector, membership-scan, and callback-iteration work during recounts."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep frontend export text construction on direct string accumulation.",
        seam="browser polling and result application",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/export.ts::buildCSV()` now builds the CSV output directly instead of pushing every row into an intermediate array and joining it after the loop. "
            "The static CSV header is now a literal string instead of a module-load columns-array join, and CSV raw-stat array fields are also formatted without `Array.prototype.join()`. "
            "`buildIocListText()` and `buildIocListTextFromResults()` also build copy-all IOC text directly while sharing one deduplicated append helper, and `copyAllIOCs()` now accepts the accumulated export results from `initExportButton()` so the live/history dropdown copy action does not rescan `.ioc-card` DOM. "
            "Focused proof lives in `app/static/src/ts/modules/export.test.ts`, where the source is guarded against `CSV_COLUMNS.join`, duplicated copy-text append branches, CSV formatting and IOC copy text still preserve behavior while `Array.prototype.push` and `Array.prototype.join` are patched to fail, and result-backed IOC copy text is guarded against `document.querySelectorAll()` scans."
        ),
        continuity_guardrails="R008, R010, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/export.test.ts app/static/src/ts/modules/history.test.ts app/static/src/ts/modules/enrichment.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve CSV column order, result-only export behavior, raw-stat extraction, quote escaping, copy-all deduplication, and live/history export wiring while avoiding module-load header joins, row-array, array-field join, IOC-value array allocations, duplicated copy-text append branches, and copy-action card DOM scans proportional to exported results."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep IOC detail graph setup on single-pass node indexing.",
        seam="browser polling and result application",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/static/src/ts/modules/graph.ts::renderRelationshipGraph()` now splits IOC/provider nodes in one pass and builds the provider index map directly instead of using `filter()`, `find()`, and `providerNodes.map()` setup passes. "
            "Provider node drawing also uses indexed iteration instead of callback iteration, literal empty graph-node payloads now return the empty state before calling `JSON.parse()`, and literal empty graph-edge payloads skip edge JSON parsing while preserving SVG rendering. "
            "Focused proof lives in `app/static/src/ts/modules/graph.test.ts`, where the renderer still creates the SVG graph and empty state while `Array.prototype.filter`, `Array.prototype.find`, `Array.prototype.map`, and `Array.prototype.forEach` are patched to fail, where an empty-node graph payload patches `JSON.parse` to fail while preserving the empty state, and where an empty-edge graph payload makes `JSON.parse('[]')` fail while still rendering a graph with zero edge lines."
        ),
        continuity_guardrails="R008, R009, R010, R040",
        rerun_lanes="`npx vitest run app/static/src/ts/modules/graph.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve IOC detail relationship graph rendering, text-node-safe labels, malformed-data empty state, empty graph-node payload empty state, empty graph-edge payload rendering, and provider edge coloring while avoiding extra graph-node array passes, callback iteration during provider drawing, and empty graph-node/edge JSON parsing."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep browser-route provider-count metadata on the direct count path.",
        seam="request/status",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/routes/analysis.py::_provider_counts_json()` now builds result-page provider-count metadata with a direct accumulator and `registry.provider_count_for_type()` instead of allocating a dict-comprehension frame or provider lists with `providers_for_type()` for every IOC type. "
            "`app/enrichment/registry.py::ProviderRegistry.registered_count()` returns the registered provider count directly, and `_provider_coverage()` now uses that count with the caller's configured-provider list instead of copying all registered providers for coverage metadata. "
            "Focused proof lives in `tests/test_routes.py::test_provider_counts_metadata_uses_direct_count_path`, which fails if provider-count metadata falls back to `providers_for_type()` or a dict-comprehension frame, `tests/test_routes.py::test_provider_coverage_reuses_configured_provider_list`, which fails if coverage allocates all providers or rereads configured providers, and `tests/test_provider_registry.py::TestRegistryRegister::test_registered_count_does_not_allocate_provider_list`, which fails if the direct count path delegates to `all()`."
        ),
        continuity_guardrails="R008, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_routes.py::test_provider_counts_metadata_uses_direct_count_path tests/test_routes.py::test_provider_coverage_reuses_configured_provider_list tests/test_routes.py::test_analyze_online_with_api_key_returns_job_id tests/test_routes.py::test_enrichable_count_multi_provider tests/test_routes.py::test_enrichable_count_domain_two_providers tests/test_provider_registry.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve result-page provider-count JSON, enrichable progress counts, provider coverage metadata, and online admission behavior while avoiding count-only provider list allocation, registered-provider list copies for coverage counts, and dict-comprehension frame creation on the fixed IOC-type metadata walk."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep Online fanout admission diagnostics on the direct count path.",
        seam="request/status",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/routes/_helpers.py::_online_fanout_diagnostics()` now caches `registry.provider_count_for_type()` per IOC type while computing dispatch limits instead of allocating provider lists with `providers_for_type()`. "
            "`app/routes/_helpers.py::_online_limits_from_config()` now centralizes Online admission limit reads so HTML and JSON analyze routes do not duplicate the same Flask config parsing. "
            "Focused proof lives in `tests/test_routes.py::test_online_fanout_diagnostics_uses_direct_count_path`, which verifies duplicate IOC types reuse one count lookup and fail if diagnostics call `providers_for_type()`, plus `tests/test_routes.py::test_analyze_online_uses_shared_limit_config_helper` and `tests/test_api.py::TestApiAnalyzeOnline::test_online_uses_shared_limit_config_helper`, which prove both route surfaces use the shared limit helper while preserving rejection behavior."
        ),
        continuity_guardrails="R008, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_routes.py::test_online_fanout_diagnostics_uses_direct_count_path tests/test_routes.py::test_analyze_online_rejects_ioc_limit_before_launch tests/test_routes.py::test_analyze_online_uses_shared_limit_config_helper tests/test_routes.py::test_analyze_online_rejects_dispatch_limit_before_launch tests/test_api.py::TestApiAnalyzeOnline::test_online_with_provider tests/test_api.py::TestApiAnalyzeOnline::test_online_rejects_ioc_limit_before_launch tests/test_api.py::TestApiAnalyzeOnline::test_online_uses_shared_limit_config_helper tests/test_api.py::TestApiAnalyzeOnline::test_online_rejects_dispatch_limit_before_launch tests/test_provider_registry.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve Online IOC and dispatch limit diagnostics, secret-free admission responses, HTML/API limit parity, and background-work rejection behavior while avoiding count-only provider list allocation and duplicated online-limit config parsing."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep browser-route enrichable progress totals on cached provider counts by IOC type.",
        seam="request/status",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/routes/analysis.py::_enrichable_count()` now caches `registry.provider_count_for_type()` results by IOC type while summing progress totals, so repeated IOC types do not repeat the same registry count after admission succeeds. "
            "The browser online route now reuses `_online_fanout_diagnostics()`' already-computed `dispatch_count` for the template `enrichable_count`, avoiding a second progress-total pass after admission. "
            "Focused proof lives in `tests/test_routes.py::test_enrichable_count_caches_provider_counts_by_ioc_type`, which verifies two IPv4 IOCs and one domain still produce the per-IOC fanout total while calling the registry count path once per type and never allocating provider lists, and `test_analyze_online_reuses_fanout_dispatch_count_for_progress_total`, which verifies the route progress total comes from the admission fanout."
        ),
        continuity_guardrails="R008, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_routes.py::test_enrichable_count_caches_provider_counts_by_ioc_type tests/test_routes.py::test_analyze_online_reuses_fanout_dispatch_count_for_progress_total tests/test_routes.py::test_analyze_online_with_api_key_returns_job_id tests/test_routes.py::test_enrichable_count_multi_provider tests/test_routes.py::test_enrichable_count_domain_two_providers`; `make verify-fast`",
        continuity_notes=(
            "Preserve browser online progress totals, per-IOC fanout semantics, background enrichment launch behavior, provider metadata, and online admission guard behavior while avoiding repeated same-type provider-count scans and the post-admission recount."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep online route configured-provider reads single-use across admission, coverage, and launch.",
        seam="request/status",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/routes/analysis.py::analyze()` and `app/routes/api.py::api_analyze()` now store the configured-provider list read for the online admission gate and pass it through `_provider_coverage()` and `_setup_orchestrator()` instead of calling `registry.configured()` again for display metadata and orchestrator construction. "
            "The browser and API online routes also skip provider configuration, admission diagnostics, and background launch setup when extraction returns zero IOCs. "
            "Focused proof lives in `tests/test_routes.py::test_provider_coverage_reuses_configured_provider_list`, `test_analyze_online_creates_all_three_adapters`, and `tests/test_api.py::TestApiAnalyzeOnline::test_online_with_provider`, which preserve launch behavior while proving configured providers are read once on the accepted route path; `tests/test_routes.py::test_analyze_online_no_iocs_skips_enrichment_setup` and `tests/test_api.py::TestApiAnalyzeOffline::test_online_no_iocs_skips_enrichment_setup` prove zero-IOC online requests do not touch provider setup."
        ),
        continuity_guardrails="R008, R010, R014, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_routes.py::test_provider_coverage_reuses_configured_provider_list tests/test_routes.py::test_analyze_online_creates_all_three_adapters tests/test_routes.py::test_analyze_online_no_iocs_skips_enrichment_setup tests/test_api.py::TestApiAnalyzeOnline::test_online_with_provider tests/test_api.py::TestApiAnalyzeOffline::test_online_no_iocs_skips_enrichment_setup`; `make verify-fast`",
        continuity_notes=(
            "Preserve no-provider rejection, Online admission limits, browser provider coverage metadata, API/browser background launch behavior, adapter list identity, and no-results responses while avoiding repeated configured-provider list allocation per accepted online request and zero-work online setup."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep API health registry detail on direct registry count paths.",
        seam="request/status",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/enrichment/registry.py::ProviderRegistry.configured_count()` now counts configured providers directly, and `app/routes/api.py::_registry_health_detail()` combines `registry.configured_count()` with `registry.registered_count()` instead of allocating registered or configured provider lists for `/api/health` count-only metadata. "
            "Focused proof lives in `tests/test_api.py::TestApiHealth::test_health_touches_only_aggregate_provider_configuration`, which preserves the health detail text while failing if the route asks for registered or configured provider lists, plus `tests/test_provider_registry.py::TestRegistryConfigured::test_configured_count_does_not_allocate_provider_list`, which fails if the direct configured count delegates to `configured()`."
        ),
        continuity_guardrails="R009, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_api.py::TestApiHealth tests/test_provider_registry.py::TestRegistryConfigured::test_configured_count_does_not_allocate_provider_list`; `make verify-fast`",
        continuity_notes=(
            "Preserve `/api/health` schema, secret-free degraded dependency handling, registry detail text, and health payload ordering while avoiding provider-list allocations for count-only registry health metadata."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep health payload ordering and validation key sets precomputed.",
        seam="request/status",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/health_contract.py::HEALTH_CHECK_ORDER` now defines the stable cache/history/registry check order as a literal tuple, and `build_health_payload()` iterates that tuple instead of sorting `HEALTH_CHECKS` on every health request or paying import-time sorted-list allocation. "
            "`HEALTH_PAYLOAD_KEYS`, `HEALTH_CHECK_VALUE_KEYS`, and `HEALTH_STATUSES` also let build/validation paths reuse precomputed frozensets instead of allocating validation or allowed-status sets per call. "
            "Validation now reuses `HEALTH_CHECK_ORDER` for per-check validation instead of creating a `checks.values()` view after the exact key set is already known. "
            "`app/text_utils.py::has_non_whitespace()` gives health and analyze routes a shared direct scanner for string presence checks, and `build_health_payload()` uses it instead of allocating stripped detail strings for every non-empty dependency detail. "
            "Focused proof lives in `tests/test_api.py::TestApiHealth::test_health_contract_constants_stay_secret_free`, which guards the literal order and tuple-backed status-set shape, plus `test_health_payload_uses_precomputed_check_order`, `test_health_payload_validation_uses_precomputed_key_sets`, `test_health_payload_uses_precomputed_status_set`, and `test_health_payload_detail_presence_skips_strip_allocation`, which patch `builtins.sorted` and `builtins.set`, make `checks.values()` fail, guard against status set-literal regressions, and make detail `.strip()` fail while preserving the secret-free health payload schema and whitespace-only fallback."
        ),
        continuity_guardrails="R009, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_api.py::TestApiHealth`; `make verify-fast`",
        continuity_notes=(
            "Preserve `/api/health` schema, check names, deterministic check order, degraded status handling, whitespace-only detail fallback, and secret-free error details while avoiding import-time/request-time sorting, validation set allocation, allowed-status set allocation, values-view scans, and stripped-string allocation on health payload paths."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep shared contract frozensets on tuple inputs.",
        seam="request/status",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "Shared static membership tables in `app/health_contract.py`, `app/diagnostics/contract.py`, `app/diagnostics/assembler.py`, and `app/diagnostics/redaction.py` now call `frozenset((...))` instead of `frozenset({...})`, avoiding temporary set-literal allocation during module import while preserving immutable membership checks. "
            "Diagnostic source-record status groups and archive dot-segment validation now also reuse static frozensets instead of rebuilding tiny membership sets during record normalization or path validation. "
            "Focused proof lives in `tests/test_api.py::TestApiHealth::test_health_contract_constants_stay_secret_free`, `tests/test_diagnostic_export_contract.py::test_contract_static_frozensets_avoid_temporary_set_literals` and `test_source_record_status_groups_are_static_frozensets`, `tests/test_diagnostic_export_assembler.py::test_archive_entry_order_uses_explicit_extension` and `test_archive_path_dot_segments_use_static_membership_set`, and `tests/test_diagnostic_redaction.py::test_redaction_static_frozensets_avoid_temporary_set_literals`, which guard those modules against inline or whitespace-separated `frozenset({` regressions and per-call static-membership set construction while the existing schema, archive, and redaction tests preserve behavior."
        ),
        continuity_guardrails="R009, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_api.py::TestApiHealth tests/test_diagnostic_export_contract.py tests/test_diagnostic_export_assembler.py tests/test_diagnostic_redaction.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve health schema validation, diagnostic source status/category validation, source-record omitted/error normalization, forbidden archive path checks, and redaction header-key membership while avoiding temporary set-literal allocation for shared static membership tables and per-call diagnostic status/path membership checks."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep API analyze IOC serialization and grouping on one pass.",
        seam="request/status",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/routes/api.py::api_analyze()` now serializes each IOC once while building the top-level `iocs` array and grouped summary in the same loop, avoiding a separate `group_by_type()` pass and identity-map lookup pass. "
            "The route now defers that serialization until after online missing-provider and fanout-limit rejection paths, so rejected online requests do not build unused IOC response payloads. "
            "`api_analyze()` also uses the shared direct non-whitespace scanner for request text validation instead of allocating a stripped copy just to reject empty input. "
            "Focused proof lives in `tests/test_api.py::TestApiAnalyzeOffline::test_groups_serialized_iocs_in_one_pass`, which monkeypatches `_serialize_ioc()` and proves each IOC is serialized once in response order while preserving grouped output, `tests/test_api.py::TestApiAnalyzeOnline::test_online_no_providers_skips_ioc_serialization`, which proves the missing-provider rejection returns before IOC serialization, and `tests/test_api.py::TestApiAnalyzeValidation::test_api_analyze_uses_shared_text_presence_check`, which proves API analyze validation is wired through the shared text presence helper."
        ),
        continuity_guardrails="R008, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_api.py::TestApiAnalyzeOffline::test_groups_serialized_iocs_in_one_pass tests/test_api.py::TestApiAnalyzeOnline::test_online_no_providers_skips_ioc_serialization tests/test_api.py::TestApiAnalyzeOffline::test_extracts_ipv4 tests/test_api.py::TestApiAnalyzeOffline::test_returns_grouped`; `make verify-fast`",
        continuity_notes=(
            "Preserve API analyze JSON shape, top-level IOC order, grouped response semantics, online rejection payloads, whitespace-only text rejection, and secret-free fanout-limit responses while avoiding duplicate IOC serialization, unused rejected-request payload work, and stripped-string allocation for request text presence checks."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep browser analyze IOC grouping on a route-local pass.",
        seam="request/status",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/routes/analysis.py::analyze()` now builds grouped template IOC data with `_group_iocs_for_template()` instead of routing extracted IOCs through the generic `group_by_type()` helper. "
            "The route now defers that grouping until after the online missing-provider redirect, so rejected online requests do not build unused template grouping data. "
            "`analyze()` also uses the shared direct non-whitespace scanner for form text validation instead of allocating a stripped copy just to reject empty input. "
            "Focused proof lives in `tests/test_routes.py::test_analyze_groups_template_iocs_without_group_by_type`, which preserves rendered offline results while failing if the old grouping helper is reintroduced, `tests/test_routes.py::test_analyze_online_without_api_key_skips_template_grouping`, which proves the missing-provider redirect returns before template grouping, and `tests/test_routes.py::test_analyze_uses_shared_text_presence_check`, which proves browser analyze validation is wired through the shared text presence helper."
        ),
        continuity_guardrails="R008, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_routes.py::test_analyze_groups_template_iocs_without_group_by_type tests/test_routes.py::test_analyze_online_without_api_key_skips_template_grouping tests/test_routes.py::test_analyze_groups_by_type tests/test_routes.py::test_analyze_with_valid_input`; `make verify-fast`",
        continuity_notes=(
            "Preserve browser analyze template grouping, top-level result count, no-results behavior, whitespace-only text rejection, online admission flow, missing-provider redirect behavior, and rendered IOC ordering while keeping grouping local to the route and avoiding unused rejected-request grouping plus stripped-string allocation for request text presence checks."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep history reload IOC reconstruction, grouping, and empty replay serialization lean.",
        seam="request/status",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/routes/history.py::_group_history_iocs()` now rebuilds persisted IOC models and groups them by type in one loop instead of first allocating a full IOC list and then rescanning it with `group_by_type()`. "
            "`app/routes/history.py::history_detail()` now checks `total_count` before rebuilding persisted IOC template data, so empty history reloads skip the grouping helper entirely. "
            "`app/routes/history.py::_history_results_json()` returns the shared literal empty replay payload for empty result lists instead of invoking the JSON encoder on the no-results history path, and history replay uses a shared empty provider-counts JSON literal for the static metadata attribute. "
            "`app/static/src/ts/modules/history.ts::init()` also recognizes that literal empty replay payload and marks history replay complete without calling `JSON.parse()`, while parsed history replay captures `#enrich-progress`, `#enrich-progress-text`, `#export-btn`, and `#export-dropdown` once and reuses those handles for completion and `initExportButton()` wiring. "
            "Focused proof lives in `tests/test_history_routes.py::TestHistoryDetailRoute::test_history_groups_iocs_while_rebuilding_models`, which preserves the rendered history detail page while failing if the old second-pass grouping helper is reintroduced, `tests/test_history_routes.py::TestHistoryDetailRoute::test_empty_history_skips_ioc_grouping`, which fails if empty history reloads rebuild unused IOC template data, `tests/test_history_routes.py::TestHistoryDetailRoute::test_empty_history_results_skip_json_dumps`, which fails if empty replay serialization calls `json.dumps()`, and `app/static/src/ts/modules/history.test.ts`, where empty replay completion keeps export disabled while `JSON.parse` is patched to fail and parsed replay verifies each history completion/export ID is looked up once."
        ),
        continuity_guardrails="R008, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_history_routes.py::TestHistoryDetailRoute::test_history_groups_iocs_while_rebuilding_models tests/test_history_routes.py::TestHistoryDetailRoute::test_empty_history_skips_ioc_grouping tests/test_history_routes.py::TestHistoryDetailRoute::test_empty_history_results_skip_json_dumps tests/test_history_routes.py::TestHistoryDetailRoute::test_history_returns_200_with_seeded_data tests/test_history_routes.py::TestHistoryDetailRoute::test_history_shows_correct_ioc_count`; `npx vitest run app/static/src/ts/modules/history.test.ts`; `make verify-fast`",
        continuity_notes=(
            "Preserve history detail rendering, persisted IOC type/value/raw_match semantics, grouped result-page template input, no-results history rendering, history replay data, empty replay payload shape, empty provider-count metadata shape, empty replay completion state, disabled empty replay export, parsed replay export enablement, and history-owner DOM attributes while avoiding an extra IOC list scan, empty-history IOC grouping, unnecessary empty-result JSON encoding, ad hoc empty provider-count JSON literals, empty replay JSON parsing, and repeated completion/export ID lookups on history reload."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep IOC detail valid-type checks on a precomputed set.",
        seam="request/status",
        evidence_kind="refactor proof + focused regression proof",
        evidence_summary=(
            "`app/routes/detail.py` now precomputes `_VALID_IOC_TYPES` once at module load through a direct helper loop instead of rebuilding `{t.value for t in IOCType}` on every detail-page request. "
            "Empty-cache detail pages now pass literal empty graph payloads instead of allocating an IOC graph node that the frontend will discard into its empty state. "
            "Focused proof lives in `tests/test_ioc_detail_routes.py::TestIocDetailRoute::test_valid_ioc_types_are_precomputed`, which guards the helper against generator/set-comprehension frames, `test_detail_page_empty_cache`, which preserves the empty page while checking the graph payloads stay `[]`, with existing 200/404 route checks preserving valid and invalid type behavior."
        ),
        continuity_guardrails="R008, R010, R040",
        rerun_lanes="`python3 -m pytest -q tests/test_ioc_detail_routes.py::TestIocDetailRoute::test_valid_ioc_types_are_precomputed tests/test_ioc_detail_routes.py::TestIocDetailRoute::test_detail_page_empty_cache tests/test_ioc_detail_routes.py::TestIocDetailRoute::test_detail_invalid_type tests/test_ioc_detail_routes.py::TestIocDetailRoute::test_detail_page_200`; `make verify-fast`",
        continuity_notes=(
            "Preserve IOC detail 200/404 routing semantics, populated provider graph payloads, and empty-cache detail messaging while avoiding repeated valid-type set construction, import-time valid-type generator/comprehension frames, and discarded empty-cache graph node allocation."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep orchestration diagnostic export coercion on bounded iteration.",
        seam="request/status",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/routes/_helpers.py::_coerce_orchestration_diagnostics_for_export()` now uses `itertools.islice()` over top-level and nested diagnostic dict keys, indexes accepted entries directly, and keeps list value caps on bounded iteration instead of materializing bounded copies or allocating dict items views before filtering. "
            "List values are also accumulated with a direct loop instead of a list-comprehension frame. "
            "Focused proof lives in `tests/test_routes.py::test_orchestration_diagnostics_export_coercion_uses_bounded_iteration`, where dict subclasses raise if coercion reads past the documented 40-entry export caps or calls `.items()`, `test_orchestration_diagnostics_export_coercion_does_not_slice_lists`, where a list subclass raises if list coercion slices before applying the 25-entry cap, and `test_orchestration_diagnostics_export_coercion_accumulates_lists_directly`, which guards the list path against `<listcomp>` bytecode."
        ),
        continuity_guardrails="R009, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_routes.py::test_orchestration_diagnostics_export_coercion_uses_bounded_iteration tests/test_routes.py::test_orchestration_diagnostics_export_coercion_does_not_slice_lists tests/test_diagnostic_export_route.py tests/test_diagnostic_export_sources.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve diagnostic export truncation, primitive-only nested/list values, unsupported-value repr fallback, and secret-safe archive assembly while avoiding full diagnostic container materialization, orchestration diagnostic mapping items-view allocation before caps are applied, and list-comprehension frames for diagnostic list values."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep diagnostic source sanitization on bounded mapping and sequence iteration.",
        seam="request/status",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/diagnostics/sources.py::_safe_jsonish()` now uses `itertools.islice()` for diagnostic mapping and sequence caps, and `_safe_mapping()` passes mappings through directly instead of copying them first. "
            "The recursive mapping and sequence normalization paths now accumulate into dicts/lists with direct loops instead of comprehension frames, and mapping caps iterate keys directly instead of allocating `items()` views. "
            "Focused proof lives in `tests/test_diagnostic_export_sources.py::test_safe_mapping_uses_bounded_iteration_for_nested_mappings`, where mapping subclasses raise if sanitization reads past the documented 50-entry caps or calls `.items()`, and `test_safe_jsonish_uses_direct_recursive_loops`, which preserves nested JSON-safe output while guarding `_safe_jsonish()` against `<dictcomp>` and `<listcomp>` bytecode."
        ),
        continuity_guardrails="R009, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_diagnostic_export_sources.py tests/test_diagnostic_export_bundle_integration.py tests/test_diagnostic_export_route.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve diagnostic source shape, recursive depth limits, string/list/dict caps, redaction compatibility, and secret-free archive assembly while avoiding full mapping and sequence materialization before caps are applied, mapping items-view allocation, and recursive comprehension-frame allocation during sanitization."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep recent-history diagnostic payloads on bounded iteration.",
        seam="request/status",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/diagnostics/sources.py::_recent_history_payload()` now uses `itertools.islice()` over the returned history rows instead of slicing a second list after `HistoryStore.list_recent(limit=...)` has already bounded the store query. "
            "It also accumulates safe rows directly instead of allocating a list-comprehension frame around `_safe_jsonish()`. "
            "Focused proof lives in `tests/test_diagnostic_export_sources.py::test_recent_history_payload_uses_bounded_iteration_not_slice`, where a list subclass raises if the payload path slices returned rows while preserving the 10-item export cap, and `test_recent_history_payload_accumulates_without_list_comprehension_frame`, which guards the payload builder against `<listcomp>` bytecode."
        ),
        continuity_guardrails="R009, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_diagnostic_export_sources.py tests/test_diagnostic_export_bundle_integration.py tests/test_diagnostic_export_route.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve recent-history limit propagation, returned_count/items payload shape, safe JSON coercion, and secret-free diagnostic archive behavior while avoiding redundant slice allocation and comprehension-frame allocation on already bounded history rows."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep diagnostic manifest duplicate-source validation single-pass.",
        seam="request/status",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/diagnostics/contract.py::DiagnosticManifest.__post_init__()` now validates duplicate source IDs while normalizing iterable source inputs instead of first materializing one source-id list and one set. "
            "Focused proof lives in `tests/test_diagnostic_export_contract.py::test_manifest_duplicate_source_validation_stops_at_first_duplicate`, where a generator raises if manifest construction reads past the first duplicate source."
        ),
        continuity_guardrails="R009, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_diagnostic_export_contract.py tests/test_diagnostic_export_assembler.py tests/test_diagnostic_export_bundle_integration.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve diagnostic manifest deterministic serialization, duplicate rejection, source tuple normalization, and aggregate counts while avoiding extra duplicate-validation containers and reads past an early duplicate."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep diagnostic safe-error summary whitespace normalization on compiled regex.",
        seam="request/status",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/diagnostics/contract.py::_normalize_error_summary()` now collapses whitespace with a module-level compiled regex instead of `strip().split()` plus `join()`, avoiding a temporary word list on every diagnostic error-source record. "
            "Diagnostic source-record required/optional text normalization now reuses `app/text_utils.py::stripped_bounded_text()` instead of carrying a duplicate local strip/bound helper. "
            "Focused proof lives in `tests/test_diagnostic_export_contract.py::test_safe_error_summary_normalizes_whitespace_without_split_list`, where a string subclass raises if normalization calls `split()` while preserving single-line summary output, and `test_source_record_text_normalization_uses_shared_helper`, which proves source-record text fields are routed through the shared stripped-text helper."
        ),
        continuity_guardrails="R009, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_diagnostic_export_contract.py tests/test_diagnostic_export_assembler.py tests/test_diagnostic_export_bundle_integration.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve diagnostic source error defaults, bounded safe_error_summary truncation, source-record text validation, single-line whitespace normalization, and secret-free manifest output while avoiding split-list allocation for error summaries and duplicate local stripped-text helper logic."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep diagnostic manifest aggregate serialization single-pass.",
        seam="request/status",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/diagnostics/contract.py::DiagnosticManifest` now caches deterministic `sorted_sources` at construction time, and `DiagnosticManifest.to_dict()` computes status counts, redaction totals, and serialized source dictionaries in one pass over that cached order instead of sorting on every serialization or rescanning with multiple `sum()` calls plus a separate source-list pass. "
            "`DiagnosticSourceRecord.to_dict()` now serializes already-normalized redaction labels with direct accumulation instead of constructor-copying the tuple with `list(...)`. "
            "`_normalize_redaction_labels()` also deduplicates labels with direct set accumulation instead of a set-comprehension frame before producing the stable sorted tuple, and skips sorting entirely for zero or one normalized label. "
            "`DiagnosticManifest.__post_init__()` now also skips sorted-source construction for zero or one source while preserving sorted order for multi-source manifests. "
            "Focused proof lives in `tests/test_diagnostic_export_contract.py::test_manifest_reuses_construction_time_sorted_sources`, where `builtins.sorted` is patched after manifest construction while source order and serialization remain deterministic, `test_manifest_construction_skips_sort_for_zero_or_one_source`, where `builtins.sorted` is patched during empty/single-source manifest construction, `test_manifest_serialization_computes_counts_in_one_source_pass`, where `builtins.sum` is patched to fail while aggregate counts and deterministic source ordering are preserved, `test_source_record_serializes_redaction_labels_without_list_constructor`, which guards source-record label serialization against `list(...)` constructor calls, `test_redaction_label_normalization_uses_direct_accumulation`, which preserves label dedupe/order while guarding against `<setcomp>` bytecode, and `test_redaction_label_normalization_skips_sort_for_zero_or_one_label`, where `builtins.sorted` is patched for empty/single-label normalization."
        ),
        continuity_guardrails="R009, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_diagnostic_export_contract.py tests/test_diagnostic_export_assembler.py tests/test_diagnostic_export_bundle_integration.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve diagnostic manifest schema, deterministic source ordering, aggregate counts, redaction totals, redaction-label dedupe/order, and JSON-safe source records while avoiding repeated sorting and repeated scans during manifest serialization, unnecessary empty/single-item sorting during manifest construction and redaction-label normalization, source-record label constructor copies, plus comprehension-frame allocation during label normalization."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep diagnostic bundle source preparation on streaming validation.",
        seam="request/status",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/diagnostics/assembler.py::assemble_diagnostic_bundle()` now passes source iterables directly into `_prepare_sources()`, which validates and normalizes descriptors while consuming them instead of first tuple-materializing every source. "
            "Archive entries now append the manifest first and explicitly extend with sorted payload entries instead of using a starred list-unpack around `sorted(payload_entries)`, and returned archive paths are accumulated directly instead of using a tuple generator expression over the archive entries. "
            "Single-source diagnostic bundles now skip prepared-source and payload-entry sorting entirely while multi-source bundles keep deterministic source/archive ordering. "
            "`DiagnosticBundle.summary` now computes aggregate counts directly from the cached manifest source order instead of calling `DiagnosticManifest.to_dict()` and serializing every source record just to return route/test summary fields. "
            "`app/diagnostics/assembler.py::_json_safe()` now recursively normalizes mappings, tuples, and lists with direct loops instead of dict/list comprehension frames before JSON encoding, and mapping normalization iterates keys directly instead of allocating an `items()` view. "
            "Diagnostic source descriptor required/optional text normalization now also reuses `app/text_utils.py::stripped_bounded_text()` instead of carrying a duplicate local strip/bound helper. "
            "Focused proof lives in `tests/test_diagnostic_export_assembler.py::test_validation_stops_consuming_source_iterable_at_first_duplicate`, where a generator raises if source preparation reads past the first duplicate source ID, `test_archive_entry_order_uses_explicit_extension`, which guards the archive-entry construction shape, `test_single_source_bundle_skips_sorting`, which patches `builtins.sorted` during one-source/one-payload assembly, `test_bundle_summary_does_not_serialize_sources`, which patches source-record serialization to fail while summary counts still work, `test_json_safe_uses_direct_recursive_loops`, which preserves JSON-safe output while failing if `_json_safe()` reintroduces comprehension frames or mapping `.items()` traversal, and `test_diagnostic_source_text_normalization_uses_shared_helper`, which proves source descriptor text fields are routed through the shared stripped-text helper."
        ),
        continuity_guardrails="R009, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_diagnostic_export_assembler.py tests/test_diagnostic_export_contract.py tests/test_diagnostic_export_bundle_integration.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve diagnostic bundle deterministic archive ordering, duplicate source/path rejection before collection, source descriptor text validation, unsafe-path validation, redaction, truncation, JSON-safe payload output, manifest output, summary counts, and archive_paths ordering while avoiding whole-source iterable materialization before validation, starred archive-entry unpacking, unnecessary single-source/payload sorting, archive-path generator frames, summary-time source serialization, recursive mapping items-view allocation, recursive comprehension frames during payload encoding, and duplicate local stripped-text helper logic."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep diagnostic archive path validation on single-pass segment scanning.",
        seam="request/status",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/diagnostics/assembler.py::_validate_archive_path()` now scans archive path segments with `_iter_archive_path_segments()` instead of allocating a `split()` parts list and running separate segment scans for dot and forbidden directory checks. "
            "Focused proof lives in `tests/test_diagnostic_export_assembler.py::test_archive_path_validation_scans_segments_without_split_list`, where a `str` subclass raises if segment iteration falls back to `split()`."
        ),
        continuity_guardrails="R009, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_diagnostic_export_assembler.py tests/test_diagnostic_export_contract.py tests/test_diagnostic_export_bundle_integration.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve unsafe archive path rejection, manifest collision rejection, deterministic archive ordering, duplicate path rejection before collection, redaction, truncation, and manifest output while avoiding repeated path-segment scans."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep diagnostic exact-secret redaction on preordered candidates.",
        seam="request/status",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/diagnostics/redaction.py::_collect_configured_secret_candidates()` now orders exact configured-secret candidates by length once, and `_apply_exact_secret_redaction()` reuses that order instead of sorting candidates for every redacted string. "
            "Provider keys are sorted directly during candidate collection instead of sorting `(key, value)` item pairs through a lambda, and secret-label inventory is accumulated explicitly before sorting instead of using a generator-expression frame. "
            "Configured-secret collection now skips `sorted()` for empty or single-provider and empty or single-label inventory paths, and skips candidate list sorting for zero or one configured secret candidate, while preserving sorted output for multi-provider snapshots and longest-secret-first redaction for overlapping values. "
            "Configured provider-label inventory now deduplicates normalized labels during the provider scan instead of collecting a label list and copying it through `set()` before sorting. "
            "Configured-secret values are now stripped once through `_usable_configured_secret()` and reused for candidate storage instead of stripping once for validation and again for the retained secret value. "
            "Recursive payload redaction now scans dict keys directly and accumulates redacted sequence items in a direct loop instead of allocating an `items()` view or list-comprehension frame while walking nested diagnostic payloads. "
            "`_normalize_label_part()` also reuses a compiled label-cleanup regex instead of calling module-level `re.sub()` for every provider label. "
            "`_RedactionAccumulator.metadata()` now reuses a cached sorted label tuple until a new label is added instead of sorting the same label set for repeated metadata reads, and skips `sorted()` entirely for empty or single-label metadata. "
            "`app/diagnostics/sources.py::_config_secret_inventory_payload()` now copies the preordered secret/provider label tuples with direct accumulation instead of constructor-copying them with `list(...)`. "
            "Focused proof lives in `tests/test_diagnostic_redaction.py::test_exact_secret_redaction_reuses_preordered_candidates` and `test_configured_secret_candidates_keep_longest_first_redaction`, which preserve overlapping-secret safety while failing if exact redaction calls `sorted()`, `test_configured_secret_candidate_order_skips_sort_for_zero_or_one_candidate`, which fails if zero/single candidate ordering calls list sort, `test_configured_secret_collection_avoids_item_pairs_and_generator_frames`, which makes provider `.items()` fail and guards the collector against `<genexpr>` bytecode while preserving provider/secret label order, `test_configured_secret_collection_strips_each_secret_once`, which fails if usable configured secrets are stripped once for validation and again for storage, `test_configured_secret_collection_skips_sort_for_single_provider`, which patches `builtins.sorted` to fail for the single-provider inventory path, `test_payload_redaction_uses_direct_recursive_loops`, which makes payload `.items()` fail and guards redaction traversal against `<listcomp>` bytecode, `test_configured_secret_inventory_deduplicates_provider_labels_directly`, which patches `builtins.set` to fail while preserving provider-label dedupe, `test_redaction_metadata_reuses_sorted_label_snapshot`, which fails if unchanged metadata labels sort again, `test_redaction_metadata_skips_sort_for_zero_or_one_label`, which fails if common empty/single-label metadata paths call `sorted()`, `test_label_part_normalization_uses_compiled_regex`, which fails if label normalization returns to module-level `re.sub()`, plus `tests/test_diagnostic_export_sources.py::test_config_secret_inventory_payload_accumulates_labels_without_list_constructor`, which guards the diagnostic source payload against label `list(...)` constructor calls."
        ),
        continuity_guardrails="R009, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_diagnostic_redaction.py tests/test_diagnostic_export_assembler.py tests/test_diagnostic_export_bundle_integration.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve configured-secret inventory labels, provider label normalization/dedupe, longest-secret-first exact replacement, pattern redaction, nested payload traversal, cycle safety, and secret-free diagnostic exports while avoiding repeated candidate sorting per string, provider item-pair sorting, repeated configured-secret stripping, unnecessary zero/single candidate sorting, unnecessary single-item provider/label sorting, secret-label generator frames, provider label list-to-set copies, recursive payload items-view/list-comprehension allocation, unnecessary metadata label sorting, repeated label-regex dispatch through module-level `re.sub()`, and diagnostic-source label constructor copies."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep normalized duplicate IOC candidates on the single-classification path in `run_pipeline()`.",
        seam="IOC extraction pipeline",
        evidence_kind="measurement + focused regression proof",
        evidence_summary=(
            "The `pipeline-duplicate-candidates` capture exercises representative URL defang variants that all normalize to `http://evil.com`: "
            "the current `app/pipeline/extractor.py::run_pipeline()` canonical-value gate returns one IOC and calls `classify()` once instead of repeating classification for every raw variant. "
            "`app/pipeline/normalizer.py::normalize()` now returns already-clean values before running the defang regex substitution loop when no known defang sentinel is present. "
            "`app/pipeline/normalizer.py::_DEFANG_PATTERNS` is now an immutable tuple of compiled pattern/replacement pairs instead of a mutable list for the static defang table. "
            "The final type/value dedup path now appends directly to the output list with a `seen_keys` set instead of storing IOCs in a dict and returning `list(values())`. "
            "`app/pipeline/classifier.py::classify()` also lowercases domain candidates once and reuses that value for blacklist lookup and IOC output. "
            "`app/pipeline/classifier.py::_DOMAIN_BLACKLIST` now uses a tuple-backed frozenset for static blacklist membership instead of a set literal at module import. "
            "IP candidate classification now parses with `ipaddress.ip_address()` once via `_classify_ip_type()` instead of probing IPv6 and IPv4 separately. "
            "Focused proof lives in `tests/test_pipeline.py::TestRunPipelineDeduplication::test_normalized_duplicate_variants_classified_once`, which preserves first-match `raw_match` semantics while proving duplicate normalized variants skip repeated classification, `test_type_value_duplicates_keep_first_output_order`, which preserves first-result order when distinct normalized candidates classify to the same IOC, `tests/test_normalizer.py::TestEdgeCases::test_clean_input_skips_defang_pattern_loop`, which fails if clean input runs regex substitutions, `test_defang_patterns_are_static_tuple`, which guards the defang pattern table shape, `tests/test_classifier.py::TestClassifyDomain::test_domain_lowercase_value_is_reused`, which fails if the domain path lowercases twice, `test_domain_blacklist_uses_static_frozenset`, which guards the blacklist membership table shape, and `tests/test_classifier.py::TestClassifyIPv4::test_ipv4_classification_parses_ip_once`, which fails if an IPv4 candidate is parsed twice."
        ),
        continuity_guardrails="R085, R087, R040",
        rerun_lanes="`python3 -m pytest -q tests/test_pipeline.py tests/test_extractor.py tests/test_normalizer.py tests/test_classifier.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve exact raw extraction behavior, all documented defang replacements, clean-input pass-through behavior, first-observed raw_match output, canonical IOC deduplication by type/value, output order, URL-before-IP precedence, IPv4/IPv6 classification semantics, domain blacklist semantics, lowercased domain output, and silent discard of unclassifiable candidates while avoiding regex substitution passes for clean values, mutable static defang pattern tables, repeated classify work for the same normalized value, the final dict-values copy, duplicate domain lowercasing, static blacklist set-literal allocation, and duplicate IP parsing."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep raw IOC extraction deduplication on direct output-list accumulation.",
        seam="IOC extraction pipeline",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/pipeline/extractor.py::extract_iocs()` now appends first-seen raw candidates directly to the returned list while tracking a `seen_raw` set, instead of storing candidates in a raw-keyed dict and returning `list(values())`. "
            "`app/pipeline/extractor.py::_EXPECTED_EXTRACTION_ERRORS` now centralizes the expected library failure tuple used by each extractor source instead of repeating it across every `except` block. "
            "Focused proof lives in `tests/test_extractor.py::TestDeduplicationInExtract::test_dedup_appends_first_seen_candidates_directly`, which patches all extractor sources and verifies duplicates keep the first type hint and first-seen output order, plus `tests/test_extractor.py::TestExtractEdgeCases::test_expected_extraction_errors_share_one_policy` and `test_expected_extraction_errors_fail_closed_without_warning`, which preserve fail-closed expected-error behavior while guarding the shared exception policy."
        ),
        continuity_guardrails="R085, R087, R040",
        rerun_lanes="`python3 -m pytest -q tests/test_extractor.py tests/test_pipeline.py tests/test_normalizer.py tests/test_classifier.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve iocextract/iocsearcher merge order, raw-value deduplication, first type-hint semantics, exception tolerance, and downstream pipeline input shape while avoiding the intermediate candidate dict, final values-list copy, and duplicated expected-exception tuples."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep SSH auth.log parsing on streaming lines, direct BSD timestamps, and cached source classification.",
        seam="IOC extraction pipeline",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/ssh/parser.py::_iter_lines()` now yields decoded text lines from bytes/text streams and `parse_auth_log()` increments `total_lines` as it parses, instead of reading the entire upload and materializing a line list before the parsing loop. "
            "`_parse_bsd_timestamp()` now uses a precomputed month map and direct `HH:MM:SS` integer extraction instead of `datetime.strptime()` for every BSD accepted-login line. "
            "`_classify_source()` now uses a bounded `lru_cache`, avoiding repeated `ipaddress.ip_address()` parsing and hostname exception paths for repeated source tokens. "
            "Focused proof lives in `tests/test_ssh_parser.py::TestStreamTypes::test_text_stream_is_not_read_all_at_once`, `TestTimestampBSD::test_bsd_timestamp_parsing_does_not_use_strptime`, and `TestSourceExtraction::test_repeated_source_classification_is_cached`, which fail if text streams are read wholesale, BSD parsing falls back to `strptime()`, or repeated source tokens are reparsed."
        ),
        continuity_guardrails="R008, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_ssh_parser.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve BSD/RFC3339 accepted-login parsing, year rollover, IPv4/IPv6/hostname classification, partial-match warnings, malformed UTF-8 replacement, and summary invariants while avoiding full-file line-list allocation, general-purpose BSD timestamp parsing, and repeated source classification for SSH auth.log uploads."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep `CacheStore.stats()` on one aggregate SQLite read.",
        seam="local cache/history",
        evidence_kind="query-count proof + focused regression proof",
        evidence_summary=(
            "The `cache-stats-query-count` capture shows `CacheStore.stats()` now returns total entries and oldest timestamp through one `SELECT COUNT(*), MIN(cached_at)` aggregate query. "
            "Focused proof lives in `tests/test_cache_store.py::TestStats::test_stats_uses_single_aggregate_query`, while the existing stats tests preserve empty-cache, populated-cache, and concurrent-write behavior."
        ),
        continuity_guardrails="R085, R087, R022, R040",
        rerun_lanes="`python3 -m pytest -q tests/test_cache_store.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve WAL-backed persistent connection behavior, total entry count, oldest cached timestamp semantics, clear/purge behavior, and thread-safe access while avoiding duplicate stats reads."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep nonpositive cache TTL reads on the pre-SQLite fast path.",
        seam="local cache/history",
        evidence_kind="query-count proof + focused regression proof",
        evidence_summary=(
            "`app/cache/store.py::CacheStore.get()` now returns `None` before touching SQLite when `ttl_seconds <= 0`, matching the existing expired-entry contract without reading or decoding a row that cannot be fresh. "
            "Focused proof lives in `tests/test_cache_store.py::TestTTL::test_nonpositive_ttl_skips_cache_lookup`, which traces the connection and asserts no `SELECT` is issued."
        ),
        continuity_guardrails="R087, R022, R040",
        rerun_lanes="`python3 -m pytest -q tests/test_cache_store.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve cache-miss behavior, positive-TTL hits, expiry semantics, WAL-backed store behavior, and no-error-caching assumptions while avoiding pointless reads when caching is effectively disabled."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep empty cache read/write payloads on JSON literals.",
        seam="local cache/history",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/cache/store.py::_EMPTY_JSON_OBJECT` centralizes the empty JSON object literal, and `CacheStore.put()` stores that literal for empty cache payloads instead of invoking `json.dumps({})`. "
            "`CacheStore.get()` and `get_all_for_ioc()` mirror that fast path by returning empty dicts directly when stored payload columns are the literal `{}`, avoiding `json.loads()` for empty cache payloads. "
            "Focused proof lives in `tests/test_cache_store.py::TestPutAndGet::test_empty_payload_skips_json_encoding`, which patches the cache-store JSON encoder to fail, `test_empty_payload_skips_json_decoding`, which patches the decoder to fail while preserving `get()` and `get_all_for_ioc()` roundtrip behavior for empty payloads, and `test_empty_payload_uses_shared_json_literal_constant`, which guards the shared literal path."
        ),
        continuity_guardrails="R087, R022, R040",
        rerun_lanes="`python3 -m pytest -q tests/test_cache_store.py::TestPutAndGet::test_empty_payload_skips_json_encoding tests/test_cache_store.py::TestPutAndGet::test_empty_payload_skips_json_decoding tests/test_cache_store.py::TestPutAndGet::test_empty_payload_uses_shared_json_literal_constant tests/test_cache_store.py::TestPutAndGet::test_roundtrip tests/test_cache_store.py::TestGetAllForIoc::test_get_all_for_ioc_returns_all_providers`; `make verify-fast`",
        continuity_notes=(
            "Preserve cache put/get JSON shape, detail-page cache result loading, provider/cached_at metadata injection, and non-empty payload encoding/decoding while avoiding unnecessary JSON encoder and decoder calls for empty cache payloads and duplicated JSON literal strings."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep cache/history SQLite PRAGMA setup behind the shared `app.sqlite.configure_connection()` helper.",
        seam="local cache/history",
        evidence_kind="refactor proof + focused regression proof",
        evidence_summary=(
            "`app/cache/store.py` and `app/enrichment/history_store.py` now share one SQLite connection-configuration helper instead of duplicating WAL, synchronous, busy-timeout, cache-size, and temp-store PRAGMA setup. "
            "Focused proof lives in `tests/test_sqlite.py`, while the existing cache/history store tests still verify WAL mode and busy-timeout on live store connections."
        ),
        continuity_guardrails="R022, R040",
        rerun_lanes="`python3 -m pytest -q tests/test_sqlite.py tests/test_cache_store.py tests/test_history_store.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve WAL-backed persistent local-store behavior and keep future SQLite tuning centralized so cache and history stores do not drift."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep recent-history summaries on the SQL-side input preview projection.",
        seam="local cache/history",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/enrichment/history_store.py::HistoryStore.list_recent()` now selects `substr(input_text, 1, 120)` for summary rows instead of returning full pasted analyst input and slicing it in Python. "
            "It now accumulates returned summary dicts with a direct loop instead of allocating a list-comprehension frame around the already SQL-bounded rows. "
            "Focused proof lives in `tests/test_history_store.py::TestListRecent::test_truncates_input_text`, which now also verifies `load_analysis()` still returns the complete saved input text, and `test_list_recent_accumulates_summaries_without_list_comprehension`, which guards `list_recent()` against `<listcomp>` bytecode."
        ),
        continuity_guardrails="R087, R022, R040",
        rerun_lanes="`python3 -m pytest -q tests/test_history_store.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve persisted analysis input fidelity and recent-history summary shape while avoiding full input-text transfer into Python for list views and comprehension-frame allocation around bounded summary rows."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep empty history save/load payloads on JSON literals.",
        seam="local cache/history",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/enrichment/history_store.py::_EMPTY_JSON_ARRAY` centralizes the empty JSON array literal, and `HistoryStore.save_analysis()` stores that literal for empty IOC and result payloads instead of invoking `json.dumps([])` for each empty list. "
            "`HistoryStore.load_analysis()` mirrors that fast path by returning empty lists directly when stored payload columns are the literal `[]`, avoiding `json.loads()` for empty history payloads. "
            "Focused proof lives in `tests/test_history_store.py::TestSaveAndLoad::test_empty_payloads_skip_json_encoding`, which patches the history-store JSON encoder to fail, `test_empty_payloads_skip_json_decoding`, which patches the decoder to fail, and `test_empty_payloads_use_shared_json_literal_constant`, which guards the shared literal path, while preserving save/load roundtrip behavior for empty payloads."
        ),
        continuity_guardrails="R087, R022, R040",
        rerun_lanes="`python3 -m pytest -q tests/test_history_store.py::TestSaveAndLoad::test_empty_payloads_skip_json_encoding tests/test_history_store.py::TestSaveAndLoad::test_empty_payloads_skip_json_decoding tests/test_history_store.py::TestSaveAndLoad::test_empty_payloads_use_shared_json_literal_constant tests/test_history_store.py::TestSaveAndLoad::test_roundtrip`; `make verify-fast`",
        continuity_notes=(
            "Preserve history save/load JSON shape, empty IOC/result roundtrips, non-empty payload encoding/decoding, and top-verdict fallback while avoiding unnecessary JSON encoder and decoder calls for empty saved payloads and duplicated JSON literal strings."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep history top-verdict computation on the malicious short-circuit path.",
        seam="local cache/history",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/enrichment/history_store.py::_compute_top_verdict()` now returns immediately when it sees `_MAX_VERDICT`, the maximum verdict severity, instead of scanning the remaining saved results. "
            "`_FALLBACK_VERDICT` also centralizes the no-verdict/error-only fallback. "
            "Focused proof lives in `tests/test_history_store.py::TestComputeTopVerdictUnit::test_malicious_verdict_short_circuits_scan`, while `test_top_verdict_terminal_constants_are_precomputed` guards the terminal verdict constants and the existing priority-order tests preserve malicious/suspicious/no_data/clean/error semantics."
        ),
        continuity_guardrails="R087, R022, R040",
        rerun_lanes="`python3 -m pytest -q tests/test_history_store.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve saved-analysis top_verdict semantics while avoiding unnecessary result-row inspection once the maximum severity has been found and avoiding duplicated terminal verdict literals."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep history verdict priority on a precomputed map.",
        seam="local cache/history",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/enrichment/history_store.py::_VERDICT_PRIORITY` now stores the top-verdict severity map once at module load, and `_compute_top_verdict()` reuses it instead of rebuilding the same dict for every saved analysis. "
            "`_MAX_VERDICT` and `_FALLBACK_VERDICT` keep the scan's terminal verdict constants next to that precomputed priority map. "
            "Focused proof lives in `tests/test_history_store.py::TestComputeTopVerdictUnit::test_priority_map_is_precomputed` and `test_top_verdict_terminal_constants_are_precomputed`, while existing priority and malicious short-circuit tests preserve verdict semantics."
        ),
        continuity_guardrails="R087, R022, R040",
        rerun_lanes="`python3 -m pytest -q tests/test_history_store.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve saved-analysis top_verdict priority order, error-only fallback, malicious short-circuiting, and history save/load behavior while avoiding repeated priority-map allocation."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep `ProviderRegistry` filters on direct provider scans.",
        seam="provider registration/config diagnostics",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/enrichment/registry.py::all()` now keeps its public mutable-list return contract while accumulating providers from registry keys directly instead of allocating a dict-values view and then copying it. "
            "`app/enrichment/registry.py::configured()` and `providers_for_type()` now keep their public list-returning contracts while accumulating matching providers from registry keys directly during the registry scan instead of allocating values views or list-comprehension frames. "
            "`provider_count_for_type()` also counts matching configured providers from registry keys in a direct loop instead of calling `providers_for_type()` and allocating a provider list just to take its length, routing the scan through a `sum()` generator, or allocating a values view. "
            "`_provider_supports_configured_type()` centralizes the shared configured/type eligibility predicate used by both list and count scans. "
            "Focused proof lives in `tests/test_provider_registry.py::TestRegistryRegister::test_all_accumulates_without_values_view`, which makes the all-provider path fail if it calls `values()`, `TestRegistryListReturningFilters::test_list_filters_do_not_allocate_comprehension_frames`, which guards the list-returning filters against `<listcomp>` bytecode, `test_list_filters_scan_without_values_view`, which makes configured/type filters fail on `values()`, `TestRegistryProvidersForType::test_providers_for_type_uses_shared_eligibility_predicate`, which proves the list path uses the shared predicate, `TestRegistryProviderCountForType::test_count_does_not_allocate_provider_list`, which makes the count fail if it falls back to `providers_for_type()`, `test_count_does_not_use_sum_generator`, which patches `builtins.sum` to fail, `test_count_scans_without_values_view`, which makes the count path fail on `values()`, and `test_count_uses_shared_eligibility_predicate`, which proves the count path uses the same predicate while preserving count semantics."
        ),
        continuity_guardrails="R085, R087, D080",
        rerun_lanes="`python3 -m pytest -q tests/test_provider_registry.py tests/test_registry_setup.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve all-provider reads, configured-provider filtering, returned list mutability, insertion order, and IOC type support semantics while keeping registry scans free of unnecessary values-view, provider-list, list-comprehension, generator allocation, and duplicated configured/type eligibility logic."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep static adapter frozensets on tuple inputs.",
        seam="provider registration/config diagnostics",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "Literal provider adapter `supported_types` constants now call `frozenset((...))` instead of `frozenset({...})`, avoiding temporary set-literal allocation during adapter module import while preserving the public immutable set contract. "
            "`app/enrichment/adapters/shodan.py::_MALICIOUS_TAGS` uses the same tuple-input shape for its static membership table. "
            "Focused proof lives in `tests/test_adapter_contract.py::test_adapter_static_frozensets_avoid_temporary_set_literals`, which scans adapter source files and fails if static `frozenset({` literals return in inline or whitespace-separated form, while the existing adapter contract suite preserves supported-type behavior for every adapter."
        ),
        continuity_guardrails="R008, R009, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_adapter_contract.py tests/test_registry_setup.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve adapter supported_types frozenset contracts, registry setup, unsupported-type guards, and Shodan malicious-tag matching while avoiding temporary set-literal allocation for static adapter membership tables."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep ASN TXT parsing on first-record and direct field extraction.",
        seam="provider registration/config diagnostics",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/enrichment/adapters/asn_cymru.py::CymruASNAdapter.lookup()` now reads the first DNS TXT answer with `next(iter(answers))` instead of materializing all answer records with `list(answers)[0]`. "
            "It also decodes the common single-chunk TXT answer directly and only joins segmented TXT chunks when DNS returns multi-part text. "
            "`_parse_txt_fields()` also extracts the pipe-delimited ASN/prefix/RIR/allocation fields directly instead of building a stripped `split()` parts list or accumulating an intermediate field list. "
            "`_no_data_result()` now owns the shared informational Cymru result shape for DNS misses and parsed ASN context instead of repeating the same constructor arguments across lookup branches. "
            "Focused proof lives in `tests/test_asn_cymru.py::TestSuccessfulLookup::test_txt_answer_uses_first_record_without_materializing_all_answers`, where a generator raises if ASN parsing reads past the first record, `test_single_chunk_txt_answer_skips_join_iteration` and `test_multi_chunk_txt_answer_still_concatenates_segments`, which preserve TXT decoding semantics while avoiding unnecessary single-chunk join iteration, `test_txt_parse_does_not_allocate_split_parts`, where a string subclass raises if parsing calls `split()`, `test_txt_field_parser_does_not_build_intermediate_field_list`, which fails if the field parser emits list-building bytecode, and `test_no_data_result_helper_preserves_informational_shape`, which preserves the centralized no-data result contract."
        ),
        continuity_guardrails="R008, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_asn_cymru.py tests/test_adapter_contract.py tests/test_registry_setup.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve Team Cymru query construction, TXT field semantics including segmented TXT concatenation, no-data verdict behavior, DNS error handling, fresh resolver behavior, and no-HTTP/no-requests boundaries while avoiding unnecessary DNS answer list materialization, single-chunk TXT join iteration, TXT field-list materialization, and duplicated no-data result construction."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep DNS record extraction on table-driven dispatch.",
        seam="provider registration/config diagnostics",
        evidence_kind="refactor proof + focused regression proof",
        evidence_summary=(
            "`app/enrichment/adapters/dns_lookup.py::DnsAdapter.lookup()` now carries each DNS record type's raw_stats key and extractor in `_RECORD_TYPES`, so the lookup loop calls the table extractor directly instead of running an `if`/`elif` chain for A/MX/NS/TXT after each resolver call. "
            "The A/NS, MX, and TXT extractors now use direct loops instead of allocating list-comprehension frames per resolved record set. "
            "TXT extraction now decodes single-chunk records directly and only joins multi-chunk records when DNS actually returns segmented TXT data. "
            "`app/enrichment/adapters/dns_lookup.py::_dns_result()` now owns the shared informational no-data result envelope for DNS record responses instead of keeping verdict, counts, scan-date, and raw_stats constructor wiring in the resolver loop. "
            "Focused proof lives in `tests/test_dns_lookup.py::TestSuccessfulLookup::test_lookup_uses_record_table_extractors`, `tests/test_dns_lookup.py::TestTXTRecords::test_single_chunk_txt_record_skips_join_iteration`, `tests/test_dns_lookup.py::TestRecordExtractorImplementation::test_record_extractors_do_not_allocate_list_comprehension_frames`, and `tests/test_dns_lookup.py::TestSuccessfulLookup::test_result_helper_preserves_provider_envelope`, while the existing A/MX/NS/TXT extraction tests preserve exact raw_stats formatting."
        ),
        continuity_guardrails="R008, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_dns_lookup.py tests/test_adapter_contract.py tests/test_registry_setup.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve DNS-only/no-HTTP behavior, resolver lifetime, record order, A/MX/NS/TXT raw_stats formats including multi-chunk TXT concatenation, NXDOMAIN/NoAnswer no-data semantics, parsed-response total_engines, and per-record lookup error collection while removing repeated record-type branch dispatch inside DNS lookups, list-comprehension extractor frames, unnecessary single-chunk TXT join iteration, and duplicated DNS result-envelope construction."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep VirusTotal engine total computation in the stats scan.",
        seam="provider registration/config diagnostics",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/enrichment/adapters/virustotal.py::_parse_response()` now computes `malicious` and total engine count while scanning `last_analysis_stats` keys once instead of calling `sum(stats.values())`, allocating an `items()` view, and then subtracting excluded buckets. "
            "`_EXCLUDED_ENGINE_STATUSES` now owns the timeout/type-unsupported exclusion table as a static frozenset instead of rebuilding that membership set inside the stats loop. "
            "Top-detection extraction now scans `last_analysis_results` keys directly instead of allocating a `values()` view while preserving first-five unique malicious detection names. "
            "`VTAdapter.supported_types` now derives directly from `ENDPOINT_MAP`, and `app/enrichment/adapters/virustotal.py::_virustotal_result()` now owns the shared provider envelope for 404 no-data hooks and parsed API responses instead of repeating provider, scan-date, total_engines, and raw_stats constructor wiring across branches. "
            "Focused proof lives in `tests/test_vt_adapter.py::TestLookupSuccess::test_total_engine_count_does_not_use_sum_helper`, where `builtins.sum` is patched to fail and stats raise if parsing calls `.items()` while detection and total engine counts are preserved, `test_engine_status_exclusions_use_static_frozenset`, which fails if the parser rebuilds excluded-status membership sets, `test_top_detections_do_not_allocate_values_view`, where analysis results raise if parsing calls `values()` while preserving top-detection dedupe, plus `tests/test_vt_adapter.py::test_supported_types_derive_from_endpoint_map` and `tests/test_vt_adapter.py::TestLookupSuccess::test_result_helper_preserves_provider_envelope`, which fail if supported IOC types drift from endpoint routing or the centralized VirusTotal result-envelope contract changes."
        ),
        continuity_guardrails="R008, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_vt_adapter.py tests/test_vt_context_fields.py tests/test_adapter_contract.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve VirusTotal endpoint mapping, 404/no-data behavior, rate-limit/auth errors, verdict semantics, excluded timeout/type-unsupported buckets, top detections, reputation, parsed-response total_engines, and HTTP safety controls while avoiding an extra stats values/sum pass, stats items-view allocation, per-parse excluded-status set construction, analysis-result values-view allocation, duplicated supported-type declarations, and duplicated VirusTotal result-envelope construction."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep ThreatMiner capped result extraction bounded.",
        seam="provider registration/config diagnostics",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/enrichment/adapters/threatminer.py` now applies passive-DNS and related-sample caps inside extraction loops instead of building full result arrays and slicing after the fact. "
            "Those extractors also return immediately for zero or negative caps, so disabled extraction paths do not touch result iterables. "
            "`_no_data_result()` now owns the shared informational ThreatMiner result shape used by IP, domain, and hash lookup paths instead of repeating the same constructor arguments in each branch. "
            "Defensive dict sample rows now scan keys directly instead of allocating a `values()` view while extracting the first string value. "
            "Focused proof lives in `tests/test_threatminer.py::TestIPLookup::test_ip_lookup_passive_dns_stops_at_cap`, `TestDomainLookup::test_domain_lookup_samples_stop_at_cap`, and `TestHashLookup::test_hash_lookup_samples_stop_at_cap`, where bounded iterables raise if extraction reads past the documented caps, `TestIPLookup::test_zero_cap_passive_dns_skips_result_iteration` and `TestDomainLookup::test_zero_cap_samples_skip_result_iteration`, where exploding iterables prove zero caps do not read rows, `TestDomainLookup::test_dict_sample_rows_do_not_allocate_values_view`, where dict rows raise if sample extraction calls `values()`, plus `TestNoDataHandling::test_no_data_result_helper_preserves_informational_shape`, which preserves the centralized no-data result contract."
        ),
        continuity_guardrails="R008, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_threatminer.py tests/test_adapter_contract.py tests/test_registry_setup.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve ThreatMiner IP/domain/hash routing, two-call domain lookup, passive DNS and sample raw_stats, no-data semantics, defensive dict sample handling, and HTTP safety controls while avoiding full oversized result scans beyond the published caps, zero-cap result iteration, dict values-view allocation in sample fallback rows, and duplicated no-data result construction."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep crt.sh certificate parsing on one body scan.",
        seam="provider registration/config diagnostics",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/enrichment/adapters/crtsh.py::_parse_response()` now computes earliest/latest certificate dates while scanning certificate rows for SAN subdomains, avoiding a separate date-list build plus `min()`/`max()` pass. "
            "`_iter_name_values()` streams newline-delimited SAN names from each `name_value` string instead of allocating a per-certificate split list. "
            "`_capped_sorted_subdomains()` also skips sorting empty or single-subdomain sets, and selects the first 50 alphabetical subdomains with `heapq.nsmallest()` when the deduplicated set exceeds the raw_stats cap instead of sorting the full set and slicing. "
            "`app/enrichment/adapters/crtsh.py::_crtsh_result()` now owns the shared informational no-data result envelope for empty and populated certificate responses instead of repeating verdict, counts, scan-date, and raw_stats constructor wiring across parse branches. "
            "Focused proof lives in `tests/test_crtsh.py::TestCertDataExtraction::test_date_range_and_subdomains_computed_in_one_body_scan`, where a single-pass body raises if parsing iterates certificate rows more than once, `test_name_value_parsing_does_not_allocate_split_list`, where a string subclass raises if SAN parsing calls `split()`, `test_empty_or_single_subdomain_sets_skip_sorting`, where `builtins.sorted` is patched to fail for empty/single sets, `test_subdomain_cap_avoids_full_sorted_list`, where `builtins.sorted` is patched to fail for oversized sets, and `test_result_helper_preserves_provider_envelope`, which preserves the centralized crt.sh result-envelope contract."
        ),
        continuity_guardrails="R008, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_crtsh.py tests/test_adapter_contract.py tests/test_registry_setup.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve crt.sh domain-only support, cert counts, earliest/latest date semantics, wildcard stripping, lowercase/deduplicated/sorted subdomains, first-50 alphabetical cap, no-data verdict behavior, parsed-response total_engines, and HTTP safety controls while avoiding a second scan for date range calculation, per-certificate SAN split-list allocation, unnecessary empty/single subdomain sorting, full oversized subdomain sorting, and duplicated crt.sh result-envelope construction."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep Shodan malicious-tag detection on a direct count.",
        seam="provider registration/config diagnostics",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/enrichment/adapters/shodan.py::_parse_response()` now counts malicious tags directly while scanning `tags` instead of building a temporary filtered `bad_tags` list and taking its length. "
            "`_shodan_result()` now owns the shared provider envelope for both InternetDB 404 no-data hooks and parsed malicious/suspicious/no-data responses instead of repeating provider, scan-date, and raw_stats constructor wiring across branches. "
            "Focused proof lives in `tests/test_shodan.py::TestLookupFound::test_malicious_tag_count_preserves_duplicate_bad_tags`, which preserves duplicate bad-tag detection counts and raw tag stats, plus `test_result_helper_preserves_provider_envelope`, which preserves the centralized result-envelope contract."
        ),
        continuity_guardrails="R008, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_shodan.py tests/test_adapter_contract.py tests/test_registry_setup.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve Shodan IPv4/IPv6 support, malicious-tag priority over vulnerability suspicion, duplicate bad-tag counting, 404 no-data behavior, parsed-response total_engines, raw_stats passthrough, and HTTP safety controls while avoiding intermediate bad-tag list allocation and duplicated result-envelope construction."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep EmailRep malicious verdict selection on the risk-flag scan.",
        seam="provider registration/config diagnostics",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/enrichment/adapters/emailrep.py::_risk_flags()` now returns both the ordered risk flag list and whether any high-confidence malicious flag was present, so `_parse_response()` does not rescan malicious flag fields with `any()` after building raw_stats. "
            "`_NO_REPUTATION_VALUES` and `_DETECTION_VERDICTS` now hold the static verdict membership tables instead of rebuilding small sets during every parse. "
            "`app/enrichment/adapters/emailrep.py::_emailrep_result()` now owns the shared provider envelope for parsed EmailRep reputation responses instead of keeping provider, scan-date, total_engines, and raw_stats constructor wiring inside the verdict parser. "
            "Focused proof lives in `tests/test_emailrep.py::TestEmailRepLookup::test_verdict_uses_risk_flag_scan_without_second_malicious_pass`, where `builtins.any` is patched to fail while malicious verdict and risk flags are preserved, `test_verdict_membership_tables_are_static_frozensets`, which fails if the parser rebuilds verdict membership sets, plus `tests/test_emailrep.py::TestEmailRepLookup::test_result_helper_preserves_provider_envelope`, which fails if the centralized EmailRep result-envelope contract changes."
        ),
        continuity_guardrails="R008, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_emailrep.py tests/test_adapter_contract.py tests/test_registry_setup.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve EmailRep email-only support, auth headers, high-confidence malicious verdict mapping, suspicious/clean/no-data behavior, ordered risk_flags raw_stats, profile passthrough, parsed-response total_engines, scan-date passthrough, and HTTP safety controls while avoiding a second malicious-flag scan, per-parse verdict membership set construction, and duplicated EmailRep result-envelope construction."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep AbuseIPDB parsed result construction behind one provider envelope helper.",
        seam="provider registration/config diagnostics",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/enrichment/adapters/abuseipdb.py::_abuseipdb_result()` now owns the shared provider envelope for parsed AbuseIPDB reputation responses instead of keeping provider, scan-date, total_engines, and raw_stats constructor wiring inside the score-threshold parser. "
            "Focused proof lives in `tests/test_abuseipdb.py::TestAbuseIPDBLookup::test_result_helper_preserves_provider_envelope`, which fails if the centralized AbuseIPDB result-envelope contract changes."
        ),
        continuity_guardrails="R008, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_abuseipdb.py tests/test_adapter_contract.py tests/test_registry_setup.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve AbuseIPDB IPv4/IPv6 support, capital Key auth header, Accept header, score threshold verdict mapping, totalReports/numDistinctUsers count mapping, lastReportedAt scan-date passthrough, raw_stats fields, rate-limit hook, and HTTP safety controls while avoiding duplicated AbuseIPDB result-envelope construction."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep ThreatFox best-record selection on a short-circuiting confidence scan.",
        seam="provider registration/config diagnostics",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/enrichment/adapters/threatfox.py::_select_best_record()` now scans records directly and returns as soon as a perfect confidence record is seen instead of using `max(..., key=lambda ...)` over every returned record. "
            "`app/enrichment/adapters/threatfox.py::_threatfox_result()` now owns the shared provider envelope for no-result and selected-record responses instead of repeating provider, scan-date, total_engines, and raw_stats constructor wiring across parse branches. "
            "Focused proof lives in `tests/test_threatfox.py::TestMultipleResults::test_best_record_selection_short_circuits_on_perfect_confidence` and `tests/test_threatfox.py::TestEdgeCases::test_result_helper_preserves_provider_envelope`, which preserve best-record selection while failing if selection walks past a confidence-100 record or the centralized ThreatFox result-envelope contract changes."
        ),
        continuity_guardrails="R008, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_threatfox.py tests/test_adapter_contract.py tests/test_registry_setup.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve ThreatFox hash and IOC lookup routing, confidence threshold semantics, highest-confidence record selection, raw malware metadata, no-result semantics, parsed-response total_engines, and HTTP safety controls while avoiding callback-based full scans when the best possible confidence appears early and duplicated ThreatFox result-envelope construction."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep IP Context geo and ASN/ISP formatting on direct string construction.",
        seam="provider registration/config diagnostics",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/enrichment/adapters/ip_api.py::_parse_response()` now builds the `geo` context string directly instead of allocating a temporary `geo_parts` list solely for `join()`, and parses the `org` ASN/ISP text with `partition()` instead of `split()` list allocation. "
            "`_no_data_result()` now owns the shared informational IP Context result shape for private-IP 404s, malformed responses, and successful geo context instead of repeating the same constructor arguments across branches. "
            "Focused proof lives in `tests/test_ip_api.py::TestGeoFormatting::test_geo_format_exact_full_context`, `test_geo_format_exact_minimal_context`, `test_org_parsing_does_not_allocate_split_parts`, and `test_no_data_result_helper_preserves_informational_shape`, which preserve full CC/city/ASN formatting, missing-field separator behavior, ASN/ISP display text without `split()`, and the centralized no-data result contract."
        ),
        continuity_guardrails="R008, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_ip_api.py tests/test_adapter_contract.py tests/test_registry_setup.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve IP Context public/private-IP behavior, no-data verdicts, raw_stats fields, ASN/org parsing, exact geo display text, and HTTP safety controls while avoiding temporary geo-part and ASN/ISP split-list allocation plus duplicated no-data result construction."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep WHOIS name-server normalization on list reuse.",
        seam="provider registration/config diagnostics",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/enrichment/adapters/whois_lookup.py::_normalise_name_servers()` now reuses already-materialized WHOIS name-server lists instead of copying them with `list()`, while still materializing tuple/iterable values for the raw_stats contract. "
            "`app/enrichment/adapters/whois_lookup.py::_whois_result()` now owns the shared informational no-data result envelope for successful lookups, domain-not-found misses, and graceful parse/TLD degrade paths instead of repeating verdict, counts, scan-date, and raw_stats constructor wiring across branches. "
            "Focused proof lives in `tests/test_whois_lookup.py::TestRawStatsExtraction::test_name_server_lists_are_reused_without_copying`, `test_name_server_non_list_iterables_are_materialized`, `TestNormaliseNameServers::test_normalise_name_servers_reuses_exact_lists_without_iterating`, and `tests/test_whois_lookup.py::TestSuccessfulLookup::test_result_helper_preserves_provider_envelope`."
        ),
        continuity_guardrails="R008, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_whois_lookup.py tests/test_adapter_contract.py tests/test_registry_setup.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve WHOIS no-data verdicts, registrar/org/date extraction, name_servers raw_stats list behavior, domain-not-found defaults, parse-error recording, parsed-response total_engines, and non-HTTP protocol boundaries while avoiding unnecessary name-server list copies and duplicated WHOIS result-envelope construction."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep shared HTTP response reads on one byte accumulator.",
        seam="provider registration/config diagnostics",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/enrichment/http_safety.py::read_limited()` now extends one `bytearray` while enforcing the 1 MB response cap instead of appending chunks to a list and joining them after the stream is read. "
            "`RESPONSE_CHUNK_SIZE` now owns the streaming read chunk size alongside the other HTTP safety constants instead of leaving an inline magic number in the response loop. "
            "Focused proof lives in `tests/test_http_safety.py::TestReadLimited::test_read_limited_parses_chunked_json`, which preserves chunked JSON parsing and the documented 8192-byte chunk size, plus `test_read_limited_uses_shared_chunk_size_constant`, which fails if `read_limited()` stops reading the shared chunk-size constant."
        ),
        continuity_guardrails="R008, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_http_safety.py tests/test_adapter_contract.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve SSRF validation, stream=True/no-redirect request flags, timeout behavior, pre-raise hook semantics, response byte cap enforcement, JSON parsing, and exception mapping while avoiding per-response chunk-list allocation and final bytes join."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep HTTP adapter allowlist membership on a construction-time set.",
        seam="provider registration/config diagnostics",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/enrichment/adapters/base.py::BaseHTTPAdapter.__init__()` now materializes `allowed_hosts` as a `frozenset` once, so every `safe_request()` SSRF validation checks hostname membership against the cached set instead of rescanning the original list. "
            "The same constructor now skips the no-op `Session.headers.update({})` call for adapters whose default auth headers are empty, while preserving keyed adapter header setup. "
            "`app/enrichment/http_safety.py::validate_endpoint()` and `safe_request()` accept collection-style allowlists, preserving the existing error path for rejected hosts. "
            "Focused proof lives in `tests/test_base_adapter.py::TestLookupDispatch::test_allowed_hosts_are_cached_as_membership_set`, which verifies `lookup()` passes the cached set to `safe_request()` and ignores later mutations to the caller's list, plus `tests/test_base_adapter.py::TestAuthHeaders::test_default_auth_headers_skip_empty_session_update`, which fails if a public adapter updates the session with an empty header mapping."
        ),
        continuity_guardrails="R008, R009, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_base_adapter.py tests/test_http_safety.py tests/test_adapter_contract.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve SSRF allowlist enforcement, unsupported-type rejection, pre-raise hook behavior, POST body dispatch, keyed adapter auth headers, and rejected-host error reporting while avoiding repeated linear allowlist membership scans on HTTP-backed provider lookups and no-op empty header updates during public adapter construction."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep route-mapped adapter support declarations derived from endpoint maps.",
        seam="provider registration/config diagnostics",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`HashlookupAdapter.supported_types`, `OTXAdapter.supported_types`, and `URLhausAdapter.supported_types` now derive directly from their private IOC-type route maps instead of repeating equivalent frozenset literals. "
            "`app/enrichment/adapters/hashlookup.py::_hashlookup_result()` now owns the shared provider envelope for CIRCL 404 no-data hooks and known-good NSRL responses instead of repeating provider, scan-date, total_engines, and raw_stats constructor wiring across branches. "
            "`app/enrichment/adapters/otx.py::_otx_result()` now owns the shared provider envelope for both OTX 404 no-data hooks and parsed malicious/suspicious/no-data pulse responses instead of repeating provider, scan-date, total_engines, and raw_stats constructor wiring across branches. "
            "`app/enrichment/adapters/urlhaus.py::_urlhaus_result()` now owns the shared provider envelope for parsed listed, host, payload, and no-result responses instead of keeping provider, scan-date, total_engines, and raw_stats constructor wiring inside the verdict branch parser. "
            "Focused proof lives in `tests/test_hashlookup.py::TestURLPattern::test_supported_types_derive_from_hash_route_map`, `tests/test_hashlookup.py::TestLookupFound::test_result_helper_preserves_provider_envelope`, `tests/test_otx.py::TestOTXTypeMapping::test_supported_types_derive_from_otx_route_map`, `tests/test_urlhaus.py::test_supported_types_derive_from_endpoint_map`, `tests/test_urlhaus.py::TestURLhausLookup::test_result_helper_preserves_provider_envelope`, and `tests/test_otx.py::TestOTXLookup::test_result_helper_preserves_provider_envelope`, which fail if supported IOC types drift from endpoint routing or centralized Hashlookup/OTX/URLhaus result-envelope contracts change."
        ),
        continuity_guardrails="R008, R010, R020, R085",
        rerun_lanes="`python3 -m pytest -q tests/test_hashlookup.py tests/test_otx.py tests/test_urlhaus.py tests/test_adapter_contract.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve provider support coverage, endpoint path/body routing, auth headers, no-data hooks, Hashlookup known-good semantics, OTX pulse verdict thresholds, URLhaus listed/host/payload verdict semantics, parsed-response total_engines, and adapter contract behavior while removing duplicated import-time type-set declarations that can drift from routing maps and duplicated Hashlookup/OTX/URLhaus result-envelope construction."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep MalwareBazaar result construction behind one provider envelope helper.",
        seam="provider registration/config diagnostics",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/enrichment/adapters/malwarebazaar.py::_malwarebazaar_result()` now owns the shared provider envelope for both `hash_not_found` no-data results and found-sample malicious results instead of repeating provider, verdict metadata, scan-date, and raw_stats constructor wiring in each branch. "
            "Focused proof lives in `tests/test_malwarebazaar.py::TestLookupFound::test_result_helper_preserves_provider_envelope`, while the existing found/not-found tests preserve MalwareBazaar verdict and metadata behavior."
        ),
        continuity_guardrails="R008, R010, R020, R085",
        rerun_lanes="`python3 -m pytest -q tests/test_malwarebazaar.py tests/test_adapter_contract.py tests/test_registry_setup.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve MalwareBazaar hash-only support, form-encoded request body, auth headers, hash-not-found no-data behavior, found-sample malicious semantics, first_seen scan_date, and raw malware metadata while removing duplicated result-envelope construction."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep GreyNoise result construction behind one provider envelope helper.",
        seam="provider registration/config diagnostics",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/enrichment/adapters/greynoise.py::_greynoise_result()` now owns the shared provider envelope for both Community API 404 no-data hooks and parsed clean/malicious/suspicious/no-data responses instead of repeating provider, total_engines, scan_date, and raw_stats constructor wiring across branches. "
            "Focused proof lives in `tests/test_greynoise.py::TestGreyNoiseLookup::test_result_helper_preserves_provider_envelope`, while the existing verdict-priority and 404 tests preserve GreyNoise response behavior."
        ),
        continuity_guardrails="R008, R010, R020, R085",
        rerun_lanes="`python3 -m pytest -q tests/test_greynoise.py tests/test_adapter_contract.py tests/test_registry_setup.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve GreyNoise IPv4/IPv6 support, lowercase auth header, 404 no-data behavior, RIOT clean priority, malicious classification priority, suspicious noise handling, last_seen scan_date, and raw_stats passthrough while removing duplicated result-envelope construction."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep ConfigStore read-after-write on the cached parser path.",
        seam="provider registration/config diagnostics",
        evidence_kind="mocked parser proof + focused regression proof",
        evidence_summary=(
            "`app/enrichment/config_store.py::_save_config()` now keeps the just-written `ConfigParser` instance cached instead of clearing `_cached_cfg`, so immediate reads after settings writes do not reparse the same config file. "
            "`app/enrichment/config_store.py::all_provider_keys()` also accumulates provider section keys directly instead of constructor-copying the section proxy. "
            "`app/enrichment/config_store.py::_provider_option_name()` now centralizes case-insensitive provider option normalization for both get and set paths. "
            "Focused proof lives in `tests/test_config_store.py::TestConfigStoreSetAndGet::test_save_keeps_written_config_cached`, which patches `ConfigParser.read` and verifies read-after-write returns the saved key without disk parsing, `TestConfigStoreMultiProvider::test_all_provider_keys_accumulates_directly_from_section`, which makes constructor-style section copying fail while preserving provider-key output, and `TestConfigStoreMultiProvider::test_provider_key_get_and_set_share_option_normalization`, which proves provider get/set use the shared option-name helper."
        ),
        continuity_guardrails="R008, R009, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_config_store.py tests/test_settings.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve owner-only config writes, disk persistence for fresh store instances, provider-key sections, provider-name case-insensitivity, cache TTL, SSH normal-hours settings, and settings-page behavior while avoiding immediate post-save config reparsing, provider-section constructor copies, and duplicated provider option-name normalization."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep registry provider-key loading on one config map read.",
        seam="provider registration/config diagnostics",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/enrichment/setup.py::build_registry()` now reads `ConfigStore.all_provider_keys()` once and passes key-requiring adapters values from that map instead of calling `get_provider_key()` once per provider. "
            "`app/enrichment/setup.py::_register_keyed_provider()` also centralizes non-VirusTotal keyed adapter construction and registration so those providers share one key-map lookup path. "
            "`_register_zero_auth_provider()` centralizes zero-auth adapter construction and registration so providers that need no API key share one construction path. "
            "Focused proof lives in `tests/test_registry_setup.py::TestBuildRegistry::test_config_store_all_provider_keys_called_once_for_key_providers`, `test_key_required_providers_share_registration_helper`, `test_zero_auth_providers_share_registration_helper`, and `tests/test_emailrep_registry_settings.py::test_build_registry_reads_emailrep_key_from_config_store`, which preserve EmailRep configuration, missing-key behavior, all-provider registration, zero-auth provider setup, and the single provider-key map load."
        ),
        continuity_guardrails="R008, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_registry_setup.py tests/test_emailrep_registry_settings.py tests/test_provider_registry.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve all 16 registered providers, VirusTotal's separate key path, key-required provider configuration semantics, zero-auth provider behavior, EmailRep email-only coverage, and local config failure fallback while avoiding repeated provider-key lookups, duplicated keyed-provider construction paths, and duplicated zero-auth construction paths during registry construction."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep settings provider-key display on one config map read.",
        seam="provider registration/config diagnostics",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/routes/settings.py::settings_get()` now reads `ConfigStore.all_provider_keys()` once and uses that map for provider status display instead of calling `get_provider_key()` once per non-VirusTotal provider. "
            "`app/routes/_helpers.py::_mask_key()` also reuses the configured-key length while building masked display text instead of measuring it twice. "
            "Focused proof lives in `tests/test_settings.py::test_get_settings_reads_provider_key_map_once`, which verifies configured display state while failing if the route falls back to per-provider reads, and `tests/test_settings.py::test_mask_key_measures_configured_key_once`, which preserves masked-key output while failing if configured key masking repeats length work."
        ),
        continuity_guardrails="R008, R009, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_settings.py tests/test_registry_setup.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve settings page provider metadata, masked key display, configured/not-configured badges, VirusTotal's separate key path, cache stats/TTL display, and history-save diagnostics while avoiding repeated provider-key lookups on settings GET and repeated configured-key length work during mask rendering."
        ),
    ),
    BaselineFinding(
        bucket="do now",
        finding="Keep settings provider validation on a precomputed ID set.",
        seam="provider registration/config diagnostics",
        evidence_kind="code-path reasoning + focused regression proof",
        evidence_summary=(
            "`app/routes/settings.py::_VALID_PROVIDER_IDS` now precomputes valid provider IDs once at import time through a direct helper loop, and `settings_post()` reuses that set instead of rebuilding `{p['id'] for p in PROVIDER_INFO}` on every save attempt. "
            "`app/routes/settings.py::_stripped_form_value()` also centralizes settings form value stripping for provider-key saves and cache TTL updates instead of open-coding request form normalization in each POST route. "
            "Focused proof lives in `tests/test_settings.py::test_save_provider_validation_uses_precomputed_id_set`, where `PROVIDER_INFO` is patched to fail if POST validation iterates it and the helper is guarded against generator/set-comprehension frames, plus `tests/test_settings.py::test_settings_post_and_cache_ttl_share_form_normalization`, which proves both POST paths share the stripped-value helper while preserving saved key and TTL values."
        ),
        continuity_guardrails="R008, R009, R010, R040, R085, R087",
        rerun_lanes="`python3 -m pytest -q tests/test_settings.py tests/test_registry_setup.py`; `make verify-fast`",
        continuity_notes=(
            "Preserve settings save validation, unknown-provider rejection, VirusTotal/provider key save routing, registry rebuild behavior, cache TTL validation, flash/redirect flow, and provider metadata rendering while avoiding repeated provider-id set construction, duplicated form-value normalization on settings POST routes, and import-time provider-id generator/comprehension frames."
        ),
    ),
    BaselineFinding(
        bucket="later",
        finding="Defer broader SQLite cache/history access-shape work until contention evidence appears.",
        seam="local cache/history",
        evidence_kind="ranked project-map priority",
        evidence_summary=(
            "`docs/project-map.md` ranks SQLite access shape third, but the `cache-store-tempdb`, `cache-stats-query-count`, and `history-store-tempdb` captures now separate the shipped stats query-count reduction from the still-healthy WAL-backed put/get/save/list/load paths. "
            "Broader persistence work remains deferred until contention or write-amplification evidence appears."
        ),
        continuity_guardrails="R085, R087, R022, R040",
        rerun_lanes="`make verify-fast` plus targeted cache/history fixtures when promoted",
        continuity_notes="Promote broader changes only with contention or write-amplification evidence showing equivalent cache hit, expiry, clear, history list, and history reload behavior with less work.",
    ),
    BaselineFinding(
        bucket="leave alone",
        finding="Leave provider registration/config diagnostics clarity alone for this optimization pass unless readiness diagnostics become the blocker.",
        seam="provider registration/config diagnostics",
        evidence_kind="identity-grounded keep-decision",
        evidence_summary=(
            "The S01 project map ranks this fifth: it supports analyst confidence and secret-redaction boundaries, but it is not the best current performance target for the paste → enrich → review loop."
        ),
        continuity_guardrails="R085, R087, D080",
        rerun_lanes="`make verify-fast` if settings/diagnostics code changes",
        continuity_notes="Do not expose API keys, tokens, or analyst-sensitive IOC data in audit artifacts, settings output, diagnostics, or command captures.",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the ranked SentinelX optimization-audit artifact. Findings must cite "
            "measurement when practical or explicit code-path reasoning otherwise."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=("template", "baseline"),
        default="template",
        help="template = scaffold the ranked artifact; baseline = write the working audit file (default: template)",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"Output markdown path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--milestone-id",
        default=DEFAULT_MILESTONE_ID,
        help=f"Milestone identifier to print in the artifact (default: {DEFAULT_MILESTONE_ID})",
    )
    parser.add_argument(
        "--repo-name",
        default="SentinelX",
        help="Repository/product name printed in the artifact (default: SentinelX)",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root used for command captures (default: current directory)",
    )
    parser.add_argument(
        "--capture-command",
        action="append",
        default=[],
        metavar="LABEL::COMMAND",
        help=(
            "Run a command, record duration/exit code, and include its summary in the artifact. "
            "Repeat for multiple captures."
        ),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=1800,
        help="Per capture-command timeout in seconds (default: 1800)",
    )
    return parser.parse_args()


def parse_capture_spec(spec: str) -> tuple[str, str]:
    delimiter = spec.find("::")
    if delimiter < 0:
        raise ValueError(
            f"Invalid capture spec '{spec}'. Use LABEL::COMMAND so the artifact can name the measurement clearly."
        )
    label = stripped_text_or_none(spec[:delimiter])
    command = stripped_text_or_none(spec[delimiter + 2:])
    if label is None or command is None:
        raise ValueError(
            f"Invalid capture spec '{spec}'. Both LABEL and COMMAND are required."
        )
    return label, command


def summarize_output(stdout: str, stderr: str) -> str:
    combined: deque[str] = deque(maxlen=3)
    for stream in (stdout, stderr):
        for line in StringIO(stream):
            cleaned = collapse_whitespace(line)
            if cleaned:
                combined.append(cleaned)
    if not combined:
        return "No stdout/stderr output captured."
    summary = " | ".join(combined)
    if len(summary) > 220:
        summary = _rstrip_whitespace(summary[:217]) + "..."
    return summary


def _rstrip_whitespace(value: str) -> str:
    end = len(value)
    while end > 0 and value[end - 1].isspace():
        end -= 1
    return value[:end]


def run_capture_command(spec: str, repo_root: Path, timeout_seconds: int) -> CommandCapture:
    label, command = parse_capture_spec(spec)
    started = utc_now()
    try:
        completed = subprocess.run(
            shlex.split(command),
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        finished = utc_now()
        duration_ms = int((finished - started).total_seconds() * 1000)
        return CommandCapture(
            label=label,
            command=command,
            exit_code=completed.returncode,
            duration_ms=duration_ms,
            summary=summarize_output(completed.stdout, completed.stderr),
        )
    except subprocess.TimeoutExpired:
        finished = utc_now()
        duration_ms = int((finished - started).total_seconds() * 1000)
        return CommandCapture(
            label=label,
            command=command,
            exit_code=124,
            duration_ms=duration_ms,
            summary=f"Timed out after {timeout_seconds}s while running: {command}",
        )
    except OSError as exc:
        finished = utc_now()
        duration_ms = int((finished - started).total_seconds() * 1000)
        return CommandCapture(
            label=label,
            command=command,
            exit_code=127,
            duration_ms=duration_ms,
            summary=f"Failed to launch command: {exc}",
        )


def run_internal_capture(label: str, command: str, measure: callable) -> CommandCapture:
    started = utc_now()
    try:
        summary = measure()
        finished = utc_now()
        duration_ms = int((finished - started).total_seconds() * 1000)
        return CommandCapture(
            label=label,
            command=command,
            exit_code=0,
            duration_ms=duration_ms,
            summary=summary,
        )
    except Exception as exc:  # pragma: no cover - defensive audit failure path
        finished = utc_now()
        duration_ms = int((finished - started).total_seconds() * 1000)
        return CommandCapture(
            label=label,
            command=command,
            exit_code=1,
            duration_ms=duration_ms,
            summary=f"Internal measurement failed: {exc.__class__.__name__}: {exc}",
        )


def _require_non_negative_int(metrics: object, field: str, *, context: str) -> int:
    if not isinstance(metrics, dict):
        raise ValueError(f"Runtime/provider capture failed: {context} metrics are not a dict.")
    value = metrics.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(
            f"Runtime/provider capture failed: {context} field '{field}' must be a non-negative integer."
        )
    return value


def _require_non_negative_float(metrics: object, field: str, *, context: str) -> float:
    if not isinstance(metrics, dict):
        raise ValueError(f"Runtime/provider capture failed: {context} metrics are not a dict.")
    value = metrics.get(field)
    if not isinstance(value, (int, float)) or value < 0:
        raise ValueError(
            f"Runtime/provider capture failed: {context} field '{field}' must be a non-negative number."
        )
    return float(value)


def _render_runtime_provider_mix(providers: object) -> str:
    if not isinstance(providers, dict) or not providers:
        raise ValueError("Runtime/provider capture failed: provider diagnostics are empty.")

    provider_names = _ordered_provider_names(providers)
    provider_count = len(provider_names)
    if provider_count == 1:
        provider_name = provider_names[0]
        return _runtime_provider_mix_entry(provider_name, providers[provider_name])
    if provider_count == 2:
        first = provider_names[0]
        second = provider_names[1]
        return (
            _runtime_provider_mix_entry(first, providers[first])
            + ", "
            + _runtime_provider_mix_entry(second, providers[second])
        )

    entries: list[str] = []
    for provider_name in provider_names:
        entries.append(_runtime_provider_mix_entry(provider_name, providers[provider_name]))
    return ", ".join(entries)


def _runtime_provider_mix_entry(provider_name: str, provider_metrics: object) -> str:
    missing = _missing_runtime_fields(RUNTIME_PROVIDER_PROVIDER_FIELDS, provider_metrics)
    if missing:
        raise ValueError(
            "Runtime/provider capture failed: provider "
            f"'{provider_name}' is missing fields: {_format_runtime_fields(missing)}"
        )
    dispatch_count = _require_non_negative_int(
        provider_metrics,
        "dispatch_count",
        context=f"provider '{provider_name}'",
    )
    error_count = _require_non_negative_int(
        provider_metrics,
        "error_count",
        context=f"provider '{provider_name}'",
    )
    return f"{provider_name}:{dispatch_count}d/{error_count}e"


def _ordered_provider_names(providers: dict[str, object]) -> tuple[str, ...]:
    provider_count = len(providers)
    if provider_count == 0:
        return ()
    if provider_count == 1:
        for provider_name in providers:
            return (provider_name,)
    if provider_count == 2:
        provider_iter = iter(providers)
        first = next(provider_iter)
        second = next(provider_iter)
        if first <= second:
            return (first, second)
        return (second, first)
    return tuple(sorted(providers))


def _ordered_strings(values: set[str]) -> tuple[str, ...]:
    value_count = len(values)
    if value_count == 0:
        return ()
    if value_count == 1:
        for value in values:
            return (value,)
    if value_count == 2:
        value_iter = iter(values)
        first = next(value_iter)
        second = next(value_iter)
        if first <= second:
            return (first, second)
        return (second, first)
    return tuple(sorted(values))


def _missing_runtime_fields(expected_fields: tuple[str, ...], payload: object) -> tuple[str, ...]:
    missing: list[str] = []
    if not isinstance(payload, dict):
        return expected_fields
    for field in expected_fields:
        if field not in payload:
            missing.append(field)
    return tuple(missing)


def _format_runtime_fields(fields: tuple[str, ...]) -> str:
    field_count = len(fields)
    if field_count == 0:
        return ""
    if field_count == 1:
        return fields[0]
    if field_count == 2:
        return fields[0] + ", " + fields[1]
    return ", ".join(fields)


def summarize_runtime_provider_diagnostics(diagnostics: object) -> str:
    if not isinstance(diagnostics, dict):
        raise ValueError("Runtime/provider capture failed: diagnostics snapshot is not a dict.")

    missing = _missing_runtime_fields(RUNTIME_PROVIDER_DIAGNOSTIC_FIELDS, diagnostics)
    if missing:
        raise ValueError(
            "Runtime/provider capture failed: missing diagnostics fields: "
            + _format_runtime_fields(missing)
        )

    provider_mix = _render_runtime_provider_mix(diagnostics.get("providers"))
    dispatch_count = _require_non_negative_int(
        diagnostics,
        "dispatch_count",
        context="job",
    )
    attempt_count = _require_non_negative_int(
        diagnostics,
        "attempt_count",
        context="job",
    )
    cache_hits = _require_non_negative_int(diagnostics, "cache_hits", context="job")
    cache_misses = _require_non_negative_int(diagnostics, "cache_misses", context="job")
    retry_count = _require_non_negative_int(diagnostics, "retry_count", context="job")
    rate_limit_retry_count = _require_non_negative_int(
        diagnostics,
        "rate_limit_retry_count",
        context="job",
    )
    error_count = _require_non_negative_int(diagnostics, "error_count", context="job")
    latency_total_seconds = _require_non_negative_float(
        diagnostics,
        "latency_total_seconds",
        context="job",
    )
    latency_max_seconds = _require_non_negative_float(
        diagnostics,
        "latency_max_seconds",
        context="job",
    )

    cache_total = cache_hits + cache_misses
    cache_hit_ratio = (cache_hits / cache_total * 100.0) if cache_total else 0.0
    return (
        f"provider mix {provider_mix}; dispatch={dispatch_count}; attempts={attempt_count}; "
        f"cache-hit ratio {cache_hits}/{cache_total} ({cache_hit_ratio:.0f}%); "
        f"retries={retry_count} (429={rate_limit_retry_count}); errors={error_count}; "
        f"latency total={latency_total_seconds:.2f}s max={latency_max_seconds:.2f}s."
    )


def measure_runtime_provider_diagnostics() -> str:
    from app.enrichment.models import EnrichmentError, EnrichmentResult
    from app.enrichment.orchestrator import EnrichmentOrchestrator
    from app.pipeline.models import IOC, IOCType

    class SyntheticCache:
        def __init__(self) -> None:
            self._rows = {
                ("198.51.100.10", "ipv4", "CacheAlpha"): {
                    "provider": "CacheAlpha",
                    "verdict": "clean",
                    "detection_count": 0,
                    "total_engines": 12,
                    "scan_date": None,
                    "raw_stats": {},
                    "cached_at": "2026-04-24T00:00:00Z",
                }
            }

        def get(self, value: str, type_: str, provider: str, ttl_seconds: int) -> dict | None:
            row = self._rows.get((value, type_, provider))
            if row is None:
                return None
            snapshot: dict[str, object] = {}
            for key in row:
                snapshot[key] = row[key]
            return snapshot

        def put(self, value: str, type_: str, provider: str, payload: dict) -> None:
            row: dict[str, object] = {}
            for key in payload:
                row[key] = payload[key]
            row["cached_at"] = "2026-04-24T00:00:00Z"
            self._rows[(value, type_, provider)] = row

    class ScriptedAdapter:
        supported_types = {IOCType.IPV4}

        def __init__(self, name: str, requires_api_key: bool, outcomes: dict[str, list[object]]) -> None:
            self.name = name
            self.requires_api_key = requires_api_key
            self._outcomes: dict[str, list[object]] = {}
            for ioc_value in outcomes:
                copied_results: list[object] = []
                for result in outcomes[ioc_value]:
                    copied_results.append(result)
                self._outcomes[ioc_value] = copied_results

        def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
            queue = self._outcomes[ioc.value]
            return queue.pop(0)

    def make_ioc(value: str) -> IOC:
        return IOC(type=IOCType.IPV4, value=value, raw_match=value)

    def make_result(ioc: IOC, provider: str) -> EnrichmentResult:
        return EnrichmentResult(
            ioc=ioc,
            provider=provider,
            verdict="clean",
            detection_count=0,
            total_engines=12,
            scan_date=None,
            raw_stats={},
        )

    def make_error(ioc: IOC, provider: str, message: str) -> EnrichmentError:
        return EnrichmentError(ioc=ioc, provider=provider, error=message)

    cache_hit_ioc = make_ioc("198.51.100.10")
    retry_ioc = make_ioc("198.51.100.11")
    cache_adapter = ScriptedAdapter(
        name="CacheAlpha",
        requires_api_key=False,
        outcomes={retry_ioc.value: [make_result(retry_ioc, "CacheAlpha")]},
    )
    rate_adapter = ScriptedAdapter(
        name="RateLimitBeta",
        requires_api_key=True,
        outcomes={
            cache_hit_ioc.value: [make_result(cache_hit_ioc, "RateLimitBeta")],
            retry_ioc.value: [
                make_error(retry_ioc, "RateLimitBeta", "HTTP 429"),
                make_result(retry_ioc, "RateLimitBeta"),
            ],
        },
    )

    orchestrator = EnrichmentOrchestrator(
        adapters=[cache_adapter, rate_adapter],
        max_workers=1,
        cache=SyntheticCache(),
        provider_concurrency={"RateLimitBeta": 1},
    )

    with patch(
        "app.enrichment.orchestrator.time.perf_counter",
        side_effect=[0.0, 0.25, 1.0, 1.5, 2.0, 2.25, 3.0, 4.0, 5.0, 5.25],
    ), patch("app.enrichment.orchestrator.time.sleep"), patch(
        "app.enrichment.orchestrator.random.uniform",
        return_value=0.0,
    ):
        orchestrator.enrich_all("runtime-provider-audit", [cache_hit_ioc, retry_ioc])

    diagnostics = orchestrator.get_diagnostics("runtime-provider-audit")
    return summarize_runtime_provider_diagnostics(diagnostics)


def measure_status_snapshot_scaling() -> str:
    from app.enrichment.orchestrator import EnrichmentOrchestrator

    orchestrator = EnrichmentOrchestrator(adapters=[])
    iterations = 400
    retained_results = 5000
    tail_count = 10
    since = retained_results - tail_count
    retained_payload: list[int] = []
    for value in range(retained_results):
        retained_payload.append(value)

    with orchestrator._lock:
        orchestrator._jobs["bench"] = {
            "total": retained_results,
            "done": retained_results,
            "results": retained_payload,
            "complete": True,
            "status": "complete",
            "terminal": False,
            "terminal_reason": None,
            "error": None,
        }

    start = perf_counter()
    for _ in range(iterations):
        full_snapshot = orchestrator.get_status("bench")
    full_ms = (perf_counter() - start) * 1000

    start = perf_counter()
    for _ in range(iterations):
        incremental_snapshot = orchestrator.get_incremental_status("bench", since=since)
    incremental_ms = (perf_counter() - start) * 1000

    returned_rows = (
        len(incremental_snapshot["results"])
        if isinstance(incremental_snapshot, dict)
        else 0
    )
    next_since = (
        incremental_snapshot.get("next_since")
        if isinstance(incremental_snapshot, dict)
        else None
    )
    speedup = full_ms / incremental_ms if incremental_ms > 0 else 0.0
    retained_count = (
        len(full_snapshot["results"])
        if isinstance(full_snapshot, dict)
        else retained_results
    )
    return (
        f"{iterations} polls at {retained_count} retained results: `get_status()` {full_ms:.2f}ms vs "
        f"`get_incremental_status(since={since})` {incremental_ms:.2f}ms ({speedup:.1f}x faster) while returning "
        f"{returned_rows} tail rows with next_since={next_since}."
    )


def measure_cache_store_tempdb() -> str:
    from app.cache.store import CacheStore

    with TemporaryDirectory() as tmp_dir:
        store = CacheStore(db_path=Path(tmp_dir) / "cache.db")
        count = 250

        start = perf_counter()
        for i in range(count):
            store.put(
                f"198.51.100.{i}",
                "ipv4",
                "VirusTotal",
                {
                    "provider": "VirusTotal",
                    "verdict": "clean",
                    "detection_count": 0,
                    "total_engines": 90,
                    "scan_date": None,
                    "raw_stats": {},
                },
            )
        put_ms = (perf_counter() - start) * 1000

        start = perf_counter()
        hits = 0
        for i in range(count):
            row = store.get(f"198.51.100.{i}", "ipv4", "VirusTotal", ttl_seconds=3600)
            hits += 1 if row is not None else 0
        get_ms = (perf_counter() - start) * 1000

        stats = store.stats()
    return (
        f"Temp WAL cache DB: {count} puts in {put_ms:.2f}ms, {count} TTL reads in {get_ms:.2f}ms, "
        f"{hits} hits, {stats['total_entries']} retained rows."
    )


def measure_cache_stats_query_count() -> str:
    from app.cache.store import CacheStore

    with TemporaryDirectory() as tmp_dir:
        store = CacheStore(db_path=Path(tmp_dir) / "cache.db")
        store.put(
            "198.51.100.10",
            "ipv4",
            "VirusTotal",
            {
                "provider": "VirusTotal",
                "verdict": "clean",
                "detection_count": 0,
                "total_engines": 90,
                "scan_date": None,
                "raw_stats": {},
            },
        )
        statements: list[str] = []
        store._conn.set_trace_callback(statements.append)
        try:
            stats = store.stats()
        finally:
            store._conn.set_trace_callback(None)

    select_count = 0
    first_select = "none"
    for statement in statements:
        if _is_select_statement(statement):
            select_count += 1
            if first_select == "none":
                first_select = statement
    return (
        f"CacheStore.stats() executed {select_count} SELECT for total_entries={stats['total_entries']} "
        f"and oldest_present={stats['oldest'] is not None}: {first_select}."
    )


def _is_select_statement(statement: str) -> bool:
    start = 0
    end = len(statement)
    while start < end and statement[start].isspace():
        start += 1
    return statement[start:start + 6].casefold() == "select"


def measure_history_store_tempdb() -> str:
    from app.enrichment.history_store import HistoryStore

    with TemporaryDirectory() as tmp_dir:
        store = HistoryStore(db_path=Path(tmp_dir) / "history.db")
        count = 180

        start = perf_counter()
        analysis_ids = []
        for i in range(count):
            analysis_ids.append(
                store.save_analysis(
                    input_text=f"ioc {i}",
                    mode="online",
                    iocs=[{"type": "ipv4", "value": f"203.0.113.{i}", "raw_match": f"203.0.113.{i}"}],
                    results=[{"type": "result", "verdict": "clean"}],
                )
            )
        save_ms = (perf_counter() - start) * 1000

        start = perf_counter()
        recent = store.list_recent(limit=20)
        recent_ms = (perf_counter() - start) * 1000

        start = perf_counter()
        loaded = store.load_analysis(analysis_ids[-1])
        load_ms = (perf_counter() - start) * 1000

    loaded_count = loaded["total_count"] if isinstance(loaded, dict) else 0
    return (
        f"Temp WAL history DB: {count} saves in {save_ms:.2f}ms, list_recent(20) in {recent_ms:.2f}ms, "
        f"single load in {load_ms:.2f}ms, latest total_count={loaded_count}, recent rows={len(recent)}."
    )


def measure_pipeline_duplicate_candidates() -> str:
    import app.pipeline.extractor as extractor

    raw_variants = [
        "hxxp://evil[.]com",
        "hxxp://evil(.)com",
        "hxxp://evil{.}com",
        "hxxp://evil[dot]com",
        "hxxp://evil(dot)com",
        "hxxp://evil{dot}com",
        "hxxp://evil_dot_com",
    ]
    original_classify = extractor.classify
    classify_calls = 0

    def fake_extract_iocs(_text: str) -> list[dict]:
        return [{"raw": raw, "type_hint": "url"} for raw in raw_variants]

    def counting_classify(normalized_value: str, raw_match: str):
        nonlocal classify_calls
        classify_calls += 1
        return original_classify(normalized_value, raw_match)

    with patch("app.pipeline.extractor.extract_iocs", fake_extract_iocs), patch(
        "app.pipeline.extractor.classify",
        counting_classify,
    ):
        results = extractor.run_pipeline("pipeline duplicate candidate audit")

    value_set: set[str] = set()
    for ioc in results:
        value_set.add(ioc.value)
    values = _ordered_strings(value_set)
    return (
        f"{len(raw_variants)} raw URL variants normalize to {len(values)} IOC value(s); "
        f"classify calls={classify_calls}; output values={', '.join(values)}."
    )


def collect_baseline_captures() -> list[CommandCapture]:
    return [
        run_internal_capture(
            label="runtime-provider-diagnostics",
            command="internal benchmark: EnrichmentOrchestrator synthetic runtime/provider diagnostics",
            measure=measure_runtime_provider_diagnostics,
        ),
        run_internal_capture(
            label="status-snapshot-scaling",
            command="internal benchmark: EnrichmentOrchestrator.get_status() snapshot scaling",
            measure=measure_status_snapshot_scaling,
        ),
        run_internal_capture(
            label="cache-store-tempdb",
            command="internal benchmark: CacheStore temp WAL put/get loop",
            measure=measure_cache_store_tempdb,
        ),
        run_internal_capture(
            label="cache-stats-query-count",
            command="internal benchmark: CacheStore.stats aggregate query count",
            measure=measure_cache_stats_query_count,
        ),
        run_internal_capture(
            label="history-store-tempdb",
            command="internal benchmark: HistoryStore temp WAL save/list/load loop",
            measure=measure_history_store_tempdb,
        ),
        run_internal_capture(
            label="pipeline-duplicate-candidates",
            command="internal benchmark: run_pipeline normalized duplicate candidate gate",
            measure=measure_pipeline_duplicate_candidates,
        ),
    ]


def bucket_table_placeholder(bucket: str) -> str:
    sample_guardrails = {
        "do now": "R040 plus the seam-specific continuity rules this finding could regress today.",
        "do next": "List the guardrails that stay relevant after the current high-confidence fix ships.",
        "later": "Call out why this stays deferred without losing current behavior/security guarantees.",
        "leave alone": "Name the proof showing the current seam is already intentionally shaped.",
    }[bucket]
    sample_rerun = {
        "do now": "`make verify-fast`; add `make verify-deep` for live-stack or DOM-state changes.",
        "do next": "Usually `make verify-fast`; escalate to `make verify` if the future change spans multiple seams.",
        "later": "Document the future lane now so the next slice does not need to reconstruct it.",
        "leave alone": "Record the lane that would need to fail before this bucket should be reconsidered.",
    }[bucket]
    return "\n".join(
        [
            "| Finding | Seam | Evidence kind | Evidence summary | Continuity guardrails | Rerun lanes | Continuity notes |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            (
                f"| _Fill during the {bucket} pass_ | runtime/provider, request/status, persistence, or frontend/render "
                f"| measurement or code-path reasoning | cite timing, command output, or the exact path reasoning "
                f"| {sample_guardrails} | {sample_rerun} | State what must remain true after any optimization ships. |"
            ),
        ]
    )


def render_measurement_section(captures: list[CommandCapture]) -> str:
    if not captures:
        return "No measurement commands were captured in this run. Use `--capture-command LABEL::COMMAND` to add timing metadata and command summaries."

    lines = [
        "| Capture | Command | Exit | Duration (ms) | Summary |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for capture in captures:
        safe_summary = capture.summary.replace("|", "\\|")
        lines.append(
            f"| {capture.label} | `{capture.command}` | {capture.exit_code} | {capture.duration_ms} | {safe_summary} |"
        )
    return "\n".join(lines)


def render_lanes_section() -> str:
    lines = [
        "| Lane | Command | Use when |",
        "| --- | --- | --- |",
    ]
    for lane in VERIFICATION_LANES:
        lines.append(f"| {lane.name} | `{lane.command}` | {lane.use_when} |")
    return "\n".join(lines)


def render_rerun_checklist_section() -> str:
    return "\n".join(
        [
            "| Step | Proof surface | Command | Required when | Expected durable evidence |",
            "| --- | --- | --- | --- | --- |",
            "| 1 | Workflow runner + ranked artifact refresh | `python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md` | Every optimization slice before handoff. | Updated M013 audit artifact with current ranked buckets, seam notes, and continuity guardrails. |",
            "| 2 | Fast local regression lane | `make verify-fast` | Every shipped optimization, including keep-decisions that changed code or build/test plumbing. | Fresh command capture or task summary evidence proving unit/integration/frontend/build checks stayed green. |",
            "| 3 | Deterministic mocked-online browser proof | `make verify-deep` | Any change touching live enrichment orchestration, polling/status flow, shared result application, or analyst-visible DOM/state. | Fresh command capture or task summary evidence proving the mocked-online browser seam still passes end-to-end. |",
            "| 4 | Final comparison + continuity note refresh | compare the updated ranked row(s), rerun lanes, and continuity notes in `.gsd/milestones/M013/M013-AUDIT.md` | Every optimization slice after verification completes. | The artifact records whether the change shipped, moved buckets, stayed deferred, or remained an explicit leave-alone decision. |",
        ]
    )


def render_guardrails_section() -> str:
    lines = [
        "| Requirement | Continuity guardrail |",
        "| --- | --- |",
    ]
    for guardrail in GUARDRAILS:
        lines.append(f"| {guardrail.requirement_id} | {guardrail.summary} |")
    return "\n".join(lines)


def render_seams_section() -> str:
    lines: list[str] = []
    for seam in SEAMS:
        lines.append(f"### {seam.name}")
        lines.append("")
        lines.append(f"- Continuity focus: {seam.continuity_focus}")
        lines.append(f"- Audit prompt 1: {seam.prompts[0]}")
        lines.append(f"- Audit prompt 2: {seam.prompts[1]}")
        lines.append("")
    return _join_lines_trimmed(lines)


def render_findings_table(findings: list[BaselineFinding]) -> str:
    lines = [
        "| Finding | Seam | Evidence kind | Evidence summary | Continuity guardrails | Rerun lanes | Continuity notes |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for finding in findings:
        lines.append(
            f"| {finding.finding} | {finding.seam} | {finding.evidence_kind} | "
            f"{finding.evidence_summary} | {finding.continuity_guardrails} | "
            f"{finding.rerun_lanes} | {finding.continuity_notes} |"
        )
    return "\n".join(lines)


def render_baseline_ranked_findings() -> str:
    lines: list[str] = []
    for bucket in FINDING_BUCKETS:
        lines.append(f"### {bucket}")
        lines.append("")
        bucket_findings = _findings_for_bucket(BASELINE_FINDINGS, bucket)
        lines.append(render_findings_table(bucket_findings))
        lines.append("")
    return _join_lines_trimmed(lines)


def _findings_for_bucket(findings: tuple[BaselineFinding, ...], bucket: str) -> list[BaselineFinding]:
    bucket_findings: list[BaselineFinding] = []
    for finding in findings:
        if finding.bucket == bucket:
            bucket_findings.append(finding)
    return bucket_findings


def render_baseline_seam_notes() -> str:
    lines = ["## Per-seam baseline notes", ""]
    for note in BASELINE_SEAM_NOTES:
        lines.append(f"### {note.seam}")
        lines.append("")
        lines.append(f"- Boundary: {note.boundary}")
        lines.append(f"- Current shape: {note.current_shape}")
        lines.append(f"- Continuity watch: {note.continuity_watch}")
        lines.append(f"- Baseline call: {note.baseline_call}")
        lines.append("")
    return _join_lines_trimmed(lines)


def render_baseline_guardrail_coverage() -> str:
    lines = [
        "## Continuity guardrail coverage",
        "",
        "| Requirement | Primary seam(s) in this baseline | Covered by | Continuity notes |",
        "| --- | --- | --- | --- |",
    ]
    for entry in BASELINE_GUARDRAIL_COVERAGE:
        lines.append(
            f"| {entry.requirement_id} | {entry.seam} | {entry.covered_by} | {entry.continuity_notes} |"
        )
    return "\n".join(lines)


def project_map_grounding(repo_root: Path) -> str:
    project_map = repo_root / PROJECT_MAP_PATH
    if not project_map.exists():
        return (
            f"⚠️ `{PROJECT_MAP_PATH}` was not found at generation time. "
            "This artifact cannot truthfully claim full M017 identity grounding or milestone identity grounding until that file is restored; "
            "ranked findings below are retained from the built-in contract as a fallback note."
        )
    return (
        f"`{PROJECT_MAP_PATH}` is present and anchors this audit to SentinelX as a local analyst IOC triage workbench: "
        "paste investigation text, extract IOCs, optionally enrich them, then review verdict-first results with history, details, filters, copy/export, and diagnostics."
    )


def render_m017_ranked_findings() -> str:
    lines: list[str] = []
    for bucket in FINDING_BUCKETS:
        lines.append(f"### {bucket}")
        lines.append("")
        bucket_findings = _findings_for_bucket(M017_FINDINGS, bucket)
        lines.append(render_findings_table(bucket_findings))
        lines.append("")
    return _join_lines_trimmed(lines)


def render_m020_ranked_findings() -> str:
    lines: list[str] = []
    for bucket in FINDING_BUCKETS:
        lines.append(f"### {bucket}")
        lines.append("")
        bucket_findings = _findings_for_bucket(M020_FINDINGS, bucket)
        lines.append(render_findings_table(bucket_findings))
        lines.append("")
    return _join_lines_trimmed(lines)


def _join_lines_trimmed(lines: list[str]) -> str:
    return _rstrip_whitespace("\n".join(lines))


def render_m017_identity_section(document: AuditDocument) -> str:
    return "\n".join(
        [
            "## M017 identity-grounded contract",
            "",
            f"- Project map grounding: {project_map_grounding(document.repo_root)}",
            "- Analyst identity: SentinelX is optimized as a fast local analyst IOC triage workbench, not as generic subsystem cleanup.",
            "- Decisions: D078 requires `docs/project-map.md` and `.gsd/PROJECT.md` before target selection; D079 ranks work by the analyst IOC triage loop; D080 allows aggressive/moderate cross-seam optimization only with proof.",
            "- Requirements: R085 requires product-identity-grounded optimization decisions; R087 requires measurement when practical or explicit code-path reasoning plus regression proof.",
            "- S01 seam inventory priorities: (1) enrichment fan-out/status snapshot cost across `app/enrichment` and `app/routes`, (2) browser result rendering churn, (3) SQLite cache/history access shape, (4) IOC pipeline duplicate candidate handling in `app/pipeline`, (5) provider registration/config diagnostics clarity.",
            "- S03 shipped proof: the do-now M017 optimization is the enrichment fan-out/status snapshot path, with measurement from `status-snapshot-scaling` and code-path proof in `app/enrichment/orchestrator.py::get_incremental_status()` plus `app/routes/_helpers.py::_get_enrichment_status()`.",
            "- Current pipeline proof: the duplicate IOC candidate follow-up now ships in `app/pipeline/extractor.py::run_pipeline()` with `pipeline-duplicate-candidates` measurement and focused `tests/test_pipeline.py` regression proof.",
        ]
    )


def render_m017_rerun_checklist_section() -> str:
    return "\n".join(
        [
            "| Step | Proof surface | Command | Required when | Expected durable evidence |",
            "| --- | --- | --- | --- | --- |",
            "| 1 | M017 workflow runner + identity-grounded ranked artifact refresh | `python3 tools/optimization_audit.py --milestone-id M017 --mode baseline --output .gsd/milestones/M017/M017-AUDIT.md` | Every M017 optimization slice before handoff. | Updated M017 audit artifact citing `docs/project-map.md`, R085/R087, D078-D080, S01 seam priorities, and current ranked buckets. |",
            "| 2 | Fast local regression lane | `make verify-fast` | Every shipped optimization, including keep-decisions that changed code or build/test plumbing. | Fresh command capture or task summary evidence proving unit/integration/frontend/build checks stayed green. |",
            "| 3 | Deterministic mocked-online browser proof | `make verify-deep` | Any change touching live enrichment orchestration, polling/status flow, shared result application, or analyst-visible DOM/state. | Fresh evidence proving the analyst-visible mocked-online browser seam still passes end-to-end. |",
            "| 4 | S04 frontend/render outcome confirmation | Compare `do now` frontend/render rows against T01/T02 focused proof and mocked-online browser evidence | Before S05 final assembly. | Clear shipped-or-rejected decision explaining why the secondary optimization outcome is durable and evidence-backed. |",
        ]
    )


def render_m020_rerun_checklist_section() -> str:
    return "\n".join(
        [
            "| Step | Proof surface | Command | Required when | Expected durable evidence |",
            "| --- | --- | --- | --- | --- |",
            "| 1 | M020 workflow runner + aggressive rewrite artifact refresh | `python3 tools/optimization_audit.py --milestone-id M020 --mode baseline --output .gsd/milestones/M020/M020-AUDIT.md` | Every M020 slice before handoff. | Updated M020 audit artifact with current shipped, rejected, deferred, and leave-alone outcomes. |",
            "| 2 | Focused seam regression lane | Run the target-specific pytest/vitest command listed on the finding row. | Every shipped or explicitly rejected rewrite target. | Fresh focused proof tied to the changed seam or rejection evidence. |",
            "| 3 | Fast local regression lane | `make verify-fast` | Every implementation slice, including audit-runner changes. | Unit, integration, frontend, typecheck, and build proof remain green. |",
            "| 4 | Deterministic mocked-online browser proof | `make verify-deep` | Browser-visible or live-enrichment-visible rewrites. | Analyst-visible mocked-online workflows still pass end-to-end. |",
            "| 5 | Final integration proof | `make verify` plus refreshed generated M020 audit. | S05 closeout. | Final artifact records shipped/rejected outcomes and the full app verification lane passes. |",
        ]
    )


def render_m020_identity_section(document: AuditDocument) -> str:
    return "\n".join(
        [
            "## M020 aggressive rewrite contract",
            "",
            f"- Project map grounding: {project_map_grounding(document.repo_root)}",
            "- Milestone intent: M020 is an audit-led aggressive refactor and deep optimization pass, not a cosmetic cleanup pass.",
            "- Decisions: D081 uses audit-led rewrites; D082 keeps the strict proof bar; D083 preserves the analyst IOC triage loop as the integration contract.",
            "- Requirements: R094 requires this source-generated milestone audit surface; R095 ranks aggressive rewrite candidates; R096 ties shipped or rejected outcomes to evidence; R097 preserves analyst workflows; R098 requires focused, fast, deep, and final verification lanes; R099 preserves diagnostics, failure visibility, and redaction boundaries; R100 records durable generated audit and closeout outcomes.",
            "- deferred-scope constraints: R101 major storage redesign, R102 major UI/product redesign, and R103 new external provider integration are constraints, not shipped optimizations. No new storage redesign, No broad UI/product redesign, and No external provider integration are claimed by M020 evidence; existing local proof only preserves current SQLite WAL-backed stores, analyst-visible surfaces, and current provider integrations.",
        "- S01 produces this generated audit artifact and ranked rewrite list. S02 consumed the highest-confidence route-helper candidate for the S02 route/API/history contract, the analyst-visible route/API/history contract, and S02-S04 analyst-visible contract handoff. S03 shipped the diagnostics policy extraction. S04 measured and rejected/deferred frontend virtualization promotion. S05 refreshes final shipped/rejected outcomes and full verification proof.",
        ]
    )


def render_m020_baseline_sections(document: AuditDocument) -> list[str]:
    return [
        render_m020_identity_section(document),
        "",
        "## Baseline stance",
        "",
        "- Do now: S02 shipped duplicate route IOC grouping and response construction behind shared helpers across analysis, API, and history replay, with focused route/API/history proof.",
        "- Do now: S03 shipped diagnostics sanitization policy extraction, centralizing archive, source, and redaction caps while preserving secret-redaction behavior.",
        "- Do now: S04 measured large-result frontend render pressure and keeps the current severity-change gate; virtualization remains deferred.",
        "- Leave alone: provider concurrency/backoff/session semantics remain explicit keep-decisions unless fresh runtime/provider measurements overturn the M017 evidence.",
        "- Evidence standard: every M020 rewrite must be shipped or rejected with measurement when practical, or explicit code-path reasoning plus focused regression proof; no row should be closed with placeholder prose.",
        "",
        "## Ranked findings",
        "",
        render_m020_ranked_findings(),
        "",
        "## M020 audit notes",
        "",
        "- This baseline intentionally contains no placeholder rows; each bucket records a current do-now/do-next/later/leave-alone decision.",
        "- Re-run with `make audit-m020` after each implementation slice so S05 can consume current shipped/rejected outcome language.",
        "- Failed optional capture commands are recorded in the measurement table with nonzero exits so incomplete proof remains visible rather than hidden.",
    ]


def template_output_for_milestone(milestone_id: str) -> Path:
    if milestone_id == M017_MILESTONE_ID:
        return M017_TEMPLATE_OUTPUT
    if milestone_id == M020_MILESTONE_ID:
        return M020_TEMPLATE_OUTPUT
    return DEFAULT_TEMPLATE_OUTPUT


def baseline_output_for_milestone(milestone_id: str) -> Path:
    if milestone_id == M017_MILESTONE_ID:
        return M017_OUTPUT
    if milestone_id == M020_MILESTONE_ID:
        return M020_OUTPUT
    return DEFAULT_OUTPUT


def convenience_targets_for_milestone(milestone_id: str) -> str:
    if milestone_id == M017_MILESTONE_ID:
        return "`make audit-m017-template` / `make audit-m017`"
    if milestone_id == M020_MILESTONE_ID:
        return "`make audit-m020-template` / `make audit-m020`"
    return "`make audit-m013-template` / `make audit-m013`"


def render_rerun_checklist_for_milestone(milestone_id: str) -> str:
    if milestone_id == M017_MILESTONE_ID:
        return render_m017_rerun_checklist_section()
    if milestone_id == M020_MILESTONE_ID:
        return render_m020_rerun_checklist_section()
    return render_rerun_checklist_section()


def render_m017_baseline_sections(document: AuditDocument) -> list[str]:
    return [
        render_m017_identity_section(document),
        "",
        "## Baseline stance",
        "",
        "- Do now: S03 shipped the enrichment fan-out/status snapshot optimization, the highest-ranked S01 seam in SentinelX's analyst IOC triage loop, with `status-snapshot-scaling` measurement and explicit route/orchestrator code-path proof.",
        "- Do now: incremental status snapshots now return empty out-of-range cursor tails before walking retained results.",
        "- Do now: polling result serialization now reuses one cached-marker map lookup per payload and skips per-result cache-key lookup work when the marker map is empty.",
        "- Do now: S04 shipped the secondary frontend/render optimization by keeping shared result application on the severity-change gate, so provider-only/no-op flushes skip global dashboard recount/reorder while severity-changing flushes still update counts and order.",
        "- Do now: live polling progress updates now reuse init-time progress element handles instead of re-querying the same IDs per status payload.",
        "- Do now: summary-row cached timestamp selection now uses a single-pass oldest lookup instead of filter/map/sort allocation.",
        "- Do now: inline context snippet formatting now builds ASN and DNS text directly instead of using temporary arrays and joins.",
        "- Do now: no-data summary insertion now scans section children once instead of querying and allocating a NodeList.",
        "- Do now: summary attribution now uses a single-pass best-candidate scan instead of filter/copy/sort allocation.",
        "- Do now: summary worst-verdict computation now combines known-good override and severity tracking in one scan.",
        "- Do now: exported worst-entry lookup now caches severity and short-circuits once malicious is found.",
        "- Do now: result-application severity detection now compares dirty IOC verdict changes during flush instead of taking whole-grid before/after snapshots.",
        "- Do now: provider-count metadata parsing now caches parsed DOM JSON by raw attribute value and reparses only when that value changes.",
        "- Do now: provider detail-row sorting now caches row severity in an indexed NodeList pass before sorting instead of recomputing it in comparator calls or allocating through Array.from/map.",
        "- Do now: export dropdown actions now use one delegated dropdown listener instead of per-action button listeners.",
        "- Do now: IOC card sorting now caches card severity in an indexed NodeList pass before sorting instead of recomputing it in comparator calls or allocating through Array.from/map.",
        "- Do now: card verdict label updates now share one classList-based helper instead of duplicated className split/filter/join logic.",
        "- Do now: filter applications now reuse init-time static card/control node lists with indexed NodeList loops instead of re-querying them or using callback iteration on every filter change.",
        "- Do now: card stagger initialization now applies capped CSS indexes with indexed NodeList iteration instead of callback iteration.",
        "- Do now: copy buttons now use one delegated document click handler instead of attaching a listener per button at init.",
        "- Do now: form initialization now reuses one element lookup bundle across submit, auto-grow, and mode-toggle helpers.",
        "- Do now: settings accordion updates now reuse init-time header references with indexed loops instead of querying headers or callback-iterating records on every expansion.",
        "- Do now: settings initialization now reuses one settings-section query with indexed NodeList loops for accordion and key-toggle setup.",
        "- Do now: dashboard verdict-count updates now scan count elements once with indexed NodeList loops and use a precomputed verdict set instead of querying once per bucket or scanning the verdict tuple per count element.",
        "- Do now: frontend export text construction now accumulates CSV and copy-all IOC text directly instead of collecting row/value strings in secondary arrays before joining.",
        "- Do now: frontend CSV exports now use a literal static header instead of joining a columns array at module load.",
        "- Do now: IOC detail graph setup now splits nodes and indexes providers in single-pass loops instead of extra array helper passes.",
        "- Do now: browser-route provider-count metadata and coverage counts now use registry direct count paths instead of allocating provider lists for count-only metadata.",
        "- Do now: Online fanout admission diagnostics now use cached direct provider counts instead of allocating provider lists per IOC type.",
        "- Do now: browser-route enrichable progress totals now reuse admission fanout counts instead of repeating same-type registry scans after launch.",
        "- Do now: online routes now reuse the configured-provider list across admission, coverage metadata, and orchestrator launch, and skip provider setup entirely for zero-IOC submissions.",
        "- Do now: API health registry detail now uses direct registered/configured count paths instead of allocating provider lists for count-only metadata.",
        "- Do now: health payload construction and validation now reuse precomputed check order/key sets instead of sorting or allocating static validation sets on every request.",
        "- Do now: shared health/diagnostic contract frozensets now use tuple inputs instead of temporary set literals at module import.",
        "- Do now: API analyze responses now serialize and group each IOC in one pass only after online admission checks pass.",
        "- Do now: browser analyze responses now group template IOCs directly in the route only after online missing-provider redirects are ruled out.",
        "- Do now: history reload now rebuilds and groups persisted IOC models in one pass, skips empty-history grouping, and returns the empty replay JSON literal without invoking the JSON encoder.",
        "- Do now: IOC detail routes now use a precomputed valid-type set instead of rebuilding it per request.",
        "- Do now: orchestration diagnostic export coercion now applies top-level, nested dict, and list caps with bounded key/list iteration instead of materializing bounded copies or allocating mapping items views before filtering.",
        "- Do now: orchestration diagnostic export list coercion now accumulates primitive list values directly instead of using a list-comprehension frame.",
        "- Do now: diagnostic source sanitization now applies mapping and sequence caps with bounded iteration instead of materializing full containers before slicing.",
        "- Do now: recent-history diagnostic payloads now use bounded iteration over returned rows instead of slicing a second list after the store-level limit.",
        "- Do now: diagnostic safe-error summary normalization now uses a compiled whitespace regex instead of split/join word-list allocation.",
        "- Do now: diagnostic archive path validation now scans path segments once instead of allocating split-list parts and rescanning them.",
        "- Do now: diagnostic provider-label normalization now reuses a compiled cleanup regex instead of module-level `re.sub()` calls.",
        "- Do now: diagnostic configured-secret candidate ordering now skips list sorting for zero or one candidate while preserving longest-secret-first ordering for overlapping multi-secret redaction.",
        "- Do now: IOC normalization now skips defang regex substitutions for already-clean values with no known defang sentinel.",
        "- Do now: the IOC pipeline now skips repeated classification for raw variants that normalize to the same canonical value, preserving first-match output semantics with focused regression proof.",
        "- Do now: IP classification now parses candidates once instead of probing IPv6 and IPv4 separately.",
        "- Do now: domain classification now reuses one lowercase value for blacklist lookup and IOC output.",
        "- Do now: raw IOC extraction now appends first-seen candidates directly while tracking a seen-raw set instead of returning dict values.",
        "- Do now: SSH auth.log parsing now streams lines, parses BSD timestamps directly, and caches repeated source classification instead of materializing full uploads, calling `strptime()`, or reparsing duplicate sources.",
        "- Do now: `CacheStore.stats()` now uses one aggregate SQLite query for total entries and oldest timestamp, backed by query-count proof.",
        "- Do now: nonpositive cache TTL reads now return before SQLite because such entries cannot be fresh.",
        "- Do now: empty cache read/write payloads now use JSON literals instead of invoking the encoder or decoder for empty result payloads.",
        "- Do now: cache/history SQLite PRAGMA setup now lives in one shared helper, preserving WAL behavior while removing duplicated store initialization code.",
        "- Do now: recent-history summaries now project the 120-character input preview in SQLite while full history reload preserves the saved input.",
        "- Do now: empty history save/load payloads now use JSON literals instead of invoking the encoder or decoder for empty IOC/result lists.",
        "- Do now: history top-verdict computation now short-circuits once a malicious verdict is found, preserving severity semantics with focused proof.",
        "- Do now: registry scans now avoid provider values views and list-comprehension frames for configured-provider filters, and provider-count lookups count matching providers with a direct counter loop instead of allocating an intermediate provider list, values view, or sum-generator path.",
        "- Do now: static adapter membership frozensets now use tuple inputs instead of temporary set literals at module import.",
        "- Do now: DNS record extraction now uses table-driven extractors instead of per-record-type branch dispatch after each resolver call, and DNS result construction now uses one informational provider envelope helper.",
        "- Do now: DNS TXT extraction now decodes single-chunk records directly and only joins multi-chunk TXT records when needed.",
        "- Do now: Team Cymru ASN TXT decoding now skips join iteration for common single-chunk answers while preserving segmented TXT concatenation.",
        "- Do now: VirusTotal stats parsing still computes engine totals in one scan, while supported IOC types now derive from endpoint routing and result construction uses one provider envelope helper.",
        "- Do now: EmailRep malicious verdict selection now reuses the ordered risk-flag scan instead of rescanning malicious flags, and EmailRep result construction now uses one provider envelope helper.",
        "- Do now: AbuseIPDB result construction now uses one provider envelope helper for parsed score-threshold responses.",
        "- Do now: crt.sh certificate parsing still uses one body scan while result construction now uses one informational provider envelope helper.",
        "- Do now: crt.sh subdomain selection now skips sorting empty or single-subdomain sets while preserving sorted multi-subdomain output and oversized caps.",
        "- Do now: Shodan result construction now uses one provider envelope helper for 404 and parsed InternetDB responses.",
        "- Do now: ThreatFox best-record selection now short-circuits when a perfect confidence record is seen instead of callback-scanning every record, and ThreatFox result construction now uses one provider envelope helper.",
        "- Do now: WHOIS name-server normalization now reuses already-materialized lists instead of copying them, and WHOIS result construction now uses one informational provider envelope helper.",
        "- Do now: HTTP adapters now cache allowed-host membership as a frozenset at construction instead of rescanning the caller's allowlist for every SSRF validation.",
        "- Do now: route-mapped HTTP adapters now derive supported IOC types from endpoint maps instead of repeating equivalent frozenset literals, and Hashlookup/OTX/URLhaus result construction now uses provider envelope helpers.",
        "- Do now: MalwareBazaar result construction now uses one provider envelope helper for found and not-found responses.",
        "- Do now: GreyNoise result construction now uses one provider envelope helper for 404 and parsed Community API responses.",
        "- Do now: ConfigStore writes now keep the just-written parser cached so immediate read-after-write paths do not reparse disk.",
        "- Later: broader SQLite cache/history access shape still needs contention evidence before promotion.",
        "- Leave alone: provider registration/config diagnostics clarity should not distract this optimization pass unless readiness diagnostics become the actual blocker.",
        "- Evidence standard: every shipped optimization needs before/after measurement when practical, or explicit code-path reasoning plus regression proof; S03 satisfies that standard for status polling and S04 satisfies it for the frontend/render follow-up; artifacts must not expose API keys, tokens, or analyst-sensitive IOC data.",
        "",
        "## Ranked findings",
        "",
        render_m017_ranked_findings(),
        "",
        "## M017 audit notes",
        "",
        "- This baseline intentionally contains no placeholder rows; each bucket records a current do-now/do-next/later/leave-alone decision.",
        "- Re-run with `make audit-m017` after each optimization slice so S05 can consume current command-capture rows and S03/S04 shipped-proof language.",
        "- Failed optional capture commands are recorded in the measurement table with nonzero exits so unrelated artifact generation remains inspectable.",
    ]


def render_document(document: AuditDocument) -> str:
    template_output = template_output_for_milestone(document.milestone_id)
    baseline_output = baseline_output_for_milestone(document.milestone_id)
    convenience_targets = convenience_targets_for_milestone(document.milestone_id)
    command_surface = "\n".join(
        [
            "| Entry point | Command | Purpose |",
            "| --- | --- | --- |",
            (
                f"| CLI help | `python3 tools/optimization_audit.py --help` | Show the supported modes, capture options, and output controls. |"
            ),
            (
                f"| Template scaffold | `python3 tools/optimization_audit.py --milestone-id {document.milestone_id} --mode template --output {template_output}` | Create a reusable milestone-local ranked artifact template. |"
            ),
            (
                f"| Working baseline artifact | `python3 tools/optimization_audit.py --milestone-id {document.milestone_id} --mode baseline --output {baseline_output}` | Create/update the current audit document used by later optimization slices. |"
            ),
            (
                f"| Convenience targets | {convenience_targets} | Repo-native wrappers around the same workflow for contributors. |"
            ),
        ]
    )

    lines = [
        f"# {document.milestone_id} Optimization Audit — {document.repo_name}",
        "",
        f"- Mode: `{document.mode}`",
        f"- Generated at: `{document.generated_at}`",
        f"- Repo root: `{document.repo_root}`",
        f"- Output path: `{document.output_path}`",
        "",
        "## Workflow contract",
        "",
        "- A finding must be backed by **measurement when practical**. If direct measurement is awkward or too invasive, the finding must cite **explicit code-path reasoning** instead of taste-based cleanup language.",
        "- Every finding must land in exactly one ranked bucket: `do now`, `do next`, `later`, or `leave alone`.",
        "- Every finding must call out the continuity guardrails it could endanger and the verification lanes that must be rerun before claiming the optimization is safe.",
        "- `leave alone` is a valid outcome when current architecture is already intentional and the evidence does not justify churn.",
        "",
        "## Command surface",
        "",
        command_surface,
        "",
        "## Verification lanes",
        "",
        render_lanes_section(),
        "",
        "## Verified rerun checklist",
        "",
        render_rerun_checklist_for_milestone(document.milestone_id),
        "",
        "## Continuity guardrails",
        "",
        render_guardrails_section(),
        "",
        "## Measurement captures",
        "",
        render_measurement_section(document.captures),
        "",
        "## Seam checklist",
        "",
        render_seams_section(),
        "",
        "## Ranked finding schema",
        "",
        "Use the same table shape in every bucket. Required fields per row:",
        "",
        "- **Finding** — one concrete optimization or keep-decision.",
        "- **Seam** — `runtime/provider`, `request/status`, `persistence`, or `frontend/render`.",
        "- **Evidence kind** — `measurement` or `code-path reasoning`.",
        "- **Evidence summary** — cite the measurement, command capture, or the exact path reasoning that justifies the rank.",
        "- **Continuity guardrails** — list the requirement IDs that must remain protected.",
        "- **Rerun lanes** — at minimum one of `make verify-fast`, `make verify-deep`, or `make verify`.",
        "- **Continuity notes** — state what behavior must remain true after the future change ships, or why the seam should stay untouched.",
        "",
    ]

    if document.mode == "baseline" and document.milestone_id == M020_MILESTONE_ID:
        lines.extend(render_m020_baseline_sections(document))
    elif document.mode == "baseline" and document.milestone_id == M017_MILESTONE_ID:
        lines.extend(render_m017_baseline_sections(document))
    elif document.mode == "baseline":
        lines.extend(
            [
                "## Baseline stance",
                "",
                "- Highest-confidence shipped fix: the status path now uses the orchestrator-owned incremental snapshot API, so the backend no longer snapshots every retained result on each poll.",
                "- The request/status seam is now an explicit shipped keep-decision: keep `_get_enrichment_status()` on `get_incremental_status()` while the helper continues to own terminal tombstones and aggregate history-save diagnostics.",
                "- The runtime/provider seam is now an explicit keep-decision: the deterministic local capture only showed a 1/5 cache-hit ratio, so no measured win justified pre-dispatch short-circuit churn ahead of the worker/semaphore path.",
                "- Highest-confidence explicit persistence keep-decision: leave the WAL-backed cache/history stores and the provider backoff/session contract alone until measured contention or provider pain shows up.",
                "- Highest-confidence shipped frontend/render fix: the shared coordinator now caches stable per-IOC DOM handles and provider-count metadata, so live/history result application no longer repeats whole-document card/slot lookups on every result.",
                "- Frontend/render follow-up remains explicit but deferred: if another pass is warranted, measure and narrow flush-wide `updateDashboardCounts()` recounts and `sortCardsBySeverity()` reorders before changing the live/history DOM contract.",
                "",
                "## Ranked findings",
                "",
                render_baseline_ranked_findings(),
                "",
                render_baseline_seam_notes(),
                "",
                render_baseline_guardrail_coverage(),
                "",
                "## Audit notes",
                "",
                "- This baseline intentionally makes keep-decisions explicit; `leave alone` rows are part of the evidence set, not filler.",
                "- Re-run this command after each optimization slice so later artifacts can compare the ranked buckets instead of restating assumptions.",
                "- Add explicit `--capture-command` entries when a downstream slice can attach fresh end-to-end timings or verification output to one of these rows.",
            ]
        )
    else:
        lines.append("## Ranked findings")
        lines.append("")
        for bucket in FINDING_BUCKETS:
            lines.append(f"### {bucket}")
            lines.append("")
            lines.append(bucket_table_placeholder(bucket))
            lines.append("")

        lines.extend(
            [
                "## Audit notes",
                "",
                "- Replace placeholder rows during the real baseline pass rather than appending free-form notes below the tables.",
                "- Add `--capture-command LABEL::COMMAND` entries whenever a claim can be supported by timing or command output.",
                "- If a seam cannot be measured directly, explain the exact control flow, persistence pattern, or DOM/render path that makes the keep/change decision credible.",
            ]
        )
    return _join_lines_trimmed(lines) + "\n"


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    if args.output == str(DEFAULT_OUTPUT):
        output_path = template_output_for_milestone(args.milestone_id) if args.mode == "template" else baseline_output_for_milestone(args.milestone_id)
    else:
        output_path = Path(args.output)

    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)

    captures: list[CommandCapture] = []
    if args.mode == "baseline":
        captures.extend(collect_baseline_captures())
    captures.extend(
        run_capture_command(spec, repo_root=repo_root, timeout_seconds=args.timeout_seconds)
        for spec in args.capture_command
    )

    document = AuditDocument(
        milestone_id=args.milestone_id,
        mode=args.mode,
        repo_name=args.repo_name,
        repo_root=repo_root,
        output_path=output_path,
        generated_at=utc_display_seconds(),
        captures=captures,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_document(document), encoding="utf-8")

    for capture in captures:
        if capture.exit_code == 0:
            continue
        print(
            f"capture '{capture.label}' failed with exit code {capture.exit_code}: {capture.summary}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
