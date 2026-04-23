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

DEFAULT_MILESTONE_ID = "M013"
DEFAULT_OUTPUT = Path(f".gsd/milestones/{DEFAULT_MILESTONE_ID}/{DEFAULT_MILESTONE_ID}-AUDIT.md")
DEFAULT_TEMPLATE_OUTPUT = Path(
    f".gsd/milestones/{DEFAULT_MILESTONE_ID}/{DEFAULT_MILESTONE_ID}-AUDIT-TEMPLATE.md"
)
FINDING_BUCKETS = ("do now", "do next", "later", "leave alone")


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
        bucket="do now",
        finding="Make `/enrichment/status` cursor-native end-to-end by avoiding full results-list snapshots before slicing `since`.",
        seam="request/status",
        evidence_kind="measurement + code-path reasoning",
        evidence_summary=(
            "Internal capture `status-snapshot-scaling` shows `get_status()` cost rises with total retained results. "
            "`app/routes/_helpers.py::_get_enrichment_status()` currently calls `orchestrator.get_status()` first, and "
            "`app/enrichment/orchestrator.py::get_status()` clones the entire `results` list before the helper slices "
            "`results[since:]`, so every poll still pays an O(total-results) copy even when the frontend only needs the delta."
        ),
        continuity_guardrails="R008, R010, R018, R019, R040",
        rerun_lanes="`make verify-fast`, `make verify-deep`",
        continuity_notes=(
            "Preserve `next_since`, terminal failure semantics, progress/warning banners, and analyst-visible completion "
            "while shifting backend polling to a truly incremental read path."
        ),
    ),
    BaselineFinding(
        bucket="do next",
        finding="Cache IOC card/slot handles inside the shared result-application coordinator before chasing deeper render changes.",
        seam="frontend/render",
        evidence_kind="code-path reasoning",
        evidence_summary=(
            "`app/static/src/ts/modules/result-application.ts` performs `findCardForIoc()` and `.querySelector('.enrichment-slot')` "
            "per incoming result, then `updateDashboardCounts()` scans every `.ioc-card` and `sortCardsBySeverity()` reorders the whole grid "
            "after each flush. The shared coordinator is the correct seam because both live polling and history replay depend on it."
        ),
        continuity_guardrails="R008, R009, R010, R019, R040",
        rerun_lanes="`make verify-fast`, `make verify-deep`",
        continuity_notes=(
            "Must preserve live/history parity, textContent-only DOM construction, expand toggles, export/copy/detail-link wiring, "
            "and deterministic mocked-online browser proof."
        ),
    ),
    BaselineFinding(
        bucket="later",
        finding="Add dispatch/cache-hit instrumentation before considering thread-pool or semaphore rewrites.",
        seam="runtime/provider",
        evidence_kind="code-path reasoning",
        evidence_summary=(
            "`app/enrichment/orchestrator.py` already concentrates concurrency control in per-provider semaphores, keeps cache access inside "
            "the attempt path, and releases semaphore slots before 429 backoff sleep. This baseline found no local evidence that worker count, "
            "retry shape, or provider caps are the present bottleneck; the missing artifact is runtime visibility, not a blind concurrency rewrite."
        ),
        continuity_guardrails="R014, R015, R018, R020, R040",
        rerun_lanes="`make verify-fast`, `make verify-deep`",
        continuity_notes=(
            "Any future runtime optimization must preserve per-provider caps, backoff semantics, cache-hit markers, and adapter-owned session reuse."
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
        finding="Keep per-provider backoff/session semantics as explicit baseline keep-decisions.",
        seam="runtime/provider",
        evidence_kind="code-path reasoning",
        evidence_summary=(
            "`app/enrichment/orchestrator.py` documents why semaphores exclude sleep and the current tests cover per-provider caps, 429 retry behavior, "
            "snapshot safety, and cached-marker locking. Reopening adapter-owned `requests.Session` reuse or backoff rules now would risk validated guardrails "
            "without evidence of live provider pain."
        ),
        continuity_guardrails="R014, R015, R018, R020, R040",
        rerun_lanes="`make verify-fast`, `make verify-deep`",
        continuity_notes=(
            "Future work should layer measurement and observability onto the current contract rather than weakening rate-limit safety or session reuse."
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
            "Treat this seam as intentionally shaped for now. Add provider-mix/cache-hit instrumentation first; do not rewrite concurrency policy on aesthetics."
        ),
    ),
    SeamNote(
        seam="request/status",
        boundary="`app/routes/_helpers.py`, `app/routes/analysis.py`, and helper/status regression coverage.",
        current_shape=(
            "The helper owns a bounded module-level orchestrator registry, a shared enrichment thread pool, terminal tombstones, and history-save diagnostics. The frontend's `since` cursor "
            "contract is preserved, but the helper still asks the orchestrator for a full status snapshot before slicing incremental results."
        ),
        continuity_watch="R008, R010, R018, R019, R040 are the key guardrails.",
        baseline_call=(
            "This is the highest-confidence near-term optimization seam because it sits on every poll request and already has a clear correctness contract to preserve."
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
            "The live polling loop runs every 750ms, batches DOM flushes with a 100ms timer, and routes both live and history application through one coordinator. The same shared path still performs repeated card/slot lookups, full dashboard recounts, and grid reorders after flushes."
        ),
        continuity_watch="R008, R009, R010, R019, R040 remain coupled to any render optimization.",
        baseline_call=(
            "Optimize this seam only after the request/status cursor cost lands, because the shared coordinator makes render work worth improving but the current proof burden is high."
        ),
    ),
)

BASELINE_GUARDRAIL_COVERAGE: tuple[GuardrailCoverage, ...] = (
    GuardrailCoverage("R008", "request/status + frontend/render", "Do-now cursor work plus do-next coordinator caching", "Keep polling continuity, export/copy/detail-link behavior, and progress visibility intact."),
    GuardrailCoverage("R009", "frontend/render", "Do-next coordinator/render work", "Preserve textContent-only DOM construction, CSP/CSRF assumptions, and host-validation-adjacent safety expectations."),
    GuardrailCoverage("R010", "request/status + frontend/render", "Do-now cursor work plus do-next render work", "Any shipped optimization must reduce or at least not worsen polling/render churn."),
    GuardrailCoverage("R014", "runtime/provider", "Later instrumentation and leave-alone keep-decision", "Per-provider concurrency remains part of the baseline contract until evidence says otherwise."),
    GuardrailCoverage("R015", "runtime/provider", "Later instrumentation and leave-alone keep-decision", "429 backoff stays protected; future changes must prove they do not regress quota safety."),
    GuardrailCoverage("R018", "runtime/provider + request/status", "Do-now cursor work plus runtime keep-decision", "Snapshot correctness, semaphore scope, and cached-marker locking remain non-negotiable."),
    GuardrailCoverage("R019", "request/status + frontend/render", "Do-now cursor work plus do-next coordinator caching", "Keep `since`/`next_since` incremental polling semantics end-to-end."),
    GuardrailCoverage("R020", "runtime/provider", "Later instrumentation and leave-alone keep-decision", "Persistent adapter-owned sessions stay justified until measured evidence argues otherwise."),
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


def measure_status_snapshot_scaling() -> str:
    from app.enrichment.orchestrator import EnrichmentOrchestrator

    orchestrator = EnrichmentOrchestrator(adapters=[])
    iterations = 400

    def elapsed_ms(result_count: int) -> float:
        with orchestrator._lock:
            orchestrator._jobs["bench"] = {
                "total": result_count,
                "done": result_count,
                "results": list(range(result_count)),
                "complete": True,
                "status": "complete",
                "terminal": False,
                "terminal_reason": None,
                "error": None,
            }
        start = perf_counter()
        for _ in range(iterations):
            orchestrator.get_status("bench")
        return (perf_counter() - start) * 1000

    small_count = 200
    large_count = 5000
    small_ms = elapsed_ms(small_count)
    large_ms = elapsed_ms(large_count)
    ratio = large_ms / small_ms if small_ms > 0 else 0.0
    return (
        f"{iterations} `get_status()` calls: {small_count} results {small_ms:.2f}ms vs "
        f"{large_count} results {large_ms:.2f}ms ({ratio:.1f}x slower), confirming the current per-poll full-list snapshot cost before `since` slicing."
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
                "- Highest-confidence near-term work: make the status path truly incremental so the backend no longer snapshots every retained result on each poll.",
                "- Highest-confidence explicit keep-decision: leave the WAL-backed cache/history stores and the provider backoff/session contract alone until measured contention or provider pain shows up.",
                "- Frontend work remains important, but it should follow the status-path fix because the shared coordinator has a broader proof burden and depends on the same poll contract.",
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
