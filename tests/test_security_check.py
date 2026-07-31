"""Focused tests for the SentinelX security scanner helpers."""
from __future__ import annotations

import importlib.util
import inspect
import json
import sys
from pathlib import Path
from types import MappingProxyType, SimpleNamespace

SCRIPT = Path("tools/security_check.py")
MAKEFILE = Path("Makefile")


def load_security_check_module():
    module_name = "security_check_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_security_check_is_part_of_fast_verification_lane() -> None:
    """The standard fast gate should fail on scanner-detected security regressions."""
    makefile = MAKEFILE.read_text(encoding="utf-8")
    verify_fast = makefile[makefile.index("verify-fast:") : makefile.index("## Deep verification lane")]

    assert "security-check" in makefile[makefile.index(".PHONY:") : makefile.index("$(TAILWIND):")]
    assert "security-check:" in makefile
    assert "python3 tools/security_check.py --path app --json" in makefile
    assert "python3 tools/security_check.py --path tools --json" in makefile
    assert "$(MAKE) security-check" in verify_fast
    assert verify_fast.index("$(MAKE) security-check") < verify_fast.index("python3 -m pytest")


def test_requests_timeout_rule_does_not_flag_an_explicit_timeout() -> None:
    security_check = load_security_check_module()
    rule = next(rule for rule in security_check.RULES if rule.rule_id == "MISSING-TIMEOUT")
    regex = security_check.re.compile(rule.pattern, security_check.re.IGNORECASE)

    safe = "requests.post(url, json=payload, timeout=(5, 30))"
    unsafe = "requests.post(url, json=payload)"

    assert security_check.scan_text(Path("app/safe.py"), safe, rule, regex) == []
    assert len(security_check.scan_text(Path("app/unsafe.py"), unsafe, rule, regex)) == 1


def test_bandit_count_helper_avoids_sum_generator(monkeypatch):
    """Bandit HIGH/MEDIUM counting should use a direct scan."""
    security_check = load_security_check_module()

    def fail_sum(*_args, **_kwargs):
        raise AssertionError("Bandit severity counting should not use sum()")

    monkeypatch.setattr("builtins.sum", fail_sum)

    assert security_check.count_bandit_high_medium([
        {"issue_severity": "HIGH", "issue_confidence": "LOW"},
        {"issue_severity": "medium", "issue_confidence": "LOW"},
        {"issue_severity": "LOW", "issue_confidence": "HIGH"},
        {"issue_severity": "", "issue_confidence": "HIGH"},
    ]) == 2
    assert security_check.BANDIT_FAIL_SEVERITIES == frozenset(("HIGH", "MEDIUM"))
    assert "BANDIT_FAIL_SEVERITIES" in security_check.count_bandit_high_medium.__code__.co_names
    assert 'in ("HIGH", "MEDIUM")' not in SCRIPT.read_text(encoding="utf-8")


def test_bandit_medium_severity_fails_gate(monkeypatch, tmp_path, capsys) -> None:
    """A Bandit medium-severity count must be reported and block the gate."""
    security_check = load_security_check_module()
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--path", str(tmp_path), "--json"])
    monkeypatch.setattr(security_check, "run_scan", lambda _root: [])
    monkeypatch.setattr(security_check, "run_bandit", lambda _root: (True, 1, 2))

    assert security_check.main() == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["bandit"] == {"ran": True, "high_medium": 1, "total": 2}


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
        if command[0].endswith("/bandit"):
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

    monkeypatch.setattr(security_check.shutil, "which", lambda tool: f"/usr/bin/{tool}")
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
        security_check.Finding(
            file="app/example.py",
            line=3,
            severity="MEDIUM",
            rule_id="SEC-TEST",
            message="test",
            snippet="test",
            fix="fix",
        ),
        security_check.Finding(
            file="app/example.py",
            line=4,
            severity="LOW",
            rule_id="SEC-TEST",
            message="test",
            snippet="test",
            fix="fix",
        ),
        security_check.Finding(
            file="app/example.py",
            line=5,
            severity="LOW",
            rule_id="SEC-TEST",
            message="test",
            snippet="test",
            fix="fix",
        ),
    ])
    report = security_check.ScanReport(findings=findings)

    assert report.counts["HIGH"] == 1
    assert report.counts["LOW"] == 3
    assert report.counts["MEDIUM"] == 1
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
    """Short severity counts should avoid the general findings loop."""
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
        severity="HIGH",
        rule_id="SEC-THIRD",
        message="third",
        snippet="third",
        fix="fix",
    )
    fourth = security_check.Finding(
        file="app/fourth.py",
        line=4,
        severity="MEDIUM",
        rule_id="SEC-FOURTH",
        message="fourth",
        snippet="fourth",
        fix="fix",
    )

    class NoIterFindings(list):
        def __iter__(self):
            raise AssertionError("short severity counts should not iterate findings")

    empty_counts = security_check.count_findings_by_severity(NoIterFindings())
    single_counts = security_check.count_findings_by_severity(NoIterFindings([finding]))
    pair_counts = security_check.count_findings_by_severity(NoIterFindings([finding, second]))
    three_counts = security_check.count_findings_by_severity(NoIterFindings([finding, second, third]))
    four_counts = security_check.count_findings_by_severity(
        NoIterFindings([finding, second, third, fourth])
    )
    empty_counts["LOW"] = 99

    assert security_check._ZERO_SEVERITY_COUNTS["LOW"] == 0
    assert single_counts == {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 0, "LOW": 0}
    assert pair_counts == {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 0, "LOW": 1}
    assert three_counts == {"CRITICAL": 0, "HIGH": 2, "MEDIUM": 0, "LOW": 1}
    assert four_counts == {"CRITICAL": 0, "HIGH": 2, "MEDIUM": 1, "LOW": 1}
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
    fourth = security_check.Finding(
        file="app/fourth.py",
        line=4,
        severity="HIGH",
        rule_id="SEC-FOURTH",
        message="fourth",
        snippet="fourth",
        fix="fix",
    )
    report = security_check.ScanReport(
        findings=[finding],
        bandit_ran=True,
        bandit_high_medium=2,
        bandit_total=3,
    )

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
    assert security_check.findings_to_dicts(NoIterFindings([finding, second, third, fourth])) == [
        security_check.finding_to_dict(finding),
        security_check.finding_to_dict(second),
        security_check.finding_to_dict(third),
        security_check.finding_to_dict(fourth),
    ]
    assert "len" in security_check.findings_to_dicts.__code__.co_names
    assert payload["summary"]["HIGH"] == 1
    assert payload["bandit"] == {"ran": True, "high_medium": 2, "total": 3}
    assert "high" not in payload["bandit"]
    assert "findings_to_dicts" in security_check.format_json.__code__.co_names
    assert "finding_to_dict" in security_check.findings_to_dicts.__code__.co_names
    assert "append_finding_dict" in security_check.findings_to_dicts.__code__.co_names
    assert "asdict" not in security_check.finding_to_dict.__code__.co_names
    assert "asdict" not in SCRIPT.read_text(encoding="utf-8")
    assert "<listcomp>" not in {
        const.co_name
        for const in security_check.findings_to_dicts.__code__.co_consts
        if hasattr(const, "co_name")
    }


def test_append_finding_dict_owns_long_path_mutation() -> None:
    """Long scanner finding serialization should share one append helper."""
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

    serialized: list[dict[str, object]] = []
    security_check.append_finding_dict(serialized, finding)
    source = inspect.getsource(security_check.findings_to_dicts)

    assert serialized == [security_check.finding_to_dict(finding)]
    assert "append_finding_dict(serialized, finding)" in source
    assert "serialized.append(finding_to_dict(finding))" not in source


def test_ordered_findings_skips_sort_for_four_findings() -> None:
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
    critical = security_check.Finding(
        file="app/critical.py",
        line=4,
        severity="CRITICAL",
        rule_id="SEC-CRITICAL",
        message="critical",
        snippet="critical",
        fix="fix",
    )

    class NoIterSortFindings(list):
        def __iter__(self):
            raise AssertionError("four security findings should not iterate")

        def sort(self, *_args, **_kwargs):
            raise AssertionError("four security findings should not sort")

    findings = NoIterSortFindings([low, high, medium, critical])

    ordered = security_check.ordered_findings(findings)

    assert ordered is findings
    assert ordered == [critical, high, medium, low]
    assert "finding_count == 4" in inspect.getsource(security_check.ordered_findings)
    assert "append_ordered_finding" in security_check.ordered_findings.__code__.co_names
    assert "sort" not in security_check.ordered_findings.__code__.co_names

    direct_ordered = []
    security_check.append_ordered_finding(direct_ordered, low)
    security_check.append_ordered_finding(direct_ordered, high)
    security_check.append_ordered_finding(direct_ordered, medium)
    security_check.append_ordered_finding(direct_ordered, critical)
    assert direct_ordered == [critical, high, medium, low]


def test_should_skip_scans_path_parts_without_set_materialization(monkeypatch) -> None:
    """Scanner exclusion checks should avoid building a set from every path."""
    security_check = load_security_check_module()

    def fail_set(*_args, **_kwargs):
        raise AssertionError("_should_skip should scan path parts directly")

    monkeypatch.setattr("builtins.set", fail_set)

    assert security_check._should_skip(Path("app/__pycache__/module.py")) is True
    assert security_check._should_skip(Path("app/security_check.py")) is True
    assert security_check._should_skip(Path("app/routes/api.py")) is False


def test_collect_files_delegates_append_mutation(tmp_path) -> None:
    """Scanner file discovery should keep filtering separate from accumulation."""
    security_check = load_security_check_module()
    app_dir = tmp_path / "app"
    cache_dir = app_dir / "__pycache__"
    app_dir.mkdir()
    cache_dir.mkdir()
    included = app_dir / "module.py"
    excluded = cache_dir / "ignored.py"
    included.write_text("print('ok')\n", encoding="utf-8")
    excluded.write_text("print('skip')\n", encoding="utf-8")
    source = inspect.getsource(security_check.collect_files)
    append_source = inspect.getsource(security_check.append_collected_file)

    files = security_check.collect_files(tmp_path, "*.py")

    assert files == [included]
    assert "append_collected_file(files, p)" in source
    assert "files.append(p)" not in source
    assert "files.append(path)" in append_source


def test_is_test_file_scans_indicators_without_any(monkeypatch) -> None:
    """Test-file detection should avoid generator setup for each scanned path."""
    security_check = load_security_check_module()

    def fail_any(*_args, **_kwargs):
        raise AssertionError("_is_test_file should scan indicators directly")

    monkeypatch.setattr("builtins.any", fail_any)

    assert security_check._is_test_file(Path("tests/test_api.py")) is True
    assert security_check._is_test_file(Path("app/testing/helpers.py")) is True
    assert security_check._is_test_file(Path("app/conftest.py")) is True
    assert security_check._is_test_file(Path("app/routes/api.py")) is False
    source = SCRIPT.read_text(encoding="utf-8")
    is_test_source = source[source.index("def _is_test_file") : source.index("def _should_skip")]
    assert "for indicator in TEST_INDICATORS" not in is_test_source
    assert '"test_" in path_str' in is_test_source
    assert '"testing/" in path_str' in is_test_source


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


def test_run_scan_delegates_compiled_rule_grouping() -> None:
    """Rule grouping should keep regex compilation out of the scan loop."""
    security_check = load_security_check_module()
    rule = security_check.Rule(
        pattern=r"\beval\s*\(",
        glob="*.py",
        severity="CRITICAL",
        rule_id="DANGEROUS-EVAL",
        message="eval",
        fix="fix",
    )
    second = security_check.Rule(
        pattern=r"shell\s*=\s*True",
        glob="*.py",
        severity="CRITICAL",
        rule_id="SHELL-TRUE",
        message="shell",
        fix="fix",
    )
    by_glob: dict[str, list[tuple[object, object]]] = {}

    security_check.append_compiled_rule(by_glob, rule)
    security_check.append_compiled_rule(by_glob, second)

    assert [compiled_rule.rule_id for compiled_rule, _regex in by_glob["*.py"]] == [
        "DANGEROUS-EVAL",
        "SHELL-TRUE",
    ]
    assert all(regex.flags & security_check.re.IGNORECASE for _rule, regex in by_glob["*.py"])
    run_scan_source = inspect.getsource(security_check.run_scan)
    helper_source = inspect.getsource(security_check.append_compiled_rule)
    assert "append_compiled_rule(by_glob, rule)" in run_scan_source
    assert "re.compile(rule.pattern" not in run_scan_source
    assert "re.compile(rule.pattern" in helper_source


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
    assert "next_scan_line" in security_check.scan_text.__code__.co_names
    assert "splitlines" not in security_check.scan_text.__code__.co_names


def test_next_scan_line_owns_line_boundary_progression() -> None:
    """Line boundary walking should stay out of scan_text's rule loop."""
    security_check = load_security_check_module()
    text = "first\r\nsecond\nthird\rfourth"

    first, offset = security_check.next_scan_line(text, 0)
    second, offset = security_check.next_scan_line(text, offset)
    third, offset = security_check.next_scan_line(text, offset)
    fourth, offset = security_check.next_scan_line(text, offset)

    assert (first, second, third, fourth) == ("first", "second", "third", "fourth")
    assert offset == len(text) + 1
    source = SCRIPT.read_text(encoding="utf-8")
    scan_source = source[source.index("def scan_text") : source.index("def next_scan_line")]
    line_source = source[source.index("def next_scan_line") : source.index("def bounded_stripped_snippet")]
    assert "while end < text_length" not in scan_source
    assert "while end < text_length" in line_source
