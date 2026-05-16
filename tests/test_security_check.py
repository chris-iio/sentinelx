"""Focused tests for the SentinelX security scanner helpers."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import MappingProxyType, SimpleNamespace

SCRIPT = Path("tools/security_check.py")


def load_security_check_module():
    module_name = "security_check_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_bandit_count_helper_avoids_sum_generator(monkeypatch):
    """Bandit HIGH/MEDIUM counting should use a direct scan."""
    security_check = load_security_check_module()

    def fail_sum(*_args, **_kwargs):
        raise AssertionError("Bandit severity counting should not use sum()")

    monkeypatch.setattr("builtins.sum", fail_sum)

    assert security_check.count_bandit_high_medium([
        {"issue_severity": "HIGH"},
        {"issue_severity": "medium"},
        {"issue_severity": "LOW"},
        {"issue_severity": ""},
    ]) == 2
    assert security_check.BANDIT_FAIL_SEVERITIES == frozenset(("HIGH", "MEDIUM"))
    assert "BANDIT_FAIL_SEVERITIES" in security_check.count_bandit_high_medium.__code__.co_names
    assert 'in ("HIGH", "MEDIUM")' not in SCRIPT.read_text(encoding="utf-8")


def test_pip_audit_count_helper_avoids_sum_generator(monkeypatch):
    """pip-audit vuln counting should use a direct scan."""
    security_check = load_security_check_module()

    def fail_sum(*_args, **_kwargs):
        raise AssertionError("pip-audit vuln counting should not use sum()")

    monkeypatch.setattr("builtins.sum", fail_sum)

    assert security_check.count_pip_audit_vulns([
        {"name": "a", "vulns": [{"id": "A"}, {"id": "B"}]},
        "not-a-dict",
        {"name": "b", "vulns": []},
        {"name": "c", "vulns": [{"id": "C"}]},
    ]) == 3


def test_external_tool_runners_use_shared_count_helpers(monkeypatch, tmp_path):
    """External scanner runners should delegate parsed counts to helper functions."""
    security_check = load_security_check_module()
    calls: list[tuple[str, object]] = []

    def fake_run(command, **_kwargs):
        if command[0] == "bandit":
            return SimpleNamespace(
                stdout=json.dumps({
                    "results": [
                        {"issue_severity": "HIGH"},
                        {"issue_severity": "LOW"},
                    ],
                })
            )
        return SimpleNamespace(
            stdout=json.dumps([
                {"name": "pkg", "vulns": [{"id": "CVE-1"}]},
            ])
        )

    def count_bandit(results):
        calls.append(("bandit", results))
        return 1

    def count_pip_audit(dependencies):
        calls.append(("pip-audit", dependencies))
        return 1

    monkeypatch.setattr(security_check.shutil, "which", lambda _tool: "/usr/bin/tool")
    monkeypatch.setattr(security_check.subprocess, "run", fake_run)
    monkeypatch.setattr(security_check, "count_bandit_high_medium", count_bandit)
    monkeypatch.setattr(security_check, "count_pip_audit_vulns", count_pip_audit)

    assert security_check.run_bandit(tmp_path) == (True, 1, 2)
    assert security_check.run_pip_audit() == (True, 1)
    assert calls == [
        ("bandit", [{"issue_severity": "HIGH"}, {"issue_severity": "LOW"}]),
        ("pip-audit", [{"name": "pkg", "vulns": [{"id": "CVE-1"}]}]),
    ]


def test_scan_report_counts_cache_finding_scan() -> None:
    """Repeated severity summaries should not rescan findings."""
    security_check = load_security_check_module()

    class CountingFindings(list):
        iterations = 0

        def __iter__(self):
            type(self).iterations += 1
            if type(self).iterations > 1:
                raise AssertionError("ScanReport.counts should reuse the cached scan")
            return super().__iter__()

    findings = CountingFindings([
        security_check.Finding(
            file="app/example.py",
            line=1,
            severity="HIGH",
            rule_id="SEC-TEST",
            message="test",
            snippet="test",
            fix="fix",
        ),
        security_check.Finding(
            file="app/example.py",
            line=2,
            severity="LOW",
            rule_id="SEC-TEST",
            message="test",
            snippet="test",
            fix="fix",
        ),
    ])
    report = security_check.ScanReport(findings=findings)

    assert report.counts["HIGH"] == 1
    assert report.counts["LOW"] == 1
    assert report.counts["HIGH"] == 1
    assert CountingFindings.iterations == 1


def test_security_scanner_records_use_slots_to_avoid_instance_dict() -> None:
    security_check = load_security_check_module()
    finding = security_check.Finding(
        file="app/example.py",
        line=1,
        severity="HIGH",
        rule_id="SEC-TEST",
        message="test",
        snippet="test",
        fix="fix",
    )
    report = security_check.ScanReport(findings=[finding])
    rule = security_check.Rule(
        pattern=r"test",
        glob="*.py",
        severity="LOW",
        rule_id="SEC-TEST",
        message="test",
        fix="fix",
    )

    assert not hasattr(finding, "__dict__")
    assert not hasattr(report, "__dict__")
    assert not hasattr(rule, "__dict__")


def test_security_scanner_static_membership_tables_are_immutable() -> None:
    """Scanner path membership tables should be immutable and tuple-backed."""
    security_check = load_security_check_module()
    source = SCRIPT.read_text(encoding="utf-8")

    assert security_check.EXCLUDE_DIRS == frozenset((
        ".venv", "venv", "env", "ENV", ".env",
        "node_modules", "__pycache__", ".git",
        ".ruff_cache", ".pytest_cache", ".mypy_cache",
        "htmlcov", "dist", "build", ".tox",
        "everything-claude-code", ".planning",
        "tools",
    ))
    assert security_check.EXCLUDE_FILES == frozenset((
        ".secrets.baseline",
        "bandit-report.json",
        "security_check.py",
    ))
    assert security_check.TEST_INDICATORS == frozenset(("test_", "conftest", "tests/", "testing/"))
    assert "EXCLUDE_DIRS = {" not in source
    assert "EXCLUDE_FILES = {" not in source
    assert 'TEST_INDICATORS = {"test_", "conftest", "tests/", "testing/"}' not in source


def test_security_scanner_static_lookup_maps_are_read_only() -> None:
    """Scanner severity/color lookup maps should not be mutable module globals."""
    security_check = load_security_check_module()
    source = SCRIPT.read_text(encoding="utf-8")

    assert isinstance(security_check._SEVERITY_SORT_ORDER, MappingProxyType)
    assert isinstance(security_check._SEV_COLOR, MappingProxyType)
    assert security_check._SEVERITY_SORT_ORDER["CRITICAL"] == 0
    assert security_check._SEV_COLOR["LOW"] == security_check._DIM
    assert "_SEVERITY_SORT_ORDER = {" not in source
    assert "_SEV_COLOR = {" not in source
    assert "MappingProxyType" in source
    assert "_SEVERITY_SORT_ORDER" in source[source.index("def run_scan") : source.index("def run_bandit")]
    assert "_SEV_COLOR" in security_check.format_terminal.__code__.co_names


def test_scan_report_counts_returns_mutation_isolated_copy() -> None:
    """The cached count map should be copied directly and stay externally immutable."""
    security_check = load_security_check_module()
    report = security_check.ScanReport(findings=[
        security_check.Finding(
            file="app/example.py",
            line=1,
            severity="LOW",
            rule_id="SEC-TEST",
            message="test",
            snippet="test",
            fix="fix",
        )
    ])

    counts = report.counts
    counts["LOW"] = 99

    assert report.counts["LOW"] == 1
    assert report.counts == security_check.copy_counts_by_severity(report._counts_cache)
    assert "copy_counts_by_severity" in security_check.ScanReport.counts.fget.__code__.co_names
    assert "dict" not in security_check.copy_counts_by_severity.__code__.co_names


def test_count_findings_by_severity_uses_short_paths() -> None:
    """Empty/single severity counts should avoid the general findings loop."""
    security_check = load_security_check_module()
    finding = security_check.Finding(
        file="app/example.py",
        line=1,
        severity="HIGH",
        rule_id="SEC-TEST",
        message="test",
        snippet="test",
        fix="fix",
    )

    class NoIterFindings(list):
        def __iter__(self):
            raise AssertionError("short severity counts should not iterate findings")

    empty_counts = security_check.count_findings_by_severity(NoIterFindings())
    single_counts = security_check.count_findings_by_severity(NoIterFindings([finding]))
    empty_counts["LOW"] = 99

    assert security_check._ZERO_SEVERITY_COUNTS["LOW"] == 0
    assert single_counts == {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 0, "LOW": 0}
    assert "len" in security_check.count_findings_by_severity.__code__.co_names
    assert "_ZERO_SEVERITY_COUNTS" in security_check.count_findings_by_severity.__code__.co_names


def test_format_json_serializes_findings_with_direct_helper() -> None:
    """Scanner JSON output should share direct, non-recursive finding serialization."""
    security_check = load_security_check_module()
    finding = security_check.Finding(
        file="app/example.py",
        line=1,
        severity="HIGH",
        rule_id="SEC-TEST",
        message="test",
        snippet="test",
        fix="fix",
    )
    second = security_check.Finding(
        file="app/second.py",
        line=2,
        severity="LOW",
        rule_id="SEC-SECOND",
        message="second",
        snippet="second",
        fix="fix",
    )
    third = security_check.Finding(
        file="app/third.py",
        line=3,
        severity="MEDIUM",
        rule_id="SEC-THIRD",
        message="third",
        snippet="third",
        fix="fix",
    )
    report = security_check.ScanReport(findings=[finding], bandit_ran=True)

    payload = json.loads(security_check.format_json(report))

    class NoIterFindings(list):
        def __iter__(self):
            raise AssertionError("short finding serialization should not iterate")

    assert payload["findings"] == security_check.findings_to_dicts([finding])
    assert payload["findings"] == [security_check.finding_to_dict(finding)]
    assert security_check.findings_to_dicts([]) == []
    assert security_check.findings_to_dicts(NoIterFindings([finding])) == [
        security_check.finding_to_dict(finding)
    ]
    assert security_check.findings_to_dicts(NoIterFindings([finding, second])) == [
        security_check.finding_to_dict(finding),
        security_check.finding_to_dict(second),
    ]
    assert security_check.findings_to_dicts(NoIterFindings([finding, second, third])) == [
        security_check.finding_to_dict(finding),
        security_check.finding_to_dict(second),
        security_check.finding_to_dict(third),
    ]
    assert "len" in security_check.findings_to_dicts.__code__.co_names
    assert payload["summary"]["HIGH"] == 1
    assert "findings_to_dicts" in security_check.format_json.__code__.co_names
    assert "finding_to_dict" in security_check.findings_to_dicts.__code__.co_names
    assert "asdict" not in security_check.finding_to_dict.__code__.co_names
    assert "asdict" not in SCRIPT.read_text(encoding="utf-8")
    assert "<listcomp>" not in {
        const.co_name
        for const in security_check.findings_to_dicts.__code__.co_consts
        if hasattr(const, "co_name")
    }


def test_ordered_findings_skips_sort_for_three_findings() -> None:
    security_check = load_security_check_module()
    low = security_check.Finding(
        file="app/low.py",
        line=3,
        severity="LOW",
        rule_id="SEC-LOW",
        message="low",
        snippet="low",
        fix="fix",
    )
    high = security_check.Finding(
        file="app/high.py",
        line=2,
        severity="HIGH",
        rule_id="SEC-HIGH",
        message="high",
        snippet="high",
        fix="fix",
    )
    medium = security_check.Finding(
        file="app/medium.py",
        line=1,
        severity="MEDIUM",
        rule_id="SEC-MEDIUM",
        message="medium",
        snippet="medium",
        fix="fix",
    )

    class NoSortFindings(list):
        def sort(self, *_args, **_kwargs):
            raise AssertionError("three security findings should not call list.sort()")

    findings = NoSortFindings([low, high, medium])

    ordered = security_check.ordered_findings(findings)

    assert ordered is findings
    assert ordered == [high, medium, low]


def test_should_skip_scans_path_parts_without_set_materialization(monkeypatch) -> None:
    """Scanner exclusion checks should avoid building a set from every path."""
    security_check = load_security_check_module()

    def fail_set(*_args, **_kwargs):
        raise AssertionError("_should_skip should scan path parts directly")

    monkeypatch.setattr("builtins.set", fail_set)

    assert security_check._should_skip(Path("app/__pycache__/module.py")) is True
    assert security_check._should_skip(Path("app/security_check.py")) is True
    assert security_check._should_skip(Path("app/routes/api.py")) is False


def test_is_test_file_scans_indicators_without_any(monkeypatch) -> None:
    """Test-file detection should avoid generator setup for each scanned path."""
    security_check = load_security_check_module()

    def fail_any(*_args, **_kwargs):
        raise AssertionError("_is_test_file should scan indicators directly")

    monkeypatch.setattr("builtins.any", fail_any)

    assert security_check._is_test_file(Path("tests/test_api.py")) is True
    assert security_check._is_test_file(Path("app/routes/api.py")) is False


def test_run_scan_reads_each_file_once_per_glob_group(monkeypatch, tmp_path) -> None:
    """Grouped rule scans should not reread the same file once per rule."""
    security_check = load_security_check_module()
    target = tmp_path / "sample.py"
    target.write_text("eval('1')\nshell=True\n", encoding="utf-8")
    rules = [
        security_check.Rule(
            pattern=r"\beval\s*\(",
            glob="*.py",
            severity="CRITICAL",
            rule_id="DANGEROUS-EVAL",
            message="eval",
            fix="fix",
        ),
        security_check.Rule(
            pattern=r"shell\s*=\s*True",
            glob="*.py",
            severity="CRITICAL",
            rule_id="SHELL-TRUE",
            message="shell",
            fix="fix",
        ),
    ]
    read_calls = 0
    original_read_text = Path.read_text

    def counting_read_text(self, *args, **kwargs):  # noqa: ANN001
        nonlocal read_calls
        if self == target:
            read_calls += 1
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(security_check, "RULES", rules)
    monkeypatch.setattr(Path, "read_text", counting_read_text)
    monkeypatch.setattr(security_check, "scan_file", lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("run_scan should scan already-read text")
    ))

    findings = security_check.run_scan(tmp_path)

    assert read_calls == 1
    assert [finding.rule_id for finding in findings] == ["DANGEROUS-EVAL", "SHELL-TRUE"]
    assert "scan_text" in security_check.run_scan.__code__.co_names
    assert "setdefault" not in security_check.run_scan.__code__.co_names


def test_run_scan_streams_applicable_rules_without_active_rule_list(monkeypatch, tmp_path) -> None:
    """Files with only test-skipped rules should not allocate or read unnecessarily."""
    security_check = load_security_check_module()
    target_dir = tmp_path / "tests"
    target_dir.mkdir()
    target = target_dir / "test_sample.py"
    target.write_text("eval('1')\n", encoding="utf-8")
    rules = [
        security_check.Rule(
            pattern=r"\beval\s*\(",
            glob="*.py",
            severity="CRITICAL",
            rule_id="DANGEROUS-EVAL",
            message="eval",
            fix="fix",
            skip_tests=True,
        ),
    ]
    original_read_text = Path.read_text

    def fail_target_read(self, *args, **kwargs):  # noqa: ANN001
        if self == target:
            raise AssertionError("test-skipped rule groups should not read the file")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(security_check, "RULES", rules)
    monkeypatch.setattr(Path, "read_text", fail_target_read)

    assert security_check.run_scan(tmp_path) == []

    source = SCRIPT.read_text(encoding="utf-8")
    run_scan_source = source[source.index("def run_scan") : source.index("def ordered_findings")]
    assert "active_rules" not in run_scan_source
    assert ".items()" not in run_scan_source
    assert "_SEVERITY_SORT_ORDER" in source[source.index("def run_scan") : source.index("def run_bandit")]


def test_ordered_findings_skips_sort_for_zero_one_or_two_findings() -> None:
    security_check = load_security_check_module()

    class SortFailingList(list):
        def sort(self, *_args, **_kwargs):
            raise AssertionError("zero, one, or two findings should not sort")

    finding = security_check.Finding(
        file="sample.py",
        line=2,
        severity="LOW",
        rule_id="TEST",
        message="message",
        snippet="snippet",
        fix="fix",
    )
    high = security_check.Finding(
        file="b.py",
        line=2,
        severity="HIGH",
        rule_id="HIGH",
        message="message",
        snippet="snippet",
        fix="fix",
    )
    critical = security_check.Finding(
        file="a.py",
        line=1,
        severity="CRITICAL",
        rule_id="CRITICAL",
        message="message",
        snippet="snippet",
        fix="fix",
    )

    empty = SortFailingList()
    single = SortFailingList([finding])
    pair = SortFailingList([high, critical])
    multiple = [finding, high, critical]

    assert security_check.ordered_findings(empty) is empty
    assert security_check.ordered_findings(single) is single
    assert security_check.ordered_findings(pair) is pair
    assert pair == [critical, high]
    assert security_check.ordered_findings(multiple) == [critical, high, finding]
    assert "finding_sort_key" in security_check.ordered_findings.__code__.co_names
    assert "ordered_findings" in security_check.run_scan.__code__.co_names


def test_finding_snippets_trim_with_bounded_slice_without_strip() -> None:
    """Finding snippets should avoid full-line strip allocation before truncation."""
    security_check = load_security_check_module()

    class NoStripLine(str):
        def strip(self, *_args, **_kwargs):
            raise AssertionError("finding snippets should trim bounds before slicing")

    line = NoStripLine("   " + "x" * 200 + "   ")

    snippet = security_check.bounded_stripped_snippet(line)

    assert snippet == "x" * 120
    assert security_check.bounded_stripped_snippet(NoStripLine("  abc  "), limit=10) == "abc"
    assert "bounded_stripped_snippet" in security_check.scan_text.__code__.co_names
    assert "strip" not in security_check.bounded_stripped_snippet.__code__.co_names
    assert "min" not in security_check.bounded_stripped_snippet.__code__.co_names


def test_scan_text_scans_lines_without_splitlines_allocation() -> None:
    """File scanning should preserve line semantics without materializing split lines."""
    security_check = load_security_check_module()

    class NoSplitLinesText(str):
        def splitlines(self, *_args, **_kwargs):
            raise AssertionError("scan_text should scan line boundaries directly")

    rule = security_check.Rule(
        pattern=r"\beval\s*\(",
        glob="*.py",
        severity="CRITICAL",
        rule_id="DANGEROUS-EVAL",
        message="eval",
        fix="fix",
    )
    regex = security_check.re.compile(rule.pattern, security_check.re.IGNORECASE)
    text = NoSplitLinesText("safe\r\neval('1')  # nosec\nignored\reval('2')\n")

    findings = security_check.scan_text(Path("sample.py"), text, rule, regex)

    assert [finding.line for finding in findings] == [4]
    assert findings[0].snippet == "eval('2')"
    assert "splitlines" not in security_check.scan_text.__code__.co_names
