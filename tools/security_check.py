#!/usr/bin/env python3
"""SentinelX Security Scanner — OPSEC & vulnerability checker.

Scans the codebase for security issues using pattern-based static analysis
tailored to Python/Flask applications. Optionally runs bandit and pip-audit
if they are installed.

Exit codes:
    0 — no CRITICAL or HIGH findings
    1 — CRITICAL or HIGH findings detected
    2 — scanner error

Usage:
    python3 tools/security_check.py              # scan app/ directory
    python3 tools/security_check.py --json       # JSON output
    python3 tools/security_check.py --path app/  # scan specific path
    python3 tools/security_check.py --strict     # fail on MEDIUM too
    python3 tools/security_check.py --with-deps  # also run pip-audit
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from enum import IntEnum
from pathlib import Path

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

class Severity(IntEnum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    severity: str
    rule_id: str
    message: str
    snippet: str
    fix: str


@dataclass
class ScanReport:
    findings: list[Finding] = field(default_factory=list)
    bandit_ran: bool = False
    bandit_high: int = 0
    bandit_total: int = 0
    pip_audit_ran: bool = False
    pip_audit_vulns: int = 0

    @property
    def counts(self) -> dict[str, int]:
        counts: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# Rules — each rule is (regex, file_glob, severity, rule_id, message, fix)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Rule:
    pattern: str
    glob: str
    severity: str
    rule_id: str
    message: str
    fix: str
    # Optional: if True, finding is only flagged outside test files
    skip_tests: bool = False


RULES: list[Rule] = [
    # ── Dangerous functions ──────────────────────────────────────────────
    Rule(
        pattern=r"\beval\s*\(",
        glob="*.py",
        severity="CRITICAL",
        rule_id="DANGEROUS-EVAL",
        message="eval() allows arbitrary code execution",
        fix="Remove eval(); use ast.literal_eval() for safe literal parsing",
        skip_tests=True,
    ),
    Rule(
        pattern=r"\bexec\s*\(",
        glob="*.py",
        severity="CRITICAL",
        rule_id="DANGEROUS-EXEC",
        message="exec() allows arbitrary code execution",
        fix="Remove exec(); restructure logic to avoid dynamic code execution",
        skip_tests=True,
    ),
    Rule(
        pattern=r"\bpickle\.loads?\s*\(",
        glob="*.py",
        severity="CRITICAL",
        rule_id="UNSAFE-PICKLE",
        message="pickle deserialization can execute arbitrary code",
        fix="Use json.loads() instead; if pickle required, sign data with HMAC first",
        skip_tests=True,
    ),
    Rule(
        pattern=r"\byaml\.load\s*\((?!.*(?:SafeLoader|safe_load))",
        glob="*.py",
        severity="CRITICAL",
        rule_id="UNSAFE-YAML",
        message="yaml.load() without SafeLoader enables code execution",
        fix="Use yaml.safe_load() or yaml.load(data, Loader=yaml.SafeLoader)",
        skip_tests=True,
    ),
    Rule(
        pattern=r"(?:from\s+subprocess\s+import|import\s+subprocess)",
        glob="*.py",
        severity="HIGH",
        rule_id="SUBPROCESS-IMPORT",
        message="subprocess module enables command injection if misused",
        fix="Avoid subprocess; use Python libraries instead. If required, never use shell=True",
        skip_tests=True,
    ),
    Rule(
        pattern=r"\bos\.system\s*\(",
        glob="*.py",
        severity="CRITICAL",
        rule_id="OS-SYSTEM",
        message="os.system() runs shell commands — command injection risk",
        fix="Remove os.system(); use subprocess.run([...], shell=False) if needed",
        skip_tests=True,
    ),
    Rule(
        pattern=r"\bos\.popen\s*\(",
        glob="*.py",
        severity="CRITICAL",
        rule_id="OS-POPEN",
        message="os.popen() runs shell commands — command injection risk",
        fix="Remove os.popen(); use subprocess.run([...], shell=False, capture_output=True)",
        skip_tests=True,
    ),
    Rule(
        pattern=r"shell\s*=\s*True",
        glob="*.py",
        severity="CRITICAL",
        rule_id="SHELL-TRUE",
        message="shell=True enables shell injection via user input",
        fix="Use shell=False (default) and pass command as a list",
        skip_tests=True,
    ),

    # ── Flask / Jinja2 security ──────────────────────────────────────────
    Rule(
        pattern=r"\|\s*safe\b",
        glob="*.html",
        severity="CRITICAL",
        rule_id="JINJA-SAFE-FILTER",
        message="|safe bypasses autoescaping — XSS risk",
        fix="Remove |safe; let Jinja2 autoescape handle output safely",
    ),
    Rule(
        pattern=r"\{%\s*autoescape\s+false\s*%\}",
        glob="*.html",
        severity="CRITICAL",
        rule_id="JINJA-AUTOESCAPE-OFF",
        message="Disabling autoescape removes XSS protection",
        fix="Remove {% autoescape false %}; keep autoescape enabled",
    ),
    Rule(
        pattern=r"\brender_template_string\s*\(",
        glob="*.py",
        severity="HIGH",
        rule_id="TEMPLATE-INJECTION",
        message="render_template_string() with user input enables SSTI",
        fix="Use render_template() with .html files instead",
        skip_tests=True,
    ),
    Rule(
        pattern=r"\bMarkup\s*\(\s*request\.",
        glob="*.py",
        severity="HIGH",
        rule_id="MARKUP-USER-INPUT",
        message="Markup() on user input bypasses escaping — XSS risk",
        fix="Never call Markup() on user input; let Jinja2 autoescape handle it",
    ),
    Rule(
        pattern=r"debug\s*=\s*True",
        glob="*.py",
        severity="CRITICAL",
        rule_id="DEBUG-ENABLED",
        message="Debug mode exposes stack traces, source code, and interactive debugger",
        fix="Set debug=False; never read debug from environment in production",
    ),
    Rule(
        pattern=r"FLASK_DEBUG\s*=\s*['\"]?1",
        glob="*",
        severity="HIGH",
        rule_id="FLASK-DEBUG-ENV",
        message="FLASK_DEBUG=1 enables debug mode via environment",
        fix="Remove FLASK_DEBUG=1; hardcode debug=False in application code",
    ),
    Rule(
        pattern=r"WTF_CSRF_ENABLED\s*=\s*False",
        glob="*.py",
        severity="HIGH",
        rule_id="CSRF-DISABLED",
        message="CSRF protection disabled — forms vulnerable to cross-site request forgery",
        fix="Only disable CSRF in test configuration (TestConfig), never in production",
        skip_tests=True,
    ),

    # ── Secrets & credentials ────────────────────────────────────────────
    Rule(
        pattern=r"(?:SECRET_KEY|secret_key)\s*=\s*['\"][a-zA-Z0-9]{4,}['\"]",
        glob="*.py",
        severity="CRITICAL",
        rule_id="HARDCODED-SECRET-KEY",
        message="Hardcoded SECRET_KEY allows session/CSRF token forgery",
        fix="Use os.environ.get('SECRET_KEY') or secrets.token_hex(32)",
    ),
    Rule(
        pattern=r"(?:password|passwd|pwd)\s*=\s*['\"][^'\"]+['\"]",
        glob="*.py",
        severity="HIGH",
        rule_id="HARDCODED-PASSWORD",
        message="Hardcoded password in source code",
        fix="Move to environment variable or secret manager",
        skip_tests=True,
    ),
    Rule(
        pattern=r"(?:api[_-]?key|apikey|api_secret)\s*=\s*['\"][A-Za-z0-9_\-]{10,}['\"]",
        glob="*.py",
        severity="CRITICAL",
        rule_id="HARDCODED-API-KEY",
        message="Hardcoded API key in source code",
        fix="Use os.environ.get() to read API keys; never commit real keys",
        skip_tests=True,
    ),
    Rule(
        pattern=r"AKIA[0-9A-Z]{16}",
        glob="*",
        severity="CRITICAL",
        rule_id="AWS-ACCESS-KEY",
        message="AWS Access Key ID detected",
        fix="Rotate the key immediately; use IAM roles or env vars instead",
    ),
    Rule(
        pattern=r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----",
        glob="*",
        severity="CRITICAL",
        rule_id="PRIVATE-KEY",
        message="Private key embedded in source file",
        fix="Remove key from source; use a secrets manager or key vault",
    ),
    Rule(
        pattern=r"ghp_[A-Za-z0-9]{36}",
        glob="*",
        severity="CRITICAL",
        rule_id="GITHUB-TOKEN",
        message="GitHub personal access token detected",
        fix="Rotate the token; use GITHUB_TOKEN env var in CI/CD",
    ),
    Rule(
        pattern=r"sk-[A-Za-z0-9]{20,}",
        glob="*",
        severity="CRITICAL",
        rule_id="OPENAI-API-KEY",
        message="OpenAI/Stripe-style secret key detected",
        fix="Rotate the key; use environment variables",
    ),

    # ── HTTP safety ──────────────────────────────────────────────────────
    Rule(
        pattern=r"requests\.\w+\s*\([^)]*verify\s*=\s*False",
        glob="*.py",
        severity="HIGH",
        rule_id="SSL-VERIFY-DISABLED",
        message="SSL verification disabled — MITM attack possible",
        fix="Remove verify=False; use the default verify=True",
    ),
    Rule(
        pattern=r"requests\.(?:get|post|put|delete|patch|head)\s*\([^)]*\)(?!.*timeout)",
        glob="*.py",
        severity="MEDIUM",
        rule_id="MISSING-TIMEOUT",
        message="HTTP request without timeout — can hang indefinitely (DoS vector)",
        fix="Add timeout=(connect_seconds, read_seconds), e.g. timeout=(5, 30)",
        skip_tests=True,
    ),
    Rule(
        pattern=r"requests\.\w+\s*\(\s*request\.",
        glob="*.py",
        severity="CRITICAL",
        rule_id="SSRF-USER-INPUT",
        message="User input passed directly to HTTP request — SSRF risk",
        fix="Validate URL against ALLOWED_API_HOSTS allowlist before making request",
    ),

    # ── SQL injection ────────────────────────────────────────────────────
    Rule(
        pattern=r'(?:execute|executemany)\s*\(\s*f["\']',
        glob="*.py",
        severity="CRITICAL",
        rule_id="SQL-INJECTION-FSTRING",
        message="f-string in SQL execute() — SQL injection risk",
        fix="Use parameterized queries: execute('SELECT ... WHERE id=?', (id,))",
    ),
    Rule(
        pattern=r'(?:execute|executemany)\s*\(\s*["\'].*%s',
        glob="*.py",
        severity="HIGH",
        rule_id="SQL-INJECTION-FORMAT",
        message="String formatting in SQL execute() — SQL injection risk",
        fix="Use parameterized queries with placeholders",
    ),

    # ── Crypto weaknesses ────────────────────────────────────────────────
    Rule(
        pattern=r"hashlib\.(?:md5|sha1)\s*\(",
        glob="*.py",
        severity="MEDIUM",
        rule_id="WEAK-HASH",
        message="MD5/SHA1 are cryptographically broken for security use",
        fix="Use hashlib.sha256() or werkzeug.security.generate_password_hash()",
        skip_tests=True,
    ),

    # ── Input handling ───────────────────────────────────────────────────
    Rule(
        pattern=r"open\s*\(\s*request\.",
        glob="*.py",
        severity="CRITICAL",
        rule_id="PATH-TRAVERSAL",
        message="User input in open() — path traversal attack possible",
        fix="Validate/sanitize filename; use werkzeug.utils.secure_filename()",
    ),
    Rule(
        pattern=r"redirect\s*\(\s*request\.",
        glob="*.py",
        severity="HIGH",
        rule_id="OPEN-REDIRECT",
        message="User input in redirect() — open redirect vulnerability",
        fix="Use url_for() for internal routes; validate external URLs against allowlist",
    ),

    # ── JavaScript security ──────────────────────────────────────────────
    Rule(
        pattern=r"\.innerHTML\s*=",
        glob="*.js",
        severity="HIGH",
        rule_id="JS-INNERHTML",
        message="innerHTML assignment — XSS risk if value contains user input",
        fix="Use textContent instead; or sanitize with DOMPurify before insertion",
    ),
    Rule(
        pattern=r"\beval\s*\(",
        glob="*.js",
        severity="CRITICAL",
        rule_id="JS-EVAL",
        message="eval() in JavaScript — code injection risk",
        fix="Remove eval(); use JSON.parse() for data, or restructure logic",
    ),
]

# ---------------------------------------------------------------------------
# File exclusions
# ---------------------------------------------------------------------------

EXCLUDE_DIRS = {
    ".venv", "venv", "env", "ENV", ".env",
    "node_modules", "__pycache__", ".git",
    ".ruff_cache", ".pytest_cache", ".mypy_cache",
    "htmlcov", "dist", "build", ".tox",
    "everything-claude-code", ".planning",
}

EXCLUDE_FILES = {
    ".secrets.baseline",
    "bandit-report.json",
}

TEST_INDICATORS = {"test_", "conftest", "tests/", "testing/"}


def _is_test_file(path: Path) -> bool:
    """Check if a file path looks like a test file."""
    path_str = str(path)
    return any(indicator in path_str for indicator in TEST_INDICATORS)


def _should_skip(path: Path) -> bool:
    """Check if a file/directory should be excluded from scanning."""
    parts = set(path.parts)
    if parts & EXCLUDE_DIRS:
        return True
    if path.name in EXCLUDE_FILES:
        return True
    return False


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

def collect_files(root: Path, glob_pattern: str) -> list[Path]:
    """Collect files matching glob, excluding ignored directories."""
    files = []
    for p in root.rglob(glob_pattern):
        if p.is_file() and not _should_skip(p):
            files.append(p)
    return files


def scan_file(filepath: Path, rule: Rule) -> list[Finding]:
    """Scan a single file against a single rule."""
    findings: list[Finding] = []
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return findings

    regex = re.compile(rule.pattern, re.IGNORECASE)
    for lineno, line in enumerate(text.splitlines(), start=1):
        # Skip nosec-suppressed lines
        if "nosec" in line or "noqa" in line:
            continue
        if regex.search(line):
            findings.append(
                Finding(
                    file=str(filepath),
                    line=lineno,
                    severity=rule.severity,
                    rule_id=rule.rule_id,
                    message=rule.message,
                    snippet=line.strip()[:120],
                    fix=rule.fix,
                )
            )
    return findings


def run_scan(root: Path) -> list[Finding]:
    """Run all rules against all matching files under root."""
    all_findings: list[Finding] = []
    # Group rules by glob to minimize filesystem traversal
    by_glob: dict[str, list[Rule]] = {}
    for rule in RULES:
        by_glob.setdefault(rule.glob, []).append(rule)

    for glob_pattern, rules in by_glob.items():
        files = collect_files(root, glob_pattern)
        for filepath in files:
            is_test = _is_test_file(filepath)
            for rule in rules:
                if rule.skip_tests and is_test:
                    continue
                all_findings.extend(scan_file(filepath, rule))

    # Sort by severity (highest first), then file, then line
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    all_findings.sort(key=lambda f: (severity_order.get(f.severity, 9), f.file, f.line))
    return all_findings


# ---------------------------------------------------------------------------
# External tool runners
# ---------------------------------------------------------------------------

def run_bandit(root: Path) -> tuple[bool, int, int]:
    """Run bandit if installed. Returns (ran, high_count, total_count).

    Only HIGH and MEDIUM severity findings count toward failure.
    LOW findings are informational only.
    """
    if not shutil.which("bandit"):
        return False, 0, 0
    try:
        result = subprocess.run(
            ["bandit", "-r", str(root), "-f", "json", "--quiet"],
            capture_output=True, text=True, timeout=120,
        )
        if result.stdout:
            data = json.loads(result.stdout)
            results = data.get("results", [])
            high_count = sum(
                1 for r in results
                if r.get("issue_severity", "").upper() in ("HIGH", "MEDIUM")
            )
            return True, high_count, len(results)
        return True, 0, 0
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return False, 0, 0


def run_pip_audit() -> tuple[bool, int]:
    """Run pip-audit if installed. Returns (ran, vuln_count)."""
    if not shutil.which("pip-audit"):
        return False, 0
    try:
        result = subprocess.run(
            ["pip-audit", "--format", "json", "--desc"],
            capture_output=True, text=True, timeout=120,
        )
        if result.stdout:
            data = json.loads(result.stdout)
            # pip-audit returns a list of dependency objects
            vulns = sum(
                len(dep.get("vulns", []))
                for dep in data
                if isinstance(dep, dict)
            )
            return True, vulns
        return True, 0
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return False, 0


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

# ANSI colors
_RED = "\033[0;31m"
_YELLOW = "\033[1;33m"
_GREEN = "\033[0;32m"
_CYAN = "\033[0;36m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_NC = "\033[0m"

_SEV_COLOR = {
    "CRITICAL": _RED,
    "HIGH": _RED,
    "MEDIUM": _YELLOW,
    "LOW": _DIM,
}


def format_terminal(report: ScanReport) -> str:
    """Colored terminal output."""
    lines: list[str] = []
    lines.append("")
    lines.append(f"{_BOLD}{'=' * 60}{_NC}")
    lines.append(f"{_BOLD}  SentinelX Security Scanner{_NC}")
    lines.append(f"{_BOLD}{'=' * 60}{_NC}")
    lines.append("")

    if not report.findings:
        lines.append(f"  {_GREEN}No security findings.{_NC}")
    else:
        for f in report.findings:
            color = _SEV_COLOR.get(f.severity, "")
            lines.append(f"  {color}[{f.severity}]{_NC} {f.rule_id}")
            lines.append(f"  {_DIM}{f.file}:{f.line}{_NC}")
            lines.append(f"    {f.message}")
            lines.append(f"    {_DIM}Code: {f.snippet}{_NC}")
            lines.append(f"    {_CYAN}Fix:  {f.fix}{_NC}")
            lines.append("")

    # Summary
    lines.append(f"{_BOLD}{'-' * 60}{_NC}")
    c = report.counts
    lines.append(
        f"  Findings: "
        f"{_RED}{c['CRITICAL']} CRITICAL{_NC}  "
        f"{_RED}{c['HIGH']} HIGH{_NC}  "
        f"{_YELLOW}{c['MEDIUM']} MEDIUM{_NC}  "
        f"{_DIM}{c['LOW']} LOW{_NC}"
    )

    if report.bandit_ran:
        if report.bandit_total == 0:
            status = f"{_GREEN}0 issues{_NC}"
        elif report.bandit_high == 0:
            status = f"{_GREEN}{report.bandit_total} low (info only){_NC}"
        else:
            status = f"{_RED}{report.bandit_high} high/medium{_NC}, {report.bandit_total} total"
        lines.append(f"  Bandit:    {status}")
    else:
        lines.append(f"  Bandit:    {_DIM}not installed (pip install bandit){_NC}")

    if report.pip_audit_ran:
        status = f"{_GREEN}0 vulns{_NC}" if report.pip_audit_vulns == 0 else f"{_RED}{report.pip_audit_vulns} vulns{_NC}"
        lines.append(f"  pip-audit: {status}")
    else:
        lines.append(f"  pip-audit: {_DIM}skipped (use --with-deps to enable){_NC}")

    lines.append(f"{_BOLD}{'-' * 60}{_NC}")

    total_critical = c["CRITICAL"] + c["HIGH"]
    if total_critical == 0 and report.bandit_high == 0 and report.pip_audit_vulns == 0:
        lines.append(f"  {_GREEN}{_BOLD}PASS{_NC} — no critical/high issues found")
    else:
        lines.append(f"  {_RED}{_BOLD}FAIL{_NC} — {total_critical} critical/high issue(s) require attention")

    lines.append("")
    return "\n".join(lines)


def format_json(report: ScanReport) -> str:
    """Machine-readable JSON output."""
    return json.dumps(
        {
            "findings": [asdict(f) for f in report.findings],
            "summary": report.counts,
            "bandit": {"ran": report.bandit_ran, "high": report.bandit_high, "total": report.bandit_total},
            "pip_audit": {"ran": report.pip_audit_ran, "vulns": report.pip_audit_vulns},
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="SentinelX Security Scanner — check codebase for OPSEC and security issues",
    )
    parser.add_argument(
        "--path", default="app",
        help="Directory to scan (default: app/)",
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Fail on MEDIUM severity and above (default: only CRITICAL/HIGH)",
    )
    parser.add_argument(
        "--with-deps", action="store_true",
        help="Also run pip-audit for dependency vulnerability scanning",
    )
    parser.add_argument(
        "--no-bandit", action="store_true",
        help="Skip bandit even if installed",
    )
    args = parser.parse_args()

    root = Path(args.path)
    if not root.exists():
        print(f"Error: path '{root}' does not exist", file=sys.stderr)
        return 2

    # Run custom scan
    findings = run_scan(root)

    # Run external tools
    report = ScanReport(findings=findings)

    if not args.no_bandit:
        report.bandit_ran, report.bandit_high, report.bandit_total = run_bandit(root)

    if args.with_deps:
        report.pip_audit_ran, report.pip_audit_vulns = run_pip_audit()

    # Output
    if args.json_output:
        print(format_json(report))
    else:
        print(format_terminal(report))

    # Exit code
    c = report.counts
    fail_severities = c["CRITICAL"] + c["HIGH"]
    if args.strict:
        fail_severities += c["MEDIUM"]

    if fail_severities > 0 or report.bandit_high > 0 or report.pip_audit_vulns > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
