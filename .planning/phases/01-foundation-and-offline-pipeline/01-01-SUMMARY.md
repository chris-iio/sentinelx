---
phase: 01-foundation-and-offline-pipeline
plan: 01
subsystem: infra
tags: [flask, python, security, csrf, csp, ioc, dataclass]

# Dependency graph
requires: []
provides:
  - Flask app factory (create_app) with full security scaffold
  - Config class reading env vars with startup validation
  - IOCType enum and IOC frozen dataclass for pipeline use
  - run.py entry point binding to 127.0.0.1 only
  - pytest fixtures (app, client) for all subsequent test plans
affects:
  - 01-02 (normalizer needs IOCType/IOC models)
  - 01-03 (extractor needs IOCType/IOC models and app factory)
  - 01-04 (UI routes build on app factory and blueprint pattern)
  - all subsequent plans (use conftest.py fixtures)

# Tech tracking
tech-stack:
  added:
    - Flask 3.1.1
    - Flask-WTF 1.2.2 (CSRFProtect)
    - iocextract 1.16.1
    - iocsearcher 2.7.2
    - python-dotenv 1.1.0
    - requests 2.32.5 (iocextract undeclared dependency)
    - pytest 9.0.2 + pytest-flask 1.3.0
    - ruff 0.15.2
    - bandit 1.9.3
  patterns:
    - Application factory pattern (create_app with config_override)
    - Security-first scaffold (all defenses in factory before route registration)
    - Pure pipeline functions (no Flask context, no HTTP calls)
    - Frozen dataclass for immutable IOC values
    - after_request security header injection

key-files:
  created:
    - app/__init__.py (create_app factory with full security scaffold)
    - app/config.py (Config class with env var reading and validation)
    - app/routes.py (Blueprint with placeholder GET / and POST /analyze)
    - app/pipeline/__init__.py (pipeline package init)
    - app/pipeline/models.py (IOCType enum, IOC frozen dataclass, group_by_type)
    - run.py (production entry point binding 127.0.0.1:5000)
    - tests/conftest.py (app and client pytest fixtures)
    - pyproject.toml (project config, ruff, pytest settings)
    - requirements.txt (pinned deps including requests workaround)
    - .gitignore (excludes .venv, .env, __pycache__, dist)
    - .env.example (documents SECRET_KEY and future API keys)
  modified: []

key-decisions:
  - "Python 3.10 used instead of 3.12 — python3.12 not available in WSL environment; Flask 3.1 and all deps are fully compatible with 3.10"
  - "requests added as explicit requirement — iocextract 1.16.1 depends on requests but does not declare it in its package metadata"
  - "app.debug = False applied twice in create_app to prevent accidental re-enable via config_override"
  - "ALLOWED_API_HOSTS list established as empty in Phase 1 so Phase 2 cannot add outbound calls without populating it"
  - "flask-talisman excluded — uses manual after_request headers per research recommendation (talisman low maintenance)"

patterns-established:
  - "Security scaffold pattern: all defenses (TRUSTED_HOSTS, MAX_CONTENT_LENGTH, CSRF, CSP) set in create_app before blueprint registration"
  - "Test config override pattern: create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False, 'SERVER_NAME': 'localhost'})"
  - "Pipeline boundary pattern: pipeline/ contains pure functions only, no Flask imports, no HTTP calls"
  - "Frozen dataclass pattern: IOC dataclass is immutable — value and raw_match cannot be mutated after creation"

requirements-completed: [SEC-01, SEC-02, SEC-03, SEC-08, SEC-09, SEC-10, SEC-11, SEC-12, SEC-13, SEC-14, SEC-15]

# Metrics
duration: 4min
completed: 2026-02-21
---

# Phase 1 Plan 01: Project Scaffold and Security Foundation Summary

**Flask 3.1 app factory with TRUSTED_HOSTS, CSRF, CSP, MAX_CONTENT_LENGTH, and frozen IOC dataclass — all security defenses established before any route code**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-21T08:21:35Z
- **Completed:** 2026-02-21T08:26:06Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments

- Flask application factory creates app with complete security scaffold (all 11 SEC requirements structurally addressed) before any routes are registered
- IOCType enum (8 types) and IOC frozen dataclass established as the typed foundation for all pipeline plans
- pytest fixtures (app, client) in conftest.py ready for all subsequent test plans
- bandit -r app/ reports zero issues at any severity level

## Task Commits

1. **Task 1: Create project scaffold and dependencies** - `67b543c` (chore)
2. **Task 2: Create app factory with security scaffold, Config, models, and test fixtures** - `d63782c` (feat)

## Files Created/Modified

- `app/__init__.py` - Flask application factory with TRUSTED_HOSTS, MAX_CONTENT_LENGTH, CSRFProtect, after_request security headers, 413 handler, debug=False hardcoded
- `app/config.py` - Config class reading SECRET_KEY/VIRUSTOTAL_API_KEY from env, ALLOWED_API_HOSTS allowlist structure, validate() for fail-fast startup
- `app/routes.py` - Blueprint with placeholder GET / and POST /analyze (full implementation in Plans 03-04)
- `app/pipeline/__init__.py` - Pipeline package init with architecture documentation
- `app/pipeline/models.py` - IOCType enum (8 types), IOC frozen dataclass (value + raw_match), group_by_type() utility
- `run.py` - Production entry point binding 127.0.0.1:5000 with debug=False hardcoded
- `tests/conftest.py` - pytest fixtures: app (TestConfig) and client (test_client)
- `pyproject.toml` - Project config with ruff (target py310, E/F/W/S/B rules) and pytest (testpaths=tests)
- `requirements.txt` - Pinned Flask 3.1.1, Flask-WTF 1.2.2, iocextract 1.16.1, iocsearcher 2.7.2, python-dotenv 1.1.0, requests 2.32.5
- `.gitignore` - Excludes .venv, .env, __pycache__, *.pyc, dist, build, .pytest_cache, .ruff_cache
- `.env.example` - Documents SECRET_KEY and future VIRUSTOTAL_API_KEY

## Decisions Made

- Used Python 3.10 (not 3.12) because python3.12 is not installed in this WSL environment. Flask 3.1 supports Python 3.9+ and all behavior is identical on 3.10.
- Added `requests` explicitly to requirements.txt because iocextract 1.16.1 imports `requests` but does not declare it as a package dependency — installation would fail without it.
- Applied `app.debug = False` both before and after `config_override` to ensure debug mode cannot be accidentally enabled via config override, even if someone passes `{'DEBUG': True}`.
- Used manual `after_request` headers instead of flask-talisman per research findings (talisman has low maintenance activity and HTTPS-enforcement conflicts with localhost HTTP dev).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Python 3.12 unavailable — adapted to Python 3.10**
- **Found during:** Task 1 (project scaffold)
- **Issue:** Plan specified `python3.12 -m venv .venv` but Python 3.12 is not installed in this WSL environment (only Python 3.10.12 available)
- **Fix:** Used Python 3.10.12 throughout; updated `pyproject.toml` to `requires-python = ">=3.10"` and `target-version = "py310"` in ruff config. All libraries (Flask 3.1, Flask-WTF 1.2.2, iocextract, iocsearcher) support Python 3.9+ and are fully compatible.
- **Files modified:** `pyproject.toml`
- **Verification:** `.venv/bin/python --version` shows 3.10.12; all imports succeed
- **Committed in:** `67b543c` (Task 1 commit)

**2. [Rule 3 - Blocking] iocextract has undeclared requests dependency**
- **Found during:** Task 1 (dependency verification)
- **Issue:** `import iocextract` raised `ModuleNotFoundError: No module named 'requests'` — iocextract 1.16.1 imports `requests` at module level but does not declare it in package metadata
- **Fix:** Installed `requests==2.32.5` and added it explicitly to `requirements.txt` with explanatory comment
- **Files modified:** `requirements.txt`
- **Verification:** `import iocextract` succeeds after fix
- **Committed in:** `67b543c` (Task 1 commit)

**3. [Rule 3 - Blocking] pip not available in venv — bootstrapped via get-pip.py**
- **Found during:** Task 1 (virtual environment creation)
- **Issue:** `python3 -m venv .venv` failed with "ensurepip is not available" (missing python3.10-venv apt package); sudo not available
- **Fix:** Created venv with `--without-pip` flag then bootstrapped pip using `python3 /tmp/get-pip.py`
- **Files modified:** None (runtime only)
- **Verification:** `.venv/bin/pip --version` succeeds; all packages install correctly
- **Committed in:** Not committed (venv excluded from git by .gitignore)

---

**Total deviations:** 3 auto-fixed (3 blocking)
**Impact on plan:** All three fixes were necessary for the plan to execute. No scope creep — functional outcome is identical to the plan's intent. Python 3.10 vs 3.12 has no behavioral difference for this codebase.

## Issues Encountered

- Virtual environment creation required manual pip bootstrapping via get-pip.py because python3.10-venv apt package is not installed and sudo access is unavailable. Resolved cleanly.
- iocextract version pinned at 1.16.1 (plan specified same version) but its `requests` dependency is undeclared. Documented and fixed in requirements.txt.
- Flask version 3.1.3 specified in plan but 3.1.1 is the actual latest available on PyPI. 3.1.1 provides identical behavior for all features used in this plan.

## User Setup Required

None - no external service configuration required. Copy `.env.example` to `.env` and optionally set `SECRET_KEY` for persistent sessions.

## Next Phase Readiness

- App factory and security scaffold complete — Plans 02-05 can build on `create_app()` without modifying security config
- IOCType enum and IOC frozen dataclass ready for Plans 02 (normalizer) and 03 (extractor/classifier)
- pytest fixtures ready — all subsequent test plans can use `app` and `client` fixtures from conftest.py
- Blueprint registered — Plans 03-04 add real route implementations to replace placeholders

No blockers. All 11 SEC requirements for Phase 1 are structurally enforced.

## Self-Check: PASSED

All created files verified present. All task commits verified in git history.

---
*Phase: 01-foundation-and-offline-pipeline*
*Completed: 2026-02-21*
