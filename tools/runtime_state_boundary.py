#!/usr/bin/env python3
"""Classify repo-local runtime state as durable, transient, or manual-review.

This tool is the authoritative checked-in boundary contract for SentinelX's
repo-local planning/runtime split. It does not read file contents and it never
mutates the working tree.

Examples:
    python3 tools/runtime_state_boundary.py classify \
        .gsd/milestones/M014/M014-ROADMAP.md \
        .gsd/state-manifest.json \
        .planning/STATE.md
    python3 tools/runtime_state_boundary.py audit --format text
    python3 tools/runtime_state_boundary.py audit --format json --fail-on-issues
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Iterable, Sequence

CLASS_DURABLE = "durable"
CLASS_TRANSIENT = "transient"
CLASS_MANUAL_REVIEW = "manual-review"

ISSUE_TRACKED_TRANSIENT = "tracked-transient"
ISSUE_UNIGNORED_TRANSIENT = "unignored-transient"
ISSUE_MANUAL_REVIEW = "manual-review-path"
ISSUE_CONFLICTING_RULE = "conflicting-rule-match"
ISSUE_UNKNOWN_ROOT = "unknown-root"
ALL_ISSUE_CODES = (
    ISSUE_TRACKED_TRANSIENT,
    ISSUE_UNIGNORED_TRANSIENT,
    ISSUE_MANUAL_REVIEW,
    ISSUE_CONFLICTING_RULE,
    ISSUE_UNKNOWN_ROOT,
)

KNOWN_BOUNDARY_ROOTS = (".gsd", ".planning", ".bg-shell")
DEFAULT_AUDIT_ROOTS = KNOWN_BOUNDARY_ROOTS


class BoundaryError(Exception):
    """Base runtime-state boundary error."""


class BoundaryPathError(BoundaryError):
    """Raised when a CLI path cannot be normalized safely."""


class GitInspectionError(BoundaryError):
    """Raised when a git inspection command fails unexpectedly."""


@dataclass(frozen=True)
class PolicyRule:
    name: str
    classification: str
    priority: int
    patterns: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class ClassificationResult:
    input_path: str
    normalized_path: str
    classification: str
    issue_code: str | None
    matched_rules: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class AuditFinding:
    path: str
    classification: str
    issue_code: str
    matched_rules: tuple[str, ...]
    rationale: str
    tracked: bool | None = None
    ignored: bool | None = None


@dataclass(frozen=True)
class AuditReport:
    repo_root: str
    scanned_paths: int
    findings: tuple[AuditFinding, ...]


BOUNDARY_POLICY: tuple[PolicyRule, ...] = (
    PolicyRule(
        name="milestone-continue-cursors",
        classification=CLASS_TRANSIENT,
        priority=100,
        patterns=(
            ".gsd/milestones/**/*-CONTINUE.md",
            ".gsd/milestones/**/continue.md",
        ),
        rationale=(
            "Continue files are repo-local execution cursors inside otherwise durable milestone trees."
        ),
    ),
    PolicyRule(
        name="gsd-canonical-ledgers",
        classification=CLASS_DURABLE,
        priority=90,
        patterns=(
            ".gsd/CODEBASE.md",
            ".gsd/DECISIONS.md",
            ".gsd/KNOWLEDGE.md",
            ".gsd/PROJECT.md",
            ".gsd/REQUIREMENTS.md",
        ),
        rationale="Canonical checked-in GSD ledgers remain durable repo artifacts.",
    ),
    PolicyRule(
        name="gsd-audit-docs",
        classification=CLASS_DURABLE,
        priority=90,
        patterns=(".gsd/audits", ".gsd/audits/**"),
        rationale="Checked-in audit markdown is durable planning evidence, not runtime state.",
    ),
    PolicyRule(
        name="gsd-project-reports",
        classification=CLASS_DURABLE,
        priority=90,
        patterns=(".gsd/reports", ".gsd/reports/**"),
        rationale="Checked-in report artifacts are durable repo evidence, not runtime state.",
    ),
    PolicyRule(
        name="gsd-milestone-artifacts",
        classification=CLASS_DURABLE,
        priority=80,
        patterns=(".gsd/milestones", ".gsd/milestones/**"),
        rationale="Milestone plans, summaries, and validated artifacts remain durable.",
    ),
    PolicyRule(
        name="bg-shell-runtime",
        classification=CLASS_TRANSIENT,
        priority=80,
        patterns=(".bg-shell", ".bg-shell/**"),
        rationale=".bg-shell contains local background-process runtime state.",
    ),
    PolicyRule(
        name="gsd-runtime-directories",
        classification=CLASS_TRANSIENT,
        priority=80,
        patterns=(
            ".gsd/activity",
            ".gsd/activity/**",
            ".gsd/browser-baselines",
            ".gsd/browser-baselines/**",
            ".gsd/browser-state",
            ".gsd/browser-state/**",
            ".gsd/exec",
            ".gsd/exec/**",
            ".gsd/forensics",
            ".gsd/forensics/**",
            ".gsd/graphs",
            ".gsd/graphs/**",
            ".gsd/journal",
            ".gsd/journal/**",
            ".gsd/parallel",
            ".gsd/parallel/**",
            ".gsd/runtime",
            ".gsd/runtime/**",
            ".gsd/safety",
            ".gsd/safety/**",
            ".gsd/worktrees",
            ".gsd/worktrees/**",
        ),
        rationale="These .gsd subtrees contain repo-local runtime data and derived machine state.",
    ),
    PolicyRule(
        name="gsd-runtime-files",
        classification=CLASS_TRANSIENT,
        priority=80,
        patterns=(
            ".gsd/STATE.md",
            ".gsd/auto.lock",
            ".gsd/completed-units.json",
            ".gsd/completed-units-*.json",
            ".gsd/DISCUSSION-MANIFEST.json",
            ".gsd/doctor-history.jsonl",
            ".gsd/event-log.jsonl",
            ".gsd/gsd.db",
            ".gsd/gsd.db-shm",
            ".gsd/gsd.db-wal",
            ".gsd/metrics.json",
            ".gsd/notifications.jsonl",
            ".gsd/state-manifest.json",
        ),
        rationale="These .gsd files are runtime manifests, journals, databases, or local cursors.",
    ),
    PolicyRule(
        name="gsd-audit-streams",
        classification=CLASS_TRANSIENT,
        priority=80,
        patterns=(".gsd/audit", ".gsd/audit/**"),
        rationale="Audit event streams are transient runtime logs and should not remain tracked.",
    ),
    PolicyRule(
        name="planning-legacy",
        classification=CLASS_MANUAL_REVIEW,
        priority=70,
        patterns=(".planning", ".planning/**"),
        rationale=(
            ".planning is a mixed legacy workflow tree and stays manual-review until a later slice"
            " migrates it safely."
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Classify repo-local planning/runtime paths and audit for tracked or unignored "
            "transient state without mutating the repo."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    classify_parser = subparsers.add_parser(
        "classify",
        help="Classify one or more paths as durable, transient, or manual-review.",
    )
    classify_parser.add_argument("paths", nargs="+", help="Repo-relative or absolute paths to classify.")
    classify_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    classify_parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root used to normalize paths (default: current directory).",
    )

    audit_parser = subparsers.add_parser(
        "audit",
        help="Scan the repo boundary for tracked transient, unignored transient, and manual-review paths.",
    )
    audit_parser.add_argument(
        "paths",
        nargs="*",
        default=list(DEFAULT_AUDIT_ROOTS),
        help=(
            "Roots or files to audit. Defaults to .gsd, .planning, and .bg-shell. "
            "Arguments may be repo-relative or absolute."
        ),
    )
    audit_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    audit_parser.add_argument(
        "--fail-on-issues",
        action="store_true",
        help="Exit non-zero when any audit findings are present.",
    )
    audit_parser.add_argument(
        "--fail-on-codes",
        nargs="+",
        choices=ALL_ISSUE_CODES,
        help=(
            "Exit non-zero only when one or more findings match the selected issue codes. "
            "Useful when manual-review findings should stay visible without failing the verifier."
        ),
    )
    audit_parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root used to normalize and inspect paths (default: current directory).",
    )

    return parser.parse_args()


def normalize_repo_root(repo_root: str | Path) -> Path:
    return Path(repo_root).resolve()


def normalize_repo_relative_path(path_value: str, repo_root: Path) -> str:
    candidate = path_value.strip()
    if not candidate:
        raise BoundaryPathError("Path arguments must not be empty.")

    raw_path = Path(candidate)
    absolute_path = raw_path if raw_path.is_absolute() else repo_root / raw_path
    resolved = absolute_path.resolve(strict=False)

    try:
        relative = resolved.relative_to(repo_root)
    except ValueError as exc:
        raise BoundaryPathError(
            f"Path '{path_value}' resolves outside repo root '{repo_root}'."
        ) from exc

    relative_posix = relative.as_posix()
    if relative_posix == ".":
        raise BoundaryPathError("Path arguments must resolve to a file or subpath inside the repo.")
    return relative_posix


def matches_pattern(path: str, pattern: str) -> bool:
    return path == pattern or fnmatchcase(path, pattern)


def classify_relative_path(
    relative_path: str,
    policy: Sequence[PolicyRule] = BOUNDARY_POLICY,
) -> ClassificationResult:
    matches = [
        rule
        for rule in policy
        if any(matches_pattern(relative_path, pattern) for pattern in rule.patterns)
    ]
    if not matches:
        root = relative_path.split("/", 1)[0]
        if root in KNOWN_BOUNDARY_ROOTS:
            return ClassificationResult(
                input_path=relative_path,
                normalized_path=relative_path,
                classification=CLASS_MANUAL_REVIEW,
                issue_code=ISSUE_MANUAL_REVIEW,
                matched_rules=(),
                rationale=(
                    "No explicit durable/transient rule matched this boundary path, so it stays "
                    "manual-review by default."
                ),
            )
        return ClassificationResult(
            input_path=relative_path,
            normalized_path=relative_path,
            classification=CLASS_MANUAL_REVIEW,
            issue_code=ISSUE_UNKNOWN_ROOT,
            matched_rules=(),
            rationale="Path is outside the supported boundary roots and fails closed to manual-review.",
        )

    highest_priority = max(rule.priority for rule in matches)
    top_matches = [rule for rule in matches if rule.priority == highest_priority]
    top_classes = {rule.classification for rule in top_matches}
    if len(top_classes) > 1:
        return ClassificationResult(
            input_path=relative_path,
            normalized_path=relative_path,
            classification=CLASS_MANUAL_REVIEW,
            issue_code=ISSUE_CONFLICTING_RULE,
            matched_rules=tuple(rule.name for rule in top_matches),
            rationale=(
                "Conflicting highest-priority policy rules matched this path, so it stays "
                "manual-review until the rule table is clarified."
            ),
        )

    winner = top_matches[0]
    issue_code = ISSUE_MANUAL_REVIEW if winner.classification == CLASS_MANUAL_REVIEW else None
    return ClassificationResult(
        input_path=relative_path,
        normalized_path=relative_path,
        classification=winner.classification,
        issue_code=issue_code,
        matched_rules=tuple(rule.name for rule in top_matches),
        rationale=winner.rationale,
    )


def classify_paths(paths: Sequence[str], repo_root: Path) -> tuple[ClassificationResult, ...]:
    results = []
    for path_value in paths:
        normalized = normalize_repo_relative_path(path_value, repo_root)
        result = classify_relative_path(normalized)
        results.append(
            ClassificationResult(
                input_path=path_value,
                normalized_path=result.normalized_path,
                classification=result.classification,
                issue_code=result.issue_code,
                matched_rules=result.matched_rules,
                rationale=result.rationale,
            )
        )
    return tuple(results)


def iter_audit_candidate_paths(paths: Sequence[str], repo_root: Path) -> tuple[str, ...]:
    discovered: set[str] = set()
    for path_value in paths:
        normalized = normalize_repo_relative_path(path_value, repo_root)
        absolute = repo_root / normalized
        if absolute.is_file():
            discovered.add(normalized)
            continue
        if absolute.is_dir():
            for child in absolute.rglob("*"):
                if child.is_file():
                    discovered.add(child.relative_to(repo_root).as_posix())
            continue
    return tuple(sorted(discovered))


def run_git_command(repo_root: Path, args: Sequence[str], *, input_bytes: bytes | None = None) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        input=input_bytes,
        capture_output=True,
        check=False,
    )
    if completed.returncode not in (0, 1):
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise GitInspectionError(
            f"git {' '.join(args)} failed with exit code {completed.returncode}: {stderr or 'no stderr'}"
        )
    return completed.stdout


def parse_nul_delimited_paths(blob: bytes) -> set[str]:
    return {entry.decode("utf-8") for entry in blob.split(b"\0") if entry}


def git_tracked_paths(repo_root: Path, paths: Sequence[str]) -> set[str]:
    if not paths:
        return set()
    stdout = run_git_command(repo_root, ["ls-files", "-z", "--", *paths])
    return parse_nul_delimited_paths(stdout)


def git_ignored_paths(repo_root: Path, paths: Sequence[str]) -> set[str]:
    if not paths:
        return set()
    payload = "\0".join(paths).encode("utf-8") + b"\0"
    stdout = run_git_command(repo_root, ["check-ignore", "-z", "--stdin"], input_bytes=payload)
    return parse_nul_delimited_paths(stdout)


def audit_paths(paths: Sequence[str], repo_root: Path) -> AuditReport:
    candidates = iter_audit_candidate_paths(paths, repo_root)
    tracked_paths = git_tracked_paths(repo_root, candidates)
    ignored_paths = git_ignored_paths(repo_root, candidates)

    findings: list[AuditFinding] = []
    for relative_path in candidates:
        result = classify_relative_path(relative_path)
        rule_names = result.matched_rules
        if result.classification == CLASS_TRANSIENT:
            tracked = relative_path in tracked_paths
            ignored = relative_path in ignored_paths
            if tracked:
                findings.append(
                    AuditFinding(
                        path=relative_path,
                        classification=result.classification,
                        issue_code=ISSUE_TRACKED_TRANSIENT,
                        matched_rules=rule_names,
                        rationale=(
                            "Transient runtime path is still tracked in Git and can block ordinary "
                            "stash/pop or checkout flows."
                        ),
                        tracked=True,
                        ignored=ignored,
                    )
                )
            elif not ignored:
                findings.append(
                    AuditFinding(
                        path=relative_path,
                        classification=result.classification,
                        issue_code=ISSUE_UNIGNORED_TRANSIENT,
                        matched_rules=rule_names,
                        rationale=(
                            "Transient runtime path is present in the working tree but not ignored by "
                            "Git yet."
                        ),
                        tracked=False,
                        ignored=False,
                    )
                )
        elif result.classification == CLASS_MANUAL_REVIEW:
            findings.append(
                AuditFinding(
                    path=relative_path,
                    classification=result.classification,
                    issue_code=result.issue_code or ISSUE_MANUAL_REVIEW,
                    matched_rules=rule_names,
                    rationale=result.rationale,
                    tracked=relative_path in tracked_paths,
                    ignored=relative_path in ignored_paths,
                )
            )

    ordered_findings = tuple(sorted(findings, key=lambda item: (item.issue_code, item.path)))
    return AuditReport(
        repo_root=str(repo_root),
        scanned_paths=len(candidates),
        findings=ordered_findings,
    )


def render_classify_text(results: Sequence[ClassificationResult]) -> str:
    lines = []
    for result in results:
        issue = result.issue_code or "-"
        rules = ",".join(result.matched_rules) if result.matched_rules else "-"
        lines.append(
            f"{result.classification}\t{result.normalized_path}\tissue={issue}\trules={rules}"
        )
    return "\n".join(lines)


def render_audit_text(report: AuditReport) -> str:
    counts: dict[str, int] = {}
    for finding in report.findings:
        counts[finding.issue_code] = counts.get(finding.issue_code, 0) + 1

    lines = [
        "runtime-state boundary audit",
        f"repo_root: {report.repo_root}",
        f"scanned_paths: {report.scanned_paths}",
        f"issue_count: {len(report.findings)}",
    ]
    for issue_code in sorted(counts):
        lines.append(f"- {issue_code}: {counts[issue_code]}")

    if report.findings:
        lines.append("findings:")
        for finding in report.findings:
            rule_names = ",".join(finding.matched_rules) if finding.matched_rules else "-"
            tracked = "yes" if finding.tracked else "no"
            ignored = "yes" if finding.ignored else "no"
            lines.append(
                f"- [{finding.issue_code}] {finding.classification} {finding.path} "
                f"tracked={tracked} ignored={ignored} rules={rule_names}"
            )
    else:
        lines.append("findings: none")
    return "\n".join(lines)


def classification_to_dict(result: ClassificationResult) -> dict[str, object]:
    return asdict(result)


def audit_report_to_dict(report: AuditReport) -> dict[str, object]:
    return {
        "repo_root": report.repo_root,
        "scanned_paths": report.scanned_paths,
        "issue_count": len(report.findings),
        "findings": [asdict(finding) for finding in report.findings],
    }


def report_has_issue_codes(report: AuditReport, issue_codes: Sequence[str]) -> bool:
    selected_codes = set(issue_codes)
    return any(finding.issue_code in selected_codes for finding in report.findings)


def main() -> int:
    args = parse_args()
    repo_root = normalize_repo_root(args.repo_root)

    try:
        if args.command == "classify":
            results = classify_paths(args.paths, repo_root)
            if args.format == "json":
                print(json.dumps([classification_to_dict(result) for result in results], indent=2))
            else:
                print(render_classify_text(results))
            return 0

        if args.command == "audit":
            report = audit_paths(args.paths, repo_root)
            if args.format == "json":
                print(json.dumps(audit_report_to_dict(report), indent=2))
            else:
                print(render_audit_text(report))
            if args.fail_on_issues and report.findings:
                return 1
            if args.fail_on_codes and report_has_issue_codes(report, args.fail_on_codes):
                return 1
            return 0
    except BoundaryError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Unsupported command: {args.command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
