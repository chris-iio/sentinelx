---
estimated_steps: 3
estimated_files: 2
skills_used: []
---

# T03: CSP header expansion + SECRET_KEY startup warning (R025)

**Slice:** S04 — Test DRY-up — shared adapter fixtures
**Milestone:** M004

## Description

R025 requires: (1) the CSP header must include `style-src 'self'`, `connect-src 'self'`, `img-src 'self'`, `font-src 'self'`, and `object-src 'none'` — currently it only has `default-src 'self'; script-src 'self'`; (2) when `SECRET_KEY` is not set in the environment, a startup warning must be logged.

R025 also mentions rate limiter persistent storage. Flask-Limiter's `limits` library only supports Memory, Redis, Memcached, and MongoDB backends — there is no filesystem backend. Since SentinelX is a single-process local dev tool, adding Redis/Memcached infrastructure is inappropriate. The rate limiter stays as `memory://` with an explanatory comment. A decision will be recorded documenting this.

## Steps

1. **Expand CSP header in `app/__init__.py`** — in the `set_security_headers()` function (currently at ~line 71), replace the current CSP line:
   ```python
   response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'"
   ```
   With:
   ```python
   response.headers["Content-Security-Policy"] = (
       "default-src 'self'; "
       "script-src 'self'; "
       "style-src 'self'; "
       "connect-src 'self'; "
       "img-src 'self'; "
       "font-src 'self'; "
       "object-src 'none'"
   )
   ```

2. **Add SECRET_KEY startup warning in `app/__init__.py`** — in the `create_app()` function, after the line `app.config["SECRET_KEY"] = config.SECRET_KEY`, add:
   ```python
   import logging
   import os
   logger = logging.getLogger(__name__)
   if not os.environ.get("SECRET_KEY"):
       logger.warning(
           "SECRET_KEY not set in environment — using auto-generated key. "
           "Sessions and CSRF tokens will not persist across restarts."
       )
   ```
   Move the `import logging` and `import os` to the top of the file (module-level imports) rather than inside the function. Check if `os` is already imported (it may be via `app/config.py` but not in `__init__.py` itself).

3. **Add explanatory comment on rate limiter storage** — on the `limiter = Limiter(...)` line (currently line 17), add a comment:
   ```python
   # SEC-21: Rate limiting — memory:// is acceptable for single-process local tool.
   # limits library has no filesystem backend; Redis/Memcached require infrastructure.
   limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
   ```

## Must-Haves

- [ ] CSP header includes all 7 directives: default-src, script-src, style-src, connect-src, img-src, font-src, object-src
- [ ] `object-src 'none'` is present in CSP (blocks plugin-based attacks)
- [ ] Startup warning logged when SECRET_KEY env var is not set
- [ ] All 944+ tests pass with 0 failures
- [ ] Rate limiter has explanatory comment documenting why memory:// is kept

## Verification

- `python3 -m pytest tests/ -x -q` — must show ≥944 passed, 0 failed
- `grep -q "style-src" app/__init__.py && echo OK` — must print OK
- `grep -q "connect-src" app/__init__.py && echo OK` — must print OK
- `grep -q "object-src 'none'" app/__init__.py && echo OK` — must print OK
- `grep -q "SECRET_KEY not set" app/__init__.py && echo OK` — must print OK
- `python3 -c "import app; print('import OK')"` — must not crash

## Inputs

- `app/__init__.py` — Flask app factory with current CSP header and limiter setup
- `app/config.py` — Config class with SECRET_KEY generation logic

## Expected Output

- `app/__init__.py` — expanded CSP header, SECRET_KEY warning, rate limiter comment
