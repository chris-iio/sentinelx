"""Intake parsing: turn pasted scanner output or notes into candidate findings.

Supported shapes, tried in order:

1. JSON scanner output — Slither (``--json``), osv-scanner, and npm audit.
2. Severity-prefixed lines — e.g. ``[HIGH] Missing access control in withdraw``
   or ``Medium: Oracle price staleness``, optionally followed by detail lines
   and a ``path/file.sol#Lx`` reference.
3. Freeform fallback — the whole paste becomes one draft finding so nothing
   is lost.

Everything is pure text processing; no network or subprocess access.
"""
from __future__ import annotations

import json
import re

from .store import SEVERITIES

_SEVERITY_WORDS = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "informational": "info",
    "info": "info",
    "optimization": "gas",
    "gas": "gas",
}

_LINE_RE = re.compile(
    r"^\s*(?:\[(?P<bracket>\w+)\]|(?P<plain>critical|high|medium|low|"
    r"informational|info|optimization|gas))\s*[:\-–—]?\s+(?P<title>.+?)\s*$",
    re.IGNORECASE,
)
_LOCATION_RE = re.compile(
    r"(?P<path>[\w./-]+\.(?:sol|rs|go|js|ts|py|vy|move))(?:#L(?P<line>\d+(?:-\d+)?))?"
)
_BLANK_RE = re.compile(r"^\s*$")


def _normalize_severity(word: str) -> str | None:
    return _SEVERITY_WORDS.get(word.lower())


def _extract_location(text: str) -> str:
    match = _LOCATION_RE.search(text)
    if not match:
        return ""
    location = match.group("path")
    if match.group("line"):
        location += f"#L{match.group('line')}"
    return location


_LOCATION_ONLY_RE = re.compile(
    r"^\s*[\w./-]+\.(?:sol|rs|go|js|ts|py|vy|move)(?:#L\d+(?:-\d+)?)?\s*$"
)


def _make_finding(title: str, severity: str, body_lines: list[str]) -> dict:
    body = "\n".join(
        line
        for line in body_lines
        if not _BLANK_RE.match(line) and not _LOCATION_ONLY_RE.match(line)
    ).strip()
    return {
        "title": title.strip()[:200] or "Untitled finding",
        "severity": severity if severity in SEVERITIES else "info",
        "target": _extract_location("\n".join([title, *body_lines])),
        "description": body,
    }


# ---------------------------------------------------------------------------
# JSON scanner formats


def _finding_dict(title: str, severity: str, target: str, description: str) -> dict:
    return {
        "title": title.strip()[:200] or "Untitled finding",
        "severity": severity if severity in SEVERITIES else "info",
        "target": target.strip(),
        "description": description.strip(),
    }


def _parse_slither(data: dict) -> list[dict] | None:
    """Parse ``slither --json`` output (results.detectors[])."""
    results = data.get("results")
    if not isinstance(results, dict):
        return None
    detectors = results.get("detectors")
    if not isinstance(detectors, list):
        return None
    findings = []
    for detector in detectors:
        if not isinstance(detector, dict):
            continue
        severity = _normalize_severity(str(detector.get("impact", ""))) or "info"
        target = ""
        elements = detector.get("elements")
        if isinstance(elements, list):
            for element in elements:
                if not isinstance(element, dict):
                    continue
                mapping = element.get("source_mapping")
                if isinstance(mapping, dict) and mapping.get("filename_relative"):
                    target = mapping["filename_relative"]
                    lines = mapping.get("lines")
                    if isinstance(lines, list) and lines:
                        target += f"#L{lines[0]}"
                        if len(lines) > 1:
                            target += f"-{lines[-1]}"
                    break
        title = str(detector.get("check", "detector finding")).replace("-", " ")
        description = str(detector.get("description", ""))
        if detector.get("markdown"):
            description = f"{description}\n\n{detector['markdown']}".strip()
        findings.append(_finding_dict(title, severity, target, description))
    return findings


def _parse_osv_scanner(data: dict) -> list[dict] | None:
    """Parse osv-scanner JSON output (results[].packages[].vulnerabilities[])."""
    results = data.get("results")
    if not isinstance(results, list):
        return None
    findings = []
    for result in results:
        if not isinstance(result, dict):
            continue
        for package in result.get("packages", []) or []:
            if not isinstance(package, dict):
                continue
            info = package.get("package") or {}
            name = info.get("name", "unknown package")
            version = package.get("installed_version", "")
            label = f"{name}@{version}" if version else name
            for vuln in package.get("vulnerabilities", []) or []:
                if not isinstance(vuln, dict):
                    continue
                severity = "info"
                database_severity = vuln.get("database_specific", {})
                if isinstance(database_severity, dict):
                    severity = (
                        _normalize_severity(str(database_severity.get("severity", "")))
                        or severity
                    )
                if severity == "info":
                    for entry in vuln.get("severity", []) or []:
                        if isinstance(entry, dict) and entry.get("score"):
                            severity = _cvss_band(str(entry["score"]))
                            if severity != "info":
                                break
                aliases = ", ".join(vuln.get("aliases", []) or [])
                vuln_id = vuln.get("id", "unknown")
                title = f"{label}: {aliases or vuln_id}"
                description = str(vuln.get("summary", "") or vuln_id)
                findings.append(
                    _finding_dict(title, severity, str(name), description)
                )
    return findings


_CVSS_BANDS = ((9.0, "critical"), (7.0, "high"), (4.0, "medium"), (0.1, "low"))


def _cvss_band(raw: str) -> str:
    """Map a CVSS score or vector string to a severity band.

    Accepts a bare numeric score ("9.8") or a vector
    ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"). For vectors, a rough
    base band is derived from the CIA impact metrics: all-high → critical,
    any high → high, any low → medium, none → low.
    """
    if raw.startswith("CVSS"):
        metrics = dict(
            pair.split(":", 1)
            for pair in raw.split("/")[1:]
            if ":" in pair
        )
        impacts = [metrics.get(key, "N") for key in ("C", "I", "A")]
        if all(value == "H" for value in impacts):
            return "critical"
        if any(value == "H" for value in impacts):
            return "high"
        if any(value == "L" for value in impacts):
            return "medium"
        return "low"
    match = re.search(r"\d+(?:\.\d+)?", raw)
    if not match:
        return "info"
    score = float(match.group(0))
    for threshold, band in _CVSS_BANDS:
        if score >= threshold:
            return band
    return "info"


def _parse_npm_audit(data: dict) -> list[dict] | None:
    """Parse ``npm audit --json`` output (vulnerabilities map)."""
    vulnerabilities = data.get("vulnerabilities")
    if not isinstance(vulnerabilities, dict):
        return None
    findings = []
    for name, entry in vulnerabilities.items():
        if not isinstance(entry, dict):
            continue
        severity = _normalize_severity(str(entry.get("severity", ""))) or "info"
        via_descriptions = []
        for via in entry.get("via", []) or []:
            if isinstance(via, dict):
                via_descriptions.append(
                    f"{via.get('title', via.get('name', ''))} ({via.get('url', 'n/a')})"
                )
            elif isinstance(via, str):
                via_descriptions.append(via)
        rng = entry.get("range", "")
        title = f"{name}: {entry.get('severity', 'unknown')} vulnerability"
        description = "\n".join(filter(None, via_descriptions))
        if rng:
            description = f"Affected range: {rng}\n{description}".strip()
        if entry.get("fixAvailable"):
            description += "\nFix available."
        findings.append(_finding_dict(title, severity, str(name), description))
    return findings


def _parse_semgrep(data: dict) -> list[dict] | None:
    """Parse ``semgrep --json`` output (results[])."""
    results = data.get("results")
    if not isinstance(results, list):
        return None
    if not all(isinstance(r, dict) and "check_id" in r for r in results):
        return None
    severity_map = {"ERROR": "high", "WARNING": "medium", "INFO": "info"}
    findings = []
    for result in results:
        extra = result.get("extra") or {}
        severity = severity_map.get(str(extra.get("severity", "")).upper(), "info")
        path = str(result.get("path", ""))
        start = result.get("start") or {}
        if path and start.get("line"):
            path += f"#L{start['line']}"
        title = str(result.get("check_id", "semgrep finding")).split(".")[-1]
        description = str(extra.get("message", ""))
        findings.append(_finding_dict(title, severity, path, description))
    return findings


def _parse_mythril(data: dict) -> list[dict] | None:
    """Parse ``myth analyze -o json`` output (issues[])."""
    issues = data.get("issues")
    if not isinstance(issues, list):
        return None
    if not all(isinstance(i, dict) and "swcID" in i for i in issues):
        return None
    findings = []
    for issue in issues:
        severity = _normalize_severity(str(issue.get("severity", ""))) or "info"
        title = str(issue.get("title") or issue.get("swcID", "mythril issue"))
        target = ""
        locations = issue.get("locations") or []
        for location in locations:
            if not isinstance(location, dict):
                continue
            mapping = location.get("sourceMap") or {}
            if mapping.get("filename"):
                target = str(mapping["filename"])
                if mapping.get("lineno"):
                    target += f"#L{mapping['lineno']}"
                break
        description = str(issue.get("description", ""))
        swc = issue.get("swcID", "")
        if swc:
            description = f"{swc}\n{description}".strip()
        findings.append(_finding_dict(title, severity, target, description))
    return findings


def _parse_json_scanners(text: str) -> list[dict] | None:
    """Try each known JSON scanner format; return findings or None.

    Tolerates log noise around the JSON payload (tool stdout mixed with
    stderr) by retrying on the outermost brace span.
    """
    candidates = [text]
    start = text.find("{")
    end = text.rfind("}")
    if 0 <= start < end:
        candidates.append(text[start : end + 1])
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        for parser in (
            _parse_slither,
            _parse_npm_audit,
            _parse_semgrep,
            _parse_mythril,
            _parse_osv_scanner,
        ):
            findings = parser(data)
            if findings is not None:
                for finding in findings:
                    finding["source"] = "scanner"
                return findings
    return None


# ---------------------------------------------------------------------------
# Line-oriented text formats


def parse_intake(text: str) -> list[dict]:
    """Parse pasted scanner output or notes into candidate finding dicts.

    Each dict has keys: title, severity, target, description. Returns at
    least one candidate for any non-empty input (freeform fallback).
    """
    if not text or not text.strip():
        return []

    json_findings = _parse_json_scanners(text)
    if json_findings is not None:
        return json_findings

    lines = text.splitlines()
    findings: list[dict] = []
    current: dict | None = None
    body: list[str] = []

    def flush() -> None:
        nonlocal current, body
        if current is not None:
            findings.append(_make_finding(current["title"], current["severity"], body))
        current = None
        body = []

    for line in lines:
        match = _LINE_RE.match(line)
        word = match and (match.group("bracket") or match.group("plain"))
        severity = _normalize_severity(word) if word else None
        if severity is not None:
            flush()
            current = {"title": match.group("title"), "severity": severity}
        elif current is not None:
            body.append(line)
    flush()

    if findings:
        for finding in findings:
            finding["source"] = "lines"
        return findings

    stripped = text.strip()
    return [
        {
            "title": stripped.splitlines()[0][:200],
            "severity": "info",
            "target": _extract_location(stripped),
            "description": stripped,
            "source": "freeform",
        }
    ]
