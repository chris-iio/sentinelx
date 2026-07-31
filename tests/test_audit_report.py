"""Tests for audit engagement markdown report generation."""

from app.audit.report import _fence, engagement_report, finding_section


def _finding(**overrides):
    finding = {
        "title": "Reentrancy in claim",
        "severity": "high",
        "status": "draft",
        "target": "contracts/Vault.sol#L42",
        "description": "State updated after external call.",
        "impact": "Attacker drains rewards.",
        "poc": "vault.claim(); vault.claim();",
        "remediation": "Apply checks-effects-interactions.",
    }
    finding.update(overrides)
    return finding


def test_fence_cannot_be_closed_by_content():
    fenced = _fence("code with ``` inside")
    assert fenced.startswith("````")
    assert fenced.endswith("````")


def test_finding_section_renders_all_sections():
    section = finding_section(_finding())
    assert "## [High] Reentrancy in claim" in section
    assert "`contracts/Vault.sol#L42`" in section
    assert "### Description" in section
    assert "### Impact" in section
    assert "### Proof of Concept" in section
    assert "vault.claim();" in section
    assert "### Recommended Mitigation" in section


def test_finding_section_omits_empty_sections():
    section = finding_section(_finding(impact="", poc="", remediation="", target=""))
    assert "### Impact" not in section
    assert "### Proof of Concept" not in section
    assert "### Recommended Mitigation" not in section
    assert "Affected code" not in section


def test_engagement_report_summary_and_findings():
    engagement = {
        "name": "Code4rena — Example",
        "platform": "code4rena",
        "url": "https://example.test",
        "deadline": "2026-08-01",
    }
    stats = {
        "total": 2,
        "by_severity": {"critical": 1, "high": 1, "medium": 0, "low": 0,
                        "info": 0, "gas": 0},
        "by_status": {},
    }
    report = engagement_report(
        engagement,
        [_finding(title="A", severity="critical"), _finding(title="B")],
        stats,
    )
    assert "# Code4rena — Example — Security Review" in report
    assert "| Critical | 1 |" in report
    assert "| High | 1 |" in report
    assert "| Medium |" not in report
    assert "## [Critical] A" in report
    assert "## [High] B" in report
