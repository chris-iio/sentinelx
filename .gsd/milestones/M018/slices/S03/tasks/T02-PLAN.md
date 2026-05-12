---
estimated_steps: 1
estimated_files: 2
skills_used: []
---

# T02: Route tests: headers, archive content, redaction, and bounded errors

Create tests/test_diagnostic_export_route.py with Flask test-client route tests. Use create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False}) and inject a fake ConfigStore (or use the real one with no secrets configured). Tests must cover: (1) GET /diagnostics/export returns 200 with Content-Type application/zip and Content-Disposition header containing 'attachment' and a .zip filename; (2) the response body is a valid ZIP archive containing manifest.json; (3) no configured provider secret values appear in the raw archive bytes (use a patched ConfigStore that returns a known test-only secret and assert it is absent); (4) patching assemble_diagnostic_bundle to raise RuntimeError causes the route to return 500 with Content-Type text/plain and body containing 'Diagnostic export failed' but not the exception message or any stack trace text; (5) X-Diagnostic-Sources header is present and numeric. Also update tests/test_diagnostic_export_bundle_integration.py to remove or replace the route-absence assertions (the negative guard is now superseded by the positive route tests); the rest of the integration suite must still pass. Run: python3 -m pytest tests/test_diagnostic_export_route.py tests/test_diagnostic_export_bundle_integration.py tests/test_diagnostic_export_assembler.py tests/test_diagnostic_export_sources.py -q

## Inputs

- `app/routes/diagnostics.py`
- `app/routes/__init__.py`
- `app/__init__.py`
- `app/diagnostics/__init__.py`
- `app/diagnostics/assembler.py`
- `app/diagnostics/sources.py`
- `tests/test_diagnostic_export_bundle_integration.py`
- `tests/test_diagnostic_export_assembler.py`
- `tests/test_diagnostic_export_sources.py`

## Expected Output

- `tests/test_diagnostic_export_route.py`
- `tests/test_diagnostic_export_bundle_integration.py`

## Verification

python3 -m pytest tests/test_diagnostic_export_route.py tests/test_diagnostic_export_bundle_integration.py tests/test_diagnostic_export_assembler.py tests/test_diagnostic_export_sources.py -q 2>&1 | tail -5
