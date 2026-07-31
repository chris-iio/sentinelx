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
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from typing import AbstractSet, Sequence

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
EMPTY_PATH_SET: frozenset[str] = frozenset()
GIT_INSPECTION_OK_RETURN_CODES = frozenset((0, 1))


class BoundaryError(Exception):
    """Base runtime-state boundary error."""


class BoundaryPathError(BoundaryError):
    """Raised when a CLI path cannot be normalized safely."""


class GitInspectionError(BoundaryError):
    """Raised when a git inspection command fails unexpectedly."""


def format_command_args(args: Sequence[str]) -> str:
    """Return shell-safe display text for command arguments."""
    return shlex.join(args)


def first_non_empty_output(*streams: str | bytes | None) -> str | None:
    """Return the first non-empty stripped text from process output streams."""
    for stream in streams:
        if stream is None:
            continue
        text = stream.decode("utf-8", errors="replace") if isinstance(stream, bytes) else stream
        stripped = stripped_text_or_none(text)
        if stripped:
            return stripped
    return None


def stripped_text_or_none(text: str) -> str | None:
    start = 0
    end = len(text)
    while start < end and text[start].isspace():
        start += 1
    if start == end:
        return None
    while end > start and text[end - 1].isspace():
        end -= 1
    return text[start:end]


def format_json_payload(payload: object, *, sort_keys: bool = False) -> str:
    """Return the repo-tooling standard pretty JSON representation."""
    return json.dumps(payload, indent=2, sort_keys=sort_keys)


@dataclass(frozen=True, slots=True)
class PolicyRule:
    name: str
    classification: str
    priority: int
    patterns: tuple[str, ...]
    rationale: str


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    input_path: str
    normalized_path: str
    classification: str
    issue_code: str | None
    matched_rules: tuple[str, ...]
    rationale: str


@dataclass(frozen=True, slots=True)
class AuditFinding:
    path: str
    classification: str
    issue_code: str
    matched_rules: tuple[str, ...]
    rationale: str
    tracked: bool | None = None
    ignored: bool | None = None


@dataclass(frozen=True, slots=True)
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
            "Continue files are repo-local execution cursors inside otherwise durable "
            "milestone trees."
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
    classify_parser.add_argument(
        "paths",
        nargs="+",
        help="Repo-relative or absolute paths to classify.",
    )
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
        help=(
            "Scan the repo boundary for tracked transient, unignored transient, "
            "and manual-review paths."
        ),
    )
    audit_parser.add_argument(
        "paths",
        nargs="*",
        default=DEFAULT_AUDIT_ROOTS,
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
    candidate = stripped_text_or_none(path_value)
    if candidate is None:
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


def rule_matches_path(relative_path: str, rule: PolicyRule) -> bool:
    for pattern in rule.patterns:  # noqa: SIM110 - tests guard direct scan without builtins.any.
        if matches_pattern(relative_path, pattern):
            return True
    return False


def repo_path_root(relative_path: str) -> str:
    """Return the first path segment without allocating split parts."""
    separator = relative_path.find("/")
    if separator < 0:
        return relative_path
    return relative_path[:separator]


def classify_relative_path(
    relative_path: str,
    policy: Sequence[PolicyRule] = BOUNDARY_POLICY,
) -> ClassificationResult:
    top_matches: list[PolicyRule] = []
    highest_priority: int | None = None
    for rule in policy:
        if rule_matches_path(relative_path, rule):
            if highest_priority is None or rule.priority > highest_priority:
                highest_priority = rule.priority
                top_matches = [rule]
            elif rule.priority == highest_priority:
                top_matches.append(rule)
    if highest_priority is None:
        root = repo_path_root(relative_path)
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
            rationale=(
                "Path is outside the supported boundary roots and fails closed "
                "to manual-review."
            ),
        )

    winner = top_matches[0]
    has_conflicting_classes = False
    for index, rule in enumerate(top_matches):
        if index == 0:
            continue
        if rule.classification != winner.classification:
            has_conflicting_classes = True
            break
    if has_conflicting_classes:
        return ClassificationResult(
            input_path=relative_path,
            normalized_path=relative_path,
            classification=CLASS_MANUAL_REVIEW,
            issue_code=ISSUE_CONFLICTING_RULE,
            matched_rules=rule_names(top_matches),
            rationale=(
                "Conflicting highest-priority policy rules matched this path, so it stays "
                "manual-review until the rule table is clarified."
            ),
        )

    issue_code = ISSUE_MANUAL_REVIEW if winner.classification == CLASS_MANUAL_REVIEW else None
    return ClassificationResult(
        input_path=relative_path,
        normalized_path=relative_path,
        classification=winner.classification,
        issue_code=issue_code,
        matched_rules=rule_names(top_matches),
        rationale=winner.rationale,
    )


def rule_names(rules: Sequence[PolicyRule]) -> tuple[str, ...]:
    rule_count = len(rules)
    if rule_count == 0:
        return ()
    if rule_count == 1:
        return (rules[0].name,)
    if rule_count == 2:
        return (rules[0].name, rules[1].name)
    if rule_count == 3:
        return (rules[0].name, rules[1].name, rules[2].name)
    if rule_count == 4:
        return (rules[0].name, rules[1].name, rules[2].name, rules[3].name)
    names: list[str] = []
    for rule in rules:
        names.append(rule.name)
    return tuple(names)


def format_matched_rules(matched_rules: Sequence[str]) -> str:
    rule_count = len(matched_rules)
    if rule_count == 0:
        return "-"
    if rule_count == 1:
        return matched_rules[0]
    if rule_count == 2:
        return f"{matched_rules[0]},{matched_rules[1]}"
    if rule_count == 3:
        return f"{matched_rules[0]},{matched_rules[1]},{matched_rules[2]}"
    if rule_count == 4:
        return f"{matched_rules[0]},{matched_rules[1]},{matched_rules[2]},{matched_rules[3]}"
    return ",".join(matched_rules)


def highest_priority_matches(matches: Sequence[PolicyRule]) -> tuple[PolicyRule, ...]:
    """Return highest-priority policy matches while scanning once."""
    match_count = len(matches)
    if match_count == 0:
        return ()
    if match_count == 1:
        return (matches[0],)
    selected: list[PolicyRule] = []
    highest_priority: int | None = None
    for rule in matches:
        if highest_priority is None or rule.priority > highest_priority:
            highest_priority = rule.priority
            selected = [rule]
        elif rule.priority == highest_priority:
            selected.append(rule)
    return policy_rules_tuple(selected)


def policy_rules_tuple(rules: Sequence[PolicyRule]) -> tuple[PolicyRule, ...]:
    """Return policy rules as a tuple with short-sequence fast paths."""
    if isinstance(rules, tuple):
        return rules
    rule_count = len(rules)
    if rule_count == 0:
        return ()
    if rule_count == 1:
        return (rules[0],)
    if rule_count == 2:
        return (rules[0], rules[1])
    if rule_count == 3:
        return (rules[0], rules[1], rules[2])
    if rule_count == 4:
        return (rules[0], rules[1], rules[2], rules[3])
    return tuple(rules)


def classify_paths(paths: Sequence[str], repo_root: Path) -> tuple[ClassificationResult, ...]:
    if not paths:
        return ()
    results = []
    for path_value in paths:
        normalized = normalize_repo_relative_path(path_value, repo_root)
        result = classify_relative_path(normalized)
        append_classification_result(
            results,
            path_value,
            result,
        )
    return classification_results_tuple(results)


def append_classification_result(
    results: list[ClassificationResult],
    input_path: str,
    result: ClassificationResult,
) -> None:
    results.append(
        ClassificationResult(
            input_path=input_path,
            normalized_path=result.normalized_path,
            classification=result.classification,
            issue_code=result.issue_code,
            matched_rules=result.matched_rules,
            rationale=result.rationale,
        )
    )


def classification_results_tuple(
    results: Sequence[ClassificationResult],
) -> tuple[ClassificationResult, ...]:
    """Return classification results as a tuple with short-sequence fast paths."""
    if isinstance(results, tuple):
        return results
    result_count = len(results)
    if result_count == 0:
        return ()
    if result_count == 1:
        return (results[0],)
    if result_count == 2:
        return (results[0], results[1])
    if result_count == 3:
        return (results[0], results[1], results[2])
    if result_count == 4:
        return (results[0], results[1], results[2], results[3])
    return tuple(results)


def iter_audit_candidate_paths(paths: Sequence[str], repo_root: Path) -> tuple[str, ...]:
    if not paths:
        return ()
    discovered: set[str] = set()
    first_discovered: str | None = None
    for path_value in paths:
        normalized = normalize_repo_relative_path(path_value, repo_root)
        absolute = repo_root / normalized
        if absolute.is_file():
            discovered.add(normalized)
            if first_discovered is None:
                first_discovered = normalized
            continue
        if absolute.is_dir():
            for child in absolute.rglob("*"):
                if child.is_file():
                    relative_child = child.relative_to(repo_root).as_posix()
                    discovered.add(relative_child)
                    if first_discovered is None:
                        first_discovered = relative_child
            continue
    discovered_count = len(discovered)
    return ordered_discovered_paths(discovered, first_discovered, discovered_count)


def ordered_discovered_paths(
    discovered: set[str],
    first_discovered: str | None,
    discovered_count: int | None = None,
) -> tuple[str, ...]:
    """Return discovered audit paths in deterministic order."""
    path_count = len(discovered) if discovered_count is None else discovered_count
    if path_count == 0:
        return ()
    if path_count == 1:
        return (first_discovered,) if first_discovered is not None else ()
    if path_count == 2:
        iterator = iter(discovered)
        first = next(iterator)
        second = next(iterator)
        if first <= second:
            return (first, second)
        return (second, first)
    if path_count == 3:
        iterator = iter(discovered)
        first = next(iterator)
        second = next(iterator)
        third = next(iterator)
        if second < first:
            first, second = second, first
        if third < second:
            second, third = third, second
            if second < first:
                first, second = second, first
        return (first, second, third)
    if path_count == 4:
        iterator = iter(discovered)
        first = next(iterator)
        second = next(iterator)
        third = next(iterator)
        fourth = next(iterator)
        if second < first:
            first, second = second, first
        if fourth < third:
            third, fourth = fourth, third
        if third < first:
            first, third = third, first
        if fourth < second:
            second, fourth = fourth, second
        if third < second:
            second, third = third, second
        return (first, second, third, fourth)
    ordered: list[str] = []
    for path in discovered:
        append_ordered_path(ordered, path)
    return tuple(ordered)


def append_ordered_path(ordered: list[str], path: str) -> None:
    path_count = len(ordered)
    if path_count == 0:
        ordered.append(path)
        return

    index = 0
    while index < path_count:
        current = ordered[index]
        if path <= current:
            ordered.insert(index, path)
            return
        index += 1

    ordered.append(path)


def run_git_command(
    repo_root: Path,
    args: Sequence[str],
    *,
    input_bytes: bytes | None = None,
) -> bytes:
    git_path = shutil.which("git")
    if git_path is None:
        raise GitInspectionError("git executable was not found on PATH.")
    completed = subprocess.run(  # noqa: S603 - fixed git executable, no shell.
        [git_path, *args],
        cwd=repo_root,
        input=input_bytes,
        capture_output=True,
        check=False,
    )
    if completed.returncode not in GIT_INSPECTION_OK_RETURN_CODES:
        stderr = first_non_empty_output(completed.stderr)
        raise GitInspectionError(
            f"git {format_command_args(args)} failed with exit code "
            f"{completed.returncode}: {stderr or 'no stderr'}"
        )
    return completed.stdout


def parse_nul_delimited_paths(blob: bytes) -> AbstractSet[str]:
    if not blob:
        return EMPTY_PATH_SET
    paths: set[str] = set()
    blob_length = len(blob)
    start = 0
    while start < blob_length:
        separator = blob.find(b"\0", start)
        if separator < 0:
            separator = blob_length
        if separator > start:
            paths.add(blob[start:separator].decode("utf-8"))
        start = separator + 1
    return paths


def git_tracked_paths(repo_root: Path, paths: Sequence[str]) -> AbstractSet[str]:
    if not paths:
        return EMPTY_PATH_SET
    stdout = run_git_command(repo_root, ["ls-files", "-z", "--", *paths])
    return parse_nul_delimited_paths(stdout)


def git_ignored_paths(repo_root: Path, paths: Sequence[str]) -> AbstractSet[str]:
    if not paths:
        return EMPTY_PATH_SET
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
                            "Transient runtime path is present in the working tree but not "
                            "ignored by Git yet."
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

    ordered_findings = ordered_audit_findings(findings)
    return AuditReport(
        repo_root=str(repo_root),
        scanned_paths=len(candidates),
        findings=ordered_findings,
    )


def audit_finding_sort_key(finding: AuditFinding) -> tuple[str, str]:
    return finding.issue_code, finding.path


def ordered_audit_findings(findings: list[AuditFinding]) -> tuple[AuditFinding, ...]:
    """Return audit findings in deterministic issue/path order."""
    finding_count = len(findings)
    if finding_count == 0:
        return ()
    if finding_count == 1:
        return (findings[0],)
    if finding_count == 2:
        first = findings[0]
        second = findings[1]
        if audit_finding_sort_key(first) <= audit_finding_sort_key(second):
            return (first, second)
        return (second, first)
    if finding_count == 3:
        first = findings[0]
        second = findings[1]
        third = findings[2]
        if audit_finding_sort_key(second) < audit_finding_sort_key(first):
            first, second = second, first
        if audit_finding_sort_key(third) < audit_finding_sort_key(second):
            second, third = third, second
            if audit_finding_sort_key(second) < audit_finding_sort_key(first):
                first, second = second, first
        return (first, second, third)
    if finding_count == 4:
        first = findings[0]
        second = findings[1]
        third = findings[2]
        fourth = findings[3]
        if audit_finding_sort_key(second) < audit_finding_sort_key(first):
            first, second = second, first
        if audit_finding_sort_key(fourth) < audit_finding_sort_key(third):
            third, fourth = fourth, third
        if audit_finding_sort_key(third) < audit_finding_sort_key(first):
            first, third = third, first
        if audit_finding_sort_key(fourth) < audit_finding_sort_key(second):
            second, fourth = fourth, second
        if audit_finding_sort_key(third) < audit_finding_sort_key(second):
            second, third = third, second
        return (first, second, third, fourth)
    ordered: list[AuditFinding] = []
    for finding in findings:
        append_ordered_audit_finding(ordered, finding)
    return tuple(ordered)


def append_ordered_audit_finding(ordered: list[AuditFinding], finding: AuditFinding) -> None:
    finding_count = len(ordered)
    if finding_count == 0:
        ordered.append(finding)
        return

    finding_key = audit_finding_sort_key(finding)
    index = 0
    while index < finding_count:
        if finding_key <= audit_finding_sort_key(ordered[index]):
            ordered.insert(index, finding)
            return
        index += 1

    ordered.append(finding)


def render_classify_text(results: Sequence[ClassificationResult]) -> str:
    result_count = len(results)
    if result_count == 0:
        return ""
    if result_count == 1:
        return _classification_text_line(results[0])
    if result_count == 2:
        return _classification_text_line(results[0]) + "\n" + _classification_text_line(results[1])
    if result_count == 3:
        return (
            _classification_text_line(results[0])
            + "\n"
            + _classification_text_line(results[1])
            + "\n"
            + _classification_text_line(results[2])
        )
    if result_count == 4:
        return (
            _classification_text_line(results[0])
            + "\n"
            + _classification_text_line(results[1])
            + "\n"
            + _classification_text_line(results[2])
            + "\n"
            + _classification_text_line(results[3])
        )

    lines = []
    for result in results:
        lines.append(_classification_text_line(result))
    return "\n".join(lines)


def _classification_text_line(result: ClassificationResult) -> str:
    issue = result.issue_code or "-"
    rules = format_matched_rules(result.matched_rules)
    return f"{result.classification}\t{result.normalized_path}\tissue={issue}\trules={rules}"


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
    append_issue_count_lines(lines, counts)

    if report.findings:
        lines.append("findings:")
        for finding in report.findings:
            rule_names = format_matched_rules(finding.matched_rules)
            tracked = "yes" if finding.tracked else "no"
            ignored = "yes" if finding.ignored else "no"
            lines.append(
                f"- [{finding.issue_code}] {finding.classification} {finding.path} "
                f"tracked={tracked} ignored={ignored} rules={rule_names}"
            )
    else:
        lines.append("findings: none")
    return "\n".join(lines)


def append_issue_count_lines(lines: list[str], counts: dict[str, int]) -> None:
    count = counts.get(ISSUE_TRACKED_TRANSIENT, 0)
    if count:
        lines.append(f"- {ISSUE_TRACKED_TRANSIENT}: {count}")
    count = counts.get(ISSUE_UNIGNORED_TRANSIENT, 0)
    if count:
        lines.append(f"- {ISSUE_UNIGNORED_TRANSIENT}: {count}")
    count = counts.get(ISSUE_MANUAL_REVIEW, 0)
    if count:
        lines.append(f"- {ISSUE_MANUAL_REVIEW}: {count}")
    count = counts.get(ISSUE_CONFLICTING_RULE, 0)
    if count:
        lines.append(f"- {ISSUE_CONFLICTING_RULE}: {count}")
    count = counts.get(ISSUE_UNKNOWN_ROOT, 0)
    if count:
        lines.append(f"- {ISSUE_UNKNOWN_ROOT}: {count}")


def classification_to_dict(result: ClassificationResult) -> dict[str, object]:
    return {
        "input_path": result.input_path,
        "normalized_path": result.normalized_path,
        "classification": result.classification,
        "issue_code": result.issue_code,
        "matched_rules": result.matched_rules,
        "rationale": result.rationale,
    }


def classifications_to_dicts(results: Sequence[ClassificationResult]) -> list[dict[str, object]]:
    result_count = len(results)
    if result_count == 0:
        return []
    if result_count == 1:
        return [classification_to_dict(results[0])]
    if result_count == 2:
        return [classification_to_dict(results[0]), classification_to_dict(results[1])]
    if result_count == 3:
        return [
            classification_to_dict(results[0]),
            classification_to_dict(results[1]),
            classification_to_dict(results[2]),
        ]
    if result_count == 4:
        return [
            classification_to_dict(results[0]),
            classification_to_dict(results[1]),
            classification_to_dict(results[2]),
            classification_to_dict(results[3]),
        ]

    serialized: list[dict[str, object]] = []
    for result in results:
        append_classification_dict(serialized, result)
    return serialized


def append_classification_dict(
    serialized: list[dict[str, object]],
    result: ClassificationResult,
) -> None:
    serialized.append(classification_to_dict(result))


def audit_findings_to_dicts(findings: Sequence[AuditFinding]) -> list[dict[str, object]]:
    finding_count = len(findings)
    if finding_count == 0:
        return []
    if finding_count == 1:
        return [audit_finding_to_dict(findings[0])]
    if finding_count == 2:
        return [audit_finding_to_dict(findings[0]), audit_finding_to_dict(findings[1])]
    if finding_count == 3:
        return [
            audit_finding_to_dict(findings[0]),
            audit_finding_to_dict(findings[1]),
            audit_finding_to_dict(findings[2]),
        ]
    if finding_count == 4:
        return [
            audit_finding_to_dict(findings[0]),
            audit_finding_to_dict(findings[1]),
            audit_finding_to_dict(findings[2]),
            audit_finding_to_dict(findings[3]),
        ]

    serialized: list[dict[str, object]] = []
    for finding in findings:
        append_audit_finding_dict(serialized, finding)
    return serialized


def append_audit_finding_dict(
    serialized: list[dict[str, object]],
    finding: AuditFinding,
) -> None:
    serialized.append(audit_finding_to_dict(finding))


def audit_finding_to_dict(finding: AuditFinding) -> dict[str, object]:
    return {
        "path": finding.path,
        "classification": finding.classification,
        "issue_code": finding.issue_code,
        "matched_rules": finding.matched_rules,
        "rationale": finding.rationale,
        "tracked": finding.tracked,
        "ignored": finding.ignored,
    }


def audit_report_to_dict(report: AuditReport) -> dict[str, object]:
    return {
        "repo_root": report.repo_root,
        "scanned_paths": report.scanned_paths,
        "issue_count": len(report.findings),
        "findings": audit_findings_to_dicts(report.findings),
    }


def report_has_issue_codes(report: AuditReport, issue_codes: Sequence[str]) -> bool:
    for finding in report.findings:
        for issue_code in issue_codes:
            if finding.issue_code == issue_code:
                return True
    return False


def main() -> int:
    args = parse_args()
    repo_root = normalize_repo_root(args.repo_root)

    try:
        if args.command == "classify":
            results = classify_paths(args.paths, repo_root)
            if args.format == "json":
                print(format_json_payload(classifications_to_dicts(results)))
            else:
                print(render_classify_text(results))
            return 0

        if args.command == "audit":
            report = audit_paths(args.paths, repo_root)
            if args.format == "json":
                print(format_json_payload(audit_report_to_dict(report)))
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
