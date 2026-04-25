"""Focused tests for the runtime-state boundary classifier."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path("tools/runtime_state_boundary.py")


def load_boundary_module():
    module_name = "runtime_state_boundary_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def run_boundary(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def init_temp_repo(repo_root: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo_root, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Runtime Boundary Tests"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "runtime-boundary-tests@example.com"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )


def test_classify_reports_representative_repo_paths():
    result = run_boundary(
        "classify",
        ".gsd/milestones/M014/M014-ROADMAP.md",
        ".gsd/state-manifest.json",
        ".gsd/audit/events.jsonl",
        ".planning/STATE.md",
        ".bg-shell/manifest.json",
        "--format",
        "json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    classes = {row["normalized_path"]: row["classification"] for row in payload}
    assert classes[".gsd/milestones/M014/M014-ROADMAP.md"] == "durable"
    assert classes[".gsd/state-manifest.json"] == "transient"
    assert classes[".gsd/audit/events.jsonl"] == "transient"
    assert classes[".planning/STATE.md"] == "manual-review"
    assert classes[".bg-shell/manifest.json"] == "transient"


def test_classify_accepts_absolute_paths_and_fails_closed_for_unknown_root():
    boundary = load_boundary_module()
    repo_root = Path.cwd().resolve()
    absolute_path = repo_root / ".gsd" / "state-manifest.json"

    absolute = boundary.classify_paths([str(absolute_path)], repo_root)[0]
    unknown = boundary.classify_paths(["README.md"], repo_root)[0]

    assert absolute.normalized_path == ".gsd/state-manifest.json"
    assert absolute.classification == "transient"
    assert unknown.classification == "manual-review"
    assert unknown.issue_code == "unknown-root"


def test_empty_and_outside_repo_paths_raise_clear_errors():
    boundary = load_boundary_module()
    repo_root = Path.cwd().resolve()

    with pytest.raises(boundary.BoundaryPathError, match="must not be empty"):
        boundary.normalize_repo_relative_path("   ", repo_root)

    with pytest.raises(boundary.BoundaryPathError, match="outside repo root"):
        boundary.normalize_repo_relative_path("/tmp/runtime-boundary-outside", repo_root)


def test_conflicting_highest_priority_rules_fail_closed_to_manual_review():
    boundary = load_boundary_module()
    policy = (
        boundary.PolicyRule(
            name="durable-match",
            classification=boundary.CLASS_DURABLE,
            priority=50,
            patterns=(".gsd/conflict.json",),
            rationale="durable match",
        ),
        boundary.PolicyRule(
            name="transient-match",
            classification=boundary.CLASS_TRANSIENT,
            priority=50,
            patterns=(".gsd/conflict.json",),
            rationale="transient match",
        ),
    )

    result = boundary.classify_relative_path(".gsd/conflict.json", policy=policy)

    assert result.classification == boundary.CLASS_MANUAL_REVIEW
    assert result.issue_code == "conflicting-rule-match"
    assert result.matched_rules == ("durable-match", "transient-match")


def test_audit_reports_tracked_transient_unignored_transient_and_manual_review(tmp_path):
    repo_root = tmp_path
    init_temp_repo(repo_root)

    tracked_transient = repo_root / ".gsd" / "audit" / "events.jsonl"
    unignored_transient = repo_root / ".gsd" / "state-manifest.json"
    manual_review = repo_root / ".planning" / "STATE.md"
    tracked_transient.parent.mkdir(parents=True)
    unignored_transient.parent.mkdir(parents=True, exist_ok=True)
    manual_review.parent.mkdir(parents=True)

    tracked_transient.write_text("[]\n", encoding="utf-8")
    unignored_transient.write_text("{}\n", encoding="utf-8")
    manual_review.write_text("legacy\n", encoding="utf-8")

    subprocess.run(
        ["git", "add", str(tracked_transient.relative_to(repo_root)), str(manual_review.relative_to(repo_root))],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )

    result = run_boundary(
        "audit",
        "--repo-root",
        str(repo_root),
        "--format",
        "json",
        "--fail-on-issues",
    )

    assert result.returncode == 1, result.stderr
    payload = json.loads(result.stdout)
    findings = {(row["issue_code"], row["path"]) for row in payload["findings"]}
    assert ("tracked-transient", ".gsd/audit/events.jsonl") in findings
    assert ("unignored-transient", ".gsd/state-manifest.json") in findings
    assert ("manual-review-path", ".planning/STATE.md") in findings


def test_cli_rejects_unsupported_subcommand():
    result = run_boundary("bogus")

    assert result.returncode != 0
    assert "usage:" in result.stderr.lower()
