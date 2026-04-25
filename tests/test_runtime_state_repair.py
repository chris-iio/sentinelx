"""Focused tests for classifier-backed runtime-state repair."""
from __future__ import annotations

import importlib.util
import json
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


def run_repair(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
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


def test_action_planner_only_mutates_tracked_transient_findings():
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

    actions = repair.plan_repair_actions(audit_report, dry_run=True)

    assert [action.action for action in actions] == [
        repair.ACTION_DEINDEX,
        repair.ACTION_BLOCKED,
        repair.ACTION_BLOCKED,
        repair.ACTION_BLOCKED,
        repair.ACTION_BLOCKED,
    ]
    assert actions[0].status == "planned"
    assert actions[0].command == ("git", "rm", "--cached", "--", ".gsd/audit/events.jsonl")
    assert all(not action.mutate for action in actions[1:])
    assert {action.issue_code for action in actions[1:]} == {
        repair.ISSUE_UNIGNORED_TRANSIENT,
        repair.ISSUE_MANUAL_REVIEW,
        repair.ISSUE_CONFLICTING_RULE,
        repair.ISSUE_UNKNOWN_ROOT,
    }


def test_dry_run_json_reports_counts_for_actionable_and_blocked_findings(tmp_path: Path):
    repo_root = tmp_path
    init_temp_repo(repo_root)

    write_file(repo_root, ".gitignore", ".gsd/audit/\n")
    tracked_transient = write_file(repo_root, ".gsd/audit/events.jsonl", '{"event":"tracked"}\n')
    manual_review = write_file(repo_root, ".planning/STATE.md", "legacy\n")
    git(repo_root, "add", ".gitignore", str(manual_review.relative_to(repo_root)))
    git(repo_root, "add", "-f", str(tracked_transient.relative_to(repo_root)))

    result = run_repair("--repo-root", str(repo_root), "--dry-run", "--format", "json")

    assert result.returncode == 1, result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "dry-run"
    assert payload["summary"]["deindex_count"] == 1
    assert payload["summary"]["blocked_count"] == 1
    assert payload["summary"]["failed_count"] == 0
    assert payload["summary"]["noop_count"] == 0
    actions = {(row["issue_code"], row["status"], row["action"], row["path"]) for row in payload["actions"]}
    assert ("tracked-transient", "planned", "deindex-tracked-transient", ".gsd/audit/events.jsonl") in actions
    assert ("manual-review-path", "blocked", "blocked", ".planning/STATE.md") in actions


def test_apply_deindexes_tracked_transient_and_preserves_worktree_contents(tmp_path: Path):
    repo_root = tmp_path
    init_temp_repo(repo_root)

    write_file(repo_root, ".gitignore", ".gsd/audit/\n")
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


def test_cli_rejects_unsupported_root_argument():
    result = run_repair("README.md")

    assert result.returncode == 2
    assert "supported boundary roots" in result.stderr


def test_clean_repo_reports_noop(tmp_path: Path):
    repo_root = tmp_path
    init_temp_repo(repo_root)

    write_file(repo_root, ".gitignore", ".gsd/audit/\n.gsd/state-manifest.json\n")
    write_file(repo_root, ".gsd/milestones/M014/M014-ROADMAP.md", "durable\n")
    git(repo_root, "add", ".")
    git(repo_root, "commit", "-m", "seed durable files")

    result = run_repair("--repo-root", str(repo_root), "--format", "json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["summary"]["noop_count"] == 1
    assert payload["summary"]["deindex_count"] == 0
    assert payload["actions"] == []
