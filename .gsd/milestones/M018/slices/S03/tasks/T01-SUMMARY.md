---
id: T01
parent: S03
milestone: M018
key_files:
  - app/routes/diagnostics.py
  - app/routes/__init__.py
  - app/templates/base.html
key_decisions:
  - Use the existing shared `main` blueprint for the diagnostic export endpoint so templates can reference `url_for('main.diagnostics_export')`.
  - Return bounded plain-text failure responses while preserving ERROR-level exception logging for server-side diagnosis.
duration: 
verification_result: passed
completed_at: 2026-05-12T10:03:18.731Z
blocker_discovered: false
---

# T01: Added a rate-limited `/diagnostics/export` Flask download route and nav link for analyst diagnostic bundles.

**Added a rate-limited `/diagnostics/export` Flask download route and nav link for analyst diagnostic bundles.**

## What Happened

Verified the existing T01 implementation creates `app/routes/diagnostics.py`, imports it through the shared `main` blueprint, and exposes a floating nav download affordance in `app/templates/base.html`. The route instantiates `ConfigStore`, reads `current_app.cache_store` and `current_app.history_store`, builds default diagnostic sources, assembles a UTC-stamped diagnostic ZIP, and returns it with application/zip download headers plus `X-Diagnostic-Sources`. Assembly failures are bounded to a plain-text 500 while logging a secret-free ERROR message with exception context for operators.

## Verification

Ran the task verification command to assert `/diagnostics/export` is registered, `app/routes/diagnostics.py` compiles, the diagnostics route module is imported, and the template references `main.diagnostics_export`. Also exercised the real Flask test-client GET route and confirmed status 200, application/zip content type, attachment disposition, numeric `X-Diagnostic-Sources`, and ZIP magic bytes.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "from app import create_app; app = create_app(); rules = [r.rule for r in app.url_map.iter_rules()]; assert '/diagnostics/export' in rules, f'route missing: {rules}'" && python3 -m py_compile app/routes/diagnostics.py && grep 'diagnostics' app/routes/__init__.py && grep 'diagnostics_export' app/templates/base.html` | 0 | ✅ pass | 287ms |
| 2 | `python3 - <<'PY'
from app import create_app
app = create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False})
client = app.test_client()
resp = client.get('/diagnostics/export')
assert resp.status_code == 200, (resp.status_code, resp.get_data(as_text=True)[:200])
assert resp.headers['Content-Type'].startswith('application/zip'), resp.headers['Content-Type']
assert 'attachment' in resp.headers['Content-Disposition'], resp.headers['Content-Disposition']
assert resp.headers['X-Diagnostic-Sources'].isdigit(), resp.headers.get('X-Diagnostic-Sources')
assert resp.data[:2] == b'PK', resp.data[:8]
print('ROUTE_SMOKE_OK status=200 content_type=%s sources=%s bytes=%d' % (resp.headers['Content-Type'], resp.headers['X-Diagnostic-Sources'], len(resp.data)))
PY` | 0 | ✅ pass | 269ms |

## Deviations

None.

## Known Issues

S03 contains a planned follow-up task (T02) for route-level test coverage and replacing the prior route-absence guard; the slice summary should be rendered only after all S03 tasks are complete.

## Files Created/Modified

- `app/routes/diagnostics.py`
- `app/routes/__init__.py`
- `app/templates/base.html`
