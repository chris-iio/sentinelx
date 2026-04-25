#!/usr/bin/env python3
"""Repair supported runtime-state boundary findings without copying classifier rules.

This tool is the mutating companion to ``tools/runtime_state_boundary.py``. It
reuses the boundary classifier's authoritative audit helpers and issue codes,
and it stays intentionally conservative:

* only ``tracked-transient`` findings mutate in this first slice
* ``unignored-transient`` remains report-only until quarantine support lands
* manual-review, conflicting, and unknown-root findings never mutate

Examples:
    python3 tools/runtime_state_repair.py --dry-run --format text
    python3 tools/runtime_state_repair.py --repo-root /path/to/repo --format json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from runtime_state_boundary import (  # noqa: E402
    AuditFinding,
    AuditReport,
    BoundaryError,
    BoundaryPathError,
    DEFAULT_AUDIT_ROOTS,
    ISSUE_CONFLICTING_RULE,
    ISSUE_MANUAL_REVIEW,
    ISSUE_TRACKED_TRANSIENT,
    ISSUE_UNIGNORED_TRANSIENT,
    ISSUE_UNKNOWN_ROOT,
    KNOWN_BOUNDARY_ROOTS,
    audit_paths,
    normalize_repo_relative_path,
    normalize_repo_root,
)

ACTION_DEINDEX = "deindex-tracked-transient"
ACTION_BLOCKED = "blocked"
SUPPORTED_MUTATION_ISSUES = frozenset({ISSUE_TRACKED_TRANSIENT})
REPORT_ONLY_ISSUES = frozenset(
    {
        ISSUE_UNIGNORED_TRANSIENT,
        ISSUE_MANUAL_REVIEW,
        ISSUE_CONFLICTING_RULE,
        ISSUE_UNKNOWN_ROOT,
    }
)


class RepairError(Exception):
    """Base runtime-state repair error."""


class GitRepairError(RepairError):
    """Raised when a git-backed repair operation fails."""


@dataclass(frozen=True)
class RepairAction:
    path: str
    issue_code: str
    classification: str
    action: str
    status: str
    mutate: bool
    tracked: bool | None
    ignored: bool | None
    rationale: str
    command: tuple[str, ...] | None = None
    detail: str | None = None


@dataclass(frozen=True)
class RepairSummary:
    deindex_count: int
    quarantine_count: int
    blocked_count: int
    failed_count: int
    noop_count: int


@dataclass(frozen=True)
class RepairReport:
    repo_root: str
    mode: str
    scanned_paths: int
    issue_count: int
    actionable_issue_count: int
    blocked_issue_count: int
    failed_issue_count: int
    summary: RepairSummary
    actions: tuple[RepairAction, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Repair supported runtime-state boundary findings using the authoritative "
            "classifier-backed action table."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help=(
            "Optional repo-relative or absolute files/roots to audit. Defaults to .gsd, "
            ".planning, and .bg-shell. Only supported boundary roots are allowed."
        ),
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root used to normalize paths and run git commands (default: current directory).",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan repairs without mutating the git index.",
    )
    return parser.parse_args()


def normalize_repair_targets(paths: Sequence[str], repo_root: Path) -> tuple[str, ...]:
    requested = tuple(paths) if paths else tuple(DEFAULT_AUDIT_ROOTS)
    normalized: list[str] = []
    for path_value in requested:
        relative_path = normalize_repo_relative_path(path_value, repo_root)
        root = relative_path.split("/", 1)[0]
        if root not in KNOWN_BOUNDARY_ROOTS:
            supported = ", ".join(KNOWN_BOUNDARY_ROOTS)
            raise BoundaryPathError(
                f"Repair paths must stay within supported boundary roots ({supported}); got '{path_value}'."
            )
        normalized.append(relative_path)
    return tuple(normalized)


def plan_action_for_finding(finding: AuditFinding, *, dry_run: bool) -> RepairAction:
    if finding.issue_code == ISSUE_TRACKED_TRANSIENT:
        command = ("git", "rm", "--cached", "--", finding.path)
        status = "planned" if dry_run else "pending"
        detail = "would remove from the git index while preserving the working tree" if dry_run else None
        return RepairAction(
            path=finding.path,
            issue_code=finding.issue_code,
            classification=finding.classification,
            action=ACTION_DEINDEX,
            status=status,
            mutate=True,
            tracked=finding.tracked,
            ignored=finding.ignored,
            rationale=(
                "Tracked transient runtime state should be deindexed so it stops blocking normal git workflows."
            ),
            command=command,
            detail=detail,
        )

    if finding.issue_code == ISSUE_UNIGNORED_TRANSIENT:
        detail = "quarantine support is not available in this task, so the path stays blocked"
    elif finding.issue_code == ISSUE_MANUAL_REVIEW:
        detail = "manual-review paths remain report-only and never mutate automatically"
    elif finding.issue_code == ISSUE_CONFLICTING_RULE:
        detail = "conflicting classifier matches fail closed to blocked/manual review"
    elif finding.issue_code == ISSUE_UNKNOWN_ROOT:
        detail = "unknown boundary roots fail closed and never receive automatic mutation"
    else:
        detail = "unsupported issue code stays blocked until the action table is extended explicitly"

    return RepairAction(
        path=finding.path,
        issue_code=finding.issue_code,
        classification=finding.classification,
        action=ACTION_BLOCKED,
        status="blocked",
        mutate=False,
        tracked=finding.tracked,
        ignored=finding.ignored,
        rationale=finding.rationale,
        detail=detail,
    )


def plan_repair_actions(report: AuditReport, *, dry_run: bool) -> tuple[RepairAction, ...]:
    return tuple(plan_action_for_finding(finding, dry_run=dry_run) for finding in report.findings)


def apply_tracked_transient_repair(action: RepairAction, repo_root: Path) -> RepairAction:
    if action.issue_code not in SUPPORTED_MUTATION_ISSUES or not action.command:
        raise RepairError(f"Unsupported mutation request for issue code '{action.issue_code}'.")

    completed = subprocess.run(
        list(action.command),
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    stderr = completed.stderr.strip()
    if completed.returncode != 0:
        detail = stderr or "git rm --cached returned a non-zero exit code"
        return RepairAction(
            **{
                **asdict(action),
                "status": "failed",
                "detail": detail,
            }
        )

    if not (repo_root / action.path).exists():
        return RepairAction(
            **{
                **asdict(action),
                "status": "failed",
                "detail": "git rm --cached removed the working-tree file unexpectedly",
            }
        )

    detail = "removed from git index; working-tree file preserved"
    if stderr:
        detail = f"{detail}; git stderr: {stderr}"
    return RepairAction(
        **{
            **asdict(action),
            "status": "applied",
            "detail": detail,
        }
    )


def execute_plan(actions: Sequence[RepairAction], repo_root: Path, *, dry_run: bool) -> tuple[RepairAction, ...]:
    executed: list[RepairAction] = []
    for action in actions:
        if dry_run or not action.mutate:
            executed.append(action)
            continue
        executed.append(apply_tracked_transient_repair(action, repo_root))
    return tuple(executed)


def summarize_actions(actions: Sequence[RepairAction]) -> RepairSummary:
    deindex_count = sum(
        1
        for action in actions
        if action.action == ACTION_DEINDEX and action.status in {"planned", "pending", "applied"}
    )
    blocked_count = sum(1 for action in actions if action.status == "blocked")
    failed_count = sum(1 for action in actions if action.status == "failed")
    noop_count = 1 if not actions else 0
    return RepairSummary(
        deindex_count=deindex_count,
        quarantine_count=0,
        blocked_count=blocked_count,
        failed_count=failed_count,
        noop_count=noop_count,
    )


def build_repair_report(
    audit_report: AuditReport,
    actions: Sequence[RepairAction],
    *,
    dry_run: bool,
) -> RepairReport:
    summary = summarize_actions(actions)
    actionable_issue_count = sum(
        1 for action in actions if action.issue_code in SUPPORTED_MUTATION_ISSUES
    )
    blocked_issue_count = sum(1 for action in actions if action.status == "blocked")
    failed_issue_count = sum(1 for action in actions if action.status == "failed")
    return RepairReport(
        repo_root=audit_report.repo_root,
        mode="dry-run" if dry_run else "apply",
        scanned_paths=audit_report.scanned_paths,
        issue_count=len(audit_report.findings),
        actionable_issue_count=actionable_issue_count,
        blocked_issue_count=blocked_issue_count,
        failed_issue_count=failed_issue_count,
        summary=summary,
        actions=tuple(actions),
    )


def repair_report_to_dict(report: RepairReport) -> dict[str, object]:
    return {
        "repo_root": report.repo_root,
        "mode": report.mode,
        "scanned_paths": report.scanned_paths,
        "issue_count": report.issue_count,
        "actionable_issue_count": report.actionable_issue_count,
        "blocked_issue_count": report.blocked_issue_count,
        "failed_issue_count": report.failed_issue_count,
        "summary": asdict(report.summary),
        "actions": [asdict(action) for action in report.actions],
    }


def render_text(report: RepairReport) -> str:
    lines = [
        "runtime-state repair",
        f"repo_root: {report.repo_root}",
        f"mode: {report.mode}",
        f"scanned_paths: {report.scanned_paths}",
        f"issue_count: {report.issue_count}",
        f"actionable_issue_count: {report.actionable_issue_count}",
        f"blocked_issue_count: {report.blocked_issue_count}",
        f"failed_issue_count: {report.failed_issue_count}",
        f"deindex_count: {report.summary.deindex_count}",
        f"quarantine_count: {report.summary.quarantine_count}",
        f"blocked_count: {report.summary.blocked_count}",
        f"failed_count: {report.summary.failed_count}",
        f"noop_count: {report.summary.noop_count}",
    ]
    if not report.actions:
        lines.append("actions: none")
        return "\n".join(lines)

    lines.append("actions:")
    for action in report.actions:
        tracked = "yes" if action.tracked else "no"
        ignored = "yes" if action.ignored else "no"
        command = " ".join(action.command) if action.command else "-"
        detail = action.detail or "-"
        lines.append(
            f"- [{action.issue_code}] {action.action} {action.path} status={action.status} "
            f"tracked={tracked} ignored={ignored} command={command} detail={detail}"
        )
    return "\n".join(lines)


def exit_code_for_report(report: RepairReport) -> int:
    if report.failed_issue_count:
        return 1
    if report.summary.noop_count == 1:
        return 0
    unresolved = any(action.status in {"planned", "pending", "blocked", "failed"} for action in report.actions)
    return 1 if unresolved else 0


def run_repair(paths: Sequence[str], repo_root: Path, *, dry_run: bool) -> RepairReport:
    targets = normalize_repair_targets(paths, repo_root)
    audit_report = audit_paths(targets, repo_root)
    planned_actions = plan_repair_actions(audit_report, dry_run=dry_run)
    executed_actions = execute_plan(planned_actions, repo_root, dry_run=dry_run)
    return build_repair_report(audit_report, executed_actions, dry_run=dry_run)


def main() -> int:
    args = parse_args()
    repo_root = normalize_repo_root(args.repo_root)
    try:
        report = run_repair(args.paths, repo_root, dry_run=args.dry_run)
    except (BoundaryError, RepairError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(repair_report_to_dict(report), indent=2))
    else:
        print(render_text(report))
    return exit_code_for_report(report)


if __name__ == "__main__":
    sys.exit(main())
