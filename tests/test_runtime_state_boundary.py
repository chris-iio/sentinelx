"""Focused tests for the runtime-state boundary classifier."""
from __future__ import annotations

import importlib.util
import inspect
import json
import os
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
    # Isolate tests from developer-global hooks (for example identity guards).
    subprocess.run(
        ["git", "config", "core.hooksPath", os.devnull],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )


def test_audit_parser_reuses_static_default_roots(monkeypatch):
    """Default audit roots should reuse the immutable tuple instead of building a list."""
    boundary = load_boundary_module()

    monkeypatch.setattr(sys, "argv", ["runtime_state_boundary.py", "audit"])

    args = boundary.parse_args()

    assert args.paths is boundary.DEFAULT_AUDIT_ROOTS
    assert args.paths == (".gsd", ".planning", ".bg-shell")
    assert "list(DEFAULT_AUDIT_ROOTS)" not in SCRIPT.read_text(encoding="utf-8")


def test_classify_reports_representative_repo_paths():
    result = run_boundary(
        "classify",
        ".gsd/milestones/M014/M014-ROADMAP.md",
        ".gsd/state-manifest.json",
        ".gsd/event-log.jsonl",
        ".gsd/audit/events.jsonl",
        ".gsd/exec/example.stdout",
        ".gsd/graphs/graph.json",
        ".gsd/safety/evidence-M014-S01-T02.json",
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
    assert classes[".gsd/event-log.jsonl"] == "transient"
    assert classes[".gsd/audit/events.jsonl"] == "transient"
    assert classes[".gsd/exec/example.stdout"] == "transient"
    assert classes[".gsd/graphs/graph.json"] == "transient"
    assert classes[".gsd/safety/evidence-M014-S01-T02.json"] == "transient"
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


def test_empty_classify_paths_skips_normalization(monkeypatch):
    boundary = load_boundary_module()

    def fail_normalize(*_args, **_kwargs):
        raise AssertionError("empty classification should not normalize paths")

    monkeypatch.setattr(boundary, "normalize_repo_relative_path", fail_normalize)

    assert boundary.classify_paths((), Path.cwd()) == ()


def test_classify_paths_delegates_result_append(monkeypatch, tmp_path: Path) -> None:
    boundary = load_boundary_module()
    calls: list[tuple[str, str]] = []
    classified = boundary.ClassificationResult(
        input_path="ignored",
        normalized_path=".gsd/state-manifest.json",
        classification=boundary.CLASS_TRANSIENT,
        issue_code=boundary.ISSUE_UNIGNORED_TRANSIENT,
        matched_rules=("gsd-runtime-files",),
        rationale="runtime state",
    )

    monkeypatch.setattr(
        boundary,
        "normalize_repo_relative_path",
        lambda path, _repo_root: f".gsd/{path}",
    )

    def classify(relative_path: str):
        calls.append(("classify", relative_path))
        return classified

    monkeypatch.setattr(boundary, "classify_relative_path", classify)
    source = inspect.getsource(boundary.classify_paths)
    append_source = inspect.getsource(boundary.append_classification_result)

    results = boundary.classify_paths(["state-manifest.json"], tmp_path)

    assert calls == [("classify", ".gsd/state-manifest.json")]
    assert results == (
        boundary.ClassificationResult(
            input_path="state-manifest.json",
            normalized_path=".gsd/state-manifest.json",
            classification=boundary.CLASS_TRANSIENT,
            issue_code=boundary.ISSUE_UNIGNORED_TRANSIENT,
            matched_rules=("gsd-runtime-files",),
            rationale="runtime state",
        ),
    )
    assert "append_classification_result(" in source
    assert "results.append(" not in source
    assert "results.append(" in append_source


def test_classification_result_tuple_helper_skips_iteration_for_short_sequences() -> None:
    boundary = load_boundary_module()
    result = boundary.ClassificationResult(
        input_path=".gsd/state-manifest.json",
        normalized_path=".gsd/state-manifest.json",
        classification=boundary.CLASS_TRANSIENT,
        issue_code=boundary.ISSUE_UNIGNORED_TRANSIENT,
        matched_rules=("gsd-runtime-files",),
        rationale="runtime state",
    )

    class NoIterResults:
        def __init__(self, items):
            self.items = items

        def __len__(self):
            return len(self.items)

        def __getitem__(self, index):
            return self.items[index]

        def __iter__(self):
            raise AssertionError("short classification result tuple conversion should not iterate")

    results = (result, result)

    assert boundary.classification_results_tuple(results) is results
    assert boundary.classification_results_tuple(NoIterResults([])) == ()
    assert boundary.classification_results_tuple(NoIterResults([result])) == (result,)
    assert boundary.classification_results_tuple(NoIterResults([result, result])) == (result, result)
    assert boundary.classification_results_tuple(NoIterResults([result, result, result])) == (
        result,
        result,
        result,
    )
    assert boundary.classification_results_tuple(NoIterResults([result, result, result, result])) == (
        result,
        result,
        result,
        result,
    )
    assert "classification_results_tuple" in boundary.classify_paths.__code__.co_names


def test_empty_and_outside_repo_paths_raise_clear_errors():
    boundary = load_boundary_module()
    repo_root = Path.cwd().resolve()

    class NoStripPath(str):
        def strip(self, *_args, **_kwargs):
            raise AssertionError("path normalization should trim by index")

    with pytest.raises(boundary.BoundaryPathError, match="must not be empty"):
        boundary.normalize_repo_relative_path(NoStripPath("   "), repo_root)

    with pytest.raises(boundary.BoundaryPathError, match="outside repo root"):
        boundary.normalize_repo_relative_path("/tmp/runtime-boundary-outside", repo_root)
    assert "stripped_text_or_none" in boundary.normalize_repo_relative_path.__code__.co_names


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


def test_rule_names_skips_list_for_empty_single_or_pair_rules() -> None:
    boundary = load_boundary_module()
    rule = boundary.PolicyRule(
        name="single",
        classification=boundary.CLASS_DURABLE,
        priority=10,
        patterns=("README.md",),
        rationale="test",
    )

    class NoIterRules:
        def __init__(self, items):
            self.items = items

        def __len__(self):
            return len(self.items)

        def __getitem__(self, index):
            return self.items[index]

        def __iter__(self):
            raise AssertionError("short rule name extraction should not iterate")

    assert boundary.rule_names(()) == ()
    assert boundary.rule_names(NoIterRules([rule])) == ("single",)
    assert boundary.rule_names(NoIterRules([rule, rule])) == ("single", "single")
    assert boundary.rule_names(NoIterRules([rule, rule, rule])) == ("single", "single", "single")
    assert boundary.rule_names(NoIterRules([rule, rule, rule, rule])) == (
        "single",
        "single",
        "single",
        "single",
    )


def test_matched_rule_formatting_skips_join_for_empty_single_or_pair_rules() -> None:
    boundary = load_boundary_module()

    class NoIterRules:
        def __init__(self, items):
            self.items = items

        def __len__(self):
            return len(self.items)

        def __getitem__(self, index):
            return self.items[index]

        def __iter__(self):
            raise AssertionError("short matched-rule formatting should not iterate")

    assert boundary.format_matched_rules(()) == "-"
    assert boundary.format_matched_rules(NoIterRules(["single"])) == "single"
    assert boundary.format_matched_rules(NoIterRules(["first", "second"])) == "first,second"
    assert boundary.format_matched_rules(NoIterRules(["first", "second", "third"])) == (
        "first,second,third"
    )
    assert boundary.format_matched_rules(NoIterRules(["first", "second", "third", "fourth"])) == (
        "first,second,third,fourth"
    )
    assert "_classification_text_line" in boundary.render_classify_text.__code__.co_names
    assert "format_matched_rules" in boundary._classification_text_line.__code__.co_names
    assert "format_matched_rules" in boundary.render_audit_text.__code__.co_names

    source = SCRIPT.read_text(encoding="utf-8")
    classify_source = source[source.index("def render_classify_text") : source.index("def render_audit_text")]
    audit_source = source[source.index("def render_audit_text") : source.index("def classification_to_dict")]
    assert "\",\".join" not in classify_source
    assert "\",\".join" not in audit_source


def test_classify_text_rendering_skips_iteration_for_empty_single_or_pair_results() -> None:
    boundary = load_boundary_module()
    result = boundary.ClassificationResult(
        input_path=".gsd/state.json",
        normalized_path=".gsd/state.json",
        classification=boundary.CLASS_TRANSIENT,
        issue_code=boundary.ISSUE_UNIGNORED_TRANSIENT,
        matched_rules=("gsd-runtime-files",),
        rationale="runtime state",
    )
    second = boundary.ClassificationResult(
        input_path=".planning/notes.md",
        normalized_path=".planning/notes.md",
        classification=boundary.CLASS_MANUAL_REVIEW,
        issue_code=boundary.ISSUE_MANUAL_REVIEW,
        matched_rules=("planning-legacy",),
        rationale="manual review",
    )
    third = boundary.ClassificationResult(
        input_path="README.md",
        normalized_path="README.md",
        classification=boundary.CLASS_DURABLE,
        issue_code=None,
        matched_rules=("durable-source",),
        rationale="durable source",
    )
    fourth = boundary.ClassificationResult(
        input_path=".codex/session.json",
        normalized_path=".codex/session.json",
        classification=boundary.CLASS_MANUAL_REVIEW,
        issue_code=boundary.ISSUE_MANUAL_REVIEW,
        matched_rules=("codex-runtime",),
        rationale="manual review",
    )

    class NoIterResults:
        def __init__(self, items):
            self.items = items

        def __len__(self):
            return len(self.items)

        def __getitem__(self, index):
            return self.items[index]

        def __iter__(self):
            raise AssertionError("short classify text rendering should not iterate")

    assert boundary.render_classify_text(NoIterResults([])) == ""
    assert boundary.render_classify_text(NoIterResults([result])) == (
        "transient\t.gsd/state.json\tissue=unignored-transient\trules=gsd-runtime-files"
    )
    assert boundary.render_classify_text(NoIterResults([result, second])) == (
        "transient\t.gsd/state.json\tissue=unignored-transient\trules=gsd-runtime-files\n"
        "manual-review\t.planning/notes.md\tissue=manual-review-path\trules=planning-legacy"
    )
    assert boundary.render_classify_text(NoIterResults([result, second, third])) == (
        "transient\t.gsd/state.json\tissue=unignored-transient\trules=gsd-runtime-files\n"
        "manual-review\t.planning/notes.md\tissue=manual-review-path\trules=planning-legacy\n"
        "durable\tREADME.md\tissue=-\trules=durable-source"
    )
    assert boundary.render_classify_text(NoIterResults([result, second, third, fourth])) == (
        "transient\t.gsd/state.json\tissue=unignored-transient\trules=gsd-runtime-files\n"
        "manual-review\t.planning/notes.md\tissue=manual-review-path\trules=planning-legacy\n"
        "durable\tREADME.md\tissue=-\trules=durable-source\n"
        "manual-review\t.codex/session.json\tissue=manual-review-path\trules=codex-runtime"
    )
    assert "result_count == 4" in inspect.getsource(boundary.render_classify_text)
    assert "_classification_text_line" in boundary.render_classify_text.__code__.co_names


def test_repo_path_root_scans_without_split_list() -> None:
    """Boundary root checks should avoid allocating split path parts."""
    boundary = load_boundary_module()

    class NoSplitPath(str):
        def split(self, *_args, **_kwargs):
            raise AssertionError("repo path root extraction should scan directly")

    assert boundary.repo_path_root(NoSplitPath(".gsd/runtime/state.json")) == ".gsd"
    assert boundary.repo_path_root(NoSplitPath("README.md")) == "README.md"
    assert "repo_path_root" in boundary.classify_relative_path.__code__.co_names
    assert "split" not in boundary.repo_path_root.__code__.co_names


def test_highest_priority_rule_selection_uses_direct_scan(monkeypatch):
    """Policy selection should avoid generator and comprehension scans."""
    boundary = load_boundary_module()
    policy = (
        boundary.PolicyRule(
            name="lower-match",
            classification=boundary.CLASS_TRANSIENT,
            priority=10,
            patterns=(".gsd/runtime/state.json",),
            rationale="lower priority",
        ),
        boundary.PolicyRule(
            name="highest-a",
            classification=boundary.CLASS_DURABLE,
            priority=50,
            patterns=(".gsd/runtime/state.json",),
            rationale="highest priority",
        ),
        boundary.PolicyRule(
            name="highest-b",
            classification=boundary.CLASS_DURABLE,
            priority=50,
            patterns=(".gsd/runtime/state.json",),
            rationale="also highest priority",
        ),
    )

    def fail_max(*_args, **_kwargs):
        raise AssertionError("highest-priority selection should scan directly")

    def fail_set(*_args, **_kwargs):
        raise AssertionError("highest-priority selection should not allocate a class set")

    def fail_any(*_args, **_kwargs):
        raise AssertionError("rule matching should scan patterns directly")

    monkeypatch.setattr("builtins.max", fail_max)
    monkeypatch.setattr("builtins.set", fail_set)
    monkeypatch.setattr("builtins.any", fail_any)

    result = boundary.classify_relative_path(".gsd/runtime/state.json", policy=policy)

    assert result.classification == boundary.CLASS_DURABLE
    assert result.matched_rules == ("highest-a", "highest-b")
    assert boundary.highest_priority_matches(()) == ()
    assert boundary.highest_priority_matches((policy[0],)) == (policy[0],)
    assert boundary.highest_priority_matches(policy) == policy[1:]
    assert "policy_rules_tuple" in boundary.highest_priority_matches.__code__.co_names
    assert boundary.rule_matches_path(".gsd/runtime/state.json", policy[0]) is True
    assert boundary.rule_names(policy[1:]) == ("highest-a", "highest-b")
    classify_source = SCRIPT.read_text(encoding="utf-8")
    classify_source = classify_source[
        classify_source.index("def classify_relative_path") : classify_source.index("def rule_names")
    ]
    assert "\n    matches: list[PolicyRule]" not in classify_source
    assert "highest_priority_matches(matches)" not in classify_source
    assert "<listcomp>" not in {
        const.co_name
        for const in boundary.highest_priority_matches.__code__.co_consts
        if hasattr(const, "co_name")
    }
    assert "<listcomp>" not in {
        const.co_name
        for const in boundary.classify_relative_path.__code__.co_consts
        if hasattr(const, "co_name")
    }
    assert "<genexpr>" not in {
        const.co_name
        for const in boundary.rule_matches_path.__code__.co_consts
        if hasattr(const, "co_name")
    }
    assert "<genexpr>" not in {
        const.co_name
        for const in boundary.rule_names.__code__.co_consts
        if hasattr(const, "co_name")
    }
    assert "<setcomp>" not in {
        const.co_name
        for const in boundary.classify_relative_path.__code__.co_consts
        if hasattr(const, "co_name")
    }


def test_policy_rules_tuple_helper_skips_iteration_for_short_sequences() -> None:
    boundary = load_boundary_module()
    rule = boundary.PolicyRule(
        name="single",
        classification=boundary.CLASS_DURABLE,
        priority=10,
        patterns=("README.md",),
        rationale="test",
    )

    class NoIterRules:
        def __init__(self, items):
            self.items = items

        def __len__(self):
            return len(self.items)

        def __getitem__(self, index):
            return self.items[index]

        def __iter__(self):
            raise AssertionError("short policy rule tuple conversion should not iterate")

    rules = (rule, rule)

    assert boundary.policy_rules_tuple(rules) is rules
    assert boundary.policy_rules_tuple(NoIterRules([])) == ()
    assert boundary.policy_rules_tuple(NoIterRules([rule])) == (rule,)
    assert boundary.policy_rules_tuple(NoIterRules([rule, rule])) == (rule, rule)
    assert boundary.policy_rules_tuple(NoIterRules([rule, rule, rule])) == (rule, rule, rule)
    assert boundary.policy_rules_tuple(NoIterRules([rule, rule, rule, rule])) == (
        rule,
        rule,
        rule,
        rule,
    )


def test_format_command_args_shell_quotes_display_values():
    boundary = load_boundary_module()

    assert (
        boundary.format_command_args(("rm", "--cached", "--", ".gsd/a path.json"))
        == "rm --cached -- '.gsd/a path.json'"
    )
    assert "tuple(args)" not in SCRIPT.read_text(encoding="utf-8")


def test_first_non_empty_output_decodes_and_strips_streams():
    boundary = load_boundary_module()

    class NoStripText(str):
        def strip(self, *_args, **_kwargs):
            raise AssertionError("boundary output trimming should scan by index")

    assert boundary.first_non_empty_output(NoStripText("   "), b"  bad utf8: \xff  ") == "bad utf8: �"
    assert boundary.first_non_empty_output(None, NoStripText(""), b"  ") is None
    assert boundary.stripped_text_or_none(NoStripText("  git failed  ")) == "git failed"
    assert "stripped_text_or_none" in boundary.first_non_empty_output.__code__.co_names
    assert "strip" not in boundary.stripped_text_or_none.__code__.co_names


def test_nul_delimited_path_parser_accumulates_directly():
    """Git NUL-delimited path parsing should avoid split-list and set-comprehension frames."""
    boundary = load_boundary_module()

    parsed = boundary.parse_nul_delimited_paths(
        b".gsd/state-manifest.json\0\0.planning/STATE.md\0"
    )

    assert parsed == {".gsd/state-manifest.json", ".planning/STATE.md"}
    assert ".split(" not in inspect.getsource(boundary.parse_nul_delimited_paths)
    assert "<setcomp>" not in {
        const.co_name
        for const in boundary.parse_nul_delimited_paths.__code__.co_consts
        if hasattr(const, "co_name")
    }


def test_format_json_payload_uses_repo_tooling_pretty_json():
    boundary = load_boundary_module()

    assert boundary.format_json_payload({"b": 1, "a": 2}, sort_keys=True) == '{\n  "a": 2,\n  "b": 1\n}'


def test_boundary_json_serialization_uses_direct_accumulation():
    """Boundary JSON helpers should avoid comprehension frames and recursive asdict walks."""
    boundary = load_boundary_module()
    result = boundary.ClassificationResult(
        input_path=".gsd/state-manifest.json",
        normalized_path=".gsd/state-manifest.json",
        classification=boundary.CLASS_TRANSIENT,
        issue_code=boundary.ISSUE_UNIGNORED_TRANSIENT,
        matched_rules=("gsd-runtime-files",),
        rationale="runtime state",
    )
    finding = boundary.AuditFinding(
        path=".gsd/state-manifest.json",
        classification=boundary.CLASS_TRANSIENT,
        issue_code=boundary.ISSUE_UNIGNORED_TRANSIENT,
        matched_rules=("gsd-runtime-files",),
        rationale="runtime state",
        tracked=False,
        ignored=False,
    )
    report = boundary.AuditReport(
        repo_root="/tmp/repo",
        scanned_paths=1,
        findings=(finding,),
    )
    class NoIterSequence:
        def __init__(self, items):
            self.items = items

        def __len__(self):
            return len(self.items)

        def __getitem__(self, index):
            return self.items[index]

        def __iter__(self):
            raise AssertionError("short boundary JSON serialization should not iterate")

    assert boundary.classifications_to_dicts(NoIterSequence([result])) == [
        boundary.classification_to_dict(result)
    ]
    assert boundary.classifications_to_dicts(()) == []
    assert boundary.classifications_to_dicts(NoIterSequence([result, result])) == [
        boundary.classification_to_dict(result),
        boundary.classification_to_dict(result),
    ]
    assert boundary.classifications_to_dicts(NoIterSequence([result, result, result])) == [
        boundary.classification_to_dict(result),
        boundary.classification_to_dict(result),
        boundary.classification_to_dict(result),
    ]
    assert boundary.classifications_to_dicts(NoIterSequence([result, result, result, result])) == [
        boundary.classification_to_dict(result),
        boundary.classification_to_dict(result),
        boundary.classification_to_dict(result),
        boundary.classification_to_dict(result),
    ]
    assert boundary.audit_report_to_dict(report)["findings"] == [
        boundary.audit_finding_to_dict(finding)
    ]
    assert boundary.audit_findings_to_dicts(()) == []
    assert boundary.audit_findings_to_dicts(NoIterSequence([finding, finding])) == [
        boundary.audit_finding_to_dict(finding),
        boundary.audit_finding_to_dict(finding),
    ]
    assert boundary.audit_findings_to_dicts(NoIterSequence([finding, finding, finding])) == [
        boundary.audit_finding_to_dict(finding),
        boundary.audit_finding_to_dict(finding),
        boundary.audit_finding_to_dict(finding),
    ]
    assert boundary.audit_findings_to_dicts(NoIterSequence([finding, finding, finding, finding])) == [
        boundary.audit_finding_to_dict(finding),
        boundary.audit_finding_to_dict(finding),
        boundary.audit_finding_to_dict(finding),
        boundary.audit_finding_to_dict(finding),
    ]
    assert "asdict" not in boundary.classification_to_dict.__code__.co_names
    assert "asdict" not in boundary.audit_finding_to_dict.__code__.co_names
    assert "asdict" not in SCRIPT.read_text(encoding="utf-8")
    assert "<listcomp>" not in {
        const.co_name
        for const in boundary.classifications_to_dicts.__code__.co_consts
        if hasattr(const, "co_name")
    }
    assert "<listcomp>" not in {
        const.co_name
        for const in boundary.audit_findings_to_dicts.__code__.co_consts
        if hasattr(const, "co_name")
    }
    assert "audit_findings_to_dicts" in boundary.audit_report_to_dict.__code__.co_names
    assert "len" in boundary.classifications_to_dicts.__code__.co_names
    assert "len" in boundary.audit_findings_to_dicts.__code__.co_names
    assert "append_classification_dict" in boundary.classifications_to_dicts.__code__.co_names
    assert "append_audit_finding_dict" in boundary.audit_findings_to_dicts.__code__.co_names


def test_boundary_json_append_helpers_own_long_path_mutation() -> None:
    boundary = load_boundary_module()
    result = boundary.ClassificationResult(
        input_path=".gsd/state-manifest.json",
        normalized_path=".gsd/state-manifest.json",
        classification=boundary.CLASS_TRANSIENT,
        issue_code=boundary.ISSUE_UNIGNORED_TRANSIENT,
        matched_rules=("gsd-runtime-files",),
        rationale="runtime state",
    )
    finding = boundary.AuditFinding(
        path=".gsd/state-manifest.json",
        classification=boundary.CLASS_TRANSIENT,
        issue_code=boundary.ISSUE_UNIGNORED_TRANSIENT,
        matched_rules=("gsd-runtime-files",),
        rationale="runtime state",
        tracked=False,
        ignored=False,
    )

    serialized_classifications: list[dict[str, object]] = []
    serialized_findings: list[dict[str, object]] = []
    boundary.append_classification_dict(serialized_classifications, result)
    boundary.append_audit_finding_dict(serialized_findings, finding)
    classifications_source = inspect.getsource(boundary.classifications_to_dicts)
    findings_source = inspect.getsource(boundary.audit_findings_to_dicts)

    assert serialized_classifications == [boundary.classification_to_dict(result)]
    assert serialized_findings == [boundary.audit_finding_to_dict(finding)]
    assert "append_classification_dict(serialized, result)" in classifications_source
    assert "serialized.append(classification_to_dict(result))" not in classifications_source
    assert "append_audit_finding_dict(serialized, finding)" in findings_source
    assert "serialized.append(audit_finding_to_dict(finding))" not in findings_source


def test_boundary_records_use_slots_to_avoid_instance_dict() -> None:
    boundary = load_boundary_module()
    rule = boundary.PolicyRule(
        name="single",
        classification=boundary.CLASS_DURABLE,
        priority=10,
        patterns=("README.md",),
        rationale="test",
    )
    result = boundary.ClassificationResult(
        input_path=".gsd/state-manifest.json",
        normalized_path=".gsd/state-manifest.json",
        classification=boundary.CLASS_TRANSIENT,
        issue_code=boundary.ISSUE_UNIGNORED_TRANSIENT,
        matched_rules=("gsd-runtime-files",),
        rationale="runtime state",
    )
    finding = boundary.AuditFinding(
        path=".gsd/state-manifest.json",
        classification=boundary.CLASS_TRANSIENT,
        issue_code=boundary.ISSUE_UNIGNORED_TRANSIENT,
        matched_rules=("gsd-runtime-files",),
        rationale="runtime state",
        tracked=False,
        ignored=False,
    )
    report = boundary.AuditReport(
        repo_root="/tmp/repo",
        scanned_paths=1,
        findings=(finding,),
    )

    assert not hasattr(rule, "__dict__")
    assert not hasattr(result, "__dict__")
    assert not hasattr(finding, "__dict__")
    assert not hasattr(report, "__dict__")


def test_audit_reports_tracked_transient_unignored_transient_and_manual_review(tmp_path):
    repo_root = tmp_path
    init_temp_repo(repo_root)

    tracked_transient = repo_root / ".gsd" / "audit" / "events.jsonl"
    unignored_transient = repo_root / ".gsd" / "state-manifest.json"
    ignored_transient = repo_root / ".gsd" / "notifications.jsonl"
    manual_review = repo_root / ".planning" / "STATE.md"
    tracked_transient.parent.mkdir(parents=True)
    unignored_transient.parent.mkdir(parents=True, exist_ok=True)
    manual_review.parent.mkdir(parents=True)

    tracked_transient.write_text("[]\n", encoding="utf-8")
    unignored_transient.write_text("{}\n", encoding="utf-8")
    ignored_transient.write_text("[]\n", encoding="utf-8")
    manual_review.write_text("legacy\n", encoding="utf-8")
    (repo_root / ".gitignore").write_text(".gsd/notifications.jsonl\n", encoding="utf-8")

    subprocess.run(
        [
            "git",
            "add",
            str(tracked_transient.relative_to(repo_root)),
            str(manual_review.relative_to(repo_root)),
            ".gitignore",
        ],
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
    findings = {(row["issue_code"], row["path"]) for row in json.loads(result.stdout)["findings"]}
    assert ("tracked-transient", ".gsd/audit/events.jsonl") in findings
    assert ("unignored-transient", ".gsd/state-manifest.json") in findings
    assert ("manual-review-path", ".planning/STATE.md") in findings
    assert ("unignored-transient", ".gsd/notifications.jsonl") not in findings
    assert ("tracked-transient", ".gsd/notifications.jsonl") not in findings


def test_audit_can_fail_only_on_selected_issue_codes(tmp_path):
    repo_root = tmp_path
    init_temp_repo(repo_root)

    manual_review = repo_root / ".planning" / "STATE.md"
    manual_review.parent.mkdir(parents=True)
    manual_review.write_text("legacy\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", str(manual_review.relative_to(repo_root))],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )

    manual_only = run_boundary(
        "audit",
        "--repo-root",
        str(repo_root),
        "--format",
        "json",
        "--fail-on-codes",
        "tracked-transient",
        "unignored-transient",
    )

    assert manual_only.returncode == 0, manual_only.stderr
    assert ("manual-review-path", ".planning/STATE.md") in {
        (row["issue_code"], row["path"]) for row in json.loads(manual_only.stdout)["findings"]
    }

    unignored_transient = repo_root / ".gsd" / "state-manifest.json"
    unignored_transient.parent.mkdir(parents=True, exist_ok=True)
    unignored_transient.write_text("{}\n", encoding="utf-8")

    blocker = run_boundary(
        "audit",
        "--repo-root",
        str(repo_root),
        "--format",
        "json",
        "--fail-on-codes",
        "tracked-transient",
        "unignored-transient",
    )

    assert blocker.returncode == 1, blocker.stderr
    findings = {(row["issue_code"], row["path"]) for row in json.loads(blocker.stdout)["findings"]}
    assert ("unignored-transient", ".gsd/state-manifest.json") in findings
    assert ("manual-review-path", ".planning/STATE.md") in findings


def test_report_issue_code_selection_scans_directly(monkeypatch):
    """Fail-on-code selection should avoid set materialization and generator frames."""
    boundary = load_boundary_module()
    report = boundary.AuditReport(
        repo_root="/tmp/repo",
        scanned_paths=2,
        findings=(
            boundary.AuditFinding(
                path=".planning/STATE.md",
                classification=boundary.CLASS_MANUAL_REVIEW,
                issue_code=boundary.ISSUE_MANUAL_REVIEW,
                matched_rules=("planning-legacy",),
                rationale="manual review",
            ),
            boundary.AuditFinding(
                path=".gsd/state-manifest.json",
                classification=boundary.CLASS_TRANSIENT,
                issue_code=boundary.ISSUE_UNIGNORED_TRANSIENT,
                matched_rules=("gsd-runtime-files",),
                rationale="unignored transient",
            ),
        ),
    )

    def fail_set(*_args, **_kwargs):
        raise AssertionError("fail-on-code selection should not materialize selected-code sets")

    monkeypatch.setattr("builtins.set", fail_set)

    assert boundary.report_has_issue_codes(report, (boundary.ISSUE_UNIGNORED_TRANSIENT,)) is True
    assert boundary.report_has_issue_codes(report, (boundary.ISSUE_TRACKED_TRANSIENT,)) is False
    assert "<genexpr>" not in {
        const.co_name
        for const in boundary.report_has_issue_codes.__code__.co_consts
        if hasattr(const, "co_name")
    }


def test_audit_text_renders_issue_counts_without_sorting(monkeypatch):
    """Audit text count rendering should use the canonical issue-code order."""
    boundary = load_boundary_module()
    report = boundary.AuditReport(
        repo_root="/tmp/repo",
        scanned_paths=2,
        findings=(
            boundary.AuditFinding(
                path=".planning/STATE.md",
                classification=boundary.CLASS_MANUAL_REVIEW,
                issue_code=boundary.ISSUE_MANUAL_REVIEW,
                matched_rules=("planning-legacy",),
                rationale="manual review",
            ),
            boundary.AuditFinding(
                path=".gsd/state-manifest.json",
                classification=boundary.CLASS_TRANSIENT,
                issue_code=boundary.ISSUE_UNIGNORED_TRANSIENT,
                matched_rules=("gsd-runtime-files",),
                rationale="unignored transient",
            ),
        ),
    )

    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("audit text issue counts should not sort per render")

    monkeypatch.setattr("builtins.sorted", fail_sorted)

    text = boundary.render_audit_text(report)

    assert text.index("- unignored-transient: 1") < text.index("- manual-review-path: 1")
    assert "- tracked-transient:" not in text
    assert "append_issue_count_lines" in boundary.render_audit_text.__code__.co_names
    assert "ALL_ISSUE_CODES" not in boundary.render_audit_text.__code__.co_names
    issue_count_source = inspect.getsource(boundary.append_issue_count_lines)
    assert "for issue_code in ALL_ISSUE_CODES" not in issue_count_source
    assert "ISSUE_UNIGNORED_TRANSIENT" in issue_count_source
    assert "ISSUE_UNKNOWN_ROOT" in issue_count_source


def test_audit_candidate_discovery_skips_sort_for_zero_one_two_or_three_paths(monkeypatch, tmp_path):
    """Targeted boundary audits should not sort candidate sets."""
    boundary = load_boundary_module()
    repo_root = tmp_path
    single = repo_root / ".gsd" / "state-manifest.json"
    second = repo_root / ".gsd" / "runtime" / "state.json"
    third = repo_root / ".bg-shell" / "manifest.json"
    fourth = repo_root / ".planning" / "notes.md"
    single.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    third.parent.mkdir(parents=True)
    fourth.parent.mkdir(parents=True)
    single.write_text("{}\n", encoding="utf-8")
    second.write_text("{}\n", encoding="utf-8")
    third.write_text("{}\n", encoding="utf-8")
    fourth.write_text("notes\n", encoding="utf-8")

    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("small audit candidate discovery should not sort")

    monkeypatch.setattr("builtins.sorted", fail_sorted)

    assert boundary.iter_audit_candidate_paths((), repo_root) == ()
    assert boundary.iter_audit_candidate_paths((".gsd/missing.json",), repo_root) == ()
    assert boundary.iter_audit_candidate_paths((".gsd/state-manifest.json",), repo_root) == (
        ".gsd/state-manifest.json",
    )
    assert boundary.iter_audit_candidate_paths((".gsd/state-manifest.json", ".gsd/runtime/state.json"), repo_root) == (
        ".gsd/runtime/state.json",
        ".gsd/state-manifest.json",
    )
    assert boundary.iter_audit_candidate_paths(
        (".gsd/state-manifest.json", ".gsd/runtime/state.json", ".bg-shell/manifest.json"),
        repo_root,
    ) == (
        ".bg-shell/manifest.json",
        ".gsd/runtime/state.json",
        ".gsd/state-manifest.json",
    )
    assert boundary.iter_audit_candidate_paths(
        (
            ".gsd/state-manifest.json",
            ".gsd/runtime/state.json",
            ".bg-shell/manifest.json",
            ".planning/notes.md",
        ),
        repo_root,
    ) == (
        ".bg-shell/manifest.json",
        ".gsd/runtime/state.json",
        ".gsd/state-manifest.json",
        ".planning/notes.md",
    )
    assert boundary.ordered_discovered_paths(
        {".gsd/state-manifest.json", ".gsd/runtime/state.json"},
        ".gsd/state-manifest.json",
    ) == (
        ".gsd/runtime/state.json",
        ".gsd/state-manifest.json",
    )
    assert boundary.ordered_discovered_paths(
        {".gsd/state-manifest.json", ".gsd/runtime/state.json", ".bg-shell/manifest.json"},
        ".gsd/state-manifest.json",
    ) == (
        ".bg-shell/manifest.json",
        ".gsd/runtime/state.json",
        ".gsd/state-manifest.json",
    )
    assert boundary.ordered_discovered_paths(
        {
            ".gsd/state-manifest.json",
            ".gsd/runtime/state.json",
            ".bg-shell/manifest.json",
            ".planning/notes.md",
        },
        ".gsd/state-manifest.json",
    ) == (
        ".bg-shell/manifest.json",
        ".gsd/runtime/state.json",
        ".gsd/state-manifest.json",
        ".planning/notes.md",
    )
    ordered_paths: list[str] = []
    boundary.append_ordered_path(ordered_paths, ".gsd/state-manifest.json")
    boundary.append_ordered_path(ordered_paths, ".bg-shell/manifest.json")
    boundary.append_ordered_path(ordered_paths, ".planning/notes.md")
    boundary.append_ordered_path(ordered_paths, ".gsd/runtime/state.json")
    assert ordered_paths == [
        ".bg-shell/manifest.json",
        ".gsd/runtime/state.json",
        ".gsd/state-manifest.json",
        ".planning/notes.md",
    ]
    source = SCRIPT.read_text(encoding="utf-8")
    helper_source = source[
        source.index("def iter_audit_candidate_paths") : source.index("def run_git_command")
    ]
    assert "next(iter(discovered))" not in helper_source
    assert "sorted(" not in helper_source
    assert "path_count == 4" in inspect.getsource(boundary.ordered_discovered_paths)
    assert "append_ordered_path" in boundary.ordered_discovered_paths.__code__.co_names
    assert "ordered_discovered_paths" in boundary.iter_audit_candidate_paths.__code__.co_names


def test_empty_audit_candidate_discovery_skips_normalization_and_set(monkeypatch, tmp_path):
    """Empty targeted audits should return before path normalization or set allocation."""
    boundary = load_boundary_module()

    def fail_normalize(*_args, **_kwargs):
        raise AssertionError("empty audit candidate discovery should not normalize paths")

    def fail_set(*_args, **_kwargs):
        raise AssertionError("empty audit candidate discovery should not allocate a discovery set")

    monkeypatch.setattr(boundary, "normalize_repo_relative_path", fail_normalize)
    monkeypatch.setattr("builtins.set", fail_set)

    assert boundary.iter_audit_candidate_paths((), tmp_path) == ()


def test_audit_paths_skips_finding_sort_for_zero_one_two_three_or_four_findings(monkeypatch, tmp_path):
    """Targeted boundary audits should not sort finding collections."""
    boundary = load_boundary_module()
    repo_root = tmp_path
    single = repo_root / ".gsd" / "state-manifest.json"
    manual = repo_root / ".planning" / "notes.md"
    bg_shell = repo_root / ".bg-shell" / "manifest.json"
    second_runtime = repo_root / ".gsd" / "runtime" / "state.json"
    single.parent.mkdir(parents=True)
    manual.parent.mkdir(parents=True)
    bg_shell.parent.mkdir(parents=True)
    second_runtime.parent.mkdir(parents=True)
    single.write_text("{}\n", encoding="utf-8")
    manual.write_text("notes\n", encoding="utf-8")
    bg_shell.write_text("{}\n", encoding="utf-8")
    second_runtime.write_text("{}\n", encoding="utf-8")

    def fail_sorted(*_args, **_kwargs):
        raise AssertionError("small audit finding sets should not sort")

    monkeypatch.setattr("builtins.sorted", fail_sorted)
    monkeypatch.setattr(boundary, "git_tracked_paths", lambda _repo_root, _paths: set())
    monkeypatch.setattr(boundary, "git_ignored_paths", lambda _repo_root, _paths: set())

    empty_report = boundary.audit_paths((".gsd/missing.json",), repo_root)
    single_report = boundary.audit_paths((".gsd/state-manifest.json",), repo_root)
    pair_report = boundary.audit_paths((".gsd/state-manifest.json", ".planning/notes.md"), repo_root)
    triple_report = boundary.audit_paths(
        (".gsd/state-manifest.json", ".planning/notes.md", ".bg-shell/manifest.json"),
        repo_root,
    )
    quad_report = boundary.audit_paths(
        (
            ".gsd/state-manifest.json",
            ".planning/notes.md",
            ".bg-shell/manifest.json",
            ".gsd/runtime/state.json",
        ),
        repo_root,
    )

    assert empty_report.findings == ()
    assert len(single_report.findings) == 1
    assert single_report.findings[0].issue_code == boundary.ISSUE_UNIGNORED_TRANSIENT
    assert [finding.issue_code for finding in pair_report.findings] == [
        boundary.ISSUE_MANUAL_REVIEW,
        boundary.ISSUE_UNIGNORED_TRANSIENT,
    ]
    assert [(finding.issue_code, finding.path) for finding in triple_report.findings] == [
        (boundary.ISSUE_MANUAL_REVIEW, ".planning/notes.md"),
        (boundary.ISSUE_UNIGNORED_TRANSIENT, ".bg-shell/manifest.json"),
        (boundary.ISSUE_UNIGNORED_TRANSIENT, ".gsd/state-manifest.json"),
    ]
    assert [(finding.issue_code, finding.path) for finding in quad_report.findings] == [
        (boundary.ISSUE_MANUAL_REVIEW, ".planning/notes.md"),
        (boundary.ISSUE_UNIGNORED_TRANSIENT, ".bg-shell/manifest.json"),
        (boundary.ISSUE_UNIGNORED_TRANSIENT, ".gsd/runtime/state.json"),
        (boundary.ISSUE_UNIGNORED_TRANSIENT, ".gsd/state-manifest.json"),
    ]
    ordered_findings = []
    boundary.append_ordered_audit_finding(ordered_findings, quad_report.findings[3])
    boundary.append_ordered_audit_finding(ordered_findings, quad_report.findings[0])
    boundary.append_ordered_audit_finding(ordered_findings, quad_report.findings[2])
    boundary.append_ordered_audit_finding(ordered_findings, quad_report.findings[1])
    assert ordered_findings == list(quad_report.findings)
    assert "append_ordered_audit_finding" in boundary.ordered_audit_findings.__code__.co_names
    assert "ordered_audit_findings" in boundary.audit_paths.__code__.co_names


def test_ordered_audit_findings_skips_iteration_for_four_findings() -> None:
    boundary = load_boundary_module()

    manual = boundary.AuditFinding(
        path=".planning/notes.md",
        classification=boundary.CLASS_MANUAL_REVIEW,
        issue_code=boundary.ISSUE_MANUAL_REVIEW,
        matched_rules=("planning-legacy",),
        rationale="manual review",
    )
    gsd = boundary.AuditFinding(
        path=".gsd/state-manifest.json",
        classification=boundary.CLASS_TRANSIENT,
        issue_code=boundary.ISSUE_UNIGNORED_TRANSIENT,
        matched_rules=("gsd-runtime-files",),
        rationale="unignored transient",
    )
    bg_shell = boundary.AuditFinding(
        path=".bg-shell/manifest.json",
        classification=boundary.CLASS_TRANSIENT,
        issue_code=boundary.ISSUE_UNIGNORED_TRANSIENT,
        matched_rules=("bg-shell-runtime",),
        rationale="unignored transient",
    )
    runtime = boundary.AuditFinding(
        path=".gsd/runtime/state.json",
        classification=boundary.CLASS_TRANSIENT,
        issue_code=boundary.ISSUE_UNIGNORED_TRANSIENT,
        matched_rules=("gsd-runtime-files",),
        rationale="unignored transient",
    )

    class NoIterFindings(list):
        def __iter__(self):
            raise AssertionError("four audit findings should not iterate")

    ordered = boundary.ordered_audit_findings(NoIterFindings([gsd, manual, runtime, bg_shell]))

    assert ordered == (manual, bg_shell, runtime, gsd)
    assert "finding_count == 4" in inspect.getsource(boundary.ordered_audit_findings)


def test_empty_git_path_sets_reuse_shared_empty_without_set_allocation(monkeypatch, tmp_path):
    """Empty git/path parsing paths should not allocate throwaway mutable sets."""
    boundary = load_boundary_module()

    def fail_set(*_args, **_kwargs):
        raise AssertionError("empty path helpers should reuse EMPTY_PATH_SET")

    def fail_git(*_args, **_kwargs):
        raise AssertionError("empty path helpers should not invoke git")

    monkeypatch.setattr("builtins.set", fail_set)
    monkeypatch.setattr(boundary, "run_git_command", fail_git)

    assert boundary.parse_nul_delimited_paths(b"") is boundary.EMPTY_PATH_SET
    assert boundary.git_tracked_paths(tmp_path, ()) is boundary.EMPTY_PATH_SET
    assert boundary.git_ignored_paths(tmp_path, ()) is boundary.EMPTY_PATH_SET

    source = SCRIPT.read_text(encoding="utf-8")
    parser_source = source[source.index("def parse_nul_delimited_paths") : source.index("def git_tracked_paths")]
    git_tracked_source = source[source.index("def git_tracked_paths") : source.index("def git_ignored_paths")]
    git_ignored_source = source[source.index("def git_ignored_paths") : source.index("def audit_paths")]
    assert "blob_length = len(blob)" in parser_source
    assert "while start < len(blob)" not in parser_source
    assert "return set()" not in git_tracked_source
    assert "return set()" not in git_ignored_source


def test_git_inspection_return_codes_use_shared_static_membership(monkeypatch, tmp_path):
    """Git inspection should accept diff-style 0/1 exits without inline tuple checks."""
    boundary = load_boundary_module()
    calls: list[tuple[str, ...]] = []

    def fake_run(args, **_kwargs):  # noqa: ANN001
        calls.append(tuple(args))
        return subprocess.CompletedProcess(args=args, returncode=1, stdout=b"changed\0", stderr=b"")

    monkeypatch.setattr(boundary.shutil, "which", lambda tool: f"/usr/bin/{tool}")
    monkeypatch.setattr(boundary.subprocess, "run", fake_run)

    assert boundary.GIT_INSPECTION_OK_RETURN_CODES == frozenset((0, 1))
    assert boundary.run_git_command(tmp_path, ["diff", "--name-only"]) == b"changed\0"
    assert calls == [("/usr/bin/git", "diff", "--name-only")]

    source = SCRIPT.read_text(encoding="utf-8")
    helper_source = source[
        source.index("def run_git_command") : source.index("def parse_nul_delimited_paths")
    ]
    assert "GIT_INSPECTION_OK_RETURN_CODES" in boundary.run_git_command.__code__.co_names
    assert "not in (0, 1)" not in helper_source


def test_cli_rejects_unsupported_subcommand():
    result = run_boundary("bogus")

    assert result.returncode != 0
    assert "usage:" in result.stderr.lower()
