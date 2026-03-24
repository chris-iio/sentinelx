---
id: T03
parent: S04
milestone: M004
provides:
  - CSP header with all 7 required directives (default-src, script-src, style-src, connect-src, img-src, font-src, object-src) per R025
  - SECRET_KEY startup warning logged when env var is unset per R025
  - Rate limiter storage documented as memory:// with explanatory comment (D038)
key_files:
  - app/__init__.py
key_decisions:
  - "D038: Rate limiter stays memory:// — limits library has no filesystem backend; Redis/Memcached inappropriate for single-process local tool"
patterns_established:
  - Security-relevant logging uses module-level logger (logging.getLogger(__name__)) in app/__init__.py
observability_surfaces:
  - "SECRET_KEY warning: logged at WARNING level on app startup when SECRET_KEY env var is unset"
  - "CSP header: inspectable via curl -sI http://localhost:5000/ | grep -i content-security-policy"
duration: 10m
verification_result: passed
completed_at: 2026-03-24
blocker_discovered: false
---

# T03: CSP header expansion + SECRET_KEY startup warning (R025)

**Expanded CSP header to 7 directives (style-src, connect-src, img-src, font-src, object-src 'none') and added SECRET_KEY startup warning for R025 compliance**

## What Happened

Made three changes to `app/__init__.py`:

1. **CSP header expansion** — replaced the minimal 2-directive CSP (`default-src 'self'; script-src 'self'`) with a comprehensive 7-directive policy adding `style-src 'self'`, `connect-src 'self'`, `img-src 'self'`, `font-src 'self'`, and `object-src 'none'`. The `object-src 'none'` directive blocks plugin-based attack vectors (Flash, Java applets).

2. **SECRET_KEY startup warning** — added `import logging` and `import os` at module level, created a module-level logger, and added a conditional warning in `create_app()` that fires when `SECRET_KEY` is not set in the environment. The warning explains the consequence: sessions and CSRF tokens won't persist across restarts.

3. **Rate limiter storage comment** — added an explanatory comment on the `limiter = Limiter(...)` line documenting why `memory://` is kept: the `limits` library has no filesystem backend, and Redis/Memcached would add inappropriate infrastructure for a local dev tool. Recorded as decision D038.

## Verification

All task-level and slice-level verification checks pass:

- `python3 -m pytest tests/ -x -q` — 944 passed, 0 failed
- CSP directives confirmed via grep: style-src, connect-src, object-src 'none' all present
- SECRET_KEY warning confirmed via `python3 -c "from app import create_app; ..."` — warning fires when env var is unset
- Live CSP header verified via test client — all 7 directives present in response headers
- TypeScript clean: `npx tsc --noEmit` exits 0
- All 12 slice verification checks pass (this is the final task of the slice)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/ -x -q` | 0 | ✅ pass | 46.9s |
| 2 | `grep -q "style-src" app/__init__.py` | 0 | ✅ pass | <1s |
| 3 | `grep -q "connect-src" app/__init__.py` | 0 | ✅ pass | <1s |
| 4 | `grep -q "object-src 'none'" app/__init__.py` | 0 | ✅ pass | <1s |
| 5 | `grep -q "SECRET_KEY not set" app/__init__.py` | 0 | ✅ pass | <1s |
| 6 | `python3 -c "import app; print('import OK')"` | 0 | ✅ pass | <1s |
| 7 | `grep -rl "from tests.helpers import" tests/test_*.py \| wc -l` → 10 | 0 | ✅ pass | <1s |
| 8 | `! grep -l "def _make_mock_.*response" tests/test_*.py` | 0 | ✅ pass | <1s |
| 9 | `grep -q '"incremental": true' tsconfig.json` | 0 | ✅ pass | <1s |
| 10 | `grep -q "ioc-type-badge--email" tailwind.config.js` | 0 | ✅ pass | <1s |
| 11 | `npx tsc --noEmit` | 0 | ✅ pass | <1s |
| 12 | `python3 -c "from tests.helpers import make_mock_response; ..."` | 0 | ✅ pass | <1s |
| 13 | CSP header in live test client response | 0 | ✅ pass | <1s |

## Diagnostics

- **CSP header inspection**: `curl -sI http://localhost:5000/ | grep -i content-security-policy` shows the live CSP header with all 7 directives.
- **SECRET_KEY warning**: When the app starts without `SECRET_KEY` in env, the warning is visible in stderr/logs. Verify with `python3 -c "from app import create_app; create_app()" 2>&1 | grep SECRET_KEY`.
- **Rate limiter comment**: `grep -A2 "memory://" app/__init__.py` shows the explanatory comment documenting why memory:// is retained.
- **Failure tracing**: If a CSP-related browser error appears (e.g., blocked style or image loading), the CSP string in `set_security_headers()` is the single location to inspect. Each directive is on its own line for easy scanning.

## Deviations

None — implementation matched the task plan exactly.

## Known Issues

None.

## Files Created/Modified

- `app/__init__.py` — expanded CSP header to 7 directives, added SECRET_KEY startup warning with module-level logger, added rate limiter storage explanatory comment
- `.gsd/milestones/M004/slices/S04/S04-PLAN.md` — added failure-path diagnostic check for CSP in verification section (pre-flight fix)
