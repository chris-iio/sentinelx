"""Security audit tests for shipping verification.

These tests codify the security properties from Phase 4 success criteria:
1. CSP header blocks inline scripts
2. No |safe filter on untrusted data in templates
3. No outbound HTTP calls with IOC values as URL components

These are regression guards — the codebase already passes all checks.
"""
import re
from pathlib import Path

APP_ROOT = Path(__file__).parent.parent / "app"
TEMPLATES_DIR = APP_ROOT / "templates"
ADAPTERS_DIR = APP_ROOT / "enrichment" / "adapters"


def test_csp_header_exact_match(client):
    """CSP must be 'default-src 'self'; script-src 'self'' — blocks inline scripts."""
    response = client.get("/")
    assert "Content-Security-Policy" in response.headers
    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    # Ensure no unsafe-inline or unsafe-eval
    assert "unsafe-inline" not in csp
    assert "unsafe-eval" not in csp


def test_no_safe_filter_in_templates():
    """No Jinja2 |safe filter usage in any template file.

    |safe disables autoescaping — any use on untrusted data (IOC values,
    API responses) creates an XSS vector (SEC-08).

    Note: | upper, | length, etc. are safe and must NOT be flagged.
    The regex specifically matches '| safe' or '|safe' (the filter name).
    """
    safe_pattern = re.compile(r"\|\s*safe\b")
    violations = []

    for template_file in TEMPLATES_DIR.rglob("*.html"):
        content = template_file.read_text()
        for line_no, line in enumerate(content.splitlines(), start=1):
            if safe_pattern.search(line):
                violations.append(f"{template_file.name}:{line_no}: {line.strip()}")

    assert violations == [], (
        f"Found |safe filter in templates (XSS risk):\n"
        + "\n".join(violations)
    )


def test_no_ioc_value_in_outbound_url():
    """No outbound HTTP call constructs its URL from an IOC value.

    IOC values must only appear as POST body data, query parameters, or
    base64-encoded path segments (VT URL lookup). Direct string
    interpolation of IOC values into URL paths is an SSRF vector (SEC-07).

    Scanning strategy: look for patterns where ioc.value or ioc_value
    appears in URL string construction (f-string, .format, or + concat
    with 'http'). Exclude known-safe patterns:
    - base64 encoding (VT _url_id)
    - POST body / json= / data= parameters
    - hash= / search_term= query parameters
    """
    # Patterns that indicate IOC value used in URL construction (unsafe)
    unsafe_patterns = [
        # f-string with ioc in URL
        re.compile(r'f["\']https?://.*\{.*ioc', re.IGNORECASE),
        # .format() with ioc in URL
        re.compile(r'["\']https?://.*\.format\(.*ioc', re.IGNORECASE),
        # String concat: "http..." + ioc_value or + ioc.value
        re.compile(r'["\']https?://[^"\']*["\']\s*\+\s*(?:ioc[._]value|ioc\.value)', re.IGNORECASE),
    ]

    # Known-safe patterns to exclude (VT base64 URL ID)
    safe_exclusions = [
        re.compile(r'base64'),
        re.compile(r'_url_id'),
    ]

    violations = []

    for adapter_file in ADAPTERS_DIR.rglob("*.py"):
        content = adapter_file.read_text()
        for line_no, line in enumerate(content.splitlines(), start=1):
            for pattern in unsafe_patterns:
                if pattern.search(line):
                    # Check if line matches a known-safe exclusion
                    is_safe = any(exc.search(line) for exc in safe_exclusions)
                    if not is_safe:
                        violations.append(
                            f"{adapter_file.name}:{line_no}: {line.strip()}"
                        )

    assert violations == [], (
        f"Found IOC value used in URL construction (SSRF risk):\n"
        + "\n".join(violations)
    )
