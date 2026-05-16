"""Focused tests for classifier-backed runtime-state repair."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path("tools/runtime_state_repair.py")
TOOLS_DIR = SCRIPT.resolve().parent


def load_repair_module():
    module_name = "runtime_state_repair_under_test"
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def run_repair(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        env=merged_env,
    )


def git(repo_root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and completed.returncode != 0:
        pytest.fail(
            f"git {' '.join(args)} failed with exit code {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed


def init_temp_repo(repo_root: Path) -> None:
    git(repo_root, "init")
    git(repo_root, "config", "user.name", "Runtime Repair Tests")
    git(repo_root, "config", "user.email", "runtime-repair-tests@example.com")


def write_file(repo_root: Path, relative_path: str, content: str) -> Path:
    path = repo_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_static_issue_code_sets_avoid_temporary_set_literals() -> None:
    repair = load_repair_module()
    source = SCRIPT.read_text(encoding="utf-8")

    assert repair.SUPPORTED_MUTATION_ISSUES == frozenset((
        repair.ISSUE_TRACKED_TRANSIENT,
        repair.ISSUE_UNIGNORED_TRANSIENT,
    ))
    assert repair.SOFT_BLOCKED_ISSUES == frozenset((repair.ISSUE_MANUAL_REVIEW,))
    assert repair.HARD_BLOCKED_ISSUES == frozenset((
        repair.ISSUE_CONFLICTING_RULE,
        repair.ISSUE_UNKNOWN_ROOT,
    ))
    assert repair.REPORT_ONLY_ISSUES == frozenset((
        repair.ISSUE_MANUAL_REVIEW,
        repair.ISSUE_CONFLICTING_RULE,
        repair.ISSUE_UNKNOWN_ROOT,
    ))
    assert "frozenset({" not in source
    assert "frozenset(SOFT_BLOCKED_ISSUES | HARD_BLOCKED_ISSUES)" not in source


def test_repair_target_normalization_uses_shared_root_scanner() -> None:
    repair = load_repair_module()
    source = SCRIPT.read_text(encoding="utf-8")
    body = source[source.index("def normalize_repair_targets") : source.index("def current_quarantine_stamp")]

    targets = (".gsd", ".planning")

    assert repair.normalize_repair_targets(targets, Path.cwd()) is targets
    assert repair.SUPPORTED_BOUNDARY_ROOTS_DISPLAY == ", ".join(repair.KNOWN_BOUNDARY_ROOTS)
    assert "repo_path_root" in repair.normalize_repair_targets.__code__.co_names
    assert "SUPPORTED_BOUNDARY_ROOTS_DISPLAY" in repair.normalize_repair_targets.__code__.co_names
    assert 'split("/", 1)' not in source
    assert "tuple(paths)" not in source
    assert "tuple(DEFAULT_AUDIT_ROOTS)" not in source
    assert '", ".join(KNOWN_BOUNDARY_ROOTS)' not in body
    assert "repair_target_tuple" in repair.normalize_repair_targets.__code__.co_names


def test_repair_target_tuple_helper_skips_iteration_for_short_sequences() -> None:
    repair = load_repair_module()

    class NoIterTargets:
        def __init__(self, items):
            self.items = items

        def __len__(self):
            return len(self.items)

        def __getitem__(self, index):
            return self.items[index]

        def __iter__(self):
            raise AssertionError("short repair target tuple normalization should not iterate")

    targets = (".gsd", ".planning")

    assert repair.repair_target_tuple(targets) is targets
    assert repair.repair_target_tuple(NoIterTargets([])) == ()
    assert repair.repair_target_tuple(NoIterTargets([".gsd"])) == (".gsd",)
    assert repair.repair_target_tuple(NoIterTargets([".gsd", ".planning"])) == (".gsd", ".planning")
    assert repair.repair_target_tuple(NoIterTargets([".gsd", ".planning", ".bg-shell"])) == (
        ".gsd",
        ".planning",
        ".bg-shell",
    )


def test_quarantine_stamp_validation_reuses_compiled_pattern(monkeypatch) -> None:
    repair = load_repair_module()
    previous = os.environ.get(repair.QUARANTINE_STAMP_ENV)

    def fail_fullmatch(*_args, **_kwargs):
        raise AssertionError("quarantine stamp validation should reuse compiled pattern")

    monkeypatch.setattr(re.fullmatch, "__call__", fail_fullmatch, raising=False)
    monkeypatch.setattr(repair.re, "fullmatch", fail_fullmatch)
    os.environ[repair.QUARANTINE_STAMP_ENV] = "stamp-123"
    try:
        assert repair.current_quarantine_stamp() == "stamp-123"
        os.environ[repair.QUARANTINE_STAMP_ENV] = "bad/stamp"
        with pytest.raises(repair.RepairError, match="letters, numbers"):
            repair.current_quarantine_stamp()
    finally:
        if previous is None:
            os.environ.pop(repair.QUARANTINE_STAMP_ENV, None)
        else:
            os.environ[repair.QUARANTINE_STAMP_ENV] = previous

    assert repair.QUARANTINE_STAMP_PATTERN.pattern == r"[A-Za-z0-9._-]+"
    assert "QUARANTINE_STAMP_PATTERN" in repair.current_quarantine_stamp.__code__.co_names
    assert "fullmatch" not in SCRIPT.read_text(encoding="utf-8").split("def current_quarantine_stamp", 1)[1].split("def build_quarantine_destination", 1)[0].replace("QUARANTINE_STAMP_PATTERN.fullmatch", "")


def test_action_planner_mutates_tracked_and_unignored_transient_findings():
    repair = load_repair_module()

    findings = (
        repair.AuditFinding(
            path=".gsd/audit/events.jsonl",
            classification="transient",
            issue_code=repair.ISSUE_TRACKED_TRANSIENT,
            matched_rules=("gsd-audit-streams",),
            rationale="tracked transient",
            tracked=True,
            ignored=True,
        ),
        repair.AuditFinding(
            path=".gsd/state-manifest.json",
            classification="transient",
            issue_code=repair.ISSUE_UNIGNORED_TRANSIENT,
            matched_rules=("gsd-runtime-files",),
            rationale="unignored transient",
            tracked=False,
            ignored=False,
        ),
        repair.AuditFinding(
            path=".planning/STATE.md",
            classification="manual-review",
            issue_code=repair.ISSUE_MANUAL_REVIEW,
            matched_rules=("planning-legacy",),
            rationale="manual review",
            tracked=True,
            ignored=False,
        ),
        repair.AuditFinding(
            path=".gsd/conflict.json",
            classification="manual-review",
            issue_code=repair.ISSUE_CONFLICTING_RULE,
            matched_rules=("durable", "transient"),
            rationale="conflict",
            tracked=False,
            ignored=False,
        ),
        repair.AuditFinding(
            path="runtime/state-manifest.json",
            classification="manual-review",
            issue_code=repair.ISSUE_UNKNOWN_ROOT,
            matched_rules=(),
            rationale="unknown root",
            tracked=False,
            ignored=False,
        ),
    )
    audit_report = repair.AuditReport(
        repo_root="/tmp/repo",
        scanned_paths=len(findings),
        findings=findings,
    )

    previous = os.environ.get(repair.QUARANTINE_STAMP_ENV)
    os.environ[repair.QUARANTINE_STAMP_ENV] = "stamp-123"
    try:
        actions = repair.plan_repair_actions(audit_report, dry_run=True)
    finally:
        if previous is None:
            os.environ.pop(repair.QUARANTINE_STAMP_ENV, None)
        else:
            os.environ[repair.QUARANTINE_STAMP_ENV] = previous

    assert [action.action for action in actions] == [
        repair.ACTION_DEINDEX,
        repair.ACTION_QUARANTINE,
        repair.ACTION_BLOCKED,
        repair.ACTION_BLOCKED,
        repair.ACTION_BLOCKED,
    ]
    assert actions[0].status == "planned"
    assert actions[0].command == ("git", "rm", "--cached", "--", ".gsd/audit/events.jsonl")
    assert actions[1].status == "planned"
    assert actions[1].destination == ".gsd/runtime/repair-quarantine/stamp-123/.gsd/state-manifest.json"
    assert actions[1].mutate is True
    assert "<genexpr>" not in {
        const.co_name
        for const in repair.plan_repair_actions.__code__.co_consts
        if hasattr(const, "co_name")
    }
    assert all(not action.mutate for action in actions[2:])
    assert {action.issue_code for action in actions[2:]} == {
        repair.ISSUE_MANUAL_REVIEW,
        repair.ISSUE_CONFLICTING_RULE,
        repair.ISSUE_UNKNOWN_ROOT,
    }


def test_action_planner_defers_quarantine_stamp_until_needed(monkeypatch) -> None:
    repair = load_repair_module()
    tracked = repair.AuditFinding(
        path=".gsd/audit/events.jsonl",
        classification="transient",
        issue_code=repair.ISSUE_TRACKED_TRANSIENT,
        matched_rules=("gsd-runtime-files",),
        rationale="tracked transient",
        tracked=True,
        ignored=True,
    )
    manual = repair.AuditFinding(
        path=".planning/STATE.md",
        classification="manual-review",
        issue_code=repair.ISSUE_MANUAL_REVIEW,
        matched_rules=("planning-legacy",),
        rationale="manual review",
        tracked=False,
        ignored=False,
    )
    quarantine_a = repair.AuditFinding(
        path=".gsd/state-a.json",
        classification="transient",
        issue_code=repair.ISSUE_UNIGNORED_TRANSIENT,
        matched_rules=("gsd-runtime-files",),
        rationale="unignored transient",
        tracked=False,
        ignored=False,
    )
    quarantine_b = repair.AuditFinding(
        path=".gsd/state-b.json",
        classification="transient",
        issue_code=repair.ISSUE_UNIGNORED_TRANSIENT,
        matched_rules=("gsd-runtime-files",),
        rationale="unignored transient",
        tracked=False,
        ignored=False,
    )

    def fail_stamp() -> str:
        raise AssertionError("quarantine stamp should only be generated for quarantine findings")

    monkeypatch.setattr(repair, "current_quarantine_stamp", fail_stamp)
    empty_report = repair.AuditReport(
        repo_root="/tmp/repo",
        scanned_paths=0,
        findings=(),
    )
    no_quarantine_report = repair.AuditReport(
        repo_root="/tmp/repo",
        scanned_paths=2,
        findings=(tracked, manual),
    )

    assert repair.plan_repair_actions(empty_report, dry_run=True) == ()

    actions = repair.plan_repair_actions(no_quarantine_report, dry_run=True)

    assert [action.action for action in actions] == [repair.ACTION_DEINDEX, repair.ACTION_BLOCKED]

    calls = 0

    def counted_stamp() -> str:
        nonlocal calls
        calls += 1
        return "shared-stamp"

    monkeypatch.setattr(repair, "current_quarantine_stamp", counted_stamp)
    quarantine_report = repair.AuditReport(
        repo_root="/tmp/repo",
        scanned_paths=2,
        findings=(quarantine_a, quarantine_b),
    )

    actions = repair.plan_repair_actions(quarantine_report, dry_run=True)

    assert calls == 1
    assert [action.destination for action in actions] == [
        ".gsd/runtime/repair-quarantine/shared-stamp/.gsd/state-a.json",
        ".gsd/runtime/repair-quarantine/shared-stamp/.gsd/state-b.json",
    ]
    assert "current_quarantine_stamp" in repair.plan_repair_actions.__code__.co_names


def test_dry_run_json_reports_counts_for_actionable_and_blocked_findings(tmp_path: Path):
    repo_root = tmp_path
    init_temp_repo(repo_root)

    write_file(repo_root, ".gitignore", ".gsd/audit/\n.gsd/runtime/\n")
    tracked_transient = write_file(repo_root, ".gsd/audit/events.jsonl", '{"event":"tracked"}\n')
    manual_review = write_file(repo_root, ".planning/STATE.md", "legacy\n")
    git(repo_root, "add", ".gitignore", str(manual_review.relative_to(repo_root)))
    git(repo_root, "add", "-f", str(tracked_transient.relative_to(repo_root)))

    result = run_repair("--repo-root", str(repo_root), "--dry-run", "--format", "json", env={"RUNTIME_STATE_REPAIR_QUARANTINE_STAMP": "dry-run-stamp"})

    assert result.returncode == 1, result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "dry-run"
    assert payload["summary"]["deindex_count"] == 1
    assert payload["summary"]["quarantine_count"] == 0
    assert payload["summary"]["blocked_count"] == 1
    assert payload["summary"]["failed_count"] == 0
    assert payload["summary"]["noop_count"] == 0
    actions = {(row["issue_code"], row["status"], row["action"], row["path"]) for row in payload["actions"]}
    assert ("tracked-transient", "planned", "deindex-tracked-transient", ".gsd/audit/events.jsonl") in actions
    assert ("manual-review-path", "blocked", "blocked", ".planning/STATE.md") in actions


def test_repair_report_reuses_single_action_count_accumulator(monkeypatch):
    """Report counts should share the summary count pass instead of rescanning with sum()."""
    repair = load_repair_module()

    def fail_sum(*_args, **_kwargs):
        raise AssertionError("repair report counts should use the shared accumulator")

    def fail_summarize(_actions):
        raise AssertionError("build_repair_report should not run a separate summary scan")

    monkeypatch.setattr("builtins.sum", fail_sum)
    monkeypatch.setattr(repair, "summarize_actions", fail_summarize)

    actions = (
        repair.RepairAction(
            path=".gsd/audit/events.jsonl",
            issue_code=repair.ISSUE_TRACKED_TRANSIENT,
            classification="transient",
            action=repair.ACTION_DEINDEX,
            status="planned",
            mutate=True,
            tracked=True,
            ignored=True,
            rationale="tracked transient",
        ),
        repair.RepairAction(
            path=".gsd/state-manifest.json",
            issue_code=repair.ISSUE_UNIGNORED_TRANSIENT,
            classification="transient",
            action=repair.ACTION_QUARANTINE,
            status="failed",
            mutate=True,
            tracked=False,
            ignored=False,
            rationale="unignored transient",
        ),
        repair.RepairAction(
            path=".planning/STATE.md",
            issue_code=repair.ISSUE_MANUAL_REVIEW,
            classification="manual-review",
            action=repair.ACTION_BLOCKED,
            status="blocked",
            mutate=False,
            tracked=True,
            ignored=False,
            rationale="manual review",
        ),
    )
    audit_report = repair.AuditReport(repo_root="/tmp/repo", scanned_paths=3, findings=())

    report = repair.build_repair_report(audit_report, actions, dry_run=True)

    assert report.actions is actions
    assert report.actionable_issue_count == 2
    assert report.blocked_issue_count == 1
    assert report.failed_issue_count == 1
    assert report.summary.deindex_count == 1
    assert report.summary.quarantine_count == 0
    assert report.summary.blocked_count == 1
    assert report.summary.failed_count == 1
    assert report.summary.noop_count == 0


def test_text_report_shell_quotes_action_commands():
    repair = load_repair_module()
    action = repair.RepairAction(
        path=".gsd/a path.json",
        issue_code=repair.ISSUE_TRACKED_TRANSIENT,
        classification="transient",
        action=repair.ACTION_DEINDEX,
        status="planned",
        mutate=True,
        tracked=True,
        ignored=True,
        rationale="tracked transient",
        command=("git", "rm", "--cached", "--", ".gsd/a path.json"),
        destination=None,
        detail=None,
    )
    report = repair.RepairReport(
        repo_root="/tmp/repo",
        mode="dry-run",
        scanned_paths=1,
        issue_count=1,
        actionable_issue_count=1,
        blocked_issue_count=0,
        failed_issue_count=0,
        summary=repair.RepairSummary(
            deindex_count=1,
            quarantine_count=0,
            blocked_count=0,
            failed_count=0,
            noop_count=0,
        ),
        actions=(action,),
    )

    text = repair.render_text(report)

    assert "command=git rm --cached -- '.gsd/a path.json'" in text


def test_render_text_no_action_path_uses_direct_header() -> None:
    repair = load_repair_module()
    report = repair.RepairReport(
        repo_root="/tmp/repo",
        mode="dry-run",
        scanned_paths=0,
        issue_count=0,
        actionable_issue_count=0,
        blocked_issue_count=0,
        failed_issue_count=0,
        summary=repair.RepairSummary(
            deindex_count=0,
            quarantine_count=0,
            blocked_count=0,
            failed_count=0,
            noop_count=1,
        ),
        actions=(),
    )

    text = repair.render_text(report)
    source = SCRIPT.read_text(encoding="utf-8")
    render_source = source[
        source.index("def render_text"):
        source.index("def _render_text_header")
    ]

    assert text.endswith("noop_count: 1\nactions: none")
    assert "_render_text_header" in repair.render_text.__code__.co_names
    assert 'return header + "\\nactions: none"' in render_source


def test_execute_plan_empty_actions_returns_before_repair_helpers(monkeypatch, tmp_path: Path):
    repair = load_repair_module()

    def fail_repair(*_args, **_kwargs):
        raise AssertionError("empty execute_plan should not call mutation helpers")

    monkeypatch.setattr(repair, "apply_tracked_transient_repair", fail_repair)
    monkeypatch.setattr(repair, "apply_unignored_transient_repair", fail_repair)

    assert repair.execute_plan((), tmp_path, dry_run=False) == ()


def test_execute_plan_dry_run_reuses_action_tuple(monkeypatch, tmp_path: Path) -> None:
    repair = load_repair_module()
    action = repair.RepairAction(
        path=".gsd/audit/events.jsonl",
        issue_code=repair.ISSUE_TRACKED_TRANSIENT,
        classification="transient",
        action=repair.ACTION_DEINDEX,
        status="planned",
        mutate=True,
        tracked=True,
        ignored=True,
        rationale="tracked transient",
        command=("git", "rm", "--cached", "--", ".gsd/audit/events.jsonl"),
    )
    actions = (action,)

    def fail_repair(*_args, **_kwargs):
        raise AssertionError("dry-run execute_plan should not call mutation helpers")

    monkeypatch.setattr(repair, "apply_tracked_transient_repair", fail_repair)
    monkeypatch.setattr(repair, "apply_unignored_transient_repair", fail_repair)

    assert repair.execute_plan(actions, tmp_path, dry_run=True) is actions


def test_repair_action_tuple_helper_skips_iteration_for_short_action_sequences() -> None:
    repair = load_repair_module()
    action = repair.RepairAction(
        path=".gsd/audit/events.jsonl",
        issue_code=repair.ISSUE_TRACKED_TRANSIENT,
        classification="transient",
        action=repair.ACTION_DEINDEX,
        status="planned",
        mutate=True,
        tracked=True,
        ignored=True,
        rationale="tracked transient",
        command=("git", "rm", "--cached", "--", ".gsd/audit/events.jsonl"),
    )
    second_action = repair.replace_action(action, status="pending", detail="second")

    class NoIterActions:
        def __init__(self, items):
            self.items = items

        def __len__(self):
            return len(self.items)

        def __getitem__(self, index):
            return self.items[index]

        def __iter__(self):
            raise AssertionError("short action tuple normalization should not iterate")

    actions = (action,)

    assert repair.repair_actions_tuple(actions) is actions
    assert repair.repair_actions_tuple(NoIterActions([])) == ()
    assert repair.repair_actions_tuple(NoIterActions([action])) == (action,)
    assert repair.repair_actions_tuple(NoIterActions([action, second_action])) == (action, second_action)
    assert repair.repair_actions_tuple(NoIterActions([action, second_action, action])) == (
        action,
        second_action,
        action,
    )
    assert "repair_actions_tuple" in repair.plan_repair_actions.__code__.co_names
    assert "repair_actions_tuple" in repair.execute_plan.__code__.co_names
    assert "repair_actions_tuple" in repair.build_repair_report.__code__.co_names


def test_apply_tracked_transient_uses_existing_command_tuple(monkeypatch, tmp_path: Path):
    """Tracked-transient repair should avoid copying the command before subprocess execution."""
    repair = load_repair_module()
    action = repair.RepairAction(
        path=".gsd/audit/events.jsonl",
        issue_code=repair.ISSUE_TRACKED_TRANSIENT,
        classification="transient",
        action=repair.ACTION_DEINDEX,
        status="pending",
        mutate=True,
        tracked=True,
        ignored=True,
        rationale="tracked transient",
        command=("git", "rm", "--cached", "--", ".gsd/audit/events.jsonl"),
    )
    target = tmp_path / action.path
    target.parent.mkdir(parents=True)
    target.write_text('{"event":"kept"}\n', encoding="utf-8")

    def fake_run(command, **_kwargs):
        assert command is action.command
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(repair.subprocess, "run", fake_run)

    result = repair.apply_tracked_transient_repair(action, tmp_path)

    assert result.status == "applied"
    assert "list(action.command)" not in SCRIPT.read_text(encoding="utf-8")


def test_replace_action_preserves_immutable_field_identity():
    """Action status updates should preserve immutable command tuple identity."""
    repair = load_repair_module()
    command = ("git", "rm", "--cached", "--", ".gsd/audit/events.jsonl")
    action = repair.RepairAction(
        path=".gsd/audit/events.jsonl",
        issue_code=repair.ISSUE_TRACKED_TRANSIENT,
        classification="transient",
        action=repair.ACTION_DEINDEX,
        status="pending",
        mutate=True,
        tracked=True,
        ignored=True,
        rationale="tracked transient",
        command=command,
    )

    replaced = repair.replace_action(action, status="applied", detail="done")

    assert replaced.status == "applied"
    assert replaced.detail == "done"
    assert replaced.command is command
    assert "dataclass_replace" in repair.replace_action.__code__.co_names


def test_json_output_uses_boundary_json_formatter() -> None:
    repair = load_repair_module()

    assert "format_json_payload" in repair.main.__code__.co_names


def test_repair_report_json_serializes_actions_directly() -> None:
    """Repair report JSON should use direct action and summary serialization."""
    repair = load_repair_module()
    action = repair.RepairAction(
        path=".gsd/audit/events.jsonl",
        issue_code=repair.ISSUE_TRACKED_TRANSIENT,
        classification="transient",
        action=repair.ACTION_DEINDEX,
        status="planned",
        mutate=True,
        tracked=True,
        ignored=True,
        rationale="tracked transient",
        command=("git", "rm", "--cached", "--", ".gsd/audit/events.jsonl"),
    )
    report = repair.RepairReport(
        repo_root="/tmp/repo",
        mode="dry-run",
        scanned_paths=1,
        issue_count=1,
        actionable_issue_count=1,
        blocked_issue_count=0,
        failed_issue_count=0,
        summary=repair.RepairSummary(
            deindex_count=1,
            quarantine_count=0,
            blocked_count=0,
            failed_count=0,
            noop_count=0,
        ),
        actions=(action,),
    )

    payload = repair.repair_report_to_dict(report)

    class NoIterActions:
        def __init__(self, items):
            self.items = items

        def __len__(self):
            return len(self.items)

        def __getitem__(self, index):
            return self.items[index]

        def __iter__(self):
            raise AssertionError("short repair action JSON serialization should not iterate")

    assert payload["summary"] == repair.repair_summary_to_dict(report.summary)
    assert payload["actions"] == [repair.repair_action_to_dict(action)]
    assert repair.repair_actions_to_dicts(()) == []
    assert repair.repair_actions_to_dicts(NoIterActions([action])) == [
        repair.repair_action_to_dict(action),
    ]
    assert repair.repair_actions_to_dicts(NoIterActions([action, action])) == [
        repair.repair_action_to_dict(action),
        repair.repair_action_to_dict(action),
    ]
    assert repair.repair_actions_to_dicts(NoIterActions([action, action, action])) == [
        repair.repair_action_to_dict(action),
        repair.repair_action_to_dict(action),
        repair.repair_action_to_dict(action),
    ]
    assert "repair_actions_to_dicts" in repair.repair_report_to_dict.__code__.co_names
    assert "repair_summary_to_dict" in repair.repair_report_to_dict.__code__.co_names
    assert "repair_action_to_dict" in repair.repair_actions_to_dicts.__code__.co_names
    assert "len" in repair.repair_actions_to_dicts.__code__.co_names
    assert "asdict" not in repair.repair_report_to_dict.__code__.co_names
    assert "asdict" not in repair.repair_action_to_dict.__code__.co_names
    assert "asdict" not in repair.repair_summary_to_dict.__code__.co_names
    assert "asdict" not in SCRIPT.read_text(encoding="utf-8")
    assert "<listcomp>" not in {
        const.co_name
        for const in repair.repair_actions_to_dicts.__code__.co_consts
        if hasattr(const, "co_name")
    }


def test_repair_records_use_slots_to_avoid_instance_dict() -> None:
    repair = load_repair_module()
    action = repair.RepairAction(
        path=".gsd/audit/events.jsonl",
        issue_code=repair.ISSUE_TRACKED_TRANSIENT,
        classification="transient",
        action=repair.ACTION_DEINDEX,
        status="planned",
        mutate=True,
        tracked=True,
        ignored=True,
        rationale="tracked transient",
    )
    summary = repair.RepairSummary(
        deindex_count=1,
        quarantine_count=0,
        blocked_count=0,
        failed_count=0,
        noop_count=0,
    )
    counts = repair.RepairActionCounts(
        summary=summary,
        actionable_issue_count=1,
        blocked_issue_count=0,
        failed_issue_count=0,
    )
    report = repair.RepairReport(
        repo_root="/tmp/repo",
        mode="dry-run",
        scanned_paths=1,
        issue_count=1,
        actionable_issue_count=1,
        blocked_issue_count=0,
        failed_issue_count=0,
        summary=summary,
        actions=(action,),
    )

    assert not hasattr(action, "__dict__")
    assert not hasattr(summary, "__dict__")
    assert not hasattr(counts, "__dict__")
    assert not hasattr(report, "__dict__")


def test_exit_code_uses_static_unapplied_status_membership(monkeypatch) -> None:
    """Exit-code handling should reuse a static status table and direct action scan."""
    repair = load_repair_module()
    action = repair.RepairAction(
        path=".gsd/state-manifest.json",
        issue_code=repair.ISSUE_UNIGNORED_TRANSIENT,
        classification="transient",
        action="deindex",
        status="planned",
        mutate=True,
        tracked=False,
        ignored=False,
        rationale="runtime state",
    )
    report = repair.RepairReport(
        repo_root="/tmp/repo",
        mode="dry-run",
        scanned_paths=1,
        issue_count=1,
        actionable_issue_count=1,
        blocked_issue_count=0,
        failed_issue_count=0,
        summary=repair.RepairSummary(
            deindex_count=1,
            quarantine_count=0,
            blocked_count=0,
            failed_count=0,
            noop_count=0,
        ),
        actions=(action,),
    )

    def fail_any(*_args, **_kwargs):
        raise AssertionError("exit-code action checks should scan directly")

    monkeypatch.setattr("builtins.any", fail_any)

    assert repair._UNAPPLIED_ACTION_STATUSES == frozenset(("planned", "pending"))
    assert repair.exit_code_for_report(report) == 1
    assert repair.report_has_exit_blocking_action((action,)) is True
    nested_names = set(repair.exit_code_for_report.__code__.co_names)
    nested_names.update(repair.report_has_exit_blocking_action.__code__.co_names)
    for const in repair.exit_code_for_report.__code__.co_consts:
        if hasattr(const, "co_names"):
            nested_names.update(const.co_names)
    for const in repair.report_has_exit_blocking_action.__code__.co_consts:
        if hasattr(const, "co_names"):
            nested_names.update(const.co_names)
    assert "_UNAPPLIED_ACTION_STATUSES" in nested_names
    assert "<genexpr>" not in {
        const.co_name
        for const in repair.report_has_exit_blocking_action.__code__.co_consts
        if hasattr(const, "co_name")
    }


def test_apply_deindexes_tracked_transient_and_preserves_worktree_contents(tmp_path: Path):
    repo_root = tmp_path
    init_temp_repo(repo_root)

    write_file(repo_root, ".gitignore", ".gsd/audit/\n.gsd/runtime/\n")
    tracked_transient = write_file(repo_root, ".gsd/audit/events.jsonl", '{"event":"tracked"}\n')
    git(repo_root, "add", ".gitignore")
    git(repo_root, "add", "-f", str(tracked_transient.relative_to(repo_root)))
    git(repo_root, "commit", "-m", "seed tracked transient")

    result = run_repair("--repo-root", str(repo_root), "--format", "json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "apply"
    assert payload["summary"]["deindex_count"] == 1
    assert payload["summary"]["blocked_count"] == 0
    assert payload["summary"]["failed_count"] == 0
    assert payload["actions"][0]["status"] == "applied"
    assert tracked_transient.exists()
    assert tracked_transient.read_text(encoding="utf-8") == '{"event":"tracked"}\n'
    assert git(repo_root, "ls-files", "--", ".gsd/audit/events.jsonl").stdout == ""

    boundary_audit = subprocess.run(
        [
            sys.executable,
            str(Path("tools/runtime_state_boundary.py")),
            "audit",
            "--repo-root",
            str(repo_root),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert boundary_audit.returncode == 0, boundary_audit.stderr
    assert json.loads(boundary_audit.stdout)["findings"] == []


def test_manual_review_only_apply_is_safe_and_reports_blocked_path(tmp_path: Path):
    repo_root = tmp_path
    init_temp_repo(repo_root)

    planning_path = write_file(repo_root, ".planning/STATE.md", "legacy planning notes\n")
    git(repo_root, "add", str(planning_path.relative_to(repo_root)))
    git(repo_root, "commit", "-m", "seed manual review path")

    result = run_repair("--repo-root", str(repo_root), "--format", "json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["summary"]["blocked_count"] == 1
    assert payload["summary"]["deindex_count"] == 0
    assert payload["summary"]["quarantine_count"] == 0
    assert payload["actions"] == [
        {
            "path": ".planning/STATE.md",
            "issue_code": "manual-review-path",
            "classification": "manual-review",
            "action": "blocked",
            "status": "blocked",
            "mutate": False,
            "tracked": True,
            "ignored": False,
            "rationale": ".planning is a mixed legacy workflow tree and stays manual-review until a later slice migrates it safely.",
            "command": None,
            "destination": None,
            "detail": "manual-review paths remain report-only and never mutate automatically",
        }
    ]
    assert planning_path.exists()
    assert planning_path.read_text(encoding="utf-8") == "legacy planning notes\n"


def test_quarantine_fails_when_destination_collision_exists(tmp_path: Path):
    repo_root = tmp_path
    init_temp_repo(repo_root)

    write_file(repo_root, ".gitignore", ".gsd/runtime/\n")
    write_file(repo_root, ".gsd/state-manifest.json", '{"jobs":[]}\n')
    collision = write_file(
        repo_root,
        ".gsd/runtime/repair-quarantine/fixed-stamp/.gsd/state-manifest.json",
        '{"jobs":["collision"]}\n',
    )

    result = run_repair(
        "--repo-root",
        str(repo_root),
        "--format",
        "json",
        env={"RUNTIME_STATE_REPAIR_QUARANTINE_STAMP": "fixed-stamp"},
    )

    assert result.returncode == 1, result.stderr
    payload = json.loads(result.stdout)
    assert payload["summary"]["failed_count"] == 1
    assert payload["summary"]["quarantine_count"] == 0
    assert payload["actions"][0]["status"] == "failed"
    assert payload["actions"][0]["detail"] == (
        "quarantine destination already exists: "
        ".gsd/runtime/repair-quarantine/fixed-stamp/.gsd/state-manifest.json"
    )
    assert collision.exists()
    assert (repo_root / ".gsd/state-manifest.json").exists()


def test_cli_rejects_unsupported_root_argument():
    result = run_repair("README.md")

    assert result.returncode == 2
    assert "supported boundary roots" in result.stderr


def test_clean_repo_reports_noop(tmp_path: Path):
    repo_root = tmp_path
    init_temp_repo(repo_root)

    write_file(repo_root, ".gitignore", ".gsd/audit/\n.gsd/runtime/\n.gsd/state-manifest.json\n")
    write_file(repo_root, ".gsd/milestones/M014/M014-ROADMAP.md", "durable\n")
    git(repo_root, "add", ".")
    git(repo_root, "commit", "-m", "seed durable files")

    result = run_repair("--repo-root", str(repo_root), "--format", "json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["summary"]["noop_count"] == 1
    assert payload["summary"]["deindex_count"] == 0
    assert payload["summary"]["quarantine_count"] == 0
    assert payload["actions"] == []
