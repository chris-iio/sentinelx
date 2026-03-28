# S02: REST API blueprint

**Goal:** Add a JSON REST API for programmatic IOC submission, fulfilling R035
**Demo:** After this: POST /api/analyze returns JSON with extracted IOCs. Online mode returns job_id for polling via GET /api/status/<job_id>. CSRF exempt, rate-limited.

## Tasks
- [x] **T01: Implemented REST API blueprint with POST /api/analyze and GET /api/status endpoints, CSRF-exempt and rate-limited.** — 1. Create app/routes/api.py with bp_api Blueprint (url_prefix='/api').
2. POST /api/analyze:
   - Accept JSON body: {"text": "...", "mode": "offline"} (mode defaults to offline)
   - Run pipeline, return {"iocs": [{"type": "ipv4", "value": "8.8.8.8", "raw_match": "8.8.8.8"}, ...], "total_count": N}
   - Online mode: also return {"job_id": "..."} for polling, launch background enrichment
   - Validate: 400 if no JSON body, 400 if text is empty, 400 if mode is invalid
3. GET /api/status/<job_id>:
   - Reuse enrichment_status logic from _helpers.py (or import from enrichment.py)
   - Same JSON response as the existing HTML polling endpoint
4. Exempt bp_api from CSRF (csrf.exempt(bp_api) in __init__.py)
5. Add rate limits (10/min for analyze, 120/min for status)
6. Register bp_api in app/routes/__init__.py
  - Estimate: 30min
  - Files: app/routes/api.py, app/routes/__init__.py
  - Verify: python3 -c "from app.routes.api import bp_api; print('OK')" && python3 -m pytest -x -q
- [x] **T02: Added 18 API tests covering validation, offline/online extraction, status polling, and CSRF exemption.** — 1. Create tests/test_api.py with comprehensive tests:
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
  - Estimate: 25min
  - Files: tests/test_api.py
  - Verify: python3 -m pytest tests/test_api.py -v && python3 -m pytest -x -q
