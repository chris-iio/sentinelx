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
    except subprocess.TimeoutExpired as exc:
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
        "## Ranked findings",
        "",
    ]

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

    captures = [
        run_capture_command(spec, repo_root=repo_root, timeout_seconds=args.timeout_seconds)
        for spec in args.capture_command
    ]

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
