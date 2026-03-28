---
estimated_steps: 11
estimated_files: 1
skills_used: []
---

# T02: API test coverage

1. Create tests/test_api.py with comprehensive tests:
   - POST /api/analyze with valid text → 200 JSON with iocs array
   - POST /api/analyze with empty text → 400 JSON error
   - POST /api/analyze with no JSON body → 400 JSON error
   - POST /api/analyze without CSRF token → 200 (exempt)
   - POST /api/analyze in online mode with configured provider → 200 with job_id
   - GET /api/status/<job_id> with known job → 200 JSON progress
   - GET /api/status/<unknown> → 404 JSON error
   - POST /api/analyze with invalid mode → 400 JSON error
   - Verify IOC extraction matches browser pipeline (same input → same IOCs)
2. Run full test suite to confirm no regressions.

## Inputs

- `app/routes/api.py`

## Expected Output

- `tests/test_api.py`

## Verification

python3 -m pytest tests/test_api.py -v && python3 -m pytest -x -q
