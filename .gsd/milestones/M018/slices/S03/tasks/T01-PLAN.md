---
estimated_steps: 1
estimated_files: 3
skills_used: []
---

# T01: Add diagnostic export route and nav affordance

Create app/routes/diagnostics.py with a GET /diagnostics/export route on the main blueprint. The route must: (1) instantiate ConfigStore(), read current_app.cache_store and current_app.history_store, call build_default_diagnostic_sources() with those runtime objects; (2) call assemble_diagnostic_bundle(sources, generated_at=..., config_store=config_store) with a UTC ISO timestamp; (3) return ZIP bytes with Content-Type: application/zip, Content-Disposition: attachment; filename="sentinelx-diagnostic-YYYY-MM-DD.zip", and X-Diagnostic-Sources: <count> headers; (4) on any exception from assemble_diagnostic_bundle, log at ERROR level (message only, no exc repr that could contain secrets) and return a plain-text 500 reading 'Diagnostic export failed. Check server logs.' with no stack trace or internal detail; (5) apply @limiter.limit('3 per minute'). Register the new module in app/routes/__init__.py via 'from . import diagnostics'. Add a nav download link to app/templates/base.html in the floating-settings nav, pointing to url_for('main.diagnostics_export') with aria-label='Download diagnostic export'.

## Inputs

- `app/diagnostics/__init__.py`
- `app/diagnostics/assembler.py`
- `app/diagnostics/sources.py`
- `app/routes/_helpers.py`
- `app/routes/__init__.py`
- `app/routes/history.py`
- `app/templates/base.html`
- `app/__init__.py`

## Expected Output

- `app/routes/diagnostics.py`
- `app/routes/__init__.py`
- `app/templates/base.html`

## Verification

python3 -c "from app import create_app; app = create_app(); rules = [r.rule for r in app.url_map.iter_rules()]; assert '/diagnostics/export' in rules, f'route missing: {rules}'" && python3 -m py_compile app/routes/diagnostics.py && grep 'diagnostics' app/routes/__init__.py && grep 'diagnostics_export' app/templates/base.html
