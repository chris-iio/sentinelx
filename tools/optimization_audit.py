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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from unittest.mock import patch

DEFAULT_MILESTONE_ID = "M013"
DEFAULT_OUTPUT = Path(f".gsd/milestones/{DEFAULT_MILESTONE_ID}/{DEFAULT_MILESTONE_ID}-AUDIT.md")
DEFAULT_TEMPLATE_OUTPUT = Path(
    f".gsd/milestones/{DEFAULT_MILESTONE_ID}/{DEFAULT_MILESTONE_ID}-AUDIT-TEMPLATE.md"
)
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


@dataclass(frozen=True)
class VerificationLane:
    name: str
    command: str
    use_when: str


@dataclass(frozen=True)
class Guardrail:
    requirement_id: str
    summary: str


@dataclass(frozen=True)
class Seam:
    name: str
    continuity_focus: str
    prompts: tuple[str, str]


@dataclass(frozen=True)
class CommandCapture:
    label: str
    command: str
    exit_code: int
    duration_ms: int
    summary: str


@dataclass(frozen=True)
class BaselineFinding:
    bucket: str
    finding: str
    seam: str
    evidence_kind: str
    evidence_summary: str
    continuity_guardrails: str
    rerun_lanes: str
    continuity_notes: str


@dataclass(frozen=True)
class SeamNote:
    seam: str
    boundary: str
    current_shape: str
    continuity_watch: str
    baseline_call: str


@dataclass(frozen=True)
class GuardrailCoverage:
    requirement_id: str
    seam: str
    covered_by: str
    continuity_notes: str


@dataclass
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
        finding="If future frontend work is warranted, target flush-wide dashboard recounts and severity reorders instead of reopening the shipped coordinator-local handle cache.",
        seam="frontend/render",
        evidence_kind="code-path reasoning",
        evidence_summary=(
            "`app/static/src/ts/modules/result-application.ts` now caches each IOC's card, enrichment slot, section handles, copy button, and provider-count total "
            "inside `createResultApplicationCoordinator()`, so `apply()`, `flush()`, and `finalize()` reuse stable DOM references instead of repeating `findCardForIoc()` "
            "and `.querySelector('.enrichment-slot')` work. The remaining shared render cost still sits in `updateDashboardCounts()` scanning every `.ioc-card` "
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
            "The live polling loop runs every 750ms, batches DOM flushes with a 100ms timer, and routes both live and history application through one coordinator. That shared path now caches stable card/slot/section handles per IOC, but each flush still recounts `.ioc-card`s and reorders the whole grid."
        ),
        continuity_watch="R008, R009, R010, R019, R040 remain coupled to any render optimization.",
        baseline_call=(
            "The shipped coordinator-local cache retired repeated card/slot lookups; any later frontend pass should focus on measuring and narrowing flush-wide dashboard recounts/reorders without disturbing the broader proof surface."
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
    if "::" not in spec:
        raise ValueError(
            f"Invalid capture spec '{spec}'. Use LABEL::COMMAND so the artifact can name the measurement clearly."
        )
    label, command = spec.split("::", 1)
    label = label.strip()
    command = command.strip()
    if not label or not command:
        raise ValueError(
            f"Invalid capture spec '{spec}'. Both LABEL and COMMAND are required."
        )
    return label, command


def summarize_output(stdout: str, stderr: str) -> str:
    combined = []
    for stream in (stdout, stderr):
        for line in stream.splitlines():
            cleaned = " ".join(line.strip().split())
            if cleaned:
                combined.append(cleaned)
    if not combined:
        return "No stdout/stderr output captured."
    summary = " | ".join(combined[-3:])
    if len(summary) > 220:
        summary = summary[:217].rstrip() + "..."
    return summary


def run_capture_command(spec: str, repo_root: Path, timeout_seconds: int) -> CommandCapture:
    label, command = parse_capture_spec(spec)
    started = datetime.now(timezone.utc)
    try:
        completed = subprocess.run(
            shlex.split(command),
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        finished = datetime.now(timezone.utc)
        duration_ms = int((finished - started).total_seconds() * 1000)
        return CommandCapture(
            label=label,
            command=command,
            exit_code=completed.returncode,
            duration_ms=duration_ms,
            summary=summarize_output(completed.stdout, completed.stderr),
        )
    except subprocess.TimeoutExpired:
        finished = datetime.now(timezone.utc)
        duration_ms = int((finished - started).total_seconds() * 1000)
        return CommandCapture(
            label=label,
            command=command,
            exit_code=124,
            duration_ms=duration_ms,
            summary=f"Timed out after {timeout_seconds}s while running: {command}",
        )
    except OSError as exc:
        finished = datetime.now(timezone.utc)
        duration_ms = int((finished - started).total_seconds() * 1000)
        return CommandCapture(
            label=label,
            command=command,
            exit_code=127,
            duration_ms=duration_ms,
            summary=f"Failed to launch command: {exc}",
        )


def run_internal_capture(label: str, command: str, measure: callable) -> CommandCapture:
    started = datetime.now(timezone.utc)
    try:
        summary = measure()
        finished = datetime.now(timezone.utc)
        duration_ms = int((finished - started).total_seconds() * 1000)
        return CommandCapture(
            label=label,
            command=command,
            exit_code=0,
            duration_ms=duration_ms,
            summary=summary,
        )
    except Exception as exc:  # pragma: no cover - defensive audit failure path
        finished = datetime.now(timezone.utc)
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

    entries: list[str] = []
    for provider_name, provider_metrics in sorted(providers.items()):
        missing = [
            field for field in RUNTIME_PROVIDER_PROVIDER_FIELDS
            if not isinstance(provider_metrics, dict) or field not in provider_metrics
        ]
        if missing:
            raise ValueError(
                "Runtime/provider capture failed: provider "
                f"'{provider_name}' is missing fields: {', '.join(missing)}"
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
        entries.append(f"{provider_name}:{dispatch_count}d/{error_count}e")
    return ", ".join(entries)


def summarize_runtime_provider_diagnostics(diagnostics: object) -> str:
    if not isinstance(diagnostics, dict):
        raise ValueError("Runtime/provider capture failed: diagnostics snapshot is not a dict.")

    missing = [field for field in RUNTIME_PROVIDER_DIAGNOSTIC_FIELDS if field not in diagnostics]
    if missing:
        raise ValueError(
            "Runtime/provider capture failed: missing diagnostics fields: "
            + ", ".join(missing)
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
            return dict(row) if row is not None else None

        def put(self, value: str, type_: str, provider: str, payload: dict) -> None:
            self._rows[(value, type_, provider)] = {
                **payload,
                "cached_at": "2026-04-24T00:00:00Z",
            }

    class ScriptedAdapter:
        supported_types = {IOCType.IPV4}

        def __init__(self, name: str, requires_api_key: bool, outcomes: dict[str, list[object]]) -> None:
            self.name = name
            self.requires_api_key = requires_api_key
            self._outcomes = {ioc_value: list(result_list) for ioc_value, result_list in outcomes.items()}

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

    with orchestrator._lock:
        orchestrator._jobs["bench"] = {
            "total": retained_results,
            "done": retained_results,
            "results": list(range(retained_results)),
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
            label="history-store-tempdb",
            command="internal benchmark: HistoryStore temp WAL save/list/load loop",
            measure=measure_history_store_tempdb,
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
    return "\n".join(lines).rstrip()


def render_findings_table(findings: list[BaselineFinding]) -> str:
    lines = [
        "| Finding | Seam | Evidence kind | Evidence summary | Continuity guardrails | Rerun lanes | Continuity notes |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for finding in findings:
        lines.append(
            "| "
            + " | ".join(
                [
                    finding.finding,
                    finding.seam,
                    finding.evidence_kind,
                    finding.evidence_summary,
                    finding.continuity_guardrails,
                    finding.rerun_lanes,
                    finding.continuity_notes,
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def render_baseline_ranked_findings() -> str:
    lines: list[str] = []
    for bucket in FINDING_BUCKETS:
        lines.append(f"### {bucket}")
        lines.append("")
        bucket_findings = [finding for finding in BASELINE_FINDINGS if finding.bucket == bucket]
        lines.append(render_findings_table(bucket_findings))
        lines.append("")
    return "\n".join(lines).rstrip()


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
    return "\n".join(lines).rstrip()


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


def render_document(document: AuditDocument) -> str:
    command_surface = "\n".join(
        [
            "| Entry point | Command | Purpose |",
            "| --- | --- | --- |",
            (
                f"| CLI help | `python3 tools/optimization_audit.py --help` | Show the supported modes, capture options, and output controls. |"
            ),
            (
                f"| Template scaffold | `python3 tools/optimization_audit.py --mode template --output {DEFAULT_TEMPLATE_OUTPUT}` | Create a reusable milestone-local ranked artifact template. |"
            ),
            (
                f"| Working baseline artifact | `python3 tools/optimization_audit.py --mode baseline --output {DEFAULT_OUTPUT}` | Create/update the current audit document used by later optimization slices. |"
            ),
            (
                "| Convenience targets | `make audit-m013-template` / `make audit-m013` | Repo-native wrappers around the same workflow for contributors. |"
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
        render_rerun_checklist_section(),
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

    if document.mode == "baseline":
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
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
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
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        captures=captures,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_document(document), encoding="utf-8")

    failed_captures = [capture for capture in captures if capture.exit_code != 0]
    if failed_captures:
        for capture in failed_captures:
            print(
                f"capture '{capture.label}' failed with exit code {capture.exit_code}: {capture.summary}",
                file=sys.stderr,
            )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
