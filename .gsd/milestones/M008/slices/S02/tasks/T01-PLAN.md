---
estimated_steps: 12
estimated_files: 2
skills_used: []
---

# T01: Implement API blueprint

1. Create app/routes/api.py with bp_api Blueprint (url_prefix='/api').
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

## Inputs

- `app/routes/_helpers.py`
- `app/routes/enrichment.py`

## Expected Output

- `app/routes/api.py`

## Verification

python3 -c "from app.routes.api import bp_api; print('OK')" && python3 -m pytest -x -q
