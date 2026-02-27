# Dead Code Analysis Report

**Project:** SentinelX
**Date:** 2026-02-28
**Analyst:** Claude Opus 4.6 (refactor-cleaner agent)
**Baseline:** 224 unit/integration tests passing (E2E skipped -- Playwright not installed)
**Codebase:** 1,708 lines Python (app/), 4,306 lines Python (tests/), 1,865 lines CSS+JS

## Executive Summary

| Category | Count | Estimated Lines Removable |
|----------|-------|---------------------------|
| SAFE to remove | 10 | ~55 lines |
| CAUTION (verify first) | 5 | ~45 lines |
| DANGER (do not touch) | 14 | 0 |

The codebase is remarkably clean for a v1.2 project. No orphaned Python files, no
dead branches, no commented-out code blocks. The main findings are unused imports
in test files, one unused Python class, one unused CSS class, and missing CSS
definitions for dynamically-generated class names.

---

## Tools Used

| Tool | Version | Scope |
|------|---------|-------|
| vulture | 2.14 | Dead code detection (60% + 80% confidence) |
| ruff | 0.15.2 | Unused imports (F401), unused variables (F841) |
| pipdeptree | 2.31.0 | Dependency tree analysis |
| Manual grep | -- | Cross-file import tracing, template analysis |

---

## SAFE -- Dead Code to Remove

### 1. Unused `import pytest` in 7 test files

**Severity:** SAFE
**Lines saved:** ~7

These files import `pytest` but never use it (no `pytest.raises`, no
`pytest.mark`, no `@pytest.fixture`):

| File | Line |
|------|------|
| `/home/chris/projects/sentinelx/tests/test_classifier.py` | 5 |
| `/home/chris/projects/sentinelx/tests/test_config_store.py` | 10 |
| `/home/chris/projects/sentinelx/tests/test_extractor.py` | 6 |
| `/home/chris/projects/sentinelx/tests/test_malwarebazaar.py` | 13 |
| `/home/chris/projects/sentinelx/tests/test_normalizer.py` | 5 |
| `/home/chris/projects/sentinelx/tests/test_pipeline.py` | 6 |
| `/home/chris/projects/sentinelx/tests/e2e/test_results_page.py` | 19 |

**Evidence:** `ruff check --select F401` reports all 7.
**Fix:** `ruff check tests/ --select F401 --fix`

### 2. Unused `IOCType` import in `test_routes.py`

**Severity:** SAFE
**Lines saved:** 1

File: `/home/chris/projects/sentinelx/tests/test_routes.py`, line 316
```python
from app.pipeline.models import IOCType  # imported but never used
```

**Evidence:** ruff F401 report. The import is inside `test_enrichable_count_multi_provider()`
but `IOCType` is not referenced in the function body.
**Fix:** Remove the import line.

### 3. Unused variable `csrf_app` in `test_routes.py`

**Severity:** SAFE
**Lines saved:** 1

File: `/home/chris/projects/sentinelx/tests/test_routes.py`, line 144
```python
csrf_app = app  # The conftest fixture has CSRF disabled
```

**Evidence:** ruff F841 report. Variable is assigned but never read. The test
immediately creates a new `prod_like_app` on the next line. This assignment was
likely a leftover from an earlier implementation.
**Fix:** Remove the line. The `app` fixture parameter is still needed to satisfy
pytest injection, but the assignment is dead.

### 4. Unused `TestConfig` class in `app/config.py`

**Severity:** SAFE
**Lines saved:** ~10

File: `/home/chris/projects/sentinelx/app/config.py`, lines 56-64
```python
class TestConfig(Config):
    """Test configuration. Disables CSRF and rate limiting for test client."""
    TESTING: bool = True
    WTF_CSRF_ENABLED: bool = False
    RATELIMIT_ENABLED: bool = False
    SERVER_NAME: str = "localhost"
    SECRET_KEY: str = "test-secret-key-not-for-production"
```

**Evidence:** Zero imports of `TestConfig` anywhere in the codebase:
- `grep -r "TestConfig" app/ tests/ --include='*.py'` returns only the definition
- `grep -r "from app.config import" app/ tests/ --include='*.py'` returns only
  `from .config import Config` in `app/__init__.py`
- Tests use `create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False, ...})` dict
  override pattern exclusively

**Note:** The prior analysis (2026-02-25) incorrectly marked this as a false
positive ("Used by tests via create_app({'TESTING': True, ...}) pattern"). The
tests do NOT import or reference `TestConfig` -- they pass config dicts directly.

### 5. Unused `.btn-ghost` CSS class

**Severity:** SAFE
**Lines saved:** ~15

File: `/home/chris/projects/sentinelx/app/static/src/input.css`, lines 468-483
```css
.btn-ghost { ... }
.btn-ghost:hover:not(:disabled) { ... }
.btn-ghost:disabled { ... }
```

**Evidence:** Not used in any template, JS file, or test:
- `grep -r "btn-ghost" app/templates/ app/static/main.js tests/` returns zero results
- Only appears in the CSS definition itself

### 6. Installed package `pycryptodome` -- not used

**Severity:** SAFE (not in requirements.txt, just installed in venv)

**Evidence:**
- `grep -r "Crypto\|pycryptodome" app/ tests/` returns zero results
- `pip show pycryptodome` shows "Required-by: (nothing)"
- Not listed in `requirements.txt`
- Was likely installed for experimentation or as a dependency that was later removed

**Fix:** `pip uninstall pycryptodome` (development environment only, not a
requirements.txt change needed)

---

## CAUTION -- Verify Before Action

### 7. Missing CSS definitions for settings page classes

**Severity:** CAUTION (functional gap, not dead code)

The settings template uses 7 CSS classes that have NO corresponding definition
in `input.css`:

| Class | Used In |
|-------|---------|
| `.settings-card` | `settings.html:5` |
| `.settings-title` | `settings.html:6` |
| `.settings-section` | `settings.html:14` |
| `.settings-section-title` | `settings.html:15` |
| `.settings-info` | `settings.html:17, 21` |
| `.settings-note` | `settings.html:28` |
| `.input-group` | `settings.html:36` |

**Impact:** These elements render with no custom styling. They rely on inherited
styles from parent selectors (`.page-settings`, base reset, etc.) and the Tailwind
preflight layer. The page still looks acceptable but has no dedicated styling for
these components.

**Action:** Either add CSS definitions for these classes (design work), or remove
the class attributes from the template if no styling is intended. This is a v1.2
milestone item -- these classes were likely added as placeholders during the
redesign.

### 8. Missing CSS definitions for `alert-success` and `alert-warning`

**Severity:** CAUTION (functional gap)

The Flask routes flash messages with categories `"success"` and `"warning"`:
```python
flash("API key saved successfully.", "success")
flash("Please configure your VirusTotal API key...", "warning")
```

The `settings.html` template renders them as:
```html
<div class="alert alert-{{ category }}">{{ message }}</div>
```

Only `.alert-error` has a CSS definition. `.alert-success` and `.alert-warning`
are not defined, so success/warning flash messages render with the base `.alert`
styling only (no colored background/border).

**Action:** Add CSS definitions for `.alert-success` and `.alert-warning` in
`input.css`, following the same pattern as `.alert-error`.

### 9. Empty `Config.validate()` method

**Severity:** CAUTION

File: `/home/chris/projects/sentinelx/app/config.py`, lines 47-53

The method is documented as "currently a no-op" but is still called from
`app/__init__.py:61`. It's an intentional extension point for future validation.

**Action:** Keep as-is. This is a design decision, not dead code.

### 10. `_DOMAIN_BLACKLIST` variable scope

**Severity:** CAUTION (not dead, but hardcoded)

File: `/home/chris/projects/sentinelx/app/pipeline/classifier.py`, line 41
```python
_DOMAIN_BLACKLIST = {"localhost"}
```

Not dead code -- it's used in the `classify()` function. But it's a single-element
set that could be a constant or moved to config. Low priority.

### 11. `tools/security_check.py` -- standalone script

**Severity:** CAUTION

A 23KB security scanning script at `/home/chris/projects/sentinelx/tools/security_check.py`.
Not imported by any module, no tests for it, and `tools/` is in `.gitignore` (so
the script itself is not tracked). It's a development utility.

**Action:** No action needed. The script is a standalone tool, not part of the
application. If you want it tracked, remove `tools/` from `.gitignore` and add a
more specific `tools/tailwindcss` entry instead.

---

## DANGER -- False Positives (Do Not Touch)

vulture reported these at 60% confidence. All are false positives:

| Finding | Why It Is Not Dead |
|---------|-------------------|
| `create_app` (app/__init__.py:20) | Flask app factory, called from `run.py` and `tests/conftest.py` |
| `app.debug = False` (app/__init__.py:52) | SEC-15: hardcoded debug flag, assigned to Flask app attribute |
| `set_security_headers` (app/__init__.py:69) | Flask `@app.after_request` decorator -- invoked by framework |
| `request_entity_too_large` (app/__init__.py:80) | Flask `@app.errorhandler(413)` -- invoked by framework |
| `rate_limit_exceeded` (app/__init__.py:85) | Flask `@app.errorhandler(429)` -- invoked by framework |
| `index` (routes.py:83) | Flask `@bp.route("/")` -- URL route handler |
| `analyze` (routes.py:90) | Flask `@bp.route("/analyze")` -- URL route handler |
| `settings_get` (routes.py:163) | Flask `@bp.route("/settings", GET)` -- URL route handler |
| `settings_post` (routes.py:178) | Flask `@bp.route("/settings", POST)` -- URL route handler |
| `enrichment_status` (routes.py:199) | Flask `@bp.route("/enrichment/status/...")` -- URL route handler |
| `VIRUSTOTAL_API_KEY` (config.py:26) | Config class attribute, read by Flask app at startup |
| `DEBUG` (config.py:37) | Config class attribute, intentional `False` constant |
| `TESTING`, `RATELIMIT_ENABLED`, `SERVER_NAME` | Part of `TestConfig` (which is itself unused -- see finding #4) |
| `from __future__ import annotations` | PEP 563, implicitly used for deferred type evaluation |

---

## Dependency Analysis

### requirements.txt -- All Verified Used

| Package | Import Location | Status |
|---------|----------------|--------|
| Flask==3.1.1 | app/__init__.py, routes.py | USED |
| Flask-Limiter==4.1.1 | app/__init__.py | USED |
| Flask-WTF==1.2.2 | app/__init__.py | USED |
| iocextract==1.16.1 | app/pipeline/extractor.py | USED |
| iocsearcher==2.7.2 | app/pipeline/extractor.py | USED |
| python-dotenv==1.1.0 | app/config.py (`from dotenv`) | USED |
| requests==2.32.5 | All 3 enrichment adapters | USED |

No unused production dependencies found.

### Dev-Only Packages (installed but not in requirements.txt)

| Package | Purpose | Action |
|---------|---------|--------|
| bandit | Security linter | Keep (used by tools/security_check.py) |
| pycryptodome | Crypto library | **UNUSED** -- safe to uninstall |
| playwright | E2E browser testing | Keep (E2E tests) |
| pytest, pytest-cov, pytest-flask | Testing | Keep |
| ruff | Linting | Keep |
| vulture, pipdeptree | Analysis tools (just installed) | Can uninstall if not needed |

**Recommendation:** Create a `requirements-dev.txt` to track dev dependencies
explicitly.

---

## File-Level Analysis

### Orphaned Files: NONE

Every `.py` file under `app/` is imported by at least one other file:

| File | References |
|------|-----------|
| config.py | 8 |
| routes.py | 3 |
| pipeline/models.py | 18 |
| pipeline/extractor.py | 4 |
| pipeline/normalizer.py | 3 |
| pipeline/classifier.py | 3 |
| enrichment/models.py | 18 |
| enrichment/orchestrator.py | 3 |
| enrichment/config_store.py | 2 |
| enrichment/http_safety.py | 6 |
| enrichment/adapters/virustotal.py | 6 |
| enrichment/adapters/malwarebazaar.py | 3 |
| enrichment/adapters/threatfox.py | 4 |

### Static Files: All Referenced

| File | Referenced By |
|------|-------------|
| static/main.js | base.html |
| static/dist/style.css | base.html |
| static/fonts/InterVariable.woff2 | base.html, input.css |
| static/fonts/JetBrainsMonoVariable.woff2 | base.html, input.css |
| static/images/logo.svg | base.html |
| static/src/input.css | Makefile |

### Template Files: All Referenced

| File | Referenced By |
|------|-------------|
| templates/base.html | Extended by index.html, results.html, settings.html |
| templates/index.html | routes.py `render_template("index.html")` |
| templates/results.html | routes.py `render_template("results.html")` |
| templates/settings.html | routes.py `render_template("settings.html")` |
| templates/macros/icons.html | base.html `{% from "macros/icons.html" ... %}` |

### Commented-Out Code: NONE

Zero instances of commented-out code (`# import`, `# def`, `# class`, etc.) in
any `app/` Python files. All comments are legitimate documentation.

---

## Recommended Actions (Priority Order)

### Immediate (SAFE, zero risk)

1. **Remove 8 unused imports in test files**
   - Run: `.venv/bin/ruff check tests/ --select F401 --fix`
   - Then: `.venv/bin/ruff check tests/ --select F841 --unsafe-fixes --fix`
   - Lines saved: ~9
   - Risk: None (test-only, ruff auto-fix)

2. **Remove `TestConfig` class from `app/config.py`**
   - Delete lines 56-64
   - Lines saved: ~10
   - Risk: None (verified zero imports)

3. **Remove `.btn-ghost` CSS class from `input.css`**
   - Delete lines 468-483
   - Lines saved: ~15
   - Risk: None (verified zero usage)

4. **Uninstall `pycryptodome` from venv**
   - Run: `.venv/bin/pip uninstall pycryptodome`
   - Risk: None (not imported anywhere)

### Short-Term (CAUTION, verify first)

5. **Add missing CSS for settings page classes**
   - Add `.settings-card`, `.settings-title`, `.settings-section`,
     `.settings-section-title`, `.settings-info`, `.settings-note`, `.input-group`
   - This is a design task, not a cleanup task

6. **Add missing CSS for `.alert-success` and `.alert-warning`**
   - Follow the `.alert-error` pattern
   - Test flash messages on settings page

### Housekeeping

7. **Fix ruff deprecation warning**
   - In `pyproject.toml`, move `select` from `[tool.ruff]` to `[tool.ruff.lint]`

8. **Consider creating `requirements-dev.txt`**
   - Track: bandit, playwright, pytest, pytest-cov, pytest-flask, ruff

---

## Estimated Impact of All SAFE Removals

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Test unused imports | 8 | 0 | -8 lines |
| Dead Python classes | 1 | 0 | -10 lines |
| Dead CSS classes | 1 | 0 | -15 lines |
| Unused pip packages | 1 | 0 | -1 package |
| Total lines removed | -- | -- | ~33 |

This is a very modest cleanup, which reflects the codebase's overall quality.
The project has no significant dead code accumulation.
