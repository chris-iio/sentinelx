#!/usr/bin/env python3
"""Repair supported runtime-state boundary findings without copying classifier rules.

This tool is the mutating companion to ``tools/runtime_state_boundary.py``. It
reuses the boundary classifier's authoritative audit helpers and issue codes,
and it stays intentionally conservative:

* ``tracked-transient`` findings are deindexed via ``git rm --cached``
* ``unignored-transient`` findings are moved into an ignored quarantine subtree
* manual-review, conflicting, and unknown-root findings never mutate

Examples:
    python3 tools/runtime_state_repair.py --dry-run --format text
    python3 tools/runtime_state_repair.py --repo-root /path/to/repo --format json
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, replace as dataclass_replace
from pathlib import Path
from typing import Sequence

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
REPO_ROOT = TOOLS_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.time_utils import utc_timestamp_slug  # noqa: E402

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
    format_command_args,
    format_json_payload,
    first_non_empty_output,
    normalize_repo_relative_path,
    normalize_repo_root,
    repo_path_root,
)

ACTION_DEINDEX = "deindex-tracked-transient"
ACTION_QUARANTINE = "quarantine-unignored-transient"
ACTION_BLOCKED = "blocked"
DEFAULT_QUARANTINE_ROOT = ".gsd/runtime/repair-quarantine"
QUARANTINE_STAMP_ENV = "RUNTIME_STATE_REPAIR_QUARANTINE_STAMP"
QUARANTINE_STAMP_PATTERN = re.compile(r"[A-Za-z0-9._-]+")
SUPPORTED_MUTATION_ISSUES = frozenset((ISSUE_TRACKED_TRANSIENT, ISSUE_UNIGNORED_TRANSIENT))
SOFT_BLOCKED_ISSUES = frozenset((ISSUE_MANUAL_REVIEW,))
HARD_BLOCKED_ISSUES = frozenset((ISSUE_CONFLICTING_RULE, ISSUE_UNKNOWN_ROOT))
REPORT_ONLY_ISSUES = frozenset((ISSUE_MANUAL_REVIEW, ISSUE_CONFLICTING_RULE, ISSUE_UNKNOWN_ROOT))
SUPPORTED_BOUNDARY_ROOTS_DISPLAY = ", ".join(KNOWN_BOUNDARY_ROOTS)


class RepairError(Exception):
    """Base runtime-state repair error."""


@dataclass(frozen=True, slots=True)
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
    destination: str | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class RepairSummary:
    deindex_count: int
    quarantine_count: int
    blocked_count: int
    failed_count: int
    noop_count: int


@dataclass(frozen=True, slots=True)
class RepairActionCounts:
    summary: RepairSummary
    actionable_issue_count: int
    blocked_issue_count: int
    failed_issue_count: int


@dataclass(frozen=True, slots=True)
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
        help=(
            "Repository root used to normalize paths and run git commands "
            "(default: current directory)."
        ),
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
        help="Plan repairs without mutating the git index or quarantine tree.",
    )
    return parser.parse_args()


def normalize_repair_targets(paths: Sequence[str], repo_root: Path) -> tuple[str, ...]:
    requested = paths if paths else DEFAULT_AUDIT_ROOTS
    normalized: list[str] = []
    changed = False
    for path_value in requested:
        relative_path = normalize_repo_relative_path(path_value, repo_root)
        if relative_path != path_value:
            changed = True
        root = repo_path_root(relative_path)
        if root not in KNOWN_BOUNDARY_ROOTS:
            raise BoundaryPathError(
                "Repair paths must stay within supported boundary roots "
                f"({SUPPORTED_BOUNDARY_ROOTS_DISPLAY}); "
                f"got '{path_value}'."
            )
        normalized.append(relative_path)
    if not changed and isinstance(requested, tuple):
        return requested
    return repair_target_tuple(normalized)


def repair_target_tuple(targets: Sequence[str]) -> tuple[str, ...]:
    """Return repair targets as a tuple, preserving common short-sequence fast paths."""
    if isinstance(targets, tuple):
        return targets
    target_count = len(targets)
    if target_count == 0:
        return ()
    if target_count == 1:
        return (targets[0],)
    if target_count == 2:
        return (targets[0], targets[1])
    if target_count == 3:
        return (targets[0], targets[1], targets[2])
    if target_count == 4:
        return (targets[0], targets[1], targets[2], targets[3])
    return tuple(targets)


def current_quarantine_stamp() -> str:
    configured = os.environ.get(QUARANTINE_STAMP_ENV)
    if configured:
        if not QUARANTINE_STAMP_PATTERN.fullmatch(configured):
            raise RepairError(
                f"{QUARANTINE_STAMP_ENV} must contain only letters, numbers, "
                "dot, underscore, or hyphen."
            )
        return configured
    return utc_timestamp_slug()


def build_quarantine_destination(path: str, *, quarantine_stamp: str) -> str:
    return f"{DEFAULT_QUARANTINE_ROOT}/{quarantine_stamp}/{path}"


def plan_action_for_finding(
    finding: AuditFinding,
    *,
    dry_run: bool,
    quarantine_stamp: str,
) -> RepairAction:
    if finding.issue_code == ISSUE_TRACKED_TRANSIENT:
        command = ("git", "rm", "--cached", "--", finding.path)
        status = "planned" if dry_run else "pending"
        detail = (
            "would remove from the git index while preserving the working tree"
            if dry_run
            else None
        )
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
                "Tracked transient runtime state should be deindexed so it "
                "stops blocking normal git workflows."
            ),
            command=command,
            detail=detail,
        )

    if finding.issue_code == ISSUE_UNIGNORED_TRANSIENT:
        destination = build_quarantine_destination(finding.path, quarantine_stamp=quarantine_stamp)
        status = "planned" if dry_run else "pending"
        detail = f"would move into ignored quarantine at {destination}" if dry_run else None
        return RepairAction(
            path=finding.path,
            issue_code=finding.issue_code,
            classification=finding.classification,
            action=ACTION_QUARANTINE,
            status=status,
            mutate=True,
            tracked=finding.tracked,
            ignored=finding.ignored,
            rationale=(
                "Unignored transient runtime state should move into the "
                "ignored quarantine subtree so the repo converges back to the "
                "supported boundary."
            ),
            destination=destination,
            detail=detail,
        )

    if finding.issue_code == ISSUE_MANUAL_REVIEW:
        detail = "manual-review paths remain report-only and never mutate automatically"
    elif finding.issue_code == ISSUE_CONFLICTING_RULE:
        detail = "conflicting classifier matches fail closed to blocked/manual review"
    elif finding.issue_code == ISSUE_UNKNOWN_ROOT:
        detail = "unknown boundary roots fail closed and never receive automatic mutation"
    else:
        detail = (
            "unsupported issue code stays blocked until the action table is "
            "extended explicitly"
        )

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
    if not report.findings:
        return ()
    quarantine_stamp: str | None = None
    actions: list[RepairAction] = []
    for finding in report.findings:
        if finding.issue_code == ISSUE_UNIGNORED_TRANSIENT and quarantine_stamp is None:
            quarantine_stamp = current_quarantine_stamp()
        actions.append(
            plan_action_for_finding(
                finding,
                dry_run=dry_run,
                quarantine_stamp=quarantine_stamp or "",
            )
        )
    return repair_actions_tuple(actions)


def repair_actions_tuple(actions: Sequence[RepairAction]) -> tuple[RepairAction, ...]:
    """Return actions as a tuple, preserving common short-sequence fast paths."""
    if isinstance(actions, tuple):
        return actions
    action_count = len(actions)
    if action_count == 0:
        return ()
    if action_count == 1:
        return (actions[0],)
    if action_count == 2:
        return (actions[0], actions[1])
    if action_count == 3:
        return (actions[0], actions[1], actions[2])
    if action_count == 4:
        return (actions[0], actions[1], actions[2], actions[3])
    return tuple(actions)


def replace_action(
    action: RepairAction,
    *,
    status: str,
    detail: str,
    destination: str | None = None,
) -> RepairAction:
    if destination is not None:
        return dataclass_replace(action, status=status, detail=detail, destination=destination)
    return dataclass_replace(action, status=status, detail=detail)


def git_executable_path() -> str:
    git_path = shutil.which("git")
    if git_path is None:
        raise RepairError("git executable was not found on PATH.")
    return git_path


def git_path_is_ignored(repo_root: Path, path: str) -> bool:
    git_path = git_executable_path()
    completed = subprocess.run(  # noqa: S603 - fixed git executable, no shell.
        [git_path, "check-ignore", "-q", "--", path],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    stderr = first_non_empty_output(completed.stderr, completed.stdout) or "git check-ignore failed"
    raise RepairError(stderr)


def apply_tracked_transient_repair(action: RepairAction, repo_root: Path) -> RepairAction:
    if action.issue_code != ISSUE_TRACKED_TRANSIENT or not action.command:
        raise RepairError(
            "Unsupported tracked-transient mutation request for issue code "
            f"'{action.issue_code}'."
        )

    git_path = git_executable_path()
    resolved_command = (git_path, *action.command[1:])
    completed = subprocess.run(  # noqa: S603 - fixed git executable, no shell.
        resolved_command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    stderr = first_non_empty_output(completed.stderr)
    if completed.returncode != 0:
        detail = stderr or "git rm --cached returned a non-zero exit code"
        return replace_action(action, status="failed", detail=detail)

    if not (repo_root / action.path).exists():
        return replace_action(
            action,
            status="failed",
            detail="git rm --cached removed the working-tree file unexpectedly",
        )

    detail = "removed from git index; working-tree file preserved"
    if stderr:
        detail = f"{detail}; git stderr: {stderr}"
    return replace_action(action, status="applied", detail=detail)


def apply_unignored_transient_repair(action: RepairAction, repo_root: Path) -> RepairAction:
    if action.issue_code != ISSUE_UNIGNORED_TRANSIENT or not action.destination:
        raise RepairError(
            "Unsupported unignored-transient mutation request for issue code "
            f"'{action.issue_code}'."
        )

    source = repo_root / action.path
    destination = repo_root / action.destination
    if not source.exists():
        return replace_action(
            action,
            status="failed",
            detail="source path disappeared before quarantine could run",
        )
    if destination.exists():
        return replace_action(
            action,
            status="failed",
            detail=f"quarantine destination already exists: {action.destination}",
        )
    if not git_path_is_ignored(repo_root, action.destination):
        return replace_action(
            action,
            status="failed",
            detail=f"quarantine destination is not ignored by git: {action.destination}",
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(source), str(destination))
    except OSError as exc:
        return replace_action(
            action,
            status="failed",
            detail=f"failed to move into quarantine: {exc}",
        )

    if source.exists():
        return replace_action(
            action,
            status="failed",
            detail=f"source path still exists after quarantine move: {action.path}",
        )
    if not destination.exists():
        return replace_action(
            action,
            status="failed",
            detail=(
                "quarantine move completed without leaving a destination "
                f"file: {action.destination}"
            ),
        )

    return replace_action(
        action,
        status="applied",
        detail=f"moved into ignored quarantine at {action.destination}",
    )


def execute_plan(
    actions: Sequence[RepairAction],
    repo_root: Path,
    *,
    dry_run: bool,
) -> tuple[RepairAction, ...]:
    if not actions:
        return ()
    if dry_run:
        return repair_actions_tuple(actions)
    executed: list[RepairAction] = []
    for action in actions:
        if not action.mutate:
            executed.append(action)
            continue
        if action.issue_code == ISSUE_TRACKED_TRANSIENT:
            executed.append(apply_tracked_transient_repair(action, repo_root))
            continue
        if action.issue_code == ISSUE_UNIGNORED_TRANSIENT:
            executed.append(apply_unignored_transient_repair(action, repo_root))
            continue
        raise RepairError(f"Unsupported mutation request for issue code '{action.issue_code}'.")
    return repair_actions_tuple(executed)


_COUNTED_ACTION_STATUSES = frozenset(("planned", "pending", "applied"))
_UNAPPLIED_ACTION_STATUSES = frozenset(("planned", "pending"))


def _repair_action_count_components(action: RepairAction) -> tuple[int, int, int, int, int]:
    actionable = 1 if action.issue_code in SUPPORTED_MUTATION_ISSUES else 0
    blocked = 1 if action.status == "blocked" else 0
    failed = 1 if action.status == "failed" else 0
    deindex = 0
    quarantine = 0
    if action.status in _COUNTED_ACTION_STATUSES:
        if action.action == ACTION_DEINDEX:
            deindex = 1
        elif action.action == ACTION_QUARANTINE:
            quarantine = 1
    return deindex, quarantine, blocked, failed, actionable


def _repair_action_counts_from_components(
    deindex_count: int,
    quarantine_count: int,
    blocked_count: int,
    failed_count: int,
    actionable_issue_count: int,
    *,
    noop_count: int,
) -> RepairActionCounts:
    return RepairActionCounts(
        summary=RepairSummary(
            deindex_count=deindex_count,
            quarantine_count=quarantine_count,
            blocked_count=blocked_count,
            failed_count=failed_count,
            noop_count=noop_count,
        ),
        actionable_issue_count=actionable_issue_count,
        blocked_issue_count=blocked_count,
        failed_issue_count=failed_count,
    )


def _count_repair_actions(actions: Sequence[RepairAction]) -> RepairActionCounts:
    action_count = len(actions)
    if action_count == 0:
        return _repair_action_counts_from_components(0, 0, 0, 0, 0, noop_count=1)
    if action_count == 1:
        deindex, quarantine, blocked, failed, actionable = _repair_action_count_components(
            actions[0]
        )
        return _repair_action_counts_from_components(
            deindex,
            quarantine,
            blocked,
            failed,
            actionable,
            noop_count=0,
        )
    if action_count == 2:
        first = _repair_action_count_components(actions[0])
        second = _repair_action_count_components(actions[1])
        return _repair_action_counts_from_components(
            first[0] + second[0],
            first[1] + second[1],
            first[2] + second[2],
            first[3] + second[3],
            first[4] + second[4],
            noop_count=0,
        )
    if action_count == 3:
        first = _repair_action_count_components(actions[0])
        second = _repair_action_count_components(actions[1])
        third = _repair_action_count_components(actions[2])
        return _repair_action_counts_from_components(
            first[0] + second[0] + third[0],
            first[1] + second[1] + third[1],
            first[2] + second[2] + third[2],
            first[3] + second[3] + third[3],
            first[4] + second[4] + third[4],
            noop_count=0,
        )
    if action_count == 4:
        first = _repair_action_count_components(actions[0])
        second = _repair_action_count_components(actions[1])
        third = _repair_action_count_components(actions[2])
        fourth = _repair_action_count_components(actions[3])
        return _repair_action_counts_from_components(
            first[0] + second[0] + third[0] + fourth[0],
            first[1] + second[1] + third[1] + fourth[1],
            first[2] + second[2] + third[2] + fourth[2],
            first[3] + second[3] + third[3] + fourth[3],
            first[4] + second[4] + third[4] + fourth[4],
            noop_count=0,
        )

    deindex_count = 0
    quarantine_count = 0
    blocked_count = 0
    failed_count = 0
    actionable_issue_count = 0

    for action in actions:
        if action.issue_code in SUPPORTED_MUTATION_ISSUES:
            actionable_issue_count += 1
        if action.status == "blocked":
            blocked_count += 1
        elif action.status == "failed":
            failed_count += 1

        if action.status not in _COUNTED_ACTION_STATUSES:
            continue
        if action.action == ACTION_DEINDEX:
            deindex_count += 1
        elif action.action == ACTION_QUARANTINE:
            quarantine_count += 1

    return _repair_action_counts_from_components(
        deindex_count,
        quarantine_count,
        blocked_count,
        failed_count,
        actionable_issue_count,
        noop_count=0,
    )


def summarize_actions(actions: Sequence[RepairAction]) -> RepairSummary:
    return _count_repair_actions(actions).summary


def build_repair_report(
    audit_report: AuditReport,
    actions: Sequence[RepairAction],
    *,
    dry_run: bool,
) -> RepairReport:
    counts = _count_repair_actions(actions)
    return RepairReport(
        repo_root=audit_report.repo_root,
        mode="dry-run" if dry_run else "apply",
        scanned_paths=audit_report.scanned_paths,
        issue_count=len(audit_report.findings),
        actionable_issue_count=counts.actionable_issue_count,
        blocked_issue_count=counts.blocked_issue_count,
        failed_issue_count=counts.failed_issue_count,
        summary=counts.summary,
        actions=repair_actions_tuple(actions),
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
        "summary": repair_summary_to_dict(report.summary),
        "actions": repair_actions_to_dicts(report.actions),
    }


def repair_summary_to_dict(summary: RepairSummary) -> dict[str, object]:
    return {
        "deindex_count": summary.deindex_count,
        "quarantine_count": summary.quarantine_count,
        "blocked_count": summary.blocked_count,
        "failed_count": summary.failed_count,
        "noop_count": summary.noop_count,
    }


def repair_actions_to_dicts(actions: Sequence[RepairAction]) -> list[dict[str, object]]:
    action_count = len(actions)
    if action_count == 0:
        return []
    if action_count == 1:
        return [repair_action_to_dict(actions[0])]
    if action_count == 2:
        return [repair_action_to_dict(actions[0]), repair_action_to_dict(actions[1])]
    if action_count == 3:
        return [
            repair_action_to_dict(actions[0]),
            repair_action_to_dict(actions[1]),
            repair_action_to_dict(actions[2]),
        ]
    if action_count == 4:
        return [
            repair_action_to_dict(actions[0]),
            repair_action_to_dict(actions[1]),
            repair_action_to_dict(actions[2]),
            repair_action_to_dict(actions[3]),
        ]

    serialized: list[dict[str, object]] = []
    for action in actions:
        append_repair_action_dict(serialized, action)
    return serialized


def append_repair_action_dict(
    serialized: list[dict[str, object]],
    action: RepairAction,
) -> None:
    serialized.append(repair_action_to_dict(action))


def repair_action_to_dict(action: RepairAction) -> dict[str, object]:
    return {
        "path": action.path,
        "issue_code": action.issue_code,
        "classification": action.classification,
        "action": action.action,
        "status": action.status,
        "mutate": action.mutate,
        "tracked": action.tracked,
        "ignored": action.ignored,
        "rationale": action.rationale,
        "command": action.command,
        "destination": action.destination,
        "detail": action.detail,
    }


def render_text(report: RepairReport) -> str:
    header = _render_text_header(report)
    if not report.actions:
        return header + "\nactions: none"

    lines = [header]
    lines.append("actions:")
    for action in report.actions:
        tracked = "yes" if action.tracked else "no"
        ignored = "yes" if action.ignored else "no"
        command = format_command_args(action.command) if action.command else "-"
        destination = action.destination or "-"
        detail = action.detail or "-"
        lines.append(
            f"- [{action.issue_code}] {action.action} {action.path} status={action.status} "
            f"tracked={tracked} ignored={ignored} command={command} "
            f"destination={destination} detail={detail}"
        )
    return "\n".join(lines)


def _render_text_header(report: RepairReport) -> str:
    return (
        "runtime-state repair\n"
        f"repo_root: {report.repo_root}\n"
        f"mode: {report.mode}\n"
        f"scanned_paths: {report.scanned_paths}\n"
        f"issue_count: {report.issue_count}\n"
        f"actionable_issue_count: {report.actionable_issue_count}\n"
        f"blocked_issue_count: {report.blocked_issue_count}\n"
        f"failed_issue_count: {report.failed_issue_count}\n"
        f"deindex_count: {report.summary.deindex_count}\n"
        f"quarantine_count: {report.summary.quarantine_count}\n"
        f"blocked_count: {report.summary.blocked_count}\n"
        f"failed_count: {report.summary.failed_count}\n"
        f"noop_count: {report.summary.noop_count}"
    )


def exit_code_for_report(report: RepairReport) -> int:
    if report.failed_issue_count:
        return 1
    if report.summary.noop_count == 1:
        return 0

    return 1 if report_has_exit_blocking_action(report.actions) else 0


def report_has_exit_blocking_action(actions: Sequence[RepairAction]) -> bool:
    for action in actions:
        if action.status in _UNAPPLIED_ACTION_STATUSES:
            return True
        if action.status == "blocked" and action.issue_code in HARD_BLOCKED_ISSUES:
            return True
    return False


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
        print(format_json_payload(repair_report_to_dict(report)))
    else:
        print(render_text(report))
    return exit_code_for_report(report)


if __name__ == "__main__":
    sys.exit(main())
