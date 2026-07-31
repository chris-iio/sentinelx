"""Temp-repo Git regression tests for runtime-state repair."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
REPAIR_SCRIPT = (REPO_ROOT / "tools" / "runtime_state_repair.py").resolve()
BOUNDARY_SCRIPT = (REPO_ROOT / "tools" / "runtime_state_boundary.py").resolve()
BOUNDARY_IGNORE_RULES = ".gsd/audit/\n.gsd/runtime/\n"


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


def run_repair(repo_root: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [sys.executable, str(REPAIR_SCRIPT), *args, "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
        env=merged_env,
    )


def run_boundary(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(BOUNDARY_SCRIPT), *args, "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )


def write_file(repo_root: Path, relative_path: str, content: str) -> Path:
    path = repo_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def init_temp_repo(repo_root: Path) -> None:
    git(repo_root, "init")
    git(repo_root, "config", "user.name", "Runtime Repair Git Tests")
    git(repo_root, "config", "user.email", "runtime-repair-git-tests@example.com")
    # Isolate tests from developer-global hooks (for example identity guards).
    git(repo_root, "config", "core.hooksPath", os.devnull)


def parse_actions(result: subprocess.CompletedProcess[str]) -> list[dict[str, object]]:
    return json.loads(result.stdout)["actions"]


def parse_findings(result: subprocess.CompletedProcess[str]) -> set[tuple[str, str]]:
    payload = json.loads(result.stdout)
    return {(row["issue_code"], row["path"]) for row in payload["findings"]}


def test_repair_apply_deindexes_and_quarantines_actionable_findings_while_leaving_manual_review_visible(tmp_path: Path):
    repo_root = tmp_path
    init_temp_repo(repo_root)

    write_file(repo_root, ".gitignore", BOUNDARY_IGNORE_RULES)
    tracked_transient = write_file(repo_root, ".gsd/audit/events.jsonl", '{"event":"tracked"}\n')
    unignored_transient = write_file(repo_root, ".gsd/state-manifest.json", '{"jobs":["runtime"]}\n')
    manual_review = write_file(repo_root, ".planning/STATE.md", "legacy planning\n")

    git(repo_root, "add", ".gitignore", str(manual_review.relative_to(repo_root)))
    git(repo_root, "add", "-f", str(tracked_transient.relative_to(repo_root)))
    git(repo_root, "commit", "-m", "seed tracked and unignored runtime state")

    result = run_repair(
        repo_root,
        "--format",
        "json",
        env={"RUNTIME_STATE_REPAIR_QUARANTINE_STAMP": "apply-stamp"},
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["summary"] == {
        "deindex_count": 1,
        "quarantine_count": 1,
        "blocked_count": 1,
        "failed_count": 0,
        "noop_count": 0,
    }
    actions = {(row["issue_code"], row["action"], row["status"], row["path"]) for row in payload["actions"]}
    assert ("tracked-transient", "deindex-tracked-transient", "applied", ".gsd/audit/events.jsonl") in actions
    assert ("unignored-transient", "quarantine-unignored-transient", "applied", ".gsd/state-manifest.json") in actions
    assert ("manual-review-path", "blocked", "blocked", ".planning/STATE.md") in actions

    quarantine_path = repo_root / ".gsd/runtime/repair-quarantine/apply-stamp/.gsd/state-manifest.json"
    assert tracked_transient.exists()
    assert git(repo_root, "ls-files", "--", ".gsd/audit/events.jsonl").stdout == ""
    assert not unignored_transient.exists()
    assert quarantine_path.exists()
    assert quarantine_path.read_text(encoding="utf-8") == '{"jobs":["runtime"]}\n'
    ignored = git(repo_root, "check-ignore", "-v", ".gsd/runtime/repair-quarantine/apply-stamp/.gsd/state-manifest.json")
    assert ".gitignore" in ignored.stdout
    assert ".gsd/runtime/repair-quarantine/apply-stamp/.gsd/state-manifest.json" in ignored.stdout

    audit = run_boundary(repo_root, "audit", "--format", "json")
    assert audit.returncode == 0, audit.stderr
    assert parse_findings(audit) == {("manual-review-path", ".planning/STATE.md")}


def test_manual_review_only_repo_remains_untouched_and_visible(tmp_path: Path):
    repo_root = tmp_path
    init_temp_repo(repo_root)

    manual_review = write_file(repo_root, ".planning/STATE.md", "keep for migration\n")
    git(repo_root, "add", str(manual_review.relative_to(repo_root)))
    git(repo_root, "commit", "-m", "seed manual review only")

    result = run_repair(repo_root, "--format", "json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["summary"] == {
        "deindex_count": 0,
        "quarantine_count": 0,
        "blocked_count": 1,
        "failed_count": 0,
        "noop_count": 0,
    }
    assert parse_actions(result)[0]["detail"] == "manual-review paths remain report-only and never mutate automatically"
    assert manual_review.exists()
    assert manual_review.read_text(encoding="utf-8") == "keep for migration\n"


def test_repeated_repair_run_converges_to_noop_after_actionable_fixes(tmp_path: Path):
    repo_root = tmp_path
    init_temp_repo(repo_root)

    write_file(repo_root, ".gitignore", BOUNDARY_IGNORE_RULES)
    tracked_transient = write_file(repo_root, ".gsd/audit/events.jsonl", '{"event":"tracked"}\n')
    write_file(repo_root, ".gsd/state-manifest.json", '{"jobs":["runtime"]}\n')
    git(repo_root, "add", ".gitignore")
    git(repo_root, "add", "-f", str(tracked_transient.relative_to(repo_root)))
    git(repo_root, "commit", "-m", "seed actionable runtime state")

    first = run_repair(
        repo_root,
        "--format",
        "json",
        env={"RUNTIME_STATE_REPAIR_QUARANTINE_STAMP": "repeat-stamp"},
    )
    assert first.returncode == 0, first.stderr
    first_payload = json.loads(first.stdout)
    assert first_payload["summary"]["deindex_count"] == 1
    assert first_payload["summary"]["quarantine_count"] == 1

    second = run_repair(repo_root, "--format", "json")
    assert second.returncode == 0, second.stderr
    second_payload = json.loads(second.stdout)
    assert second_payload["summary"] == {
        "deindex_count": 0,
        "quarantine_count": 0,
        "blocked_count": 0,
        "failed_count": 0,
        "noop_count": 1,
    }
    assert second_payload["actions"] == []

    audit = run_boundary(repo_root, "audit", "--format", "json")
    assert audit.returncode == 0, audit.stderr
    assert json.loads(audit.stdout)["findings"] == []
