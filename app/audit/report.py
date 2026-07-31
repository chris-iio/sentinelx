"""Markdown report generation for audit engagements.

Produces a submission-ready report: summary table of severities, then each
finding rendered with the sections contest and bounty platforms expect
(description, impact, proof of concept, remediation).
"""
from __future__ import annotations

from .store import SEVERITIES


def _fence(text: str) -> str:
    """Wrap text in a code fence that cannot be closed by its content."""
    fence = "```"
    while fence in text:
        fence += "`"
    return f"{fence}\n{text}\n{fence}"


_SEVERITY_LABELS = {severity: severity.capitalize() for severity in SEVERITIES}


def finding_section(finding: dict) -> str:
    """Render one finding as a markdown report section."""
    lines = [
        f"## [{_SEVERITY_LABELS.get(finding['severity'], 'Info')}] {finding['title']}",
        "",
    ]
    if finding.get("target"):
        lines += [f"**Affected code:** `{finding['target']}`", ""]
    if finding.get("description"):
        lines += ["### Description", "", finding["description"], ""]
    if finding.get("impact"):
        lines += ["### Impact", "", finding["impact"], ""]
    if finding.get("poc"):
        lines += ["### Proof of Concept", "", _fence(finding["poc"]), ""]
    if finding.get("remediation"):
        lines += ["### Recommended Mitigation", "", finding["remediation"], ""]
    return "\n".join(lines).rstrip() + "\n"


def engagement_report(engagement: dict, findings: list[dict], stats: dict) -> str:
    """Render a whole engagement: header, severity summary, then findings."""
    lines = [
        f"# {engagement['name']} — Security Review",
        "",
        f"- Platform: {engagement['platform']}",
        f"- URL: {engagement['url'] or 'n/a'}",
        f"- Deadline: {engagement['deadline'] or 'n/a'}",
        "",
        "## Summary",
        "",
        "| Severity | Count |",
        "| --- | --- |",
    ]
    for severity in SEVERITIES:
        count = stats["by_severity"].get(severity, 0)
        if count:
            lines.append(f"| {_SEVERITY_LABELS[severity]} | {count} |")
    lines += ["", "---", ""]
    for finding in findings:
        lines += [finding_section(finding), "---", ""]
    return "\n".join(lines).rstrip() + "\n"
