"""Temp-repo Git regression tests for the runtime-state boundary."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = (Path(__file__).resolve().parents[1] / "tools" / "runtime_state_boundary.py").resolve()
BOUNDARY_IGNORE_RULES = """.gsd/audit/
.gsd/state-manifest.json
.gsd/event-log.jsonl
"""


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


def run_boundary(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )


def write_file(repo_root: Path, relative_path: str, content: str) -> Path:
    path = repo_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def init_temp_repo(repo_root: Path) -> str:
    git(repo_root, "init")
    git(repo_root, "config", "user.name", "Runtime Boundary Tests")
    git(repo_root, "config", "user.email", "runtime-boundary-tests@example.com")
    return git(repo_root, "branch", "--show-current").stdout.strip() or "master"


def parse_findings(result: subprocess.CompletedProcess[str]) -> set[tuple[str, str]]:
    payload = json.loads(result.stdout)
    return {(row["issue_code"], row["path"]) for row in payload["findings"]}


def test_tracked_transient_stash_pop_conflict_is_surfaced_before_pop(tmp_path: Path):
    repo_root = tmp_path
    base_branch = init_temp_repo(repo_root)

    write_file(repo_root, ".gitignore", BOUNDARY_IGNORE_RULES)
    write_file(repo_root, ".gsd/milestones/M014/M014-ROADMAP.md", "durable milestone\n")
    tracked_transient = write_file(repo_root, ".gsd/audit/events.jsonl", '{"event":"base"}\n')

    git(repo_root, "add", ".gitignore", ".gsd/milestones/M014/M014-ROADMAP.md")
    git(repo_root, "add", "-f", ".gsd/audit/events.jsonl")
    git(repo_root, "commit", "-m", "seed tracked transient")

    tracked_transient.write_text('{"event":"runtime-local"}\n', encoding="utf-8")
    stash = git(repo_root, "stash", "push", "-m", "runtime transient")
    assert stash.returncode == 0, stash.stderr

    git(repo_root, "checkout", "-b", "feature")
    tracked_transient.write_text('{"event":"branch-change"}\n', encoding="utf-8")
    git(repo_root, "commit", "-am", "branch rewrites transient log")

    audit = run_boundary(repo_root, "audit", "--format", "json")
    assert audit.returncode == 0, audit.stderr
    findings = parse_findings(audit)
    assert ("tracked-transient", ".gsd/audit/events.jsonl") in findings
    assert all(path != ".gsd/milestones/M014/M014-ROADMAP.md" for _, path in findings)

    pop = git(repo_root, "stash", "pop", check=False)
    combined_output = f"{pop.stdout}\n{pop.stderr}"
    assert pop.returncode != 0
    assert ".gsd/audit/events.jsonl" in combined_output
    assert "CONFLICT" in combined_output or "both modified" in combined_output

    git(repo_root, "checkout", base_branch, check=False)


def test_ignored_untracked_transients_do_not_block_checkout_or_audit(tmp_path: Path):
    repo_root = tmp_path
    base_branch = init_temp_repo(repo_root)

    write_file(repo_root, ".gitignore", BOUNDARY_IGNORE_RULES)
    write_file(repo_root, ".gsd/milestones/M014/M014-ROADMAP.md", "durable milestone\n")
    write_file(repo_root, "README.md", "base branch\n")
    git(repo_root, "add", ".")
    git(repo_root, "commit", "-m", "seed durable files")

    git(repo_root, "checkout", "-b", "feature")
    write_file(repo_root, "README.md", "feature branch\n")
    git(repo_root, "commit", "-am", "change durable file on feature")
    git(repo_root, "checkout", base_branch)

    write_file(repo_root, ".gsd/state-manifest.json", '{"jobs":[]}\n')
    write_file(repo_root, ".gsd/event-log.jsonl", '{"event":"runtime"}\n')

    audit = run_boundary(repo_root, "audit", "--format", "json")
    assert audit.returncode == 0, audit.stderr
    assert json.loads(audit.stdout)["findings"] == []

    ignored = git(
        repo_root,
        "check-ignore",
        "-v",
        ".gsd/state-manifest.json",
        ".gsd/event-log.jsonl",
    )
    assert ".gitignore" in ignored.stdout
    assert ".gsd/state-manifest.json" in ignored.stdout
    assert ".gsd/event-log.jsonl" in ignored.stdout

    checkout = git(repo_root, "checkout", "feature", check=False)
    assert checkout.returncode == 0, checkout.stderr

    status = git(repo_root, "status", "--short", "--ignored", ".gsd")
    assert "!! .gsd/state-manifest.json" in status.stdout
    assert "!! .gsd/event-log.jsonl" in status.stdout


def test_missing_ignore_rules_and_unknown_boundary_roots_fail_closed(tmp_path: Path):
    repo_root = tmp_path
    init_temp_repo(repo_root)

    write_file(repo_root, ".gsd/state-manifest.json", '{"jobs":[]}\n')

    audit = run_boundary(repo_root, "audit", "--format", "json", "--fail-on-issues")
    assert audit.returncode == 1, audit.stderr
    assert ("unignored-transient", ".gsd/state-manifest.json") in parse_findings(audit)

    classify = run_boundary(repo_root, "classify", "runtime/state-manifest.json", "--format", "json")
    assert classify.returncode == 0, classify.stderr
    payload = json.loads(classify.stdout)
    assert payload[0]["classification"] == "manual-review"
    assert payload[0]["issue_code"] == "unknown-root"
